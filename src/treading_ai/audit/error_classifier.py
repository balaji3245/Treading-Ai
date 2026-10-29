"""Evidence-based Error Classification Taxonomy for XAUUSD Trade Audits.

This module categorizes trade failures and adverse outcomes into distinct,
falsifiable diagnostic buckets to enable evidence-driven learning:
- DIRECTIONAL_THESIS_ERROR: Market moved adversely from entry without entering profit.
- ENTRY_TIMING_ERROR: Market eventually moved in predicted direction, but stopped out prematurely.
- EXIT_RISK_ERROR: Floating profit reached substantial gain, but was given back to a loss.
- REGIME_MISMATCH: Trade strategy incompatible with current macro/volatility regime.
- VOLATILITY_EVENT_SHOCK: Extreme single-candle spike or rollover closure disruption.
- TRANSACTION_COST_DRAG: Gross PnL was positive, but friction produced a net loss.
- DATA_QUALITY_PROBLEM: Execution during abnormal spread expansion or data anomaly.
- MODEL_OVERCONFIDENCE: High predicted confidence (>=0.70) with severe loss (MAE > 2.0 ATR).
- INSUFFICIENT_EVIDENCE: Price remained within ambient noise band; outcome ambiguous.

Multi-label classification is supported when multiple distinct factors contributed.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set
import numpy as np


class ErrorCategory(str, Enum):
    """Standardized error taxonomy categories."""
    DIRECTIONAL_THESIS_ERROR = "DIRECTIONAL_THESIS_ERROR"
    ENTRY_TIMING_ERROR = "ENTRY_TIMING_ERROR"
    EXIT_RISK_ERROR = "EXIT_RISK_ERROR"
    REGIME_MISMATCH = "REGIME_MISMATCH"
    VOLATILITY_EVENT_SHOCK = "VOLATILITY_EVENT_SHOCK"
    TRANSACTION_COST_DRAG = "TRANSACTION_COST_DRAG"
    DATA_QUALITY_PROBLEM = "DATA_QUALITY_PROBLEM"
    MODEL_OVERCONFIDENCE = "MODEL_OVERCONFIDENCE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


@dataclass
class DiagnosticResult:
    """Result of post-outcome trade error diagnosis."""
    decision_id: str
    is_failure: bool
    categories: List[str]
    primary_reason: str
    explanation: str
    corrective_hypothesis: str
    metrics: Dict[str, float]


class TradeErrorClassifier:
    """Classifies simulated and historical trade outcomes against the error taxonomy."""

    def __init__(
        self,
        noise_atr_band: float = 0.5,
        overconfidence_prob: float = 0.70,
        overconfidence_mae_atr: float = 2.0,
        volatility_shock_atr_mult: float = 3.0,
    ):
        """
        Initialize TradeErrorClassifier.

        Args:
            noise_atr_band: Multiplier of ATR defining the ambient noise band.
            overconfidence_prob: Probability threshold above which large loss indicates overconfidence.
            overconfidence_mae_atr: MAE in ATR units defining severe loss for overconfidence.
            volatility_shock_atr_mult: Multiplier of ATR defining a volatility shock.
        """
        self.noise_atr_band = noise_atr_band
        self.overconfidence_prob = overconfidence_prob
        self.overconfidence_mae_atr = overconfidence_mae_atr
        self.volatility_shock_atr_mult = volatility_shock_atr_mult

    def classify_outcome(
        self,
        decision_id: str,
        predicted_direction: int,  # +1 (Long), -1 (Short), 0 (None)
        gross_pnl: float,
        net_pnl: float,
        total_friction: float,
        mfe: float,  # Maximum Favorable Excursion ($/oz)
        mae: float,  # Maximum Adverse Excursion ($/oz, positive value)
        entry_atr: float,
        confidence: Optional[float] = None,
        market_regime: Optional[str] = None,  # 'LOW', 'NORMAL', 'HIGH', 'EXTREME'
        exit_reason: Optional[str] = None,    # 'TARGET', 'STOP', 'TIME'
        target_distance: Optional[float] = None,
        stop_distance: Optional[float] = None,
        max_candle_range: Optional[float] = None,
        is_rollover: bool = False,
    ) -> DiagnosticResult:
        """
        Diagnose a completed trade outcome and assign error classifications.

        Args:
            decision_id: Unique identifier for the trade decision.
            predicted_direction: 1 for Long, -1 for Short, 0 for None.
            gross_pnl: Realized gross PnL ($/oz).
            net_pnl: Realized net PnL after all friction ($/oz).
            total_friction: Total spread + slippage + commission ($/oz).
            mfe: Maximum Favorable Excursion ($/oz).
            mae: Maximum Adverse Excursion ($/oz, >= 0).
            entry_atr: ATR at order entry ($/oz).
            confidence: Model confidence / probability (0.0 to 1.0).
            market_regime: Macro volatility regime string.
            exit_reason: Simulator exit reason ('TARGET', 'STOP', 'TIME').
            target_distance: Profit target distance ($/oz).
            stop_distance: Stop loss distance ($/oz).
            max_candle_range: Maximum single bar high-low range during trade ($/oz).
            is_rollover: Whether trade crossed or executed in rollover window.

        Returns:
            DiagnosticResult with assigned categories and corrective hypothesis.
        """
        atr = entry_atr if entry_atr > 1e-4 else 1.0
        mfe_atr = mfe / atr
        mae_atr = mae / atr
        noise_band = self.noise_atr_band * atr

        categories: List[ErrorCategory] = []
        is_failure = net_pnl < 0.0

        # Successful trade (Net PnL >= 0)
        if not is_failure:
            return DiagnosticResult(
                decision_id=decision_id,
                is_failure=False,
                categories=[],
                primary_reason="SUCCESSFUL_EXECUTION",
                explanation=f"Trade achieved positive net PnL (${net_pnl:.2f}/oz, Gross: ${gross_pnl:.2f}/oz).",
                corrective_hypothesis="No correction needed; trade satisfied positive net expectancy criteria.",
                metrics={"gross_pnl": gross_pnl, "net_pnl": net_pnl, "mfe": mfe, "mae": mae, "mfe_atr": mfe_atr},
            )

        # 1. TRANSACTION_COST_DRAG
        # Gross profit was positive, but friction pushed net PnL into a loss
        if gross_pnl > 0.0 and net_pnl < 0.0:
            categories.append(ErrorCategory.TRANSACTION_COST_DRAG)

        # 2. VOLATILITY_EVENT_SHOCK
        if max_candle_range is not None and max_candle_range >= self.volatility_shock_atr_mult * atr:
            categories.append(ErrorCategory.VOLATILITY_EVENT_SHOCK)
        elif is_rollover:
            categories.append(ErrorCategory.VOLATILITY_EVENT_SHOCK)

        # 3. REGIME_MISMATCH
        if market_regime is not None:
            if market_regime == "LOW":
                # Low volatility compression: price movement too small to overcome friction
                categories.append(ErrorCategory.REGIME_MISMATCH)

        # 4. ENTRY_TIMING_ERROR
        # Price moved strongly in predicted direction (MFE >= target or MFE >= 1.5 ATR),
        # but trade was stopped out early due to premature entry
        target_thresh = target_distance if target_distance is not None else 1.5 * atr
        if exit_reason == "STOP" and mfe >= target_thresh:
            categories.append(ErrorCategory.ENTRY_TIMING_ERROR)

        # 5. EXIT_RISK_ERROR
        # Price went significantly into profit (MFE >= 1.5 ATR or >= target), but was not banked,
        # reversing into a loss at time limit or trailing stop
        if mfe >= 1.2 * atr and exit_reason != "TARGET" and net_pnl < 0.0:
            categories.append(ErrorCategory.EXIT_RISK_ERROR)

        # 6. MODEL_OVERCONFIDENCE
        if confidence is not None:
            if confidence >= self.overconfidence_prob and mae_atr >= self.overconfidence_mae_atr:
                categories.append(ErrorCategory.MODEL_OVERCONFIDENCE)

        # 7. INSUFFICIENT_EVIDENCE
        # Trade stayed within tight ambient noise band throughout holding period
        if mfe <= noise_band and mae <= noise_band:
            categories.append(ErrorCategory.INSUFFICIENT_EVIDENCE)

        # 8. DIRECTIONAL_THESIS_ERROR
        # Market moved against trade immediately and stayed adverse (MFE <= friction or MAE >> MFE)
        if mfe <= total_friction or (mae_atr >= 1.0 and mfe_atr < 0.3):
            if ErrorCategory.INSUFFICIENT_EVIDENCE not in categories:
                categories.append(ErrorCategory.DIRECTIONAL_THESIS_ERROR)

        # If no specific category matched, default to DIRECTIONAL_THESIS_ERROR if loss is substantial
        if len(categories) == 0:
            if mae_atr >= 0.5:
                categories.append(ErrorCategory.DIRECTIONAL_THESIS_ERROR)
            else:
                categories.append(ErrorCategory.INSUFFICIENT_EVIDENCE)

        # Determine primary failure reason and formulate falsifiable corrective hypothesis
        primary_reason = categories[0].value
        explanation, hypothesis = self._formulate_hypothesis(categories, metrics={
            "gross_pnl": gross_pnl,
            "net_pnl": net_pnl,
            "total_friction": total_friction,
            "mfe": mfe,
            "mae": mae,
            "mfe_atr": mfe_atr,
            "mae_atr": mae_atr,
            "confidence": confidence or 0.0,
            "market_regime": market_regime or "UNKNOWN",
        })

        return DiagnosticResult(
            decision_id=decision_id,
            is_failure=True,
            categories=[c.value for c in categories],
            primary_reason=primary_reason,
            explanation=explanation,
            corrective_hypothesis=hypothesis,
            metrics={
                "gross_pnl": gross_pnl,
                "net_pnl": net_pnl,
                "total_friction": total_friction,
                "mfe": mfe,
                "mae": mae,
                "mfe_atr": mfe_atr,
                "mae_atr": mae_atr,
            },
        )

    def _formulate_hypothesis(self, categories: List[ErrorCategory], metrics: Dict) -> Tuple[str, str]:
        """Generate human-readable diagnostic explanation and falsifiable corrective hypothesis."""
        cats = set(categories)
        explanations = []
        hypotheses = []

        if ErrorCategory.TRANSACTION_COST_DRAG in cats:
            explanations.append(
                f"Gross profit (${metrics['gross_pnl']:.2f}/oz) was eroded by transaction costs (${metrics['total_friction']:.2f}/oz)."
            )
            hypotheses.append("Require estimated target distance >= 3.0x expected friction before entering.")

        if ErrorCategory.REGIME_MISMATCH in cats:
            explanations.append(f"Trade executed during {metrics['market_regime']} regime where price movement cannot support costs.")
            hypotheses.append("Gate directional entries to NORMAL, HIGH, or EXTREME volatility regimes only.")

        if ErrorCategory.ENTRY_TIMING_ERROR in cats:
            explanations.append(f"Price eventually moved in direction (MFE={metrics['mfe']:.2f}), but premature entry triggered stop.")
            hypotheses.append("Wait for liquidity sweep-and-reclaim or FVG retest before executing entry.")

        if ErrorCategory.EXIT_RISK_ERROR in cats:
            explanations.append(f"Trade reached MFE of {metrics['mfe']:.2f} ({metrics['mfe_atr']:.1f} ATR) but gave it all back.")
            hypotheses.append("Implement breakeven stop adjustment once price reaches 1.0 ATR favorable excursion.")

        if ErrorCategory.VOLATILITY_EVENT_SHOCK in cats:
            explanations.append("Severe volatility spike or rollover event disrupted price action.")
            hypotheses.append("Enforce blackout periods around rollover (17:00-18:00 NY) and volatility shocks.")

        if ErrorCategory.MODEL_OVERCONFIDENCE in cats:
            explanations.append(f"Model assigned high confidence ({metrics['confidence']:.2f}) but suffered severe adverse excursion ({metrics['mae_atr']:.1f} ATR).")
            hypotheses.append("Apply probability calibration (e.g. isotonic or temperature scaling) and cap position sizing.")

        if ErrorCategory.DIRECTIONAL_THESIS_ERROR in cats:
            explanations.append(f"Market moved adverse to directional thesis from entry (MAE={metrics['mae']:.2f}, MFE={metrics['mfe']:.2f}).")
            hypotheses.append("Require higher timeframe (H1/H4) structural alignment (BOS/CHoCH) in the direction of the trade.")

        if ErrorCategory.INSUFFICIENT_EVIDENCE in cats:
            explanations.append("Price moved within ambient noise band; evidence is insufficient to conclude structural error.")
            hypotheses.append("Filter trades where expected move is smaller than ambient ATR noise threshold.")

        full_explanation = " | ".join(explanations)
        full_hypothesis = " AND ".join(hypotheses)
        return full_explanation, full_hypothesis
