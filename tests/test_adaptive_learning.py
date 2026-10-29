"""Unit tests for Adaptive Learning Orchestrator."""

from pathlib import Path
import pytest

from treading_ai.audit.error_classifier import ErrorCategory
from treading_ai.audit.trade_journal import DecisionJournal
from treading_ai.governance.adaptive_learner import AdaptiveLearner
from treading_ai.governance.challenger_gate import ChallengerGate, PromotionCriteria
from treading_ai.governance.model_registry import ModelRegistry


@pytest.fixture
def learner_setup(tmp_path: Path):
    db_file = tmp_path / "adaptive_test.db"
    reg_dir = tmp_path / "models_reg"

    journal = DecisionJournal(db_path=db_file)
    registry = ModelRegistry(registry_dir=reg_dir)
    gate = ChallengerGate(PromotionCriteria(min_net_expectancy=0.0, min_profit_factor=1.0, min_trades_count=20))

    learner = AdaptiveLearner(journal=journal, registry=registry, gate=gate)
    return journal, registry, learner


class TestAdaptiveLearningLoop:
    """Verifies batch error analysis, hypothesis formulation, and challenger evaluation."""

    def test_batch_error_analysis_and_hypothesis_generation(self, learner_setup):
        """Populate journal with trades concentrated in LOW regime; verify analysis & hypothesis."""
        journal, registry, learner = learner_setup

        # Register initial incumbent
        registry.register_model(
            model_version="incumbent_v1",
            model_obj={},
            model_class="Baseline",
            feature_names=["f1"],
            hyperparameters={},
            status="INCUMBENT",
        )

        # Simulate 10 trades: 8 losses in LOW regime due to REGIME_MISMATCH
        for i in range(10):
            dec_id = f"trade_{i}"
            regime = "LOW" if i < 8 else "HIGH"
            journal.record_decision(
                decision_id=dec_id,
                timestamp=f"2024-01-08T{10+i:02d}:00:00Z",
                data_version="v2.1",
                feature_version="v2.1",
                model_version="incumbent_v1",
                strategy_id="strat_test",
                decision="BUY",
                predicted_direction=1,
                confidence=0.60,
                expected_horizon_bars=24,
                entry_reference_price=2030.0,
                market_regime=regime,
                session="LONDON",
                structure_state="NEUTRAL",
                reasoning_summary="Test trade",
            )
            # Record outcome: loss in LOW regime, win in HIGH regime
            net_pnl = -1.50 if regime == "LOW" else 2.00
            gross_pnl = -0.80 if regime == "LOW" else 2.70
            journal.record_outcome(
                decision_id=dec_id,
                outcome_timestamp=f"2024-01-08T{12+i:02d}:00:00Z",
                exit_price=2029.0 if regime == "LOW" else 2032.5,
                exit_reason="TIME" if regime == "LOW" else "TARGET",
                bars_held=24,
                gross_pnl=gross_pnl,
                estimated_friction=0.70,
                net_pnl=net_pnl,
                mfe=0.30 if regime == "LOW" else 3.00,
                mae=1.80 if regime == "LOW" else 0.40,
                entry_atr=1.00,
            )

        # Run error analysis
        analysis = learner.analyze_batch_errors(batch_size=10)
        assert analysis.matured_trades == 10
        assert analysis.loss_count == 8
        assert analysis.win_count == 2
        assert analysis.regime_loss_distribution.get("LOW", 0) == 8

        # Formulate hypothesis
        hypothesis = learner.formulate_corrective_hypothesis(analysis)
        assert hypothesis.rule_type == "REGIME_FILTER"
        assert "LOW volatility" in hypothesis.description

    def test_learning_iteration_rejection_when_criteria_fail(self, learner_setup):
        """When challenger still fails post-cost hurdles, gate rejects and retains incumbent."""
        journal, registry, learner = learner_setup

        registry.register_model(
            model_version="incumbent_v1",
            model_obj={},
            model_class="Baseline",
            feature_names=["f1"],
            hyperparameters={},
            status="INCUMBENT",
        )

        # Evaluator that returns a failing challenger (negative PnL)
        def failing_eval(hypo):
            chal_metrics = {
                "net_pnl": -250.0,  # Still negative
                "profit_factor": 0.85,
                "trade_count": 35,
                "max_drawdown": 800.0,
                "fold_pnls": [-100.0, -80.0, -70.0],
            }
            stress_metrics = {"net_pnl": -450.0}
            return chal_metrics, stress_metrics

        step_res = learner.execute_learning_iteration(
            batch_size=10,
            challenger_eval_func=failing_eval,
        )

        assert step_res.action_taken == "RETAINED_INCUMBENT"
        assert step_res.gate_decision.is_approved is False
        assert registry.get_incumbent().model_version == "incumbent_v1"

    def test_learning_iteration_promotion_when_criteria_pass(self, learner_setup):
        """When challenger passes all hurdles, it is promoted to incumbent."""
        journal, registry, learner = learner_setup

        registry.register_model(
            model_version="incumbent_v1",
            model_obj={},
            model_class="Baseline",
            feature_names=["f1"],
            hyperparameters={},
            status="INCUMBENT",
            performance_metrics={"net_pnl": 50.0, "profit_factor": 1.02, "max_drawdown": 600.0},
        )

        # Evaluator that returns a winning challenger
        def winning_eval(hypo):
            chal_metrics = {
                "net_pnl": 520.0,
                "profit_factor": 1.35,
                "trade_count": 45,
                "max_drawdown": 450.0,
                "fold_pnls": [180.0, 190.0, 150.0],
            }
            stress_metrics = {"net_pnl": 310.0}
            return chal_metrics, stress_metrics

        step_res = learner.execute_learning_iteration(
            batch_size=10,
            challenger_eval_func=winning_eval,
        )

        assert step_res.action_taken == "PROMOTED_CHALLENGER"
        assert step_res.gate_decision.is_approved is True
        assert registry.get_incumbent().model_version == step_res.challenger_version
