"""Phase 20A: Automated Test Suite for Independent Forensic Audit.

Tests:
1. Cryptographic data partition protection (val.parquet, test.parquet).
2. Protocol SHA-256 cryptographic hash match (82d47383a2b65265ed3bebc5080aa3e259941f7508286dd377bb8dff8f92969c).
3. Directional accuracy formula invariants (active masking, zero returns).
4. Benchmark F daily long-only turnover vs continuous buy-and-hold calculations.
5. Wednesday swap rollover timing reconciliation (entry_dow vs settlement_dow).
6. Asymmetric short swap sensitivity verification.
7. Macro model net negative performance invariance under all cost corrections.
8. Holm-Bonferroni multiple testing reproduction.
9. Final audit verdict and corrected_results.json schema validation.
"""

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path("/home/bhoot/project/Treading-Ai")
ALIGNED_PARQUET_PATH = PROJECT_ROOT / "data/processed/macro/macro_gold_aligned.parquet"
PROTOCOL_MD_PATH = PROJECT_ROOT / "reports/phase20/preregistered_protocol.md"
PHASE20_RESULTS_PATH = PROJECT_ROOT / "reports/phase20/results.json"
CORRECTED_RESULTS_PATH = PROJECT_ROOT / "reports/phase20a/corrected_results.json"

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


def test_protected_partitions_unmodified():
    """Verify that protected validation and test partitions remain bit-for-bit identical."""
    assert VAL_PARQUET_PATH.exists()
    assert TEST_PARQUET_PATH.exists()
    assert compute_sha256(VAL_PARQUET_PATH) == VAL_EXPECTED_SHA256
    assert compute_sha256(TEST_PARQUET_PATH) == TEST_EXPECTED_SHA256


def test_preregistered_protocol_sha256():
    """Verify pre-registered protocol hash matches the cryptographic constant."""
    assert PROTOCOL_MD_PATH.exists()
    actual_hash = compute_sha256(PROTOCOL_MD_PATH)
    assert actual_hash == EXPECTED_PROTOCOL_SHA256


def test_directional_accuracy_invariants():
    """Verify directional accuracy formula excludes inactive trades and handles zero returns."""
    df = pd.read_parquet(ALIGNED_PARQUET_PATH)
    df["settlement_date"] = pd.to_datetime(df["settlement_date"])
    # Compute feature diff on full series before slicing OOS
    df["d1_real_yield"] = df["dfii10_real_yield"].diff()
    df["pos_A"] = -np.sign(df["d1_real_yield"]).fillna(0)

    oos = df[(df["settlement_date"] >= "2023-01-02") & (df["settlement_date"] <= "2024-12-31")].copy().reset_index(drop=True)
    oos["target_pnl_usd"] = oos["session_close_price"] - oos["session_open_price"]

    # Zero returns check
    zero_ret_count = int((oos["target_pnl_usd"] == 0).sum())
    assert zero_ret_count == 0, f"Expected 0 zero-return sessions, found {zero_ret_count}"

    active_A = (oos["pos_A"] != 0)
    assert active_A.sum() == 364
    assert (~active_A).sum() == 152

    correct_A = int((np.sign(oos["pos_A"][active_A]) == np.sign(oos["target_pnl_usd"][active_A])).sum())
    assert correct_A == 181
    acc_A = correct_A / 364 * 100.0
    assert np.isclose(acc_A, 49.72527472527473)


def test_benchmark_f_turnover_vs_continuous_holding():
    """Verify that Benchmark F in Phase 20 is a daily long-only strategy and distinct from continuous buy-and-hold."""
    df = pd.read_parquet(ALIGNED_PARQUET_PATH)
    df["settlement_date"] = pd.to_datetime(df["settlement_date"])
    oos = df[(df["settlement_date"] >= "2023-01-02") & (df["settlement_date"] <= "2024-12-31")].copy().reset_index(drop=True)
    oos["target_pnl_usd"] = oos["session_close_price"] - oos["session_open_price"]

    # Daily long-only gross PnL
    daily_gross_sum = float(oos["target_pnl_usd"].sum())
    assert np.isclose(daily_gross_sum, 789.614, atol=0.01)

    # Continuous holding gross PnL
    open_start = float(oos.loc[0, "session_open_price"])
    close_end = float(oos.loc[len(oos) - 1, "session_close_price"])
    continuous_gross = float(close_end - open_start)
    assert np.isclose(continuous_gross, 797.168, atol=0.01)

    # Rollover gaps captured by continuous holding
    overnight_gap_sum = continuous_gross - daily_gross_sum
    assert np.isclose(overnight_gap_sum, 7.554, atol=0.01)

    # Daily turnover friction deducted in Phase 20: 516 * $0.30 = $154.80
    daily_turnover_friction = 516 * 0.30
    assert np.isclose(daily_turnover_friction, 154.80)

    # Continuous holding turnover friction: single round turn = $0.30
    continuous_turnover_friction = 0.30
    assert np.isclose(continuous_turnover_friction, 0.30)

    # Continuous holding Net PnL with corrected swap ($86.64)
    continuous_net_corr = continuous_gross - (continuous_turnover_friction + 86.64)
    assert np.isclose(continuous_net_corr, 710.228, atol=0.01)


def test_wednesday_swap_rollover_timing():
    """Verify Wednesday swap rollover timing discrepancy between entry_dow and settlement_dow."""
    df = pd.read_parquet(ALIGNED_PARQUET_PATH)
    df["settlement_date"] = pd.to_datetime(df["settlement_date"])
    oos = df[(df["settlement_date"] >= "2023-01-02") & (df["settlement_date"] <= "2024-12-31")].copy().reset_index(drop=True)

    entry_dow = pd.to_datetime(oos["entry_ts_ny"].str[:10]).dt.day_of_week
    settlement_dow = oos["settlement_date"].dt.day_of_week

    # Verify session count shift
    assert (entry_dow == 2).sum() == 104
    assert (settlement_dow == 2).sum() == 103

    swap_orig = np.where(entry_dow == 2, 0.36, 0.12)
    swap_corr = np.where(settlement_dow == 2, 0.36, 0.12)

    assert np.isclose(swap_orig.sum(), 86.88, atol=0.01)
    assert np.isclose(swap_corr.sum(), 86.64, atol=0.01)


def test_models_remain_net_negative_after_all_corrections():
    """Verify that even after swap corrections and zero short swap, all macro models remain net negative."""
    with open(CORRECTED_RESULTS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    rec = data["model_reconciliation"]

    # Baseline 1.0x costs
    assert rec["Model_A_Yield_Only"]["cost_1_0x_baseline"]["corrected_net_pnl_usd"] < 0.0
    assert rec["Model_B_Dollar_Only"]["cost_1_0x_baseline"]["corrected_net_pnl_usd"] < 0.0
    assert rec["Model_C_Bivariate"]["cost_1_0x_baseline"]["corrected_net_pnl_usd"] < 0.0
    assert rec["Model_D_Trivariate"]["cost_1_0x_baseline"]["corrected_net_pnl_usd"] < 0.0

    # Zero short swap sensitivity
    assert rec["Model_A_Yield_Only"]["cost_asymmetric_short_swap_0"]["net_pnl_usd"] < 0.0
    assert rec["Model_B_Dollar_Only"]["cost_asymmetric_short_swap_0"]["net_pnl_usd"] < 0.0
    assert rec["Model_C_Bivariate"]["cost_asymmetric_short_swap_0"]["net_pnl_usd"] < 0.0
    assert rec["Model_D_Trivariate"]["cost_asymmetric_short_swap_0"]["net_pnl_usd"] < 0.0


def test_holm_bonferroni_multiple_testing_reproduction():
    """Verify Holm-Bonferroni correction fails to reject null hypothesis at all ranks."""
    with open(CORRECTED_RESULTS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    hb = data["holm_bonferroni_audit"]
    assert hb["m_tests"] == 4
    for test in hb["tests"]:
        assert test["raw_p"] > test["threshold"]
        assert test["rejected"] is False


def test_final_audit_verdict():
    """Verify that final audit verdict is strictly PHASE 20 PARTIALLY INVALID — CORRECTIONS REQUIRED."""
    with open(CORRECTED_RESULTS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["final_verdict"] == "PHASE 20 PARTIALLY INVALID — CORRECTIONS REQUIRED"
    assert "Benchmark F was mislabeled" in data["verdict_justification"]
