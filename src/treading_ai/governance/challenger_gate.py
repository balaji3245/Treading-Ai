"""Challenger Validation Gate and Promotion Engine for Treading-AI.

Enforces pre-registered statistical and economic hurdles before any challenger
model or strategy can replace the incumbent. Prevents overfitting, selection bias,
and unverified self-learning claims.
"""

from dataclasses import dataclass, field
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class GateDecision:
    """Outcome of challenger validation against promotion criteria."""
    is_approved: bool
    rejection_reasons: List[str]
    scorecard: Dict[str, Any]
    recommendation: str  # 'PROMOTE', 'REJECT'


@dataclass
class PromotionCriteria:
    """Pre-registered acceptance criteria for model promotion."""
    min_net_expectancy: float = 0.0  # Must beat flat no-trade baseline
    min_profit_factor: float = 1.0   # Must have positive gross edge
    min_trades_count: int = 30       # Minimum sample size requirement
    max_drawdown_tolerance: float = 1.10  # Max drawdown cannot exceed incumbent by >10%
    min_improvement_net_pnl: float = 100.0  # Must improve net PnL by at least $100/oz
    stress_spread_multiplier: float = 1.5   # Tested under 1.5x spread stress


class ChallengerGate:
    """Evaluates challenger models against incumbents under strict pre-registered hurdles."""

    def __init__(self, criteria: Optional[PromotionCriteria] = None):
        self.criteria = criteria or PromotionCriteria()

    def evaluate(
        self,
        challenger_metrics: Dict[str, Any],
        incumbent_metrics: Optional[Dict[str, Any]] = None,
        stress_metrics: Optional[Dict[str, Any]] = None,
    ) -> GateDecision:
        """
        Evaluate a candidate challenger against the incumbent and acceptance criteria.

        Args:
            challenger_metrics: Performance metrics on unseen walk-forward test folds.
                Must include: 'net_pnl', 'profit_factor', 'trade_count', 'max_drawdown', 'fold_pnls'.
            incumbent_metrics: Performance metrics of the incumbent model.
            stress_metrics: Performance metrics under 1.5x spread and slippage stress.

        Returns:
            GateDecision with approval status, rejection reasons, and scorecard.
        """
        rejection_reasons: List[str] = []
        scorecard: Dict[str, Any] = {}

        chal_net_pnl = float(challenger_metrics.get("net_pnl", 0.0))
        chal_pf = float(challenger_metrics.get("profit_factor", 0.0))
        chal_trades = int(challenger_metrics.get("trade_count", 0))
        chal_dd = abs(float(challenger_metrics.get("max_drawdown", 0.0)))
        chal_fold_pnls = challenger_metrics.get("fold_pnls", [])

        scorecard["challenger_net_pnl"] = chal_net_pnl
        scorecard["challenger_profit_factor"] = chal_pf
        scorecard["challenger_trade_count"] = chal_trades
        scorecard["challenger_max_drawdown"] = chal_dd

        # 1. Minimum Sample Size Hurdle
        if chal_trades < self.criteria.min_trades_count:
            rejection_reasons.append(
                f"Sample size too small ({chal_trades} trades < required {self.criteria.min_trades_count})."
            )

        # 2. Benchmark Hurdle: Beat No-Trade Baseline
        if chal_net_pnl < self.criteria.min_net_expectancy:
            # If negative net PnL, check whether it is at least an improvement over incumbent
            if incumbent_metrics is not None:
                inc_net_pnl = float(incumbent_metrics.get("net_pnl", 0.0))
                scorecard["incumbent_net_pnl"] = inc_net_pnl
                improvement = chal_net_pnl - inc_net_pnl
                scorecard["net_pnl_improvement"] = improvement

                if improvement < self.criteria.min_improvement_net_pnl:
                    rejection_reasons.append(
                        f"Net PnL (${chal_net_pnl:.2f}) failed positive expectancy hurdle (${self.criteria.min_net_expectancy:.2f}) "
                        f"and improvement (${improvement:.2f}) is below hurdle (${self.criteria.min_improvement_net_pnl:.2f})."
                    )
                else:
                    # Partial improvement, but still negative net PnL
                    rejection_reasons.append(
                        f"Net PnL (${chal_net_pnl:.2f}) remains negative after transaction costs (No-Trade baseline $0.00 dominates)."
                    )
            else:
                rejection_reasons.append(
                    f"Net PnL (${chal_net_pnl:.2f}) is negative after transaction costs (fails No-Trade baseline)."
                )

        # 3. Profit Factor Hurdle
        if chal_pf < self.criteria.min_profit_factor:
            rejection_reasons.append(
                f"Profit Factor ({chal_pf:.3f}) is below hurdle ({self.criteria.min_profit_factor:.3f})."
            )

        # 4. Drawdown Comparison
        if incumbent_metrics is not None:
            inc_dd = abs(float(incumbent_metrics.get("max_drawdown", 0.0)))
            scorecard["incumbent_max_drawdown"] = inc_dd
            if inc_dd > 0:
                if chal_dd > inc_dd * self.criteria.max_drawdown_tolerance:
                    rejection_reasons.append(
                        f"Max Drawdown (${chal_dd:.2f}) exceeds incumbent (${inc_dd:.2f}) by >{int((self.criteria.max_drawdown_tolerance - 1) * 100)}%."
                    )

        # 5. Chronological Fold Stability
        if len(chal_fold_pnls) > 1:
            neg_folds = [p for p in chal_fold_pnls if p < 0]
            scorecard["negative_fold_count"] = len(neg_folds)
            scorecard["total_folds"] = len(chal_fold_pnls)
            # If all folds are negative, reject
            if len(neg_folds) == len(chal_fold_pnls):
                rejection_reasons.append("All chronological walk-forward folds produced negative net PnL.")

        # 6. Spread Stress Test Hurdle
        if stress_metrics is not None:
            stress_net_pnl = float(stress_metrics.get("net_pnl", 0.0))
            scorecard["stress_net_pnl"] = stress_net_pnl
            if incumbent_metrics is not None:
                inc_stress_pnl = float(incumbent_metrics.get("stress_net_pnl", incumbent_metrics.get("net_pnl", 0.0)))
                if stress_net_pnl < inc_stress_pnl - 100.0:
                    rejection_reasons.append(
                        f"Challenger deteriorated excessively under 1.5x spread stress (${stress_net_pnl:.2f} vs incumbent ${inc_stress_pnl:.2f})."
                    )

        is_approved = len(rejection_reasons) == 0
        recommendation = "PROMOTE" if is_approved else "REJECT"

        scorecard["is_approved"] = is_approved
        scorecard["rejection_reasons_count"] = len(rejection_reasons)

        if is_approved:
            logger.info("Challenger PASSED all promotion gates! Scorecard: %s", scorecard)
        else:
            logger.warning("Challenger REJECTED by gatekeeper: %s", rejection_reasons)

        return GateDecision(
            is_approved=is_approved,
            rejection_reasons=rejection_reasons,
            scorecard=scorecard,
            recommendation=recommendation,
        )
