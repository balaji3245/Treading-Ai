"""Tests for technical feature extraction engine.

Verifies mathematical correctness, stationary scaling, bounds, and numerical safety
of returns, volatility, ATR, trend indicators, and momentum oscillators.
"""

from datetime import datetime, timedelta, timezone
import numpy as np
import pandas as pd
import pytest

from treading_ai.features.technical import TechnicalFeatureExtractor


@pytest.fixture
def sample_ohlcv_df() -> pd.DataFrame:
    """Generate 100 bars of deterministic OHLCV data."""
    start = datetime(2025, 1, 6, 10, 0, 0, tzinfo=timezone.utc)
    timestamps = [start + timedelta(minutes=5 * i) for i in range(100)]
    
    # Simple deterministic synthetic series around 2600
    np.random.seed(42)
    closes = 2600.0 + np.cumsum(np.random.normal(0, 1.0, 100))
    opens = np.roll(closes, 1)
    opens[0] = 2600.0
    highs = np.maximum(opens, closes) + np.abs(np.random.normal(0.5, 0.2, 100))
    lows = np.minimum(opens, closes) - np.abs(np.random.normal(0.5, 0.2, 100))
    volumes = np.random.uniform(50, 200, 100)

    return pd.DataFrame({
        "timestamp": timestamps,
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes,
    })


class TestTechnicalFeatureExtractor:
    """Unit tests for TechnicalFeatureExtractor."""

    def test_compute_returns(self, sample_ohlcv_df: pd.DataFrame):
        extractor = TechnicalFeatureExtractor(return_periods=[1, 5, 10])
        ret_df = extractor.compute_returns(sample_ohlcv_df)

        # Check multi-horizon simple and log returns
        assert "ret_1" in ret_df.columns
        assert "ret_5" in ret_df.columns
        assert "log_ret_1" in ret_df.columns
        assert "log_ret_5" in ret_df.columns

        # Verify math for ret_1 and log_ret_1 on row 10
        expected_ret_1 = (sample_ohlcv_df["close"].iloc[10] - sample_ohlcv_df["close"].iloc[9]) / sample_ohlcv_df["close"].iloc[9]
        expected_log_ret_1 = np.log(sample_ohlcv_df["close"].iloc[10] / sample_ohlcv_df["close"].iloc[9])

        assert pytest.approx(ret_df["ret_1"].iloc[10], rel=1e-6) == expected_ret_1
        assert pytest.approx(ret_df["log_ret_1"].iloc[10], rel=1e-6) == expected_log_ret_1

        # Check candlestick geometry
        assert "candle_return" in ret_df.columns
        assert "candle_span" in ret_df.columns
        assert "log_hl_ratio" in ret_df.columns
        assert "body_to_range" in ret_df.columns
        assert (ret_df["body_to_range"].dropna() >= 0.0).all()
        assert (ret_df["body_to_range"].dropna() <= 1.0 + 1e-6).all()

    def test_compute_volatility(self, sample_ohlcv_df: pd.DataFrame):
        extractor = TechnicalFeatureExtractor(volatility_windows=[5, 15, 30])
        vol_df = extractor.compute_volatility(sample_ohlcv_df)

        # Verify rolling std, parkinson, and garman-klass columns exist
        assert "volatility_5" in vol_df.columns
        assert "volatility_15" in vol_df.columns
        assert "volatility_30" in vol_df.columns
        assert "parkinson_vol_15" in vol_df.columns
        assert "garman_klass_vol_15" in vol_df.columns

        # Volatility must be non-negative
        assert (vol_df["volatility_15"].dropna() >= 0.0).all()
        assert (vol_df["parkinson_vol_15"].dropna() >= 0.0).all()
        assert (vol_df["garman_klass_vol_15"].dropna() >= 0.0).all()

    def test_compute_atr_and_natr(self, sample_ohlcv_df: pd.DataFrame):
        extractor = TechnicalFeatureExtractor(atr_windows=[7, 14])
        atr_df = extractor.compute_atr(sample_ohlcv_df)

        assert "true_range" in atr_df.columns
        assert "atr_14" in atr_df.columns
        assert "natr_14" in atr_df.columns

        # True range must be >= (High - Low)
        hl_diff = sample_ohlcv_df["high"] - sample_ohlcv_df["low"]
        assert (atr_df["true_range"] >= hl_diff - 1e-9).all()

        # ATR and NATR must be positive
        assert (atr_df["atr_14"].dropna() > 0.0).all()
        assert (atr_df["natr_14"].dropna() > 0.0).all()

        # NATR should be roughly ATR / Close
        expected_natr_last = atr_df["atr_14"].iloc[-1] / sample_ohlcv_df["close"].iloc[-1]
        assert pytest.approx(atr_df["natr_14"].iloc[-1], rel=1e-5) == expected_natr_last

    def test_compute_trend(self, sample_ohlcv_df: pd.DataFrame):
        extractor = TechnicalFeatureExtractor(ema_periods=[9, 21, 50])
        trend_df = extractor.compute_trend(sample_ohlcv_df)

        assert "dist_ema_9" in trend_df.columns
        assert "dist_ema_21" in trend_df.columns
        assert "ema_slope_9" in trend_df.columns
        assert "ema_ratio_9_21" in trend_df.columns

        # Distances and slopes should be stationary percentage measures (typically between -0.1 and 0.1)
        valid_dist = trend_df["dist_ema_9"].dropna()
        assert (valid_dist.abs() < 0.1).all()

    def test_compute_momentum(self, sample_ohlcv_df: pd.DataFrame):
        extractor = TechnicalFeatureExtractor(rsi_period=14, macd_fast=12, macd_slow=26, macd_signal=9)
        mom_df = extractor.compute_momentum(sample_ohlcv_df)

        assert "rsi_14" in mom_df.columns
        assert "rsi_14_norm" in mom_df.columns
        assert "macd_norm" in mom_df.columns
        assert "macd_signal_norm" in mom_df.columns
        assert "macd_hist_norm" in mom_df.columns
        assert "bb_pct_b" in mom_df.columns
        assert "bb_bandwidth" in mom_df.columns

        # RSI must be strictly bounded in [0, 100]
        valid_rsi = mom_df["rsi_14"].dropna()
        assert (valid_rsi >= 0.0).all() and (valid_rsi <= 100.0).all()

        # Normalized RSI in [-1, 1]
        valid_rsi_norm = mom_df["rsi_14_norm"].dropna()
        assert (valid_rsi_norm >= -1.0).all() and (valid_rsi_norm <= 1.0).all()

        # Bollinger bandwidth must be non-negative
        valid_bw = mom_df["bb_bandwidth"].dropna()
        assert (valid_bw >= 0.0).all()

    def test_scale_stationarity(self, sample_ohlcv_df: pd.DataFrame):
        """Scaling the price level by 2x should preserve scale-free features."""
        extractor = TechnicalFeatureExtractor(
            return_periods=[1, 5],
            volatility_windows=[15],
            atr_windows=[14],
            ema_periods=[9, 21],
            rsi_period=14,
        )

        df1 = sample_ohlcv_df.copy()
        df2 = sample_ohlcv_df.copy()
        for col in ["open", "high", "low", "close"]:
            df2[col] = df2[col] * 2.0

        f1 = extractor.extract_all(df1)
        f2 = extractor.extract_all(df2)

        # Invariant features:
        # - returns and log returns
        # - normalized atr (natr)
        # - distance from EMA
        # - RSI and normalized RSI
        # - BB %B and bandwidth
        for col in ["ret_1", "log_ret_1", "natr_14", "dist_ema_9", "rsi_14", "rsi_14_norm", "bb_pct_b", "bb_bandwidth"]:
            s1 = f1[col].dropna()
            s2 = f2[col].dropna()
            np.testing.assert_allclose(s1.values, s2.values, rtol=1e-5, atol=1e-6)
