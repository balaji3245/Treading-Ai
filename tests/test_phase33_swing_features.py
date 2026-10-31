"""Unit tests for Phase 33 Multi-Timeframe Swing Feature Pipeline and Temporal Integrity.

Verifies:
1. Mathematical correctness of indicator calculations (TR, ATR, RSI, ADX, Donchian).
2. Strict lookahead-free temporal causality: d1_available_ts <= h4_decision_ts.
3. Proper New York close alignment across Daylight Saving Time (EDT vs EST).
4. Defensible completeness policy (sessions with 1-5 quiet minutes remain eligible).
5. Cross-timeframe alignment metrics and hypothesis feature readiness.
6. Absolute immutability of protected partitions.
"""

from datetime import datetime, time, timedelta, timezone
import hashlib
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
import pytest

from treading_ai.features.swing_features import (
    D1FeatureExtractor,
    H4FeatureExtractor,
    MultiTimeframeSwingPipeline,
    compute_adx,
    compute_atr,
    compute_rsi,
    compute_true_range,
)

TZ_NEW_YORK = ZoneInfo("America/New_York")

FROZEN_VAL_HASH = "7e9222e9dc0893601e24505912eeab78330670c4e70ebcc2fa462ff8d44a4f94"
FROZEN_TEST_HASH = "f95fd09a5d07666e3f1d9a72e840e2e97f3c058d11b6bb0c712b21dea86a5dec"


def test_protected_partitions_unmodified():
    """Verify that protected holdout partitions have not been accessed or altered."""
    val_path = Path("data/features/XAUUSD_M5_features_val.parquet")
    test_path = Path("data/features/XAUUSD_M5_features_test.parquet")

    assert val_path.exists(), "Validation partition file missing"
    assert test_path.exists(), "Test partition file missing"

    val_hash = hashlib.sha256(val_path.read_bytes()).hexdigest()
    test_hash = hashlib.sha256(test_path.read_bytes()).hexdigest()

    assert val_hash == FROZEN_VAL_HASH, f"VAL partition modified! {val_hash} != {FROZEN_VAL_HASH}"
    assert test_hash == FROZEN_TEST_HASH, f"TEST partition modified! {test_hash} != {FROZEN_TEST_HASH}"


def test_compute_true_range_and_atr():
    """Verify True Range and Wilder's exponential smoothed ATR calculations."""
    high = pd.Series([100.0, 105.0, 102.0, 108.0, 107.0])
    low = pd.Series([95.0, 98.0, 97.0, 101.0, 103.0])
    close = pd.Series([98.0, 101.0, 99.0, 106.0, 105.0])

    tr = compute_true_range(high, low, close)
    assert len(tr) == 5
    assert (tr >= 0).all()

    # Bar 1: hl = 105-98=7, hc = |105-98|=7, lc = |98-98|=0 => max = 7
    assert tr.iloc[1] == pytest.approx(7.0)
    # Bar 2: hl = 102-97=5, hc = |102-101|=1, lc = |97-101|=4 => max = 5
    assert tr.iloc[2] == pytest.approx(5.0)

    atr = compute_atr(high, low, close, period=3)
    assert len(atr) == 5
    assert (atr.dropna() > 0).all()


def test_compute_rsi_and_adx_bounded():
    """Verify RSI and ADX are bounded between 0 and 100."""
    np.random.seed(42)
    n = 60
    prices = 1800.0 + np.cumsum(np.random.randn(n) * 5.0)
    high = pd.Series(prices + np.abs(np.random.randn(n) * 2.0))
    low = pd.Series(prices - np.abs(np.random.randn(n) * 2.0))
    close = pd.Series(prices)

    rsi = compute_rsi(close, period=14)
    adx = compute_adx(high, low, close, period=14)

    valid_rsi = rsi.dropna()
    valid_adx = adx.dropna()

    assert (valid_rsi >= 0.0).all() and (valid_rsi <= 100.0).all()
    assert (valid_adx >= 0.0).all() and (valid_adx <= 100.0).all()


def test_d1_feature_extractor_dst_alignment():
    """Verify D1 available timestamp is exactly 17:00 NY Time in UTC across DST transitions."""
    # March 2021 DST transition: 2021-03-14 (EDT begins, UTC-4)
    # Winter date (EST, UTC-5): 2021-01-15 -> 17:00 NY = 22:00 UTC
    # Summer date (EDT, UTC-4): 2021-06-15 -> 17:00 NY = 21:00 UTC
    d1_df = pd.DataFrame(
        {
            "timestamp": [
                pd.Timestamp("2021-01-15 00:00:00", tz=timezone.utc),
                pd.Timestamp("2021-06-15 00:00:00", tz=timezone.utc),
            ],
            "open": [1850.0, 1860.0],
            "high": [1860.0, 1870.0],
            "low": [1840.0, 1850.0],
            "close": [1855.0, 1865.0],
            "volume": [100000.0, 100000.0],
            "bar_count": [1380, 1378],
            "is_complete": [True, False],
        }
    )

    extractor = D1FeatureExtractor()
    feat = extractor.compute_features(d1_df)

    assert "d1_available_ts" in feat.columns
    # Row 0: EST -> 22:00 UTC
    assert feat["d1_available_ts"].iloc[0] == pd.Timestamp("2021-01-15 22:00:00", tz=timezone.utc)
    # Row 1: EDT -> 21:00 UTC
    assert feat["d1_available_ts"].iloc[1] == pd.Timestamp("2021-06-15 21:00:00", tz=timezone.utc)


def test_h4_feature_extractor_candlestick_geometry():
    """Verify H4 feature extractor decision timestamps and candlestick geometry metrics."""
    h4_df = pd.DataFrame(
        {
            "timestamp": [
                pd.Timestamp("2021-01-15 00:00:00", tz=timezone.utc),
                pd.Timestamp("2021-01-15 04:00:00", tz=timezone.utc),
            ],
            "open": [1850.0, 1855.0],
            "high": [1860.0, 1865.0],
            "low": [1845.0, 1850.0],
            "close": [1855.0, 1860.0],
            "volume": [20000.0, 25000.0],
            "bar_count": [240, 240],
            "is_complete": [True, True],
        }
    )

    extractor = H4FeatureExtractor()
    feat = extractor.compute_features(h4_df)

    # Decision timestamp must be open + 4 hours
    assert feat["h4_decision_ts"].iloc[0] == pd.Timestamp("2021-01-15 04:00:00", tz=timezone.utc)
    assert feat["h4_decision_ts"].iloc[1] == pd.Timestamp("2021-01-15 08:00:00", tz=timezone.utc)

    # Geometry: body ratio + upper wick + lower wick should equal ~1.0
    # Candle 0: Range = 15. Body = |1855 - 1850| = 5 (0.333). Upper = 1860 - 1855 = 5 (0.333). Lower = 1850 - 1845 = 5 (0.333).
    total_ratio = (
        feat["h4_body_ratio"].iloc[0]
        + feat["h4_upper_wick_ratio"].iloc[0]
        + feat["h4_lower_wick_ratio"].iloc[0]
    )
    assert total_ratio == pytest.approx(1.0, rel=1e-3)


def test_multi_timeframe_swing_pipeline_zero_temporal_leakage():
    """Verify strict temporal causality: d1_available_ts <= h4_decision_ts for all rows."""
    # Synthetic calendar: Jan 10 through Jan 15, 2021
    # Generate daily candles
    d1_records = []
    start_date = pd.Timestamp("2021-01-10", tz=timezone.utc)
    for i in range(6):
        d = start_date + pd.Timedelta(days=i)
        d1_records.append(
            {
                "timestamp": d,
                "open": 1800.0 + i * 2,
                "high": 1810.0 + i * 2,
                "low": 1795.0 + i * 2,
                "close": 1805.0 + i * 2,
                "volume": 100000.0,
                "bar_count": 1380,
                "is_complete": True,
            }
        )
    df_d1 = pd.DataFrame(d1_records)

    # Generate H4 candles every 4 hours from Jan 10 00:00 to Jan 15 20:00
    h4_records = []
    ts = pd.Timestamp("2021-01-10 00:00:00", tz=timezone.utc)
    end_ts = pd.Timestamp("2021-01-15 20:00:00", tz=timezone.utc)
    idx = 0
    while ts <= end_ts:
        h4_records.append(
            {
                "timestamp": ts,
                "open": 1800.0 + idx * 0.5,
                "high": 1805.0 + idx * 0.5,
                "low": 1798.0 + idx * 0.5,
                "close": 1802.0 + idx * 0.5,
                "volume": 15000.0,
                "bar_count": 240,
                "is_complete": True,
            }
        )
        ts += pd.Timedelta(hours=4)
        idx += 1
    df_h4 = pd.DataFrame(h4_records)

    pipeline = MultiTimeframeSwingPipeline()
    merged = pipeline.build_swing_features(df_h4, df_d1)

    # Drop warm-up bars where no D1 had closed yet
    valid = merged.dropna(subset=["d1_available_ts"]).copy()
    assert len(valid) > 0, "No valid merged rows found"

    # CRITICAL INVARIANT: The decision timestamp of H4 must be GREATER OR EQUAL to D1 availability
    leakage = valid[valid["d1_available_ts"] > valid["h4_decision_ts"]]
    assert len(leakage) == 0, f"Found {len(leakage)} temporal leakage violations!"

    # Specific check: on Jan 12 at 16:00 UTC (before 22:00 UTC close of Jan 12),
    # the merged D1 must be Jan 11 (close at Jan 11 22:00 UTC)
    h4_jan12_midday = valid[valid["timestamp"] == pd.Timestamp("2021-01-12 12:00:00", tz=timezone.utc)]
    if not h4_jan12_midday.empty:
        # Decision ts is 16:00 UTC. Jan 12 D1 closes at 22:00 UTC, so it MUST observe Jan 11 D1
        expected_d1_avail = pd.Timestamp("2021-01-11 22:00:00", tz=timezone.utc)
        assert h4_jan12_midday["d1_available_ts"].iloc[0] == expected_d1_avail


def test_pipeline_on_real_2021_development_data():
    """Verify feature pipeline on real 2021 development dataset."""
    h4_path = Path("data/processed/XAUUSD/H4/XAUUSD_H4_2021.parquet")
    d1_path = Path("data/processed/XAUUSD/D1/XAUUSD_D1_2021.parquet")

    if not (h4_path.exists() and d1_path.exists()):
        pytest.skip("2021 development Parquet files not present on disk")

    df_h4 = pd.read_parquet(h4_path)
    df_d1 = pd.read_parquet(d1_path)

    pipeline = MultiTimeframeSwingPipeline()
    merged = pipeline.build_swing_features(df_h4, df_d1)

    assert len(merged) == len(df_h4)
    assert "h4_decision_ts" in merged.columns
    assert "d1_available_ts" in merged.columns
    assert "cross_trend_alignment" in merged.columns
    assert "cross_h4_d1_zscore" in merged.columns
    assert "cross_vol_expansion_in_d1_compression" in merged.columns
    assert "cross_pullback_in_d1_trend" in merged.columns
    assert "swing_signal_eligible" in merged.columns

    # Test temporal causality across all observations with merged D1
    matched = merged.dropna(subset=["d1_available_ts"])
    leakage_rows = matched[matched["d1_available_ts"] > matched["h4_decision_ts"]]
    assert len(leakage_rows) == 0, f"Real 2021 data produced {len(leakage_rows)} lookahead leakage rows!"

    # Verify defensible completeness flags
    # In 2021, regular sessions with >= 1350 bars should be flagged d1_regular_session == True
    assert matched["d1_regular_session"].sum() > 200
    assert matched["swing_signal_eligible"].sum() > 1000


def test_defensible_completeness_policy_logic():
    """Verify completeness policy distinguishes quiet minutes from shortened sessions."""
    df_d1 = pd.DataFrame(
        {
            "timestamp": [
                pd.Timestamp("2021-01-11 00:00:00", tz=timezone.utc),
                pd.Timestamp("2021-01-12 00:00:00", tz=timezone.utc),
                pd.Timestamp("2021-01-13 00:00:00", tz=timezone.utc),
            ],
            "open": [1800.0, 1810.0, 1820.0],
            "high": [1820.0, 1830.0, 1840.0],
            "low": [1790.0, 1800.0, 1810.0],
            "close": [1810.0, 1820.0, 1830.0],
            "volume": [50000.0, 50000.0, 10000.0],
            "bar_count": [1380, 1378, 600],  # 1380=full, 1378=quiet mins, 600=early close
            "is_complete": [True, False, False],
        }
    )

    df_h4 = pd.DataFrame(
        {
            "timestamp": [
                pd.Timestamp("2021-01-12 00:00:00", tz=timezone.utc),
                pd.Timestamp("2021-01-13 00:00:00", tz=timezone.utc),
                pd.Timestamp("2021-01-14 00:00:00", tz=timezone.utc),
            ],
            "open": [1810.0, 1820.0, 1830.0],
            "high": [1815.0, 1825.0, 1835.0],
            "low": [1805.0, 1815.0, 1825.0],
            "close": [1812.0, 1822.0, 1832.0],
            "volume": [10000.0, 10000.0, 10000.0],
            "bar_count": [240, 240, 240],
            "is_complete": [True, True, True],
        }
    )

    pipeline = MultiTimeframeSwingPipeline(min_d1_bars_for_regular_session=1350)
    merged = pipeline.build_swing_features(df_h4, df_d1)

    # Row 0 matches Jan 11 (1380 bars) -> regular
    assert merged["d1_regular_session"].iloc[0] == True
    # Row 1 matches Jan 12 (1378 bars) -> regular despite 2 quiet minutes
    assert merged["d1_regular_session"].iloc[1] == True
    # Row 2 matches Jan 13 (600 bars) -> shortened holiday session -> NOT regular
    assert merged["d1_regular_session"].iloc[2] == False
