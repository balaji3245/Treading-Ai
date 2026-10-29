"""Adaptive Self-Learning Orchestrator for Treading-AI.

Implements the controlled feedback loop:
DECISION -> OUTCOME MATURITY -> JOURNAL -> ERROR ANALYSIS -> HYPOTHESIS ->
CHALLENGER TRAINING -> WALK-FORWARD EVALUATION -> ACCEPT/REJECT -> VERSION/ROLLBACK

Detects recurring error patterns across decision batches, formulates falsifiable
corrective hypotheses, tests challenger models under strict gates, and maintains
governance records.
"""

from dataclasses import asdict, dataclass, field
import datetime
import logging
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from treading_ai.audit.error_classifier import ErrorCategory
from treading_ai.audit.trade_journal import DecisionJournal
from treading_ai.governance.challenger_gate import ChallengerGate, GateDecision, PromotionCriteria
from treading_ai.governance.model_registry import ModelMetadata, ModelRegistry

logger = logging.getLogger(__name__)


@dataclass
class ErrorClusterAnalysis:
    """Summary of error patterns detected in a batch of decisions."""
    batch_size: int
    matured_trades: int
    win_count: int
    loss_count: int
    win_rate: float
    total_net_pnl: float
    error_counts: Dict[str, int]
    top_error_category: str
    top_error_frequency: float
    regime_loss_distribution: Dict[str, int]
    session_loss_distribution: Dict[str, int]
    dominant_failure_mode: str


@dataclass
class CorrectiveHypothesis:
    """Falsifiable corrective hypothesis formulated from error pattern analysis."""
    hypothesis_id: str
    target_error_category: str
    description: str
    rule_type: str  # 'REGIME_FILTER', 'STRUCTURE_ALIGNMENT', 'SWEEP_CONFIRMATION', 'COST_HURDLE'
    parameter_adjustments: Dict[str, Any]
    expected_mechanism: str


@dataclass
class LearningStepResult:
    """Complete record of an adaptive learning iteration."""
    step_id: str
    timestamp: str
    incumbent_version: str
    error_analysis: ErrorClusterAnalysis
    hypothesis: CorrectiveHypothesis
    challenger_version: str
    gate_decision: GateDecision
    action_taken: str  # 'PROMOTED_CHALLENGER', 'RETAINED_INCUMBENT'
    justification: str


class AdaptiveLearner:
    """Orchestrates evidence-driven adaptive learning and model updates."""

    def __init__(
        self,
        journal: DecisionJournal,
        registry: ModelRegistry,
        gate: Optional[ChallengerGate] = None,
    ):
        self.journal = journal
        self.registry = registry
        self.gate = gate or ChallengerGate()

    def analyze_batch_errors(self, batch_size: int = 50, model_version: Optional[str] = None) -> ErrorClusterAnalysis:
        """
        Examine the latest matured decisions from the journal and identify error clusters.

        Args:
            batch_size: Number of most recent matured decisions to inspect.
            model_version: Filter by specific model version if provided.

        Returns:
            ErrorClusterAnalysis containing failure mode frequencies.
        """
        df = self.journal.query(model_version=model_version, outcome_observed_only=True)
        trades_df = df[df["decision"].isin(["BUY", "SELL"])].tail(batch_size)

        if len(trades_df) == 0:
            return ErrorClusterAnalysis(
                batch_size=0,
                matured_trades=0,
                win_count=0,
                loss_count=0,
                win_rate=0.0,
                total_net_pnl=0.0,
                error_counts={},
                top_error_category="NONE",
                top_error_frequency=0.0,
                regime_loss_distribution={},
                session_loss_distribution={},
                dominant_failure_mode="NO_TRADES",
            )

        wins = trades_df[trades_df["net_pnl"] > 0]
        losses = trades_df[trades_df["net_pnl"] < 0]

        win_count = len(wins)
        loss_count = len(losses)
        win_rate = win_count / len(trades_df)
        total_net_pnl = float(trades_df["net_pnl"].sum())

        # Error category frequencies
        error_counts: Dict[str, int] = {}
        regime_losses: Dict[str, int] = {}
        session_losses: Dict[str, int] = {}

        for _, row in losses.iterrows():
            cat = row.get("primary_error_category") or "UNKNOWN"
            error_counts[cat] = error_counts.get(cat, 0) + 1

            reg = row.get("market_regime") or "UNKNOWN"
            regime_losses[reg] = regime_losses.get(reg, 0) + 1

            sess = row.get("session") or "UNKNOWN"
            session_losses[sess] = session_losses.get(sess, 0) + 1

        top_cat = "NONE"
        top_freq = 0.0
        if error_counts and loss_count > 0:
            top_cat = max(error_counts, key=error_counts.get)
            top_freq = error_counts[top_cat] / loss_count

        # Identify dominant failure mode
        dominant_failure = top_cat
        if regime_losses.get("LOW", 0) / max(1, loss_count) >= 0.40:
            dominant_failure = "LOW_REGIME_CONCENTRATION"

        return ErrorClusterAnalysis(
            batch_size=len(trades_df),
            matured_trades=len(trades_df),
            win_count=win_count,
            loss_count=loss_count,
            win_rate=win_rate,
            total_net_pnl=total_net_pnl,
            error_counts=error_counts,
            top_error_category=top_cat,
            top_error_frequency=top_freq,
            regime_loss_distribution=regime_losses,
            session_loss_distribution=session_losses,
            dominant_failure_mode=dominant_failure,
        )

    def formulate_corrective_hypothesis(self, analysis: ErrorClusterAnalysis) -> CorrectiveHypothesis:
        """
        Formulate a specific, falsifiable corrective hypothesis based on error cluster analysis.
        """
        now_ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
        hypo_id = f"hypo_{now_ts}"

        # 1. High concentration of losses in LOW volatility regime
        if analysis.dominant_failure_mode == "LOW_REGIME_CONCENTRATION" or (
            analysis.top_error_category in [ErrorCategory.REGIME_MISMATCH.value, ErrorCategory.TRANSACTION_COST_DRAG.value]
            and analysis.regime_loss_distribution.get("LOW", 0) > 0
        ):
            return CorrectiveHypothesis(
                hypothesis_id=hypo_id,
                target_error_category=ErrorCategory.REGIME_MISMATCH.value,
                description="Suppress all directional trade entries during LOW volatility regimes where ambient price movement cannot overcome bid-ask spread and slippage friction.",
                rule_type="REGIME_FILTER",
                parameter_adjustments={"allowed_regimes": ["NORMAL", "HIGH", "EXTREME"], "min_atr_threshold": 1.15},
                expected_mechanism="Prunes low-expectancy trades that disproportionately incur friction losses.",
            )

        # 2. Dominant ENTRY_TIMING_ERROR
        if analysis.top_error_category == ErrorCategory.ENTRY_TIMING_ERROR.value:
            return CorrectiveHypothesis(
                hypothesis_id=hypo_id,
                target_error_category=ErrorCategory.ENTRY_TIMING_ERROR.value,
                description="Require liquidity sweep-and-reclaim or FVG retest confirmation before executing entry, preventing premature stop-outs.",
                rule_type="SWEEP_CONFIRMATION",
                parameter_adjustments={"require_sweep_reclaim": True, "fvg_retest_required": True},
                expected_mechanism="Delays entry until market exhibits structural exhaustion and rejection.",
            )

        # 3. Dominant DIRECTIONAL_THESIS_ERROR
        if analysis.top_error_category == ErrorCategory.DIRECTIONAL_THESIS_ERROR.value:
            return CorrectiveHypothesis(
                hypothesis_id=hypo_id,
                target_error_category=ErrorCategory.DIRECTIONAL_THESIS_ERROR.value,
                description="Enforce higher timeframe (H1/H4) structural alignment: BUY only when structure is Bullish (HH+HL or BOS), SELL only when Bearish (LH+LL or BOS).",
                rule_type="STRUCTURE_ALIGNMENT",
                parameter_adjustments={"require_htf_bos_alignment": True, "min_trend_state": 1},
                expected_mechanism="Eliminates counter-trend entries that fight established order flow.",
            )

        # Default fallback: Cost hurdle tightening
        return CorrectiveHypothesis(
            hypothesis_id=hypo_id,
            target_error_category=ErrorCategory.TRANSACTION_COST_DRAG.value,
            description="Tighten selective probability threshold from 0.60 to 0.65 to ensure estimated gross edge overcomes transaction costs.",
            rule_type="COST_HURDLE",
            parameter_adjustments={"probability_threshold": 0.65},
            expected_mechanism="Increases selectivity, trading only setups with higher estimated confidence.",
        )

    def execute_learning_iteration(
        self,
        batch_size: int = 50,
        challenger_version: Optional[str] = None,
        challenger_eval_func: Optional[Any] = None,
    ) -> LearningStepResult:
        """
        Execute an end-to-end adaptive learning iteration:
        1. Analyze error patterns in recent matured trades.
        2. Formulate falsifiable hypothesis.
        3. Evaluate challenger model / policy incorporating the hypothesis.
        4. Pass through ChallengerGate for pre-registered hurdle verification.
        5. Promote to INCUMBENT if passing, or REJECT and retain current incumbent.
        """
        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
        step_id = f"step_{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S')}"

        incumbent = self.registry.get_incumbent()
        inc_version = incumbent.model_version if incumbent else "NONE"
        inc_metrics = incumbent.performance_metrics if incumbent else None

        # Step 1: Analyze errors
        analysis = self.analyze_batch_errors(batch_size=batch_size, model_version=inc_version if inc_version != "NONE" else None)

        # Step 2: Formulate hypothesis
        hypothesis = self.formulate_corrective_hypothesis(analysis)

        # Step 3: Evaluate challenger
        chal_ver = challenger_version or f"chal_{hypothesis.rule_type.lower()}_{datetime.datetime.now(datetime.timezone.utc).strftime('%m%d_%H%M')}"

        if challenger_eval_func is not None:
            chal_metrics, stress_metrics = challenger_eval_func(hypothesis)
        else:
            # Default synthetic evaluation metrics from hypothesis simulation
            chal_metrics = {
                "net_pnl": -500.0,
                "profit_factor": 0.89,
                "trade_count": 45,
                "max_drawdown": 1200.0,
                "fold_pnls": [-200.0, -150.0, -150.0],
            }
            stress_metrics = {"net_pnl": -750.0}

        # Step 4: Register challenger in registry
        self.registry.register_model(
            model_version=chal_ver,
            model_obj={"hypothesis": asdict(hypothesis)},
            model_class=hypothesis.rule_type,
            feature_names=["market_structure", "technical", "regimes"],
            hyperparameters=hypothesis.parameter_adjustments,
            status="CHALLENGER",
            performance_metrics=chal_metrics,
            parent_version=inc_version,
            hypothesis_tested=hypothesis.description,
        )

        # Step 5: Evaluate against promotion gate
        gate_decision = self.gate.evaluate(
            challenger_metrics=chal_metrics,
            incumbent_metrics=inc_metrics,
            stress_metrics=stress_metrics,
        )

        # Step 6: Governance Action
        if gate_decision.is_approved:
            action = "PROMOTED_CHALLENGER"
            justification = f"Passed all gates. Scorecard: {gate_decision.scorecard}"
            self.registry.promote_challenger(chal_ver, justification=justification)
        else:
            action = "RETAINED_INCUMBENT"
            justification = f"Rejected: {'; '.join(gate_decision.rejection_reasons)}"
            self.registry.reject_challenger(chal_ver, rejection_reason=justification)

        return LearningStepResult(
            step_id=step_id,
            timestamp=now_str,
            incumbent_version=inc_version,
            error_analysis=analysis,
            hypothesis=hypothesis,
            challenger_version=chal_ver,
            gate_decision=gate_decision,
            action_taken=action,
            justification=justification,
        )
