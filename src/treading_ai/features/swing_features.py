"""Multi-Timeframe Swing Feature Engineering Pipeline.

Computes strictly causal, lookahead-free H4 and D1 quantitative features
designed for multi-day swing research in spot gold (XAUUSD).

Core Invariants:
1. Decision Causality: All features for decision instant T (e.g. close of H4 bar t)
   use information finalized strictly on or before T.
2. D1 Session Alignment: A D1 bar for session date D closes at 17:00:00 New York Time
   (21:00 or 22:00 UTC) on date D. H4 bars prior to 17:00 NY merge strictly with the
   completed D-1 session.
3. Scale Invariance & Stationarity: Returns, ATR percentages, Z-scores, and normalized
   pullback metrics are scale-invariant.
4. Defensible Completeness Policy: Separates genuine data dropouts from regular sessions
   with 1-5 quiet minutes (bar_count >= 1350).
"""

from datetime import datetime, time, timedelta, timezone
import logging
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from treading_ai.config import TIMEFRAME_M1_COUNT

logger = logging.getLogger(__name__)

TZ_NEW_YORK = ZoneInfo("America/New_York")


def compute_true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    """Compute standard True Range: max(H - L, |H - C_prev|, |L - C_prev|)."""
    prev_close = close.shift(1)
    hl = high - low
    hc = (high - prev_close).abs()
    lc = (low - prev_close).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    return tr


def compute_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Compute Average True Range using Wilder's exponential smoothing."""
    tr = compute_true_range(high, low, close)
    # Wilder's smoothing alpha = 1 / period
    atr = tr.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    return atr


def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Compute standard Relative Strength Index (RSI)."""
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / (avg_loss + 1e-10)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi


def compute_adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Compute Average Directional Index (ADX) measuring trend strength."""
    tr = compute_true_range(high, low, close)
    atr = tr.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

    up_move = high - high.shift(1)
    down_move = low.shift(1) - low

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    plus_dm_s = pd.Series(plus_dm, index=high.index).ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    minus_dm_s = pd.Series(minus_dm, index=high.index).ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

    plus_di = 100.0 * (plus_dm_s / (atr + 1e-10))
    minus_di = 100.0 * (minus_dm_s / (atr + 1e-10))

    dx = 100.0 * ((plus_di - minus_di).abs() / (plus_di + minus_di + 1e-10))
    adx = dx.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    return adx


class D1FeatureExtractor:
    """Computes daily macroeconomic and structural features from D1 candles."""

    def __init__(self, eps: float = 1e-8):
        self.eps = eps

    def compute_features(self, df_d1: pd.DataFrame) -> pd.DataFrame:
        """Extract stationary, lookahead-free Daily features with explicit close timestamps.

        Parameters
        ----------
        df_d1 : pd.DataFrame
            Daily OHLC DataFrame indexed or containing 'timestamp' (UTC 00:00:00 of session date).

        Returns
        -------
        pd.DataFrame
            DataFrame containing all D1 features and 'd1_available_ts' indicating the
            exact UTC timestamp when the D1 session finalized (17:00 NY Time).
        """
        df = df_d1.sort_values("timestamp").reset_index(drop=True).copy()

        # Compute exact session close timestamp in UTC (17:00:00 America/New_York)
        avail_ts: List[pd.Timestamp] = []
        for ts in df["timestamp"]:
            session_date = ts.date()
            close_ny = pd.Timestamp.combine(session_date, time(17, 0)).tz_localize(TZ_NEW_YORK)
            close_utc = close_ny.tz_convert(timezone.utc)
            avail_ts.append(close_utc)
        df["d1_available_ts"] = avail_ts

        close = df["close"]
        high = df["high"]
        low = df["low"]

        # 1. Multi-Day Lagged Returns
        df["d1_ret_1"] = close.pct_change(1)
        df["d1_ret_3"] = close.pct_change(3)
        df["d1_ret_5"] = close.pct_change(5)
        df["d1_ret_10"] = close.pct_change(10)

        # 2. Moving Average Trend Structure
        df["d1_ema_10"] = close.ewm(span=10, adjust=False).mean()
        df["d1_ema_20"] = close.ewm(span=20, adjust=False).mean()
        df["d1_ema_50"] = close.ewm(span=50, adjust=False).mean()

        # Trend regime: +1 bullish (EMA20 > EMA50), -1 bearish (EMA20 < EMA50)
        df["d1_trend_regime"] = np.where(
            df["d1_ema_20"] > df["d1_ema_50"], 1, np.where(df["d1_ema_20"] < df["d1_ema_50"], -1, 0)
        )
        # 20-day EMA slope over 5 days
        df["d1_trend_slope_20"] = (df["d1_ema_20"] - df["d1_ema_20"].shift(5)) / (df["d1_ema_20"].shift(5) + self.eps)

        # 3. Volatility & Regimes
        df["d1_tr"] = compute_true_range(high, low, close)
        df["d1_atr_14"] = compute_atr(high, low, close, period=14)
        df["d1_atr_pct"] = df["d1_atr_14"] / (close + self.eps)
        df["d1_atr_10"] = compute_atr(high, low, close, period=10)
        df["d1_atr_50"] = compute_atr(high, low, close, period=50)

        # Volatility Compression Ratio (low value = compressed regime)
        df["d1_vol_compression_ratio"] = df["d1_atr_10"] / (df["d1_atr_50"] + self.eps)

        # 20-day rolling standard deviation
        df["d1_rolling_std_20"] = close.rolling(window=20, min_periods=20).std()

        # 4. Trend Strength (ADX)
        df["d1_adx_14"] = compute_adx(high, low, close, period=14)

        # 5. Donchian Channel
        df["d1_donchian_high_20"] = high.rolling(window=20, min_periods=20).max().shift(1)
        df["d1_donchian_low_20"] = low.rolling(window=20, min_periods=20).min().shift(1)

        return df


class H4FeatureExtractor:
    """Computes 4-hour technical, candlestick geometry, and swing features."""

    def __init__(self, eps: float = 1e-8):
        self.eps = eps

    def compute_features(self, df_h4: pd.DataFrame) -> pd.DataFrame:
        """Extract H4 technical features with explicit decision timestamps.

        Parameters
        ----------
        df_h4 : pd.DataFrame
            H4 OHLC DataFrame containing 'timestamp' (candle open timestamp).

        Returns
        -------
        pd.DataFrame
            DataFrame containing H4 features and 'h4_decision_ts' (candle open + 4h).
        """
        df = df_h4.sort_values("timestamp").reset_index(drop=True).copy()

        # Decision timestamp: an H4 bar starting at T closes at T + 4h
        df["h4_decision_ts"] = df["timestamp"] + pd.Timedelta(hours=4)

        close = df["close"]
        open_ = df["open"]
        high = df["high"]
        low = df["low"]

        # 1. Multi-Horizon Lagged Returns
        df["h4_ret_1"] = close.pct_change(1)
        df["h4_ret_3"] = close.pct_change(3)    # 12 hours
        df["h4_ret_6"] = close.pct_change(6)    # 24 hours (1 day)
        df["h4_ret_12"] = close.pct_change(12)  # 48 hours (2 days)

        # 2. Moving Averages & Pullback Metrics
        df["h4_ema_10"] = close.ewm(span=10, adjust=False).mean()
        df["h4_ema_20"] = close.ewm(span=20, adjust=False).mean()
        df["h4_ema_50"] = close.ewm(span=50, adjust=False).mean()

        df["h4_trend_regime"] = np.where(
            df["h4_ema_20"] > df["h4_ema_50"], 1, np.where(df["h4_ema_20"] < df["h4_ema_50"], -1, 0)
        )

        # 3. Volatility Metrics
        df["h4_tr"] = compute_true_range(high, low, close)
        df["h4_atr_14"] = compute_atr(high, low, close, period=14)
        df["h4_atr_pct"] = df["h4_atr_14"] / (close + self.eps)

        # True Range expansion ratio (current TR relative to 20-period rolling median TR)
        rolling_median_tr = df["h4_tr"].rolling(window=20, min_periods=20).median()
        df["h4_tr_expansion"] = df["h4_tr"] / (rolling_median_tr + self.eps)

        # Pullback depth normalized by ATR: (Close - EMA20) / ATR14
        df["h4_pullback_depth_atr"] = (close - df["h4_ema_20"]) / (df["h4_atr_14"] + self.eps)

        # 4. Candlestick Geometry
        candle_range = high - low + self.eps
        df["h4_body_ratio"] = (close - open_).abs() / candle_range
        df["h4_upper_wick_ratio"] = (high - np.maximum(open_, close)) / candle_range
        df["h4_lower_wick_ratio"] = (np.minimum(open_, close) - low) / candle_range

        # 5. Donchian Swing Channels (strictly shifted by 1 to exclude current bar)
        df["h4_donchian_high_20"] = high.rolling(window=20, min_periods=20).max().shift(1)
        df["h4_donchian_low_20"] = low.rolling(window=20, min_periods=20).min().shift(1)

        # Channel Breakout Distance (positive = breakout above/below)
        df["h4_channel_breakout_long"] = (close - df["h4_donchian_high_20"]) / (df["h4_atr_14"] + self.eps)
        df["h4_channel_breakout_short"] = (df["h4_donchian_low_20"] - close) / (df["h4_atr_14"] + self.eps)

        # 6. Momentum (RSI)
        df["h4_rsi_14"] = compute_rsi(close, period=14)

        return df


class MultiTimeframeSwingPipeline:
    """End-to-end multi-timeframe feature alignment pipeline with strict causality guarantees."""

    def __init__(
        self,
        d1_extractor: Optional[D1FeatureExtractor] = None,
        h4_extractor: Optional[H4FeatureExtractor] = None,
        max_staleness: pd.Timedelta = pd.Timedelta(days=5),
        min_d1_bars_for_regular_session: int = 1350,
    ):
        self.d1_extractor = d1_extractor or D1FeatureExtractor()
        self.h4_extractor = h4_extractor or H4FeatureExtractor()
        self.max_staleness = max_staleness
        self.min_d1_bars_for_regular_session = min_d1_bars_for_regular_session

    def build_swing_features(
        self,
        df_h4: pd.DataFrame,
        df_d1: pd.DataFrame,
    ) -> pd.DataFrame:
        """Construct causally aligned multi-timeframe feature dataset.

        Parameters
        ----------
        df_h4 : pd.DataFrame
            H4 candlesticks.
        df_d1 : pd.DataFrame
            D1 candlesticks.

        Returns
        -------
        pd.DataFrame
            Unified H4 DataFrame enriched with completed D1 features and cross-timeframe metrics.
        """
        # 1. Compute single-timeframe features
        feat_d1 = self.d1_extractor.compute_features(df_d1)
        feat_h4 = self.h4_extractor.compute_features(df_h4)

        # 2. Prepare D1 columns for merge
        d1_cols_to_merge = [
            c for c in feat_d1.columns if c not in ["open", "high", "low", "close", "volume"]
        ]
        d1_prep = feat_d1[d1_cols_to_merge].copy()

        # Prefix D1 feature columns (except d1_available_ts)
        rename_map = {}
        for col in d1_prep.columns:
            if col != "d1_available_ts":
                rename_map[col] = f"{col}" if col.startswith("d1_") else f"d1_{col}"
        d1_prep = d1_prep.rename(columns=rename_map)

        # 3. Sort both DataFrames for backward as-of merge
        h4_sorted = feat_h4.sort_values("h4_decision_ts").reset_index(drop=True)
        d1_sorted = d1_prep.sort_values("d1_available_ts").reset_index(drop=True)

        # 4. Backward As-Of Merge:
        # Matches latest completed D1 candle where d1_available_ts <= h4_decision_ts
        merged = pd.merge_asof(
            h4_sorted,
            d1_sorted,
            left_on="h4_decision_ts",
            right_on="d1_available_ts",
            direction="backward",
            tolerance=self.max_staleness,
        )

        # 5. Cross-Timeframe Alignment Features
        # Cross Trend Alignment: +1 if both bullish, -1 if both bearish, 0 divergent
        both_bull = (merged["h4_trend_regime"] == 1) & (merged["d1_trend_regime"] == 1)
        both_bear = (merged["h4_trend_regime"] == -1) & (merged["d1_trend_regime"] == -1)
        merged["cross_trend_alignment"] = np.where(both_bull, 1, np.where(both_bear, -1, 0))

        # Cross Z-Score: Distance of H4 close from D1 20-day EMA normalized by D1 20-day Std
        std = merged["d1_rolling_std_20"].replace(0.0, np.nan)
        merged["cross_h4_d1_zscore"] = (merged["close"] - merged["d1_ema_20"]) / (std + 1e-8)

        # Cross Volatility Expansion: H4 TR expanding while D1 is in compression
        merged["cross_vol_expansion_in_d1_compression"] = (
            (merged["h4_tr_expansion"] > 1.30) & (merged["d1_vol_compression_ratio"] < 0.80)
        )

        # Cross Pullback In Trend: H4 pullback occurs within prevailing D1 trend
        long_pb = (merged["d1_trend_regime"] == 1) & (merged["h4_pullback_depth_atr"] < -0.5)
        short_pb = (merged["d1_trend_regime"] == -1) & (merged["h4_pullback_depth_atr"] > 0.5)
        merged["cross_pullback_in_d1_trend"] = long_pb | short_pb

        # 6. Defensible Completeness Policy Flags
        # Standard H4 completeness flag
        merged["h4_eligible"] = merged["is_complete"]
        # D1 regular trading day flag (permits 1-5 quiet minutes in regular 23h session)
        merged["d1_regular_session"] = merged["d1_bar_count"] >= self.min_d1_bars_for_regular_session
        # Combined eligibility for hypothesis signal evaluation
        merged["swing_signal_eligible"] = merged["h4_eligible"] & merged["d1_regular_session"]

        return merged
