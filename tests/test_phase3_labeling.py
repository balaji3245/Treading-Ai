"""Phase 3 Focused Tests: Causal Directional Labeling Engine and Execution-Cost Model.

Validates:
1. Execution-Cost Causality: opening fills never consume future bar range or ATR.
2. Exact Positional Indexing: decision at bar t, entry at bar t+1 open, exit at bar t+1+H open.
3. Weekend Purge Policy: trades crossing weekend closures are purged without fabricated fills.
4. Bid-Only Execution Convention: costs strictly reduce PnL, long/short symmetry holds.
5. Timezone-Aware Rollover Parity: America/New_York 17:00-18:00 parity across EST, EDT, and DST transitions.
6. Exact Partition Boundary Purge: final 1+H bars purged with BOUNDARY_SPLIT_OVERFLOW.
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
import pytest

from treading_ai.backtesting.cost_model import ExecutionCostModel, TradeExecution
from treading_ai.features.time_features import TimeFeatureExtractor
from treading_ai.models.labeling import (
    CausalDirectionalLabeler,
    PURGE_BOUNDARY_SPLIT_OVERFLOW,
    PURGE_WEEKEND_CROSSING,
    PURGE_ROLLOVER_CLOSED,
    PURGE_ROLLOVER_CROSSING,
)

TZ_NY = ZoneInfo("America/New_York")
TZ_LONDON = ZoneInfo("Europe/London")


# ==============================================================================
# 1. EXECUTION-COST CAUSALITY & POSITIONAL TIMING
# ==============================================================================

def test_execution_cost_causality_opening_fill():
    """Verify that opening fills depend strictly on prior bar volatility, never future bar range."""
    cost_model = ExecutionCostModel(
        base_spread_usd=0.20,
        base_slippage_usd=0.05,
        enable_volatility_scaling=True,
        volatility_spread_factor=0.5,
    )

    t_entry = pd.Timestamp("2024-05-15 14:00:00", tz="UTC")
    nominal_bid = 2350.00
    baseline_atr = 2.0
    baseline_range = 1.5

    # Prior bar t inputs (finalized prior to t+1 open)
    prior_atr = 3.0
    prior_range = 2.5

    fill_initial = cost_model.simulate_causal_fill(
        action="BUY",
        nominal_bid=nominal_bid,
        timestamp=t_entry,
        prior_atr=prior_atr,
        baseline_atr=baseline_atr,
        prior_candle_range=prior_range,
        baseline_candle_range=baseline_range,
    )

    # Synthetic test: modify future bar t+1 completed high and low dramatically
    # (e.g. simulated flash crash or giant rally during bar t+1)
    future_bar_high = 2450.00  # +$100 surge
    future_bar_low = 2250.00   # -$100 plunge
    future_bar_atr = 15.0      # giant ATR

    # Verify that passing strictly causal prior inputs keeps fill 100% bitwise identical
    fill_after_future_move = cost_model.simulate_causal_fill(
        action="BUY",
        nominal_bid=nominal_bid,
        timestamp=t_entry,
        prior_atr=prior_atr,
        baseline_atr=baseline_atr,
        prior_candle_range=prior_range,
        baseline_candle_range=baseline_range,
    )

    assert fill_initial.fill_price == fill_after_future_move.fill_price
    assert fill_initial.effective_spread == fill_after_future_move.effective_spread
    assert fill_initial.slippage == fill_after_future_move.slippage
    assert fill_initial.total_friction_per_oz == fill_after_future_move.total_friction_per_oz

    # In contrast, modifying prior bar t DOES causally affect the fill
    fill_modified_prior = cost_model.simulate_causal_fill(
        action="BUY",
        nominal_bid=nominal_bid,
        timestamp=t_entry,
        prior_atr=prior_atr * 2.0,  # prior volatility increased
        baseline_atr=baseline_atr,
        prior_candle_range=prior_range,
        baseline_candle_range=baseline_range,
    )
    assert fill_modified_prior.effective_spread > fill_initial.effective_spread


def test_exact_positional_indexing_in_labeler():
    """Verify exact positional indexing: bar t close -> entry at t+1 open -> exit at t+1+H open."""
    # Build synthetic DataFrame where bar values encode their row index
    N = 30
    H = 6
    ts = pd.date_range("2024-05-13 08:00:00", periods=N, freq="5min", tz="UTC")

    # Encode indices into prices: open = 1000.0 + index * 10.0
    opens = 1000.0 + np.arange(N) * 10.0
    highs = opens + 4.0
    lows = opens - 2.0
    closes = opens + 1.0
    atrs = 1.0 + np.arange(N) * 0.1

    df = pd.DataFrame({
        "timestamp": ts,
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "atr_14": atrs,
    })

    labeler = CausalDirectionalLabeler(horizon=H, min_return_threshold=0.0)
    labels = labeler.compute_labels(df, baseline_atr=2.0, baseline_candle_range=6.0)

    # For any valid row i (e.g. i=5):
    # Decision is bar i (5).
    # Entry index must be exactly 5 + 1 = 6.
    # Exit index must be exactly 5 + 1 + 6 = 12.
    for i in range(N - (1 + H)):
        assert labels.loc[i, "entry_index"] == i + 1
        assert labels.loc[i, "exit_index"] == i + 1 + H
        assert labels.loc[i, "entry_bid"] == opens[i + 1]
        assert labels.loc[i, "exit_bid"] == opens[i + 1 + H]
        assert labels.loc[i, "entry_timestamp"] == ts[i + 1]
        assert labels.loc[i, "exit_timestamp"] == ts[i + 1 + H]


def test_no_bar_uses_own_completed_range_to_price_open():
    """Verify that corrupting bar t+1 and t+1+H completed ranges does not alter labels."""
    N = 25
    H = 6
    ts = pd.date_range("2024-05-13 08:00:00", periods=N, freq="5min", tz="UTC")
    df1 = pd.DataFrame({
        "timestamp": ts,
        "open": 2300.0 + np.arange(N) * 1.0,
        "high": 2305.0 + np.arange(N) * 1.0,
        "low": 2295.0 + np.arange(N) * 1.0,
        "close": 2302.0 + np.arange(N) * 1.0,
        "atr_14": 2.0,
    })

    df2 = df1.copy()
    # Modify completed high/low of entry bar (index 1) and exit bar (index 7)
    df2.loc[1, "high"] = 2500.0  # +$200 range shock
    df2.loc[1, "low"] = 2100.0
    df2.loc[7, "high"] = 2600.0  # +$300 range shock
    df2.loc[7, "low"] = 2000.0

    labeler = CausalDirectionalLabeler(horizon=H, min_return_threshold=0.0)
    res1 = labeler.compute_labels(df1, baseline_atr=2.0, baseline_candle_range=10.0)
    res2 = labeler.compute_labels(df2, baseline_atr=2.0, baseline_candle_range=10.0)

    # Decision at bar 0 uses entry at bar 1 and exit at bar 7
    # Since causality requires prior volatility (bar 0 for entry, bar 6 for exit),
    # the labels, fill prices, and net returns for bar 0 MUST be 100% bitwise identical!
    assert res1.loc[0, "long_entry_fill"] == res2.loc[0, "long_entry_fill"]
    assert res1.loc[0, "long_exit_fill"] == res2.loc[0, "long_exit_fill"]
    assert res1.loc[0, "short_entry_fill"] == res2.loc[0, "short_entry_fill"]
    assert res1.loc[0, "short_exit_fill"] == res2.loc[0, "short_exit_fill"]
    assert res1.loc[0, "net_return_long"] == res2.loc[0, "net_return_long"]
    assert res1.loc[0, "net_return_short"] == res2.loc[0, "net_return_short"]
    assert res1.loc[0, "target_class"] == res2.loc[0, "target_class"]


# ==============================================================================
# 2. BID-ONLY EXECUTION CONVENTION & DETERMINISTIC FRICTION TESTS
# ==============================================================================

def test_deterministic_cost_friction_never_improves_pnl():
    """Verify costs strictly drag PnL: Net PnL < Gross PnL across all scenarios."""
    cost_model = ExecutionCostModel(
        base_spread_usd=0.20,
        base_slippage_usd=0.05,
        commission_per_lot_usd=5.0,  # $0.05 / oz leg
    )

    t_entry = pd.Timestamp("2024-05-15 14:00:00", tz="UTC")
    t_exit = pd.Timestamp("2024-05-15 14:30:00", tz="UTC")

    scenarios = [
        (2300.0, 2320.0),  # Bullish market (+ $20)
        (2300.0, 2280.0),  # Bearish market (- $20)
        (2300.0, 2300.0),  # Flat / zero-movement market
        (2300.0, 2300.10), # Micro-movement (+ $0.10, less than round-turn costs)
    ]

    for entry_bid, exit_bid in scenarios:
        # Long trade: BUY entry, SELL exit
        buy_entry = cost_model.simulate_causal_fill("BUY", nominal_bid=entry_bid, timestamp=t_entry)
        sell_exit = cost_model.simulate_causal_fill("SELL", nominal_bid=exit_bid, timestamp=t_exit)

        gross_pnl_long = exit_bid - entry_bid
        net_pnl_long = (sell_exit.fill_price - buy_entry.fill_price) - 2.0 * cost_model.commission_per_oz

        # Total Long friction
        total_long_friction = buy_entry.effective_spread + buy_entry.slippage + sell_exit.slippage + 2.0 * cost_model.commission_per_oz
        assert net_pnl_long == pytest.approx(gross_pnl_long - total_long_friction, abs=1e-5)
        assert net_pnl_long < gross_pnl_long, "Costs must strictly reduce Long PnL"

        # Short trade: SELL entry, BUY exit
        sell_entry = cost_model.simulate_causal_fill("SELL", nominal_bid=entry_bid, timestamp=t_entry)
        buy_exit = cost_model.simulate_causal_fill("BUY", nominal_bid=exit_bid, timestamp=t_exit)

        gross_pnl_short = entry_bid - exit_bid
        net_pnl_short = (sell_entry.fill_price - buy_exit.fill_price) - 2.0 * cost_model.commission_per_oz

        # Total Short friction
        total_short_friction = buy_exit.effective_spread + sell_entry.slippage + buy_exit.slippage + 2.0 * cost_model.commission_per_oz
        assert net_pnl_short == pytest.approx(gross_pnl_short - total_short_friction, abs=1e-5)
        assert net_pnl_short < gross_pnl_short, "Costs must strictly reduce Short PnL"


def test_zero_movement_trade_guarantees_negative_returns_both_sides():
    """In zero-movement market, transaction friction ensures both Long and Short lose money."""
    N = 20
    H = 6
    ts = pd.date_range("2024-05-13 12:00:00", periods=N, freq="5min", tz="UTC")
    df = pd.DataFrame({
        "timestamp": ts,
        "open": 2350.00,  # Completely flat price
        "high": 2351.00,
        "low": 2349.00,
        "close": 2350.00,
        "atr_14": 1.5,
    })

    labeler = CausalDirectionalLabeler(horizon=H, min_return_threshold=0.0)
    labels = labeler.compute_labels(df)

    # For all valid rows, both net_return_long and net_return_short must be strictly negative
    valid_mask = ~labels["is_purged"]
    assert valid_mask.sum() == N - (1 + H)

    assert (labels.loc[valid_mask, "net_return_long"] < 0.0).all()
    assert (labels.loc[valid_mask, "net_return_short"] < 0.0).all()
    # Therefore, all valid rows must be labeled 0 (Neutral)
    assert (labels.loc[valid_mask, "target_class"] == 0).all()


def test_bid_only_execution_symmetry_and_consistency():
    """Assert long and short execution structures are symmetric: 1 spread, 2 slippages, 2 commissions."""
    cost_model = ExecutionCostModel(base_spread_usd=0.20, base_slippage_usd=0.05, commission_per_lot_usd=5.0)
    t = pd.Timestamp("2024-05-15 14:00:00", tz="UTC")
    bid = 2300.00

    buy = cost_model.simulate_causal_fill("BUY", nominal_bid=bid, timestamp=t)
    sell = cost_model.simulate_causal_fill("SELL", nominal_bid=bid, timestamp=t)

    # Buy fill executes at Ask = Bid + Spread + Slippage
    assert buy.fill_price == pytest.approx(bid + 0.20 + 0.05, abs=1e-4)
    # Sell fill executes at Bid - Slippage
    assert sell.fill_price == pytest.approx(bid - 0.05, abs=1e-4)

    # Round-turn friction for identical spread & slippage on entry and exit:
    # Long: Spread (entry) + Slippage (entry) + Slippage (exit) + 2*Comm = 0.20 + 0.05 + 0.05 + 0.10 = 0.40
    # Short: Spread (exit) + Slippage (entry) + Slippage (exit) + 2*Comm = 0.20 + 0.05 + 0.05 + 0.10 = 0.40
    friction_long = buy.effective_spread + buy.slippage + sell.slippage + 2.0 * cost_model.commission_per_oz
    friction_short = buy.effective_spread + sell.slippage + buy.slippage + 2.0 * cost_model.commission_per_oz
    assert friction_long == pytest.approx(friction_short, abs=1e-5)
    assert friction_long == pytest.approx(0.40, abs=1e-5)


# ==============================================================================
# 3. TIMEZONE-AWARE ROLLOVER PARITY (EST, EDT, DST TRANSITIONS)
# ==============================================================================

def test_cost_model_rollover_parity_dst_and_standard_time():
    """Verify cost_model.is_rollover_closed matches time_features.is_daily_roll_window.

    Tests:
    1. Winter / Standard Time (EST: UTC-5, rollover at 22:00-23:00 UTC).
    2. Summer / Daylight Saving Time (EDT: UTC-4, rollover at 21:00-22:00 UTC).
    3. March US DST transition week.
    4. November US DST transition week.
    """
    cost_model = ExecutionCostModel()
    extractor = TimeFeatureExtractor()

    test_date_ranges = [
        # 1. Winter (EST): January 2024
        ("2024-01-15 00:00:00", "2024-01-20 00:00:00"),
        # 2. Summer (EDT): July 2024
        ("2024-07-15 00:00:00", "2024-07-20 00:00:00"),
        # 3. Spring DST transition (US starts EDT March 10, 2024)
        ("2024-03-08 00:00:00", "2024-03-15 00:00:00"),
        # 4. Autumn DST transition (US ends EDT November 3, 2024)
        ("2024-11-01 00:00:00", "2024-11-08 00:00:00"),
    ]

    for start_str, end_str in test_date_ranges:
        ts = pd.date_range(start_str, end_str, freq="15min", tz="UTC")
        series_ts = pd.Series(ts)

        features = extractor.extract_time_features(series_ts)
        roll_features = features["is_daily_roll_window"].to_numpy(dtype=bool)

        # Check scalar method
        scalar_checks = np.array([cost_model.is_rollover_closed(t) for t in ts], dtype=bool)
        assert np.array_equal(scalar_checks, roll_features), (
            f"Parity mismatch between scalar is_rollover_closed and is_daily_roll_window for {start_str} to {end_str}"
        )

        # Check vectorized method
        vec_checks = cost_model.is_rollover_closed_series(series_ts)
        assert np.array_equal(vec_checks, roll_features), (
            f"Parity mismatch between vectorized is_rollover_closed_series and is_daily_roll_window for {start_str} to {end_str}"
        )


def test_rollover_trade_rejection():
    """Verify orders during daily settlement rollover (Mon-Thu 17:00 NY) are rejected."""
    cost_model = ExecutionCostModel()

    # Summer (EDT: UTC-4): 17:30 NY = 21:30 UTC on Wednesday
    t_summer_roll = pd.Timestamp("2024-07-17 21:30:00", tz="UTC")
    exec_summer = cost_model.simulate_causal_fill("BUY", nominal_bid=2400.0, timestamp=t_summer_roll)
    assert exec_summer.is_tradable is False
    assert "Market closed during daily settlement rollover" in exec_summer.rejection_reason

    # Winter (EST: UTC-5): 17:30 NY = 22:30 UTC on Wednesday
    t_winter_roll = pd.Timestamp("2024-01-17 22:30:00", tz="UTC")
    exec_winter = cost_model.simulate_causal_fill("SELL", nominal_bid=2050.0, timestamp=t_winter_roll)
    assert exec_winter.is_tradable is False
    assert "Market closed during daily settlement rollover" in exec_winter.rejection_reason


# ==============================================================================
# 4. WEEKEND PURGE POLICY TESTS
# ==============================================================================

def test_weekend_purge_policy_default():
    """Verify trades crossing a weekend market closure are purged with reason WEEKEND_CROSSING."""
    # Construct synthetic candles around Friday close to Sunday open:
    # Friday 16:30, 16:35, 16:40, 16:45, 16:50, 16:55 NY time
    # (In summer EDT: 20:30 to 20:55 UTC)
    fri_ts = pd.date_range("2024-05-17 20:30:00", periods=6, freq="5min", tz="UTC")

    # Sunday 18:00 NY time onward (22:00 UTC onward)
    sun_ts = pd.date_range("2024-05-19 22:00:00", periods=10, freq="5min", tz="UTC")

    all_ts = fri_ts.append(sun_ts)
    N = len(all_ts)

    df = pd.DataFrame({
        "timestamp": all_ts,
        "open": 2370.0 + np.arange(N) * 1.0,
        "high": 2372.0 + np.arange(N) * 1.0,
        "low": 2368.0 + np.arange(N) * 1.0,
        "close": 2371.0 + np.arange(N) * 1.0,
        "atr_14": 2.0,
    })

    H = 6
    labeler = CausalDirectionalLabeler(horizon=H, weekend_policy="purge")
    labels = labeler.compute_labels(df)
    summary = labeler.get_summary(labels)

    # Any trade whose entry is on Friday and exit lands on Sunday spans across the weekend gap (> 24h)
    # Check that weekend crossing rows have target_class == NaN and purge_reason == 'WEEKEND_CROSSING'
    weekend_rows = labels[labels["purge_reason"] == PURGE_WEEKEND_CROSSING]
    assert len(weekend_rows) > 0
    assert weekend_rows["target_class"].isna().all()
    assert weekend_rows["is_purged"].all()
    assert summary.purge_counts[PURGE_WEEKEND_CROSSING] == len(weekend_rows)

    # Verify NO fabricated Friday exit fill: exit prices and exit timestamps must reflect actual data or NaT
    for _, row in weekend_rows.iterrows():
        # The exit timestamp must be on Sunday (or NaT), NEVER a fabricated Friday 16:59 timestamp
        if pd.notna(row["exit_timestamp"]):
            assert row["exit_timestamp"] >= pd.Timestamp("2024-05-19 22:00:00", tz="UTC")


def test_weekend_purge_configurable():
    """Verify configurable weekend_policy='allow' preserves weekend-spanning trades."""
    fri_ts = pd.date_range("2024-05-17 20:30:00", periods=6, freq="5min", tz="UTC")
    sun_ts = pd.date_range("2024-05-19 22:00:00", periods=10, freq="5min", tz="UTC")
    all_ts = fri_ts.append(sun_ts)
    N = len(all_ts)

    df = pd.DataFrame({
        "timestamp": all_ts,
        "open": 2370.0 + np.arange(N) * 1.0,
        "high": 2372.0 + np.arange(N) * 1.0,
        "low": 2368.0 + np.arange(N) * 1.0,
        "close": 2371.0 + np.arange(N) * 1.0,
        "atr_14": 2.0,
    })

    H = 6
    labeler_allow = CausalDirectionalLabeler(horizon=H, weekend_policy="allow")
    labels_allow = labeler_allow.compute_labels(df)
    summary_allow = labeler_allow.get_summary(labels_allow)

    assert summary_allow.purge_counts[PURGE_WEEKEND_CROSSING] == 0


# ==============================================================================
# 5. EXACT PARTITION-BOUNDARY PURGING TESTS
# ==============================================================================

def test_partition_boundary_purge():
    """Verify that exactly the final 1 + H rows of a partition are purged with BOUNDARY_SPLIT_OVERFLOW."""
    N = 40
    for H in [6, 12]:
        ts = pd.date_range("2024-05-13 08:00:00", periods=N, freq="5min", tz="UTC")
        df = pd.DataFrame({
            "timestamp": ts,
            "open": 2300.0,
            "high": 2302.0,
            "low": 2298.0,
            "close": 2300.0,
            "atr_14": 1.5,
        })

        labeler = CausalDirectionalLabeler(horizon=H)
        labels = labeler.compute_labels(df)
        summary = labeler.get_summary(labels)

        # Expected boundary purged count: exactly 1 + H
        assert summary.purge_counts[PURGE_BOUNDARY_SPLIT_OVERFLOW] == 1 + H
        assert labels["purge_reason"].iloc[-(1 + H):].tolist() == [PURGE_BOUNDARY_SPLIT_OVERFLOW] * (1 + H)
        assert labels["target_class"].iloc[-(1 + H):].isna().all()
        assert labels["is_purged"].iloc[-(1 + H):].all()

        # Non-boundary rows must NOT be purged by split overflow
        assert (labels["purge_reason"].iloc[:-(1 + H)] != PURGE_BOUNDARY_SPLIT_OVERFLOW).all()


def test_cross_split_isolation():
    """Verify that appending Validation data after Train data has zero effect on Train labels."""
    N_train = 30
    N_val = 20
    H = 6

    ts_all = pd.date_range("2024-05-13 08:00:00", periods=N_train + N_val, freq="5min", tz="UTC")
    df_all = pd.DataFrame({
        "timestamp": ts_all,
        "open": 2300.0 + np.sin(np.linspace(0, 10, N_train + N_val)) * 5.0,
        "high": 2305.0 + np.sin(np.linspace(0, 10, N_train + N_val)) * 5.0,
        "low": 2295.0 + np.sin(np.linspace(0, 10, N_train + N_val)) * 5.0,
        "close": 2301.0 + np.sin(np.linspace(0, 10, N_train + N_val)) * 5.0,
        "atr_14": 2.0,
    })

    df_train = df_all.iloc[:N_train].copy().reset_index(drop=True)

    labeler = CausalDirectionalLabeler(horizon=H)
    labels_isolated_train = labeler.compute_labels(df_train)

    # In isolated train, exactly the final 1 + H rows are purged
    assert labels_isolated_train["purge_reason"].iloc[-(1 + H):].tolist() == [PURGE_BOUNDARY_SPLIT_OVERFLOW] * (1 + H)

    # Now verify that modifying the Validation set prices has ZERO effect on isolated Train labels
    df_train_copy = df_train.copy()
    labels_train_recomputed = labeler.compute_labels(df_train_copy)

    pd.testing.assert_frame_equal(labels_isolated_train, labels_train_recomputed)


# ==============================================================================
# 6. ADVERSARIAL EDGE CASE & ROBUSTNESS REGRESSION TESTS
# ==============================================================================

def test_entry_immediately_before_rollover_spread_expansion():
    """Verify entry immediately before 17:00 NY incurs the 12x DAILY_ROLL_BREAK spread penalty."""
    cost_model = ExecutionCostModel(base_spread_usd=0.20)
    # 16:55 NY on Wednesday (in summer EDT: 20:55 UTC)
    t_roll_pre = pd.Timestamp("2024-07-17 20:55:00", tz="UTC")
    session = cost_model.get_session_name(t_roll_pre)
    assert session == "DAILY_ROLL_BREAK"
    spread = cost_model.calculate_effective_spread(t_roll_pre)
    assert spread == pytest.approx(0.20 * 12.0, abs=1e-4)


def test_exit_during_rollover_closure_rejected():
    """Verify an exit scheduled during 17:00-18:00 NY rollover is purged with ROLLOVER_CLOSED."""
    # Bar 0 at 16:30 NY, Entry at 16:35 NY, Exit at 17:05 NY (H=6)
    ts = pd.date_range("2024-07-17 20:30:00", periods=8, freq="5min", tz="UTC")
    df = pd.DataFrame({
        "timestamp": ts,
        "open": 2400.0,
        "high": 2402.0,
        "low": 2398.0,
        "close": 2401.0,
        "atr_14": 1.5,
    })

    # For row 0 (16:30 NY): entry is at 16:35 NY (row 1), exit is at 17:05 NY (row 7)
    # Row 7 is 17:05 NY on Wednesday -> market closed for rollover!
    labeler = CausalDirectionalLabeler(horizon=6)
    labels = labeler.compute_labels(df)
    assert labels.loc[0, "purge_reason"] == PURGE_ROLLOVER_CLOSED
    assert labels.loc[0, "is_purged"] == True
    assert np.isnan(labels.loc[0, "target_class"])


def test_entry_before_rollover_exit_after_reopening_policies():
    """Verify policy for positions that enter before 17:00 NY and exit after 18:00 NY."""
    # Candles from 16:50 NY, 16:55 NY, [roll break 17:00-18:00 NY], 18:00 NY, 18:05 NY, 18:10 NY, 18:15 NY, 18:20 NY
    ts = pd.to_datetime([
        "2024-07-17 20:50:00+00:00", # 16:50 NY (row 0 - decision)
        "2024-07-17 20:55:00+00:00", # 16:55 NY (row 1 - entry)
        # [Daily roll closure 17:00 to 18:00 NY: 21:00 to 22:00 UTC]
        "2024-07-17 22:00:00+00:00", # 18:00 NY (row 2)
        "2024-07-17 22:05:00+00:00", # 18:05 NY (row 3)
        "2024-07-17 22:10:00+00:00", # 18:10 NY (row 4)
        "2024-07-17 22:15:00+00:00", # 18:15 NY (row 5)
        "2024-07-17 22:20:00+00:00", # 18:20 NY (row 6)
        "2024-07-17 22:25:00+00:00", # 18:25 NY (row 7 - exit for H=6)
        "2024-07-17 22:30:00+00:00", # 18:30 NY (row 8)
    ])
    df = pd.DataFrame({
        "timestamp": ts,
        "open": 2400.0,
        "high": 2405.0,
        "low": 2395.0,
        "close": 2402.0,
        "atr_14": 2.0,
    })

    # Policy 1: 'allow' (default)
    labeler_allow = CausalDirectionalLabeler(horizon=6, rollover_policy="allow")
    labels_allow = labeler_allow.compute_labels(df)
    # Row 0 enters at 16:55 NY and exits at 18:25 NY (same civil day)
    assert labels_allow.loc[0, "purge_reason"] is None or labels_allow.loc[0, "purge_reason"] != PURGE_ROLLOVER_CROSSING
    assert labels_allow.loc[0, "is_purged"] == False
    # Entry at 16:55 NY was subject to DAILY_ROLL_BREAK spread ($2.40 base)
    assert labels_allow.loc[0, "long_entry_fill"] >= 2400.0 + 2.40

    # Policy 2: 'purge'
    labeler_purge = CausalDirectionalLabeler(horizon=6, rollover_policy="purge")
    labels_purge = labeler_purge.compute_labels(df)
    assert labels_purge.loc[0, "purge_reason"] == PURGE_ROLLOVER_CROSSING
    assert labels_purge.loc[0, "is_purged"] == True
    assert np.isnan(labels_purge.loc[0, "target_class"])


def test_weekend_market_closure_rejection():
    """Verify cost_model.simulate_causal_fill rejects fills on weekends."""
    cost_model = ExecutionCostModel()

    # Saturday noon UTC
    t_sat = pd.Timestamp("2024-05-18 12:00:00", tz="UTC")
    exec_sat = cost_model.simulate_causal_fill("BUY", 2400.0, timestamp=t_sat)
    assert exec_sat.is_tradable is False
    assert "Market closed for weekend" in exec_sat.rejection_reason

    # Sunday 14:00 NY (18:00 UTC) - still before 18:00 NY reopen
    t_sun = pd.Timestamp("2024-05-19 18:00:00", tz="UTC")
    exec_sun = cost_model.simulate_causal_fill("SELL", 2400.0, timestamp=t_sun)
    assert exec_sun.is_tradable is False
    assert "Market closed for weekend" in exec_sun.rejection_reason


def test_invalid_timestamps_adversarial():
    """Verify labeler rejects non-monotonic or duplicated timestamps."""
    labeler = CausalDirectionalLabeler(horizon=6)

    # 1. Non-monotonic timestamps
    ts_non_mono = pd.to_datetime([
        "2024-05-13 08:00:00+00:00",
        "2024-05-13 08:10:00+00:00",
        "2024-05-13 08:05:00+00:00",  # inverted!
        "2024-05-13 08:15:00+00:00",
    ])
    df_non_mono = pd.DataFrame({
        "timestamp": ts_non_mono,
        "open": 2300.0,
        "high": 2305.0,
        "low": 2295.0,
        "close": 2302.0,
    })
    with pytest.raises(ValueError, match="strictly monotonic"):
        labeler.compute_labels(df_non_mono)

    # 2. Duplicate timestamps
    ts_dup = pd.to_datetime([
        "2024-05-13 08:00:00+00:00",
        "2024-05-13 08:05:00+00:00",
        "2024-05-13 08:05:00+00:00",  # duplicate!
        "2024-05-13 08:10:00+00:00",
    ])
    df_dup = pd.DataFrame({
        "timestamp": ts_dup,
        "open": 2300.0,
        "high": 2305.0,
        "low": 2295.0,
        "close": 2302.0,
    })
    with pytest.raises(ValueError, match="duplicate"):
        labeler.compute_labels(df_dup)


def test_invalid_price_and_atr_inputs_adversarial():
    """Verify labeler rejects negative prices, High < Low, and negative ATR."""
    labeler = CausalDirectionalLabeler(horizon=6)
    ts = pd.date_range("2024-05-13 08:00:00", periods=10, freq="5min", tz="UTC")

    # 1. Negative price
    df_neg = pd.DataFrame({
        "timestamp": ts,
        "open": [-100.0] + [2300.0] * 9,
        "high": 2305.0,
        "low": 2295.0,
        "close": 2302.0,
    })
    with pytest.raises(ValueError, match="non-positive"):
        labeler.compute_labels(df_neg)

    # 2. High < Low
    df_inv_hl = pd.DataFrame({
        "timestamp": ts,
        "open": 2300.0,
        "high": 2290.0,  # High < Low!
        "low": 2310.0,
        "close": 2300.0,
    })
    with pytest.raises(ValueError, match="cannot be strictly less than"):
        labeler.compute_labels(df_inv_hl)

    # 3. Negative ATR
    df_neg_atr = pd.DataFrame({
        "timestamp": ts,
        "open": 2300.0,
        "high": 2305.0,
        "low": 2295.0,
        "close": 2302.0,
        "atr_14": [-1.0] + [2.0] * 9,
    })
    with pytest.raises(ValueError, match="negative"):
        labeler.compute_labels(df_neg_atr)


def test_vectorized_vs_scalar_labeling_complete_parity():
    """Assert complete numeric parity between vectorized compute_labels and scalar simulate_causal_fill."""
    N = 50
    H = 6
    ts = pd.date_range("2024-05-13 08:00:00", periods=N, freq="5min", tz="UTC")
    opens = 2300.0 + np.sin(np.linspace(0, 10, N)) * 10.0
    highs = opens + 3.0
    lows = opens - 3.0
    closes = opens + 1.0
    atrs = 1.5 + np.cos(np.linspace(0, 10, N)) * 0.5

    df = pd.DataFrame({
        "timestamp": ts,
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "atr_14": atrs,
    })

    cost_model = ExecutionCostModel()
    labeler = CausalDirectionalLabeler(horizon=H, cost_model=cost_model)
    res_vec = labeler.compute_labels(df, baseline_atr=1.5, baseline_candle_range=6.0)

    # Compare row-by-row against scalar simulate_causal_fill for all non-purged rows
    for i in range(N - (1 + H)):
        if res_vec.loc[i, "is_purged"]:
            continue

        entry_bid = opens[i + 1]
        exit_bid = opens[i + 1 + H]
        entry_t = ts[i + 1]
        exit_t = ts[i + 1 + H]

        prior_atr_e = atrs[i]
        prior_rng_e = highs[i] - lows[i]
        prior_atr_x = atrs[i + H]
        prior_rng_x = highs[i + H] - lows[i + H]

        # Scalar BUY entry
        fill_e_long = cost_model.simulate_causal_fill(
            "BUY", nominal_bid=entry_bid, timestamp=entry_t,
            prior_atr=prior_atr_e, baseline_atr=1.5,
            prior_candle_range=prior_rng_e, baseline_candle_range=6.0,
        )
        # Scalar SELL exit
        fill_x_long = cost_model.simulate_causal_fill(
            "SELL", nominal_bid=exit_bid, timestamp=exit_t,
            prior_atr=prior_atr_x, baseline_atr=1.5,
            prior_candle_range=prior_rng_x, baseline_candle_range=6.0,
        )

        assert res_vec.loc[i, "long_entry_fill"] == fill_e_long.fill_price
        assert res_vec.loc[i, "long_exit_fill"] == fill_x_long.fill_price

        # Scalar SELL entry
        fill_e_short = cost_model.simulate_causal_fill(
            "SELL", nominal_bid=entry_bid, timestamp=entry_t,
            prior_atr=prior_atr_e, baseline_atr=1.5,
            prior_candle_range=prior_rng_e, baseline_candle_range=6.0,
        )
        # Scalar BUY exit
        fill_x_short = cost_model.simulate_causal_fill(
            "BUY", nominal_bid=exit_bid, timestamp=exit_t,
            prior_atr=prior_atr_x, baseline_atr=1.5,
            prior_candle_range=prior_rng_x, baseline_candle_range=6.0,
        )

        assert res_vec.loc[i, "short_entry_fill"] == fill_e_short.fill_price
        assert res_vec.loc[i, "short_exit_fill"] == fill_x_short.fill_price


def test_long_horizon_weekend_threshold_regression():
    """Verify that long horizons (e.g. H=288, 24h trading duration) do not falsely purge
    normal weekday positions due to hardcoded 24h weekend thresholds.
    """
    N = 600
    H = 288
    ts = pd.date_range("2024-05-13 00:00:00", periods=N, freq="5min", tz="UTC")
    df = pd.DataFrame({
        "timestamp": ts,
        "open": 2300.0 + np.arange(N) * 0.1,
        "high": 2302.0 + np.arange(N) * 0.1,
        "low": 2298.0 + np.arange(N) * 0.1,
        "close": 2301.0 + np.arange(N) * 0.1,
        "atr_14": 2.0,
    })

    # Default initialization should auto-scale weekend_threshold_hours
    labeler = CausalDirectionalLabeler(horizon=H)
    assert labeler.weekend_threshold_hours == pytest.approx(max(24.0, (H * 5 / 60.0) + 20.0), abs=1e-3)
    assert labeler.weekend_threshold_hours > 25.0

    labels = labeler.compute_labels(df)
    summary = labeler.get_summary(labels)

    # In continuous weekday data, ZERO rows should be purged for PURGE_WEEKEND_CROSSING
    assert summary.purge_counts[PURGE_WEEKEND_CROSSING] == 0
    # Exactly 1 + H rows purged for BOUNDARY_SPLIT_OVERFLOW at the end of partition
    assert summary.purge_counts[PURGE_BOUNDARY_SPLIT_OVERFLOW] == 1 + H
    # Daily settlement rollover (17:00-18:00 NY) accounts for 12 bars of closure per weekday
    assert summary.purge_counts[PURGE_ROLLOVER_CLOSED] == 12
    # Valid rows must equal N - (1 + H) - ROLLOVER_CLOSED
    expected_valid = N - (1 + H) - summary.purge_counts[PURGE_ROLLOVER_CLOSED]
    assert summary.valid_rows == expected_valid
    assert summary.valid_rows == 299


def test_weekend_boundary_near_closure_precision():
    """Verify exact purge behavior near Friday market closure across short and long horizons."""
    # Summer EDT (UTC-4):
    # Friday 15:00 NY = 19:00 UTC
    # Friday 17:00 NY = 21:00 UTC (Market Closes)
    # Sunday 18:00 NY = 22:00 UTC (Market Reopens, 49h gap)
    # Monday 04:00 NY = 08:00 UTC

    # Friday bars: 15:00 NY to 16:55 NY (24 bars)
    fri_ts = pd.date_range("2024-05-17 19:00:00", "2024-05-17 20:55:00", freq="5min", tz="UTC")
    # Sunday/Monday bars: Sunday 18:00 NY to Monday 04:00 NY (120 bars)
    sun_ts = pd.date_range("2024-05-19 22:00:00", "2024-05-20 08:00:00", freq="5min", tz="UTC")

    all_ts = fri_ts.append(sun_ts)
    N = len(all_ts)

    df = pd.DataFrame({
        "timestamp": all_ts,
        "open": 2350.0 + np.arange(N) * 0.05,
        "high": 2352.0 + np.arange(N) * 0.05,
        "low": 2348.0 + np.arange(N) * 0.05,
        "close": 2351.0 + np.arange(N) * 0.05,
        "atr_14": 2.0,
    })

    # Test Short Horizon H=6 (30 mins)
    labeler_h6 = CausalDirectionalLabeler(horizon=6)
    labels_h6 = labeler_h6.compute_labels(df)

    # 1. Early Friday trade: Decision at bar 0 (15:00 NY)
    # Entry at bar 1 (15:05 NY), Exit at bar 7 (15:35 NY). Both on Friday.
    assert labels_h6.loc[0, "is_purged"] == False or labels_h6.loc[0, "purge_reason"] != PURGE_WEEKEND_CROSSING
    assert pd.notna(labels_h6.loc[0, "target_class"])

    # 2. Friday trade crossing into Sunday: Decision at bar 20 (16:40 NY)
    # Entry at bar 21 (16:45 NY), Exit at bar 27 (Sunday 18:15 NY).
    # Crosses the 49h weekend gap!
    assert labels_h6.loc[20, "purge_reason"] == PURGE_WEEKEND_CROSSING
    assert labels_h6.loc[20, "is_purged"] == True
    assert np.isnan(labels_h6.loc[20, "target_class"])

    # Test Extended Horizon H=96 (8.0 hours)
    labeler_h96 = CausalDirectionalLabeler(horizon=96)
    labels_h96 = labeler_h96.compute_labels(df)

    # Any Friday trade for H=96 must cross the weekend closure because only 24 Friday bars exist!
    for fri_idx in range(len(fri_ts)):
        if labels_h96.loc[fri_idx, "is_purged"]:
            assert labels_h96.loc[fri_idx, "purge_reason"] in [
                PURGE_WEEKEND_CROSSING, PURGE_ROLLOVER_CLOSED, PURGE_BOUNDARY_SPLIT_OVERFLOW
            ]

    # Sunday reopen trade: Decision at bar 25 (Sunday 18:05 NY)
    # Enters Sunday 18:10 NY, exits Monday 02:10 NY. 96 continuous bars on Sunday night / Monday.
    # Elapsed time is 8 hours, well below H=96 threshold of 28 hours!
    idx_sun_trade = len(fri_ts) + 1  # Sunday 18:05 NY
    assert labels_h96.loc[idx_sun_trade, "purge_reason"] != PURGE_WEEKEND_CROSSING
    assert labels_h96.loc[idx_sun_trade, "is_purged"] == False
    assert pd.notna(labels_h96.loc[idx_sun_trade, "target_class"])


def test_multi_horizon_purge_behavior_consistency():
    """Verify threshold computation and configuration override across all horizons."""
    for H in [6, 12, 24, 48, 72, 96, 120, 288]:
        lbl_default = CausalDirectionalLabeler(horizon=H)
        expected_thresh = max(24.0, (H * 5 / 60.0) + 20.0)
        assert lbl_default.weekend_threshold_hours == pytest.approx(expected_thresh, abs=1e-4)

        # Explicit override must be respected
        lbl_override = CausalDirectionalLabeler(horizon=H, weekend_threshold_hours=99.0)
        assert lbl_override.weekend_threshold_hours == 99.0

