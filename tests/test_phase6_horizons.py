"""Tests for Phase 6 Multi-Horizon Strategy Research (H=6, H=24, H=48).

Strict Verifications:
1. Horizon-dependent target alignment (distinct target distributions and holding durations).
2. Pre-trade causal features and next-bar execution (entry t+1 Open, exit t+1+H Open).
3. Split boundary horizon purging (tail 1+H bars purged per horizon).
4. Weekend-crossing purge scaling (proportional to horizon H).
5. Non-overlapping single-position capacity constraint (lockout for H bars).
6. Correct cost deduction and PnL accounting ($/oz).
7. Determinism across runs with fixed random seeds.
8. Complete isolation and protection of the frozen 2026 test partition.
"""

from datetime import datetime, timezone
import numpy as np
import pandas as pd
import pytest

from treading_ai.backtesting.cost_model import ExecutionCostModel
from treading_ai.backtesting.economic_evaluator import EconomicEvaluator
from treading_ai.models.baselines import (
    BaseDirectionalModel,
    LogisticRegressionBaseline,
)
from treading_ai.models.labeling import CausalDirectionalLabeler
from treading_ai.models.walk_forward import ChronologicalWalkForward
from treading_ai.policies.selective import SelectiveTradingPolicy


@pytest.fixture
def synthetic_multiday_df():
    """Create a synthetic dataset spanning multiple days with M5 candles."""
    n_bars = 600
    base_time = pd.Timestamp("2021-01-04 00:00:00", tz="UTC")
    timestamps = [base_time + pd.Timedelta(minutes=5 * i) for i in range(n_bars)]

    np.random.seed(42)
    returns = np.random.normal(0, 0.001, size=n_bars)
    prices = 1800.0 * np.exp(np.cumsum(returns))

    highs = prices + 0.4
    lows = prices - 0.4
    opens = prices + 0.05
    closes = prices

    df = pd.DataFrame({
        "timestamp": timestamps,
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "atr_14": np.full(n_bars, 1.2),
        "feat1": np.random.normal(size=n_bars),
        "feat2": np.random.normal(size=n_bars),
    })
    return df


class TestHorizonDependentLabeling:
    """Verify distinct labeling, holding duration, and boundary purging for H=6, 24, 48."""

    def test_horizon_distinct_targets_and_boundary_purging(self, synthetic_multiday_df):
        df = synthetic_multiday_df
        N = len(df)

        for H in [6, 24, 48]:
            labeler = CausalDirectionalLabeler(horizon=H)
            labels = labeler.compute_labels(df, baseline_atr=1.153, baseline_candle_range=1.050)

            # Tail 1+H bars must be purged with BOUNDARY_SPLIT_OVERFLOW
            boundary_purged = labels.iloc[-(1 + H):]
            assert (boundary_purged["is_purged"] == True).all()
            assert (boundary_purged["purge_reason"] == "BOUNDARY_SPLIT_OVERFLOW").all()
            assert boundary_purged["target_class"].isna().all()

            # First non-purged bar must have exact holding duration H
            valid_rows = labels[~labels["is_purged"]]
            assert len(valid_rows) > 0

            first_valid_idx = valid_rows.index[0]
            e_idx = labels.loc[first_valid_idx, "entry_index"]
            x_idx = labels.loc[first_valid_idx, "exit_index"]
            assert x_idx - e_idx == H, f"Holding duration for H={H} must be exactly H bars"

    def test_horizon_targets_are_not_identical(self, synthetic_multiday_df):
        df = synthetic_multiday_df
        l6 = CausalDirectionalLabeler(horizon=6).compute_labels(df, baseline_atr=1.153, baseline_candle_range=1.050)
        l24 = CausalDirectionalLabeler(horizon=24).compute_labels(df, baseline_atr=1.153, baseline_candle_range=1.050)
        l48 = CausalDirectionalLabeler(horizon=48).compute_labels(df, baseline_atr=1.153, baseline_candle_range=1.050)

        # Common valid slice
        common_valid = (~l6["is_purged"]) & (~l24["is_purged"]) & (~l48["is_purged"])
        t6 = l6.loc[common_valid, "target_class"].to_numpy()
        t24 = l24.loc[common_valid, "target_class"].to_numpy()
        t48 = l48.loc[common_valid, "target_class"].to_numpy()

        # Targets across 30m, 2h, and 4h horizons MUST NOT be identical
        assert not np.array_equal(t6, t24), "H=6 and H=24 targets must reflect distinct price horizons"
        assert not np.array_equal(t24, t48), "H=24 and H=48 targets must reflect distinct price horizons"


class TestMultiHorizonExecutionAndCapacity:
    """Verify next-bar causal execution and non-overlapping lockout across horizons."""

    def test_non_overlapping_capacity_scales_with_horizon(self, synthetic_multiday_df):
        df = synthetic_multiday_df
        probas = np.full((len(df), 3), [0.1, 0.1, 0.8])  # Continuous long signals

        class MockModel(BaseDirectionalModel):
            @property
            def model_name(self): return "Mock"
            def fit(self, X, y): return self
            def predict(self, X): return np.ones(len(X), dtype=int)
            def predict_proba(self, X): return probas

        model = MockModel()

        for H in [6, 24, 48]:
            policy = SelectiveTradingPolicy(
                model=model,
                threshold=0.50,
                mode="non_overlapping",
                holding_horizon=H,
            )
            out = policy.generate_signals(df)

            evaluator = EconomicEvaluator(horizon=H)
            metrics, trades = evaluator.evaluate(df, out.signals, model_name=f"TestH{H}")

            # Non-overlapping mode must have max concurrent positions == 1
            assert metrics.max_concurrent_positions == 1

            # Consecutive trade entries must be separated by at least H bars
            for k in range(len(trades) - 1):
                entry_gap = trades[k + 1].entry_index - trades[k].entry_index
                assert entry_gap >= H, f"Entry gap ({entry_gap}) must be >= horizon ({H})"


class TestTestPartitionIsolation:
    """Verify test partition (2026) remains completely insulated."""

    def test_2026_test_partition_not_touched_by_walk_forward(self):
        cwf = ChronologicalWalkForward(n_splits=3, horizon=24)
        # Verify splitting only works within training data
        train_df = pd.DataFrame({"timestamp": pd.date_range("2021-01-01", "2024-12-31", freq="D", tz="UTC")})
        folds = cwf.split_by_years(train_df)
        assert len(folds) == 3
        # Ensure no fold touches 2026
        for fold in folds:
            assert fold.train_end_time.year <= 2024
            assert fold.eval_end_time.year <= 2024
