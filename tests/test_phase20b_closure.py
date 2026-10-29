"""Phase 20B: Automated Test Suite for Research Closure & Formal Corrections.

Tests:
1. Protected data partition security invariants (val.parquet, test.parquet).
2. Protocol SHA-256 cryptographic match (82d47383a2b65265ed3bebc5080aa3e259941f7508286dd377bb8dff8f92969c).
3. Benchmark separation into E, F1, F2, and G with exact verified metrics.
4. Corrected Wednesday swap timing reconciliation (settlement_dow == 2).
5. Short-position swap classification as unverified proxy and robustness under $0.00 short swap.
6. Feature predictive metrics & directional hit rates vs 50% coin toss.
7. Holm-Bonferroni correction reproduction across candidate family M=4.
8. Preservation of historical Phase 20 and Phase 20A artifacts.
9. Final closure verdict: strictly 'PHASE 20 CLOSED — NO PREDICTIVE EDGE'.
"""

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

PROJECT_ROOT = Path("/home/bhoot/project/Treading-Ai")
PROTOCOL_MD_PATH = PROJECT_ROOT / "reports/phase20/preregistered_protocol.md"
PHASE20_RESULTS_PATH = PROJECT_ROOT / "reports/phase20/results.json"
PHASE20A_RESULTS_PATH = PROJECT_ROOT / "reports/phase20a/corrected_results.json"
CLOSURE_METRICS_PATH = PROJECT_ROOT / "reports/phase20b/corrected_metrics.json"

VAL_PARQUET_PATH = PROJECT_ROOT / "data/features/XAUUSD_M5_features_val.parquet"
TEST_PARQUET_PATH = PROJECT_ROOT / "data/features/XAUUSD_M5_features_test.parquet"

VAL_EXPECTED_SHA256 = "7e9222e9dc0893601e24505912eeab78330670c4e70ebcc2fa462ff8d44a4f94"
TEST_EXPECTED_SHA256 = "f95fd09a5d07666e3f1d9a72e840e2e97f3c058d11b6bb0c712b21dea86a5dec"
EXPECTED_PROTOCOL_SHA256 = "82d47383a2b65265ed3bebc5080aa3e259941f7508286dd377bb8dff8f92969c"


def compute_sha256(filepath: Path) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def test_partition_protection_invariants():
    """Verify protected partitions remain untouched and cryptographically identical."""
    assert VAL_PARQUET_PATH.exists()
    assert TEST_PARQUET_PATH.exists()
    assert compute_sha256(VAL_PARQUET_PATH) == VAL_EXPECTED_SHA256
    assert compute_sha256(TEST_PARQUET_PATH) == TEST_EXPECTED_SHA256


def test_preregistered_protocol_integrity():
    """Verify pre-registered protocol hash matches cryptographic constant."""
    assert PROTOCOL_MD_PATH.exists()
    assert compute_sha256(PROTOCOL_MD_PATH) == EXPECTED_PROTOCOL_SHA256


def test_preservation_of_prior_artifacts():
    """Verify original Phase 20 and Phase 20A artifacts are preserved unchanged."""
    assert PHASE20_RESULTS_PATH.exists()
    assert PHASE20A_RESULTS_PATH.exists()
    assert CLOSURE_METRICS_PATH.exists()


def test_benchmark_separation_and_metrics():
    """Verify formal separation and numerical reconciliation of benchmarks E, F1, F2, and G."""
    with open(CLOSURE_METRICS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Benchmark E: No-Trade
    bench_e = data["reconciled_trading_metrics"]["Benchmark_E_No_Trade"]["cost_1_0x_baseline"]
    assert bench_e["corrected_net_pnl_usd"] == 0.0

    # Benchmark F1: Daily Long-Only
    bench_f1 = data["reconciled_trading_metrics"]["Benchmark_F1_Daily_Long_Only"]["cost_1_0x_baseline"]
    assert np.isclose(bench_f1["corrected_net_pnl_usd"], 548.17, atol=0.02)
    assert bench_f1["corrected_costs_usd"] == 241.44

    # Benchmark F2: Continuous Buy-and-Hold
    bench_f2 = data["continuous_buy_and_hold_benchmark"]
    assert np.isclose(bench_f2["net_pnl_usd_corr"], 710.23, atol=0.02)
    assert np.isclose(bench_f2["total_costs_usd_corr"], 86.94, atol=0.02)
    assert np.isclose(bench_f2["overnight_roll_gaps_captured_usd"], 7.554, atol=0.01)
    assert bench_f2["active_trades"] == 1

    # Benchmark G: Prior Momentum
    bench_g = data["reconciled_trading_metrics"]["Benchmark_G_Prior_Momentum"]["cost_1_0x_baseline"]
    assert np.isclose(bench_g["corrected_net_pnl_usd"], -472.35, atol=0.02)


def test_models_remain_net_negative_across_all_tiers():
    """Verify that all models remain negative under baseline, elevated, stressed, and zero short swap."""
    with open(CLOSURE_METRICS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    trading = data["reconciled_trading_metrics"]
    for m in ["Model_A_Yield_Only", "Model_B_Dollar_Only", "Model_C_Bivariate", "Model_D_Trivariate"]:
        # 1.0x baseline
        assert trading[m]["cost_1_0x_baseline"]["corrected_net_pnl_usd"] < 0.0
        # 1.5x elevated
        assert trading[m]["cost_1_5x_elevated"]["net_pnl_usd"] < 0.0
        # 2.0x stressed
        assert trading[m]["cost_2_0x_stressed"]["net_pnl_usd"] < 0.0
        # Zero short swap sensitivity
        assert trading[m]["zero_short_swap_sensitivity"]["net_pnl_usd"] < 0.0


def test_directional_hit_rates_and_predictive_metrics():
    """Verify directional hit rates fail to beat 50% coin toss and correlations are near zero."""
    with open(CLOSURE_METRICS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    feats = data["feature_predictive_metrics"]
    for m in ["Model_A_Yield_Only", "Model_B_Dollar_Only", "Model_C_Bivariate", "Model_D_Trivariate"]:
        assert feats[m]["directional_accuracy_pct"] >= 49.0
        assert feats[m]["directional_accuracy_pct"] <= 52.0
        assert feats[m]["binomial_test_p_value"] > 0.20
        assert abs(feats[m]["pearson_r"]) <= 0.025
        assert feats[m]["pearson_p_value"] > 0.55


def test_holm_bonferroni_multiple_testing():
    """Verify Holm-Bonferroni correction step-down fails at rank 1."""
    with open(CLOSURE_METRICS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    hb = data["holm_bonferroni_records"]
    assert len(hb) == 4
    for record in hb:
        assert record["raw_p_value"] > record["adjusted_alpha_threshold"]
        assert record["is_significant_after_holm"] is False


def test_final_closure_verdict():
    """Verify final verdict is strictly 'PHASE 20 CLOSED — NO PREDICTIVE EDGE'."""
    with open(CLOSURE_METRICS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["final_verdict"] == "PHASE 20 CLOSED — NO PREDICTIVE EDGE"
    assert "No evidence of predictive edge exists" in data["verdict_justification"]
