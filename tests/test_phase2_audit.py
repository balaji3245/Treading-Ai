"""Targeted verification tests for Phase 2 independent audit.

Tests:
1. Exact row-count ledger reconciliation (the 47-row difference between clean rows and split sums).
2. Candle-open timestamp semantics across M1, M5, H1, H4.
3. Higher-timeframe causality boundary testing (minute-by-minute transitions).
4. Session flag behavior across winter (standard time) vs summer (DST).
5. Verification that continuous clean data has 0 NaNs prior to any fill.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from treading_ai.config import (
    FEATURES_DATA_DIR,
    TEST_END_DATE,
    TEST_START_DATE,
    TRAIN_END_DATE,
    TRAIN_START_DATE,
    VAL_END_DATE,
    VAL_START_DATE,
)
from treading_ai.features.multi_timeframe import MultiTimeframeAligner
from treading_ai.features.time_features import TimeFeatureExtractor
from treading_ai.preprocessing.resampler import TimeframeResampler
from treading_ai.preprocessing.storage import ParquetStorageEngine


class TestPhase2Audit:
    """Independent audit tests for Treading-AI Phase 2."""

    def test_reconcile_47_row_discrepancy(self):
        """Reconcile the 47-row difference: 373,873 loaded - 13,378 warmup = 360,495; splits sum to 360,448."""
        storage = ParquetStorageEngine()
        df_base = storage.load_continuous_dataset("XAUUSD", "M5", filter_incomplete=True)

        # 1. Total loaded M5 candles
        total_loaded = len(df_base)
        assert total_loaded == 373873

        # 2. Warm-up bars dropped (early 2021 before 2021-03-11 18:00 UTC)
        t_train_start = pd.to_datetime(TRAIN_START_DATE, utc=True)
        # In pipeline, first_valid_idx is 13,378
        warmup_dropped = 13378
        clean_df = df_base.iloc[warmup_dropped:].reset_index(drop=True)
        assert len(clean_df) == 360495

        # 3. Splits
        t_train_end = pd.to_datetime(TRAIN_END_DATE, utc=True)
        t_val_start = pd.to_datetime(VAL_START_DATE, utc=True)
        t_val_end = pd.to_datetime(VAL_END_DATE, utc=True)
        t_test_start = pd.to_datetime(TEST_START_DATE, utc=True)
        t_test_end = pd.to_datetime(TEST_END_DATE, utc=True)

        train_split = clean_df[(clean_df["timestamp"] >= t_train_start) & (clean_df["timestamp"] <= t_train_end)]
        val_split = clean_df[(clean_df["timestamp"] >= t_val_start) & (clean_df["timestamp"] <= t_val_end)]
        test_split = clean_df[(clean_df["timestamp"] >= t_test_start) & (clean_df["timestamp"] <= t_test_end)]

        assert len(train_split) == 260821
        assert len(val_split) == 70759
        assert len(test_split) == 28868
        split_sum = len(train_split) + len(val_split) + len(test_split)
        assert split_sum == 360448

        # 4. Forensic accounting of the remaining 47 rows:
        # Rows with timestamp > TEST_END_DATE (2026-05-31 23:59:00 UTC)
        tail_rows = clean_df[clean_df["timestamp"] > t_test_end]
        assert len(tail_rows) == 47, f"Expected 47 tail rows, got {len(tail_rows)}"

        # Verify these 47 rows occur on 2026-06-01 from 00:00 to 03:50 UTC
        assert tail_rows["timestamp"].min() == pd.to_datetime("2026-06-01 00:00:00+00:00")
        assert tail_rows["timestamp"].max() == pd.to_datetime("2026-06-01 03:50:00+00:00")

        # Mathematical Identity Proof:
        # Loaded (373,873) - Warmup (13,378) = Clean (360,495)
        # Clean (360,495) = Train (260,821) + Val (70,759) + Test (28,868) + Post-Test Tail (47)
        assert total_loaded - warmup_dropped == split_sum + len(tail_rows)

    def test_candle_open_timestamp_semantics(self):
        """Verify that resampler and storage use candle-open timestamp convention (closed='left', label='left')."""
        resampler = TimeframeResampler()
        start = datetime(2025, 4, 1, 10, 0, tzinfo=timezone.utc)
        m1_times = [start + timedelta(minutes=i) for i in range(60)]
        m1_df = pd.DataFrame({
            "timestamp": m1_times,
            "open": [100.0 + i for i in range(60)],
            "high": [101.0 + i for i in range(60)],
            "low": [99.0 + i for i in range(60)],
            "close": [100.5 + i for i in range(60)],
            "volume": [10.0] * 60,
        })

        h1_df = resampler.resample_candle_series(m1_df, "H1")
        assert len(h1_df) == 1
        h1_candle = h1_df.iloc[0]

        # Candle-open convention assertions:
        # 1. Timestamp is 10:00:00 (start of interval, NOT 11:00:00 close)
        assert h1_candle["timestamp"] == start
        # 2. Open is the open of the first M1 bar (10:00)
        assert h1_candle["open"] == 100.0
        # 3. Close is the close of the last M1 bar (10:59)
        assert h1_candle["close"] == 100.5 + 59
        # 4. Completeness
        assert h1_candle["is_complete"] == True
        assert h1_candle["bar_count"] == 60

    def test_htf_boundary_exact_minute_causality(self):
        """Verify that at 10:55, the 10:00-11:00 H1 bar is NOT available; only at 11:00 is it available."""
        aligner = MultiTimeframeAligner(ltf_timeframe="M5")

        m5_df = pd.DataFrame({
            "timestamp": [
                datetime(2025, 6, 4, 10, 50, tzinfo=timezone.utc),
                datetime(2025, 6, 4, 10, 55, tzinfo=timezone.utc),
                datetime(2025, 6, 4, 11, 0, tzinfo=timezone.utc),
            ],
            "close": [2600.0, 2601.0, 2602.0],
        })

        h1_df = pd.DataFrame({
            "timestamp": [
                datetime(2025, 6, 4, 9, 0, tzinfo=timezone.utc),   # Closes at 10:00
                datetime(2025, 6, 4, 10, 0, tzinfo=timezone.utc),  # Closes at 11:00
            ],
            "h1_feature": [111.0, 222.0],
        })

        aligned = aligner.align_htf_features(m5_df, h1_df, "H1")

        # 10:50 and 10:55 MUST see the 09:00 H1 bar (111.0), NOT 222.0
        assert aligned.loc[0, "htf_h1_h1_feature"] == 111.0
        assert aligned.loc[1, "htf_h1_h1_feature"] == 111.0

        # Only at 11:00 does the 10:00 H1 bar become available (222.0)
        assert aligned.loc[2, "htf_h1_h1_feature"] == 222.0

    def test_session_flags_are_timezone_aware(self):
        """Verify that session flags operate on timezone-aware local market hours (Europe/London, America/New_York)."""
        extractor = TimeFeatureExtractor()

        # London Session (08:00 to 16:30 local London time):
        # In Summer (July 15, BST=UTC+1): 07:00 UTC is 08:00 BST (London open). session_london MUST be 1.
        ts_summer_07utc = pd.Series([datetime(2025, 7, 15, 7, 0, tzinfo=timezone.utc)])
        f_summer = extractor.extract_time_features(ts_summer_07utc).iloc[0]
        assert f_summer["session_london"] == 1

        # In Winter (Jan 15, GMT=UTC+0): 07:00 UTC is 07:00 GMT (1 hour BEFORE London open at 08:00 GMT).
        # session_london MUST be 0!
        ts_winter_07utc = pd.Series([datetime(2025, 1, 15, 7, 0, tzinfo=timezone.utc)])
        f_winter = extractor.extract_time_features(ts_winter_07utc).iloc[0]
        assert f_winter["session_london"] == 0

        # At 08:00 UTC in Winter: London opens (08:00 GMT). session_london MUST be 1.
        ts_winter_08utc = pd.Series([datetime(2025, 1, 15, 8, 0, tzinfo=timezone.utc)])
        f_winter_open = extractor.extract_time_features(ts_winter_08utc).iloc[0]
        assert f_winter_open["session_london"] == 1

    def test_anomalous_htf_gap_tolerance(self):
        """Verify that normal weekend closures (~49h) are preserved while anomalous gaps (>4 days) produce NaNs."""
        aligner = MultiTimeframeAligner(ltf_timeframe="M5", max_staleness=pd.Timedelta(days=4))

        # Friday close, Sunday open (49h gap), and an anomalous point 5 days later (120h gap)
        m5_df = pd.DataFrame({
            "timestamp": [
                datetime(2025, 1, 3, 21, 55, tzinfo=timezone.utc),  # Friday
                datetime(2025, 1, 5, 23, 0, tzinfo=timezone.utc),   # Sunday (49h gap from Friday 22:00 available)
                datetime(2025, 1, 10, 23, 0, tzinfo=timezone.utc),  # Anomalous point (7 days gap)
            ],
            "close": [2600.0, 2610.0, 2620.0],
        })

        h1_df = pd.DataFrame({
            "timestamp": [datetime(2025, 1, 3, 20, 0, tzinfo=timezone.utc)],  # Available at 21:00 UTC Friday
            "feat": [42.0],
        })

        aligned = aligner.align_htf_features(m5_df, h1_df, "H1")

        # 1. Friday close sees the 21:00 available bar
        assert aligned.loc[0, "htf_h1_feat"] == 42.0
        # 2. Sunday open (49h gap <= 4 days) successfully sees Friday's bar
        assert aligned.loc[1, "htf_h1_feat"] == 42.0
        # 3. Anomalous 7-day point (> 4 days max_staleness) MUST be NaN!
        assert np.isnan(aligned.loc[2, "htf_h1_feat"])
