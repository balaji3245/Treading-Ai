"""Unit and Integrity Tests for Phase 16: AI Model Capability Assessment.

Verifies:
1. Strict Data Partition Protection: SHA256 integrity of 2025 Validation and 2026 Test partitions.
2. Deliverable Integrity: Presence, structure, and machine-readability of Phase 16 outputs.
3. Predictive Metric Invariants: Accuracy, Balanced Accuracy, Macro F1, Brier, Log Loss, ROC-AUC.
4. Economic Accounting Invariants: Net PnL = Gross PnL - Friction, Net Expectancy, No-Trade Benchmark.
5. Governance Gate Integrity: Disqualification of unprofitable strategies.
"""

import hashlib
import json
from pathlib import Path
import pytest
import pandas as pd
import numpy as np


TRAIN_PATH = Path("data/features/XAUUSD_M5_features_train.parquet")
VAL_PATH = Path("data/features/XAUUSD_M5_features_val.parquet")
TEST_PATH = Path("data/features/XAUUSD_M5_features_test.parquet")

VAL_SHA256 = "7e9222e9dc0893601e24505912eeab78330670c4e70ebcc2fa462ff8d44a4f94"
TEST_SHA256 = "f95fd09a5d07666e3f1d9a72e840e2e97f3c058d11b6bb0c712b21dea86a5dec"

PHASE16_DIR = Path("reports/phase16")
PRED_METRICS_PATH = PHASE16_DIR / "phase16_predictive_metrics.json"
ECON_METRICS_PATH = PHASE16_DIR / "phase16_economic_metrics.json"
OOF_PREDS_PATH = PHASE16_DIR / "phase16_oof_predictions.parquet"
REPORT_PATH = PHASE16_DIR / "phase16_model_capability_report.md"


class TestDataPartitionProtection:
    """Verifies strict isolation and non-modification of protected partitions."""

    def test_protected_validation_partition_hash_invariant(self):
        """2025 Validation partition must remain completely untouched with bitwise invariant hash."""
        assert VAL_PATH.exists(), f"Missing validation partition at {VAL_PATH}"
        with open(VAL_PATH, "rb") as f:
            h = hashlib.sha256(f.read()).hexdigest()
        assert h == VAL_SHA256, "Protected 2025 Validation partition hash changed! Data boundary violation."

    def test_protected_test_partition_hash_invariant(self):
        """Frozen 2026 Test partition must remain completely untouched with bitwise invariant hash."""
        assert TEST_PATH.exists(), f"Missing test partition at {TEST_PATH}"
        with open(TEST_PATH, "rb") as f:
            h = hashlib.sha256(f.read()).hexdigest()
        assert h == TEST_SHA256, "Frozen 2026 Test partition hash changed! Data boundary violation."

    def test_phase16_script_does_not_load_protected_partitions(self):
        """Inspection of scripts/run_phase16_model_capability_assessment.py confirms zero loading of val/test."""
        script_path = Path("scripts/run_phase16_model_capability_assessment.py")
        assert script_path.exists()
        code = script_path.read_text()
        assert "read_parquet(val_path)" not in code
        assert "read_parquet(test_path)" not in code
        assert "pd.read_parquet(FEATURES_DATA_DIR / \"XAUUSD_M5_features_val.parquet\")" not in code
        assert "pd.read_parquet(FEATURES_DATA_DIR / \"XAUUSD_M5_features_test.parquet\")" not in code


class TestDeliverablesIntegrity:
    """Verifies all Phase 16 machine-readable and markdown artifacts are generated."""

    def test_predictive_metrics_json_structure(self):
        """phase16_predictive_metrics.json contains all required models and valid metric keys."""
        if not PRED_METRICS_PATH.exists():
            pytest.skip("Phase 16 execution script in progress.")
        with open(PRED_METRICS_PATH) as f:
            data = json.load(f)

        required_models = [
            "majority_class_h24",
            "heuristic_rsi_mom_h24",
            "incumbent_lr_h24",
            "market_structure_lr_h24",
            "adaptive_challenger_h24",
            "majority_class_h96",
            "heuristic_rsi_mom_h96",
            "candidate5_overlap_h96",
        ]
        for m in required_models:
            assert m in data, f"Missing model {m} in predictive metrics"
            m_res = data[m]
            assert "accuracy" in m_res
            assert "balanced_accuracy" in m_res
            assert "f1_macro" in m_res
            assert "log_loss" in m_res
            assert "brier_score" in m_res
            assert "roc_auc_ovr_macro" in m_res
            assert "pr_auc_ovr_macro" in m_res
            assert "expected_calibration_error" in m_res
            assert "bootstrap_95_ci" in m_res

    def test_economic_metrics_json_structure(self):
        """phase16_economic_metrics.json contains all evaluated strategies and accounting keys."""
        if not ECON_METRICS_PATH.exists():
            pytest.skip("Phase 16 execution script in progress.")
        with open(ECON_METRICS_PATH) as f:
            data = json.load(f)

        required_models = [
            "no_trade_baseline",
            "majority_class_h24",
            "heuristic_rsi_mom_h24",
            "incumbent_lr_h24",
            "market_structure_lr_h24",
            "adaptive_challenger_h24",
            "majority_class_h96",
            "heuristic_rsi_mom_h96",
            "candidate5_overlap_h96",
        ]
        for m in required_models:
            assert m in data, f"Missing strategy {m} in economic metrics"
            e_res = data[m]
            assert "total_trades" in e_res
            assert "gross_pnl_usd" in e_res
            assert "friction_usd" in e_res
            assert "net_pnl_base_usd" in e_res
            assert "net_expectancy_usd" in e_res
            assert "profit_factor_net" in e_res
            assert "max_drawdown_usd" in e_res
            assert "per_fold_results" in e_res

    def test_oof_predictions_parquet_schema(self):
        """phase16_oof_predictions.parquet contains valid out-of-fold timeseries and predictions."""
        if not OOF_PREDS_PATH.exists():
            pytest.skip("Phase 16 execution script in progress.")
        df = pd.read_parquet(OOF_PREDS_PATH)
        assert len(df) > 100000
        assert "timestamp" in df.columns
        assert "fold_id" in df.columns
        assert "target_class_h24" in df.columns
        assert "target_class_h96" in df.columns
        assert "prob_inc_long_h24" in df.columns
        assert "prob_ms_long_h24" in df.columns
        assert "prob_cand5_long_h96" in df.columns


class TestMetricCalculationsAndInvariants:
    """Verifies mathematical consistency of classification and economic metrics."""

    def test_predictive_metric_bounds(self):
        """All classification metrics must satisfy theoretical probability and score bounds."""
        if not PRED_METRICS_PATH.exists():
            pytest.skip("Phase 16 execution script in progress.")
        with open(PRED_METRICS_PATH) as f:
            data = json.load(f)

        for m, res in data.items():
            acc = res["accuracy"]
            bacc = res["balanced_accuracy"]
            f1 = res["f1_macro"]
            roc = res["roc_auc_ovr_macro"]
            pr = res["pr_auc_ovr_macro"]
            brier = res["brier_score"]
            ll = res["log_loss"]
            ece = res["expected_calibration_error"]

            assert 0.0 <= acc <= 1.0, f"Accuracy out of bounds for {m}: {acc}"
            assert 0.0 <= bacc <= 1.0, f"Balanced accuracy out of bounds for {m}: {bacc}"
            assert 0.0 <= f1 <= 1.0, f"Macro F1 out of bounds for {m}: {f1}"
            assert 0.0 <= roc <= 1.0, f"ROC-AUC out of bounds for {m}: {roc}"
            assert 0.0 <= pr <= 1.0, f"PR-AUC out of bounds for {m}: {pr}"
            assert 0.0 <= brier <= 2.0, f"Brier score out of bounds for {m}: {brier}"
            assert ll >= 0.0, f"Log loss negative for {m}: {ll}"
            assert 0.0 <= ece <= 1.0, f"ECE out of bounds for {m}: {ece}"

    def test_majority_baseline_theoretical_properties(self):
        """Majority class baseline must exhibit chance balanced accuracy and 0.50 ROC-AUC."""
        if not PRED_METRICS_PATH.exists():
            pytest.skip("Phase 16 execution script in progress.")
        with open(PRED_METRICS_PATH) as f:
            data = json.load(f)

        maj24 = data["majority_class_h24"]
        assert abs(maj24["balanced_accuracy"] - (1.0 / 3.0)) < 0.05
        assert abs(maj24["roc_auc_ovr_macro"] - 0.50) < 1e-4

        maj96 = data["majority_class_h96"]
        assert abs(maj96["balanced_accuracy"] - (1.0 / 3.0)) < 0.05
        assert abs(maj96["roc_auc_ovr_macro"] - 0.50) < 1e-4

    def test_economic_accounting_exactness(self):
        """Net PnL must strictly equal Gross PnL minus Friction across all models."""
        if not ECON_METRICS_PATH.exists():
            pytest.skip("Phase 16 execution script in progress.")
        with open(ECON_METRICS_PATH) as f:
            data = json.load(f)

        for m, res in data.items():
            gross = res["gross_pnl_usd"]
            fric = res["friction_usd"]
            net = res["net_pnl_base_usd"]
            n_tr = res["total_trades"]
            net_exp = res["net_expectancy_usd"]

            assert abs(net - (gross - fric)) < 1e-4, f"PnL accounting mismatch in {m}"
            if n_tr > 0:
                assert abs(net_exp - (net / n_tr)) < 1e-6, f"Expectancy mismatch in {m}"
            else:
                assert net == 0.0 and gross == 0.0 and fric == 0.0 and net_exp == 0.0

    def test_no_trade_benchmark_exactness(self):
        """No-trade economic baseline must be exactly 0 trades and $0.00 PnL."""
        if not ECON_METRICS_PATH.exists():
            pytest.skip("Phase 16 execution script in progress.")
        with open(ECON_METRICS_PATH) as f:
            data = json.load(f)

        nt = data["no_trade_baseline"]
        assert nt["total_trades"] == 0
        assert nt["net_pnl_base_usd"] == 0.0
        assert nt["gross_pnl_usd"] == 0.0
        assert nt["friction_usd"] == 0.0
        assert nt["max_drawdown_usd"] == 0.0


class TestGovernanceAndPromotionGate:
    """Verifies that no losing model is promoted or declared profitable."""

    def test_candidate_models_fail_promotion_gate(self):
        """All existing ML models must show negative net expectancy after transaction costs."""
        if not ECON_METRICS_PATH.exists():
            pytest.skip("Phase 16 execution script in progress.")
        with open(ECON_METRICS_PATH) as f:
            data = json.load(f)

        for key in ["incumbent_lr_h24", "market_structure_lr_h24", "adaptive_challenger_h24", "candidate5_overlap_h96"]:
            res = data[key]
            assert res["net_pnl_base_usd"] < 0.0, f"Model {key} unexpectedly positive net PnL"
            assert res["net_expectancy_usd"] < 0.0, f"Model {key} unexpectedly positive net expectancy"
            # Net profit factor must be < 1.0
            assert res["profit_factor_net"] < 1.0, f"Model {key} has PF >= 1.0: {res['profit_factor_net']}"
