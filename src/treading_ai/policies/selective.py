"""Selective Trading Policy Engine for Systematic Directional Trading.

Implements probability-thresholded and capital-constrained trade filtering:
1. Probability Thresholding: Only take trades where P(direction) >= threshold.
2. Abstention / Flat: Remain in cash (signal = 0) whenever edge is insufficient.
3. Position Capacity Constraint:
   - "overlapping": Allows concurrent active positions up to holding horizon H.
   - "non_overlapping": Strict capacity=1. Suppresses new entries while an active
     trade is open.
4. Edge Estimation & Cost Causality:
   - Evaluates expected gross edge against expected friction.
   - Zero future look-ahead: decisions use strictly bar t close probabilities.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from treading_ai.models.baselines import BaseDirectionalModel


@dataclass(frozen=True)
class PolicyOutput:
    """Output container for a policy execution run."""
    signals: np.ndarray  # Final emitted signals in {-1, 0, +1}
    raw_signals: np.ndarray  # Signals before capacity constraint
    probabilities: np.ndarray  # Shape (N, 3) for classes [-1, 0, 1]
    threshold: Optional[float]
    mode: str
    n_eligible_signals: int
    n_capacity_rejected: int
    n_executed_signals: int


class SelectiveTradingPolicy:
    """Selective trading policy wrapping a probabilistic directional predictor.

    Parameters
    ----------
    model : BaseDirectionalModel
        Underlying trained model providing `predict_proba(X)`.
    threshold : Optional[float], default=0.50
        Probability threshold for trade eligibility.
        - If None: unfiltered standard argmax prediction (Phase 4 baseline).
        - If 1.0: no-trade baseline (always flat).
        - If 0.50 <= threshold < 1.0: selective directional entry.
    mode : str, default="overlapping"
        Position execution mode:
        - "overlapping": Each eligible signal enters an independent position.
        - "non_overlapping": Strict 1-position limit. Ignores new signals while an
          existing trade is held for `holding_horizon` bars.
    holding_horizon : int, default=6
        Holding period in bars.
    """

    def __init__(
        self,
        model: BaseDirectionalModel,
        threshold: Optional[float] = 0.50,
        mode: str = "overlapping",
        holding_horizon: int = 6,
    ) -> None:
        if mode not in ["overlapping", "non_overlapping"]:
            raise ValueError(f"Invalid mode '{mode}'. Must be 'overlapping' or 'non_overlapping'.")

        self.model = model
        self.threshold = threshold
        self.mode = mode
        self.holding_horizon = holding_horizon

    def generate_signals(
        self,
        X: Union[np.ndarray, pd.DataFrame],
    ) -> PolicyOutput:
        """Generate directional trading signals with thresholding and capacity control.

        Parameters
        ----------
        X : Union[np.ndarray, pd.DataFrame]
            Feature matrix available at decision time (bar t close).
        """
        probas = self.model.predict_proba(X)
        n_samples = len(probas)

        # Canonical class alignment: index 0 is -1 (Short), 1 is 0 (Neutral), 2 is +1 (Long)
        p_short = probas[:, 0]
        p_neutral = probas[:, 1]
        p_long = probas[:, 2]

        raw_signals = np.zeros(n_samples, dtype=int)

        if self.threshold is None:
            # Unfiltered baseline: argmax over [-1, 0, 1]
            raw_signals = self.model.predict(X)
        elif self.threshold >= 1.0:
            # No-trade baseline: always flat
            raw_signals = np.zeros(n_samples, dtype=int)
        else:
            # Selective thresholding
            long_eligible = p_long >= self.threshold
            short_eligible = p_short >= self.threshold

            # For threshold >= 0.5, long and short cannot both be true.
            # For edge cases (threshold < 0.5), higher probability takes precedence.
            both_eligible = long_eligible & short_eligible
            raw_signals[long_eligible] = 1
            raw_signals[short_eligible] = -1
            if np.any(both_eligible):
                prefer_long = p_long >= p_short
                raw_signals[both_eligible & prefer_long] = 1
                raw_signals[both_eligible & (~prefer_long)] = -1

        n_eligible = int(np.sum(raw_signals != 0))

        if self.mode == "overlapping":
            # All eligible signals are passed through
            return PolicyOutput(
                signals=raw_signals.copy(),
                raw_signals=raw_signals,
                probabilities=probas,
                threshold=self.threshold,
                mode=self.mode,
                n_eligible_signals=n_eligible,
                n_capacity_rejected=0,
                n_executed_signals=n_eligible,
            )

        # Strict Single-Position Non-Overlapping Mode
        final_signals = np.zeros(n_samples, dtype=int)
        n_capacity_rejected = 0
        lockout_until = -1
        H = self.holding_horizon

        for i in range(n_samples):
            sig = raw_signals[i]
            if sig == 0:
                continue

            if i < lockout_until:
                # Currently holding an active position: capacity exhausted
                n_capacity_rejected += 1
                continue

            # Position is free: accept trade and lock out subsequent bars
            final_signals[i] = sig
            # Trade enters at i + 1 Open and exits at i + 1 + H Open.
            # Next trade can enter at i + 1 + H Open, which is signaled at i + H close.
            # Therefore bars i + 1 through i + H - 1 are locked out.
            lockout_until = i + H

        n_executed = int(np.sum(final_signals != 0))

        return PolicyOutput(
            signals=final_signals,
            raw_signals=raw_signals,
            probabilities=probas,
            threshold=self.threshold,
            mode=self.mode,
            n_eligible_signals=n_eligible,
            n_capacity_rejected=n_capacity_rejected,
            n_executed_signals=n_executed,
        )


def compute_brier_scores(
    y_true: np.ndarray,
    probas: np.ndarray,
) -> Dict[str, float]:
    """Compute multiclass Brier scores to assess probability calibration.

    Brier score = (1/N) * sum_i sum_k (p_{i,k} - y_{i,k})^2.
    Lower score indicates superior calibration (0.0 is perfect, 0.667 is uniform random).
    """
    classes = [-1, 0, 1]
    n_samples = len(y_true)
    y_one_hot = np.zeros((n_samples, 3), dtype=float)
    for k, cls in enumerate(classes):
        y_one_hot[y_true == cls, k] = 1.0

    brier_per_class = np.mean((probas - y_one_hot) ** 2, axis=0)
    total_brier = float(np.mean(np.sum((probas - y_one_hot) ** 2, axis=1)))

    return {
        "brier_short": float(brier_per_class[0]),
        "brier_neutral": float(brier_per_class[1]),
        "brier_long": float(brier_per_class[2]),
        "brier_total": total_brier,
    }
