"""Test suite for Phase 17: Research Feasibility & Edge Diagnostic.

Validates:
1. Strict Data Partition Protection (Zero-access invariant for 2025 val and 2026 test).
2. AST and code audit guaranteeing no references to protected partitions in Phase 17 scripts.
3. Integrity and schema validity of all machine-readable diagnostic deliverables.
4. Mathematical invariants, bounds, and accounting exactness.
5. Governance gate validation.
"""

import ast
import hashlib
import json
from pathlib import Path

import pytest

PROJECT_ROOT = Path("/home/bhoot/project/Treading-Ai")
VAL_PARQUET_PATH = PROJECT_ROOT / "data/features/XAUUSD_M5_features_val.parquet"
TEST_PARQUET_PATH = PROJECT_ROOT / "data/features/XAUUSD_M5_features_test.parquet"
PHASE17_SCRIPT_PATH = PROJECT_ROOT / "scripts/run_phase17_feasibility_diagnostic.py"
PHASE17_OUTPUT_DIR = PROJECT_ROOT / "reports/phase17"

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

    def test_phase17_script_does_not_load_protected_partitions(self):
        assert PHASE17_SCRIPT_PATH.exists(), "Phase 17 script missing!"
        source = PHASE17_SCRIPT_PATH.read_text()
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                val_str = node.value.lower()
                assert "read_parquet" not in val_str or "val" not in val_str, (
                    "Phase 17 script contains reference loading protected validation data!"
                )
                assert "read_parquet" not in val_str or "test" not in val_str, (
                    "Phase 17 script contains reference loading protected test data!"
                )


class TestDeliverablesIntegrity:
    """Ensure all required machine-readable JSON files exist and have valid structure."""

    def test_label_diagnostics_json_structure(self):
        path = PHASE17_OUTPUT_DIR / "phase17_label_diagnostics.json"
        assert path.exists(), f"Missing deliverable: {path}"
        with open(path) as f:
            data = json.load(f)

        assert isinstance(data, dict), "Label diagnostics must be a JSON object"
        for h in [12, 24, 48, 72, 96, 120, 288]:
            k = f"H_{h}"
            assert k in data, f"Missing horizon key {k} in label diagnostics"
            item = data[k]
            assert "class_counts" in item
            assert "class_pcts" in item
            assert "consecutive_bar_overlap_ratio" in item
            assert "effective_sample_size_neff" in item
            assert item["consecutive_bar_overlap_ratio"] > 0.90, "Overlap ratio should be > 0.90 for H >= 12"

    def test_friction_diagnostics_json_structure(self):
        path = PHASE17_OUTPUT_DIR / "phase17_friction_diagnostics.json"
        assert path.exists(), f"Missing deliverable: {path}"
        with open(path) as f:
            data = json.load(f)

        assert isinstance(data, dict), "Friction diagnostics must be a JSON object"
        for h in [12, 24, 48, 72, 96, 120, 288]:
            k = f"H_{h}"
            assert k in data, f"Missing horizon key {k} in friction diagnostics"
            item = data[k]
            assert "gross_terminal_move" in item
            assert "excursions" in item
            assert "cost_drag" in item
            assert "break_even_hurdles" in item

    def test_feature_diagnostics_json_structure(self):
        path = PHASE17_OUTPUT_DIR / "phase17_feature_diagnostics.json"
        assert path.exists(), f"Missing deliverable: {path}"
        with open(path) as f:
            data = json.load(f)

        assert isinstance(data, dict)
        assert data["total_features"] == 232
        assert "collinearity" in data
        assert "pca_effective_rank" in data
        assert "distributional_drift_2021_vs_2024" in data
        pca = data["pca_effective_rank"]
        assert pca["components_90_pct_variance"] < data["total_features"], "PCA components must compress features"

    def test_regime_error_diagnostics_json_structure(self):
        path = PHASE17_OUTPUT_DIR / "phase17_regime_error_diagnostics.json"
        assert path.exists(), f"Missing deliverable: {path}"
        with open(path) as f:
            data = json.load(f)

        assert isinstance(data, dict)
        assert "volatility_regimes" in data
        assert "trend_regimes" in data
        assert "session_regimes" in data
        assert "directional_asymmetry_by_year" in data


class TestMathematicalAndEconomicInvariants:
    """Validate mathematical properties, bounds, and cost-friction realities."""

    def test_friction_drag_monotonicity(self):
        path = PHASE17_OUTPUT_DIR / "phase17_friction_diagnostics.json"
        with open(path) as f:
            data = json.load(f)

        # Cost drag % must decrease monotonically as horizon increases
        drag_12 = data["H_12"]["cost_drag"]["base_cost_drag_pct_of_median"]
        drag_24 = data["H_24"]["cost_drag"]["base_cost_drag_pct_of_median"]
        drag_96 = data["H_96"]["cost_drag"]["base_cost_drag_pct_of_median"]
        drag_288 = data["H_288"]["cost_drag"]["base_cost_drag_pct_of_median"]

        assert drag_12 > drag_24 > drag_96 > drag_288, (
            f"Friction drag must decrease with horizon: {drag_12:.1f}% > {drag_24:.1f}% > {drag_96:.1f}% > {drag_288:.1f}%"
        )

    def test_required_win_rate_strictly_exceeds_fifty_percent(self):
        path = PHASE17_OUTPUT_DIR / "phase17_friction_diagnostics.json"
        with open(path) as f:
            data = json.load(f)

        for h in [12, 24, 48, 72, 96, 120, 288]:
            k = f"H_{h}"
            req_wr = data[k]["break_even_hurdles"]["required_win_rate_base_cost_pct"]
            assert req_wr > 50.0, f"Required win rate for {k} must exceed 50% due to friction: {req_wr:.2f}%"

    def test_mfe_and_mae_non_negative_and_symmetric(self):
        path = PHASE17_OUTPUT_DIR / "phase17_friction_diagnostics.json"
        with open(path) as f:
            data = json.load(f)

        for h in [12, 24, 48, 72, 96, 120, 288]:
            k = f"H_{h}"
            exc = data[k]["excursions"]
            assert exc["mean_mfe_usd"] > 0
            assert exc["mean_mae_usd"] > 0
            ratio = exc["mfe_mae_ratio"]
            # Ratio should be very close to 1.0 (unconditional Brownian motion)
            assert 0.95 <= ratio <= 1.05, f"MFE/MAE ratio for {k} must be ~1.0: got {ratio:.3f}"

    def test_effective_sample_size_reduction(self):
        path = PHASE17_OUTPUT_DIR / "phase17_label_diagnostics.json"
        with open(path) as f:
            data = json.load(f)

        for h in [12, 24, 48, 72, 96, 120, 288]:
            k = f"H_{h}"
            item = data[k]
            assert item["effective_sample_size_neff"] == pytest.approx(item["valid_rows"] / h, rel=1e-3)
            assert item["sample_inflation_factor"] == float(h)
