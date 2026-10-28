"""Unit tests for HistoricalDataOrchestrator."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from treading_ai.data_collection.downloader import PeriodUnavailableError
from treading_ai.data_collection.orchestrator import HistoricalDataOrchestrator


def test_orchestrator_sync_coverage(tmp_path: Path):
    mock_downloader = MagicMock()

    # Period 1 (2026, 1): SUCCESS
    mock_downloader.download_xauusd_m1.side_effect = [
        {
            "status": "DOWNLOADED",
            "files": {
                "extracted_csv_name": "DAT_ASCII_XAUUSD_M1_202601.csv",
                "extracted_csv_sha256": "hash111",
                "extracted_csv_size_bytes": 1000000,
            },
            "data_summary": {
                "row_count": 28827,
                "start_timestamp_utc": "2026-01-01T23:00:00+00:00",
                "end_timestamp_utc": "2026-01-30T21:58:00+00:00",
            },
        },
        # Period 2 (2026, 11): UNAVAILABLE
        PeriodUnavailableError("Month 11 is not yet published"),
        # Period 3 (2026, 12): FAILED
        RuntimeError("Connection reset by peer"),
    ]

    reports_dir = tmp_path / "reports"
    orchestrator = HistoricalDataOrchestrator(
        downloader=mock_downloader,
        raw_dir=tmp_path / "raw",
        reports_dir=reports_dir,
    )

    periods = [(2026, 1), (2026, 11), (2026, 12)]
    report = orchestrator.sync_coverage(periods=periods, symbol="XAUUSD")

    assert report.total_requested == 3
    assert report.total_available == 1
    assert report.total_unavailable == 1
    assert report.total_failed == 1
    assert report.total_m1_rows == 28827
    assert report.overall_start_utc == "2026-01-01T23:00:00+00:00"
    assert report.overall_end_utc == "2026-01-30T21:58:00+00:00"

    # Verify report files were created
    json_path = reports_dir / "coverage_report_XAUUSD.json"
    md_path = reports_dir / "coverage_report_XAUUSD.md"
    assert json_path.exists()
    assert md_path.exists()

    with open(json_path) as f:
        data = json.load(f)
    assert data["total_m1_rows"] == 28827
    assert len(data["periods"]) == 3
