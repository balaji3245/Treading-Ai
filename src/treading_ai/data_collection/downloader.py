"""Historical data downloader for XAUUSD spot data from HistData.com.

Provides automated, robust, and reproducible downloading of M1 historical bar
quotes with full provenance tracking, integrity verification, and metadata generation.
"""

from datetime import datetime, timedelta, timezone
import hashlib
import json
import logging
from pathlib import Path
import re
import time
from typing import Any, Dict, Optional, Tuple
import zipfile
from zoneinfo import ZoneInfo


import requests

from treading_ai.config import (
    HISTDATA_BASE_URL,
    HISTDATA_CSV_SEP,
    HISTDATA_DATETIME_FORMAT,
    HISTDATA_DEFAULT_SYMBOL,
    HISTDATA_DOWNLOAD_ENDPOINT,
    HISTDATA_TIMEZONE,
    RAW_DATA_DIR,
)

logger = logging.getLogger(__name__)


class PeriodUnavailableError(Exception):
    """Raised when a requested historical period is unavailable or not yet published on HistData."""
    pass


class ArchiveCorruptionError(Exception):
    """Raised when a downloaded archive fails CRC or format verification."""
    pass


def compute_sha256(filepath: Path) -> str:
    """Compute SHA-256 hash of a file for integrity and provenance tracking."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def inspect_raw_csv_metadata(csv_path: Path) -> Dict[str, Any]:
    """Inspect raw HistData CSV to calculate line count and boundary timestamps in UTC.

    HistData timestamps originate from a European DST feeder server (Europe/London with -5h offset).
    """
    row_count = 0
    first_line: Optional[str] = None
    last_line: Optional[str] = None

    with open(csv_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            if row_count == 0:
                first_line = stripped
            last_line = stripped
            row_count += 1

    start_iso = None
    end_iso = None
    london_tz = ZoneInfo("Europe/London")

    if first_line:
        try:
            dt_part = first_line.split(HISTDATA_CSV_SEP)[0].strip()
            dt_naive = datetime.strptime(dt_part, HISTDATA_DATETIME_FORMAT)
            london_dt = (dt_naive + timedelta(hours=5)).replace(tzinfo=london_tz)
            start_iso = london_dt.astimezone(timezone.utc).isoformat()
        except Exception as e:
            logger.warning("Could not parse start timestamp from line '%s': %s", first_line, e)

    if last_line:
        try:
            dt_part = last_line.split(HISTDATA_CSV_SEP)[0].strip()
            dt_naive = datetime.strptime(dt_part, HISTDATA_DATETIME_FORMAT)
            london_dt = (dt_naive + timedelta(hours=5)).replace(tzinfo=london_tz)
            end_iso = london_dt.astimezone(timezone.utc).isoformat()
        except Exception as e:
            logger.warning("Could not parse end timestamp from line '%s': %s", last_line, e)

    return {
        "row_count": row_count,
        "start_timestamp_utc": start_iso,
        "end_timestamp_utc": end_iso,
    }


class HistDataDownloader:
    """Downloader client for HistData.com free historical Forex / Gold data."""

    def __init__(
        self,
        base_url: str = HISTDATA_BASE_URL,
        download_endpoint: str = HISTDATA_DOWNLOAD_ENDPOINT,
        output_dir: Path = RAW_DATA_DIR,
        timeout_seconds: int = 30,
        max_retries: int = 3,
        backoff_factor: float = 2.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.download_endpoint = download_endpoint
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
        )

    def get_landing_url(self, symbol: str, year: int, month: Optional[int] = None) -> str:
        """Construct the HistData landing page URL for the requested symbol, year, and month."""
        symbol_lower = symbol.lower()
        if month is not None:
            return (
                f"{self.base_url}/download-free-forex-historical-data/"
                f"?/ascii/1-minute-bar-quotes/{symbol_lower}/{year}/{month}"
            )
        return (
            f"{self.base_url}/download-free-forex-historical-data/"
            f"?/ascii/1-minute-bar-quotes/{symbol_lower}/{year}"
        )

    def extract_download_token(self, html: str, year: Optional[int] = None, month: Optional[int] = None) -> str:
        """Extract the dynamic session download token from HistData landing page HTML.

        Raises PeriodUnavailableError if the page indicates the period is not available.
        """
        # Detect empty token inputs on monthly pages for completed annual archives or future months
        if re.search(r'<input[^>]*id=["\']tk["\'][^>]*value=["\']["\']', html) or re.search(r'<input[^>]*name=["\']tk["\'][^>]*value=["\']["\']', html):
            if month is not None:
                raise PeriodUnavailableError(
                    f"HistData does not provide monthly download for period {year}-{month:02d}. "
                    f"Completed historical years are packaged as full annual archives (use month=None), "
                    f"or this is an unreleased future month."
                )
            raise PeriodUnavailableError(f"Historical period {year} is not available on HistData.com.")

        match = re.search(r'name=["\']tk["\']\s+id=["\']tk["\']\s+value=["\']([a-zA-Z0-9_\-]+)["\']', html)
        if not match:
            # Fallback search if id and name appear in reverse order
            match = re.search(r'id=["\']tk["\']\s+name=["\']tk["\']\s+value=["\']([a-zA-Z0-9_\-]+)["\']', html)
        if not match:
            # General fallback matching input with id="tk" or name="tk"
            match = re.search(r'<input[^>]*(?:id=["\']tk["\']|name=["\']tk["\'])[^>]*value=["\']([a-zA-Z0-9_\-]+)["\']', html)
        if not match:
            # Fallback matching value first
            match = re.search(r'<input[^>]*value=["\']([a-zA-Z0-9_\-]+)["\'][^>]*(?:id=["\']tk["\']|name=["\']tk["\'])', html)
        if not match:
            raise PeriodUnavailableError(f"Could not extract download token ('tk') from HistData landing page for {year}-{month}.")
        return match.group(1)

    def download_xauusd_m1(
        self,
        year: int,
        month: Optional[int] = None,
        symbol: str = HISTDATA_DEFAULT_SYMBOL,
        force: bool = False,
    ) -> Dict[str, Any]:
        """Download and extract raw 1-minute historical data for XAUUSD.

        Parameters
        ----------
        year : int
            Calendar year (e.g., 2024, 2026).
        month : Optional[int]
            Calendar month (1-12) for monthly archives, or None for yearly archives.
        symbol : str
            Symbol identifier (default: "XAUUSD").
        force : bool
            If True, re-downloads even if files already exist locally.

        Returns
        -------
        Dict[str, Any]
            Detailed provenance metadata dictionary with status and data summary.
        """
        landing_url = self.get_landing_url(symbol, year, month)
        date_str = str(year)
        datemonth_str = f"{year}{month:02d}" if month is not None else str(year)

        # Expected file names
        zip_stem = f"HISTDATA_COM_ASCII_{symbol.upper()}_M1{datemonth_str}"
        zip_path = self.output_dir / f"{zip_stem}.zip"
        meta_path = self.output_dir / f"{zip_stem}_metadata.json"

        # Check for existing download if force is False
        if not force and meta_path.exists():
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    existing_meta = json.load(f)
                csv_name = existing_meta.get("files", {}).get("extracted_csv_name") or existing_meta.get("extracted_csv_name")
                if csv_name:
                    extracted_csv = self.output_dir / csv_name
                    if extracted_csv.is_file() and extracted_csv.stat().st_size > 0:
                        expected_sha = existing_meta.get("files", {}).get("extracted_csv_sha256")
                        actual_sha = compute_sha256(extracted_csv)
                        if not expected_sha or actual_sha == expected_sha:
                            # Verify zip integrity if zip exists
                            if zip_path.is_file():
                                with zipfile.ZipFile(zip_path, "r") as zf:
                                    if zf.testzip() is not None:
                                        raise ArchiveCorruptionError("Cached zip archive failed CRC test.")
                            # Ensure data summary exists in metadata
                            if "data_summary" not in existing_meta or not existing_meta["data_summary"].get("start_timestamp_utc"):
                                existing_meta["data_summary"] = inspect_raw_csv_metadata(extracted_csv)
                                with open(meta_path, "w", encoding="utf-8") as f:
                                    json.dump(existing_meta, f, indent=2)

                            existing_meta["status"] = "CACHED"
                            logger.info("Dataset already exists locally and verified: %s", extracted_csv)
                            return existing_meta
                        else:
                            logger.warning("Local CSV hash mismatch! Expected %s, got %s. Re-downloading.", expected_sha, actual_sha)
            except Exception as e:
                logger.warning("Error verifying cached metadata %s: %s. Re-downloading.", meta_path, e)

        logger.info("Connecting to landing page: %s", landing_url)
        token = None
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = self.session.get(landing_url, timeout=self.timeout_seconds)
                resp.raise_for_status()
                token = self.extract_download_token(resp.text, year=year, month=month)
                break
            except PeriodUnavailableError:
                raise
            except Exception as e:
                logger.warning("Attempt %d/%d to retrieve landing page failed: %s", attempt, self.max_retries, e)
                if attempt == self.max_retries:
                    raise RuntimeError(f"Failed to access HistData landing page {landing_url}: {e}") from e
                time.sleep(self.backoff_factor ** attempt)

        # Post payload required by HistData
        payload = {
            "tk": token,
            "date": date_str,
            "datemonth": datemonth_str,
            "platform": "ASCII",
            "timeframe": "M1",
            "fxpair": symbol.upper(),
        }

        post_headers = {
            "Referer": landing_url,
            "Origin": self.base_url,
            "Content-Type": "application/x-www-form-urlencoded",
        }

        logger.info("Requesting raw archive from: %s", self.download_endpoint)
        for attempt in range(1, self.max_retries + 1):
            try:
                post_resp = self.session.post(
                    self.download_endpoint,
                    data=payload,
                    headers=post_headers,
                    timeout=self.timeout_seconds,
                    stream=True,
                )
                post_resp.raise_for_status()

                # Stream response to temporary or final file
                with open(zip_path, "wb") as f:
                    for chunk in post_resp.iter_content(chunk_size=65536):
                        if chunk:
                            f.write(chunk)

                # Verify zip validity and test CRC
                with zipfile.ZipFile(zip_path, "r") as zf:
                    corrupt_file = zf.testzip()
                    if corrupt_file is not None:
                        raise ArchiveCorruptionError(f"Corrupted file in ZIP archive: {corrupt_file}")
                    extracted_names = zf.namelist()
                    if not extracted_names:
                        raise ArchiveCorruptionError("Downloaded archive is empty")
                    zf.extractall(self.output_dir)

                logger.info("Successfully extracted archive contents: %s", extracted_names)
                break
            except Exception as e:
                logger.warning("Attempt %d/%d to download data archive failed: %s", attempt, self.max_retries, e)
                if zip_path.exists():
                    zip_path.unlink()
                if attempt == self.max_retries:
                    raise RuntimeError(f"Failed to download data archive from HistData: {e}") from e
                time.sleep(self.backoff_factor ** attempt)

        # Identify extracted CSV and status TXT
        extracted_csv = None
        extracted_txt = None
        for name in extracted_names:
            if name.lower().endswith(".csv"):
                extracted_csv = self.output_dir / name
            elif name.lower().endswith(".txt"):
                extracted_txt = self.output_dir / name

        if not extracted_csv or not extracted_csv.exists():
            raise FileNotFoundError(f"Could not locate extracted CSV file among: {extracted_names}")

        # Compute file hashes and inspection data
        csv_hash = compute_sha256(extracted_csv)
        zip_hash = compute_sha256(zip_path)
        data_summary = inspect_raw_csv_metadata(extracted_csv)

        retrieved_at_utc = datetime.now(timezone.utc).isoformat()
        metadata: Dict[str, Any] = {
            "status": "DOWNLOADED",
            "provenance": {
                "source_name": "HistData.com",
                "instrument": "XAU/USD",
                "instrument_type": "Spot Gold vs US Dollar",
                "timeframe": "M1",
                "source_timezone": HISTDATA_TIMEZONE,
                "timezone_description": "European DST interbank feeder server (Europe/London - 5h offset: UTC-5 in winter, UTC-4 in summer)",
                "volume_semantics": "0 / Not aggregated by HistData (Broker-specific volume removed)",
                "landing_url": landing_url,
                "download_endpoint": self.download_endpoint,
                "retrieved_at_utc": retrieved_at_utc,
            },
            "parameters": {
                "symbol": symbol.upper(),
                "year": year,
                "month": month,
                "datemonth": datemonth_str,
                "period_type": "annual" if month is None else "monthly",
            },
            "data_summary": data_summary,
            "files": {
                "raw_zip_name": zip_path.name,
                "raw_zip_sha256": zip_hash,
                "raw_zip_size_bytes": zip_path.stat().st_size,
                "extracted_csv_name": extracted_csv.name,
                "extracted_csv_sha256": csv_hash,
                "extracted_csv_size_bytes": extracted_csv.stat().st_size,
                "status_report_name": extracted_txt.name if extracted_txt and extracted_txt.exists() else None,
            },
        }

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        logger.info("Provenance metadata saved to: %s", meta_path)
        return metadata
