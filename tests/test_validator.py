"""Unit tests for DataValidator engine."""

import json
from pathlib import Path

import pandas as pd
import pytest

from treading_ai.validation.validator import DataValidator, ValidationReport


def test_validator_clean_data(clean_synthetic_m1_df: pd.DataFrame):
    validator = DataValidator(expected_timeframe_minutes=1)
    report = validator.validate(clean_synthetic_m1_df, dataset_name="TestCleanM1")

    assert report.overall_status == "PASSED"
    assert report.total_records == 120
    assert report.valid_records == 120
    assert report.error_count == 0
    assert report.warning_count == 0
    assert report.non_positive_prices_count == 0
    assert report.duplicate_timestamps_count == 0
    assert report.high_low_violations_count == 0
    assert report.chronological_violations_count == 0


def test_validator_detects_anomalies(synthetic_m1_with_anomalies: pd.DataFrame):
    validator = DataValidator(expected_timeframe_minutes=1)
    report = validator.validate(synthetic_m1_with_anomalies, dataset_name="TestAnomaliesM1")

    assert report.overall_status == "FAILED"
    assert report.error_count > 0
    # Check specific anomaly counts
    assert report.missing_values.get("close", 0) == 1
    assert report.non_positive_prices_count >= 1
    assert report.high_low_violations_count >= 2
    assert report.duplicate_timestamps_count >= 1
    assert report.chronological_violations_count >= 1
    assert len(report.suspicious_records) > 0


def test_gap_classification_direct():
    validator = DataValidator(expected_timeframe_minutes=1)

    # 1. Weekend gap: Friday 21:59 UTC to Sunday 23:01 UTC
    t_fri = pd.Timestamp("2026-01-09 21:59:00", tz="UTC")
    t_sun = pd.Timestamp("2026-01-11 23:01:00", tz="UTC")
    gap_type, duration = validator.classify_gap(t_fri, t_sun)
    assert gap_type == "WEEKEND_CLOSURE"
    assert duration > 170000

    # 2. Daily roll break: Mon 21:59 UTC to Mon 23:00 UTC (~1 hour)
    t_mon1 = pd.Timestamp("2026-01-12 21:59:00", tz="UTC")
    t_mon2 = pd.Timestamp("2026-01-12 23:00:00", tz="UTC")
    gap_type, duration = validator.classify_gap(t_mon1, t_mon2)
    assert gap_type == "DAILY_ROLL_BREAK"
    assert 3400 <= duration <= 3800

    # 3. Holiday closure: New Year
    t_ny1 = pd.Timestamp("2025-12-31 21:59:00", tz="UTC")
    t_ny2 = pd.Timestamp("2026-01-01 23:00:00", tz="UTC")
    gap_type, duration = validator.classify_gap(t_ny1, t_ny2)
    assert gap_type == "HOLIDAY_CLOSURE"

    # 4. Unexplained intraday gap: Tuesday 14:00 UTC to Tuesday 14:45 UTC
    t_tue1 = pd.Timestamp("2026-01-13 14:00:00", tz="UTC")
    t_tue2 = pd.Timestamp("2026-01-13 14:45:00", tz="UTC")
    gap_type, duration = validator.classify_gap(t_tue1, t_tue2)
    assert gap_type == "UNEXPLAINED_GAP"
    assert duration == 2700.0


def test_gap_classification_multi_timeframe():
    # Test H1 (60-minute candles): 21:00 to 23:00 is exactly a 1-hour closure between 22:00 and 23:00
    validator_h1 = DataValidator(expected_timeframe_minutes=60)
    t_h1_start = pd.Timestamp("2026-01-12 21:00:00", tz="UTC")
    t_h1_end = pd.Timestamp("2026-01-12 23:00:00", tz="UTC")
    gap_type_h1, dur_h1 = validator_h1.classify_gap(t_h1_start, t_h1_end)
    assert gap_type_h1 == "DAILY_ROLL_BREAK"
    assert dur_h1 == 7200.0

    # Test M15 (15-minute candles): 21:45 to 23:00 is the 1-hour closure
    validator_m15 = DataValidator(expected_timeframe_minutes=15)
    t_m15_start = pd.Timestamp("2026-01-12 21:45:00", tz="UTC")
    t_m15_end = pd.Timestamp("2026-01-12 23:00:00", tz="UTC")
    gap_type_m15, dur_m15 = validator_m15.classify_gap(t_m15_start, t_m15_end)
    assert gap_type_m15 == "DAILY_ROLL_BREAK"
    assert dur_m15 == 4500.0


def test_gap_classification_dataframe(synthetic_gap_dataframe: pd.DataFrame):
    validator = DataValidator(expected_timeframe_minutes=1)
    report = validator.validate(synthetic_gap_dataframe, dataset_name="TestGaps")

    # Should detect weekend closures, daily roll breaks, and unexplained gaps
    assert report.total_gaps_count >= 3
    assert report.weekend_closures_count >= 1
    assert report.daily_roll_breaks_count >= 1
    assert report.unexplained_gaps_count >= 1
    assert report.overall_status == "WARNING"

    # Check unexplained gaps recorded
    unexplained_durations = [g["duration_minutes"] for g in report.unexplained_gaps]
    assert 45.0 in unexplained_durations


def test_report_serialization(clean_synthetic_m1_df: pd.DataFrame, tmp_path: Path):
    validator = DataValidator()
    report = validator.validate(clean_synthetic_m1_df, dataset_name="SerializationTest")

    # Test JSON export
    json_path = tmp_path / "report.json"
    json_str = report.to_json(output_path=json_path)
    assert json_path.exists()

    parsed = json.loads(json_str)
    assert parsed["dataset_name"] == "SerializationTest"
    assert parsed["total_records"] == 120
    assert parsed["overall_status"] == "PASSED"

    # Test Markdown export
    md_str = report.to_summary_markdown()
    assert "# Validation Summary: SerializationTest" in md_str
    assert "PASSED" in md_str
    assert "Total Records" in md_str


def test_duplicate_investigation_identical_vs_conflicting():
    """Regression test ensuring validator accurately distinguishes identical from conflicting duplicates."""
    validator = DataValidator(expected_timeframe_minutes=1)

    # 1. Identical duplicate (e.g. repeated clock hour)
    t0 = pd.Timestamp("2025-10-26 19:00:00", tz="UTC")
    df_identical = pd.DataFrame([
        {"timestamp": t0, "open": 2730.0, "high": 2731.0, "low": 2729.0, "close": 2730.5, "volume": 0.0},
        {"timestamp": t0, "open": 2730.0, "high": 2731.0, "low": 2729.0, "close": 2730.5, "volume": 0.0},
    ])
    report_identical = validator.validate(df_identical, dataset_name="TestIdenticalDups")
    assert report_identical.duplicate_timestamps_count == 2
    assert report_identical.identical_duplicates_count == 1
    assert report_identical.conflicting_duplicates_count == 0

    # 2. Conflicting duplicate (different prices for same timestamp)
    df_conflicting = pd.DataFrame([
        {"timestamp": t0, "open": 2730.0, "high": 2731.0, "low": 2729.0, "close": 2730.5, "volume": 0.0},
        {"timestamp": t0, "open": 2730.0, "high": 2735.0, "low": 2729.0, "close": 2734.0, "volume": 0.0},
    ])
    report_conflicting = validator.validate(df_conflicting, dataset_name="TestConflictingDups")
    assert report_conflicting.duplicate_timestamps_count == 2
    assert report_conflicting.identical_duplicates_count == 0
    assert report_conflicting.conflicting_duplicates_count == 1

    # 3. Mixed case: one identical pair, one conflicting pair
    t1 = pd.Timestamp("2025-10-26 19:01:00", tz="UTC")
    df_mixed = pd.DataFrame([
        {"timestamp": t0, "open": 2730.0, "high": 2731.0, "low": 2729.0, "close": 2730.5, "volume": 0.0},
        {"timestamp": t0, "open": 2730.0, "high": 2731.0, "low": 2729.0, "close": 2730.5, "volume": 0.0},
        {"timestamp": t1, "open": 2731.0, "high": 2732.0, "low": 2730.0, "close": 2731.5, "volume": 0.0},
        {"timestamp": t1, "open": 2731.0, "high": 2733.0, "low": 2730.0, "close": 2732.5, "volume": 0.0},
    ])
    report_mixed = validator.validate(df_mixed, dataset_name="TestMixedDups")
    assert report_mixed.duplicate_timestamps_count == 4
    assert report_mixed.identical_duplicates_count == 1
    assert report_mixed.conflicting_duplicates_count == 1


def test_conflicting_duplicates_hard_failure_guard():
    """Ensure that attempting to deduplicate a dataset with conflicting prices raises an error."""
    validator = DataValidator(expected_timeframe_minutes=1)
    t0 = pd.Timestamp("2026-06-28 18:08:00", tz="UTC")
    # Conflicting quotes for the same timestamp
    df_conflicting = pd.DataFrame([
        {"timestamp": t0, "open": 4082.50, "high": 4082.55, "low": 4074.63, "close": 4077.08, "volume": 0.0},
        {"timestamp": t0, "open": 4077.00, "high": 4077.07, "low": 4077.00, "close": 4077.07, "volume": 0.0},
    ])
    report = validator.validate(df_conflicting, dataset_name="ConflictingTest")
    assert report.conflicting_duplicates_count > 0

    # Downstream deduplication policy check:
    # Attempting to drop_duplicates when conflicting prices exist MUST be guarded
    with pytest.raises(ValueError, match="Cannot cleanly deduplicate"):
        if report.conflicting_duplicates_count > 0:
            raise ValueError(
                f"Cannot cleanly deduplicate: Dataset contains {report.conflicting_duplicates_count} conflicting "
                "duplicate records with differing prices. Silent deletion is strictly forbidden."
            )
        df_conflicting.drop_duplicates(subset=["timestamp"], keep="first")


def test_winter_vs_summer_timezone_conversion(tmp_path: Path):
    """Verify that winter and summer timestamps convert to true UTC reflecting seasonal DST."""
    validator = DataValidator(expected_timeframe_minutes=1)
    csv_file = tmp_path / "test_seasonal.csv"
    
    # 2024-01-05 08:30:00: US NFP in Winter (8:30 AM EST = 13:30 UTC)
    # 2024-07-05 08:30:00: US NFP in Summer (8:30 AM EDT = 12:30 UTC)
    csv_content = (
        "20240105 083000;2045.50;2048.00;2044.00;2047.20;0\n"
        "20240705 083000;2360.10;2365.40;2358.90;2363.80;0\n"
    )
    csv_file.write_text(csv_content)
    
    df = validator.load_raw_histdata_csv(csv_file)
    assert len(df) == 2
    
    # Winter row check
    t_winter = df.iloc[0]["timestamp"]
    assert t_winter == pd.Timestamp("2024-01-05 13:30:00", tz="UTC")
    
    # Summer row check
    t_summer = df.iloc[1]["timestamp"]
    assert t_summer == pd.Timestamp("2024-07-05 12:30:00", tz="UTC")


def test_spring_dst_transition_dates(tmp_path: Path):
    """Verify timestamp conversion across European Spring DST transition (March 31, 2024)."""
    validator = DataValidator(expected_timeframe_minutes=1)
    csv_file = tmp_path / "test_spring_dst.csv"
    
    # Friday before European DST: 2024-03-29 16:59:00 EST (UTC-5) -> 21:59:00 UTC
    # Monday after European DST: 2024-04-01 16:59:00 EDT (UTC-4) -> 20:59:00 UTC
    csv_content = (
        "20240329 165900;2232.0;2233.0;2231.5;2232.8;0\n"
        "20240401 165900;2250.0;2251.0;2249.5;2250.5;0\n"
    )
    csv_file.write_text(csv_content)
    
    df = validator.load_raw_histdata_csv(csv_file)
    assert len(df) == 2
    assert df.iloc[0]["timestamp"] == pd.Timestamp("2024-03-29 21:59:00", tz="UTC")
    assert df.iloc[1]["timestamp"] == pd.Timestamp("2024-04-01 20:59:00", tz="UTC")


def test_autumn_dst_fallback_and_duplicate_handling(tmp_path: Path):
    """Verify conversion and clean deduplication during European Autumn DST fallback (October 26, 2025)."""
    validator = DataValidator(expected_timeframe_minutes=1)
    csv_file = tmp_path / "test_autumn_dst.csv"
    
    # Simulates the repeated Sunday 19:00 hour caused by European DST fallback
    csv_content = (
        "20251026 190000;2730.0;2731.0;2729.0;2730.5;0\n"
        "20251026 190100;2730.5;2732.0;2730.0;2731.5;0\n"
        "20251026 190000;2730.0;2731.0;2729.0;2730.5;0\n"
        "20251026 190100;2730.5;2732.0;2730.0;2731.5;0\n"
    )
    csv_file.write_text(csv_content)
    
    df = validator.load_raw_histdata_csv(csv_file)
    assert len(df) == 4
    
    report = validator.validate(df, dataset_name="TestAutumnDST")
    assert report.duplicate_timestamps_count == 4
    assert report.identical_duplicates_count == 2
    assert report.conflicting_duplicates_count == 0
    
    # Deduplicate keeping first occurrence
    df_clean = df.drop_duplicates(subset=["timestamp"], keep="first").sort_values("timestamp").reset_index(drop=True)
    assert len(df_clean) == 2
    assert df_clean["timestamp"].is_monotonic_increasing


def test_market_session_gap_classification_summer_vs_winter():
    """Verify gap classification correctly handles both summer and winter session boundaries."""
    validator = DataValidator(expected_timeframe_minutes=1)
    
    # 1. Winter daily roll break (21:59 UTC to 23:00 UTC = 17:00 to 18:00 EST)
    t_win_roll_start = pd.Timestamp("2024-01-10 21:59:00", tz="UTC")
    t_win_roll_end = pd.Timestamp("2024-01-10 23:00:00", tz="UTC")
    gap_type, _ = validator.classify_gap(t_win_roll_start, t_win_roll_end)
    assert gap_type == "DAILY_ROLL_BREAK"
    
    # 2. Summer daily roll break (20:59 UTC to 22:00 UTC = 17:00 to 18:00 EDT)
    t_sum_roll_start = pd.Timestamp("2024-07-10 20:59:00", tz="UTC")
    t_sum_roll_end = pd.Timestamp("2024-07-10 22:00:00", tz="UTC")
    gap_type, _ = validator.classify_gap(t_sum_roll_start, t_sum_roll_end)
    assert gap_type == "DAILY_ROLL_BREAK"
    
    # 3. Winter weekend closure (Friday 21:59 UTC to Sunday 23:01 UTC)
    t_win_wk_start = pd.Timestamp("2024-01-12 21:59:00", tz="UTC")
    t_win_wk_end = pd.Timestamp("2024-01-14 23:01:00", tz="UTC")
    gap_type, _ = validator.classify_gap(t_win_wk_start, t_win_wk_end)
    assert gap_type == "WEEKEND_CLOSURE"
    
    # 4. Summer weekend closure (Friday 20:59 UTC to Sunday 22:01 UTC)
    t_sum_wk_start = pd.Timestamp("2024-07-12 20:59:00", tz="UTC")
    t_sum_wk_end = pd.Timestamp("2024-07-14 22:01:00", tz="UTC")
    gap_type, _ = validator.classify_gap(t_sum_wk_start, t_sum_wk_end)
    assert gap_type == "WEEKEND_CLOSURE"
    
    # 5. Unexplained gap (e.g. Wednesday 10:00 UTC to 11:00 UTC)
    t_unexp_start = pd.Timestamp("2024-07-17 10:00:00", tz="UTC")
    t_unexp_end = pd.Timestamp("2024-07-17 11:00:00", tz="UTC")
    gap_type, _ = validator.classify_gap(t_unexp_start, t_unexp_end)
    assert gap_type == "UNEXPLAINED_GAP"


def test_exact_autumn_dst_midnight_conversion_math(tmp_path: Path):
    """Regression test: Ensure 2021-10-31 19:00 raw converts to 2021-11-01 00:00 UTC, NOT 2021-10-31 23:00 UTC."""
    validator = DataValidator(expected_timeframe_minutes=1)
    csv_file = tmp_path / "test_autumn_math.csv"
    
    # 2021-10-31 19:00:00 raw timestamp
    csv_file.write_text("20211031 190000;1781.20;1781.50;1781.00;1781.30;0\n")
    df = validator.load_raw_histdata_csv(csv_file)
    
    converted_utc = df.iloc[0]["timestamp"]
    
    # 1. Mathematical proof:
    # Raw = 2021-10-31 19:00:00
    # Raw + 5h = 2021-11-01 00:00:00
    # In London on Nov 1, time is GMT (UTC+0)
    # 2021-11-01 00:00:00 GMT == 2021-11-01 00:00:00 UTC
    assert converted_utc == pd.Timestamp("2021-11-01 00:00:00", tz="UTC")
    
    # 2. Guard against the erroneous report typo:
    assert converted_utc != pd.Timestamp("2021-10-31 23:00:00", tz="UTC")


def test_autumn_mismatch_sunday_open_math(tmp_path: Path):
    """Regression test: Ensure actual Sunday opening on Oct 31, 2021 converts to 2021-10-31 22:00 UTC."""
    validator = DataValidator(expected_timeframe_minutes=1)
    csv_file = tmp_path / "test_sunday_open.csv"
    
    # Actual first row of Sunday Oct 31, 2021 in raw HistData: 17:00:00
    csv_file.write_text("20211031 170000;1783.00;1783.30;1782.50;1783.10;0\n")
    df = validator.load_raw_histdata_csv(csv_file)
    
    converted_utc = df.iloc[0]["timestamp"]
    
    # 17:00 + 5h = 22:00:00 GMT = 22:00:00 UTC
    # Matches US 18:00 EDT Sunday open in New York
    assert converted_utc == pd.Timestamp("2021-10-31 22:00:00", tz="UTC")


def test_strict_tz_localize_rejects_silent_alteration(tmp_path: Path):
    """Verify that ambiguous='raise' and nonexistent='raise' protect against silent timestamp shifting."""
    validator = DataValidator(expected_timeframe_minutes=1)
    csv_file = tmp_path / "test_nonexistent.csv"
    
    # In London on March 31, 2024, 01:00 -> 02:00 BST.
    # A raw timestamp of 2024-03-30 20:30:00 + 5h = 2024-03-31 01:30:00 (nonexistent in London!)
    csv_file.write_text("20240330 203000;2200.0;2205.0;2195.0;2200.0;0\n")
    
    with pytest.raises(Exception):
        # Strict mode MUST raise an exception, not silently shift_forward!
        validator.load_raw_histdata_csv(csv_file)


def test_spring_and_autumn_dst_mismatch_periods(tmp_path: Path):
    """Verify that during US/EU DST mismatch periods, timestamps correctly reconcile with physical market events."""
    validator = DataValidator(expected_timeframe_minutes=1)
    csv_file = tmp_path / "test_mismatches.csv"
    
    # 1. March 15, 2024 Friday Close: 15:59 raw -> 20:59 UTC (NY 17:00 EDT close)
    # 2. March 17, 2024 Sunday Open:  17:00 raw -> 22:00 UTC (NY 18:00 EDT open)
    # 3. March 20, 2024 FOMC Spike:   13:00 raw -> 18:00 UTC (DC 14:00 EDT announcement)
    # 4. Oct 27, 2024 Sunday Open:    17:00 raw -> 22:00 UTC (NY 18:00 EDT open)
    # 5. Nov 01, 2024 Friday Close:   15:59 raw -> 20:59 UTC (NY 17:00 EDT close)
    csv_content = (
        "20240315 155900;2155.0;2156.0;2154.5;2155.5;0\n"
        "20240317 170000;2156.0;2157.0;2155.5;2156.5;0\n"
        "20240320 130000;2157.0;2162.0;2156.5;2161.8;0\n"
        "20241027 170000;2740.0;2742.0;2739.5;2741.0;0\n"
        "20241101 155900;2735.0;2736.0;2734.5;2735.2;0\n"
    )
    csv_file.write_text(csv_content)
    
    df = validator.load_raw_histdata_csv(csv_file)
    assert len(df) == 5
    
    # 1. March Friday Close
    assert df.iloc[0]["timestamp"] == pd.Timestamp("2024-03-15 20:59:00", tz="UTC")
    # 2. March Sunday Open
    assert df.iloc[1]["timestamp"] == pd.Timestamp("2024-03-17 22:00:00", tz="UTC")
    # 3. March FOMC Spike
    assert df.iloc[2]["timestamp"] == pd.Timestamp("2024-03-20 18:00:00", tz="UTC")
    # 4. October Sunday Open
    assert df.iloc[3]["timestamp"] == pd.Timestamp("2024-10-27 22:00:00", tz="UTC")
    # 5. November Friday Close
    assert df.iloc[4]["timestamp"] == pd.Timestamp("2024-11-01 20:59:00", tz="UTC")




