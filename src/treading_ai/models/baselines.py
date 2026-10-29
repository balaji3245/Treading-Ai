"""Reproducible Baseline Models for Intraday Direction Prediction.

Implements simple, deterministic, and benchmarkable baselines for XAUUSD:
1. MajorityClassBaseline: Always predicts the most frequent training class.
2. DirectionalHeuristicBaseline: Deterministic momentum/trend rule (RSI + Momentum).
3. LogisticRegressionBaseline: Multiclass classification with training-only StandardScaler.
4. RandomForestBaseline: Controlled, reproducible tree-based baseline.

Strict Leakage & Separation Rules:
- All preprocessors (e.g. StandardScaler) are fit strictly on training data inside `fit()`.
- Predictions on validation or out-of-sample data use strictly transformed features.
- Zero future leakage or target leakage.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler


class BaseDirectionalModel(ABC):
    """Abstract base class for all directional prediction models."""

    @abstractmethod
    def fit(self, X: Union[np.ndarray, pd.DataFrame], y: Union[np.ndarray, pd.Series]) -> "BaseDirectionalModel":
        """Fit the model to training data."""
        pass

    @abstractmethod
    def predict(self, X: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        """Generate predictions {-1, 0, +1}."""
        pass

    @abstractmethod
    def predict_proba(self, X: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        """Generate class probabilities for classes [-1, 0, 1]."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Human-readable model name."""
        pass


class MajorityClassBaseline(BaseDirectionalModel):
    """Baseline predicting the most frequent class observed in the training set.

    Serves as the foundational null hypothesis benchmark against which all
    statistical and machine learning models must be compared.
    """

    def __init__(self) -> None:
        self.majority_class_: Optional[int] = None
        self.classes_: np.ndarray = np.array([-1, 0, 1], dtype=int)
        self.class_priors_: Optional[np.ndarray] = None

    @property
    def model_name(self) -> str:
        return "Majority-Class Baseline"

    def fit(self, X: Union[np.ndarray, pd.DataFrame], y: Union[np.ndarray, pd.Series]) -> "MajorityClassBaseline":
        y_arr = np.asarray(y, dtype=int)
        if len(y_arr) == 0:
            raise ValueError("Cannot fit MajorityClassBaseline on empty target array.")

        values, counts = np.unique(y_arr, return_counts=True)
        majority_idx = int(np.argmax(counts))
        self.majority_class_ = int(values[majority_idx])

        # Compute prior probabilities over [-1, 0, 1]
        priors = np.zeros(3, dtype=float)
        for i, cls in enumerate(self.classes_):
            mask = y_arr == cls
            priors[i] = np.mean(mask) if len(y_arr) > 0 else 0.0
        self.class_priors_ = priors
        return self

    def predict(self, X: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        if self.majority_class_ is None:
            raise RuntimeError("MajorityClassBaseline must be fit before predict.")
        n_samples = len(X)
        return np.full(n_samples, self.majority_class_, dtype=int)

    def predict_proba(self, X: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        if self.class_priors_ is None:
            raise RuntimeError("MajorityClassBaseline must be fit before predict_proba.")
        n_samples = len(X)
        return np.tile(self.class_priors_, (n_samples, 1))


class DirectionalHeuristicBaseline(BaseDirectionalModel):
    """Deterministic momentum and trend heuristic baseline.

    Uses a predefined, non-fitted rule combining short-term momentum and RSI:
    - Long (+1): RSI_14 > 55.0 and ret_10 > 0.0005 (+5 bps)
    - Short (-1): RSI_14 < 45.0 and ret_10 < -0.0005 (-5 bps)
    - Neutral (0): Otherwise

    If feature column names are not available (e.g. raw numpy array), uses specified
    column indices (default: col 0 for rsi_14, col 1 for ret_10).
    """

    def __init__(
        self,
        rsi_col: Union[str, int] = "rsi_14",
        momentum_col: Union[str, int] = "ret_10",
        rsi_bull_threshold: float = 55.0,
        rsi_bear_threshold: float = 45.0,
        momentum_threshold: float = 0.0005,
    ) -> None:
        self.rsi_col = rsi_col
        self.momentum_col = momentum_col
        self.rsi_bull_threshold = rsi_bull_threshold
        self.rsi_bear_threshold = rsi_bear_threshold
        self.momentum_threshold = momentum_threshold
        self.classes_: np.ndarray = np.array([-1, 0, 1], dtype=int)
        self.is_fit_: bool = False

    @property
    def model_name(self) -> str:
        return "Directional Heuristic (RSI+Momentum)"

    def fit(self, X: Union[np.ndarray, pd.DataFrame], y: Union[np.ndarray, pd.Series]) -> "DirectionalHeuristicBaseline":
        # Rule is predefined and deterministic; fit confirms interface compatibility and validates inputs
        self.is_fit_ = True
        return self

    def _extract_signals(self, X: Union[np.ndarray, pd.DataFrame]) -> tuple[np.ndarray, np.ndarray]:
        if isinstance(X, pd.DataFrame):
            if isinstance(self.rsi_col, str) and self.rsi_col in X.columns:
                rsi_vals = X[self.rsi_col].to_numpy(dtype=float)
            else:
                rsi_vals = X.iloc[:, 0].to_numpy(dtype=float)

            if isinstance(self.momentum_col, str) and self.momentum_col in X.columns:
                mom_vals = X[self.momentum_col].to_numpy(dtype=float)
            else:
                mom_vals = X.iloc[:, 1].to_numpy(dtype=float)
        else:
            X_arr = np.asarray(X, dtype=float)
            col_rsi_idx = self.rsi_col if isinstance(self.rsi_col, int) else 0
            col_mom_idx = self.momentum_col if isinstance(self.momentum_col, int) else 1
            rsi_vals = X_arr[:, col_rsi_idx]
            mom_vals = X_arr[:, col_mom_idx]

        return rsi_vals, mom_vals

    def predict(self, X: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        rsi_vals, mom_vals = self._extract_signals(X)
        n = len(rsi_vals)
        preds = np.zeros(n, dtype=int)

        long_cond = (rsi_vals > self.rsi_bull_threshold) & (mom_vals > self.momentum_threshold)
        short_cond = (rsi_vals < self.rsi_bear_threshold) & (mom_vals < -self.momentum_threshold)

        preds[long_cond] = 1
        preds[short_cond] = -1
        return preds

    def predict_proba(self, X: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        preds = self.predict(X)
        n = len(preds)
        probas = np.zeros((n, 3), dtype=float)
        for i, p in enumerate(preds):
            if p == -1:
                probas[i] = [0.8, 0.1, 0.1]
            elif p == 0:
                probas[i] = [0.2, 0.6, 0.2]
            else:
                probas[i] = [0.1, 0.1, 0.8]
        return probas


class LogisticRegressionBaseline(BaseDirectionalModel):
    """Multiclass Logistic Regression baseline with strict train-only StandardScaler.

    Parameters
    ----------
    C : float, default=1.0
        Inverse regularization strength.
    max_iter : int, default=500
        Maximum number of iterations for the solver.
    random_state : int, default=42
        Seed for reproducibility.
    class_weight : Optional[Union[dict, str]], default=None
        Weights associated with classes.
    """

    def __init__(
        self,
        C: float = 1.0,
        max_iter: int = 500,
        random_state: int = 42,
        class_weight: Optional[Union[dict, str]] = None,
        solver: str = "lbfgs",
    ) -> None:
        self.C = C
        self.max_iter = max_iter
        self.random_state = random_state
        self.class_weight = class_weight
        self.solver = solver

        self.scaler_: Optional[StandardScaler] = None
        self.model_: Optional[LogisticRegression] = None
        self.classes_: np.ndarray = np.array([-1, 0, 1], dtype=int)

    @property
    def model_name(self) -> str:
        return f"Logistic Regression (C={self.C})"

    def fit(self, X: Union[np.ndarray, pd.DataFrame], y: Union[np.ndarray, pd.Series]) -> "LogisticRegressionBaseline":
        X_arr = np.asarray(X, dtype=float)
        y_arr = np.asarray(y, dtype=int)

        # Fit scaler STRICTLY on training split
        self.scaler_ = StandardScaler()
        X_scaled = self.scaler_.fit_transform(X_arr)

        self.model_ = LogisticRegression(
            C=self.C,
            max_iter=self.max_iter,
            random_state=self.random_state,
            class_weight=self.class_weight,
            solver=self.solver,
        )
        self.model_.fit(X_scaled, y_arr)
        return self

    def predict(self, X: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        if self.scaler_ is None or self.model_ is None:
            raise RuntimeError("LogisticRegressionBaseline must be fit before predict.")
        X_arr = np.asarray(X, dtype=float)
        X_scaled = self.scaler_.transform(X_arr)
        return self.model_.predict(X_scaled).astype(int)

    def predict_proba(self, X: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        if self.scaler_ is None or self.model_ is None:
            raise RuntimeError("LogisticRegressionBaseline must be fit before predict_proba.")
        X_arr = np.asarray(X, dtype=float)
        X_scaled = self.scaler_.transform(X_arr)
        probas = self.model_.predict_proba(X_scaled)

        # Align probabilities to canonical classes [-1, 0, 1]
        model_classes = self.model_.classes_
        if np.array_equal(model_classes, self.classes_):
            return probas

        aligned = np.zeros((len(X_arr), 3), dtype=float)
        for idx, cls in enumerate(self.classes_):
            if cls in model_classes:
                model_idx = int(np.where(model_classes == cls)[0][0])
                aligned[:, idx] = probas[:, model_idx]
        return aligned


class RandomForestBaseline(BaseDirectionalModel):
    """Controlled, reproducible Random Forest baseline.

    Parameters
    ----------
    n_estimators : int, default=100
        Number of trees in the forest.
    max_depth : int, default=10
        Maximum depth of the trees.
    min_samples_leaf : int, default=50
        Minimum number of samples required at a leaf node.
    random_state : int, default=42
        Seed for reproducibility.
    n_jobs : int, default=-1
        Number of CPU workers.
    """

    def __init__(
        self,
        n_estimators: int = 100,
        max_depth: int = 10,
        min_samples_leaf: int = 50,
        random_state: int = 42,
        n_jobs: int = -1,
        class_weight: Optional[Union[dict, str]] = None,
    ) -> None:
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.min_samples_leaf = min_samples_leaf
        self.random_state = random_state
        self.n_jobs = n_jobs
        self.class_weight = class_weight

        self.model_: Optional[RandomForestClassifier] = None
        self.classes_: np.ndarray = np.array([-1, 0, 1], dtype=int)

    @property
    def model_name(self) -> str:
        return f"Random Forest (trees={self.n_estimators}, depth={self.max_depth}, leaf={self.min_samples_leaf})"

    def fit(self, X: Union[np.ndarray, pd.DataFrame], y: Union[np.ndarray, pd.Series]) -> "RandomForestBaseline":
        X_arr = np.asarray(X, dtype=float)
        y_arr = np.asarray(y, dtype=int)

        self.model_ = RandomForestClassifier(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            min_samples_leaf=self.min_samples_leaf,
            random_state=self.random_state,
            n_jobs=self.n_jobs,
            class_weight=self.class_weight,
        )
        self.model_.fit(X_arr, y_arr)
        return self

    def predict(self, X: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        if self.model_ is None:
            raise RuntimeError("RandomForestBaseline must be fit before predict.")
        X_arr = np.asarray(X, dtype=float)
        return self.model_.predict(X_arr).astype(int)

    def predict_proba(self, X: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        if self.model_ is None:
            raise RuntimeError("RandomForestBaseline must be fit before predict_proba.")
        X_arr = np.asarray(X, dtype=float)
        probas = self.model_.predict_proba(X_arr)

        model_classes = self.model_.classes_
        if np.array_equal(model_classes, self.classes_):
            return probas

        aligned = np.zeros((len(X_arr), 3), dtype=float)
        for idx, cls in enumerate(self.classes_):
            if cls in model_classes:
                model_idx = int(np.where(model_classes == cls)[0][0])
                aligned[:, idx] = probas[:, model_idx]
        return aligned
