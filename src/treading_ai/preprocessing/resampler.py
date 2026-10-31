"""Timeframe resampling engine for multi-timeframe financial market analysis.

Constructs higher timeframe candles (M5, M15, M30, H1, H4, D1) from base M1 OHLC data
using rigorous financial aggregation semantics without fabricating data.
"""

from datetime import timedelta
import logging
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from treading_ai.config import (
    OHLC_COLUMNS,
    TIMEFRAME_FREQ_MAP,
    TIMEFRAME_M1_COUNT,
)

logger = logging.getLogger(__name__)

TZ_NEW_YORK = ZoneInfo("America/New_York")


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
            List of timeframes to resample into (default: M5, M15, M30, H1, H4, D1).
        h4_alignment : str
            Alignment strategy for H4 candles:
            - 'session' (default): Anchored to 22:00 UTC (17:00 NY close / 23:00 market open, offset='2h')
              so no H4 candle merges across the daily settlement closure.
            - 'utc': Standard 00:00 UTC anchor (00:00, 04:00, ..., 20:00).
        """
        self.target_timeframes = target_timeframes or ["M5", "M15", "M30", "H1", "H4", "D1"]
        self.h4_alignment = h4_alignment

    @staticmethod
    def get_h4_scheduled_active_minutes(start_ts_utc: pd.Timestamp) -> int:
        """Calculate scheduled active market minutes for an H4 candle [start, start + 4h).

        Spot gold scheduled closures:
        - Daily settlement rollover: Mon-Thu 17:00-18:00 New York Time (60 min closure).
        - Weekend closure: Friday 17:00 NY to Sunday 18:00 NY.

        Returns
        -------
        int
            Expected active minutes (180 for rollover or weekend boundary candles, 240 for standard candles).
        """
        mins = pd.date_range(start=start_ts_utc, periods=240, freq="1min")
        mins_ny = mins.tz_convert(TZ_NEW_YORK)
        # Daily rollover closure: Mon-Thu 17:00-18:00 NY
        is_roll = (mins_ny.day_of_week < 4) & (mins_ny.hour == 17)
        # Weekend closure: Fri >= 17:00, Sat, Sun < 18:00
        w = mins_ny.day_of_week
        h = mins_ny.hour
        is_wknd = ((w == 4) & (h >= 17)) | (w == 5) | ((w == 6) & (h < 18))
        closed_count = int((is_roll | is_wknd).sum())
        return 240 - closed_count

    def resample_daily_session_ny(self, df_m1: pd.DataFrame) -> pd.DataFrame:
        """Resample 1-minute OHLC DataFrame into Daily (D1) candles aligned to New York close.

        Financial Market Session Boundary Semantics:
        - Spot gold daily trading session opens at 18:00:00 New York Time (America/New_York)
          on date D-1 (e.g. Sunday 18:00 NY) and closes at 17:00:00 New York Time on date D
          (e.g. Monday 17:00 NY).
        - Daylight Saving Time (DST) transitions are handled explicitly via dynamic timezone
          conversion to America/New_York (no static UTC offset assumption).
        - Friday close at 17:00 NY to Sunday open at 18:00 NY is recognized as weekend closure.
          Zero artificial Sunday mini-candles are produced. Exactly 5 sessions/week are aggregated.
        - Causal aggregation: Each D1 candle contains strictly constituent M1 observations
          belonging to its session window.
        - Expected M1 count for a full 23-hour session is 1,380 bars (23h * 60m). Shortened sessions
          (e.g., market holidays such as Thanksgiving or Memorial Day) are flagged is_complete=False.

        Parameters
        ----------
        df_m1 : pd.DataFrame
            Base 1-minute OHLC DataFrame with UTC timestamp.

        Returns
        -------
        pd.DataFrame
            Resampled D1 OHLC DataFrame with session date timestamp at 00:00:00 UTC,
            bar_count, and is_complete flag.
        """
        if df_m1.empty:
            return pd.DataFrame(columns=OHLC_COLUMNS + ["bar_count", "is_complete"])

        df = df_m1.copy()
        if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        elif df["timestamp"].dt.tz is None:
            df["timestamp"] = df["timestamp"].dt.tz_localize("UTC")
        else:
            df["timestamp"] = df["timestamp"].dt.tz_convert("UTC")

        df = df.sort_values("timestamp").reset_index(drop=True)

        # Explicit New York Local Timezone Conversion for Causal Session Boundary Alignment
        ts_ny = df["timestamp"].dt.tz_convert(TZ_NEW_YORK)

        # In America/New_York:
        # Ticks >= 18:00 belong to the next calendar trading day's session (e.g., Sun 18:00 NY -> Mon)
        # Ticks < 17:00 belong to the current calendar trading day's session
        # Ticks between 17:00 and 18:00 (if any occur during daily rollover break) belong to the current date
        session_date = ts_ny.dt.date.copy()
        is_evening_session = ts_ny.dt.hour >= 18
        session_date.loc[is_evening_session] = session_date.loc[is_evening_session].apply(
            lambda d: d + timedelta(days=1)
        )
        df["session_date"] = session_date

        grouped = df.groupby("session_date", sort=True)
        agg_dict = {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        }
        resampled_df = grouped.agg(agg_dict)
        resampled_df["bar_count"] = grouped["open"].count().astype("int32")

        # Exclude empty days
        resampled_df = resampled_df[resampled_df["bar_count"] > 0].copy()

        # Full 23-hour session = 1,380 minutes (23 * 60)
        expected_d1_count = TIMEFRAME_M1_COUNT.get("D1", 1380)
        resampled_df["is_complete"] = (resampled_df["bar_count"] == expected_d1_count).astype("bool")

        # Standard daily timestamp convention: UTC 00:00:00 of the trading session date
        resampled_df["timestamp"] = pd.to_datetime(resampled_df.index).tz_localize("UTC")
        resampled_df = resampled_df.reset_index(drop=True)

        # Enforce exact column order and types
        cols = OHLC_COLUMNS + ["bar_count", "is_complete"]
        resampled_df = resampled_df[cols]
        resampled_df["bar_count"] = resampled_df["bar_count"].astype("int32")
        resampled_df["is_complete"] = resampled_df["is_complete"].astype("bool")
        return resampled_df

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
            Target timeframe string ('M5', 'M15', 'M30', 'H1', 'H4', 'D1').
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

        # Daily timeframe handled via dynamic New York Close session alignment
        if target_timeframe == "D1":
            return self.resample_daily_session_ny(df_m1)

        freq = TIMEFRAME_FREQ_MAP[target_timeframe]
        expected_m1_count = TIMEFRAME_M1_COUNT.get(target_timeframe, 1)

        # Ensure timestamp is set as datetime index
        df = df_m1.copy()
        if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        elif df["timestamp"].dt.tz is None:
            df["timestamp"] = df["timestamp"].dt.tz_localize("UTC")
        else:
            df["timestamp"] = df["timestamp"].dt.tz_convert("UTC")

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

        # Completeness logic:
        if target_timeframe == "H4":
            # Schedule-aware completeness: check if the candle spans scheduled daily rollover
            # or weekend market closures (180 active minutes expected) vs active hours (240 minutes expected).
            # Distinguishes scheduled market closures from genuinely missing source data.
            expected_minutes = np.array([
                self.get_h4_scheduled_active_minutes(ts) for ts in resampled_df.index
            ], dtype=int)
            resampled_df["is_complete"] = resampled_df["bar_count"].to_numpy() == expected_minutes
        else:
            # Flag complete vs partial boundary candles for intraday timeframes (M5, M15, M30, H1)
            resampled_df["is_complete"] = resampled_df["bar_count"] == expected_m1_count

        resampled_df = resampled_df.reset_index()

        # Enforce exact column order and types
        resampled_df["bar_count"] = resampled_df["bar_count"].astype("int32")
        resampled_df["is_complete"] = resampled_df["is_complete"].astype("bool")

        return resampled_df

    def resample_all_timeframes(self, df_m1: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """Resample M1 DataFrame across all target timeframes (M5, M15, M30, H1, H4, D1).

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
