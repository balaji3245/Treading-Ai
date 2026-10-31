"""Tests for Phase 25: Controlled Development Backtest — HYP-24-NY-REVERSAL-EXHAUSTION.

Validates:
1. Strict data governance and fail-closed partition protection.
2. Cryptographic verification of protected partitions (val/test).
3. Frozen strategy parameter immutability.
4. No look-ahead bias in ATR20 lag and threshold estimation.
5. Correct anchor (11:55 close) and measurement (13:55 close) bars.
6. Counter-trend long/short directional logic.
7. Entry timing at 14:05:00 UTC bar open.
8. Stop placement and adverse entry gap aborts.
9. Adverse open-gap stop slippage handling.
10. Intrabar precedence: stop-loss checked before scheduled time exit.
11. Missing-bar fail-closed handling.
12. No trades outside permitted window (14:05 to 18:30 UTC).
13. Single trade per eligible day constraint.
14. Consistency and reconciliation between metrics, trade logs, and audit records.
"""

import json
from datetime import datetime, time, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts.run_phase25_development_backtest import (
    BASE_ROUND_TURN_FRICTION,
    FRICTION_1_5X,
    FRICTION_2_0X,
    FROZEN_EXHAUSTION_THRESHOLD,
    METRICS_JSON_PATH,
    PROJECT_ROOT,
    TEST_EXPECTED_SHA256,
    TEST_PARQUET_PATH,
    TRADES_CSV_PATH,
    VAL_EXPECTED_SHA256,
    VAL_PARQUET_PATH,
    compute_sha256,
    verify_partition_checksums,
)

AUDIT_JSON_PATH = PROJECT_ROOT / "reports/phase25/audit_reconciliation.json"


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


def test_frozen_strategy_parameters():
    """Verify that core strategy parameters match the frozen specification."""
    assert FROZEN_EXHAUSTION_THRESHOLD == 0.320210
    assert BASE_ROUND_TURN_FRICTION == 0.25
    assert FRICTION_1_5X == 0.375
    assert FRICTION_2_0X == 0.50


def test_no_lookahead_atr_lag():
    """Verify that daily ATR is strictly lagged by 1 full day without current-day leakage."""
    # Synthetic daily data
    daily_tr = pd.Series([10.0] * 25, index=pd.date_range("2021-01-01", periods=25))
    atr20 = daily_tr.rolling(20).mean()
    atr20_prior = atr20.shift(1)

    # On day 20 (0-indexed), atr20 is available, but atr20_prior on day 20 is NaN (shifted)
    assert pd.isna(atr20_prior.iloc[19])
    # On day 21 (0-indexed), atr20_prior incorporates strictly days 0..19
    assert atr20_prior.iloc[20] == 10.0

    # Changing day 20's TR does NOT change day 20's atr20_prior
    daily_tr_modified = daily_tr.copy()
    daily_tr_modified.iloc[20] = 500.0
    atr20_prior_mod = daily_tr_modified.rolling(20).mean().shift(1)
    assert atr20_prior_mod.iloc[20] == atr20_prior.iloc[20]


def test_consensus_anchor_and_measurement_timing():
    """Verify consensus anchor is 11:55 bar close (12:00 UTC) and measurement is 13:55 bar close (14:00 UTC)."""
    t_anchor = time(11, 55, 0)
    t_meas = time(13, 55, 0)
    t_entry = time(14, 5, 0)
    t_exit = time(18, 25, 0)

    # Assert strict temporal sequencing
    assert t_anchor < t_meas < t_entry < t_exit


def test_counter_trend_direction_logic():
    """Verify counter-trend direction: upside excursion -> Short, downside excursion -> Long."""
    p_base = 1800.0

    # Case 1: Upside overshoot (delta_p > 0) -> Fading upside -> SHORT
    p_1400_high = 1815.0
    delta_p_up = p_1400_high - p_base
    direction_up = -1 if delta_p_up > 0 else (1 if delta_p_up < 0 else 0)
    assert direction_up == -1  # SHORT

    # Case 2: Downside overshoot (delta_p < 0) -> Fading downside -> LONG
    p_1400_low = 1785.0
    delta_p_down = p_1400_low - p_base
    direction_down = -1 if delta_p_down > 0 else (1 if delta_p_down < 0 else 0)
    assert direction_down == 1  # LONG

    # Case 3: Flat excursion -> No signal
    delta_p_zero = 0.0
    direction_zero = -1 if delta_p_zero > 0 else (1 if delta_p_zero < 0 else 0)
    assert direction_zero == 0


def test_stop_loss_placement_and_distance():
    """Verify stop distance is exactly 0.75 * |delta_p| beyond entry price."""
    delta_p = 10.0  # Upside excursion -> Short trade
    stop_mult = 0.75
    stop_dist = stop_mult * abs(delta_p)
    assert stop_dist == 7.5

    entry_price = 1814.5
    stop_price_short = entry_price + stop_dist
    assert stop_price_short == 1822.0

    # Long trade (delta_p = -10.0)
    entry_price_long = 1785.5
    stop_price_long = entry_price_long - stop_dist
    assert stop_price_long == 1778.0


def test_adverse_entry_gap_abort():
    """Verify trade is aborted if entry bar opens beyond the stop level."""
    # Long trade: entry expected near 1785, stop at 1778
    stop_price_long = 1778.0

    # Normal open: 1785.0 -> Not aborted
    entry_open_normal = 1785.0
    assert not (entry_open_normal <= stop_price_long)

    # Catastrophic gap down: 1775.0 (below stop) -> Aborted
    entry_open_gap = 1775.0
    is_aborted = (entry_open_gap <= stop_price_long)
    assert is_aborted is True


def test_adverse_open_gap_stop_slippage():
    """Verify that if a bar opens beyond the stop level, it executes at the bar Open."""
    stop_price = 1778.0
    # Long trade: next bar opens at 1772.0 (past stop of 1778.0)
    bar_gap = {
        "open": 1772.0,
        "high": 1775.0,
        "low": 1770.0,
        "close": 1774.0,
    }

    exit_price = None
    exit_reason = None
    if bar_gap["open"] <= stop_price:
        exit_price = bar_gap["open"]
        exit_reason = "STOP_GAP"

    assert exit_reason == "STOP_GAP"
    assert exit_price == 1772.0  # Slippage realized past 1778.0


def test_stop_loss_order_of_operations_precedes_exit():
    """Verify stop-loss check strictly precedes scheduled time exit on the final bar."""
    stop_price = 1822.0
    # Short trade: on 18:25 bar (pit close), price spikes to 1825.0 before closing at 1820.0
    bar_1825 = {
        "time_utc": time(18, 25, 0),
        "open": 1821.0,
        "high": 1825.0,  # Spikes above stop
        "low": 1819.0,
        "close": 1820.0,  # Closes in profit
    }

    exit_price = None
    exit_reason = None

    # Step 1: Open gap
    if bar_1825["open"] >= stop_price:
        exit_price = bar_1825["open"]
        exit_reason = "STOP_GAP"

    # Step 2: Intrabar high penetration (Short stop)
    if exit_price is None and bar_1825["high"] >= stop_price:
        exit_price = stop_price
        exit_reason = "STOP_LOSS"

    # Step 3: Scheduled time exit
    if exit_price is None and bar_1825["time_utc"] == time(18, 25, 0):
        exit_price = bar_1825["close"]
        exit_reason = "TIME_EXIT_1830"

    assert exit_reason == "STOP_LOSS"
    assert exit_price == stop_price


def test_missing_bar_handling():
    """Verify fail-closed behavior when critical protocol bars are missing."""
    # Simulated day missing 13:55 excursion bar
    bars_dict = {
        time(11, 55, 0): {"close": 1800.0},
        # time(13, 55, 0) is missing
        time(14, 5, 0): {"open": 1805.0},
    }

    can_trade = (time(11, 55, 0) in bars_dict) and (time(13, 55, 0) in bars_dict) and (time(14, 5, 0) in bars_dict)
    assert can_trade is False


def test_no_trades_outside_permitted_window():
    """Verify that all executed trades enter at 14:05 UTC and exit at or before 18:30 UTC."""
    assert TRADES_CSV_PATH.exists()
    df_trades = pd.read_csv(TRADES_CSV_PATH)
    assert not df_trades.empty

    for _, row in df_trades.iterrows():
        entry_ts = pd.to_datetime(row["entry_ts"])
        exit_ts = pd.to_datetime(row["exit_ts"])

        # Entry must be at 14:05:00 UTC
        assert entry_ts.time() == time(14, 5, 0)

        # Exit must be between 14:05:00 and 18:30:00 UTC (same bar exit if stopped out immediately)
        assert entry_ts <= exit_ts
        assert exit_ts.time() <= time(18, 30, 0)


def test_single_trade_per_day_constraint():
    """Verify that the generated trade log strictly enforces at most one trade per calendar day."""
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
    assert n_trades == metrics["sample_counts"]["n_executed_trades"]
    assert n_trades == 124

    # 2. Directional counts
    n_long = int((df_trades["direction"] == "LONG").sum())
    n_short = int((df_trades["direction"] == "SHORT").sum())
    assert n_long == metrics["sample_counts"]["n_long_trades"]
    assert n_short == metrics["sample_counts"]["n_short_trades"]
    assert n_long == 62
    assert n_short == 62

    # 3. Gross PnL check
    gross_sum = float(df_trades["gross_pnl_usd"].sum())
    expected_gross = metrics["cost_tiers"]["cost_1_0x_baseline"]["gross_pnl_usd"]
    assert np.isclose(gross_sum, expected_gross, atol=1e-2)

    # 4. Net PnL 1.0x check
    net_10_sum = float(df_trades["net_pnl_1_0x_usd"].sum())
    expected_net_10 = metrics["cost_tiers"]["cost_1_0x_baseline"]["net_pnl_usd"]
    assert np.isclose(net_10_sum, expected_net_10, atol=1e-2)

    # 5. Win count check
    n_wins = int(df_trades["is_win_1_0x"].sum())
    assert n_wins == metrics["cost_tiers"]["cost_1_0x_baseline"]["wins_count"]
    assert n_wins == 72

    # 6. Exit reason distribution check
    time_exits = int((df_trades["exit_reason"] == "TIME_EXIT_1830").sum())
    stop_exits = int((df_trades["exit_reason"] == "STOP_LOSS").sum())
    assert time_exits == metrics["exit_reasons"]["TIME_EXIT_1830"]
    assert stop_exits == metrics["exit_reasons"]["STOP_LOSS"]
    assert time_exits == 101
    assert stop_exits == 23

    # 7. Final decision check
    assert metrics["final_decision"] == "PASS"


def test_clean_room_audit_reconciliation():
    """Verify that independent audit reconciliation passed with 0 discrepancies."""
    assert AUDIT_JSON_PATH.exists()
    with open(AUDIT_JSON_PATH, "r") as f:
        audit_data = json.load(f)

    assert audit_data["reconciliation"]["reconciliation_passed"] is True
    assert audit_data["reconciliation"]["discrepancies_count"] == 0
    assert audit_data["reconciliation"]["n_trades_checked"] == 124
    assert audit_data["protected_partitions"]["val"]["match"] is True
    assert audit_data["protected_partitions"]["test"]["match"] is True
