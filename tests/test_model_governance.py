"""Unit tests for Model Governance, Registry, and Rollback."""

from pathlib import Path
import pytest
from treading_ai.governance.challenger_gate import ChallengerGate, PromotionCriteria
from treading_ai.governance.model_registry import ModelRegistry


@pytest.fixture
def temp_registry(tmp_path: Path):
    reg_dir = tmp_path / "model_registry"
    return ModelRegistry(registry_dir=reg_dir)


class TestModelRegistry:
    """Verifies model registration, promotion, rejection, and rollback."""

    def test_register_and_retrieve_model(self, temp_registry):
        """Model object and metadata are persisted and retrieved correctly."""
        meta = temp_registry.register_model(
            model_version="v1.0",
            model_obj={"weights": [0.1, 0.2, 0.3]},
            model_class="LogisticRegression",
            feature_names=["f1", "f2", "f3"],
            hyperparameters={"C": 1.0},
            status="INCUMBENT",
        )
        assert meta.model_version == "v1.0"
        assert meta.status == "INCUMBENT"

        obj, fetched_meta = temp_registry.get_model("v1.0")
        assert obj["weights"] == [0.1, 0.2, 0.3]
        assert fetched_meta.model_class == "LogisticRegression"

        incumbent = temp_registry.get_incumbent()
        assert incumbent is not None
        assert incumbent.model_version == "v1.0"

    def test_promote_challenger_archives_previous_incumbent(self, temp_registry):
        """Promoting a challenger archives the existing incumbent."""
        # Setup initial incumbent
        temp_registry.register_model(
            model_version="v1.0",
            model_obj={"weights": [1]},
            model_class="Baseline",
            feature_names=["f1"],
            hyperparameters={},
            status="INCUMBENT",
        )

        # Register challenger
        temp_registry.register_model(
            model_version="v2.0",
            model_obj={"weights": [2]},
            model_class="Challenger",
            feature_names=["f1", "f2"],
            hyperparameters={},
            status="CHALLENGER",
        )

        # Promote challenger
        temp_registry.promote_challenger("v2.0", justification="Outperformed on walk-forward folds.")

        new_incumbent = temp_registry.get_incumbent()
        assert new_incumbent.model_version == "v2.0"
        assert new_incumbent.status == "INCUMBENT"

        _, old_meta = temp_registry.get_model("v1.0")
        assert old_meta.status == "ARCHIVED"

    def test_rollback_restores_earlier_incumbent(self, temp_registry):
        """Rollback restores an archived model to incumbent status."""
        temp_registry.register_model("v1.0", [1], "ClassA", ["f1"], {}, status="INCUMBENT")
        temp_registry.register_model("v2.0", [2], "ClassB", ["f1"], {}, status="CHALLENGER")
        temp_registry.promote_challenger("v2.0", "Promoted")

        # Rollback to v1.0
        rolled_back = temp_registry.rollback("v1.0", rollback_reason="Performance drift detected in v2.0.")
        assert rolled_back.model_version == "v1.0"
        assert rolled_back.status == "INCUMBENT"

        incumbent = temp_registry.get_incumbent()
        assert incumbent.model_version == "v1.0"


class TestChallengerGate:
    """Verifies pre-registered promotion criteria enforcement."""

    def test_rejects_negative_expectancy(self):
        """Challenger with negative net PnL is rejected."""
        gate = ChallengerGate(PromotionCriteria(min_net_expectancy=0.0, min_profit_factor=1.0))
        challenger_metrics = {
            "net_pnl": -350.0,
            "profit_factor": 0.82,
            "trade_count": 50,
            "max_drawdown": 800.0,
            "fold_pnls": [-150.0, -100.0, -100.0],
        }
        decision = gate.evaluate(challenger_metrics)
        assert decision.is_approved is False
        assert decision.recommendation == "REJECT"
        assert any("negative after transaction costs" in r or "failed positive expectancy" in r for r in decision.rejection_reasons)

    def test_approves_qualifying_challenger(self):
        """Challenger meeting all hurdles is approved."""
        gate = ChallengerGate(PromotionCriteria(min_net_expectancy=0.0, min_profit_factor=1.0, min_trades_count=30))
        incumbent_metrics = {
            "net_pnl": 120.0,
            "profit_factor": 1.05,
            "trade_count": 60,
            "max_drawdown": 500.0,
        }
        challenger_metrics = {
            "net_pnl": 450.0,
            "profit_factor": 1.25,
            "trade_count": 55,
            "max_drawdown": 480.0,
            "fold_pnls": [150.0, 180.0, 120.0],
        }
        decision = gate.evaluate(challenger_metrics, incumbent_metrics=incumbent_metrics)
        assert decision.is_approved is True
        assert decision.recommendation == "PROMOTE"
        assert len(decision.rejection_reasons) == 0
