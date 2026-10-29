"""Technical feature extraction engine for financial OHLCV time series.

Computes mathematically sound, stationary, and lookahead-free quantitative features
including returns, volatility metrics, ATR, trend indicators, and momentum oscillators.
"""

from typing import Dict, List, Optional
import numpy as np
import pandas as pd


class TechnicalFeatureExtractor:
    """Computes technical, volatility, trend, and momentum features from OHLC data.

    Strict Guarantees:
    - Purely backward-looking: No feature calculation uses future candles.
    - Scale stationarity: Price distances, moving average divergences, and ATRs are
      normalized by current price or volatility to ensure regime stationarity.
    - Numerical safety: Safeguarded against division by zero with small epsilon.
    """

    def __init__(
        self,
        return_periods: Optional[List[int]] = None,
        volatility_windows: Optional[List[int]] = None,
        atr_windows: Optional[List[int]] = None,
        ema_periods: Optional[List[int]] = None,
        rsi_period: int = 14,
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9,
        bb_period: int = 20,
        bb_std: float = 2.0,
        eps: float = 1e-8,
    ):
        self.return_periods = return_periods or [1, 2, 3, 5, 10, 15, 30, 60]
        self.volatility_windows = volatility_windows or [5, 15, 30, 60, 240]
        self.atr_windows = atr_windows or [7, 14, 28]
        self.ema_periods = ema_periods or [9, 21, 50, 200]
        self.rsi_period = rsi_period
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.eps = eps

    def compute_returns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute multi-horizon simple and log returns, plus intrabar candlestick geometry."""
        features = pd.DataFrame(index=df.index)
        close = df["close"]
        open_ = df["open"]
        high = df["high"]
        low = df["low"]

        # Multi-horizon returns (backward looking)
        for k in self.return_periods:
            features[f"ret_{k}"] = close.pct_change(k)
            # Log return: ln(C_t / C_{t-k}) = ln(C_t) - ln(C_{t-k})
            features[f"log_ret_{k}"] = np.log(close / close.shift(k))

        # Intrabar candlestick geometry
        features["candle_return"] = (close - open_) / (open_ + self.eps)
        features["candle_span"] = (high - low) / (low + self.eps)
        features["log_hl_ratio"] = np.log(high / (low + self.eps))

        # Candle shadow proportions
        max_oc = np.maximum(open_, close)
        min_oc = np.minimum(open_, close)
        features["upper_shadow"] = (high - max_oc) / (close + self.eps)
        features["lower_shadow"] = (min_oc - low) / (close + self.eps)
        features["body_to_range"] = np.abs(close - open_) / ((high - low) + self.eps)

        return features

    def compute_volatility(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute rolling realized volatility, Parkinson volatility, and Garman-Klass volatility."""
        features = pd.DataFrame(index=df.index)
        close = df["close"]
        open_ = df["open"]
        high = df["high"]
        low = df["low"]

        log_ret_1 = np.log(close / close.shift(1))

        # 1. Realized Volatility: rolling standard deviation of 1-period log returns
        for w in self.volatility_windows:
            features[f"volatility_{w}"] = log_ret_1.rolling(window=w, min_periods=w).std()

        # Short to long term volatility ratio (e.g. 5 vs 30)
        if 5 in self.volatility_windows and 30 in self.volatility_windows:
            features["vol_ratio_5_30"] = features["volatility_5"] / (features["volatility_30"] + self.eps)

        # 2. Parkinson Volatility: High-Low range based volatility (more efficient than close-to-close)
        # sigma_P = sqrt( (1 / (4 * ln(2) * W)) * sum( (ln(H/L))^2 ) )
        log_hl_sq = (np.log(high / (low + self.eps))) ** 2
        factor_p = 1.0 / (4.0 * np.log(2.0))
        for w in [15, 30, 60]:
            if w <= max(self.volatility_windows):
                rolling_hl = log_hl_sq.rolling(window=w, min_periods=w).mean()
                features[f"parkinson_vol_{w}"] = np.sqrt(np.maximum(factor_p * rolling_hl, 0.0))

        # 3. Garman-Klass Volatility: Includes Open, High, Low, Close
        # term = 0.5 * (ln(H/L))^2 - (2*ln(2) - 1) * (ln(C/O))^2
        log_co_sq = (np.log(close / (open_ + self.eps))) ** 2
        gk_term = 0.5 * log_hl_sq - (2.0 * np.log(2.0) - 1.0) * log_co_sq
        for w in [15, 30, 60]:
            if w <= max(self.volatility_windows):
                rolling_gk = gk_term.rolling(window=w, min_periods=w).mean()
                features[f"garman_klass_vol_{w}"] = np.sqrt(np.maximum(rolling_gk, 0.0))

        return features

    def compute_atr(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute True Range, Average True Range (ATR), and Normalized ATR (NATR)."""
        features = pd.DataFrame(index=df.index)
        high = df["high"]
        low = df["low"]
        prev_close = df["close"].shift(1)

        # True Range: max(H - L, |H - C_{t-1}|, |L - C_{t-1}|)
        tr1 = high - low
        tr2 = (high - prev_close).abs().fillna(0.0)
        tr3 = (low - prev_close).abs().fillna(0.0)
        true_range = np.maximum(tr1, np.maximum(tr2, tr3))
        features["true_range"] = true_range

        close = df["close"]
        for w in self.atr_windows:
            # Wilder's smoothing via ewm(alpha=1/w)
            atr = true_range.ewm(alpha=1.0 / w, min_periods=w, adjust=False).mean()
            features[f"atr_{w}"] = atr
            # Normalized ATR (NATR): percentage of price
            features[f"natr_{w}"] = atr / (close + self.eps)

        return features

    def compute_trend(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute Exponential Moving Averages (EMA), price divergences, and slope metrics."""
        features = pd.DataFrame(index=df.index)
        close = df["close"]

        ema_series: Dict[int, pd.Series] = {}
        for p in self.ema_periods:
            ema = close.ewm(span=p, min_periods=p, adjust=False).mean()
            ema_series[p] = ema
            # Distance from EMA: (C - EMA) / EMA (stationary!)
            features[f"dist_ema_{p}"] = (close - ema) / (ema + self.eps)
            # EMA momentum slope (1-bar pct change of EMA)
            features[f"ema_slope_{p}"] = (ema - ema.shift(1)) / (ema.shift(1) + self.eps)

        # Cross ratios between fast and slow EMAs
        if 9 in ema_series and 21 in ema_series:
            features["ema_ratio_9_21"] = (ema_series[9] - ema_series[21]) / (ema_series[21] + self.eps)
        if 21 in ema_series and 50 in ema_series:
            features["ema_ratio_21_50"] = (ema_series[21] - ema_series[50]) / (ema_series[50] + self.eps)
        if 50 in ema_series and 200 in ema_series:
            features["ema_ratio_50_200"] = (ema_series[50] - ema_series[200]) / (ema_series[200] + self.eps)

        return features

    def compute_momentum(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute RSI, normalized MACD, and Bollinger Bands metrics."""
        features = pd.DataFrame(index=df.index)
        close = df["close"]

        # 1. Relative Strength Index (RSI) using Wilder's exponential smoothing
        delta = close.diff()
        gain = np.maximum(delta, 0.0)
        loss = np.maximum(-delta, 0.0)

        alpha = 1.0 / self.rsi_period
        avg_gain = gain.ewm(alpha=alpha, min_periods=self.rsi_period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=alpha, min_periods=self.rsi_period, adjust=False).mean()

        rs = avg_gain / (avg_loss + self.eps)
        rsi = 100.0 - (100.0 / (1.0 + rs))
        features[f"rsi_{self.rsi_period}"] = rsi
        # Normalized RSI centered around 0 in [-1.0, 1.0]
        features[f"rsi_{self.rsi_period}_norm"] = (rsi - 50.0) / 50.0

        # 2. Moving Average Convergence Divergence (MACD)
        ema_fast = close.ewm(span=self.macd_fast, min_periods=self.macd_fast, adjust=False).mean()
        ema_slow = close.ewm(span=self.macd_slow, min_periods=self.macd_slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=self.macd_signal, min_periods=self.macd_signal, adjust=False).mean()
        macd_hist = macd_line - signal_line

        # Normalized by close price for scale invariance
        features["macd_norm"] = macd_line / (close + self.eps)
        features["macd_signal_norm"] = signal_line / (close + self.eps)
        features["macd_hist_norm"] = macd_hist / (close + self.eps)

        # 3. Bollinger Bands (20, 2.0)
        sma_bb = close.rolling(window=self.bb_period, min_periods=self.bb_period).mean()
        std_bb = close.rolling(window=self.bb_period, min_periods=self.bb_period).std()
        upper_bb = sma_bb + self.bb_std * std_bb
        lower_bb = sma_bb - self.bb_std * std_bb

        # %B: Position of price within Bollinger Bands
        features["bb_pct_b"] = (close - lower_bb) / ((upper_bb - lower_bb) + self.eps)
        # Bandwidth: Relative width of bands normalized by middle band
        features["bb_bandwidth"] = (upper_bb - lower_bb) / (sma_bb + self.eps)

        return features

    def extract_all(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract all technical, volatility, ATR, trend, and momentum features.

        Parameters
        ----------
        df : pd.DataFrame
            OHLC DataFrame with columns ['open', 'high', 'low', 'close'] and optional ['volume'].

        Returns
        -------
        pd.DataFrame
            Concatenated feature DataFrame aligned with input index.
        """
        returns_df = self.compute_returns(df)
        vol_df = self.compute_volatility(df)
        atr_df = self.compute_atr(df)
        trend_df = self.compute_trend(df)
        mom_df = self.compute_momentum(df)

        return pd.concat([returns_df, vol_df, atr_df, trend_df, mom_df], axis=1)
