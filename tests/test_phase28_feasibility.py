"""
Automated Test Suite for Phase 28: Research Feasibility, Data Adequacy & Governance Audit
Treading-Ai | Quantitative Research & Independent Financial ML Audit
"""

import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from scipy import stats

REPO_ROOT = Path("/home/bhoot/project/Treading-Ai")
REPORTS_DIR = REPO_ROOT / "reports" / "phase28"
DATA_DIR = REPO_ROOT / "data" / "processed" / "XAUUSD" / "M5"

FROZEN_VAL_PATH = REPO_ROOT / "data" / "features" / "XAUUSD_M5_features_val.parquet"
FROZEN_TEST_PATH = REPO_ROOT / "data" / "features" / "XAUUSD_M5_features_test.parquet"
EXPECTED_VAL_SHA256 = "7e9222e9dc0893601e24505912eeab78330670c4e70ebcc2fa462ff8d44a4f94"
EXPECTED_TEST_SHA256 = "f95fd09a5d07666e3f1d9a72e840e2e97f3c058d11b6bb0c712b21dea86a5dec"
EXPECTED_P27_REGISTRY_SHA256 = "e51dfffc1e42e7f8312adaeba71d31aaf4532100942d7fbc3c01ac4c6b044337"

def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def test_governance_and_frozen_partitions_intact():
    """Verify that protected holdouts and previous phase registries remain pristine."""
    assert compute_sha256(FROZEN_VAL_PATH) == EXPECTED_VAL_SHA256, "Protected Val partition modified!"
    assert compute_sha256(FROZEN_TEST_PATH) == EXPECTED_TEST_SHA256, "Protected Test partition modified!"
    
    p27_registry = REPO_ROOT / "reports" / "phase27" / "hypothesis_registry.md"
    assert compute_sha256(p27_registry) == EXPECTED_P27_REGISTRY_SHA256, "Phase 27 registry altered!"

def test_data_adequacy_verified_schema_and_volume():
    """Verify that development data contains no Ask quotes, no volume, and valid OHLC invariants."""
    df21 = pd.read_parquet(DATA_DIR / "XAUUSD_M5_2021.parquet")
    df22 = pd.read_parquet(DATA_DIR / "XAUUSD_M5_2022.parquet")
    combined = pd.concat([df21, df22], ignore_index=True)
    
    assert len(combined) == 141614, f"Unexpected row count: {len(combined)}"
    
    # Assert missing fields
    missing_fields = ["ask", "bid", "spread", "order_book", "real_volume", "tick_volume"]
    for field in missing_fields:
        assert field not in combined.columns, f"Forbidden field '{field}' unexpectedly found!"
        
    # Assert 100% volume is zero
    assert (combined["volume"] == 0.0).all(), "Volume column unexpectedly contains non-zero data!"
    
    # Assert OHLC invariants
    assert (combined["high"] >= np.maximum(combined["open"], combined["close"])).all(), "Invalid High invariant!"
    assert (combined["low"] <= np.minimum(combined["open"], combined["close"])).all(), "Invalid Low invariant!"

def test_statistical_power_mathematics_and_sample_sizes():
    """Verify statistical power equations and demonstrate severe underpowering of Phase 27."""
    delta = 0.50  # Target economic edge
    alpha = 0.05
    z_alpha_half = stats.norm.ppf(1 - alpha / 2)  # 1.95996
    z_power_80 = stats.norm.ppf(0.80)            # 0.84162
    
    # Test case 1: HYP-27-VOL-SHOCK-EXPANSION (sigma = 6.462, N = 49)
    sigma_1 = 6.462
    n_1 = 49
    se_1 = sigma_1 / np.sqrt(n_1)
    z_1 = delta / se_1
    power_1 = 1 - stats.norm.cdf(z_alpha_half - z_1) + stats.norm.cdf(-z_alpha_half - z_1)
    
    assert power_1 < 0.10, f"Expected statistical power < 10%, got {power_1*100:.2f}%"
    
    # Required N for 80% power
    n_req_1 = ((z_alpha_half + z_power_80) * sigma_1 / delta) ** 2
    assert n_req_1 > 1000, f"Expected n_req > 1000 trades, got {n_req_1}"
    
    # Minimum Detectable Effect at N=49
    mde_1 = (z_alpha_half + z_power_80) * sigma_1 / np.sqrt(n_1)
    assert mde_1 > 2.0, f"Expected MDE > $2.00/oz, got {mde_1}"

def test_phase28_metrics_file_integrity_and_reconciliation():
    """Verify metrics JSON file exists, is internally consistent, and Phase 27 reconciliation passes."""
    metrics_file = REPORTS_DIR / "phase28_audit_metrics.json"
    assert metrics_file.exists(), "phase28_audit_metrics.json does not exist!"
    
    with open(metrics_file) as f:
        data = json.load(f)
        
    assert data["final_decision"] == "IMPROVE DATA FIRST"
    assert data["governance_audit"]["val_intact"] is True
    assert data["governance_audit"]["test_intact"] is True
    assert data["governance_audit"]["p27_registry_intact"] is True
    
    # Assert zero reconciliation errors across Phase 27 hypotheses
    recon = data["governance_audit"]["reconciliation"]
    for hyp_id, result in recon.items():
        assert result["sample_size_match"] is True, f"{hyp_id} sample size mismatch!"
        assert result["net_pnl_match"] is True, f"{hyp_id} net PnL mismatch!"
        assert result["avg_exp_match"] is True, f"{hyp_id} average expectancy mismatch!"

def test_predictive_information_and_friction_dominance():
    """Verify that OOS predictive models do not survive friction and exhibit negative R2 beyond 5m."""
    metrics_file = REPORTS_DIR / "phase28_audit_metrics.json"
    with open(metrics_file) as f:
        data = json.load(f)
        
    models = data["predictive_information_audit"]["model_evaluations"]
    
    # 1. 1-bar horizon
    assert models["fwd_ret_1"]["oos_2022_r2_vs_zero_baseline"] < 0.001
    assert models["fwd_ret_1"]["net_expectancy_at_0_25_cost_usd"] < 0, "1-bar should not survive friction!"
    
    # 2. Multi-bar horizons must have non-positive OOS R2 vs zero benchmark
    assert models["fwd_ret_3"]["oos_2022_r2_vs_zero_baseline"] <= 0.0, "3-bar OOS R2 should be <= 0"
    assert models["fwd_ret_12"]["oos_2022_r2_vs_zero_baseline"] <= 0.0, "12-bar OOS R2 should be <= 0"
    
    # 3. None survive friction
    for target, res in models.items():
        assert res["survives_friction"] is False, f"{target} unexpectedly survived friction!"

def test_all_phase28_reports_delivered():
    """Verify that all 7 required Phase 28 audit markdown reports exist and have non-zero content."""
    expected_reports = [
        "research_feasibility.md",
        "execution_cost_audit.md",
        "data_adequacy_report.md",
        "statistical_power_analysis.md",
        "predictive_information_audit.md",
        "governance_and_reproducibility.md",
        "phase28_decision.md"
    ]
    
    for report in expected_reports:
        path = REPORTS_DIR / report
        assert path.exists(), f"Missing required Phase 28 report: {report}"
        assert path.stat().st_size > 1000, f"Report {report} is suspiciously small (<1KB)"

def test_phase28_decision_formal_verdict():
    """Verify that phase28_decision.md explicitly contains the approved verdict."""
    decision_file = REPORTS_DIR / "phase28_decision.md"
    content = decision_file.read_text()
    
    assert "IMPROVE DATA FIRST" in content, "Formal verdict 'IMPROVE DATA FIRST' missing from decision record!"
    assert "CONTINUE RESEARCH" not in content or "PHASE 28 FORMAL VERDICT: IMPROVE DATA FIRST" in content
    assert "STRICTLY PROHIBITED" in content, "Prohibition warnings missing!"
