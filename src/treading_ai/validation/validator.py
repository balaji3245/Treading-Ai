"""Automated data validation engine for financial market OHLC datasets.

Performs comprehensive mathematical, integrity, and temporal validation on
historical candles, distinguishing legitimate market closures from data gaps.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from treading_ai.config import (
    DAILY_ROLL_END_HOUR_UTC,
    DAILY_ROLL_START_HOUR_UTC,
    HISTDATA_CSV_COLUMNS,
    HISTDATA_CSV_SEP,
    HISTDATA_DATETIME_FORMAT,
    OHLC_COLUMNS,
    REPORTS_DIR,
    WEEKEND_CLOSE_DAY_UTC,
    WEEKEND_CLOSE_HOUR_UTC,
    WEEKEND_OPEN_DAY_UTC,
    WEEKEND_OPEN_HOUR_UTC,
)

logger = logging.getLogger(__name__)


@dataclass
class GapRecord:
    start: str
    end: str
    duration_seconds: float
    duration_minutes: float
    gap_type: str  # 'WEEKEND_CLOSURE', 'DAILY_ROLL_BREAK', 'HOLIDAY_CLOSURE', 'UNEXPLAINED_GAP'
    start_weekday: str
    end_weekday: str


@dataclass
class ValidationReport:
    overall_status: str  # 'PASSED', 'WARNING', 'FAILED'
    dataset_name: str
    total_records: int
    valid_records: int
    error_count: int
    warning_count: int
    start_timestamp: Optional[str] = None
    end_timestamp: Optional[str] = None
    missing_values: Dict[str, int] = field(default_factory=dict)
    duplicate_timestamps_count: int = 0
    identical_duplicates_count: int = 0
    conflicting_duplicates_count: int = 0
    non_positive_prices_count: int = 0
    high_low_violations_count: int = 0
    chronological_violations_count: int = 0
    total_gaps_count: int = 0
    weekend_closures_count: int = 0
    daily_roll_breaks_count: int = 0
    holiday_closures_count: int = 0
    unexplained_gaps_count: int = 0
    suspicious_records: List[Dict[str, Any]] = field(default_factory=list)
    unexplained_gaps: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self, output_path: Optional[Path] = None) -> str:
        data = self.to_dict()
        json_str = json.dumps(data, indent=2)
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(json_str)
        return json_str

    def to_summary_markdown(self) -> str:
        status_badge = {
            "PASSED": "PASSED (Clean)",
            "WARNING": "WARNING (Non-critical anomalies / Unexplained gaps)",
            "FAILED": "FAILED (Integrity violations)",
        }.get(self.overall_status, self.overall_status)

        md = [
            f"# Validation Summary: {self.dataset_name}",
            "",
            f"**Overall Status**: {status_badge}",
            f"- **Total Records**: {self.total_records:,}",
            f"- **Valid Records**: {self.valid_records:,}",
            f"- **Date Range**: {self.start_timestamp} to {self.end_timestamp}",
            f"- **Errors**: {self.error_count}",
            f"- **Warnings**: {self.warning_count}",
            "",
            "## Data Integrity Checks",
            "| Check | Result | Details |",
            "| :--- | :---: | :--- |",
            f"| Missing / Null Values | {'PASS' if sum(self.missing_values.values()) == 0 else 'FAIL'} | {self.missing_values} |",
            f"| Duplicate Timestamps | {'PASS' if self.duplicate_timestamps_count == 0 else 'FAIL'} | {self.duplicate_timestamps_count} duplicates ({self.identical_duplicates_count} identical, {self.conflicting_duplicates_count} conflicting) |",
            f"| Non-positive Prices (<= 0) | {'PASS' if self.non_positive_prices_count == 0 else 'FAIL'} | {self.non_positive_prices_count} invalid prices |",
            f"| High/Low Logic Violations | {'PASS' if self.high_low_violations_count == 0 else 'FAIL'} | {self.high_low_violations_count} candles violated High/Low logic |",
            f"| Chronological Ordering | {'PASS' if self.chronological_violations_count == 0 else 'FAIL'} | {self.chronological_violations_count} out-of-order records |",
            "",
            "## Market Gap & Session Analysis",
            f"- **Total Gaps Detected (> 1 min)**: {self.total_gaps_count}",
            f"- **Weekend Closures (Legitimate)**: {self.weekend_closures_count}",
            f"- **Daily Session Roll Breaks (~1h Legitimate)**: {self.daily_roll_breaks_count}",
            f"- **Holiday Closures (Legitimate)**: {self.holiday_closures_count}",
            f"- **Unexplained Gaps**: {self.unexplained_gaps_count}",
            "",
        ]

        if self.unexplained_gaps:
            md.append("### Unexplained Gaps Details (Top 10):")
            md.append("| Start (UTC) | End (UTC) | Duration (min) | Start Day | End Day |")
            md.append("| :--- | :--- | :---: | :---: | :---: |")
            for g in self.unexplained_gaps[:10]:
                md.append(f"| {g['start']} | {g['end']} | {g['duration_minutes']:.1f} | {g['start_weekday']} | {g['end_weekday']} |")
            md.append("")

        if self.suspicious_records:
            md.append(f"### Suspicious Records Sample (Showing {min(len(self.suspicious_records), 5)} of {len(self.suspicious_records)}):")
            for r in self.suspicious_records[:5]:
                md.append(f"- **Index {r.get('index')}** ({r.get('timestamp')}): {r.get('issue')} | Values: Open={r.get('open')}, High={r.get('high')}, Low={r.get('low')}, Close={r.get('close')}")
            md.append("")

        return "\n".join(md)


class DataValidator:
    """Automated validator for financial market OHLC datasets."""

    def __init__(self, expected_timeframe_minutes: int = 1):
        self.expected_interval_seconds = expected_timeframe_minutes * 60

    def load_raw_histdata_csv(self, filepath: Union[str, Path]) -> pd.DataFrame:
        """Load a raw HistData M1 CSV file without modifying original values.

        Raw HistData format:
        DateTime;Open;High;Low;Close;Volume
        YYYYMMDD HHMMSS;float;float;float;float;int
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        df = pd.read_csv(
            filepath,
            sep=HISTDATA_CSV_SEP,
            header=None,
            names=HISTDATA_CSV_COLUMNS,
            dtype={
                "datetime_str": str,
                "open": np.float64,
                "high": np.float64,
                "low": np.float64,
                "close": np.float64,
                "volume": np.float64,
            },
        )
        # Convert raw timestamps to true UTC:
        # Provenance Evidence:
        # HistData raw timestamps originate from an interbank feeder server aligned to European DST
        # (Europe/London with a -5h offset: UTC-5 in European winter, UTC-4 in European summer).
        # Shifting naive timestamps by +5h aligns them with Europe/London local time, which is then
        # converted to true UTC with seasonal Daylight Saving Time accuracy.
        dt_naive = pd.to_datetime(df["datetime_str"], format=HISTDATA_DATETIME_FORMAT)
        london_naive = dt_naive + pd.Timedelta(hours=5)
        london_tz = ZoneInfo("Europe/London")
        df["timestamp"] = london_naive.dt.tz_localize(
            london_tz, ambiguous="raise", nonexistent="raise"
        ).dt.tz_convert(timezone.utc)
        df = df[OHLC_COLUMNS]
        return df

    def classify_gap(self, t_start: pd.Timestamp, t_end: pd.Timestamp) -> Tuple[str, float]:
        """Classify a market data gap into legitimate market closures or unexplained gap.

        Parameters
        ----------
        t_start : pd.Timestamp
            The timestamp of the last candle before the gap (must be UTC).
        t_end : pd.Timestamp
            The timestamp of the first candle after the gap (must be UTC).

        Returns
        -------
        Tuple[str, float]
            (gap_type, duration_seconds)
        """
        # Ensure UTC
        if t_start.tzinfo is None:
            t_start = t_start.tz_localize(timezone.utc)
        else:
            t_start = t_start.tz_convert(timezone.utc)
        if t_end.tzinfo is None:
            t_end = t_end.tz_localize(timezone.utc)
        else:
            t_end = t_end.tz_convert(timezone.utc)

        duration = (t_end - t_start).total_seconds()
        candle_end = t_start + timedelta(seconds=self.expected_interval_seconds)
        closure_seconds = (t_end - candle_end).total_seconds()

        start_day = t_start.weekday()  # Monday is 0, Sunday is 6
        start_hour = t_start.hour
        end_day = t_end.weekday()
        end_hour = t_end.hour

        # 1. Weekend Closure: Friday ~21:00/22:00 UTC to Sunday ~22:00/23:00 UTC
        # Accounts for summer (close ~21:00 UTC, open ~22:00 UTC) and winter (close ~22:00 UTC, open ~23:00 UTC)
        if (start_day == 4 and start_hour >= 20) and (
            (end_day == 6 and end_hour >= 21) or (end_day == 0 and end_hour <= 1)
        ):
            return "WEEKEND_CLOSURE", duration

        # 2. Daily Roll Break: Mon-Thu between 21:00-22:00 UTC (Summer / EDT) or 22:00-23:00 UTC (Winter / EST) (~3600 seconds closure)
        # Accounts for base candle duration across any timeframe (M1, M5, M15, M30, H1)
        if 3400 <= closure_seconds <= 3800 or (3400 <= duration <= 3800 and self.expected_interval_seconds == 60):
            if start_day in [0, 1, 2, 3]:
                if (start_hour in [20, 21, 22] and end_hour in [21, 22, 23, 0]):
                    return "DAILY_ROLL_BREAK", duration

        # 3. Known Major Holidays (Christmas Dec 25, New Year Jan 1)
        if (t_start.month == 12 and t_start.day >= 24 and t_end.day >= 26) or (
            t_start.month == 12 and t_start.day == 31 and t_end.month == 1 and t_end.day <= 2
        ):
            return "HOLIDAY_CLOSURE", duration

        return "UNEXPLAINED_GAP", duration

    def validate(self, df: pd.DataFrame, dataset_name: str = "XAUUSD_M1") -> ValidationReport:
        """Run complete mathematical and temporal validation suite on OHLC DataFrame.

        Parameters
        ----------
        df : pd.DataFrame
            DataFrame containing OHLC columns: timestamp, open, high, low, close, volume.
        dataset_name : str
            Descriptive dataset name for reporting.

        Returns
        -------
        ValidationReport
            Comprehensive structured validation report.
        """
        report = ValidationReport(
            overall_status="PASSED",
            dataset_name=dataset_name,
            total_records=len(df),
            valid_records=len(df),
            error_count=0,
            warning_count=0,
        )

        if df.empty:
            report.overall_status = "FAILED"
            report.error_count += 1
            report.suspicious_records.append({"issue": "Dataset is completely empty"})
            return report

        # Check required columns
        missing_cols = [c for c in OHLC_COLUMNS if c not in df.columns]
        if missing_cols:
            report.overall_status = "FAILED"
            report.error_count += 1
            report.suspicious_records.append({"issue": f"Missing required columns: {missing_cols}"})
            return report

        # 1. Missing / Null Values
        null_counts = df[OHLC_COLUMNS].isnull().sum().to_dict()
        report.missing_values = {col: int(cnt) for col, cnt in null_counts.items()}
        total_nulls = sum(null_counts.values())
        if total_nulls > 0:
            report.error_count += total_nulls
            null_rows = df[df.isnull().any(axis=1)].head(10)
            for idx, row in null_rows.iterrows():
                report.suspicious_records.append({
                    "index": int(idx),
                    "timestamp": str(row["timestamp"]),
                    "issue": "Null/NaN value detected",
                    "values": row.to_dict(),
                })

        # 2. Timestamp Validation
        if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
            try:
                df = df.copy()
                df["timestamp"] = pd.to_datetime(df["timestamp"])
            except Exception as e:
                report.error_count += 1
                report.suspicious_records.append({"issue": f"Timestamps could not be parsed as datetime: {e}"})

        # Record date range
        report.start_timestamp = str(df["timestamp"].iloc[0])
        report.end_timestamp = str(df["timestamp"].iloc[-1])

        # 3. Duplicate Timestamps
        duplicate_mask = df.duplicated(subset=["timestamp"], keep=False)
        report.duplicate_timestamps_count = int(duplicate_mask.sum())
        if report.duplicate_timestamps_count > 0:
            report.error_count += report.duplicate_timestamps_count
            
            # Group duplicates by timestamp to determine if values are identical or conflicting
            dup_df = df[duplicate_mask]
            value_cols = [c for c in ["open", "high", "low", "close", "volume"] if c in df.columns]
            grouped = dup_df.groupby("timestamp")
            
            conflicting_ts = 0
            identical_ts = 0
            for ts, grp in grouped:
                if grp[value_cols].nunique().max() > 1:
                    conflicting_ts += 1
                else:
                    identical_ts += 1
            
            report.conflicting_duplicates_count = conflicting_ts
            report.identical_duplicates_count = identical_ts

            dups = df[duplicate_mask].head(10)
            for idx, row in dups.iterrows():
                report.suspicious_records.append({
                    "index": int(idx),
                    "timestamp": str(row["timestamp"]),
                    "issue": "Duplicate timestamp",
                    "open": float(row["open"]),
                    "close": float(row["close"]),
                })

        # 4. Chronological Ordering
        is_monotonic = df["timestamp"].is_monotonic_increasing
        if not is_monotonic:
            report.error_count += 1
            # Find inversion points
            time_diffs = df["timestamp"].diff()
            inversion_indices = df.index[time_diffs < pd.Timedelta(0)].tolist()
            report.chronological_violations_count = len(inversion_indices)
            for idx in inversion_indices[:10]:
                report.suspicious_records.append({
                    "index": int(idx),
                    "timestamp": str(df.loc[idx, "timestamp"]),
                    "issue": "Timestamp is out of chronological order (earlier than preceding record)",
                })

        # 5. Price Sanity (Non-positive prices <= 0)
        non_pos_mask = (df["open"] <= 0) | (df["high"] <= 0) | (df["low"] <= 0) | (df["close"] <= 0)
        report.non_positive_prices_count = int(non_pos_mask.sum())
        if report.non_positive_prices_count > 0:
            report.error_count += report.non_positive_prices_count
            invalid_rows = df[non_pos_mask].head(10)
            for idx, row in invalid_rows.iterrows():
                report.suspicious_records.append({
                    "index": int(idx),
                    "timestamp": str(row["timestamp"]),
                    "issue": "Non-positive price (<= 0)",
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                })

        # 6. High-Low Consistency Checks
        # High >= max(Open, Close)
        # Low <= min(Open, Close)
        # High >= Low
        high_low_violation_mask = (
            (df["high"] < df["low"])
            | (df["high"] < df["open"])
            | (df["high"] < df["close"])
            | (df["low"] > df["open"])
            | (df["low"] > df["close"])
        )
        report.high_low_violations_count = int(high_low_violation_mask.sum())
        if report.high_low_violations_count > 0:
            report.error_count += report.high_low_violations_count
            hl_violators = df[high_low_violation_mask].head(10)
            for idx, row in hl_violators.iterrows():
                report.suspicious_records.append({
                    "index": int(idx),
                    "timestamp": str(row["timestamp"]),
                    "issue": "High/Low logic violated (High < max(Open,Close) or Low > min(Open,Close) or High < Low)",
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                })

        # 7. Market Data Gap Analysis
        # Calculate time diff between consecutive rows
        if is_monotonic and len(df) > 1:
            diffs = df["timestamp"].diff().dt.total_seconds()
            gap_mask = diffs > (self.expected_interval_seconds * 1.5)
            gap_indices = df.index[gap_mask].tolist()
            report.total_gaps_count = len(gap_indices)

            for idx in gap_indices:
                t_prev = df.loc[idx - 1, "timestamp"]
                t_curr = df.loc[idx, "timestamp"]
                gap_type, duration_sec = self.classify_gap(t_prev, t_curr)

                if gap_type == "WEEKEND_CLOSURE":
                    report.weekend_closures_count += 1
                elif gap_type == "DAILY_ROLL_BREAK":
                    report.daily_roll_breaks_count += 1
                elif gap_type == "HOLIDAY_CLOSURE":
                    report.holiday_closures_count += 1
                else:
                    report.unexplained_gaps_count += 1
                    report.warning_count += 1
                    report.unexplained_gaps.append({
                        "start": str(t_prev),
                        "end": str(t_curr),
                        "duration_seconds": duration_sec,
                        "duration_minutes": duration_sec / 60.0,
                        "start_weekday": t_prev.strftime("%A"),
                        "end_weekday": t_curr.strftime("%A"),
                    })

        # Calculate final valid records and overall status
        invalid_mask = duplicate_mask | non_pos_mask | high_low_violation_mask
        report.valid_records = int((~invalid_mask).sum())

        if report.error_count > 0:
            report.overall_status = "FAILED"
        elif report.warning_count > 0:
            report.overall_status = "WARNING"
        else:
            report.overall_status = "PASSED"

        return report
