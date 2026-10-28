"""Historical data orchestrator for bulk downloading and coverage reporting.

Orchestrates multi-year historical ingestion, verifies local cache integrity,
tracks available vs unavailable periods, and produces audit-ready coverage reports.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from treading_ai.config import (
    HISTDATA_DEFAULT_SYMBOL,
    RAW_DATA_DIR,
    REPORTS_DIR,
)
from treading_ai.data_collection.downloader import (
    ArchiveCorruptionError,
    HistDataDownloader,
    PeriodUnavailableError,
)

logger = logging.getLogger(__name__)


@dataclass
class PeriodCoverageRecord:
    period_id: str
    year: int
    month: Optional[int]
    period_type: str  # "annual" or "monthly"
    status: str       # "DOWNLOADED", "CACHED", "UNAVAILABLE", "FAILED"
    row_count: int = 0
    start_timestamp_utc: Optional[str] = None
    end_timestamp_utc: Optional[str] = None
    csv_file_name: Optional[str] = None
    csv_sha256: Optional[str] = None
    csv_size_bytes: int = 0
    error_message: Optional[str] = None


@dataclass
class CoverageReport:
    generated_at_utc: str
    symbol: str
    total_requested: int
    total_available: int
    total_unavailable: int
    total_failed: int
    total_m1_rows: int
    overall_start_utc: Optional[str] = None
    overall_end_utc: Optional[str] = None
    periods: List[PeriodCoverageRecord] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self, output_path: Optional[Path] = None) -> str:
        data = self.to_dict()
        json_str = json.dumps(data, indent=2)
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(json_str)
        return json_str

    def to_markdown(self) -> str:
        md = [
            f"# Historical Data Coverage Report: {self.symbol}",
            "",
            f"**Generated**: {self.generated_at_utc}",
            f"- **Periods Requested**: {self.total_requested}",
            f"- **Periods Available / Ingested**: {self.total_available}",
            f"- **Periods Unavailable / Future**: {self.total_unavailable}",
            f"- **Periods Failed**: {self.total_failed}",
            f"- **Total M1 Candles**: {self.total_m1_rows:,}",
            f"- **Verified Date Range**: {self.overall_start_utc} to {self.overall_end_utc}",
            "",
            "## Historical Ingestion Matrix",
            "| Period | Type | Status | Rows | Start (UTC) | End (UTC) | Size (MB) | Details |",
            "| :--- | :---: | :---: | :---: | :--- | :--- | :---: | :--- |",
        ]

        for p in self.periods:
            size_mb = f"{p.csv_size_bytes / (1024 * 1024):.2f}" if p.csv_size_bytes > 0 else "-"
            rows_str = f"{p.row_count:,}" if p.row_count > 0 else "-"
            start_str = p.start_timestamp_utc or "-"
            end_str = p.end_timestamp_utc or "-"
            details = p.error_message or f"SHA: {p.csv_sha256[:10]}..." if p.csv_sha256 else "Verified"
            md.append(
                f"| **{p.period_id}** | {p.period_type} | `{p.status}` | {rows_str} | {start_str} | {end_str} | {size_mb} | {details} |"
            )

        md.append("")
        return "\n".join(md)


class HistoricalDataOrchestrator:
    """Orchestrates historical dataset ingestion, validation, and coverage reporting."""

    def __init__(
        self,
        downloader: Optional[HistDataDownloader] = None,
        raw_dir: Path = RAW_DATA_DIR,
        reports_dir: Path = REPORTS_DIR,
    ):
        self.raw_dir = Path(raw_dir)
        self.reports_dir = Path(reports_dir)
        self.downloader = downloader or HistDataDownloader(output_dir=self.raw_dir)

    def sync_period(
        self,
        year: int,
        month: Optional[int] = None,
        symbol: str = HISTDATA_DEFAULT_SYMBOL,
        force: bool = False,
    ) -> PeriodCoverageRecord:
        """Download or verify a single historical period."""
        period_id = f"{year}_{month:02d}" if month is not None else str(year)
        period_type = "monthly" if month is not None else "annual"

        try:
            meta = self.downloader.download_xauusd_m1(
                year=year,
                month=month,
                symbol=symbol,
                force=force,
            )
            files = meta.get("files", {})
            summary = meta.get("data_summary", {})
            return PeriodCoverageRecord(
                period_id=period_id,
                year=year,
                month=month,
                period_type=period_type,
                status=meta.get("status", "SUCCESS"),
                row_count=summary.get("row_count", 0),
                start_timestamp_utc=summary.get("start_timestamp_utc"),
                end_timestamp_utc=summary.get("end_timestamp_utc"),
                csv_file_name=files.get("extracted_csv_name"),
                csv_sha256=files.get("extracted_csv_sha256"),
                csv_size_bytes=files.get("extracted_csv_size_bytes", 0),
            )
        except PeriodUnavailableError as e:
            logger.info("Period %s is unavailable on source: %s", period_id, e)
            return PeriodCoverageRecord(
                period_id=period_id,
                year=year,
                month=month,
                period_type=period_type,
                status="UNAVAILABLE",
                error_message=str(e),
            )
        except Exception as e:
            logger.error("Failed to download period %s: %s", period_id, e)
            return PeriodCoverageRecord(
                period_id=period_id,
                year=year,
                month=month,
                period_type=period_type,
                status="FAILED",
                error_message=str(e),
            )

    def sync_coverage(
        self,
        periods: List[Tuple[int, Optional[int]]],
        symbol: str = HISTDATA_DEFAULT_SYMBOL,
        force: bool = False,
    ) -> CoverageReport:
        """Synchronize multiple historical periods and compile a complete coverage report."""
        records: List[PeriodCoverageRecord] = []
        total_rows = 0
        overall_starts: List[str] = []
        overall_ends: List[str] = []

        total_avail = 0
        total_unavail = 0
        total_fail = 0

        for year, month in periods:
            rec = self.sync_period(year=year, month=month, symbol=symbol, force=force)
            records.append(rec)
            if rec.status in ("DOWNLOADED", "CACHED", "SUCCESS"):
                total_avail += 1
                total_rows += rec.row_count
                if rec.start_timestamp_utc:
                    overall_starts.append(rec.start_timestamp_utc)
                if rec.end_timestamp_utc:
                    overall_ends.append(rec.end_timestamp_utc)
            elif rec.status == "UNAVAILABLE":
                total_unavail += 1
            else:
                total_fail += 1

        overall_start = min(overall_starts) if overall_starts else None
        overall_end = max(overall_ends) if overall_ends else None

        report = CoverageReport(
            generated_at_utc=datetime.now(timezone.utc).isoformat(),
            symbol=symbol,
            total_requested=len(periods),
            total_available=total_avail,
            total_unavailable=total_unavail,
            total_failed=total_fail,
            total_m1_rows=total_rows,
            overall_start_utc=overall_start,
            overall_end_utc=overall_end,
            periods=records,
        )

        # Write reports
        json_path = self.reports_dir / f"coverage_report_{symbol}.json"
        md_path = self.reports_dir / f"coverage_report_{symbol}.md"
        report.to_json(json_path)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(report.to_markdown())

        logger.info("Coverage report saved to: %s and %s", json_path, md_path)
        return report
