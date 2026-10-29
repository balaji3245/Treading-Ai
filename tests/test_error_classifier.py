"""Unit tests for Evidence-based Error Classification Taxonomy."""

import pytest
from treading_ai.audit.error_classifier import ErrorCategory, TradeErrorClassifier


class TestTradeErrorClassifier:
    """Verifies each scenario in the 9-category error taxonomy."""

    @pytest.fixture
    def classifier(self):
        return TradeErrorClassifier()

    def test_successful_trade_not_classified_as_failure(self, classifier):
        """A winning trade (net PnL > 0) has is_failure=False and zero error categories."""
        res = classifier.classify_outcome(
            decision_id="test_01",
            predicted_direction=1,
            gross_pnl=3.50,
            net_pnl=2.80,
            total_friction=0.70,
            mfe=4.00,
            mae=0.80,
            entry_atr=1.50,
        )
        assert res.is_failure is False
        assert len(res.categories) == 0
        assert res.primary_reason == "SUCCESSFUL_EXECUTION"

    def test_transaction_cost_drag_classification(self, classifier):
        """Gross PnL > 0, but friction produces net loss -> TRANSACTION_COST_DRAG."""
        res = classifier.classify_outcome(
            decision_id="test_02",
            predicted_direction=1,
            gross_pnl=0.40,
            net_pnl=-0.30,
            total_friction=0.70,
            mfe=0.80,
            mae=0.50,
            entry_atr=1.50,
        )
        assert res.is_failure is True
        assert ErrorCategory.TRANSACTION_COST_DRAG.value in res.categories

    def test_directional_thesis_error(self, classifier):
        """Price moves adverse immediately (MAE large, MFE <= friction) -> DIRECTIONAL_THESIS_ERROR."""
        res = classifier.classify_outcome(
            decision_id="test_03",
            predicted_direction=1,
            gross_pnl=-3.00,
            net_pnl=-3.70,
            total_friction=0.70,
            mfe=0.20,
            mae=3.20,
            entry_atr=1.50,
        )
        assert res.is_failure is True
        assert ErrorCategory.DIRECTIONAL_THESIS_ERROR.value in res.categories

    def test_entry_timing_error(self, classifier):
        """Stopped out early, but price eventually reached target -> ENTRY_TIMING_ERROR."""
        res = classifier.classify_outcome(
            decision_id="test_04",
            predicted_direction=1,
            gross_pnl=-1.50,
            net_pnl=-2.20,
            total_friction=0.70,
            mfe=3.50,  # reached strong favorable move
            mae=1.60,
            entry_atr=1.50,
            exit_reason="STOP",
            target_distance=3.0,
            stop_distance=1.5,
        )
        assert res.is_failure is True
        assert ErrorCategory.ENTRY_TIMING_ERROR.value in res.categories

    def test_exit_risk_error(self, classifier):
        """Price went into strong profit (MFE >= 1.2 ATR), but reversed into loss at time limit."""
        res = classifier.classify_outcome(
            decision_id="test_05",
            predicted_direction=1,
            gross_pnl=-0.50,
            net_pnl=-1.20,
            total_friction=0.70,
            mfe=2.50,  # strong profit of 1.66 ATR
            mae=1.00,
            entry_atr=1.50,
            exit_reason="TIME",
        )
        assert res.is_failure is True
        assert ErrorCategory.EXIT_RISK_ERROR.value in res.categories

    def test_regime_mismatch(self, classifier):
        """Trade taken during LOW volatility regime."""
        res = classifier.classify_outcome(
            decision_id="test_06",
            predicted_direction=1,
            gross_pnl=-0.80,
            net_pnl=-1.50,
            total_friction=0.70,
            mfe=0.40,
            mae=1.00,
            entry_atr=1.00,
            market_regime="LOW",
        )
        assert res.is_failure is True
        assert ErrorCategory.REGIME_MISMATCH.value in res.categories

    def test_model_overconfidence(self, classifier):
        """Confidence >= 0.70 with severe adverse excursion (MAE > 2.0 ATR)."""
        res = classifier.classify_outcome(
            decision_id="test_07",
            predicted_direction=1,
            gross_pnl=-3.50,
            net_pnl=-4.20,
            total_friction=0.70,
            mfe=0.10,
            mae=3.80,
            entry_atr=1.50,  # MAE is 3.8 / 1.5 = 2.53 ATR
            confidence=0.85,
        )
        assert res.is_failure is True
        assert ErrorCategory.MODEL_OVERCONFIDENCE.value in res.categories

    def test_volatility_event_shock(self, classifier):
        """Single-candle range exceeds 3.0x ATR."""
        res = classifier.classify_outcome(
            decision_id="test_08",
            predicted_direction=-1,
            gross_pnl=-2.00,
            net_pnl=-2.70,
            total_friction=0.70,
            mfe=0.50,
            mae=2.50,
            entry_atr=1.00,
            max_candle_range=4.50,  # 4.5x ATR
        )
        assert res.is_failure is True
        assert ErrorCategory.VOLATILITY_EVENT_SHOCK.value in res.categories

    def test_insufficient_evidence_noise_band(self, classifier):
        """Price stays within 0.5 ATR noise band without significant excursion."""
        res = classifier.classify_outcome(
            decision_id="test_09",
            predicted_direction=1,
            gross_pnl=-0.10,
            net_pnl=-0.80,
            total_friction=0.70,
            mfe=0.30,
            mae=0.30,
            entry_atr=1.50,  # noise band = 0.75
        )
        assert res.is_failure is True
        assert ErrorCategory.INSUFFICIENT_EVIDENCE.value in res.categories
