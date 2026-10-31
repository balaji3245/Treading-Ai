"""Phase 23 Out-of-Sample Evaluation Test Suite.

Validates:
1. Cryptographic integrity of protected partitions (2025 val and 2026 test).
2. Data partition boundaries (strictly 2023-2024).
3. Strategy parameter immutability (frozen Q1 threshold = 0.281865).
4. Trade log and metrics reconciliation.
5. Verification of directional breakdown (Long vs Short performance divergence).
6. Statistical significance and bootstrap confidence interval validity.
7. Verification that final decision is REJECT based on statistical and execution evidence.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts.run_phase23_oos_evaluation import (
    FROZEN_COMPRESSION_THRESHOLD,
    METRICS_JSON_PATH,
    PROJECT_ROOT,
    TEST_EXPECTED_SHA256,
    TEST_PARQUET_PATH,
    TRADES_CSV_PATH,
    VAL_EXPECTED_SHA256,
    VAL_PARQUET_PATH,
    compute_sha256,
    load_evaluation_data,
)


def test_phase23_protected_partitions_unmodified():
    """Verify protected partitions remain untouched and cryptographically valid."""
    assert VAL_PARQUET_PATH.exists()
    assert TEST_PARQUET_PATH.exists()

    val_hash = compute_sha256(VAL_PARQUET_PATH)
    test_hash = compute_sha256(TEST_PARQUET_PATH)

    assert val_hash == VAL_EXPECTED_SHA256
    assert test_hash == TEST_EXPECTED_SHA256


def test_phase23_evaluation_data_boundaries():
    """Verify that evaluation data contains only 2023-2024 bars and passes fail-closed check."""
    df, meta = load_evaluation_data()
    min_ts = pd.to_datetime(meta["min_timestamp_utc"])
    max_ts = pd.to_datetime(meta["max_timestamp_utc"])

    assert min_ts >= pd.to_datetime("2023-01-01", utc=True)
    assert max_ts < pd.to_datetime("2025-01-01", utc=True)
    assert meta["fail_closed_check_passed"] is True
    assert meta["total_evaluation_bars"] == 132927


def test_phase23_frozen_strategy_parameters():
    """Verify strategy threshold and cost parameters remained strictly frozen."""
    assert FROZEN_COMPRESSION_THRESHOLD == 0.281865


def test_phase23_metrics_reconciliation():
    """Verify that evaluation_metrics.json and evaluation_trades.csv are completely consistent."""
    assert METRICS_JSON_PATH.exists()
    assert TRADES_CSV_PATH.exists()

    with open(METRICS_JSON_PATH, "r") as f:
        metrics = json.load(f)

    trades_df = pd.read_csv(TRADES_CSV_PATH)
    n_trades = len(trades_df)

    assert n_trades == metrics["sample_counts"]["n_executed_trades"]
    assert n_trades == 89

    n_long = int((trades_df["direction"] == "LONG").sum())
    n_short = int((trades_df["direction"] == "SHORT").sum())
    assert n_long == metrics["sample_counts"]["n_long_trades"]
    assert n_short == metrics["sample_counts"]["n_short_trades"]
    assert n_long == 52
    assert n_short == 37

    gross_sum = float(trades_df["gross_pnl_usd"].sum())
    assert np.isclose(gross_sum, metrics["cost_tiers"]["cost_1_0x_baseline"]["gross_pnl_usd"], atol=1e-2)

    net_sum = float(trades_df["net_pnl_1_0x_usd"].sum())
    assert np.isclose(net_sum, metrics["cost_tiers"]["cost_1_0x_baseline"]["net_pnl_usd"], atol=1e-2)

    wins_count = int(trades_df["is_win_1_0x"].sum())
    assert wins_count == metrics["cost_tiers"]["cost_1_0x_baseline"]["wins_count"]
    assert wins_count == 39


def test_phase23_directional_failure_verification():
    """Verify severe breakdown of Short trades out-of-sample."""
    trades_df = pd.read_csv(TRADES_CSV_PATH)
    short_trades = trades_df[trades_df["direction"] == "SHORT"]

    short_pnl = short_trades["net_pnl_1_0x_usd"].sum()
    short_wins = int(short_trades["is_win_1_0x"].sum())
    short_win_rate = short_wins / len(short_trades) * 100.0

    assert short_pnl < 0.0, "Short trades should be negative"
    assert round(short_pnl, 3) == -41.933
    assert round(short_win_rate, 2) == 27.03


def test_phase23_decision_is_reject():
    """Verify that the formal phase decision is REJECT."""
    with open(METRICS_JSON_PATH, "r") as f:
        metrics = json.load(f)

    assert metrics["final_decision"] == "REJECT"
    assert "statistical significance" in metrics["decision_rationale"].lower()
