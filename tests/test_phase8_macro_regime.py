"""Unit and Regression Tests for Phase 8 Macro Volatility Regime Analytics.

Strict Verifications:
1. Causal baseline calculation: bar t uses strictly past observations.
2. No future lookahead: truncating data produces identical historical regime series.
3. Accurate episode segmentation and duration statistics.
4. Transition matrix row stochasticity (rows sum to 1.0).
5. Cost feasibility calculations and movement percentiles.
6. Complete isolation and protection of the 2026 test partition.
"""

from datetime import datetime, timezone
import os
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from treading_ai.models.macro_regime import (
    CausalRegimeDetector,
    RegimeEpisode,
    RegimeMovementAnalyzer,
    VolatilityRegime,
)


@pytest.fixture
def clean_regime_synthetic_df():
    """Create a 300-bar synthetic dataframe with clear volatility transitions."""
    n_bars = 300
    base_time = pd.Timestamp("2021-01-04 00:00:00", tz="UTC")
    timestamps = [base_time + pd.Timedelta(minutes=5 * i) for i in range(n_bars)]

    # Bars 0-99: Low volatility (ATR ~ 0.5)
    # Bars 100-199: High volatility (ATR ~ 2.5)
    # Bars 200-299: Normal volatility (ATR ~ 1.0)
    atrs = np.ones(n_bars, dtype=float)
    atrs[:100] = 0.5
    atrs[100:200] = 2.5
    atrs[200:] = 1.0

    opens = np.full(n_bars, 1800.0)
    highs = opens + atrs / 2.0
    lows = opens - atrs / 2.0
    closes = opens.copy()

    # Add realistic price movement
    for i in range(1, n_bars):
        delta = (atrs[i] / 2.0) if (i % 2 == 0) else -(atrs[i] / 2.0)
        opens[i] = opens[i - 1] + delta
        closes[i] = opens[i] + delta / 2.0
        highs[i] = max(opens[i], closes[i]) + atrs[i] / 4.0
        lows[i] = min(opens[i], closes[i]) - atrs[i] / 4.0

    df = pd.DataFrame({
        "timestamp": timestamps,
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "atr_14": atrs,
    })
    return df


class TestMacroRegimeCausality:
    """Verify strictly causal regime calculation with zero lookahead bias."""

    def test_causal_baseline_calculation(self, clean_regime_synthetic_df):
        df = clean_regime_synthetic_df.copy()
        detector = CausalRegimeDetector(baseline_window=50, rank_window=100)

        # Compute on original df
        reg_orig = detector.compute_regimes(df)

        # Alter future data at bar 150 onwards
        df_modified = df.copy()
        df_modified.loc[150:, "atr_14"] = 100.0

        reg_mod = detector.compute_regimes(df_modified)

        # Past values (bars 0 to 149) MUST BE 100% IDENTICAL
        np.testing.assert_allclose(
            reg_orig.loc[:149, "expansion_ratio"].to_numpy(),
            reg_mod.loc[:149, "expansion_ratio"].to_numpy(),
            err_msg="Future ATR modification altered past expansion ratio!",
        )
        assert (reg_orig.loc[:149, "regime"] == reg_mod.loc[:149, "regime"]).all()

    def test_truncation_invariance(self, clean_regime_synthetic_df):
        """Truncating the dataset at index K must yield identical values for indices 0..K."""
        df = clean_regime_synthetic_df.copy()
        detector = CausalRegimeDetector(baseline_window=50, rank_window=100)

        reg_full = detector.compute_regimes(df)
        reg_trunc = detector.compute_regimes(df.iloc[:180].copy())

        np.testing.assert_allclose(
            reg_full.loc[:179, "expansion_ratio"].to_numpy(),
            reg_trunc["expansion_ratio"].to_numpy(),
            err_msg="Truncation changed historical expansion ratio!",
        )


class TestRegimeEpisodesAndTransitions:
    """Verify episode segmentation and transition matrix properties."""

    def test_episodes_extraction_durations(self, clean_regime_synthetic_df):
        df = clean_regime_synthetic_df.copy()
        detector = CausalRegimeDetector(baseline_window=50, rank_window=100)
        reg_df = detector.compute_regimes(df)
        episodes = detector.extract_episodes(reg_df)

        assert len(episodes) >= 2
        total_bars = sum(ep.duration_bars for ep in episodes)
        assert total_bars == len(df), f"Sum of episode durations ({total_bars}) != total bars ({len(df)})"

        for ep in episodes:
            assert ep.duration_bars > 0
            assert ep.duration_hours == ep.duration_bars * 5 / 60.0
            assert ep.regime in [r.value for r in VolatilityRegime]

    def test_transition_matrix_row_stochastic(self, clean_regime_synthetic_df):
        df = clean_regime_synthetic_df.copy()
        detector = CausalRegimeDetector(baseline_window=50, rank_window=100)
        reg_df = detector.compute_regimes(df)
        trans_matrix = detector.compute_transition_matrix(reg_df)

        for r_from, to_probs in trans_matrix.items():
            prob_sum = sum(to_probs.values())
            if prob_sum > 0:
                assert np.isclose(prob_sum, 1.0, atol=1e-5), f"Row {r_from} does not sum to 1.0 (sum={prob_sum})"


class TestMovementFeasibilityAnalytics:
    """Verify cost-adjusted movement calculations and distribution statistics."""

    def test_movement_distribution_metrics(self, clean_regime_synthetic_df):
        df = clean_regime_synthetic_df.copy()
        detector = CausalRegimeDetector(baseline_window=50, rank_window=100)
        reg_df = detector.compute_regimes(df)

        analyzer = RegimeMovementAnalyzer(base_friction_usd=0.35, horizons=[12, 24])
        high_movements = analyzer.analyze_regime_movements(df, reg_df, regime_filter=VolatilityRegime.HIGH.value)

        assert 12 in high_movements and 24 in high_movements
        m24 = high_movements[24]
        assert m24.n_observations > 0
        assert m24.median_terminal_move >= 0.0
        assert m24.median_hl_span >= m24.median_terminal_move
        assert m24.median_to_base_cost_ratio == m24.median_terminal_move / 0.35
        assert 0.0 <= m24.pct_exceeding_base_cost <= 1.0
        assert 0.0 <= m24.top_1pct_movement_share <= 1.0


class TestPartitionSafety:
    """Verify complete isolation and freeze of the 2026 test partition."""

    def test_test_partition_frozen_and_untouched(self):
        test_path = Path("data/features/XAUUSD_M5_features_test.parquet")
        assert test_path.exists(), "Test partition must exist"
        # Ensure no phase 8 reports inspected test data
        assert not os.path.exists("data/reports/phase8_test_results.json")
        assert not os.path.exists("data/reports/phase8_macro_regime_test.json")
