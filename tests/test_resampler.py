"""Unit tests for TimeframeResampler engine."""

from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from treading_ai.preprocessing.resampler import TimeframeResampler


def test_resample_m1_to_m5_math(clean_synthetic_m1_df: pd.DataFrame):
    resampler = TimeframeResampler()
    df_m5 = resampler.resample_candle_series(clean_synthetic_m1_df, target_timeframe="M5")

    # 120 M1 candles should yield exactly 24 M5 candles (120 / 5)
    assert len(df_m5) == 24
    assert list(df_m5.columns) == ["timestamp", "open", "high", "low", "close", "volume", "bar_count", "is_complete"]

    # Verify first 5-minute candle against first 5 M1 candles
    m1_first_5 = clean_synthetic_m1_df.iloc[:5]
    first_m5 = df_m5.iloc[0]

    assert first_m5["timestamp"] == m1_first_5.iloc[0]["timestamp"]
    assert first_m5["open"] == m1_first_5.iloc[0]["open"]
    assert first_m5["high"] == m1_first_5["high"].max()
    assert first_m5["low"] == m1_first_5["low"].min()
    assert first_m5["close"] == m1_first_5.iloc[-1]["close"]
    assert pytest.approx(first_m5["volume"]) == m1_first_5["volume"].sum()
    assert first_m5["bar_count"] == 5
    assert first_m5["is_complete"] is True or first_m5["is_complete"] == 1


def test_resample_all_timeframes(clean_synthetic_m1_df: pd.DataFrame):
    resampler = TimeframeResampler(target_timeframes=["M5", "M15", "M30", "H1"])
    multi_tf = resampler.resample_all_timeframes(clean_synthetic_m1_df)

    assert "M1" in multi_tf
    assert "M5" in multi_tf
    assert "M15" in multi_tf
    assert "M30" in multi_tf
    assert "H1" in multi_tf

    assert len(multi_tf["M1"]) == 120
    assert len(multi_tf["M5"]) == 24
    assert len(multi_tf["M15"]) == 8  # 120 / 15
    assert len(multi_tf["M30"]) == 4  # 120 / 30
    assert len(multi_tf["H1"]) == 2   # 120 / 60


def test_incomplete_candle_detection():
    # Only 3 candles inside a 5-minute bucket: 10:00, 10:01, 10:02 (missing 10:03, 10:04)
    start = datetime(2026, 1, 7, 10, 0, 0, tzinfo=timezone.utc)
    timestamps = [start + timedelta(minutes=i) for i in range(3)]
    df_partial = pd.DataFrame({
        "timestamp": timestamps,
        "open": [2650.0, 2651.0, 2652.0],
        "high": [2651.0, 2652.0, 2653.0],
        "low": [2649.5, 2650.5, 2651.5],
        "close": [2651.0, 2652.0, 2652.5],
        "volume": [10.0, 20.0, 30.0],
    })

    resampler = TimeframeResampler()
    df_m5 = resampler.resample_candle_series(df_partial, target_timeframe="M5")

    assert len(df_m5) == 1
    candle = df_m5.iloc[0]
    assert candle["bar_count"] == 3
    assert candle["is_complete"] is False or candle["is_complete"] == 0
    assert candle["open"] == 2650.0
    assert candle["close"] == 2652.5


def test_no_fabrication_on_empty_periods():
    # Two isolated candles separated by 2 hours
    t1 = datetime(2026, 1, 7, 10, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 1, 7, 12, 0, 0, tzinfo=timezone.utc)
    df_isolated = pd.DataFrame({
        "timestamp": [t1, t2],
        "open": [2650.0, 2660.0],
        "high": [2651.0, 2661.0],
        "low": [2649.0, 2659.0],
        "close": [2650.5, 2660.5],
        "volume": [10.0, 15.0],
    })

    resampler = TimeframeResampler()
    df_h1 = resampler.resample_candle_series(df_isolated, target_timeframe="H1")

    # Should only produce 2 H1 candles (for 10:00 and 12:00), NOT a fabricated 11:00 candle
    assert len(df_h1) == 2
    assert df_h1.iloc[0]["timestamp"] == t1
    assert df_h1.iloc[1]["timestamp"] == t2


def test_invalid_timeframe_raises():
    resampler = TimeframeResampler()
    df_dummy = pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])
    with pytest.raises(ValueError, match="Unsupported timeframe"):
        resampler.resample_candle_series(df_dummy, target_timeframe="D2")


def test_h4_session_vs_utc_alignment():
    # 24 hours of data spanning Monday 00:00 to 23:59 UTC
    start = datetime(2026, 1, 5, 0, 0, 0, tzinfo=timezone.utc)
    timestamps = [start + timedelta(minutes=i) for i in range(1440)]
    df_day = pd.DataFrame({
        "timestamp": timestamps,
        "open": [2600.0] * 1440,
        "high": [2605.0] * 1440,
        "low": [2595.0] * 1440,
        "close": [2601.0] * 1440,
        "volume": [10.0] * 1440,
    })

    # Session aligned H4 (offset 2h): bins anchored at 22:00, 02:00, 06:00, 10:00, 14:00, 18:00
    resampler_session = TimeframeResampler(h4_alignment="session")
    df_session_h4 = resampler_session.resample_candle_series(df_day, "H4")
    session_hours = [t.hour for t in df_session_h4["timestamp"]]
    # Should contain hours matching offset 2h (2, 6, 10, 14, 18, 22)
    assert 18 in session_hours
    assert 22 in session_hours

    # Standard UTC H4: bins anchored at 00:00, 04:00, 08:00, 12:00, 16:00, 20:00
    resampler_utc = TimeframeResampler(h4_alignment="utc")
    df_utc_h4 = resampler_utc.resample_candle_series(df_day, "H4")
    utc_hours = [t.hour for t in df_utc_h4["timestamp"]]
    assert 0 in utc_hours
    assert 20 in utc_hours


def test_no_lookahead_leakage():
    """Verify that higher timeframe bars contain only constituent candles within [T, T + timeframe)
    and strictly do NOT leak prices from future candles at T + timeframe."""
    start = datetime(2026, 1, 5, 10, 0, 0, tzinfo=timezone.utc)
    # Create 10 M1 candles (10:00 to 10:09)
    timestamps = [start + timedelta(minutes=i) for i in range(10)]
    df = pd.DataFrame({
        "timestamp": timestamps,
        "open": [2000.0] * 10,
        "high": [2005.0] * 10,
        "low": [1995.0] * 10,
        "close": [2000.0] * 10,
        "volume": [10.0] * 10,
    })
    # Inject a distinct spike at 10:05 (the exact start of the second M5 bar)
    # The first M5 bar (10:00 to 10:04) must NOT see this spike!
    df.loc[5, "high"] = 9999.0
    df.loc[5, "close"] = 9990.0

    resampler = TimeframeResampler()
    df_m5 = resampler.resample_candle_series(df, "M5")

    assert len(df_m5) == 2
    bar_10_00 = df_m5.iloc[0]
    bar_10_05 = df_m5.iloc[1]

    # Bar 10:00 must NOT have the 9999 spike (no future lookahead)
    assert bar_10_00["timestamp"] == pd.Timestamp("2026-01-05 10:00:00", tz="UTC")
    assert bar_10_00["high"] == 2005.0
    assert bar_10_00["close"] == 2000.0

    # Bar 10:05 MUST have the spike
    assert bar_10_05["timestamp"] == pd.Timestamp("2026-01-05 10:05:00", tz="UTC")
    assert bar_10_05["high"] == 9999.0
    assert bar_10_05["open"] == 2000.0


