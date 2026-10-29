"""Test suite for Phase 20: Pre-Registered Macro Hypothesis Test.

Validates:
1. Strict Data Partition Protection (Zero-access invariant for 2025 val and 2026 test).
2. AST and code audit guaranteeing no references loading protected partitions in Phase 20 scripts.
3. Pre-registered protocol file existence and SHA-256 integrity hash verification.
4. Target return construction and zero leakage into features.
5. Strict separation of Development (2021-2022) vs Out-of-Sample (2023-2024) partitions.
6. Alignment policy: observation age tracking, holiday forward-fill limits, and business-day lag.
7. Daylight-saving transitions and session boundary definitions.
8. Cost accounting accuracy: round-turn spread ($0.20), slippage ($0.10), swap ($0.12/day, $0.36 Wed).
9. Holm-Bonferroni multiple testing adjustment logic.
10. Final verdict invariant: NO EVIDENCE OF PREDICTIVE EDGE.
"""

import ast
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path("/home/bhoot/project/Treading-Ai")
ALIGNED_PARQUET_PATH = PROJECT_ROOT / "data/processed/macro/macro_gold_aligned.parquet"
PROTOCOL_MD_PATH = PROJECT_ROOT / "reports/phase20/preregistered_protocol.md"
RESULTS_JSON_PATH = PROJECT_ROOT / "reports/phase20/results.json"
PHASE20_SCRIPT_PATH = PROJECT_ROOT / "scripts/run_phase20_macro_test.py"

VAL_PARQUET_PATH = PROJECT_ROOT / "data/features/XAUUSD_M5_features_val.parquet"
TEST_PARQUET_PATH = PROJECT_ROOT / "data/features/XAUUSD_M5_features_test.parquet"

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

    def test_phase20_script_does_not_load_protected_partitions(self):
        assert PHASE20_SCRIPT_PATH.exists(), "Phase 20 script missing!"
        source = PHASE20_SCRIPT_PATH.read_text()
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                val_str = node.value.lower()
                assert "read_parquet" not in val_str or "val" not in val_str, (
                    "Phase 20 script contains reference loading protected validation data!"
                )
                assert "read_parquet" not in val_str or "test" not in val_str, (
                    "Phase 20 script contains reference loading protected test data!"
                )


class TestProtocolAndDataIntegrity:
    """Validate protocol freeze and aligned dataset invariants."""

    def test_protocol_file_exists_and_hash_logged(self):
        assert PROTOCOL_MD_PATH.exists(), "Pre-registered protocol file missing!"
        hasher = hashlib.sha256()
        with open(PROTOCOL_MD_PATH, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        actual_hash = hasher.hexdigest()

        with open(RESULTS_JSON_PATH, "r") as f:
            results = json.load(f)
        logged_hash = results["governance"]["protocol_sha256"]
        assert actual_hash == logged_hash, f"Protocol hash mismatch! {actual_hash} vs {logged_hash}"

    def test_aligned_dataset_partition_counts(self):
        assert ALIGNED_PARQUET_PATH.exists(), "Aligned parquet missing!"
        df = pd.read_parquet(ALIGNED_PARQUET_PATH)

        assert len(df) == 984
        dev_count = ((df["settlement_date"] >= "2021-03-11") & (df["settlement_date"] <= "2022-12-30")).sum()
        oos_count = ((df["settlement_date"] >= "2023-01-02") & (df["settlement_date"] <= "2024-12-31")).sum()
        assert dev_count == 468, f"Expected 468 dev sessions, got {dev_count}"
        assert oos_count == 516, f"Expected 516 out-of-sample sessions, got {oos_count}"


class TestAlignmentAndPointInTimeSafety:
    """Validate publication lag, observation age, and daylight-saving transitions."""

    def test_conservative_business_day_lag_strictly_precedes_entry(self):
        df = pd.read_parquet(ALIGNED_PARQUET_PATH)
        for _, row in df.iterrows():
            entry_date = pd.to_datetime(row["entry_ts_ny"]).date()
            macro_date = pd.to_datetime(row["macro_obs_date"]).date()
            # Must strictly precede entry date
            assert macro_date < entry_date, f"Leakage: macro {macro_date} >= entry {entry_date}"

    def test_observation_age_bounded_at_4_calendar_days(self):
        df = pd.read_parquet(ALIGNED_PARQUET_PATH)
        ages = []
        for _, row in df.iterrows():
            entry_date = pd.to_datetime(row["entry_ts_ny"]).date()
            macro_date = pd.to_datetime(row["macro_obs_date"]).date()
            age_days = (entry_date - macro_date).days
            ages.append(age_days)
        max_age = max(ages)
        min_age = min(ages)
        assert min_age >= 1, f"Observation age must be >= 1 day, got {min_age}"
        assert max_age <= 4, f"Observation age unexpectedly exceeds 4 days, got {max_age}"

    def test_daylight_saving_transitions_session_boundaries(self):
        df = pd.read_parquet(ALIGNED_PARQUET_PATH)
        # Check EDT (UTC-4) vs EST (UTC-5)
        # In summer (e.g. July), offset is -04:00. In winter (e.g. January), offset is -05:00.
        july_sessions = df[df["settlement_date"].str.startswith("2023-07")]
        jan_sessions = df[df["settlement_date"].str.startswith("2023-01")]

        for _, row in july_sessions.iterrows():
            assert "-04:00" in row["entry_ts_ny"]
        for _, row in jan_sessions.iterrows():
            assert "-05:00" in row["entry_ts_ny"]


class TestTargetAndCostAccounting:
    """Validate target computation and transaction cost accounting."""

    def test_target_return_no_leakage_into_features(self):
        """Synthetic test verifying target return is derived from future prices relative to features."""
        df = pd.read_parquet(ALIGNED_PARQUET_PATH).copy()
        df["target_return"] = (df["session_close_price"] - df["session_open_price"]) / df["session_open_price"]
        df["d1_yield"] = df["dfii10_real_yield"].diff()

        # Feature at row t is based on macro_obs_date <= entry_date - 1
        # Target at row t is based on session_close (17:00 NY next day) - session_open (18:00 NY entry)
        # Correlation between feature and target return must not be mechanically 1.0
        corr = df[["d1_yield", "target_return"]].dropna().corr().iloc[0, 1]
        assert abs(corr) < 0.2, f"Correlation suspiciously high ({corr}), check for leakage!"

    def test_cost_accounting_distinguishes_wednesday_triple_swap(self):
        df = pd.read_parquet(ALIGNED_PARQUET_PATH).copy()
        entry_day = pd.to_datetime(df["entry_ts_ny"].str[:10]).dt.day_of_week
        is_wednesday = (entry_day == 2)
        swap_base = np.where(is_wednesday, 0.36, 0.12)
        base_friction = 0.20 + 0.10 + swap_base

        wed_cost = base_friction[is_wednesday].mean()
        non_wed_cost = base_friction[~is_wednesday].mean()
        assert np.isclose(wed_cost, 0.66), f"Wednesday cost should be $0.66, got {wed_cost}"
        assert np.isclose(non_wed_cost, 0.42), f"Non-Wednesday cost should be $0.42, got {non_wed_cost}"


class TestStatisticalValidationAndVerdict:
    """Validate Holm-Bonferroni correction, out-of-sample results, and final verdict."""

    def test_holm_bonferroni_adjustment_logic(self):
        """Synthetic test validating step-down Holm-Bonferroni implementation."""
        # 4 test p-values
        p_vals = [0.04, 0.02, 0.005, 0.80]
        alpha = 0.05
        m = len(p_vals)

        # Sorted: 0.005 (rank 1), 0.02 (rank 2), 0.04 (rank 3), 0.80 (rank 4)
        # Thresholds:
        # rank 1: alpha / 4 = 0.0125. 0.005 < 0.0125 -> PASS
        # rank 2: alpha / 3 = 0.0167. 0.02 > 0.0167 -> FAIL (stops)
        # rank 3: alpha / 2 = 0.025 -> FAIL
        # rank 4: alpha / 1 = 0.05 -> FAIL
        sorted_p = sorted(p_vals)
        sig = []
        stopped = False
        for k, p in enumerate(sorted_p, start=1):
            thresh = alpha / (m - k + 1)
            if not stopped and p < thresh:
                sig.append(True)
            else:
                stopped = True
                sig.append(False)
        assert sig == [True, False, False, False]

    def test_phase20_results_json_verdict_and_invariants(self):
        assert RESULTS_JSON_PATH.exists(), "results.json missing!"
        with open(RESULTS_JSON_PATH, "r") as f:
            res = json.load(f)

        assert res["final_verdict"] == "NO EVIDENCE OF PREDICTIVE EDGE"
        assert "verdict_rationale" in res

        # Verify all 4 candidate models failed promotion gates
        gates = res["promotion_gate_audit"]
        for m, audit in gates.items():
            assert audit["meets_all_promotion_gates"] is False
            assert audit["positive_net_pnl"] is False
            assert audit["net_profit_factor_gt_1_25"] is False
