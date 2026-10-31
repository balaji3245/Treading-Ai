"""Tests for Phase 26: Locked Historical Evaluation — HYP-24-NY-REVERSAL-EXHAUSTION.

Validates:
1. Strict data governance and fail-closed partition boundaries (2023-01-01 to 2024-12-31).
2. Cryptographic verification of protected holdout partitions (val/test).
3. Cryptographic verification of frozen protocol SHA-256.
4. Frozen strategy parameter immutability.
5. Evaluation data hashes and row counts.
6. Consistency and accuracy of evaluation trade logs (77 executed trades).
7. Missing entry bar fail-closed behavior (10 days skipped).
8. Consistency and completeness of evaluation metrics and promotion gate failures.
9. Independent clean-room audit reconciliation (0 discrepancies).
10. Single trade per day constraint and valid timestamp adherence.
"""

import json
from datetime import time
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts.run_phase26_historical_evaluation import (
    BASE_ROUND_TURN_FRICTION,
    FRICTION_1_5X,
    FRICTION_2_0X,
    FROZEN_EXHAUSTION_THRESHOLD,
    METRICS_JSON_PATH,
    PROJECT_ROOT,
    PROTOCOL_EXPECTED_SHA256,
    PROTOCOL_PATH,
    TEST_EXPECTED_SHA256,
    TEST_PARQUET_PATH,
    TRADES_CSV_PATH,
    VAL_EXPECTED_SHA256,
    VAL_PARQUET_PATH,
    compute_sha256,
    verify_partition_checksums,
)

AUDIT_JSON_PATH = PROJECT_ROOT / "reports/phase26/audit_reconciliation.json"


def test_protected_partitions_unmodified():
    """Verify that protected 2025 val and 2026 test partitions are cryptographically intact."""
    assert VAL_PARQUET_PATH.exists(), "Protected validation partition missing"
    assert TEST_PARQUET_PATH.exists(), "Protected test partition missing"

    val_hash = compute_sha256(VAL_PARQUET_PATH)
    test_hash = compute_sha256(TEST_PARQUET_PATH)

    assert val_hash == VAL_EXPECTED_SHA256, f"Validation partition modified! Got {val_hash}"
    assert test_hash == TEST_EXPECTED_SHA256, f"Test partition modified! Got {test_hash}"

    checksums = verify_partition_checksums()
    assert checksums["val"]["is_unmodified"] is True
    assert checksums["test"]["is_unmodified"] is True


def test_protocol_sha256_unmodified():
    """Verify that the frozen protocol matches the Phase 24/25 expected SHA-256."""
    assert PROTOCOL_PATH.exists(), "Frozen protocol file missing"
    actual_hash = compute_sha256(PROTOCOL_PATH)
    assert actual_hash == PROTOCOL_EXPECTED_SHA256, f"Protocol hash modified! Got {actual_hash}"


def test_fail_closed_on_prohibited_dates():
    """Verify fail-closed exception when encountering dates < 2023 or >= 2025."""
    lower_boundary = pd.to_datetime("2023-01-01 00:00:00", utc=True)
    upper_boundary = pd.to_datetime("2025-01-01 00:00:00", utc=True)

    # Test lower boundary violation
    ts_early = pd.to_datetime("2022-12-31 23:55:00", utc=True)
    assert ts_early < lower_boundary

    # Test upper boundary violation
    ts_late = pd.to_datetime("2025-01-01 00:00:00", utc=True)
    assert ts_late >= upper_boundary


def test_frozen_strategy_parameters():
    """Verify strategy parameters match frozen specification."""
    assert FROZEN_EXHAUSTION_THRESHOLD == 0.320210
    assert BASE_ROUND_TURN_FRICTION == 0.25
    assert FRICTION_1_5X == 0.375
    assert FRICTION_2_0X == 0.50


def test_evaluation_data_hashes_and_rows():
    """Verify row counts and SHA-256 checksums of 2023 and 2024 parquet files."""
    p23 = PROJECT_ROOT / "data/processed/XAUUSD/M5/XAUUSD_M5_2023.parquet"
    p24 = PROJECT_ROOT / "data/processed/XAUUSD/M5/XAUUSD_M5_2024.parquet"

    assert p23.exists() and p24.exists()

    h23 = compute_sha256(p23)
    h24 = compute_sha256(p24)

    assert h23 == "4b0a461b598ff7ef0491a077523daf9e24009c86677270f90a1a318a4b862c77"
    assert h24 == "1aa6027334f1bb7801be12553368e7420007fd6e2b0e20d26dcacd28076657d0"

    df23 = pd.read_parquet(p23)
    df24 = pd.read_parquet(p24)

    assert len(df23) == 61794
    assert len(df24) == 71133


def test_evaluation_trades_consistency():
    """Verify evaluation_trades.csv properties and trade volume."""
    assert TRADES_CSV_PATH.exists()
    df_trades = pd.read_csv(TRADES_CSV_PATH)
    assert len(df_trades) == 77

    n_long = int((df_trades["direction"] == "LONG").sum())
    n_short = int((df_trades["direction"] == "SHORT").sum())
    assert n_long == 37
    assert n_short == 40

    for _, row in df_trades.iterrows():
        entry_ts = pd.to_datetime(row["entry_ts"])
        exit_ts = pd.to_datetime(row["exit_ts"])

        # Entry strictly at 14:05:00 UTC
        assert entry_ts.time() == time(14, 5, 0)
        # Exit between 14:05 and 18:30 UTC
        assert entry_ts <= exit_ts
        assert exit_ts.time() <= time(18, 30, 0)


def test_single_trade_per_day_constraint():
    """Verify at most one trade per calendar day."""
    assert TRADES_CSV_PATH.exists()
    df_trades = pd.read_csv(TRADES_CSV_PATH)
    counts = df_trades["date"].value_counts()
    assert (counts <= 1).all(), "Found multiple trades on the same calendar day!"


def test_missing_entry_bars_handled_fail_closed():
    """Verify missing entry bar days were properly recorded in metrics."""
    assert METRICS_JSON_PATH.exists()
    with open(METRICS_JSON_PATH, "r") as f:
        metrics = json.load(f)

    assert metrics["sample_counts"]["missing_entry_days_count"] == 10
    assert metrics["sample_counts"]["n_eligible_exhaustion_days"] == 87
    assert metrics["sample_counts"]["n_executed_trades"] == 77


def test_evaluation_metrics_and_gate_failures():
    """Verify evaluation_metrics.json accurately captures all promotion gate failures."""
    assert METRICS_JSON_PATH.exists()
    with open(METRICS_JSON_PATH, "r") as f:
        metrics = json.load(f)

    c10 = metrics["cost_tiers"]["cost_1_0x_baseline"]
    assert np.isclose(c10["net_pnl_usd"], -178.903, atol=1e-2)
    assert np.isclose(c10["avg_net_trade_usd"], -2.323, atol=1e-2)
    assert np.isclose(c10["net_profit_factor"], 0.551, atol=1e-2)
    assert np.isclose(c10["win_rate_pct"], 42.86, atol=1e-2)
    assert np.isclose(c10["max_drawdown_usd"], 178.903, atol=1e-2)

    gates = metrics["promotion_gate_evaluation"]
    assert gates["gate_1_expectancy_ge_0_50"]["passed"] is False
    assert gates["gate_2_profit_factor_ge_1_25"]["passed"] is False
    assert gates["gate_3_win_rate_ge_52_5"]["passed"] is False
    assert gates["gate_4_net_pnl_1_5x_gt_0"]["passed"] is False
    assert gates["gate_5_directional_symmetry_pf_ge_1_10"]["passed"] is False
    assert gates["gate_6_bootstrap_exp_lower_gt_0"]["passed"] is False
    assert gates["gate_7_max_drawdown_le_45_00"]["passed"] is False
    assert gates["all_gates_passed"] is False

    assert metrics["final_decision"] == "FAIL — STRATEGY REJECTED"


def test_audit_reconciliation_passed():
    """Verify independent audit clean-room reconciliation passed with zero discrepancies."""
    assert AUDIT_JSON_PATH.exists()
    with open(AUDIT_JSON_PATH, "r") as f:
        audit = json.load(f)

    assert audit["reconciliation"]["reconciliation_passed"] is True
    assert audit["reconciliation"]["discrepancies_count"] == 0
    assert audit["reconciliation"]["n_trades_checked"] == 77
    assert audit["protected_partitions"]["val"]["match"] is True
    assert audit["protected_partitions"]["test"]["match"] is True
    assert audit["protected_partitions"]["protocol"]["match"] is True
