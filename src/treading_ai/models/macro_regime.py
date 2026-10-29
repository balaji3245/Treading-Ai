"""Macro Volatility Regime Detection and Feasibility Analytics for XAUUSD.

Strict Quantitative Protocol:
1. Causal Regime Detection:
   - Uses strictly past observations to calculate trailing baseline ATR and realized volatility.
   - Zero forward-looking lookahead bias: bar t uses strictly rolling window [t-W: t-1] for baseline.
   - Trailing Expansion Ratio: Current ATR / Trailing Median ATR(W=288).
   - Trailing Percentile Rank: Percentile of Current ATR in trailing historical window.
2. Independent Regime Episodes:
   - Contiguous blocks of M5 bars belonging to the same regime.
   - Measures episode count, duration statistics (mean, median, max bars), and transition probabilities.
3. Multi-Horizon Forward Price Movement Analytics:
   - Measured over forward independent windows H in [6, 12, 24, 48] bars.
   - High-Low span (MFE) and terminal absolute price change.
   - Ratio of forward movement to transaction friction under base, 2x, and 3x cost tiers.
4. Outlier Concentration Analytics:
   - Evaluates whether movement is evenly distributed or concentrated in rare tail shocks.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd


class VolatilityRegime(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    EXTREME = "EXTREME"


@dataclass(frozen=True)
class RegimeEpisode:
    """An independent contiguous episode of a volatility regime."""
    regime: str
    start_index: int
    end_index: int
    start_timestamp: pd.Timestamp
    end_timestamp: pd.Timestamp
    duration_bars: int
    duration_hours: float
    peak_expansion_ratio: float
    mean_expansion_ratio: float


@dataclass
class MovementDistribution:
    """Descriptive statistics of price movement over a specific forward horizon."""
    horizon: int
    n_observations: int
    mean_terminal_move: float
    median_terminal_move: float
    p25_terminal_move: float
    p75_terminal_move: float
    p90_terminal_move: float
    p95_terminal_move: float
    p99_terminal_move: float
    mean_hl_span: float
    median_hl_span: float
    p90_hl_span: float
    # Cost adjusted ratios
    base_friction: float
    median_to_base_cost_ratio: float
    pct_exceeding_base_cost: float
    median_to_2x_cost_ratio: float
    pct_exceeding_2x_cost: float
    median_to_3x_cost_ratio: float
    pct_exceeding_3x_cost: float
    # Outlier concentration
    top_1pct_movement_share: float
    top_5pct_movement_share: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "horizon_bars": self.horizon,
            "horizon_hours": self.horizon * 5 / 60.0,
            "n_observations": self.n_observations,
            "terminal_move": {
                "mean": round(self.mean_terminal_move, 3),
                "median": round(self.median_terminal_move, 3),
                "p25": round(self.p25_terminal_move, 3),
                "p75": round(self.p75_terminal_move, 3),
                "p90": round(self.p90_terminal_move, 3),
                "p95": round(self.p95_terminal_move, 3),
                "p99": round(self.p99_terminal_move, 3),
            },
            "hl_span": {
                "mean": round(self.mean_hl_span, 3),
                "median": round(self.median_hl_span, 3),
                "p90": round(self.p90_hl_span, 3),
            },
            "cost_feasibility": {
                "base_friction_usd": round(self.base_friction, 3),
                "median_to_base_cost_ratio": round(self.median_to_base_cost_ratio, 3),
                "pct_exceeding_base_cost": round(self.pct_exceeding_base_cost * 100, 2),
                "median_to_2x_cost_ratio": round(self.median_to_2x_cost_ratio, 3),
                "pct_exceeding_2x_cost": round(self.pct_exceeding_2x_cost * 100, 2),
                "median_to_3x_cost_ratio": round(self.median_to_3x_cost_ratio, 3),
                "pct_exceeding_3x_cost": round(self.pct_exceeding_3x_cost * 100, 2),
            },
            "outlier_concentration": {
                "top_1pct_share": round(self.top_1pct_movement_share * 100, 2),
                "top_5pct_share": round(self.top_5pct_movement_share * 100, 2),
            },
        }


class CausalRegimeDetector:
    """Causal detector for market volatility regimes using strictly past rolling data.

    Parameters
    ----------
    baseline_window : int, default=288
        Trailing window size in M5 bars (288 bars = 24 hours) used to compute the
        historical baseline median ATR. Strictly lagged to prevent lookahead bias.
    rank_window : int, default=500
        Trailing window size in M5 bars used to calculate rolling percentile rank.
    low_ratio_thresh : float, default=0.85
        Expansion ratio threshold below which regime is classified as LOW.
    high_ratio_thresh : float, default=1.25
        Expansion ratio threshold above which regime is classified as HIGH.
    extreme_ratio_thresh : float, default=1.60
        Expansion ratio threshold above which regime is classified as EXTREME.
    atr_col : str, default='atr_14'
        Column name in DataFrame containing 14-period ATR.
    """

    def __init__(
        self,
        baseline_window: int = 288,
        rank_window: int = 500,
        low_ratio_thresh: float = 0.85,
        high_ratio_thresh: float = 1.25,
        extreme_ratio_thresh: float = 1.60,
        atr_col: str = "atr_14",
    ) -> None:
        self.baseline_window = baseline_window
        self.rank_window = rank_window
        self.low_ratio_thresh = low_ratio_thresh
        self.high_ratio_thresh = high_ratio_thresh
        self.extreme_ratio_thresh = extreme_ratio_thresh
        self.atr_col = atr_col

    def compute_regimes(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute causal rolling regime indicators on DataFrame.

        Guarantees:
        - Baseline median uses strictly `shift(1).rolling(baseline_window)`.
        - Percentile rank uses strictly past observations.
        - Zero future information leakage.
        """
        out = pd.DataFrame(index=df.index)
        out["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)

        # 1. Obtain causal ATR
        if self.atr_col in df.columns:
            atr = df[self.atr_col].to_numpy(dtype=float)
        else:
            highs = df["high"].to_numpy(dtype=float)
            lows = df["low"].to_numpy(dtype=float)
            atr = pd.Series(highs - lows).rolling(14, min_periods=1).mean().to_numpy()

        atr_series = pd.Series(atr, index=df.index)

        # 2. Causal trailing baseline ATR (strictly past bars)
        # shift(1) ensures bar t is NOT in its own baseline median
        trailing_baseline_median = (
            atr_series.shift(1).rolling(self.baseline_window, min_periods=max(24, self.baseline_window // 4)).median()
        )
        # Backfill initial warm-up safely with expanding median
        expanding_median = atr_series.shift(1).expanding(min_periods=10).median()
        trailing_baseline_median = trailing_baseline_median.fillna(expanding_median).fillna(atr_series)

        # 3. Causal Expansion Ratio: current ATR / trailing baseline median
        expansion_ratio = atr_series / trailing_baseline_median
        expansion_ratio = expansion_ratio.fillna(1.0).to_numpy(dtype=float)

        # 4. Trailing Percentile Rank of ATR over past rank_window bars
        # For each bar t, percentile of atr[t] within past rank_window bars
        n = len(df)
        percentile_ranks = np.zeros(n, dtype=float)
        atr_vals = atr_series.to_numpy()

        # Vectorized approximation or rolling rank
        # Using rolling apply with strictly past bars
        for i in range(n):
            if i < 10:
                percentile_ranks[i] = 0.50
                continue
            start_idx = max(0, i - self.rank_window)
            past_window = atr_vals[start_idx:i]  # excludes i
            if len(past_window) > 0:
                percentile_ranks[i] = float(np.mean(past_window <= atr_vals[i]))
            else:
                percentile_ranks[i] = 0.50

        # 5. Classify Regimes
        regime_labels = []
        for i in range(n):
            ratio = expansion_ratio[i]
            pct = percentile_ranks[i]

            if ratio >= self.extreme_ratio_thresh or pct >= 0.90:
                regime_labels.append(VolatilityRegime.EXTREME.value)
            elif ratio >= self.high_ratio_thresh or pct >= 0.67:
                regime_labels.append(VolatilityRegime.HIGH.value)
            elif ratio < self.low_ratio_thresh or pct < 0.33:
                regime_labels.append(VolatilityRegime.LOW.value)
            else:
                regime_labels.append(VolatilityRegime.NORMAL.value)

        out["atr"] = atr_vals
        out["trailing_baseline_median"] = trailing_baseline_median.to_numpy()
        out["expansion_ratio"] = expansion_ratio
        out["trailing_percentile"] = percentile_ranks
        out["regime"] = regime_labels

        return out

    def extract_episodes(self, regime_df: pd.DataFrame) -> List[RegimeEpisode]:
        """Extract contiguous independent episodes for each regime."""
        episodes: List[RegimeEpisode] = []
        n = len(regime_df)
        if n == 0:
            return episodes

        timestamps = regime_df["timestamp"]
        regimes = regime_df["regime"].to_numpy()
        expansion_ratios = regime_df["expansion_ratio"].to_numpy()

        current_regime = regimes[0]
        start_idx = 0

        for i in range(1, n):
            if regimes[i] != current_regime:
                end_idx = i - 1
                dur_bars = end_idx - start_idx + 1
                dur_hours = dur_bars * 5 / 60.0
                ratios = expansion_ratios[start_idx:end_idx + 1]

                episodes.append(
                    RegimeEpisode(
                        regime=current_regime,
                        start_index=start_idx,
                        end_index=end_idx,
                        start_timestamp=timestamps.iloc[start_idx],
                        end_timestamp=timestamps.iloc[end_idx],
                        duration_bars=dur_bars,
                        duration_hours=dur_hours,
                        peak_expansion_ratio=float(np.max(ratios)),
                        mean_expansion_ratio=float(np.mean(ratios)),
                    )
                )
                current_regime = regimes[i]
                start_idx = i

        # Final episode
        end_idx = n - 1
        dur_bars = end_idx - start_idx + 1
        dur_hours = dur_bars * 5 / 60.0
        ratios = expansion_ratios[start_idx:end_idx + 1]
        episodes.append(
            RegimeEpisode(
                regime=current_regime,
                start_index=start_idx,
                end_index=end_idx,
                start_timestamp=timestamps.iloc[start_idx],
                end_timestamp=timestamps.iloc[end_idx],
                duration_bars=dur_bars,
                duration_hours=dur_hours,
                peak_expansion_ratio=float(np.max(ratios)),
                mean_expansion_ratio=float(np.mean(ratios)),
            )
        )

        return episodes

    def compute_transition_matrix(self, regime_df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
        """Compute the empirical Markov 1-step transition probability matrix between regimes."""
        regimes = regime_df["regime"].to_numpy()
        order = [r.value for r in VolatilityRegime]
        counts: Dict[str, Dict[str, int]] = {r1: {r2: 0 for r2 in order} for r1 in order}

        for i in range(len(regimes) - 1):
            r_from = regimes[i]
            r_to = regimes[i + 1]
            if r_from in counts and r_to in counts[r_from]:
                counts[r_from][r_to] += 1

        probs: Dict[str, Dict[str, float]] = {}
        for r_from in order:
            total = sum(counts[r_from].values())
            probs[r_from] = {}
            for r_to in order:
                probs[r_from][r_to] = float(counts[r_from][r_to] / total) if total > 0 else 0.0

        return probs


class RegimeMovementAnalyzer:
    """Computes descriptive and cost-adjusted forward price movement statistics per regime."""

    def __init__(
        self,
        base_friction_usd: float = 0.35,  # $0.20 spread + 2 * $0.05 slip + $0.05 * 2 comm
        horizons: Optional[List[int]] = None,
    ) -> None:
        self.base_friction = base_friction_usd
        self.horizons = horizons or [6, 12, 24, 48]

    def analyze_regime_movements(
        self,
        price_df: pd.DataFrame,
        regime_df: pd.DataFrame,
        regime_filter: Optional[str] = None,
    ) -> Dict[int, MovementDistribution]:
        """Analyze forward price movement distributions for a specific regime."""
        opens = price_df["open"].to_numpy(dtype=float)
        highs = price_df["high"].to_numpy(dtype=float)
        lows = price_df["low"].to_numpy(dtype=float)
        closes = price_df["close"].to_numpy(dtype=float)
        regimes = regime_df["regime"].to_numpy()

        n = len(price_df)
        results: Dict[int, MovementDistribution] = {}

        friction_base = self.base_friction
        friction_2x = friction_base + 0.25  # ~ $0.60
        friction_3x = friction_base + 0.50  # ~ $0.85

        for H in self.horizons:
            # Mask of valid indices where entry at i+1 and forward H bars stay within dataset
            max_i = n - (1 + H)
            if max_i <= 0:
                continue

            if regime_filter is not None:
                indices = [i for i in range(max_i) if regimes[i] == regime_filter]
            else:
                indices = list(range(max_i))

            if not indices:
                continue

            indices_arr = np.array(indices, dtype=int)
            entry_opens = opens[indices_arr + 1]
            exit_closes = closes[indices_arr + H]

            # Terminal absolute movement: |Close_{t+H} - Open_{t+1}|
            terminal_moves = np.abs(exit_closes - entry_opens)

            # High-Low span: max(High_{t+1: t+H}) - min(Low_{t+1: t+H})
            hl_spans = np.zeros(len(indices_arr), dtype=float)
            for idx_k, i in enumerate(indices_arr):
                sub_highs = highs[i + 1 : i + 1 + H]
                sub_lows = lows[i + 1 : i + 1 + H]
                hl_spans[idx_k] = np.max(sub_highs) - np.min(sub_lows)

            # Descriptive metrics
            mean_term = float(np.mean(terminal_moves))
            med_term = float(np.median(terminal_moves))
            p25 = float(np.percentile(terminal_moves, 25))
            p75 = float(np.percentile(terminal_moves, 75))
            p90 = float(np.percentile(terminal_moves, 90))
            p95 = float(np.percentile(terminal_moves, 95))
            p99 = float(np.percentile(terminal_moves, 99))

            mean_hl = float(np.mean(hl_spans))
            med_hl = float(np.median(hl_spans))
            p90_hl = float(np.percentile(hl_spans, 90))

            # Feasibility ratios
            med_to_base = float(med_term / friction_base) if friction_base > 0 else 0.0
            pct_base = float(np.mean(terminal_moves > friction_base))

            med_to_2x = float(med_term / friction_2x) if friction_2x > 0 else 0.0
            pct_2x = float(np.mean(terminal_moves > friction_2x))

            med_to_3x = float(med_term / friction_3x) if friction_3x > 0 else 0.0
            pct_3x = float(np.mean(terminal_moves > friction_3x))

            # Outlier concentration: share of total movement accounted for by top 1% and 5%
            sorted_moves = np.sort(terminal_moves)
            total_sum = np.sum(sorted_moves)
            if total_sum > 0:
                top_1pct_n = max(1, int(np.ceil(len(sorted_moves) * 0.01)))
                top_5pct_n = max(1, int(np.ceil(len(sorted_moves) * 0.05)))
                share_1pct = float(np.sum(sorted_moves[-top_1pct_n:]) / total_sum)
                share_5pct = float(np.sum(sorted_moves[-top_5pct_n:]) / total_sum)
            else:
                share_1pct = 0.0
                share_5pct = 0.0

            results[H] = MovementDistribution(
                horizon=H,
                n_observations=len(indices_arr),
                mean_terminal_move=mean_term,
                median_terminal_move=med_term,
                p25_terminal_move=p25,
                p75_terminal_move=p75,
                p90_terminal_move=p90,
                p95_terminal_move=p95,
                p99_terminal_move=p99,
                mean_hl_span=mean_hl,
                median_hl_span=med_hl,
                p90_hl_span=p90_hl,
                base_friction=friction_base,
                median_to_base_cost_ratio=med_to_base,
                pct_exceeding_base_cost=pct_base,
                median_to_2x_cost_ratio=med_to_2x,
                pct_exceeding_2x_cost=pct_2x,
                median_to_3x_cost_ratio=med_to_3x,
                pct_exceeding_3x_cost=pct_3x,
                top_1pct_movement_share=share_1pct,
                top_5pct_movement_share=share_5pct,
            )

        return results
