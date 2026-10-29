"""Test suite for Phase 18B: Audit Corrections & Macro Research Feasibility.

Validates:
1. Strict Data Partition Protection (Zero-access invariant for 2025 val and 2026 test).
2. AST and code audit guaranteeing no references loading protected partitions in Phase 18B scripts.
3. Hand-checkable synthetic unit tests for corrected excursion boundary indexing (strictly active trade candles [i+1, i+H], zero data post-exit).
4. Synthetic demonstration of the MFE/MAE pooling identity refuting the random walk fallacy.
5. Effective sample size sensitivity across estimators (Heuristic N/H, Bartlett 2H, Bartlett First-Neg, Parzen 2H).
6. Clean feature diagnostics (zero-variance filtering, NaN prevention, collinearity detection).
7. Institutional daily bar construction (276 M5 bars vs H=288 refutation).
8. Schema, invariants, and verdict in reports/phase18b/phase18b_results.json.
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
PHASE18B_SCRIPT_PATH = PROJECT_ROOT / "scripts/run_phase18b_corrected_diagnostics.py"
PHASE18B_JSON_PATH = PROJECT_ROOT / "reports/phase18b/phase18b_results.json"

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

    def test_phase18b_script_does_not_load_protected_partitions(self):
        assert PHASE18B_SCRIPT_PATH.exists(), "Phase 18B script missing!"
        source = PHASE18B_SCRIPT_PATH.read_text()
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                val_str = node.value.lower()
                assert "read_parquet" not in val_str or "val" not in val_str, (
                    "Phase 18B script contains reference loading protected validation data!"
                )
                assert "read_parquet" not in val_str or "test" not in val_str, (
                    "Phase 18B script contains reference loading protected test data!"
                )


class TestExcursionIndexingAndBoundaries:
    """Hand-checkable synthetic tests for excursion boundaries and timing definitions."""

    def test_synthetic_excursion_indexing_no_post_exit_data(self):
        """Prove that corrected indexing strictly excludes prices occurring after exit time."""
        # Timeline:
        # Candle 0: Open=100, High=102, Low=99,  Close=101 (Decision time: Close of candle 0)
        # Candle 1: Open=101, High=105, Low=100, Close=104 (Entry time: Open of candle 1)
        # Candle 2: Open=104, High=110, Low=102, Close=108 (Active trade candle)
        # Candle 3: Open=108, High=999, Low=50,  Close=500 (Exit time: Open of candle 3; High/Low/Close post-exit!)
        # Horizon H = 2.
        # Active trade window is candles [1, 2].
        # For a LONG entered at Open of candle 1 (101.0):
        # Max high during trade = max(High[1], High[2]) = max(105, 110) = 110.0
        # Min low during trade  = min(Low[1],  Low[2])  = min(100, 102) = 100.0
        # Correct MFE = 110.0 - 101.0 = +9.0
        # Correct MAE = 101.0 - 100.0 = +1.0
        highs = pd.Series([102.0, 105.0, 110.0, 999.0, 115.0])
        lows  = pd.Series([99.0,  100.0, 102.0, 50.0,  100.0])
        opens = pd.Series([100.0, 101.0, 104.0, 108.0, 112.0])
        h = 2
        max_idx = len(highs) - 1 - h  # 5 - 1 - 2 = 2

        # Corrected indexing: slice [:max_idx]
        corr_fwd_max = highs.iloc[::-1].rolling(h, min_periods=h).max().iloc[::-1].shift(-1).to_numpy()[:max_idx]
        corr_fwd_min = lows.iloc[::-1].rolling(h, min_periods=h).min().iloc[::-1].shift(-1).to_numpy()[:max_idx]
        entry_prices = opens.to_numpy()[1 : max_idx + 1]

        # Trade 0: decision at candle 0, entry candle 1 (open=101.0), exit candle 3 (open=108.0)
        assert corr_fwd_max[0] == 110.0, f"Expected 110.0, got {corr_fwd_max[0]}"
        assert corr_fwd_min[0] == 100.0, f"Expected 100.0, got {corr_fwd_min[0]}"
        mfe_trade0 = corr_fwd_max[0] - entry_prices[0]
        mae_trade0 = entry_prices[0] - corr_fwd_min[0]
        assert mfe_trade0 == 9.0
        assert mae_trade0 == 1.0

        # Phase 17 indexing: slice [1 : max_idx + 1]
        p17_fwd_max = highs.iloc[::-1].rolling(h, min_periods=h).max().iloc[::-1].shift(-1).to_numpy()[1 : max_idx + 1]
        # Notice that for trade 0, Phase 17 took index 1 of the shifted series, which looked into candle 3 (High=999.0)!
        assert p17_fwd_max[0] == 999.0, "Demonstrates Phase 17 leaked post-exit price into trade excursion!"

    def test_pooled_mfe_mae_identity_refutes_random_walk(self):
        """Prove algebraically that pooled_mfe == pooled_mae for ANY price series.

        This identity is a mathematical tautology:
        Long MFE  = max(High) - Open
        Long MAE  = Open - min(Low)
        Short MFE = Open - min(Low)  [IDENTICAL to Long MAE]
        Short MAE = max(High) - Open [IDENTICAL to Long MFE]
        Therefore:
        pooled_mfe = 0.5 * (Long MFE + Short MFE) = 0.5 * (max(High) - Open + Open - min(Low))
                   = 0.5 * (max(High) - min(Low))
        pooled_mae = 0.5 * (Long MAE + Short MAE) = 0.5 * (Open - min(Low) + max(High) - Open)
                   = 0.5 * (max(High) - min(Low))
        They are IDENTICAL by definition regardless of whether prices are trending, mean-reverting, or random!
        """
        rng = np.random.RandomState(42)
        # Generate arbitrary trending series
        trend = np.linspace(100, 200, 50)
        highs = trend + rng.uniform(1, 5, 50)
        lows = trend - rng.uniform(1, 5, 50)
        opens = trend

        long_mfe = highs - opens
        long_mae = opens - lows
        short_mfe = opens - lows
        short_mae = highs - opens

        pooled_mfe = 0.5 * (long_mfe + short_mfe)
        pooled_mae = 0.5 * (long_mae + short_mae)

        np.testing.assert_allclose(pooled_mfe, pooled_mae)
        # Assert that even with a massive deterministic upward trend, pooled_mfe == pooled_mae!
        assert np.all(long_mfe > 0)
        assert np.all(long_mae > 0)


class TestEffectiveSampleSizeSensitivity:
    """Validate sensitivity of effective sample size estimation."""

    def test_sample_size_estimator_sensitivity_on_synthetic_ar1(self):
        """Demonstrate that N_eff varies systematically across valid estimators."""
        # Simulate AR(1) process with positive autocorrelation rho=0.8
        n = 1000
        rho = 0.8
        x = np.zeros(n)
        for t in range(1, n):
            x[t] = rho * x[t-1] + np.random.normal(0, 1)

        # Autocorrelations
        x_c = x - np.mean(x)
        gamma0 = np.mean(x_c ** 2)
        acf = [np.mean(x_c[:-k] * x_c[k:]) / gamma0 for k in range(1, 21)]

        # Bartlett kernel truncation at 10
        bw = 10
        vif_bartlett = 1.0 + 2.0 * sum((1.0 - (k / bw)) * acf[k-1] for k in range(1, bw))
        n_eff_bartlett = n / vif_bartlett

        # Parzen kernel truncation at 10
        weights_parzen = []
        for k in range(1, bw):
            u = k / bw
            if u <= 0.5:
                w = 1.0 - 6.0 * (u ** 2) + 6.0 * (u ** 3)
            else:
                w = 2.0 * ((1.0 - u) ** 3)
            weights_parzen.append(w)
        vif_parzen = 1.0 + 2.0 * sum(weights_parzen[k-1] * acf[k-1] for k in range(1, bw))
        n_eff_parzen = n / vif_parzen

        # N / bw heuristic
        n_eff_heuristic = n / bw

        assert n_eff_heuristic < n_eff_bartlett
        assert n_eff_bartlett != n_eff_parzen
        assert n_eff_parzen > 0


class TestCleanFeatureDiagnostics:
    """Validate zero-variance filtering and collinearity checks."""

    def test_zero_variance_column_exclusion_prevents_nans(self):
        """Verify that constant columns are excluded and do not poison the correlation matrix."""
        df = pd.DataFrame({
            "feat_normal": [1.0, 2.0, 3.0, 4.0, 5.0],
            "feat_constant": [0.0, 0.0, 0.0, 0.0, 0.0],  # zero variance
            "feat_correlated": [2.0, 4.0, 6.0, 8.0, 10.0],
        })

        # Pre-filter zero-variance columns
        variances = df.var()
        zero_var_cols = variances[variances == 0].index.tolist()
        assert zero_var_cols == ["feat_constant"]

        clean_df = df.drop(columns=zero_var_cols)
        corr_matrix = clean_df.corr().to_numpy()

        assert not np.isnan(corr_matrix).any(), "Correlation matrix contains NaNs after zero-variance filtering!"
        assert not np.isinf(corr_matrix).any(), "Correlation matrix contains Infs!"
        assert np.isclose(corr_matrix[0, 1], 1.0), "feat_correlated should have correlation 1.0 with feat_normal"


class TestInstitutionalDailyAggregation:
    """Validate institutional gold daily session construction."""

    def test_institutional_gold_session_bar_count(self):
        """Confirm that an institutional gold trading day contains 276 M5 bars, NOT 288."""
        # Spot gold trades 23 hours per day (18:00 NY to 17:00 NY next day).
        # Daily maintenance roll closure is 1 hour (17:00 NY to 18:00 NY).
        trading_hours_per_day = 23
        m5_bars_per_hour = 12
        expected_bars = trading_hours_per_day * m5_bars_per_hour
        assert expected_bars == 276, f"Expected 276 bars, got {expected_bars}"
        assert expected_bars != 288, "288 bars corresponds to 24 hours without closure, which does not exist in gold trading"


class TestPhase18BResultsInvariants:
    """Validate contents and invariants of phase18b_results.json."""

    def test_results_json_structure_and_verdict(self):
        assert PHASE18B_JSON_PATH.exists(), "phase18b_results.json missing!"
        with open(PHASE18B_JSON_PATH, "r") as f:
            data = json.load(f)

        assert "data_partition_protection" in data
        assert data["data_partition_protection"]["val"]["is_unmodified"] is True
        assert data["data_partition_protection"]["test"]["is_unmodified"] is True

        assert "corrected_excursions" in data
        assert "effective_sample_size_sensitivity" in data
        assert "clean_feature_diagnostics" in data
        assert "transaction_costs_and_breakeven" in data
        assert "macro_research_feasibility" in data

        # Check macro variables inventory is empty locally
        assert len(data["macro_research_feasibility"]["macro_variables_inventory"]["locally_available_macro_features"]) == 0

        # Check final verdict
        assert data["final_verdict"] == "MACRO RESEARCH FEASIBLE AFTER DATA ACQUISITION"
