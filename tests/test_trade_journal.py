"""Unit tests for SQLite-backed Decision and Trade Journal."""

from pathlib import Path
import pytest
from treading_ai.audit.trade_journal import DecisionJournal, JournalEntry


@pytest.fixture
def temp_journal(tmp_path: Path):
    db_file = tmp_path / "test_journal.db"
    return DecisionJournal(db_path=db_file)


class TestDecisionJournal:
    """Verifies persistence, outcome updates, and query functionality."""

    def test_record_and_get_decision(self, temp_journal):
        """Record decision and retrieve exact fields."""
        decision_id = "dec_001"
        temp_journal.record_decision(
            decision_id=decision_id,
            timestamp="2024-01-08T10:00:00Z",
            data_version="v2.1",
            feature_version="v2.1",
            model_version="lr_baseline_v1",
            strategy_id="strat_selective_60",
            decision="BUY",
            predicted_direction=1,
            confidence=0.68,
            expected_horizon_bars=24,
            entry_reference_price=2035.50,
            market_regime="HIGH",
            session="LONDON",
            structure_state="BULLISH",
            reasoning_summary="Bullish CHoCH confirmed with FVG retest",
            stop_loss_price=2030.00,
            target_price=2045.00,
            invalidation_price=2028.00,
            feature_evidence={"rsi_14": 56.4, "ms_trend_state": 1},
        )

        entry = temp_journal.get_decision(decision_id)
        assert entry is not None
        assert entry.decision_id == decision_id
        assert entry.decision == "BUY"
        assert entry.predicted_direction == 1
        assert entry.confidence == 0.68
        assert entry.entry_reference_price == 2035.50
        assert entry.market_regime == "HIGH"
        assert entry.outcome_observed is False
        assert entry.net_pnl is None

    def test_record_outcome_updates_entry_and_diagnoses_error(self, temp_journal):
        """Record outcome, assert fields updated and error diagnosis populated."""
        decision_id = "dec_002"
        temp_journal.record_decision(
            decision_id=decision_id,
            timestamp="2024-01-08T11:00:00Z",
            data_version="v2.1",
            feature_version="v2.1",
            model_version="lr_baseline_v1",
            strategy_id="strat_selective_60",
            decision="BUY",
            predicted_direction=1,
            confidence=0.62,
            expected_horizon_bars=24,
            entry_reference_price=2035.00,
            market_regime="NORMAL",
            session="LONDON",
            structure_state="BULLISH",
            reasoning_summary="Bullish trend continuation",
        )

        # Record outcome: stopped out after favorable move
        diag = temp_journal.record_outcome(
            decision_id=decision_id,
            outcome_timestamp="2024-01-08T13:00:00Z",
            exit_price=2033.00,
            exit_reason="STOP",
            bars_held=24,
            gross_pnl=-2.00,
            estimated_friction=0.70,
            net_pnl=-2.70,
            mfe=3.50,  # reached strong favorable move
            mae=2.20,
            entry_atr=1.50,
            target_distance=3.0,
            stop_distance=1.5,
        )

        assert diag.is_failure is True
        assert "ENTRY_TIMING_ERROR" in diag.categories

        entry = temp_journal.get_decision(decision_id)
        assert entry.outcome_observed is True
        assert entry.net_pnl == -2.70
        assert entry.mfe == 3.50
        assert entry.mae == 2.20
        assert entry.primary_error_category == "ENTRY_TIMING_ERROR"
        assert "ENTRY_TIMING_ERROR" in entry.error_categories_json
        assert len(entry.corrective_hypothesis) > 0

    def test_query_and_summarize_performance(self, temp_journal):
        """Test performance aggregation across multiple decisions."""
        # 1 win, 1 loss, 1 NONE
        temp_journal.record_decision(
            decision_id="win_01",
            timestamp="2024-01-08T10:00:00Z",
            data_version="v2.1",
            feature_version="v2.1",
            model_version="test_model",
            strategy_id="strat_a",
            decision="BUY",
            predicted_direction=1,
            confidence=0.65,
            expected_horizon_bars=24,
            entry_reference_price=2030.00,
            market_regime="HIGH",
            session="LONDON",
            structure_state="BULLISH",
            reasoning_summary="Win trade",
        )
        temp_journal.record_outcome(
            decision_id="win_01",
            outcome_timestamp="2024-01-08T12:00:00Z",
            exit_price=2034.00,
            exit_reason="TARGET",
            bars_held=24,
            gross_pnl=4.00,
            estimated_friction=0.60,
            net_pnl=3.40,
            mfe=4.50,
            mae=0.50,
            entry_atr=1.50,
        )

        temp_journal.record_decision(
            decision_id="loss_01",
            timestamp="2024-01-08T14:00:00Z",
            data_version="v2.1",
            feature_version="v2.1",
            model_version="test_model",
            strategy_id="strat_a",
            decision="SELL",
            predicted_direction=-1,
            confidence=0.60,
            expected_horizon_bars=24,
            entry_reference_price=2030.00,
            market_regime="LOW",
            session="NY",
            structure_state="NEUTRAL",
            reasoning_summary="Loss trade in LOW regime",
        )
        temp_journal.record_outcome(
            decision_id="loss_01",
            outcome_timestamp="2024-01-08T16:00:00Z",
            exit_price=2031.50,
            exit_reason="TIME",
            bars_held=24,
            gross_pnl=-1.50,
            estimated_friction=0.60,
            net_pnl=-2.10,
            mfe=0.20,
            mae=1.80,
            entry_atr=1.00,
        )

        summary = temp_journal.summarize_performance(model_version="test_model")
        assert summary["matured_trades"] == 2
        assert summary["win_rate"] == 0.50
        assert summary["total_net_pnl"] == pytest.approx(1.30, abs=1e-3)
        assert summary["profit_factor"] == pytest.approx(3.40 / 2.10, abs=1e-2)
        assert "REGIME_MISMATCH" in summary["error_distribution"] or "DIRECTIONAL_THESIS_ERROR" in summary["error_distribution"]

    def test_export_to_parquet(self, temp_journal, tmp_path: Path):
        """Verify journal exports cleanly to Parquet."""
        temp_journal.record_decision(
            decision_id="dec_parquet",
            timestamp="2024-01-08T10:00:00Z",
            data_version="v2.1",
            feature_version="v2.1",
            model_version="test_model",
            strategy_id="strat_a",
            decision="BUY",
            predicted_direction=1,
            confidence=0.65,
            expected_horizon_bars=24,
            entry_reference_price=2030.00,
            market_regime="HIGH",
            session="LONDON",
            structure_state="BULLISH",
            reasoning_summary="Parquet test",
        )
        out_pq = tmp_path / "journal_export.parquet"
        result_path = temp_journal.export_to_parquet(out_pq)
        assert result_path.exists()
        assert result_path.stat().st_size > 0
