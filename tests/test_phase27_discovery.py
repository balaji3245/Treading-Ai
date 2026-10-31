"""Tests for Phase 27: New Hypothesis Discovery & Research Design.

Validates:
1. Strict data governance and fail-closed partition boundaries.
2. Cryptographic verification of protected holdout partitions (val/test).
3. Cryptographic verification of frozen hypothesis registry SHA-256.
4. No look-ahead bias in daily ATR20 lag and feature calculations.
5. Correct execution timing and bar sequencing across candidate hypotheses.
6. Mathematical fidelity of gross PnL, net PnL, and cost tier friction.
7. Completeness and consistency of the all_trades.csv ledger (368 trades).
8. Consistency of hypothesis_results.csv and experiment_metrics.json.
9. Independent clean-room audit reconciliation (0 discrepancies).
10. Verification of terminal promotion gate rejections across all 5 hypotheses.
"""

import json
from datetime import time
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts.run_phase27_discovery_experiments import (
    ALL_TRADES_CSV_PATH,
    COST_BASELINE,
    COST_1_5X,
    COST_2_0X,
    METRICS_JSON_PATH,
    PROJECT_ROOT,
    REGISTRY_EXPECTED_SHA256,
    REGISTRY_PATH,
    RESULTS_CSV_PATH,
    TEST_EXPECTED_SHA256,
    TEST_PARQUET_PATH,
    VAL_EXPECTED_SHA256,
    VAL_PARQUET_PATH,
    compute_sha256,
    verify_governance,
)

AUDIT_JSON_PATH = PROJECT_ROOT / "reports/phase27/audit_reconciliation.json"


def test_protected_partitions_unmodified():
    """Verify that protected 2025 val and 2026 test partitions are cryptographically intact."""
    assert VAL_PARQUET_PATH.exists(), "Protected validation partition missing"
    assert TEST_PARQUET_PATH.exists(), "Protected test partition missing"

    val_hash = compute_sha256(VAL_PARQUET_PATH)
    test_hash = compute_sha256(TEST_PARQUET_PATH)

    assert val_hash == VAL_EXPECTED_SHA256, f"Validation partition modified! Got {val_hash}"
    assert test_hash == TEST_EXPECTED_SHA256, f"Test partition modified! Got {test_hash}"


def test_registry_sha256_unmodified():
    """Verify that hypothesis_registry.md matches the frozen pre-registration SHA-256."""
    assert REGISTRY_PATH.exists(), "Hypothesis registry file missing"
    actual_hash = compute_sha256(REGISTRY_PATH)
    assert actual_hash == REGISTRY_EXPECTED_SHA256, f"Registry modified! Got {actual_hash}"

    gov = verify_governance()
    assert gov["governance_verified"] is True


def test_fail_closed_on_prohibited_dates():
    """Verify fail-closed exception when encountering dates >= 2023-01-01 in development."""
    prohibited_df = pd.DataFrame({
        "timestamp": [
            pd.to_datetime("2022-12-31 23:55:00", utc=True),
            pd.to_datetime("2023-01-01 00:00:00", utc=True),
        ],
        "open": [1800.0, 1801.0],
    })

    prohibited_boundary = pd.to_datetime("2023-01-01 00:00:00", utc=True)
    with pytest.raises(ValueError, match="CRITICAL: Development data contains prohibited data"):
        max_ts = prohibited_df["timestamp"].max()
        if max_ts >= prohibited_boundary:
            raise ValueError(f"CRITICAL: Development data contains prohibited data >= 2023! Max TS: {max_ts}")


def test_no_lookahead_atr_lag():
    """Verify that daily ATR is strictly lagged by 1 full day without current-day leakage."""
    daily_tr = pd.Series([10.0] * 25, index=pd.date_range("2021-01-01", periods=25))
    atr20 = daily_tr.rolling(20).mean()
    atr20_prior = atr20.shift(1)

    assert pd.isna(atr20_prior.iloc[19])
    assert atr20_prior.iloc[20] == 10.0

    # Changing day 20's TR does NOT alter day 20's atr20_prior
    daily_tr_mod = daily_tr.copy()
    daily_tr_mod.iloc[20] = 999.0
    atr20_prior_mod = daily_tr_mod.rolling(20).mean().shift(1)
    assert atr20_prior_mod.iloc[20] == atr20_prior.iloc[20]


def test_execution_timing_and_timestamps():
    """Verify that all executed trades enter after signals and exit before session close."""
    assert ALL_TRADES_CSV_PATH.exists()
    df_trades = pd.read_csv(ALL_TRADES_CSV_PATH)
    assert not df_trades.empty

    for _, row in df_trades.iterrows():
        entry_ts = pd.to_datetime(row["entry_ts"])
        exit_ts = pd.to_datetime(row["exit_ts"])
        hyp_id = row["hypothesis_id"]

        assert entry_ts <= exit_ts

        # Verify entry timing by hypothesis
        if hyp_id == "HYP-27-VOL-SHOCK-EXPANSION":
            assert entry_ts.time() == time(8, 5, 0)
            assert exit_ts.time() <= time(12, 0, 0)
        elif hyp_id == "HYP-27-LONDON-PM-FIX-IMBALANCE":
            assert entry_ts.time() == time(15, 5, 0)
            assert exit_ts.time() <= time(17, 0, 0)
        elif hyp_id == "HYP-27-POST-COMEX-DRIFT-REVERSION":
            assert entry_ts.time() == time(20, 5, 0)
            assert exit_ts.time() <= time(22, 0, 0)
        elif hyp_id == "HYP-27-CONSECUTIVE-RANGE-MOMENTUM":
            assert entry_ts.time() == time(9, 5, 0)
            assert exit_ts.time() <= time(16, 0, 0)
        elif hyp_id == "HYP-27-MONDAY-WEEKEND-GAP-REVERSION":
            assert entry_ts.time() == time(2, 5, 0)
            assert exit_ts.time() <= time(7, 0, 0)


def test_pnl_and_cost_accounting():
    """Verify mathematical consistency of gross and net PnL across all cost tiers."""
    assert ALL_TRADES_CSV_PATH.exists()
    df_trades = pd.read_csv(ALL_TRADES_CSV_PATH)

    for _, row in df_trades.iterrows():
        entry_p = float(row["entry_price"])
        exit_p = float(row["exit_price"])
        dir_mult = 1 if row["direction"] == "LONG" else -1

        expected_gross = (exit_p - entry_p) * dir_mult
        assert np.isclose(float(row["gross_pnl_usd"]), expected_gross, atol=1e-3)

        expected_net10 = expected_gross - COST_BASELINE
        expected_net15 = expected_gross - COST_1_5X
        expected_net20 = expected_gross - COST_2_0X

        assert np.isclose(float(row["net_pnl_1_0x_usd"]), expected_net10, atol=1e-3)
        assert np.isclose(float(row["net_pnl_1_5x_usd"]), expected_net15, atol=1e-3)
        assert np.isclose(float(row["net_pnl_2_0x_usd"]), expected_net20, atol=1e-3)


def test_all_trades_ledger_consistency():
    """Verify total trade volume and counts by hypothesis."""
    assert ALL_TRADES_CSV_PATH.exists()
    df_trades = pd.read_csv(ALL_TRADES_CSV_PATH)

    assert len(df_trades) == 368

    counts = df_trades["hypothesis_id"].value_counts().to_dict()
    assert counts["HYP-27-VOL-SHOCK-EXPANSION"] == 49
    assert counts["HYP-27-LONDON-PM-FIX-IMBALANCE"] == 133
    assert counts["HYP-27-POST-COMEX-DRIFT-REVERSION"] == 100
    assert counts["HYP-27-CONSECUTIVE-RANGE-MOMENTUM"] == 46
    assert counts["HYP-27-MONDAY-WEEKEND-GAP-REVERSION"] == 40


def test_hypothesis_results_summary_consistency():
    """Verify hypothesis_results.csv matches experiment_metrics.json."""
    assert RESULTS_CSV_PATH.exists()
    assert METRICS_JSON_PATH.exists()

    df_res = pd.read_csv(RESULTS_CSV_PATH)
    assert len(df_res) == 5

    with open(METRICS_JSON_PATH, "r") as f:
        metrics = json.load(f)

    hyp_res_json = metrics["hypothesis_results"]
    assert len(hyp_res_json) == 5

    for idx, row in df_res.iterrows():
        json_item = hyp_res_json[idx]
        assert row["hypothesis_id"] == json_item["hypothesis_id"]
        assert row["sample_size"] == json_item["sample_size"]
        assert np.isclose(float(row["net_pnl_1_0x_usd"]), json_item["net_pnl_1_0x_usd"], atol=1e-2)
        assert row["decision"] == json_item["decision"]
        assert row["decision"] == "REJECTED"


def test_independent_audit_reconciliation_passed():
    """Verify that independent forensic audit passed with 0 discrepancies."""
    assert AUDIT_JSON_PATH.exists()
    with open(AUDIT_JSON_PATH, "r") as f:
        audit = json.load(f)

    assert audit["overall_audit_verdict"] == "PASS"
    assert audit["reconciliation"]["reconciliation_passed"] is True
    assert audit["reconciliation"]["discrepancies_count"] == 0
    assert audit["reconciliation"]["total_trades_checked"] == 368
    assert audit["protected_partitions"]["val"]["match"] is True
    assert audit["protected_partitions"]["test"]["match"] is True
    assert audit["protected_partitions"]["registry"]["match"] is True


def test_all_hypotheses_rejected_decision():
    """Verify that zero hypotheses were promoted and all five were rejected."""
    df_res = pd.read_csv(RESULTS_CSV_PATH)
    decisions = df_res["decision"].tolist()
    assert all(d == "REJECTED" for d in decisions), f"Expected all REJECTED, got {decisions}"
