"""Adversarial stress and safety tests for Phase 9B & Phase 10.

Verifies:
1. Truncation invariance and strict causality across noisy market states.
2. Prevention of duplicate decision ID collision or corruption in SQLite journal.
3. Strict isolation of immature decisions from matured performance aggregations.
4. Blocking of unsafe or overfitted model promotions.
5. Multi-round rollback and re-promotion consistency.
"""

from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from treading_ai.audit.error_classifier import ErrorCategory
from treading_ai.audit.trade_journal import DecisionJournal
from treading_ai.features.market_structure import MarketStructureEngine
from treading_ai.governance.adaptive_learner import AdaptiveLearner
from treading_ai.governance.challenger_gate import ChallengerGate, PromotionCriteria
from treading_ai.governance.model_registry import ModelRegistry


class TestAdversarialMarketStructureCausality:
    """Stress tests verifying causality under noisy stochastic walk."""

    def test_random_walk_truncation_invariance(self):
        """Random walk price path must produce bitwise identical features when truncated."""
        np.random.seed(999)
        n_bars = 150
        base_time = pd.Timestamp("2024-01-08 00:00:00+00:00")
        timestamps = [base_time + pd.Timedelta(minutes=5 * i) for i in range(n_bars)]

        # Noisy random walk with sudden spikes
        returns = np.random.normal(0, 0.001, n_bars)
        closes = 2050.0 * np.exp(np.cumsum(returns))
        highs = closes + np.abs(np.random.normal(0.5, 0.2, n_bars))
        lows = closes - np.abs(np.random.normal(0.5, 0.2, n_bars))
        opens = np.roll(closes, 1)
        opens[0] = closes[0]

        df = pd.DataFrame(
            {"open": opens, "high": highs, "low": lows, "close": closes, "volume": 100},
            index=pd.DatetimeIndex(timestamps),
        )

        engine = MarketStructureEngine(swing_left_bars=5, swing_right_bars=5)
        full_df = engine.compute_features(df)

        # Truncate at multiple intermediate points
        for test_idx in [40, 75, 110]:
            trunc_df = engine.compute_features(df.iloc[: test_idx + 1])
            for col in full_df.columns:
                val_full = full_df[col].iloc[test_idx]
                val_trunc = trunc_df[col].iloc[test_idx]
                assert val_full == pytest.approx(val_trunc, rel=1e-5, abs=1e-5), (
                    f"Causal leak on {col} at bar {test_idx}!"
                )


class TestAdversarialJournalPersistence:
    """Stress tests on decision recording and database integrity."""

    def test_duplicate_decision_id_handling(self, tmp_path: Path):
        """Overwriting an existing decision ID updates the entry without duplicate key errors."""
        journal = DecisionJournal(db_path=tmp_path / "dup_test.db")

        journal.record_decision(
            decision_id="dup_01",
            timestamp="2024-01-08T10:00:00Z",
            data_version="v1",
            feature_version="v1",
            model_version="m1",
            strategy_id="s1",
            decision="BUY",
            predicted_direction=1,
            confidence=0.60,
            expected_horizon_bars=24,
            entry_reference_price=2030.0,
            market_regime="NORMAL",
            session="LONDON",
            structure_state="BULLISH",
            reasoning_summary="Original",
        )

        # Overwrite with same ID
        journal.record_decision(
            decision_id="dup_01",
            timestamp="2024-01-08T10:00:00Z",
            data_version="v1",
            feature_version="v1",
            model_version="m1",
            strategy_id="s1",
            decision="BUY",
            predicted_direction=1,
            confidence=0.75,
            expected_horizon_bars=24,
            entry_reference_price=2030.0,
            market_regime="NORMAL",
            session="LONDON",
            structure_state="BULLISH",
            reasoning_summary="Updated with higher confidence",
        )

        entry = journal.get_decision("dup_01")
        assert entry.confidence == 0.75
        assert entry.reasoning_summary == "Updated with higher confidence"

        # Check total rows
        all_df = journal.query()
        assert len(all_df) == 1

    def test_immature_trades_strictly_excluded_from_performance_summary(self, tmp_path: Path):
        """Decisions without observed outcomes must not contaminate performance calculations."""
        journal = DecisionJournal(db_path=tmp_path / "immature_test.db")

        # 1 matured trade (Net PnL = $3.00)
        journal.record_decision(
            decision_id="mat_01",
            timestamp="2024-01-08T10:00:00Z",
            data_version="v1",
            feature_version="v1",
            model_version="m1",
            strategy_id="s1",
            decision="BUY",
            predicted_direction=1,
            confidence=0.60,
            expected_horizon_bars=24,
            entry_reference_price=2030.0,
            market_regime="NORMAL",
            session="LONDON",
            structure_state="BULLISH",
            reasoning_summary="Matured win",
        )
        journal.record_outcome(
            decision_id="mat_01",
            outcome_timestamp="2024-01-08T12:00:00Z",
            exit_price=2033.5,
            exit_reason="TARGET",
            bars_held=24,
            gross_pnl=3.50,
            estimated_friction=0.50,
            net_pnl=3.00,
            mfe=4.00,
            mae=0.50,
            entry_atr=1.50,
        )

        # 5 immature pending decisions
        for i in range(5):
            journal.record_decision(
                decision_id=f"pending_{i}",
                timestamp=f"2024-01-08T{13+i:02d}:00:00Z",
                data_version="v1",
                feature_version="v1",
                model_version="m1",
                strategy_id="s1",
                decision="BUY",
                predicted_direction=1,
                confidence=0.65,
                expected_horizon_bars=24,
                entry_reference_price=2035.0,
                market_regime="NORMAL",
                session="LONDON",
                structure_state="BULLISH",
                reasoning_summary="Pending immature",
            )

        summary = journal.summarize_performance()
        assert summary["total_decisions"] == 1  # outcome_observed_only = True
        assert summary["matured_trades"] == 1
        assert summary["total_net_pnl"] == 3.00
        assert summary["win_rate"] == 1.0


class TestAdversarialPromotionSafety:
    """Stress tests verifying promotion hurdles cannot be bypassed."""

    def test_unsafe_promotion_blocking_on_spread_stress(self):
        """Challenger with good nominal PnL that collapses under spread stress is REJECTED."""
        gate = ChallengerGate(PromotionCriteria(
            min_net_expectancy=0.0,
            min_profit_factor=1.0,
            min_trades_count=20,
        ))
        incumbent_metrics = {
            "net_pnl": 100.0,
            "profit_factor": 1.08,
            "trade_count": 50,
            "max_drawdown": 400.0,
            "stress_net_pnl": -50.0,
        }
        # Challenger looks great nominally ($500), but under spread stress collapses to -$300
        challenger_metrics = {
            "net_pnl": 500.0,
            "profit_factor": 1.30,
            "trade_count": 45,
            "max_drawdown": 420.0,
            "fold_pnls": [150.0, 200.0, 150.0],
        }
        stress_metrics = {
            "net_pnl": -350.0,  # Deterioration > $100 compared to incumbent stress
        }
        decision = gate.evaluate(
            challenger_metrics=challenger_metrics,
            incumbent_metrics=incumbent_metrics,
            stress_metrics=stress_metrics,
        )
        assert decision.is_approved is False
        assert decision.recommendation == "REJECT"
        assert any("spread stress" in r for r in decision.rejection_reasons)

    def test_multi_round_rollback_and_promotion_stability(self, tmp_path: Path):
        """Repeated sequential promotions and rollbacks maintain index consistency."""
        registry = ModelRegistry(registry_dir=tmp_path / "multi_round_reg")

        # Round 1: v1.0 is incumbent
        registry.register_model("v1.0", [1], "ClassA", ["f1"], {}, status="INCUMBENT")
        assert registry.get_incumbent().model_version == "v1.0"

        # Round 2: v2.0 challenger promoted
        registry.register_model("v2.0", [2], "ClassB", ["f1"], {}, status="CHALLENGER")
        registry.promote_challenger("v2.0", "Passed Gate 1")
        assert registry.get_incumbent().model_version == "v2.0"

        # Round 3: v3.0 challenger promoted
        registry.register_model("v3.0", [3], "ClassC", ["f1"], {}, status="CHALLENGER")
        registry.promote_challenger("v3.0", "Passed Gate 2")
        assert registry.get_incumbent().model_version == "v3.0"

        # Round 4: Emergency Rollback to v1.0
        registry.rollback("v1.0", "v3.0 regressed in production walk-forward")
        assert registry.get_incumbent().model_version == "v1.0"

        # Round 5: Re-promotion to v2.0
        registry.promote_challenger("v2.0", "Re-verified v2.0 stability")
        assert registry.get_incumbent().model_version == "v2.0"

        # Verify all models remain queryable
        models = registry.list_models()
        assert len(models) == 3
