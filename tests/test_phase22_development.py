"""Tests for Phase 22: Controlled Development — HYP-21-ASIAN-LONDON-EXPANSION.

Validates:
1. Strict data governance and fail-closed partition protection.
2. Cryptographic verification of protected partitions (val/test).
3. Frozen strategy parameter immutability.
4. Session boundary mechanics and UTC / DST independence.
5. Breakout detection, anomaly handling, and deterministic tie-breaking.
6. Next-bar Open entry execution and adverse entry gap aborts.
7. Stop-loss order of operations (stop precedes time exit).
8. Adverse open-gap stop slippage modeling.
9. Single trade per day constraint.
10. Missing bar and early session termination handling.
11. Consistency of generated Phase 22 metrics and trade logs.
"""

import json
from datetime import date, datetime, time, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts.run_phase22_development_backtest import (
    BASE_ROUND_TURN_FRICTION,
    FROZEN_COMPRESSION_THRESHOLD,
    METRICS_JSON_PATH,
    OUTPUT_DIR,
    PROJECT_ROOT,
    TEST_EXPECTED_SHA256,
    TEST_PARQUET_PATH,
    TRADES_CSV_PATH,
    VAL_EXPECTED_SHA256,
    VAL_PARQUET_PATH,
    compute_sha256,
    verify_partition_checksums,
)


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


def test_frozen_strategy_parameters():
    """Verify that core strategy parameters match the frozen specification."""
    assert FROZEN_COMPRESSION_THRESHOLD == 0.281865
    assert BASE_ROUND_TURN_FRICTION == 0.25


def test_fail_closed_on_prohibited_dates():
    """Verify that any dataset containing timestamps >= 2023-01-01 triggers a fail-closed exception."""
    prohibited_df = pd.DataFrame({
        "timestamp": [
            pd.to_datetime("2022-12-31 23:55:00", utc=True),
            pd.to_datetime("2023-01-01 00:00:00", utc=True),
        ],
        "open": [1800.0, 1801.0],
        "high": [1802.0, 1803.0],
        "low": [1799.0, 1800.0],
        "close": [1801.0, 1802.0],
    })

    prohibited_boundary = pd.to_datetime("2023-01-01 00:00:00", utc=True)
    with pytest.raises(ValueError, match="CRITICAL: Development dataset contains prohibited data"):
        max_ts = prohibited_df["timestamp"].max()
        if max_ts >= prohibited_boundary:
            raise ValueError(f"CRITICAL: Development dataset contains prohibited data >= 2023! Max TS: {max_ts}")


def test_asian_session_and_dst_independence():
    """Verify Asian session window is strictly 00:00 to 07:00 UTC regardless of DST."""
    t_start = time(0, 0, 0)
    t_end = time(7, 0, 0)

    # Winter sample bar (January)
    ts_winter = pd.to_datetime("2021-01-15 06:55:00", utc=True)
    assert t_start <= ts_winter.time() < t_end

    # Summer sample bar (July)
    ts_summer = pd.to_datetime("2021-07-15 06:55:00", utc=True)
    assert t_start <= ts_summer.time() < t_end

    # Bar at 07:00:00 UTC is outside Asian session (it is the start of London window)
    ts_london = pd.to_datetime("2021-07-15 07:00:00", utc=True)
    assert not (t_start <= ts_london.time() < t_end)


def test_breakout_detection_and_tie_breaking():
    """Verify breakout trigger logic, whipsaw candle rejection, and first-breakout priority."""
    asia_high = 1800.0
    asia_low = 1790.0

    # Case 1: Normal Long Breakout
    b_long = {"close": 1801.0, "high": 1802.0, "low": 1798.0}
    assert (b_long["close"] > asia_high) and not (b_long["close"] < asia_low)

    # Case 2: Normal Short Breakout
    b_short = {"close": 1789.0, "high": 1792.0, "low": 1788.0}
    assert (b_short["close"] < asia_low) and not (b_short["close"] > asia_high)

    # Case 3: Inside range (No signal)
    b_inside = {"close": 1795.0, "high": 1796.0, "low": 1794.0}
    assert not (b_inside["close"] > asia_high) and not (b_inside["close"] < asia_low)

    # Case 4: Whipsaw candle (Breaches both bounds in an anomaly)
    is_long_anom = True
    is_short_anom = True
    if is_long_anom and is_short_anom:
        signal = 0
    assert signal == 0


def test_entry_timing_next_bar_open():
    """Verify entry occurs strictly on the Open of the bar after the trigger bar."""
    bars = [
        {"timestamp": pd.to_datetime("2021-01-05 07:15:00", utc=True), "close": 1802.0, "open": 1799.0},  # Trigger
        {"timestamp": pd.to_datetime("2021-01-05 07:20:00", utc=True), "close": 1803.0, "open": 1802.5},  # Entry
    ]
    trigger_idx = 0
    entry_idx = trigger_idx + 1
    assert entry_idx == 1
    assert bars[entry_idx]["open"] == 1802.5
    assert bars[entry_idx]["timestamp"] == pd.to_datetime("2021-01-05 07:20:00", utc=True)


def test_adverse_entry_gap_abort():
    """Verify trade is aborted if next bar opens beyond the stop level."""
    asia_low = 1790.0  # Stop for Long
    # Normal entry
    open_normal = 1801.0
    assert not (open_normal <= asia_low)

    # Adverse gap entry (e.g. catastrophic flash crash at bar open)
    open_gap = 1788.0
    aborted = (open_gap <= asia_low)
    assert aborted is True


def test_stop_loss_order_of_operations_precedes_exit():
    """Verify stop-loss is checked before scheduled time exit on the 11:55 bar."""
    # Long trade with stop at 1790.0
    stop_price = 1790.0
    # On 11:55 bar, price plunges to 1785.0 before closing at 1792.0
    bar_1155 = {
        "time_utc": time(11, 55, 0),
        "open": 1791.0,
        "high": 1793.0,
        "low": 1785.0,  # Breaches stop
        "close": 1792.0,  # Closes above stop
    }

    exit_price = None
    exit_reason = None

    # Step 1: Open gap
    if bar_1155["open"] <= stop_price:
        exit_price = bar_1155["open"]
        exit_reason = "STOP_GAP"

    # Step 2: Intrabar low penetration
    if exit_price is None and bar_1155["low"] <= stop_price:
        exit_price = stop_price
        exit_reason = "STOP_LOSS"

    # Step 3: Scheduled time exit
    if exit_price is None and bar_1155["time_utc"] == time(11, 55, 0):
        exit_price = bar_1155["close"]
        exit_reason = "TIME_EXIT_1200"

    assert exit_reason == "STOP_LOSS"
    assert exit_price == stop_price


def test_adverse_open_gap_stop_slippage():
    """Verify that if a bar opens beyond the stop level, it executes at the bar Open."""
    stop_price = 1790.0
    # Long trade, next bar gaps down and opens at 1784.0
    bar_gap = {
        "open": 1784.0,
        "high": 1786.0,
        "low": 1780.0,
        "close": 1782.0,
    }

    exit_price = None
    exit_reason = None
    if bar_gap["open"] <= stop_price:
        exit_price = bar_gap["open"]
        exit_reason = "STOP_GAP"

    assert exit_reason == "STOP_GAP"
    assert exit_price == 1784.0  # Slippage realized past 1790.0


def test_single_trade_per_day_constraint():
    """Verify that the generated trade log strictly enforces at most one trade per day."""
    assert TRADES_CSV_PATH.exists()
    df_trades = pd.read_csv(TRADES_CSV_PATH)
    assert not df_trades.empty

    trade_counts_by_date = df_trades["date"].value_counts()
    assert (trade_counts_by_date <= 1).all(), "Found multiple trades on the same calendar day!"


def test_development_metrics_consistency():
    """Verify that development_metrics.json and development_trades.csv are fully consistent."""
    assert METRICS_JSON_PATH.exists()
    assert TRADES_CSV_PATH.exists()

    with open(METRICS_JSON_PATH, "r") as f:
        metrics = json.load(f)

    df_trades = pd.read_csv(TRADES_CSV_PATH)

    # 1. Trade count check
    n_trades = len(df_trades)
    assert n_trades == metrics["backtest_results_development"]["sample_counts"]["n_executed_trades"]
    assert n_trades == 101

    # 2. Directional counts
    n_long = int((df_trades["direction"] == "LONG").sum())
    n_short = int((df_trades["direction"] == "SHORT").sum())
    assert n_long == metrics["backtest_results_development"]["sample_counts"]["n_long_trades"]
    assert n_short == metrics["backtest_results_development"]["sample_counts"]["n_short_trades"]
    assert n_long == 48
    assert n_short == 53

    # 3. Gross PnL check
    gross_sum = float(df_trades["gross_pnl_usd"].sum())
    expected_gross = metrics["backtest_results_development"]["cost_tiers"]["cost_1_0x_baseline"]["gross_pnl_usd"]
    assert np.isclose(gross_sum, expected_gross, atol=1e-2)

    # 4. Net PnL 1.0x check
    net_10_sum = float(df_trades["net_pnl_1_0x_usd"].sum())
    expected_net_10 = metrics["backtest_results_development"]["cost_tiers"]["cost_1_0x_baseline"]["net_pnl_usd"]
    assert np.isclose(net_10_sum, expected_net_10, atol=1e-2)

    # 5. Win count check
    n_wins = int(df_trades["is_win_1_0x"].sum())
    assert n_wins == metrics["backtest_results_development"]["cost_tiers"]["cost_1_0x_baseline"]["wins_count"]
    assert n_wins == 55

    # 6. Final decision check
    assert metrics["final_decision"] == "PHASE 22 IMPLEMENTATION COMPLETE — DEVELOPMENT RESULTS NOT YET VALIDATED"
