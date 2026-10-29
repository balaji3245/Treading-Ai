"""Classification Evaluation Engine for Financial Directional Predictions.

Computes comprehensive, uninflated metrics:
- Overall accuracy and balanced accuracy (unweighted class recall average).
- Macro-averaged F1 score.
- Per-class precision, recall, F1, and support for classes {-1, 0, +1}.
- Confusion matrix (3x3).
- Observed class distributions vs predicted distributions.
- Coverage metrics (valid vs purged observations).
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
)


@dataclass(frozen=True)
class PerClassMetrics:
    precision: float
    recall: float
    f1: float
    support: int


@dataclass(frozen=True)
class ClassificationMetrics:
    """Complete classification evaluation container."""
    model_name: str
    split_name: str
    n_total: int
    n_valid: int
    n_purged: int
    coverage: float
    accuracy: float
    balanced_accuracy: float
    macro_f1: float
    per_class: Dict[int, PerClassMetrics]
    confusion_mat: np.ndarray  # shape (3, 3) for [-1, 0, 1]
    observed_distribution: Dict[int, float]
    predicted_distribution: Dict[int, float]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "split_name": self.split_name,
            "n_total": self.n_total,
            "n_valid": self.n_valid,
            "n_purged": self.n_purged,
            "coverage": self.coverage,
            "accuracy": self.accuracy,
            "balanced_accuracy": self.balanced_accuracy,
            "macro_f1": self.macro_f1,
            "per_class": {
                cls: {
                    "precision": m.precision,
                    "recall": m.recall,
                    "f1": m.f1,
                    "support": m.support,
                }
                for cls, m in self.per_class.items()
            },
            "confusion_matrix": self.confusion_mat.tolist(),
            "observed_distribution": self.observed_distribution,
            "predicted_distribution": self.predicted_distribution,
        }

    def summary_table(self) -> str:
        """Formatted summary table representation."""
        lines = [
            f"=== {self.model_name} on {self.split_name} ===",
            f"Total Rows: {self.n_total:,} | Valid: {self.n_valid:,} | Purged: {self.n_purged:,} (Coverage: {self.coverage:.2%})",
            f"Accuracy: {self.accuracy:.4f} | Balanced Accuracy: {self.balanced_accuracy:.4f} | Macro-F1: {self.macro_f1:.4f}",
            "",
            "Per-Class Metrics (Canonical [-1, 0, +1]):",
            f"  Class -1 (Short):   Prec={self.per_class[-1].precision:.4f}, Rec={self.per_class[-1].recall:.4f}, F1={self.per_class[-1].f1:.4f}, Support={self.per_class[-1].support:,}",
            f"  Class  0 (Neutral): Prec={self.per_class[0].precision:.4f}, Rec={self.per_class[0].recall:.4f}, F1={self.per_class[0].f1:.4f}, Support={self.per_class[0].support:,}",
            f"  Class +1 (Long):    Prec={self.per_class[1].precision:.4f}, Rec={self.per_class[1].recall:.4f}, F1={self.per_class[1].f1:.4f}, Support={self.per_class[1].support:,}",
            "",
            "Confusion Matrix [rows=True, cols=Pred]:",
            f"  True -1:  {self.confusion_mat[0, 0]:6d}  {self.confusion_mat[0, 1]:6d}  {self.confusion_mat[0, 2]:6d}",
            f"  True  0:  {self.confusion_mat[1, 0]:6d}  {self.confusion_mat[1, 1]:6d}  {self.confusion_mat[1, 2]:6d}",
            f"  True +1:  {self.confusion_mat[2, 0]:6d}  {self.confusion_mat[2, 1]:6d}  {self.confusion_mat[2, 2]:6d}",
        ]
        return "\n".join(lines)


def evaluate_classification(
    y_true: Union[np.ndarray, pd.Series],
    y_pred: Union[np.ndarray, pd.Series],
    model_name: str,
    split_name: str,
    n_total: Optional[int] = None,
    n_purged: Optional[int] = None,
) -> ClassificationMetrics:
    """Compute all required classification metrics on valid, non-purged observations.

    Parameters
    ----------
    y_true : Union[np.ndarray, pd.Series]
        Ground-truth labels in {-1, 0, +1}. Purged rows must already be filtered out.
    y_pred : Union[np.ndarray, pd.Series]
        Predicted labels in {-1, 0, +1}.
    model_name : str
        Identifier for the model.
    split_name : str
        Identifier for the dataset split or fold.
    n_total : Optional[int]
        Total raw rows before purging.
    n_purged : Optional[int]
        Number of purged rows.
    """
    y_t = np.asarray(y_true, dtype=int)
    y_p = np.asarray(y_pred, dtype=int)

    if len(y_t) != len(y_p):
        raise ValueError(f"Length mismatch: y_true ({len(y_t)}) vs y_pred ({len(y_p)})")
    if len(y_t) == 0:
        raise ValueError("Cannot evaluate classification on empty arrays.")

    n_valid = len(y_t)
    total_obs = n_total if n_total is not None else n_valid
    purged_obs = n_purged if n_purged is not None else (total_obs - n_valid)
    coverage = float(n_valid / total_obs) if total_obs > 0 else 0.0

    acc = float(accuracy_score(y_t, y_p))
    bal_acc = float(balanced_accuracy_score(y_t, y_p))
    m_f1 = float(f1_score(y_t, y_p, average="macro", zero_division=0))

    # Per-class metrics
    labels = [-1, 0, 1]
    p, r, f, s = precision_recall_fscore_support(y_t, y_p, labels=labels, zero_division=0)

    per_class = {
        cls: PerClassMetrics(
            precision=float(p[i]),
            recall=float(r[i]),
            f1=float(f[i]),
            support=int(s[i]),
        )
        for i, cls in enumerate(labels)
    }

    # Confusion matrix
    cm = confusion_matrix(y_t, y_p, labels=labels)

    # Distributions
    obs_dist = {cls: float(np.mean(y_t == cls)) for cls in labels}
    pred_dist = {cls: float(np.mean(y_p == cls)) for cls in labels}

    return ClassificationMetrics(
        model_name=model_name,
        split_name=split_name,
        n_total=total_obs,
        n_valid=n_valid,
        n_purged=purged_obs,
        coverage=coverage,
        accuracy=acc,
        balanced_accuracy=bal_acc,
        macro_f1=m_f1,
        per_class=per_class,
        confusion_mat=cm,
        observed_distribution=obs_dist,
        predicted_distribution=pred_dist,
    )
