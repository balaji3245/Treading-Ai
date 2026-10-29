"""Chronological Walk-Forward Validation Engine for Time-Series Trading ML.

Generates strictly chronological expanding-window folds with explicit horizon purging:
- No future-to-past contamination.
- Overlapping label horizons at fold boundaries are explicitly purged.
- Preserves the chronological structure of the training dataset (2021-2024).
"""

from dataclasses import dataclass
from typing import Any, Dict, Iterator, List, Optional, Tuple
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class WalkForwardFold:
    """Metadata and indices for a single walk-forward cross-validation fold."""
    fold_id: int
    train_start_time: pd.Timestamp
    train_end_time: pd.Timestamp
    eval_start_time: pd.Timestamp
    eval_end_time: pd.Timestamp
    train_indices: np.ndarray
    eval_indices: np.ndarray
    purged_boundary_indices: np.ndarray
    n_train: int
    n_eval: int
    n_purged_boundary: int


class ChronologicalWalkForward:
    """Expanding-window chronological cross-validator with boundary horizon purging.

    Parameters
    ----------
    n_splits : int, default=3
        Number of walk-forward folds.
    horizon : int, default=6
        Target label horizon $H$. The last $1 + H$ bars of the fold training window
        are purged from training to prevent label forward-leakage into the eval split.
    embargo_bars : int, default=0
        Additional embargo bars between train and eval splits.
    """

    def __init__(
        self,
        n_splits: int = 3,
        horizon: int = 6,
        embargo_bars: int = 0,
    ) -> None:
        self.n_splits = n_splits
        self.horizon = horizon
        self.embargo_bars = embargo_bars

    def split_by_years(
        self,
        df: pd.DataFrame,
        timestamp_col: str = "timestamp",
    ) -> List[WalkForwardFold]:
        """Generate expanding-window folds split strictly by calendar year inside the dataset.

        For 2021-2024 training data:
        - Fold 1: Train 2021, Eval 2022
        - Fold 2: Train 2021-2022, Eval 2023
        - Fold 3: Train 2021-2023, Eval 2024
        """
        ts = pd.to_datetime(df[timestamp_col], utc=True)
        years = ts.dt.year.unique()
        years = np.sort(years)

        if len(years) < self.n_splits + 1:
            raise ValueError(
                f"Dataset contains {len(years)} distinct years ({years}), "
                f"which is insufficient for {self.n_splits} expanding folds."
            )

        folds: List[WalkForwardFold] = []
        purge_window = 1 + self.horizon + self.embargo_bars

        for fold_idx in range(self.n_splits):
            train_years = years[: fold_idx + 1]
            eval_year = years[fold_idx + 1]

            train_mask = ts.dt.year.isin(train_years)
            eval_mask = ts.dt.year == eval_year

            train_idxs = np.where(train_mask)[0]
            eval_idxs = np.where(eval_mask)[0]

            # Purge the last (1 + H + embargo) bars of the training segment
            if len(train_idxs) > purge_window:
                boundary_purged = train_idxs[-purge_window:]
                clean_train_idxs = train_idxs[:-purge_window]
            else:
                boundary_purged = np.array([], dtype=int)
                clean_train_idxs = train_idxs

            train_start = ts.iloc[clean_train_idxs[0]]
            train_end = ts.iloc[clean_train_idxs[-1]]
            eval_start = ts.iloc[eval_idxs[0]]
            eval_end = ts.iloc[eval_idxs[-1]]

            fold = WalkForwardFold(
                fold_id=fold_idx + 1,
                train_start_time=train_start,
                train_end_time=train_end,
                eval_start_time=eval_start,
                eval_end_time=eval_end,
                train_indices=clean_train_idxs,
                eval_indices=eval_idxs,
                purged_boundary_indices=boundary_purged,
                n_train=len(clean_train_idxs),
                n_eval=len(eval_idxs),
                n_purged_boundary=len(boundary_purged),
            )
            folds.append(fold)

        return folds
