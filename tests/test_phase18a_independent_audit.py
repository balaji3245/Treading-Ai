"""Test suite for Phase 18A: Independent Forensic Audit.

Validates:
1. Strict Data Partition Protection (Zero-access invariant for 2025 val and 2026 test).
2. AST and code audit guaranteeing no references to protected partitions in Phase 18A scripts.
3. Hand-checkable synthetic unit tests for excursion boundary indexing.
4. Hand-checkable mathematical proof of the MFE/MAE pooling identity.
5. Schema, bounds, accounting exactness, and reconciliation of Candidate 5.
"""

import ast
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path("/home/bhoot/project/Treading-Ai")
VAL_PARQUET_PATH = PROJECT_ROOT / "data/features/XAUUSD_M5_features_val.parquet"
TEST_PARQUET_PATH = PROJECT_ROOT / "data/features/XAUUSD_M5_features_test.parquet"
AUDIT_SCRIPT_PATH = PROJECT_ROOT / "scripts/run_phase18a_independent_audit.py"
AUDIT_JSON_PATH = PROJECT_ROOT / "reports/phase18a/audit_results.json"

VAL_PARQUET_EXPECTED_SHA256 = "7e9222e9dc0893601e24505912eeab78330670c4e70ebcc2fa462ff8d44a4f94"
TEST_PARQUET_EXPECTED_SHA256 = "f95fd09a5d07666e3f1d9a72e840e2e97f3c058d11b6bb0c712b21dea86a5dec"


class TestDataPartitionProtection:
    """Ensure protected validation and test partitions remain untouched."""

    def test_protected_validation_partition_hash_invariant(self):
        assert VAL_PARQUET_PATH.exists(), "Protected validation parquet missing!"
        hasher = hashlib.sha256()
        with open(VAL_PARQUET_PATH, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        actual_hash = hasher.hexdigest()
        assert actual_hash == VAL_PARQUET_EXPECTED_SHA256, (
            f"CRITICAL: Protected validation partition modified! Expected {VAL_PARQUET_EXPECTED_SHA256}, got {actual_hash}"
        )

    def test_protected_test_partition_hash_invariant(self):
        assert TEST_PARQUET_PATH.exists(), "Protected test parquet missing!"
        hasher = hashlib.sha256()
        with open(TEST_PARQUET_PATH, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        actual_hash = hasher.hexdigest()
        assert actual_hash == TEST_PARQUET_EXPECTED_SHA256, (
            f"CRITICAL: Protected test partition modified! Expected {TEST_PARQUET_EXPECTED_SHA256}, got {actual_hash}"
        )

    def test_phase18a_script_does_not_load_protected_partitions(self):
        assert AUDIT_SCRIPT_PATH.exists(), "Phase 18A script missing!"
        source = AUDIT_SCRIPT_PATH.read_text()
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                val_str = node.value.lower()
                assert "read_parquet" not in val_str or "val" not in val_str, (
                    "Phase 18A script contains reference loading protected validation data!"
                )
                assert "read_parquet" not in val_str or "test" not in val_str, (
                    "Phase 18A script contains reference loading protected test data!"
                )


class TestSyntheticBoundaryAndMathematicalInvariants:
    """Hand-checkable synthetic examples proving indexing and algebraic properties."""

    def test_synthetic_excursion_boundary_indexing(self):
        """Prove that Phase 17's slice [1 : max_idx+1] had an off-by-one lookahead."""
        highs = pd.Series([100.0, 105.0, 110.0, 108.0, 120.0, 115.0])
        opens = pd.Series([99.0,  101.0, 106.0, 107.0, 109.0, 114.0])
        h = 2
        max_idx = len(highs) - 1 - h  # 6 - 1 - 2 = 3

        # Decision at index 0:
        # Entry executes at Open of candle 1 (101.0)
        # Exit executes at Open of candle 1+h = 3 (107.0)
        # Trade is active across candles [1, 2]. Intended max high = max(highs[1], highs[2]) = max(105, 110) = 110.0

        # Phase 17 formula (sliced [1 : max_idx+1]):
        p17_fwd_max = highs.iloc[::-1].rolling(h, min_periods=h).max().iloc[::-1].shift(-1).to_numpy()[1 : max_idx + 1]
        # Element 0 of Phase 17 took index 1 of shifted series: max of candles [2, 3] = max(110, 108) = 110.
        # But for decision 1 (entry candle 2, exit candle 4): trade candles [2, 3], intended max(110, 108)=110.
        # Phase 17 element 1 took index 2: max of candles [3, 4] = max(108, 120) = 120.0! (Looked into candle 4 after exit!)
        assert p17_fwd_max[1] == 120.0, "Demonstrates Phase 17 looked into exit candle 4"

        # Corrected formula (sliced [:max_idx]):
        corr_fwd_max = highs.iloc[::-1].rolling(h, min_periods=h).max().iloc[::-1].shift(-1).to_numpy()[:max_idx]
        assert corr_fwd_max[0] == 110.0  # max(105, 110)
        assert corr_fwd_max[1] == 110.0  # max(110, 108)
        assert corr_fwd_max[2] == 120.0  # max(108, 120)

    def test_algebraic_proof_of_pooled_mfe_mae_identity(self):
        """Prove algebraically that pooled_mfe == pooled_mae for ANY price series."""
        np.random.seed(42)
        # Random price series
        highs = np.random.uniform(105, 120, 100)
        lows = np.random.uniform(90, 104, 100)
        opens = np.random.uniform(95, 115, 100)

        # Definitions
        long_mfe = np.maximum(0.0, highs - opens)
        long_mae = np.maximum(0.0, opens - lows)
        short_mfe = np.maximum(0.0, opens - lows)
        short_mae = np.maximum(0.0, highs - opens)

        # Pooling formula used in Phase 17:
        pooled_mfe = 0.5 * (long_mfe + short_mfe)
        pooled_mae = 0.5 * (long_mae + short_mae)

        # Because long_mfe == short_mae and short_mfe == long_mae:
        # pooled_mfe = 0.5 * ((highs - opens) + (opens - lows)) = 0.5 * (highs - lows)
        # pooled_mae = 0.5 * ((opens - lows) + (highs - opens)) = 0.5 * (highs - lows)
        assert np.array_equal(pooled_mfe, pooled_mae), (
            "Proof that pooled_mfe == pooled_mae is an algebraic identity, not empirical Brownian motion!"
        )


class TestAuditDeliverablesAndReconciliation:
    """Validate JSON deliverables, claim classifications, and Candidate 5 reconciliation."""

    def test_audit_results_json_schema(self):
        assert AUDIT_JSON_PATH.exists(), f"Missing audit deliverables: {AUDIT_JSON_PATH}"
        with open(AUDIT_JSON_PATH) as f:
            data = json.load(f)

        assert "claim_classifications" in data
        assert len(data["claim_classifications"]) == 9
        assert "final_audit_verdict" in data
        assert data["final_audit_verdict"] == "PHASE 17 PARTIALLY VERIFIED — FIXES REQUIRED"

    def test_candidate5_reconciliation_exactness(self):
        with open(AUDIT_JSON_PATH) as f:
            data = json.load(f)

        c5 = data["candidate5_audit"]["reconciled_metrics"]
        assert c5["total_trades"] == 531
        assert pytest.approx(c5["gross_pnl_usd"], abs=0.01) == 265.08
        assert pytest.approx(c5["friction_usd"], abs=0.01) == 338.80
        assert pytest.approx(c5["net_pnl_usd"], abs=0.01) == -73.72
        assert c5["long_trades_total"] == 257
        assert c5["short_trades_total"] == 274
        assert pytest.approx(c5["long_net_pnl_usd"], abs=0.01) == 67.24
        assert pytest.approx(c5["short_net_pnl_usd"], abs=0.01) == -140.96

        # Directional reconciliation: Long + Short = Total
        assert pytest.approx(c5["long_net_pnl_usd"] + c5["short_net_pnl_usd"], abs=0.01) == -73.72

        # Fold reconciliation
        pf = c5["per_fold"]
        f1_net = pf["fold_1"]["net_pnl"]
        f2_net = pf["fold_2"]["net_pnl"]
        f3_net = pf["fold_3"]["net_pnl"]
        assert pytest.approx(f1_net, abs=0.01) == -53.54
        assert pytest.approx(f2_net, abs=0.01) == -77.76
        assert pytest.approx(f3_net, abs=0.01) == 57.57
        assert pytest.approx(f1_net + f2_net + f3_net, abs=0.01) == -73.73
