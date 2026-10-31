"""
Automated Test Suite for Phase 29: Data Acquisition Plan, Provider Evaluation & Cost Architecture
Treading-Ai | Quantitative Research & Infrastructure Audit
"""

import hashlib
from pathlib import Path
import pytest

REPO_ROOT = Path("/home/bhoot/project/Treading-Ai")
REPORTS_DIR = REPO_ROOT / "reports" / "phase29"
PROCESSED_DIR = REPO_ROOT / "data" / "processed" / "XAUUSD"
MACRO_DIR = REPO_ROOT / "data" / "raw" / "macro"

FROZEN_VAL_PATH = REPO_ROOT / "data" / "features" / "XAUUSD_M5_features_val.parquet"
FROZEN_TEST_PATH = REPO_ROOT / "data" / "features" / "XAUUSD_M5_features_test.parquet"
EXPECTED_VAL_SHA256 = "7e9222e9dc0893601e24505912eeab78330670c4e70ebcc2fa462ff8d44a4f94"
EXPECTED_TEST_SHA256 = "f95fd09a5d07666e3f1d9a72e840e2e97f3c058d11b6bb0c712b21dea86a5dec"

def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def test_governance_and_frozen_partitions_intact():
    """Verify that protected holdouts remain pristine and untouched."""
    assert compute_sha256(FROZEN_VAL_PATH) == EXPECTED_VAL_SHA256, "Protected Val partition modified!"
    assert compute_sha256(FROZEN_TEST_PATH) == EXPECTED_TEST_SHA256, "Protected Test partition modified!"

def test_existing_data_and_macro_inventory():
    """Verify that existing higher-timeframe and macro assets are available for Path 1 research."""
    # Check macro files exist and have content
    macro_series = ["DFII10_raw.csv", "DTWEXBGS_raw.csv", "T10YIE_raw.csv", "acquisition_metadata.json"]
    for fname in macro_series:
        fpath = MACRO_DIR / fname
        assert fpath.exists(), f"Macro asset missing: {fname}"
        assert fpath.stat().st_size > 0, f"Macro asset empty: {fname}"

    # Check H1 and H4 processed datasets exist for 2021-2022
    for tf in ["H1", "H4"]:
        for year in [2021, 2022]:
            pfile = PROCESSED_DIR / tf / f"XAUUSD_{tf}_{year}.parquet"
            assert pfile.exists(), f"Processed dataset missing: {pfile}"
            assert pfile.stat().st_size > 1000, f"Processed file suspiciously small: {pfile}"

def test_all_phase29_deliverables_exist():
    """Verify that all 6 required Phase 29 audit reports exist and are thoroughly populated."""
    expected_reports = [
        "data_source_inventory.md",
        "provider_comparison.md",
        "research_horizon_assessment.md",
        "aws_cost_plan.md",
        "licensing_and_risks.md",
        "phase29_decision.md"
    ]
    
    for report_name in expected_reports:
        report_path = REPORTS_DIR / report_name
        assert report_path.exists(), f"Missing required Phase 29 report: {report_name}"
        assert report_path.stat().st_size > 1000, f"Report {report_name} is suspiciously small (<1KB)"

def test_phase29_decision_content_and_rules():
    """Verify that phase29_decision.md enforces dual-track strategy, zero cloud spend, and no strategy creation."""
    decision_content = (REPORTS_DIR / "phase29_decision.md").read_text()
    
    # Assert formal verdict and dual tracks
    assert "PHASE 29 FORMAL VERDICT: APPROVE DUAL-TRACK DATA ARCHITECTURE" in decision_content
    assert "PRIMARY PATH:  PATH 1 — MULTI-DAY SWING RESEARCH ON H4 / DAILY (ZERO COST)" in decision_content
    assert "FALLBACK PATH: PATH 2 — DUKASCOPY HISTORICAL TICK BID/ASK DATA INGESTION (ZERO COST)" in decision_content
    assert "$0.00 CLOUD SPEND AUTHORIZED" in decision_content
    
    # Assert prohibitions
    assert "No Strategy Generation in Phase 29" in decision_content
    assert "No Data Purchases or Subscriptions" in decision_content
    assert "No Cloud Resource Creation" in decision_content

def test_aws_cost_plan_controls():
    """Verify that aws_cost_plan.md specifies guardrails and documents zero current footprint."""
    aws_plan_content = (REPORTS_DIR / "aws_cost_plan.md").read_text()
    
    assert "$0.00 / month" in aws_plan_content
    assert "AWS Budgets & Alarm Thresholds" in aws_plan_content
    assert "Ephemeral Spot Compute" in aws_plan_content
    assert "Local Workstation Priority" in aws_plan_content

def test_licensing_and_risks_document():
    """Verify that licensing_and_risks.md covers CME redistribution and futures roll hazards."""
    licensing_content = (REPORTS_DIR / "licensing_and_risks.md").read_text()
    
    assert "CME Group Information Services Agreement" in licensing_content
    assert "Futures Contract Roll Discontinuities" in licensing_content
    assert "Public Domain" in licensing_content
    assert "STRICTLY PROHIBITED" in licensing_content
