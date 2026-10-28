"""Timeframe resampling engine for multi-timeframe financial market analysis.

Constructs higher timeframe candles (M5, M15, M30, H1, H4) from base M1 OHLC data
using rigorous financial aggregation semantics without fabricating data.
"""

import logging
from typing import Dict, Optional

import pandas as pd

from treading_ai.config import (
    OHLC_COLUMNS,
    TIMEFRAME_FREQ_MAP,
    TIMEFRAME_M1_COUNT,
)

logger = logging.getLogger(__name__)


class TimeframeResampler:
    """Resamples M1 historical candles to higher timeframes with explicit session boundary handling."""

    def __init__(
        self,
        target_timeframes: Optional[list] = None,
        h4_alignment: str = "session",
    ):
        """Initialize resampler.

        Parameters
        ----------
        target_timeframes : Optional[list]
            List of timeframes to resample into (default: M5, M15, M30, H1, H4).
        h4_alignment : str
            Alignment strategy for H4 candles:
            - 'session' (default): Anchored to 22:00 UTC (17:00 NY close / 23:00 market open, offset='2h')
              so no H4 candle merges across the daily settlement closure.
            - 'utc': Standard 00:00 UTC anchor (00:00, 04:00, ..., 20:00).
        """
        self.target_timeframes = target_timeframes or ["M5", "M15", "M30", "H1", "H4"]
        self.h4_alignment = h4_alignment

    def resample_candle_series(
        self,
        df_m1: pd.DataFrame,
        target_timeframe: str,
        h4_alignment: Optional[str] = None,
    ) -> pd.DataFrame:
        """Resample 1-minute OHLC DataFrame into a target timeframe.

        Parameters
        ----------
        df_m1 : pd.DataFrame
            Base 1-minute OHLC DataFrame with UTC timestamp.
        target_timeframe : str
            Target timeframe string ('M5', 'M15', 'M30', 'H1', 'H4').
        h4_alignment : Optional[str]
            Override for H4 alignment ('session' or 'utc'). Defaults to self.h4_alignment.

        Returns
        -------
        pd.DataFrame
            Resampled OHLC DataFrame with constituent count and completeness flags.
        """
        if target_timeframe not in TIMEFRAME_FREQ_MAP:
            raise ValueError(
                f"Unsupported timeframe '{target_timeframe}'. "
                f"Supported: {list(TIMEFRAME_FREQ_MAP.keys())}"
            )

        if df_m1.empty:
            return pd.DataFrame(columns=OHLC_COLUMNS + ["bar_count", "is_complete"])

        freq = TIMEFRAME_FREQ_MAP[target_timeframe]
        expected_m1_count = TIMEFRAME_M1_COUNT.get(target_timeframe, 1)

        # Ensure timestamp is set as datetime index
        df = df_m1.copy()
        if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)

        df = df.sort_values("timestamp")
        df = df.set_index("timestamp")

        # Standard financial candle convention: closed='left', label='left'
        align_mode = h4_alignment or self.h4_alignment
        if target_timeframe == "H4" and align_mode == "session":
            # Offset by 2h so bins are [22:00, 02:00), [02:00, 06:00), ..., [18:00, 22:00)
            # The 18:00-22:00 bar ends cleanly at the 22:00 daily market close without straddling.
            resampler = df.resample(freq, closed="left", label="left", offset="2h")
        else:
            resampler = df.resample(freq, closed="left", label="left")

        agg_dict = {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        }

        resampled_df = resampler.agg(agg_dict)

        # Count actual constituent M1 candles to detect incomplete / boundary candles
        counts = resampler["open"].count()
        resampled_df["bar_count"] = counts

        # Drop intervals with zero trading activity (e.g., weekends, holidays)
        # We do not fabricate or forward-fill missing historical candles
        resampled_df = resampled_df[resampled_df["bar_count"] > 0].copy()

        # Flag complete vs partial boundary candles
        resampled_df["is_complete"] = resampled_df["bar_count"] == expected_m1_count

        resampled_df = resampled_df.reset_index()

        # Enforce exact column order and types
        resampled_df["bar_count"] = resampled_df["bar_count"].astype("int32")
        resampled_df["is_complete"] = resampled_df["is_complete"].astype("bool")

        return resampled_df

    def resample_all_timeframes(self, df_m1: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """Resample M1 DataFrame across all target timeframes (M5, M15, M30, H1, H4).

        Returns
        -------
        Dict[str, pd.DataFrame]
            Dictionary mapping timeframe strings to resampled DataFrames.
        """
        results: Dict[str, pd.DataFrame] = {}

        # M1 format standardized with bar_count=1 and is_complete=True
        df_m1_standard = df_m1.copy()
        if "bar_count" not in df_m1_standard.columns:
            df_m1_standard["bar_count"] = 1
        if "is_complete" not in df_m1_standard.columns:
            df_m1_standard["is_complete"] = True
        df_m1_standard["bar_count"] = df_m1_standard["bar_count"].astype("int32")
        df_m1_standard["is_complete"] = df_m1_standard["is_complete"].astype("bool")
        results["M1"] = df_m1_standard

        for tf in self.target_timeframes:
            if tf == "M1":
                continue
            logger.info("Resampling to timeframe: %s", tf)
            resampled = self.resample_candle_series(df_m1, target_timeframe=tf)
            results[tf] = resampled

        return results
