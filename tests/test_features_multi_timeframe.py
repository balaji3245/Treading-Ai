"""Tests for Multi-timeframe alignment engine.

Verifies mathematical causality and strict zero-lookahead guarantees:
HTF candles must NEVER be exposed to LTF records before the HTF candle has closed.
"""

from datetime import datetime, timedelta, timezone
import pandas as pd
import pytest

from treading_ai.features.multi_timeframe import MultiTimeframeAligner


class TestMultiTimeframeAligner:
    """Unit tests for MultiTimeframeAligner."""

    def test_strict_temporal_causality_m5_to_h1(self):
        # Create M5 candles from 09:00 to 12:00 (36 bars)
        t_start = datetime(2025, 5, 7, 9, 0, 0, tzinfo=timezone.utc)
        m5_timestamps = [t_start + timedelta(minutes=5 * i) for i in range(36)]
        m5_df = pd.DataFrame({
            "timestamp": m5_timestamps,
            "close": [2600.0 + i for i in range(36)],
        })

        # Create H1 candles for 09:00, 10:00, 11:00
        # 09:00 bar closes at 10:00
        # 10:00 bar closes at 11:00
        # 11:00 bar closes at 12:00
        h1_timestamps = [
            datetime(2025, 5, 7, 9, 0, 0, tzinfo=timezone.utc),
            datetime(2025, 5, 7, 10, 0, 0, tzinfo=timezone.utc),
            datetime(2025, 5, 7, 11, 0, 0, tzinfo=timezone.utc),
        ]
        h1_df = pd.DataFrame({
            "timestamp": h1_timestamps,
            "rsi_14": [30.0, 50.0, 70.0],  # Distinct feature values
            "trend_signal": [1, 2, 3],
        })

        aligner = MultiTimeframeAligner(ltf_timeframe="M5")
        aligned = aligner.align_htf_features(
            ltf_df=m5_df,
            htf_df=h1_df,
            htf_timeframe="H1",
        )

        assert "htf_h1_rsi_14" in aligned.columns
        assert "htf_h1_trend_signal" in aligned.columns

        # CAUSALITY ASSERTIONS:
        # 1. During [09:00, 10:00): The 09:00 H1 bar has NOT closed yet!
        # There was no prior H1 bar in h1_df, so all M5 bars from 09:00 to 09:55 must have NaN for HTF features.
        bars_09_to_10 = aligned[aligned["timestamp"] < datetime(2025, 5, 7, 10, 0, 0, tzinfo=timezone.utc)]
        assert len(bars_09_to_10) == 12
        assert bars_09_to_10["htf_h1_rsi_14"].isna().all(), "M5 bars before 10:00 saw an unclosed H1 bar!"

        # 2. During [10:00, 11:00): The 09:00 H1 bar closed at 10:00:00.
        # So all M5 bars from 10:00 to 10:55 must see the 09:00 H1 bar (rsi_14=30.0, trend_signal=1).
        # They MUST NOT see the 10:00 H1 bar (which only closes at 11:00:00)!
        bars_10_to_11 = aligned[
            (aligned["timestamp"] >= datetime(2025, 5, 7, 10, 0, 0, tzinfo=timezone.utc))
            & (aligned["timestamp"] < datetime(2025, 5, 7, 11, 0, 0, tzinfo=timezone.utc))
        ]
        assert len(bars_10_to_11) == 12
        assert (bars_10_to_11["htf_h1_rsi_14"] == 30.0).all(), "M5 bars in [10:00, 11:00) leaked 10:00 H1 features!"
        assert (bars_10_to_11["htf_h1_trend_signal"] == 1).all()

        # 3. During [11:00, 12:00): The 10:00 H1 bar closed at 11:00:00.
        # Now and only now do M5 bars see the 10:00 H1 bar (rsi_14=50.0, trend_signal=2).
        bars_11_to_12 = aligned[aligned["timestamp"] >= datetime(2025, 5, 7, 11, 0, 0, tzinfo=timezone.utc)]
        assert len(bars_11_to_12) == 12
        assert (bars_11_to_12["htf_h1_rsi_14"] == 50.0).all(), "M5 bars starting at 11:00 should see the closed 10:00 H1 bar!"
        assert (bars_11_to_12["htf_h1_trend_signal"] == 2).all()

    def test_invalid_timeframe_durations(self):
        # M15 cannot be HTF for M30
        aligner = MultiTimeframeAligner(ltf_timeframe="M30")
        df_ltf = pd.DataFrame({"timestamp": [datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)]})
        df_htf = pd.DataFrame({"timestamp": [datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)], "feat": [1]})

        with pytest.raises(ValueError, match="must be strictly greater than"):
            aligner.align_htf_features(df_ltf, df_htf, htf_timeframe="M15")

        with pytest.raises(ValueError, match="must be strictly greater than"):
            aligner.align_htf_features(df_ltf, df_htf, htf_timeframe="M30")
