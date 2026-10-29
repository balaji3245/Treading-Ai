"""Causal Triple-Barrier Labeling Engine for Financial Machine Learning.

Strict Execution Causality & Barrier Dynamics:
1. Decision Time (T_t): Finalized at bar t close (index i).
   Volatility metric: ATR_t finalized at or before bar t close.
2. Entry Time (T_{t+1}): Order executes at bar t+1 Open (index i+1).
   Simulated fill price includes pre-trade causal entry spread and slippage.
3. Three Barriers:
   - Upper Barrier (Profit Target): Entry Fill + pt_atr * ATR_t (for Long)
   - Lower Barrier (Stop Loss): Entry Fill - sl_atr * ATR_t (for Long)
   - Vertical Barrier (Time Limit): Maximum holding duration H_max bars.
4. Conservative Execution & Ambiguity Handling:
   - Gap handling: If a bar opens beyond the barrier, fill is assigned at the bar Open
     (conservative execution), not the ideal barrier price.
   - Ambiguous Intrabar Touch: If both stop and target are crossed within the same M5 bar,
     conservative STOP-FIRST assumption is applied.
   - Weekend Closure: Any trade crossing the weekend closure is purged.
   - Market Closures: Mon-Thu 17:00-18:00 NY rollover closure rejects entry/exit.
5. Causal Target Class:
   - +1: Profit target barrier hit before stop loss or time limit.
   - -1: Stop loss barrier hit before profit target or time limit.
   -  0: Time limit reached (neither barrier touched) or net return below threshold.
   - NaN: Purged (weekend crossing, closure rejection, or partition boundary overflow).
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd

from treading_ai.backtesting.cost_model import ExecutionCostModel

TZ_NEW_YORK = ZoneInfo("America/New_York")

PURGE_BOUNDARY_SPLIT_OVERFLOW = "BOUNDARY_SPLIT_OVERFLOW"
PURGE_WEEKEND_CROSSING = "WEEKEND_CROSSING"
PURGE_ROLLOVER_CLOSED = "ROLLOVER_CLOSED"


@dataclass(frozen=True)
class BarrierEvent:
    """Details of a barrier touch event."""
    hit_type: str  # 'TARGET', 'STOP', 'TIME_LIMIT', or 'REJECTED'
    exit_bar_index: int
    exit_timestamp: pd.Timestamp
    exit_price: float
    bars_held: int
    is_ambiguous_same_bar: bool = False
    is_gap_through: bool = False


class TripleBarrierLabeler:
    """Causal Triple-Barrier Target Labeling Engine.

    Parameters
    ----------
    pt_atr : float, default=2.0
        Profit-taking multiplier in units of ATR.
    sl_atr : float, default=1.0
        Stop-loss multiplier in units of ATR.
    max_holding_bars : int, default=24
        Maximum holding period in M5 bars (e.g. 24 bars = 2 hours).
    cost_model : Optional[ExecutionCostModel]
        Execution cost simulator for dynamic spread and slippage.
    atr_column : str, default='atr_14'
        Column name for ATR in the input DataFrame.
    conservative_stop_first : bool, default=True
        If True, applies stop-first assumption when both barriers are touched in the same bar.
    """

    def __init__(
        self,
        pt_atr: float = 2.0,
        sl_atr: float = 1.0,
        max_holding_bars: int = 24,
        cost_model: Optional[ExecutionCostModel] = None,
        atr_column: str = "atr_14",
        conservative_stop_first: bool = True,
        weekend_threshold_hours: float = 24.0,
    ) -> None:
        if pt_atr <= 0:
            raise ValueError(f"pt_atr must be positive, got {pt_atr}")
        if sl_atr <= 0:
            raise ValueError(f"sl_atr must be positive, got {sl_atr}")
        if max_holding_bars < 1:
            raise ValueError(f"max_holding_bars must be >= 1, got {max_holding_bars}")

        self.pt_atr = pt_atr
        self.sl_atr = sl_atr
        self.max_holding_bars = max_holding_bars
        self.cost_model = cost_model or ExecutionCostModel()
        self.atr_column = atr_column
        self.conservative_stop_first = conservative_stop_first
        self.weekend_threshold_hours = weekend_threshold_hours

    def compute_labels(
        self,
        df: pd.DataFrame,
        baseline_atr: float = 1.153,
        baseline_candle_range: float = 1.050,
    ) -> pd.DataFrame:
        """Compute causal directional triple-barrier labels for financial candles.

        Parameters
        ----------
        df : pd.DataFrame
            DataFrame containing ['timestamp', 'open', 'high', 'low', 'close']
            and ATR column.
        baseline_atr : float
            Baseline ATR for volatility spread scaling.
        baseline_candle_range : float
            Baseline candle range for slippage scaling.
        """
        required_cols = ["timestamp", "open", "high", "low", "close"]
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Missing required price column '{col}'")

        timestamps = pd.to_datetime(df["timestamp"], utc=True)
        opens = df["open"].to_numpy(dtype=float)
        highs = df["high"].to_numpy(dtype=float)
        lows = df["low"].to_numpy(dtype=float)
        closes = df["close"].to_numpy(dtype=float)

        if self.atr_column in df.columns:
            atrs = df[self.atr_column].to_numpy(dtype=float)
        else:
            ranges = highs - lows
            atrs = pd.Series(ranges).rolling(14, min_periods=1).mean().to_numpy()

        candle_ranges = highs - lows
        N = len(df)
        H_max = self.max_holding_bars

        # Pre-allocate output arrays
        target_classes = np.full(N, np.nan, dtype=float)
        is_purged = np.zeros(N, dtype=bool)
        purge_reasons = np.full(N, None, dtype=object)

        long_events = np.full(N, None, dtype=object)
        short_events = np.full(N, None, dtype=object)
        long_bars_held = np.full(N, -1, dtype=int)
        short_bars_held = np.full(N, -1, dtype=int)

        market_closed_series = self.cost_model.is_market_closed_series(timestamps)
        weekend_gap_threshold = pd.Timedelta(hours=self.weekend_threshold_hours)

        # Boundary split overflow: bars near partition tail cannot monitor up to H_max
        max_valid_i = N - (1 + H_max)
        if max_valid_i < 0:
            purge_reasons[:] = PURGE_BOUNDARY_SPLIT_OVERFLOW
            is_purged[:] = True
        else:
            purge_reasons[max_valid_i:] = PURGE_BOUNDARY_SPLIT_OVERFLOW
            is_purged[max_valid_i:] = True

        valid_limit = max(0, max_valid_i)

        for i in range(valid_limit):
            entry_idx = i + 1
            if entry_idx >= N:
                continue

            entry_ts = timestamps.iloc[entry_idx]

            # Reject entry during market closure
            if market_closed_series[entry_idx]:
                is_purged[i] = True
                purge_reasons[i] = PURGE_ROLLOVER_CLOSED
                continue

            # Causal volatility metrics finalized on or before bar i
            entry_atr = atrs[i]
            entry_range = candle_ranges[i]
            entry_bid = opens[entry_idx]

            # Entry spread and slippage
            entry_spread = self.cost_model.calculate_effective_spread(
                timestamp=entry_ts,
                current_atr=entry_atr,
                baseline_atr=baseline_atr,
            )
            entry_slippage = self.cost_model.calculate_slippage(
                candle_range=entry_range,
                baseline_candle_range=baseline_candle_range,
            )

            # Long Entry executes at Ask = Bid + Spread + Slippage
            long_fill = entry_bid + entry_spread + entry_slippage
            # Short Entry executes at Bid = Bid - Slippage
            short_fill = entry_bid - entry_slippage

            # Barrier calculations (anchored relative to simulated entry fill price)
            pt_delta = self.pt_atr * entry_atr
            sl_delta = self.sl_atr * entry_atr

            # LONG BARRIERS:
            long_target_barrier = long_fill + pt_delta
            long_stop_barrier = long_fill - sl_delta

            # SHORT BARRIERS:
            short_target_barrier = short_fill - pt_delta
            short_stop_barrier = short_fill + sl_delta

            # -------------------------------------------------------------
            # Monitor bars k from i+1 to i+1+H_max
            # -------------------------------------------------------------
            long_exit_type = None
            long_exit_bar = -1
            short_exit_type = None
            short_exit_bar = -1

            weekend_purged = False

            for k in range(entry_idx, min(N, entry_idx + H_max)):
                bar_ts = timestamps.iloc[k]

                # Check weekend crossing
                if (bar_ts - entry_ts) > weekend_gap_threshold:
                    weekend_purged = True
                    break

                b_open = opens[k]
                b_high = highs[k]
                b_low = lows[k]

                # --- LONG BARRIER MONITORING ---
                if long_exit_type is None:
                    # Gap check at open (for k > entry_idx)
                    gap_target = (k > entry_idx) and (b_open >= long_target_barrier)
                    gap_stop = (k > entry_idx) and (b_open <= long_stop_barrier)

                    touch_target = b_high >= long_target_barrier
                    touch_stop = b_low <= long_stop_barrier

                    if gap_stop:
                        long_exit_type = "STOP"
                        long_exit_bar = k
                    elif gap_target:
                        long_exit_type = "TARGET"
                        long_exit_bar = k
                    elif touch_target and touch_stop:
                        # Ambiguity in same candle: apply conservative stop-first
                        long_exit_type = "STOP" if self.conservative_stop_first else "TARGET"
                        long_exit_bar = k
                    elif touch_stop:
                        long_exit_type = "STOP"
                        long_exit_bar = k
                    elif touch_target:
                        long_exit_type = "TARGET"
                        long_exit_bar = k

                # --- SHORT BARRIER MONITORING ---
                if short_exit_type is None:
                    gap_target_s = (k > entry_idx) and (b_open <= short_target_barrier)
                    gap_stop_s = (k > entry_idx) and (b_open >= short_stop_barrier)

                    touch_target_s = b_low <= short_target_barrier
                    touch_stop_s = b_high >= short_stop_barrier

                    if gap_stop_s:
                        short_exit_type = "STOP"
                        short_exit_bar = k
                    elif gap_target_s:
                        short_exit_type = "TARGET"
                        short_exit_bar = k
                    elif touch_target_s and touch_stop_s:
                        # Ambiguity: conservative stop-first
                        short_exit_type = "STOP" if self.conservative_stop_first else "TARGET"
                        short_exit_bar = k
                    elif touch_stop_s:
                        short_exit_type = "STOP"
                        short_exit_bar = k
                    elif touch_target_s:
                        short_exit_type = "TARGET"
                        short_exit_bar = k

                # If both long and short resolved, we can stop scanning
                if long_exit_type is not None and short_exit_type is not None:
                    break

            if weekend_purged:
                is_purged[i] = True
                purge_reasons[i] = PURGE_WEEKEND_CROSSING
                continue

            # Time limit exit if barrier not hit within H_max bars
            time_exit_idx = min(N - 1, entry_idx + H_max)
            if long_exit_type is None:
                long_exit_type = "TIME_LIMIT"
                long_exit_bar = time_exit_idx

            if short_exit_type is None:
                short_exit_type = "TIME_LIMIT"
                short_exit_bar = time_exit_idx

            long_events[i] = long_exit_type
            short_events[i] = short_exit_type
            long_bars_held[i] = long_exit_bar - entry_idx + 1
            short_bars_held[i] = short_exit_bar - entry_idx + 1

            # -------------------------------------------------------------
            # Target Class Assignment:
            # +1 (Long Edge): Long hits TARGET while Short does not
            # -1 (Short Edge): Short hits TARGET while Long does not
            #  0 (Neutral): Both hit stop, both hit target, or time limit
            # -------------------------------------------------------------
            long_won = (long_exit_type == "TARGET")
            short_won = (short_exit_type == "TARGET")

            if long_won and not short_won:
                target_classes[i] = 1
            elif short_won and not long_won:
                target_classes[i] = -1
            else:
                target_classes[i] = 0

        out = pd.DataFrame(index=df.index)
        out["timestamp"] = timestamps
        out["target_class"] = target_classes
        out["is_purged"] = is_purged
        out["purge_reason"] = purge_reasons
        out["long_barrier_event"] = long_events
        out["short_barrier_event"] = short_events
        out["long_bars_held"] = long_bars_held
        out["short_bars_held"] = short_bars_held

        return out
