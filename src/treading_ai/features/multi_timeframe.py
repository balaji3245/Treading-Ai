"""Multi-timeframe alignment engine with strict lookahead-leakage prevention.

Ensures higher timeframe features are only merged onto lower timeframe records
AFTER the higher timeframe candle has completely closed, preserving temporal causality.
"""

from datetime import timedelta
import logging
from typing import Dict, List, Optional
import pandas as pd

from treading_ai.config import TIMEFRAME_M1_COUNT

logger = logging.getLogger(__name__)


class MultiTimeframeAligner:
    """Aligns higher timeframe (HTF) features onto lower timeframe (LTF) datasets.

    Strict Temporal Causality Guarantee:
    - An HTF bar starting at T with duration D closes at T + D.
    - An LTF candle at timestamp t is strictly forbidden from seeing HTF bar (T)
      until t >= T + D.
    - Implemented via backward as-of merging on `available_timestamp = T + D`.
    """

    def __init__(
        self,
        ltf_timeframe: str = "M5",
        max_staleness: Optional[pd.Timedelta] = pd.Timedelta(days=4),
    ):
        """Initialize aligner.

        Parameters
        ----------
        ltf_timeframe : str
            Base trading timeframe (e.g. 'M5').
        max_staleness : Optional[pd.Timedelta]
            Maximum allowable gap between LTF timestamp and HTF availability timestamp
            (default: 4 days / 96 hours). Accommodates normal weekend closures (~49h)
            and holiday weekends (~73h) while preventing indefinite stale feature carryover.
        """
        self.ltf_timeframe = ltf_timeframe.upper()
        self.ltf_duration_minutes = TIMEFRAME_M1_COUNT.get(self.ltf_timeframe, 5)
        self.max_staleness = max_staleness

    def align_htf_features(
        self,
        ltf_df: pd.DataFrame,
        htf_df: pd.DataFrame,
        htf_timeframe: str,
        feature_columns: Optional[List[str]] = None,
        prefix: Optional[str] = None,
    ) -> pd.DataFrame:
        """Align HTF features onto LTF DataFrame without forward lookahead.

        Parameters
        ----------
        ltf_df : pd.DataFrame
            Lower timeframe DataFrame containing 'timestamp' column.
        htf_df : pd.DataFrame
            Higher timeframe DataFrame containing 'timestamp' and feature columns.
        htf_timeframe : str
            Higher timeframe identifier (e.g. 'M15', 'M30', 'H1', 'H4').
        feature_columns : Optional[List[str]]
            List of feature column names in htf_df to merge. If None, merges all
            columns except standard OHLC metadata.
        prefix : Optional[str]
            Column name prefix. Defaults to 'htf_{timeframe.lower()}_'.

        Returns
        -------
        pd.DataFrame
            Copy of ltf_df with aligned HTF features appended.
        """
        htf_tf = htf_timeframe.upper()
        htf_duration_minutes = TIMEFRAME_M1_COUNT.get(htf_tf)
        if htf_duration_minutes is None:
            raise ValueError(f"Unsupported HTF timeframe: {htf_timeframe}. Must be one of {list(TIMEFRAME_M1_COUNT.keys())}")

        if htf_duration_minutes <= self.ltf_duration_minutes:
            raise ValueError(
                f"HTF duration ({htf_tf}={htf_duration_minutes}m) must be strictly greater than "
                f"LTF duration ({self.ltf_timeframe}={self.ltf_duration_minutes}m)."
            )

        # Select columns to merge
        if feature_columns is None:
            excluded = {"open", "high", "low", "close", "volume", "bar_count", "is_complete"}
            feature_cols = [c for c in htf_df.columns if c != "timestamp" and c not in excluded]
        else:
            feature_cols = [c for c in feature_columns if c in htf_df.columns]

        if not feature_cols:
            logger.warning("No feature columns to align from %s", htf_timeframe)
            return ltf_df.copy()

        # Compute availability timestamp: candle start + candle duration
        htf_prep = htf_df[["timestamp"] + feature_cols].copy()
        duration_delta = pd.Timedelta(minutes=htf_duration_minutes)
        htf_prep["_available_timestamp"] = htf_prep["timestamp"] + duration_delta

        # Rename feature columns with prefix to avoid collision
        col_prefix = prefix or f"htf_{htf_tf.lower()}_"
        rename_map = {col: f"{col_prefix}{col}" for col in feature_cols}
        htf_prep = htf_prep.rename(columns=rename_map)

        # Sort both DataFrames by timestamp for merge_asof
        ltf_sorted = ltf_df.sort_values("timestamp").copy()
        htf_prep = htf_prep.sort_values("_available_timestamp").reset_index(drop=True)

        # Ensure both timestamp columns are in UTC
        if ltf_sorted["timestamp"].dt.tz is None:
            ltf_sorted["timestamp"] = ltf_sorted["timestamp"].dt.tz_localize("UTC")
        if htf_prep["_available_timestamp"].dt.tz is None:
            htf_prep["_available_timestamp"] = htf_prep["_available_timestamp"].dt.tz_localize("UTC")

        # Backward as-of merge:
        # For each LTF row at t_ltf, matches the latest HTF row where _available_timestamp <= t_ltf.
        # Enforces max_staleness tolerance to reject anomalous missing periods.
        merged = pd.merge_asof(
            ltf_sorted,
            htf_prep[["_available_timestamp"] + list(rename_map.values())],
            left_on="timestamp",
            right_on="_available_timestamp",
            direction="backward",
            tolerance=self.max_staleness,
        )

        merged = merged.drop(columns=["_available_timestamp"])
        return merged
