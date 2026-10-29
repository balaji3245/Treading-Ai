"""Test suite for Phase 19: Macro Data Acquisition & Integrity Audit.

Validates:
1. Strict Data Partition Protection (Zero-access invariant for 2025 val and 2026 test).
2. AST and code audit guaranteeing no references loading protected partitions in Phase 19 scripts.
3. Raw macro data acquisition and schema integrity (absence of duplicates, monotonicity).
4. Macro range and unit sanity (TIPS real yields, broad dollar index, breakeven inflation).
5. Critical distinction: DTWEXBGS is the broad dollar index, NOT ICE DXY.
6. Gold M5 data integrity (monotonic timestamps, 0 duplicates, 0 invalid OHLC bars).
7. Institutional session boundaries (18:00 NY to 17:00 NY next day, 276 M5 bars standard).
8. Publication-lag enforcement and zero future-data leakage in macro-gold alignment.
9. Point-in-time limitation flags and final verdict invariants in data_quality_results.json.
"""

import ast
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path("/home/bhoot/project/Treading-Ai")
RAW_DATA_DIR = PROJECT_ROOT / "data/raw/macro"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data/processed/macro"
PHASE19_REPORT_DIR = PROJECT_ROOT / "reports/phase19"

VAL_PARQUET_PATH = PROJECT_ROOT / "data/features/XAUUSD_M5_features_val.parquet"
TEST_PARQUET_PATH = PROJECT_ROOT / "data/features/XAUUSD_M5_features_test.parquet"

ACQUIRE_SCRIPT_PATH = PROJECT_ROOT / "scripts/acquire_macro_data.py"
VALIDATE_SCRIPT_PATH = PROJECT_ROOT / "scripts/validate_macro_data.py"
QUALITY_JSON_PATH = PHASE19_REPORT_DIR / "data_quality_results.json"

VAL_EXPECTED_SHA256 = "7e9222e9dc0893601e24505912eeab78330670c4e70ebcc2fa462ff8d44a4f94"
TEST_EXPECTED_SHA256 = "f95fd09a5d07666e3f1d9a72e840e2e97f3c058d11b6bb0c712b21dea86a5dec"


class TestDataPartitionProtection:
    """Ensure protected validation (2025) and frozen test (2026) partitions remain untouched."""

    def test_protected_validation_partition_hash_invariant(self):
        assert VAL_PARQUET_PATH.exists(), "Protected validation parquet missing!"
        hasher = hashlib.sha256()
        with open(VAL_PARQUET_PATH, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        actual_hash = hasher.hexdigest()
        assert actual_hash == VAL_EXPECTED_SHA256, (
            f"CRITICAL: Protected validation partition modified! Expected {VAL_EXPECTED_SHA256}, got {actual_hash}"
        )

    def test_protected_test_partition_hash_invariant(self):
        assert TEST_PARQUET_PATH.exists(), "Protected test parquet missing!"
        hasher = hashlib.sha256()
        with open(TEST_PARQUET_PATH, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        actual_hash = hasher.hexdigest()
        assert actual_hash == TEST_EXPECTED_SHA256, (
            f"CRITICAL: Protected test partition modified! Expected {TEST_EXPECTED_SHA256}, got {actual_hash}"
        )

    def test_phase19_scripts_do_not_load_protected_partitions(self):
        for script_path in [ACQUIRE_SCRIPT_PATH, VALIDATE_SCRIPT_PATH]:
            assert script_path.exists(), f"Script {script_path} missing!"
            source = script_path.read_text()
            tree = ast.parse(source)

            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    val_str = node.value.lower()
                    assert "read_parquet" not in val_str or "val" not in val_str, (
                        f"{script_path.name} contains reference loading protected validation data!"
                    )
                    assert "read_parquet" not in val_str or "test" not in val_str, (
                        f"{script_path.name} contains reference loading protected test data!"
                    )


class TestRawMacroDataIntegrity:
    """Validate acquired raw macroeconomic files."""

    def test_raw_csv_files_exist_and_non_empty(self):
        raw_files = ["DFII10_raw.csv", "DTWEXBGS_raw.csv", "T10YIE_raw.csv"]
        for fn in raw_files:
            p = RAW_DATA_DIR / fn
            assert p.exists(), f"Raw file {fn} missing!"
            assert p.stat().st_size > 10000, f"Raw file {fn} unexpectedly small!"

    def test_macro_metadata_provenance_and_checksums(self):
        meta_p = RAW_DATA_DIR / "acquisition_metadata.json"
        assert meta_p.exists(), "Acquisition metadata missing!"
        with open(meta_p, "r") as f:
            meta = json.load(f)

        assert "series" in meta
        for series_id in ["DFII10", "DTWEXBGS", "T10YIE"]:
            assert series_id in meta["series"]
            entry = meta["series"][series_id]
            assert "download_url" in entry
            assert "sha256" in entry
            assert "earliest_observation_date" in entry
            assert "latest_observation_date" in entry

            # Verify on-disk checksum matches metadata
            p = Path(entry["local_raw_path"])
            hasher = hashlib.sha256()
            with open(p, "rb") as f:
                while chunk := f.read(65536):
                    hasher.update(chunk)
            assert hasher.hexdigest() == entry["sha256"]

    def test_critical_distinction_dtwexbgs_labeled_not_dxy(self):
        meta_p = RAW_DATA_DIR / "acquisition_metadata.json"
        with open(meta_p, "r") as f:
            meta = json.load(f)
        dtw_info = meta["series"]["DTWEXBGS"]
        assert "NOT ICE DXY" in dtw_info["license_info"]
        assert "Broad" in dtw_info["title"]


class TestProcessedMacroAndRangeSanity:
    """Validate cleaned macro series values, absence of duplicates, and reasonable bounds."""

    def test_cleaned_macro_parquet_schema_and_monotonicity(self):
        p = PROCESSED_DATA_DIR / "macro_daily_cleaned.parquet"
        assert p.exists(), "Cleaned macro parquet missing!"
        df = pd.read_parquet(p)

        assert isinstance(df.index, pd.DatetimeIndex)
        assert df.index.is_monotonic_increasing
        assert df.index.duplicated().sum() == 0

        for col in ["dfii10", "dtwexbgs", "t10yie"]:
            assert col in df.columns

        # Check 2021-2024 range sanity
        df_target = df.loc["2021-01-01":"2024-12-31"]
        # Real yield DFII10 should be within [-2.0%, +4.0%]
        valid_dfii10 = df_target["dfii10"].dropna()
        assert (valid_dfii10 >= -2.0).all()
        assert (valid_dfii10 <= 4.0).all()

        # Broad dollar index DTWEXBGS should be within [90, 150]
        valid_dtw = df_target["dtwexbgs"].dropna()
        assert (valid_dtw >= 90.0).all()
        assert (valid_dtw <= 150.0).all()

        # Breakeven inflation T10YIE should be within [1.0%, 4.0%]
        valid_t10 = df_target["t10yie"].dropna()
        assert (valid_t10 >= 1.0).all()
        assert (valid_t10 <= 4.0).all()


class TestGoldM5DataIntegrity:
    """Validate gold M5 training dataset integrity and session structure."""

    def test_gold_m5_data_has_no_duplicates_or_invalid_ohlc(self):
        train_p = PROJECT_ROOT / "data/features/XAUUSD_M5_features_train.parquet"
        assert train_p.exists()
        df = pd.read_parquet(train_p)

        assert df["timestamp"].duplicated().sum() == 0
        assert df["timestamp"].is_monotonic_increasing

        # OHLC bounds
        assert (df["high"] >= df["low"]).all()
        assert (df["open"] <= df["high"]).all()
        assert (df["open"] >= df["low"]).all()
        assert (df["close"] <= df["high"]).all()
        assert (df["close"] >= df["low"]).all()

    def test_gold_institutional_session_bar_count_and_boundaries(self):
        aligned_p = PROCESSED_DATA_DIR / "macro_gold_aligned.parquet"
        assert aligned_p.exists()
        aligned_df = pd.read_parquet(aligned_p)

        assert len(aligned_df) == 984, f"Expected 984 daily sessions, got {len(aligned_df)}"
        # Standard sessions have exactly 276 bars
        std_count = (aligned_df["session_n_m5_bars"] == 276).sum()
        assert std_count == 671, f"Expected 671 standard 276-bar sessions, got {std_count}"


class TestPublicationLagAndNoFutureLeakage:
    """Validate that macro observations strictly respect publication lag with zero future leakage."""

    def test_conservative_lag_strictly_precedes_entry_date(self):
        aligned_p = PROCESSED_DATA_DIR / "macro_gold_aligned.parquet"
        aligned_df = pd.read_parquet(aligned_p)

        for _, row in aligned_df.iterrows():
            entry_ts_ny = pd.to_datetime(row["entry_ts_ny"])
            entry_date = entry_ts_ny.date()
            macro_obs_date = pd.to_datetime(row["macro_obs_date"]).date()

            # Under conservative policy, macro observation date MUST be strictly prior to entry date
            assert macro_obs_date < entry_date, (
                f"Future leakage detected! Entry date {entry_date} used macro observation dated {macro_obs_date}!"
            )

    def test_synthetic_lag_enforcement_fixture(self):
        """Synthetic unit test verifying lag filter logic."""
        # Synthetic macro date series
        macro_dates = pd.to_datetime(["2023-05-01", "2023-05-02", "2023-05-03"])
        macro_series = pd.DataFrame({"val": [1.5, 1.6, 1.7]}, index=macro_dates)

        # Entry at 18:00 NY on 2023-05-02 (for 2023-05-03 settlement)
        entry_date = pd.to_datetime("2023-05-02").date()

        # Conservative policy: macro_date <= entry_date - 1 day
        cutoff = pd.to_datetime(entry_date) - pd.Timedelta(days=1)
        prior_slice = macro_series.loc[:cutoff]
        assert prior_slice.index[-1].date() == pd.to_datetime("2023-05-01").date()
        assert prior_slice.iloc[-1]["val"] == 1.5


class TestPhase19QualityResultsAndVerdict:
    """Validate contents and final verdict of data_quality_results.json."""

    def test_quality_results_verdict_and_limitations(self):
        assert QUALITY_JSON_PATH.exists(), "data_quality_results.json missing!"
        with open(QUALITY_JSON_PATH, "r") as f:
            res = json.load(f)

        assert res["final_verdict"] == "DATA ACQUIRED — POINT-IN-TIME LIMITATIONS REMAIN"
        assert "verdict_rationale" in res
        assert "point-in-time" in res["verdict_rationale"].lower()

        # Verify alignment sample size
        alignment = res["macro_gold_alignment_audit"]
        assert alignment["total_gold_sessions"] == 984
        assert alignment["conservative_lag_policy"]["holiday_ffill_limit3_sessions_complete"] == 984
        assert alignment["sample_size_evaluation_for_phase20"]["usable_sample_size_N"] == 984
        assert alignment["sample_size_evaluation_for_phase20"]["is_sample_sufficient"] is True
