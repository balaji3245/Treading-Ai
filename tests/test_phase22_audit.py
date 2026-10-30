"""Phase 22 Independent Audit Test Suite.

Validates:
1. Independent reconstruction of trade log with 0 discrepancies against Phase 22 development_trades.csv.
2. Verification of Empirical Q1 quantile calculation matching frozen threshold 0.281865.
3. Verification that all 101 trades are strictly intraday (zero rollover swap financing).
4. Verification that drawdown calculation conforms to documented cumulative equity peak-to-trough.
5. Verification of cost tier monotonicity.
6. Verification of statistical significance calculations (binomial test p = 0.2131).
7. Protected partition inviolability.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from scripts.run_phase22_independent_audit import (
    AUDIT_OUTPUT_JSON,
    FROZEN_Q1_THRESHOLD,
    PHASE22_METRICS_JSON,
    PHASE22_TRADES_CSV,
    TEST_EXPECTED_SHA256,
    TEST_PARQUET_PATH,
    VAL_EXPECTED_SHA256,
    VAL_PARQUET_PATH,
    compute_sha256,
    independent_reconstruction,
    load_raw_data,
    reconcile_trades,
)


def test_audit_protected_partitions_intact():
    """Verify protected partitions remain untouched and cryptographically valid."""
    assert VAL_PARQUET_PATH.exists()
    assert TEST_PARQUET_PATH.exists()

    val_hash = compute_sha256(VAL_PARQUET_PATH)
    test_hash = compute_sha256(TEST_PARQUET_PATH)

    assert val_hash == VAL_EXPECTED_SHA256
    assert test_hash == TEST_EXPECTED_SHA256


def test_independent_trade_reconstruction_zero_discrepancies():
    """Verify independent trade reconstruction produces identical trades to Phase 22."""
    df = load_raw_data()
    recon_trades, daily_df, info = independent_reconstruction(df)

    assert len(recon_trades) == 101
    assert info["n_evaluated_days"] == 495
    assert info["n_compressed_days"] == 124

    recon_res = reconcile_trades(recon_trades, PHASE22_TRADES_CSV)
    assert recon_res["reconciliation_passed"] is True
    assert recon_res["discrepancies_count"] == 0
    assert len(recon_res["discrepancies"]) == 0


def test_empirical_q1_matches_frozen_threshold():
    """Verify that linear quantile 0.25 of development compression ratio equals 0.281865."""
    df = load_raw_data()
    _, daily_df, info = independent_reconstruction(df)

    q1_calc = float(daily_df["compression_ratio"].quantile(0.25, interpolation="linear"))
    assert round(q1_calc, 6) == FROZEN_Q1_THRESHOLD


def test_zero_overnight_swap_holding():
    """Verify every executed trade opens after 07:00 UTC and exits by 12:00 UTC."""
    assert PHASE22_TRADES_CSV.exists()
    trades_df = pd.read_csv(PHASE22_TRADES_CSV)

    trades_df["entry_time"] = pd.to_datetime(trades_df["entry_ts"]).dt.time
    trades_df["exit_time"] = pd.to_datetime(trades_df["exit_ts"]).dt.time

    earliest_entry = min(trades_df["entry_time"])
    latest_exit = max(trades_df["exit_time"])

    # Earliest possible entry is 07:05:00 UTC
    assert earliest_entry >= pd.to_datetime("07:05:00").time()
    # Latest possible exit is 12:00:00 UTC
    assert latest_exit <= pd.to_datetime("12:00:00").time()


def test_drawdown_calculation_convention():
    """Verify maximum drawdown equals peak-to-trough on cumulative net PnL series."""
    trades_df = pd.read_csv(PHASE22_TRADES_CSV)
    net_pnl = trades_df["net_pnl_1_0x_usd"].to_numpy()

    cum_pnl = np.cumsum(net_pnl)
    peak = np.maximum.accumulate(cum_pnl)
    drawdowns = peak - cum_pnl
    max_dd = float(np.max(drawdowns))

    assert round(max_dd, 3) == 30.659


def test_cost_tier_monotonicity():
    """Verify net PnL decreases monotonically as transaction friction increases."""
    trades_df = pd.read_csv(PHASE22_TRADES_CSV)

    net_10 = trades_df["net_pnl_1_0x_usd"].sum()
    net_15 = trades_df["net_pnl_1_5x_usd"].sum()
    net_20 = trades_df["net_pnl_2_0x_usd"].sum()

    assert net_10 > net_15 > net_20
    assert round(net_10, 3) == 42.438
    assert round(net_15, 3) == 29.813
    assert round(net_20, 3) == 17.188


def test_binomial_test_reproducibility():
    """Verify binomial test of 55 wins out of 101 trades yields p = 0.2131."""
    trades_df = pd.read_csv(PHASE22_TRADES_CSV)
    n_wins = int(trades_df["is_win_1_0x"].sum())
    n_trades = len(trades_df)

    assert n_wins == 55
    assert n_trades == 101

    res = stats.binomtest(n_wins, n_trades, 0.5, alternative="greater")
    assert round(res.pvalue, 4) == 0.2131
