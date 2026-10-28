"""Unit tests for HistDataDownloader using mock fixtures (100% offline)."""

from datetime import datetime, timezone
import io
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import zipfile

import pytest
import requests

from treading_ai.data_collection.downloader import (
    ArchiveCorruptionError,
    HistDataDownloader,
    PeriodUnavailableError,
    compute_sha256,
    inspect_raw_csv_metadata,
)


def test_landing_url_generation():
    downloader = HistDataDownloader(base_url="https://www.histdata.com")

    # Yearly URL
    yearly_url = downloader.get_landing_url(symbol="XAUUSD", year=2024)
    assert yearly_url == "https://www.histdata.com/download-free-forex-historical-data/?/ascii/1-minute-bar-quotes/xauusd/2024"

    # Monthly URL
    monthly_url = downloader.get_landing_url(symbol="XAUUSD", year=2026, month=1)
    assert monthly_url == "https://www.histdata.com/download-free-forex-historical-data/?/ascii/1-minute-bar-quotes/xauusd/2026/1"


def test_extract_download_token_success():
    downloader = HistDataDownloader()

    # Valid HTML snippet
    sample_html = """
    <html>
        <body>
            <form id="file_down" method="POST" action="/get.php">
                <input type="hidden" name="tk" id="tk" value="abcdef1234567890abcdef1234567890" />
                <input type="hidden" name="date" value="2024" />
            </form>
        </body>
    </html>
    """
    token = downloader.extract_download_token(sample_html)
    assert token == "abcdef1234567890abcdef1234567890"


def test_extract_download_token_unavailable_periods():
    downloader = HistDataDownloader()

    # Monthly request on completed year with empty token
    html_empty = '<input type="hidden" name="tk" id="tk" value="" />'
    with pytest.raises(PeriodUnavailableError, match="HistData does not provide monthly download"):
        downloader.extract_download_token(html_empty, year=2024, month=1)

    # Missing form / token entirely
    with pytest.raises(PeriodUnavailableError, match="Could not extract download token"):
        downloader.extract_download_token("<html><body>No token form here</body></html>", year=2026, month=11)


def test_inspect_raw_csv_metadata(tmp_path: Path):
    csv_file = tmp_path / "test.csv"
    # Three lines in EST: 2026-01-01 18:00:00 (EST) to 2026-01-01 18:02:00 (EST)
    csv_file.write_text(
        "20260101 180000;2650.0;2652.0;2649.0;2651.0;0\n"
        "20260101 180100;2651.0;2653.0;2650.5;2652.0;0\n"
        "20260101 180200;2652.0;2654.0;2651.0;2653.5;0\n"
    )

    info = inspect_raw_csv_metadata(csv_file)
    assert info["row_count"] == 3
    # 18:00 EST + 5h = 23:00 UTC
    assert info["start_timestamp_utc"] == "2026-01-01T23:00:00+00:00"
    assert info["end_timestamp_utc"] == "2026-01-01T23:02:00+00:00"


@patch("requests.Session")
def test_mocked_download_monthly_pipeline(mock_session_cls, tmp_path: Path):
    mock_session = MagicMock()
    mock_session_cls.return_value = mock_session

    # 1. Mock landing page response
    mock_landing_resp = MagicMock()
    mock_landing_resp.status_code = 200
    mock_landing_resp.text = '<input type="hidden" name="tk" id="tk" value="mocktoken123" />'
    mock_session.get.return_value = mock_landing_resp

    # 2. Mock zip download response
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        zf.writestr("DAT_ASCII_XAUUSD_M1_202601.csv", "20260101 180000;4300.0;4305.0;4299.0;4302.0;0\n")
        zf.writestr("DAT_ASCII_XAUUSD_M1_202601.txt", "HistData status report: 0 gaps\n")

    mock_post_resp = MagicMock()
    mock_post_resp.status_code = 200
    mock_post_resp.iter_content.return_value = [zip_buffer.getvalue()]
    mock_session.post.return_value = mock_post_resp

    downloader = HistDataDownloader(output_dir=tmp_path)
    downloader.session = mock_session

    metadata = downloader.download_xauusd_m1(year=2026, month=1, force=True)

    assert metadata["status"] == "DOWNLOADED"
    assert metadata["provenance"]["instrument"] == "XAU/USD"
    assert metadata["parameters"]["period_type"] == "monthly"
    assert metadata["data_summary"]["row_count"] == 1
    assert metadata["data_summary"]["start_timestamp_utc"] == "2026-01-01T23:00:00+00:00"

    extracted_csv = tmp_path / metadata["files"]["extracted_csv_name"]
    assert extracted_csv.exists()
    assert extracted_csv.read_text().startswith("20260101 180000")


@patch("requests.Session")
def test_mocked_download_annual_archive(mock_session_cls, tmp_path: Path):
    mock_session = MagicMock()
    mock_session_cls.return_value = mock_session

    mock_landing = MagicMock()
    mock_landing.text = '<input type="hidden" name="tk" id="tk" value="annualtoken456" />'
    mock_session.get.return_value = mock_landing

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        zf.writestr("DAT_ASCII_XAUUSD_M1_2024.csv", "20240101 180000;2060.0;2065.0;2058.0;2062.0;0\n")

    mock_post = MagicMock()
    mock_post.iter_content.return_value = [zip_buffer.getvalue()]
    mock_session.post.return_value = mock_post

    downloader = HistDataDownloader(output_dir=tmp_path)
    downloader.session = mock_session

    metadata = downloader.download_xauusd_m1(year=2024, month=None, force=True)
    assert metadata["status"] == "DOWNLOADED"
    assert metadata["parameters"]["period_type"] == "annual"
    assert metadata["parameters"]["month"] is None
    assert metadata["files"]["extracted_csv_name"] == "DAT_ASCII_XAUUSD_M1_2024.csv"


@patch("requests.Session")
def test_cache_hit_and_corruption_detection(mock_session_cls, tmp_path: Path):
    mock_session = MagicMock()
    mock_session_cls.return_value = mock_session

    downloader = HistDataDownloader(output_dir=tmp_path)
    downloader.session = mock_session

    csv_path = tmp_path / "DAT_ASCII_XAUUSD_M1_202603.csv"
    csv_path.write_text("20260301 180000;4500.0;4505.0;4495.0;4500.0;0\n")
    actual_hash = compute_sha256(csv_path)

    meta_path = tmp_path / "HISTDATA_COM_ASCII_XAUUSD_M1202603_metadata.json"
    meta_content = {
        "status": "DOWNLOADED",
        "parameters": {"year": 2026, "month": 3},
        "data_summary": {"row_count": 1, "start_timestamp_utc": "2026-03-01T23:00:00+00:00", "end_timestamp_utc": "2026-03-01T23:00:00+00:00"},
        "files": {
            "extracted_csv_name": csv_path.name,
            "extracted_csv_sha256": actual_hash,
            "raw_zip_name": "HISTDATA_COM_ASCII_XAUUSD_M1202603.zip",
        },
    }
    meta_path.write_text(json.dumps(meta_content))

    # 1. Valid file with matching hash -> CACHED hit without HTTP calls
    res = downloader.download_xauusd_m1(year=2026, month=3, force=False)
    assert res["status"] == "CACHED"
    assert mock_session.get.call_count == 0

    # 2. Corrupted file (hash mismatch) -> triggers re-download
    csv_path.write_text("tampered content")
    mock_landing = MagicMock()
    mock_landing.text = '<input type="hidden" name="tk" id="tk" value="tok123" />'
    mock_session.get.return_value = mock_landing

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        zf.writestr("DAT_ASCII_XAUUSD_M1_202603.csv", "restored content\n")
    mock_post = MagicMock()
    mock_post.iter_content.return_value = [zip_buf.getvalue()]
    mock_session.post.return_value = mock_post

    res2 = downloader.download_xauusd_m1(year=2026, month=3, force=False)
    assert mock_session.get.call_count == 1
    assert res2["status"] == "DOWNLOADED"


@patch("requests.Session")
def test_retries_on_http_error(mock_session_cls, tmp_path: Path):
    mock_session = MagicMock()
    mock_session_cls.return_value = mock_session

    # Attempt 1 fails with 500 Server Error; Attempt 2 succeeds
    mock_fail = MagicMock()
    mock_fail.raise_for_status.side_effect = requests.HTTPError("500 Internal Server Error")

    mock_ok = MagicMock()
    mock_ok.status_code = 200
    mock_ok.text = '<input type="hidden" name="tk" id="tk" value="retrytok" />'

    mock_session.get.side_effect = [requests.HTTPError("500 Error"), mock_ok]

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        zf.writestr("DAT_ASCII_XAUUSD_M1_202604.csv", "20260401 180000;4600.0;4605.0;4595.0;4600.0;0\n")
    mock_post = MagicMock()
    mock_post.iter_content.return_value = [zip_buf.getvalue()]
    mock_session.post.return_value = mock_post

    downloader = HistDataDownloader(output_dir=tmp_path, max_retries=2, backoff_factor=0.01)
    downloader.session = mock_session

    res = downloader.download_xauusd_m1(year=2026, month=4, force=True)
    assert res["status"] == "DOWNLOADED"
    assert mock_session.get.call_count == 2


@patch("requests.Session")
def test_corrupted_zip_detection(mock_session_cls, tmp_path: Path):
    mock_session = MagicMock()
    mock_session_cls.return_value = mock_session

    mock_landing = MagicMock()
    mock_landing.text = '<input type="hidden" name="tk" id="tk" value="corrupttok" />'
    mock_session.get.return_value = mock_landing

    # Corrupted non-zip payload
    mock_post = MagicMock()
    mock_post.iter_content.return_value = [b"NOT A VALID ZIP FILE HEADER"]
    mock_session.post.return_value = mock_post

    downloader = HistDataDownloader(output_dir=tmp_path, max_retries=1, backoff_factor=0.01)
    downloader.session = mock_session

    with pytest.raises(RuntimeError, match="Failed to download data archive"):
        downloader.download_xauusd_m1(year=2026, month=5, force=True)
