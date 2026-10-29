"""Tests for Phase 7 Volatility-Scaled Triple-Barrier Labeling and Strategy Simulator.

Strict Verifications:
1. Barrier-touch ordering (target, stop, time-limit).
2. Conservative stop-first handling for ambiguous same-bar candles.
3. Realistic gap-through fill pricing (filling at open, not ideal barrier).
4. Time-stop vertical exit at exact max_holding_bars limit.
5. Causal volatility scaling (ATR finalized at or before decision time).
6. Weekend-crossing and boundary split purging.
7. Non-overlapping single-position capacity constraint.
8. Exact PnL reconciliation: Net PnL = Gross PnL - (spread + slippage + comm).
9. Complete isolation and protection of the frozen 2026 test partition.
"""

from datetime import datetime, timezone
import numpy as np
import pandas as pd
import pytest

from treading_ai.backtesting.cost_model import ExecutionCostModel
from treading_ai.backtesting.triple_barrier_simulator import (
    TripleBarrierSimulator,
    TripleBarrierMetrics,
    TripleBarrierTrade,
)
from treading_ai.models.triple_barrier_labeler import (
    TripleBarrierLabeler,
    PURGE_BOUNDARY_SPLIT_OVERFLOW,
    PURGE_WEEKEND_CROSSING,
)


@pytest.fixture
def clean_synthetic_df():
    """Create a 100-bar synthetic dataframe for deterministic barrier testing."""
    n_bars = 100
    base_time = pd.Timestamp("2021-01-04 00:00:00", tz="UTC")
    timestamps = [base_time + pd.Timedelta(minutes=5 * i) for i in range(n_bars)]

    # Fixed price at 1800, flat candles with range 0.2
    opens = np.full(n_bars, 1800.0)
    highs = np.full(n_bars, 1800.1)
    lows = np.full(n_bars, 1799.9)
    closes = np.full(n_bars, 1800.0)
    atrs = np.full(n_bars, 1.0)  # ATR = 1.0

    df = pd.DataFrame({
        "timestamp": timestamps,
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "atr_14": atrs,
    })
    return df


class TestTripleBarrierMechanics:
    """Verify barrier touches, gap fills, and ambiguous candle resolution."""

    def test_target_barrier_hit_triggers_target_exit(self, clean_synthetic_df):
        df = clean_synthetic_df.copy()
        # Signal at bar 0 (index 0), entry at bar 1 (Open=1800.0)
        # Entry fill for Long: ~1800.25 (1800 + spread 0.20 + slippage 0.05)
        # Target: fill + 2.0 * ATR = ~1802.25
        # Set bar 5 High to 1803.0 -> Target reached!
        df.loc[5, "high"] = 1803.0

        signals = np.zeros(len(df), dtype=int)
        signals[0] = 1

        sim = TripleBarrierSimulator(pt_atr=2.0, sl_atr=1.0, max_holding_bars=24)
        metrics, trades = sim.simulate(df, signals, strategy_name="TestTarget")

        assert len(trades) == 1
        t = trades[0]
        assert t.exit_reason == "TARGET"
        assert t.exit_index == 5
        assert t.bars_held == 4  # entry at bar 1, exit at bar 5 (5 - 1 = 4 bars elapsed)
        assert t.gross_pnl > 0.0
        assert t.net_pnl > 0.0

    def test_stop_barrier_hit_triggers_stop_exit(self, clean_synthetic_df):
        df = clean_synthetic_df.copy()
        # Set bar 3 Low to 1798.0 -> Stop reached! (Stop is ~1799.25)
        df.loc[3, "low"] = 1798.0

        signals = np.zeros(len(df), dtype=int)
        signals[0] = 1

        sim = TripleBarrierSimulator(pt_atr=2.0, sl_atr=1.0, max_holding_bars=24)
        metrics, trades = sim.simulate(df, signals, strategy_name="TestStop")

        assert len(trades) == 1
        t = trades[0]
        assert t.exit_reason == "STOP"
        assert t.exit_index == 3
        assert t.gross_pnl < 0.0
        assert t.net_pnl < 0.0

    def test_ambiguous_same_bar_applies_conservative_stop_first(self, clean_synthetic_df):
        df = clean_synthetic_df.copy()
        # On bar 4, price swings wildly: High = 1805.0 (touches target), Low = 1795.0 (touches stop)
        df.loc[4, "high"] = 1805.0
        df.loc[4, "low"] = 1795.0

        signals = np.zeros(len(df), dtype=int)
        signals[0] = 1

        # With conservative_stop_first=True, it MUST exit as STOP!
        sim = TripleBarrierSimulator(pt_atr=2.0, sl_atr=1.0, max_holding_bars=24, conservative_stop_first=True)
        metrics, trades = sim.simulate(df, signals, strategy_name="TestAmbiguity")

        assert len(trades) == 1
        t = trades[0]
        assert t.is_ambiguous_same_bar is True
        assert t.exit_reason == "STOP", "Ambiguous bar must be resolved conservatively as STOP"
        assert t.exit_index == 4

    def test_gap_through_fill_executes_at_open_price(self, clean_synthetic_df):
        df = clean_synthetic_df.copy()
        # At bar 4, market gaps down severely: Open=1795.0 (well below stop barrier ~1799.25)
        df.loc[4, "open"] = 1795.0
        df.loc[4, "high"] = 1795.5
        df.loc[4, "low"] = 1794.5
        df.loc[4, "close"] = 1795.0

        signals = np.zeros(len(df), dtype=int)
        signals[0] = 1

        sim = TripleBarrierSimulator(pt_atr=2.0, sl_atr=1.0, max_holding_bars=24)
        metrics, trades = sim.simulate(df, signals, strategy_name="TestGap")

        assert len(trades) == 1
        t = trades[0]
        assert t.is_gap_exit is True
        assert t.exit_reason == "STOP"
        # Executable exit bid must reflect the gap open price (1795.0), NOT ideal barrier (1799.25)!
        assert t.exit_bid == 1795.0

    def test_time_limit_exit_when_no_barrier_touched(self, clean_synthetic_df):
        df = clean_synthetic_df.copy()
        # Flat prices: neither target nor stop is touched
        signals = np.zeros(len(df), dtype=int)
        signals[0] = 1

        H_max = 24
        sim = TripleBarrierSimulator(pt_atr=2.0, sl_atr=1.0, max_holding_bars=H_max)
        metrics, trades = sim.simulate(df, signals, strategy_name="TestTimeLimit")

        assert len(trades) == 1
        t = trades[0]
        assert t.exit_reason == "TIME_LIMIT"
        assert t.bars_held == H_max
        assert t.exit_index == 1 + H_max


class TestAccountingAndCapacity:
    """Verify exact PnL reconciliation and single-position capacity lockout."""

    def test_pnl_reconciliation_zero_double_counting(self, clean_synthetic_df):
        df = clean_synthetic_df.copy()
        df.loc[5, "high"] = 1805.0  # Target hit for long
        df.loc[20, "high"] = 1805.0  # Target hit for next trade

        signals = np.zeros(len(df), dtype=int)
        signals[0] = 1   # Long
        signals[10] = -1 # Short

        sim = TripleBarrierSimulator(pt_atr=2.0, sl_atr=1.0, max_holding_bars=24)
        metrics, trades = sim.simulate(df, signals, strategy_name="TestRecon")

        assert len(trades) == 2
        for t in trades:
            expected_friction = t.entry_spread + t.exit_spread + t.entry_slippage + t.exit_slippage + t.commission
            assert np.isclose(t.total_friction, expected_friction, atol=1e-4)
            assert np.isclose(t.net_pnl, t.gross_pnl - t.total_friction, atol=1e-4)

        # Aggregate metrics
        assert np.isclose(metrics.net_pnl_usd, metrics.gross_pnl_usd - metrics.total_friction_usd, atol=1e-4)

    def test_non_overlapping_lockout_duration(self, clean_synthetic_df):
        df = clean_synthetic_df.copy()
        # Signals at every bar from 0 to 9
        signals = np.zeros(len(df), dtype=int)
        signals[0:10] = 1

        # Make trade 1 hit target at bar 5
        df.loc[5, "high"] = 1805.0

        sim = TripleBarrierSimulator(pt_atr=2.0, sl_atr=1.0, max_holding_bars=24, mode="non_overlapping")
        metrics, trades = sim.simulate(df, signals, strategy_name="TestCapacity")

        # Trade 1 entered at bar 1 and exited at bar 5.
        # Signals at bars 1, 2, 3, 4 were suppressed (capacity rejected).
        # Bar 5 is exit bar; next trade can enter at bar 6.
        assert len(trades) >= 2
        assert trades[0].entry_index == 1
        assert trades[0].exit_index == 5
        assert trades[1].entry_index == 6
        assert metrics.max_concurrent_positions == 1
        assert metrics.n_capacity_rejected > 0


class TestLabelerPurgingAndIsolation:
    """Verify triple barrier labeler boundary purging and weekend closures."""

    def test_labeler_tail_boundary_purged(self, clean_synthetic_df):
        df = clean_synthetic_df.copy()
        H_max = 24
        labeler = TripleBarrierLabeler(pt_atr=2.0, sl_atr=1.0, max_holding_bars=H_max)
        labels = labeler.compute_labels(df)

        # Tail 1 + H_max bars must be purged
        tail = labels.iloc[-(1 + H_max):]
        assert (tail["is_purged"] == True).all()
        assert (tail["purge_reason"] == PURGE_BOUNDARY_SPLIT_OVERFLOW).all()

    def test_weekend_crossing_purged(self, clean_synthetic_df):
        df = clean_synthetic_df.copy()
        # Insert a weekend jump (>24 hours) between bar 5 and bar 6
        for k in range(6, len(df)):
            df.loc[k, "timestamp"] = df.loc[k, "timestamp"] + pd.Timedelta(hours=50)

        labeler = TripleBarrierLabeler(pt_atr=2.0, sl_atr=1.0, max_holding_bars=24)
        labels = labeler.compute_labels(df)

        # A trade initiated at bar 3 would cross the weekend gap at bar 6 (holding > 3 bars)
        assert bool(labels.loc[3, "is_purged"]) is True or bool(labels.loc[4, "is_purged"]) is True

    def test_causal_atr_barrier_definition(self, clean_synthetic_df):
        df = clean_synthetic_df.copy()
        # Set bar 0 ATR to 2.0, bar 1 ATR to 10.0
        df.loc[0, "atr_14"] = 2.0
        df.loc[1, "atr_14"] = 10.0
        # Set bar 4 high to 1805.0: touches target of ~1804.25 (2.0 * 2.0 = 4.0)
        # But if bar 1 ATR (10.0) leaked, target would be ~1820.25 and 1805.0 would not touch!
        df.loc[4, "high"] = 1805.0

        signals = np.zeros(len(df), dtype=int)
        signals[0] = 1  # Signal at bar 0

        sim = TripleBarrierSimulator(pt_atr=2.0, sl_atr=1.0, max_holding_bars=24, atr_column="atr_14")
        metrics, trades = sim.simulate(df, signals, strategy_name="TestCausalATR")

        assert len(trades) == 1
        t = trades[0]
        # Must hit TARGET because it used bar 0 ATR (2.0)
        assert t.exit_reason == "TARGET"
        assert t.exit_index == 4

    def test_cost_stress_scaling(self, clean_synthetic_df):
        df = clean_synthetic_df.copy()
        df.loc[5, "high"] = 1805.0  # target hit
        signals = np.zeros(len(df), dtype=int)
        signals[0] = 1

        cost_base = ExecutionCostModel(base_spread_usd=0.20, base_slippage_usd=0.05)
        cost_2x = ExecutionCostModel(base_spread_usd=0.40, base_slippage_usd=0.10)

        sim_base = TripleBarrierSimulator(pt_atr=2.0, sl_atr=1.0, max_holding_bars=24, cost_model=cost_base)
        sim_2x = TripleBarrierSimulator(pt_atr=2.0, sl_atr=1.0, max_holding_bars=24, cost_model=cost_2x)

        m_base, t_base = sim_base.simulate(df, signals)
        m_2x, t_2x = sim_2x.simulate(df, signals)

        assert len(t_base) == 1 and len(t_2x) == 1
        # Spread and slippage should be exactly double in 2x
        assert np.isclose(t_2x[0].entry_spread, 2.0 * t_base[0].entry_spread, atol=1e-4)
        assert np.isclose(t_2x[0].entry_slippage, 2.0 * t_base[0].entry_slippage, atol=1e-4)
        assert m_2x.net_pnl_usd < m_base.net_pnl_usd

    def test_frozen_test_partition_isolation(self):
        import os
        from pathlib import Path
        test_file = Path("data/features/XAUUSD_M5_features_test.parquet")
        assert test_file.exists(), "Test partition must exist"
        # Test partition must remain completely untouched
        assert not os.path.exists("data/reports/phase7_test_results.json")
        assert not os.path.exists("data/reports/phase7_triple_barrier_test.json")
