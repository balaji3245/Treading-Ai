"""
Automated Test Suite for Phase 30: H4 and Daily Dataset Audit, Horizon Statistics & Execution Cost Analysis
Treading-Ai | Quantitative Research & Market Data Audit
"""

import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path("/home/bhoot/project/Treading-Ai")
REPORTS_DIR = REPO_ROOT / "reports" / "phase30"
PROCESSED_H4_DIR = REPO_ROOT / "data" / "processed" / "XAUUSD" / "H4"
PROCESSED_M1_DIR = REPO_ROOT / "data" / "processed" / "XAUUSD" / "M1"

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
    """Verify that protected holdout partitions remain pristine and untouched."""
    assert compute_sha256(FROZEN_VAL_PATH) == EXPECTED_VAL_SHA256, "Protected Val partition modified!"
    assert compute_sha256(FROZEN_TEST_PATH) == EXPECTED_TEST_SHA256, "Protected Test partition modified!"

def test_h4_data_integrity_and_invariants():
    """Verify H4 invariants, row counts, monotonicity, and 180-bar rollover candles."""
    h4_21 = pd.read_parquet(PROCESSED_H4_DIR / "XAUUSD_H4_2021.parquet")
    h4_22 = pd.read_parquet(PROCESSED_H4_DIR / "XAUUSD_H4_2022.parquet")
    combined = pd.concat([h4_21, h4_22], ignore_index=True)

    assert len(combined) == 3086, f"Expected 3086 H4 bars, got {len(combined)}"
    assert combined["timestamp"].is_monotonic_increasing, "H4 timestamps not strictly monotonic!"
    assert combined["timestamp"].duplicated().sum() == 0, "Duplicate H4 timestamps found!"

    # Invariants
    assert (combined["high"] >= np.maximum(combined["open"], combined["close"])).all(), "Invalid High invariant!"
    assert (combined["low"] <= np.minimum(combined["open"], combined["close"])).all(), "Invalid Low invariant!"
    assert ((combined["open"] > 0) & (combined["high"] > 0) & (combined["low"] > 0) & (combined["close"] > 0)).all(), "Non-positive price!"
    assert (combined["volume"] == 0.0).all(), "H4 volume column contains non-zero data!"

    # Rollover 180-bar verification
    bc_180 = (combined["bar_count"] == 180).sum()
    assert bc_180 == 498, f"Expected 498 rollover 180-bar candles, got {bc_180}"

def test_daily_alignment_comparison():
    """Verify that NY Close alignment produces 516 trading days while UTC alignment produces 620 days."""
    m1_21 = pd.read_parquet(PROCESSED_M1_DIR / "XAUUSD_M1_2021.parquet")
    m1_22 = pd.read_parquet(PROCESSED_M1_DIR / "XAUUSD_M1_2022.parquet")
    m1 = pd.concat([m1_21, m1_22], ignore_index=True)
    m1_idx = m1.set_index("timestamp").sort_index()

    # NY Close alignment (22:00 UTC anchor, freq='24h', offset='22h')
    d_ny = m1_idx.resample("24h", offset="22h", closed="left", label="left")["open"].count()
    d_ny_clean = d_ny[d_ny > 0]
    assert len(d_ny_clean) == 516, f"Expected 516 NY-aligned trading days, got {len(d_ny_clean)}"

    # UTC midnight alignment (00:00 UTC anchor, freq='1D')
    d_utc = m1_idx.resample("1D", closed="left", label="left")["open"].count()
    d_utc_clean = d_utc[d_utc > 0]
    assert len(d_utc_clean) == 620, f"Expected 620 UTC calendar days, got {len(d_utc_clean)}"

def test_phase30_reports_delivered():
    """Verify that all 6 required Phase 30 markdown reports exist and have substantive content."""
    expected_reports = [
        "data_integrity_audit.md",
        "horizon_statistics.md",
        "execution_cost_audit.md",
        "dukascopy_ingestion_readiness.md",
        "research_preregistration_checklist.md",
        "phase30_decision.md"
    ]

    for report_name in expected_reports:
        path = REPORTS_DIR / report_name
        assert path.exists(), f"Missing required Phase 30 report: {report_name}"
        assert path.stat().st_size > 1000, f"Report {report_name} is suspiciously small (<1KB)"

def test_phase30_decision_verdict_and_blockers():
    """Verify that phase30_decision.md contains formal verdict and identifies the 3 blockers."""
    decision_file = REPORTS_DIR / "phase30_decision.md"
    content = decision_file.read_text()

    assert "PHASE 30 FORMAL VERDICT: IMPROVE DATA/COST MODEL FIRST" in content
    assert "BLOCKER 1" in content
    assert "BLOCKER 2" in content
    assert "BLOCKER 3" in content
    assert "SUSPENDED" in content

def test_execution_cost_audit_missing_inputs():
    """Verify metrics JSON records that net-PnL backtesting cannot yet be certified."""
    metrics_file = REPORTS_DIR / "phase30_audit_metrics.json"
    assert metrics_file.exists(), "phase30_audit_metrics.json does not exist!"

    with open(metrics_file) as f:
        data = json.load(f)

    cost_audit = data["execution_cost_audit"]
    assert cost_audit["supports_credible_net_pnl_backtest"] is False
    assert len(cost_audit["missing_inputs"]) >= 3
    assert data["formal_verdict"] == "IMPROVE DATA/COST MODEL FIRST"
