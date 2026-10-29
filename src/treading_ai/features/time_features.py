"""Time and session feature extraction engine for financial market time series.

Extracts smooth cyclical encodings and categorical session flags representing
global Forex and Gold market trading microstructure (Asian, London, NY, overlaps, roll breaks).
"""

import numpy as np
import pandas as pd
from zoneinfo import ZoneInfo

TZ_LONDON = ZoneInfo("Europe/London")
TZ_NEW_YORK = ZoneInfo("America/New_York")
TZ_TOKYO = ZoneInfo("Asia/Tokyo")


class TimeFeatureExtractor:
    """Computes continuous cyclical encodings and discrete session indicators from timestamps.

    Strict Timezone-Aware Microstructure Semantics:
    - London Session: 08:00 to 16:30 local London time (Europe/London: GMT in winter, BST in summer).
    - New York Session: 08:00 to 17:00 local New York time (America/New_York: EST in winter, EDT in summer).
    - London-NY Overlap: Exact logical conjunction (London active AND NY active).
    - Asian Session: 09:00 to 18:00 local Tokyo time (Asia/Tokyo: JST UTC+9).
    - Daily Rollover Window: 17:00 to 18:00 New York time, Monday-Thursday (daily settlement closure).
    - Friday Close Approaching: Friday 14:00 to 17:00 New York time (pre-weekend squaring).
    - Sunday Open: Sunday from 18:00 New York time onward (market reopening).
    """

    def __init__(self):
        pass

    def extract_time_features(self, timestamps: pd.Series) -> pd.DataFrame:
        """Extract continuous cyclical and binary session features from UTC Timestamp Series.

        Parameters
        ----------
        timestamps : pd.Series
            Series of timezone-aware UTC timestamps (`datetime64[..., UTC]`).

        Returns
        -------
        pd.DataFrame
            DataFrame of extracted time and session features.
        """
        # Ensure UTC datetime
        if not pd.api.types.is_datetime64_any_dtype(timestamps):
            ts_utc = pd.to_datetime(timestamps, utc=True)
        elif timestamps.dt.tz is None:
            ts_utc = timestamps.dt.tz_localize("UTC")
        else:
            ts_utc = timestamps.dt.tz_convert("UTC")

        features = pd.DataFrame(index=timestamps.index)

        hour_utc = ts_utc.dt.hour
        minute_utc = ts_utc.dt.minute
        day_of_week_utc = ts_utc.dt.day_of_week  # Monday=0 ... Sunday=6
        month_utc = ts_utc.dt.month

        # 1. Continuous Cyclical Encodings (Harmonics based on continuous UTC)
        # Minute of the day: [0, 1440)
        minute_of_day = hour_utc * 60 + minute_utc
        features["sin_time_of_day"] = np.sin(2.0 * np.pi * minute_of_day / 1440.0)
        features["cos_time_of_day"] = np.cos(2.0 * np.pi * minute_of_day / 1440.0)

        # Day of the week: [0, 7)
        features["sin_day_of_week"] = np.sin(2.0 * np.pi * day_of_week_utc / 7.0)
        features["cos_day_of_week"] = np.cos(2.0 * np.pi * day_of_week_utc / 7.0)

        # Month of the year: [0, 12)
        features["sin_month"] = np.sin(2.0 * np.pi * (month_utc - 1) / 12.0)
        features["cos_month"] = np.cos(2.0 * np.pi * (month_utc - 1) / 12.0)

        # 2. Timezone-Aware Local Market Sessions
        # Convert to local market timezones for accurate civil & DST tracking
        ts_london = ts_utc.dt.tz_convert(TZ_LONDON)
        ts_ny = ts_utc.dt.tz_convert(TZ_NEW_YORK)
        ts_tokyo = ts_utc.dt.tz_convert(TZ_TOKYO)

        # London Session: 08:00 to 16:30 local London time (Monday-Friday)
        # Covers both GMT (winter) and BST (summer) seamlessly
        min_london = ts_london.dt.hour * 60 + ts_london.dt.minute
        is_weekday_london = ts_london.dt.day_of_week < 5
        features["session_london"] = (
            (min_london >= 8 * 60) & (min_london < 16 * 60 + 30) & is_weekday_london
        ).astype(np.int8)

        # New York Session: 08:00 to 17:00 local New York time (Monday-Friday)
        # Covers both EST (winter) and EDT (summer) seamlessly
        min_ny = ts_ny.dt.hour * 60 + ts_ny.dt.minute
        is_weekday_ny = ts_ny.dt.day_of_week < 5
        features["session_ny"] = (
            (min_ny >= 8 * 60) & (min_ny < 17 * 60) & is_weekday_ny
        ).astype(np.int8)

        # London / New York Overlap: Exact, consistent conjunction
        features["session_london_ny_overlap"] = (
            features["session_london"] & features["session_ny"]
        ).astype(np.int8)

        # Asian Session: 09:00 to 18:00 local Tokyo time (Monday-Friday)
        is_weekday_tokyo = ts_tokyo.dt.day_of_week < 5
        features["session_asian"] = (
            (ts_tokyo.dt.hour >= 9) & (ts_tokyo.dt.hour < 18) & is_weekday_tokyo
        ).astype(np.int8)

        # 3. Market Regime & Liquidity Risk Flags (in New York Market Time)
        # Daily rollover & settlement window: 17:00 to 18:00 New York Time (Monday-Thursday)
        # In summer (EDT): 21:00-22:00 UTC. In winter (EST): 22:00-23:00 UTC.
        features["is_daily_roll_window"] = (
            (ts_ny.dt.hour == 17) & (ts_ny.dt.day_of_week < 4)
        ).astype(np.int8)

        # Friday close approaching: Friday 14:00 to 17:00 New York Time (pre-weekend squaring)
        features["is_friday_close_approaching"] = (
            (ts_ny.dt.day_of_week == 4) & (ts_ny.dt.hour >= 14) & (ts_ny.dt.hour < 17)
        ).astype(np.int8)

        # Sunday opening session: Sunday from 18:00 New York Time onward (weekend reopening)
        features["is_sunday_open"] = (
            (ts_ny.dt.day_of_week == 6) & (ts_ny.dt.hour >= 18)
        ).astype(np.int8)

        return features
