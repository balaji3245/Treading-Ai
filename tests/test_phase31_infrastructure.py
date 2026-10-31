"""Test suite for Phase 31 Infrastructure Improvements:
1. Daily (D1) Data Pipeline with dynamic New York close session alignment and DST handling.
2. Schedule-aware H4 completeness logic distinguishing market closures from missing data.
3. Overnight swap financing engine with Wednesday triple swap and multi-unit support.
4. Accounting, integration, and strict holdout partition protection.
"""

from datetime import datetime, time, timedelta, timezone
import hashlib
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
import pytest

from treading_ai.config import (
    PROCESSED_DATA_DIR,
    TIMEFRAME_FREQ_MAP,
    TIMEFRAME_M1_COUNT,
)
from treading_ai.preprocessing.resampler import TimeframeResampler, TZ_NEW_YORK
from treading_ai.preprocessing.storage import ParquetStorageEngine
from treading_ai.backtesting.cost_model import (
    ExecutionCostModel,
    OvernightSwapEngine,
    SwapFinancingRecord,
    TradeExecution,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VAL_PATH = PROJECT_ROOT / "data/features/XAUUSD_M5_features_val.parquet"
TEST_PATH = PROJECT_ROOT / "data/features/XAUUSD_M5_features_test.parquet"

EXPECTED_VAL_HASH = "7e9222e9dc0893601e24505912eeab78330670c4e70ebcc2fa462ff8d44a4f94"
EXPECTED_TEST_HASH = "f95fd09a5d07666e3f1d9a72e840e2e97f3c058d11b6bb0c712b21dea86a5dec"


def compute_file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ==============================================================================
# 1. HOLD-OUT DATA PARTITION PROTECTION
# ==============================================================================

class TestHoldoutPartitionProtection:
    """Verify that protected holdout partitions are strictly preserved with 0 byte variance."""

    def test_val_partition_hash_unmodified(self):
        assert VAL_PATH.exists(), f"Validation partition missing: {VAL_PATH}"
        actual_hash = compute_file_sha256(VAL_PATH)
        assert actual_hash == EXPECTED_VAL_HASH, (
            f"CRITICAL: 2025 Validation partition altered! Expected {EXPECTED_VAL_HASH}, got {actual_hash}"
        )

    def test_test_partition_hash_unmodified(self):
        assert TEST_PATH.exists(), f"Test partition missing: {TEST_PATH}"
        actual_hash = compute_file_sha256(TEST_PATH)
        assert actual_hash == EXPECTED_TEST_HASH, (
            f"CRITICAL: 2026 Test partition altered! Expected {EXPECTED_TEST_HASH}, got {actual_hash}"
        )


# ==============================================================================
# 2. D1 DATA PIPELINE & SESSION ALIGNMENT
# ==============================================================================

class TestD1DataPipeline:
    """Verify Daily (D1) data pipeline, New York close session alignment, and DST handling."""

    def test_d1_timeframe_configuration(self):
        assert "D1" in TIMEFRAME_FREQ_MAP, "D1 missing from TIMEFRAME_FREQ_MAP"
        assert "D1" in TIMEFRAME_M1_COUNT, "D1 missing from TIMEFRAME_M1_COUNT"
        assert TIMEFRAME_M1_COUNT["D1"] == 1380, "D1 expected M1 count must be 1,380 (23h * 60m)"

    def test_d1_aggregation_against_m1_source(self):
        """Verify that D1 candles aggregate M1 source data with exact mathematical identity."""
        resampler = TimeframeResampler()
        storage = ParquetStorageEngine(base_dir=PROCESSED_DATA_DIR)

        # Load 2021 M1 data
        m1_path = PROCESSED_DATA_DIR / "XAUUSD/M1/XAUUSD_M1_2021.parquet"
        d1_path = PROCESSED_DATA_DIR / "XAUUSD/D1/XAUUSD_D1_2021.parquet"
        assert m1_path.exists()
        assert d1_path.exists()

        df_m1 = storage.read_candlesticks(m1_path)
        df_d1 = storage.read_candlesticks(d1_path)

        assert len(df_d1) == 258, f"Expected 258 trading days in 2021, got {len(df_d1)}"

        # Validate first session (2021-01-04):
        # In NY time, starts Sunday 2021-01-03 18:00 NY (23:00 UTC) and ends Monday 2021-01-04 17:00 NY (22:00 UTC)
        c0 = df_d1.iloc[0]
        assert c0["timestamp"] == pd.Timestamp("2021-01-04 00:00:00", tz="UTC")
        assert c0["bar_count"] == 1380
        assert c0["is_complete"] is True or c0["is_complete"] == 1

        # Check constituent slice from M1:
        # 1380 bars from 2021-01-03 23:00:00 to 2021-01-04 21:59:00 UTC
        m1_slice = df_m1.iloc[:1380]
        assert m1_slice.iloc[0]["timestamp"] == pd.Timestamp("2021-01-03 23:00:00", tz="UTC")
        assert m1_slice.iloc[-1]["timestamp"] == pd.Timestamp("2021-01-04 21:59:00", tz="UTC")

        assert c0["open"] == m1_slice.iloc[0]["open"]
        assert c0["high"] == m1_slice["high"].max()
        assert c0["low"] == m1_slice["low"].min()
        assert c0["close"] == m1_slice.iloc[-1]["close"]
        assert pytest.approx(c0["volume"]) == m1_slice["volume"].sum()

    def test_d1_zero_weekend_bars(self):
        """Verify that Sunday trading merges into Monday and produces 0 weekend candles."""
        storage = ParquetStorageEngine(base_dir=PROCESSED_DATA_DIR)
        for year in [2021, 2022]:
            d1_path = PROCESSED_DATA_DIR / f"XAUUSD/D1/XAUUSD_D1_{year}.parquet"
            df_d1 = storage.read_candlesticks(d1_path)
            weekdays = df_d1["timestamp"].dt.day_of_week
            # Weekdays: Monday=0, Tuesday=1, Wednesday=2, Thursday=3, Friday=4
            assert (weekdays < 5).all(), f"Found weekend bars in {year} D1 dataset!"
            assert (weekdays == 5).sum() == 0, f"Saturday bars present in {year}!"
            assert (weekdays == 6).sum() == 0, f"Sunday bars present in {year}!"

    def test_d1_dst_transitions(self):
        """Verify dynamic handling of US Daylight Saving Time transitions (March and November)."""
        storage = ParquetStorageEngine(base_dir=PROCESSED_DATA_DIR)
        df_m1_2021 = storage.read_candlesticks(PROCESSED_DATA_DIR / "XAUUSD/M1/XAUUSD_M1_2021.parquet")
        resampler = TimeframeResampler()
        df_d1 = resampler.resample_daily_session_ny(df_m1_2021)

        # In 2021, US Spring Forward occurred on Sunday March 14, 2021.
        # Monday March 15 session opened Sunday March 14 at 18:00 NY = 22:00 UTC (EDT summer: UTC-4).
        # Before March 14 (winter, EST: UTC-5), session opened at 23:00 UTC.
        d1_mar15 = df_d1[df_d1["timestamp"] == pd.Timestamp("2021-03-15", tz="UTC")]
        assert len(d1_mar15) == 1
        assert d1_mar15.iloc[0]["bar_count"] == 1380
        assert d1_mar15.iloc[0]["is_complete"] is True or d1_mar15.iloc[0]["is_complete"] == 1

        # In 2021, US Fall Back occurred on Sunday Nov 7, 2021.
        # Monday Nov 8 session opened Sunday Nov 7 at 18:00 NY = 23:00 UTC (EST winter: UTC-5).
        d1_nov08 = df_d1[df_d1["timestamp"] == pd.Timestamp("2021-11-08", tz="UTC")]
        assert len(d1_nov08) == 1
        assert d1_nov08.iloc[0]["bar_count"] == 1380
        assert d1_nov08.iloc[0]["is_complete"] is True or d1_nov08.iloc[0]["is_complete"] == 1

    def test_d1_holiday_incomplete_classification(self):
        """Verify that known shortened sessions (holidays) are flagged is_complete=False."""
        storage = ParquetStorageEngine(base_dir=PROCESSED_DATA_DIR)
        df_d1_2021 = storage.read_candlesticks(PROCESSED_DATA_DIR / "XAUUSD/D1/XAUUSD_D1_2021.parquet")

        # Thanksgiving 2021: 2021-11-25 (1,139 bars)
        thanksgiving = df_d1_2021[df_d1_2021["timestamp"] == pd.Timestamp("2021-11-25", tz="UTC")].iloc[0]
        assert thanksgiving["bar_count"] < 1350
        assert thanksgiving["is_complete"] is False or thanksgiving["is_complete"] == 0

        # Memorial Day 2021: 2021-05-31 (360 bars)
        memorial = df_d1_2021[df_d1_2021["timestamp"] == pd.Timestamp("2021-05-31", tz="UTC")].iloc[0]
        assert memorial["bar_count"] == 360
        assert memorial["is_complete"] is False or memorial["is_complete"] == 0


# ==============================================================================
# 3. H4 SCHEDULE-AWARE COMPLETENESS LOGIC
# ==============================================================================

class TestH4CompletenessLogic:
    """Verify H4 schedule-aware completeness logic distinguishing closures from missing data."""

    def test_h4_scheduled_active_minutes_calculation(self):
        resampler = TimeframeResampler()

        # 1. Summer rollover candle (18:00 UTC = 14:00 NY): spans 17:00-18:00 NY rollover break -> 180 min
        t_summer_roll = pd.Timestamp("2021-06-15 18:00:00", tz="UTC")
        assert resampler.get_h4_scheduled_active_minutes(t_summer_roll) == 180

        # 2. Winter rollover candle (22:00 UTC = 17:00 NY): spans 17:00-18:00 NY rollover break -> 180 min
        t_winter_roll = pd.Timestamp("2021-01-12 22:00:00", tz="UTC")
        assert resampler.get_h4_scheduled_active_minutes(t_winter_roll) == 180

        # 3. Active European morning candle (06:00 UTC): no closure -> 240 min
        t_active = pd.Timestamp("2021-01-12 06:00:00", tz="UTC")
        assert resampler.get_h4_scheduled_active_minutes(t_active) == 240

        # 4. Friday Summer close (18:00 UTC = 14:00 NY): market closes at 17:00 NY -> 180 min
        t_fri_close = pd.Timestamp("2021-06-18 18:00:00", tz="UTC")
        assert resampler.get_h4_scheduled_active_minutes(t_fri_close) == 180

    def test_h4_rollover_candle_marked_complete(self):
        """Synthetic fixture: 180-bar rollover candle is correctly marked is_complete=True."""
        resampler = TimeframeResampler()

        # Create 180 M1 bars for a summer rollover window [18:00, 22:00) UTC
        # Ticks present from 18:00 to 20:59 UTC (180 mins). 21:00-22:00 UTC is closed (17:00-18:00 NY).
        start = pd.Timestamp("2021-06-15 18:00:00", tz="UTC")
        times = [start + timedelta(minutes=i) for i in range(180)]
        df_roll = pd.DataFrame({
            "timestamp": times,
            "open": [1800.0] * 180,
            "high": [1805.0] * 180,
            "low": [1795.0] * 180,
            "close": [1801.0] * 180,
            "volume": [10.0] * 180,
        })

        h4_df = resampler.resample_candle_series(df_roll, target_timeframe="H4", h4_alignment="session")
        assert len(h4_df) == 1
        candle = h4_df.iloc[0]
        assert candle["bar_count"] == 180
        assert candle["is_complete"] is True or candle["is_complete"] == 1

    def test_h4_missing_data_not_blindly_marked_complete(self):
        """Synthetic fixture: 180 bars during active hours (06:00 UTC) must be is_complete=False."""
        resampler = TimeframeResampler()

        # Create 180 M1 bars during active European morning [06:00, 10:00) UTC
        # Scheduled duration is 240 mins. 60 bars are MISSING.
        start = pd.Timestamp("2021-06-15 06:00:00", tz="UTC")
        times = [start + timedelta(minutes=i) for i in range(180)]
        df_dropout = pd.DataFrame({
            "timestamp": times,
            "open": [1800.0] * 180,
            "high": [1805.0] * 180,
            "low": [1795.0] * 180,
            "close": [1801.0] * 180,
            "volume": [10.0] * 180,
        })

        h4_df = resampler.resample_candle_series(df_dropout, target_timeframe="H4", h4_alignment="session")
        assert len(h4_df) == 1
        candle = h4_df.iloc[0]
        assert candle["bar_count"] == 180
        # Crucial: Must NOT be complete because expected active minutes was 240!
        assert candle["is_complete"] is False or candle["is_complete"] == 0

    def test_h4_partial_rollover_candle_incomplete(self):
        """Synthetic fixture: A rollover candle with only 175 bars (5 missing) must be is_complete=False."""
        resampler = TimeframeResampler()

        start = pd.Timestamp("2021-06-15 18:00:00", tz="UTC")
        times = [start + timedelta(minutes=i) for i in range(175)]
        df_partial = pd.DataFrame({
            "timestamp": times,
            "open": [1800.0] * 175,
            "high": [1805.0] * 175,
            "low": [1795.0] * 175,
            "close": [1801.0] * 175,
            "volume": [10.0] * 175,
        })

        h4_df = resampler.resample_candle_series(df_partial, target_timeframe="H4", h4_alignment="session")
        assert len(h4_df) == 1
        candle = h4_df.iloc[0]
        assert candle["bar_count"] == 175
        assert candle["is_complete"] is False or candle["is_complete"] == 0


# ==============================================================================
# 4. OVERNIGHT SWAP FINANCING ENGINE
# ==============================================================================

class TestOvernightSwapFinancingEngine:
    """Deterministic tests for OvernightSwapEngine supporting long/short, units, triple swap."""

    def test_intraday_trade_zero_swap(self):
        """Intraday trade held within London/NY overlap crossing no 17:00 NY rollover incurs 0 swap."""
        engine = OvernightSwapEngine(swap_rate_long=-0.12, swap_rate_short=-0.04)

        # Tuesday 09:00 NY (13:00 UTC) to Tuesday 15:00 NY (19:00 UTC)
        entry_ts = pd.Timestamp("2021-06-15 13:00:00", tz="UTC")
        exit_ts = pd.Timestamp("2021-06-15 19:00:00", tz="UTC")

        record = engine.calculate_swap_financing("LONG", entry_ts, exit_ts, position_size_oz=100.0)
        assert record.rollover_count == 0
        assert record.weighted_days == 0.0
        assert record.swap_pnl_per_oz == 0.0
        assert record.total_swap_pnl_usd == 0.0
        assert record.swap_drag_per_oz == 0.0
        assert record.total_swap_drag_usd == 0.0
        assert record.is_calibrated is False  # Explicitly labeled assumption

    def test_single_rollover_crossing(self):
        """Trade held across Tuesday 17:00 NY rollover incurs exactly 1 day of financing."""
        engine = OvernightSwapEngine(swap_rate_long=-0.12, swap_rate_short=-0.04)

        # Tuesday 16:50 NY (20:50 UTC) to Tuesday 18:10 NY (22:10 UTC in EDT)
        entry_ts = pd.Timestamp("2021-06-15 20:50:00", tz="UTC")
        exit_ts = pd.Timestamp("2021-06-15 22:10:00", tz="UTC")

        # Long position: -0.12 $/oz
        rec_long = engine.calculate_swap_financing("LONG", entry_ts, exit_ts, position_size_oz=100.0)
        assert rec_long.rollover_count == 1
        assert rec_long.weighted_days == 1.0
        assert rec_long.swap_pnl_per_oz == -0.12
        assert rec_long.total_swap_pnl_usd == -12.0
        assert rec_long.swap_drag_per_oz == 0.12
        assert rec_long.total_swap_drag_usd == 12.0

        # Short position: -0.04 $/oz
        rec_short = engine.calculate_swap_financing("SHORT", entry_ts, exit_ts, position_size_oz=100.0)
        assert rec_short.rollover_count == 1
        assert rec_short.weighted_days == 1.0
        assert rec_short.swap_pnl_per_oz == -0.04
        assert rec_short.total_swap_pnl_usd == -4.0
        assert rec_short.swap_drag_per_oz == 0.04
        assert rec_short.total_swap_drag_usd == 4.0

    def test_wednesday_triple_swap(self):
        """Trade held across Wednesday 17:00 NY rollover incurs exactly 3.0 weighted days (triple swap)."""
        engine = OvernightSwapEngine(swap_rate_long=-0.12, swap_rate_short=-0.04)

        # Wednesday 16:50 NY (20:50 UTC) to Wednesday 18:10 NY (22:10 UTC in EDT)
        entry_ts = pd.Timestamp("2021-06-16 20:50:00", tz="UTC")
        exit_ts = pd.Timestamp("2021-06-16 22:10:00", tz="UTC")

        rec_long = engine.calculate_swap_financing("LONG", entry_ts, exit_ts, position_size_oz=100.0)
        assert rec_long.rollover_count == 1
        assert rec_long.weighted_days == 3.0  # Triple swap applied!
        assert rec_long.swap_pnl_per_oz == -0.36  # 3 * -0.12
        assert rec_long.total_swap_pnl_usd == -36.0
        assert rec_long.swap_drag_per_oz == 0.36
        assert rec_long.total_swap_drag_usd == 36.0

    def test_multi_day_holding_period(self):
        """Holding from Monday 10:00 NY to Friday 10:00 NY crosses Mon(1), Tue(1), Wed(3), Thu(1) = 6 days."""
        engine = OvernightSwapEngine(swap_rate_long=-0.12, swap_rate_short=-0.04)

        entry_ts = pd.Timestamp("2021-06-14 14:00:00", tz="UTC")  # Mon 10:00 NY
        exit_ts = pd.Timestamp("2021-06-18 14:00:00", tz="UTC")   # Fri 10:00 NY

        rec = engine.calculate_swap_financing("LONG", entry_ts, exit_ts, position_size_oz=100.0)
        assert rec.rollover_count == 4
        assert rec.weighted_days == 6.0  # 1 + 1 + 3 + 1 = 6.0
        assert rec.swap_pnl_per_oz == -0.72
        assert rec.total_swap_pnl_usd == -72.0

    def test_one_week_holding_period(self):
        """Holding 7 calendar days (Mon to next Mon) crosses 5 rollovers = 7.0 weighted days."""
        engine = OvernightSwapEngine(swap_rate_long=-0.12, swap_rate_short=-0.04)

        entry_ts = pd.Timestamp("2021-06-14 14:00:00", tz="UTC")  # Mon 10:00 NY
        exit_ts = pd.Timestamp("2021-06-21 14:00:00", tz="UTC")   # Mon 10:00 NY

        rec = engine.calculate_swap_financing("LONG", entry_ts, exit_ts, position_size_oz=100.0)
        assert rec.rollover_count == 5
        assert rec.weighted_days == 7.0  # Mon(1) + Tue(1) + Wed(3) + Thu(1) + Fri(1) = 7.0
        assert rec.swap_pnl_per_oz == -0.84
        assert rec.total_swap_pnl_usd == -84.0

    def test_unit_conversions(self):
        """Verify unit conversions across points, usd_per_lot, and annual_percentage."""
        entry_ts = pd.Timestamp("2021-06-15 20:50:00", tz="UTC")
        exit_ts = pd.Timestamp("2021-06-15 22:10:00", tz="UTC")

        # 1. points_per_day: -12.0 points @ $0.01/point = -$0.12/oz
        engine_points = OvernightSwapEngine(swap_rate_long=-12.0, rate_unit="points_per_day")
        rec_pts = engine_points.calculate_swap_financing("LONG", entry_ts, exit_ts, position_size_oz=100.0)
        assert rec_pts.rate_per_oz_day == -0.12
        assert rec_pts.total_swap_pnl_usd == -12.0

        # 2. usd_per_lot_day: -$12.00/lot / 100 oz = -$0.12/oz
        engine_lot = OvernightSwapEngine(swap_rate_long=-12.00, rate_unit="usd_per_lot_day")
        rec_lot = engine_lot.calculate_swap_financing("LONG", entry_ts, exit_ts, position_size_oz=100.0)
        assert rec_lot.rate_per_oz_day == -0.12
        assert rec_lot.total_swap_pnl_usd == -12.0

        # 3. annual_percentage: -2.5% p.a. on $1,800 gold: 1800 * (-0.025) / 360 = -$0.125/oz
        engine_annual = OvernightSwapEngine(swap_rate_long=-2.5, rate_unit="annual_percentage")
        rec_ann = engine_annual.calculate_swap_financing("LONG", entry_ts, exit_ts, position_size_oz=100.0, spot_price=1800.0)
        assert pytest.approx(rec_ann.rate_per_oz_day, rel=1e-3) == -0.125
        assert pytest.approx(rec_ann.total_swap_pnl_usd, rel=1e-3) == -12.50


# ==============================================================================
# 5. ACCOUNTING & INTEGRATION
# ==============================================================================

class TestAccountingAndIntegration:
    """Verify combined round-turn cost accounting and zero double-counting."""

    def test_calculate_round_turn_cost_integration(self):
        cost_model = ExecutionCostModel(
            base_spread_usd=0.20,
            base_slippage_usd=0.05,
            commission_per_lot_usd=5.0,  # $0.05/oz
        )

        # Entry on Monday 14:00 UTC (London/NY overlap, spread 0.20, slippage 0.05, comm 0.05 -> friction $0.30/oz)
        t_entry = pd.Timestamp("2021-06-14 14:00:00", tz="UTC")
        entry_exec = cost_model.simulate_execution("BUY", bid_price=1850.00, timestamp=t_entry)
        assert entry_exec.fill_price == 1850.25
        assert entry_exec.total_friction_per_oz == 0.30

        # Exit on Friday 14:00 UTC (4 rollovers = 6 weighted days -> swap $0.72/oz)
        t_exit = pd.Timestamp("2021-06-18 14:00:00", tz="UTC")
        exit_exec = cost_model.simulate_execution("SELL", bid_price=1880.00, timestamp=t_exit)
        assert exit_exec.fill_price == 1879.95
        assert exit_exec.total_friction_per_oz == 0.10  # slippage 0.05 + comm 0.05

        # Combined round turn:
        # Entry friction: $0.30/oz
        # Exit friction: $0.10/oz
        # Swap drag: $0.72/oz (6 days @ $0.12/day)
        # Total round-turn friction: $1.12/oz
        # For 1 standard lot (100 oz): $112.00
        rt = cost_model.calculate_round_turn_cost(entry_exec, exit_exec, position_size_oz=100.0)

        assert rt["direction"] == "LONG"
        assert rt["position_size_oz"] == 100.0
        assert rt["entry_friction_per_oz"] == 0.30
        assert rt["exit_friction_per_oz"] == 0.10
        assert rt["total_execution_friction_per_oz"] == 0.40
        assert rt["swap_drag_per_oz"] == 0.72
        assert rt["total_friction_per_oz"] == 1.12
        assert rt["total_friction_usd"] == 112.00
        assert rt["is_calibrated"] is False  # Confirmed assumption
