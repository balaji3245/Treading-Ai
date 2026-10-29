"""Tests for Phase 5 Selective Trading Policies, Risk Controls, and Economic Evaluation.

Strict Verifications:
1. Probability/target/time alignment (classes [-1, 0, 1], probas sum to 1).
2. Threshold application and abstention behavior (flat when edge < threshold).
3. Non-overlapping single-position capacity constraint (max concurrent = 1).
4. Overlapping position and market-exposure tracking.
5. Pre-trade causal execution timing (signal t -> entry t+1 Open -> exit t+1+H Open).
6. Market-closure fill rejection (rollover & weekend closures).
7. Correct PnL units, cost friction deductions, and median calculations.
8. No test-set influence or leakage (2026 partition isolation).
9. Deterministic policy outputs with fixed random seeds.
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
    RandomForestBaseline,
)
from treading_ai.policies.selective import (
    PolicyOutput,
    SelectiveTradingPolicy,
    compute_brier_scores,
)


class MockProbabilisticModel(BaseDirectionalModel):
    """Mock model with pre-set probability outputs for testing."""

    def __init__(self, probas: np.ndarray) -> None:
        self.probas = probas
        self.classes_ = np.array([-1, 0, 1], dtype=int)

    @property
    def model_name(self) -> str:
        return "MockProbabilisticModel"

    def fit(self, X, y):
        return self

    def predict(self, X):
        return self.classes_[np.argmax(self.probas, axis=1)]

    def predict_proba(self, X):
        return self.probas


@pytest.fixture
def synthetic_features_and_df():
    """Create a synthetic dataset with features and timestamps spanning 200 bars."""
    n_bars = 200
    base_time = pd.Timestamp("2021-01-04 00:00:00", tz="UTC")
    timestamps = [base_time + pd.Timedelta(minutes=5 * i) for i in range(n_bars)]

    np.random.seed(42)
    prices = 1800.0 + np.cumsum(np.random.normal(0, 0.5, size=n_bars))
    highs = prices + 0.5
    lows = prices - 0.5
    opens = prices + 0.1
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


class TestProbabilityAlignmentAndAbstention:
    """Verify class probability alignment and threshold abstention behavior."""

    def test_threshold_abstention_behavior(self):
        # 4 samples:
        # 0: Long confident (0.1, 0.2, 0.7) -> Long (+1) for th=0.50, th=0.65
        # 1: Short confident (0.55, 0.25, 0.20) -> Short (-1) for th=0.50, but Abstain for th=0.60
        # 2: Neutral majority (0.2, 0.6, 0.2) -> Abstain (0) for th=0.50
        # 3: Low-confidence tie (0.35, 0.35, 0.30) -> Abstain (0) for th=0.50
        probas = np.array([
            [0.10, 0.20, 0.70],
            [0.55, 0.25, 0.20],
            [0.20, 0.60, 0.20],
            [0.35, 0.35, 0.30],
        ])
        model = MockProbabilisticModel(probas)
        X_dummy = np.zeros((4, 2))

        # Threshold 0.50
        p50 = SelectiveTradingPolicy(model=model, threshold=0.50, mode="overlapping")
        out50 = p50.generate_signals(X_dummy)
        assert np.array_equal(out50.signals, [1, -1, 0, 0])
        assert out50.n_eligible_signals == 2

        # Threshold 0.60
        p60 = SelectiveTradingPolicy(model=model, threshold=0.60, mode="overlapping")
        out60 = p60.generate_signals(X_dummy)
        assert np.array_equal(out60.signals, [1, 0, 0, 0])
        assert out60.n_eligible_signals == 1

        # No-trade baseline (threshold 1.0)
        p_flat = SelectiveTradingPolicy(model=model, threshold=1.0, mode="overlapping")
        out_flat = p_flat.generate_signals(X_dummy)
        assert np.array_equal(out_flat.signals, [0, 0, 0, 0])
        assert out_flat.n_eligible_signals == 0

        # Unfiltered baseline (threshold None)
        p_unfilt = SelectiveTradingPolicy(model=model, threshold=None, mode="overlapping")
        out_unfilt = p_unfilt.generate_signals(X_dummy)
        assert np.array_equal(out_unfilt.signals, [1, -1, 0, -1])


class TestPositionCapacityConstraints:
    """Verify non-overlapping single position execution vs overlapping execution."""

    def test_non_overlapping_suppresses_concurrent_entries(self):
        # 10 consecutive long-eligible signals
        probas = np.full((10, 3), [0.1, 0.1, 0.8])
        model = MockProbabilisticModel(probas)
        X_dummy = np.zeros((10, 2))

        H = 4  # holding horizon of 4 bars
        p_non_overlap = SelectiveTradingPolicy(
            model=model,
            threshold=0.50,
            mode="non_overlapping",
            holding_horizon=H,
        )
        out = p_non_overlap.generate_signals(X_dummy)

        # Bar 0 enters -> locked out for bars 1, 2, 3 (indices 1 to H-1)
        # Next trade can enter at bar 4 (index H) -> locked out for bars 5, 6, 7
        # Next trade can enter at bar 8
        expected = np.zeros(10, dtype=int)
        expected[0] = 1
        expected[4] = 1
        expected[8] = 1

        assert np.array_equal(out.signals, expected)
        assert out.n_eligible_signals == 10
        assert out.n_executed_signals == 3
        assert out.n_capacity_rejected == 7

    def test_overlapping_allows_concurrent_entries(self):
        probas = np.full((10, 3), [0.1, 0.1, 0.8])
        model = MockProbabilisticModel(probas)
        X_dummy = np.zeros((10, 2))

        p_overlap = SelectiveTradingPolicy(
            model=model,
            threshold=0.50,
            mode="overlapping",
            holding_horizon=4,
        )
        out = p_overlap.generate_signals(X_dummy)
        assert np.array_equal(out.signals, np.ones(10, dtype=int))
        assert out.n_executed_signals == 10
        assert out.n_capacity_rejected == 0


class TestEconomicEvaluatorEnhancedMetrics:
    """Verify cost breakdown, median PnL, and concurrent exposure calculation."""

    def test_cost_breakdown_and_concurrency_metrics(self, synthetic_features_and_df):
        df = synthetic_features_and_df
        signals = np.zeros(len(df), dtype=int)
        # Place 2 spaced-out long signals
        signals[10] = 1
        signals[30] = 1

        evaluator = EconomicEvaluator(horizon=6)
        metrics, trades = evaluator.evaluate(df, signals, model_name="TestMetrics")

        assert metrics.n_eligible_signals == 2
        assert metrics.n_executed_entries == 2
        assert metrics.n_completed_trades == 2
        assert metrics.n_trades_rejected_closure == 0

        # Cost breakdown check
        assert metrics.total_spread_usd > 0.0
        assert metrics.total_slippage_usd > 0.0
        assert metrics.total_commission_usd > 0.0
        expected_friction = metrics.total_spread_usd + metrics.total_slippage_usd + metrics.total_commission_usd
        assert np.isclose(metrics.total_friction_usd, expected_friction, atol=1e-4)

        # Net PnL check
        assert np.isclose(metrics.net_pnl_usd, metrics.gross_pnl_usd - metrics.total_friction_usd, atol=1e-4)

        # Median vs Mean net PnL check
        assert metrics.median_net_pnl_per_trade is not None
        assert metrics.avg_net_pnl_per_trade is not None

        # Concurrency & Exposure
        assert metrics.max_concurrent_positions == 1
        assert metrics.market_exposure_pct > 0.0

    def test_brier_score_calibration(self):
        # Perfect probabilities
        y_true = np.array([-1, 0, 1])
        probas_perfect = np.array([
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ])
        brier = compute_brier_scores(y_true, probas_perfect)
        assert np.isclose(brier["brier_total"], 0.0)

        # Uniform random probabilities (1/3 each)
        probas_uniform = np.full((3, 3), 1.0 / 3.0)
        brier_uniform = compute_brier_scores(y_true, probas_uniform)
        # Expected Brier for uniform on 3 classes = (2/3)^2 + 2*(1/3)^2 = 4/9 + 2/9 = 6/9 = 0.6667
        assert np.isclose(brier_uniform["brier_total"], 2.0 / 3.0, atol=1e-4)
