"""Causal Directional Labeling Engine for Intraday Financial Machine Learning.

Strict Execution-Cost Causality & Timezone-Aware Boundary Alignment:
-------------------------------------------------------------------
1. Coordinate Timing:
   - Decision Time (T_t): Finalized at the close of bar t (index i).
   - Entry Time (T_{t+1}): Order executes at the Open of bar t+1 (index i + 1).
     Volatility inputs (ATR and candle range) MUST be finalized no later than bar t (index i).
     Bar t+1's completed range or future ATR is NEVER accessed to price the entry fill.
   - Exit Time (T_{t+1+H}): Order executes at the Open of bar t+1+H (index i + 1 + H).
     Volatility inputs (ATR and candle range) MUST be finalized no later than bar t+H (index i + H).
     Bar t+1+H's completed range or future ATR is NEVER accessed to price the exit fill.

2. Weekend Market Closure Policy:
   - For intraday labeling, any trade whose entry-to-exit interval crosses a weekend
     market closure is purged (target_class assigned NaN) with reason 'WEEKEND_CROSSING'.
   - No fabricated Friday exit fill is constructed.
   - Configurable policy: default is 'purge' (strict intraday isolation).

3. Daily Settlement Rollover Policy:
   - Gold market settlement closure occurs Mon-Thu 17:00:00 to 18:00:00 New York Time.
   - Any order attempting to execute an entry or exit during rollover closure is rejected
     and purged with reason 'ROLLOVER_CLOSED'.
   - Positions entering before 17:00 NY and exiting at or after 18:00 NY:
     * rollover_policy='allow' (default): Allowed to bridge daily settlement, penalized by
       the DAILY_ROLL_BREAK session liquidity spread multiplier (12.0x base spread) for fills
       in the 16:45-18:15 NY window.
     * rollover_policy='purge': Purged with reason 'ROLLOVER_CROSSING' to enforce strict
       intraday settlement exit.

4. Exact Partition-Boundary Purging:
   - For a partition of length N (indices 0 <= i < N), rows where i + 1 + H >= N
     cannot execute an exit within the split.
   - These rows are purged with reason 'BOUNDARY_SPLIT_OVERFLOW' to prevent cross-split leakage.

5. Bid-Only Execution Pricing & Net Return:
   - Long Trade:
     * Entry (Buy at Ask): nominal_bid + entry_spread + entry_slippage
     * Exit (Sell at Bid): nominal_bid - exit_slippage
     * Net Long Return = (Exit_Fill - Entry_Fill - 2 * Commission) / Entry_Fill
   - Short Trade:
     * Entry (Sell at Bid): nominal_bid - entry_slippage
     * Exit (Buy at Ask): nominal_bid + exit_spread + exit_slippage
     * Net Short Return = (Entry_Fill - Exit_Fill - 2 * Commission) / Entry_Fill
   - Directional Target:
     * +1 (Long) if Net_Long_Return > min_return_threshold and Net_Long_Return > Net_Short_Return
     * -1 (Short) if Net_Short_Return > min_return_threshold and Net_Short_Return > Net_Long_Return
     *  0 (Neutral) if neither condition is met (friction eliminates directional edge)
     * NaN if purged.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd

from treading_ai.backtesting.cost_model import ExecutionCostModel

TZ_NEW_YORK = ZoneInfo("America/New_York")

PURGE_BOUNDARY_SPLIT_OVERFLOW = "BOUNDARY_SPLIT_OVERFLOW"
PURGE_WEEKEND_CROSSING = "WEEKEND_CROSSING"
PURGE_ROLLOVER_CLOSED = "ROLLOVER_CLOSED"
PURGE_ROLLOVER_CROSSING = "ROLLOVER_CROSSING"


@dataclass(frozen=True)
class LabelingSummary:
    """Summary metrics of the labeling run."""
    horizon: int
    total_rows: int
    valid_rows: int
    purged_rows: int
    purge_counts: Dict[str, int]
    class_balance_counts: Dict[int, int]
    class_balance_percentages: Dict[int, float]
    weekend_policy: str
    rollover_policy: str
    min_return_threshold: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "horizon": self.horizon,
            "total_rows": self.total_rows,
            "valid_rows": self.valid_rows,
            "purged_rows": self.purged_rows,
            "purge_counts": self.purge_counts,
            "class_balance_counts": self.class_balance_counts,
            "class_balance_percentages": self.class_balance_percentages,
            "weekend_policy": self.weekend_policy,
            "rollover_policy": self.rollover_policy,
            "min_return_threshold": self.min_return_threshold,
        }


class CausalDirectionalLabeler:
    """Causal directional labeling engine with bid-only execution modeling."""

    def __init__(
        self,
        horizon: int = 6,
        cost_model: Optional[ExecutionCostModel] = None,
        weekend_policy: str = "purge",
        rollover_policy: str = "allow",
        min_return_threshold: float = 0.0,
        atr_column: str = "atr_14",
        weekend_threshold_hours: Optional[float] = None,
    ):
        if horizon < 1:
            raise ValueError(f"horizon must be a positive integer, got {horizon}")
        if weekend_policy not in ["purge", "allow"]:
            raise ValueError(f"weekend_policy must be 'purge' or 'allow', got {weekend_policy}")
        if rollover_policy not in ["allow", "purge"]:
            raise ValueError(f"rollover_policy must be 'allow' or 'purge', got {rollover_policy}")

        self.horizon = horizon
        self.cost_model = cost_model or ExecutionCostModel()
        self.weekend_policy = weekend_policy
        self.rollover_policy = rollover_policy
        self.min_return_threshold = min_return_threshold
        self.atr_column = atr_column
        if weekend_threshold_hours is None:
            self.weekend_threshold_hours = max(24.0, (horizon * 5 / 60.0) + 20.0)
        else:
            self.weekend_threshold_hours = float(weekend_threshold_hours)

    def compute_labels(
        self,
        df: pd.DataFrame,
        baseline_atr: Optional[float] = None,
        baseline_candle_range: Optional[float] = None,
    ) -> pd.DataFrame:
        """Compute causal directional labels for a partition of financial candles.

        Parameters
        ----------
        df : pd.DataFrame
            Partition DataFrame containing columns ['timestamp', 'open', 'high', 'low', 'close']
            and optionally an ATR column matching self.atr_column.
        baseline_atr : Optional[float]
            Baseline ATR for volatility spread scaling. Defaults to median of ATR column.
        baseline_candle_range : Optional[float]
            Baseline candle range for slippage scaling. Defaults to median of (high - low).

        Returns
        -------
        pd.DataFrame
            DataFrame matching the input index, containing label columns and purge diagnostics.
        """
        required_cols = ["timestamp", "open", "high", "low", "close"]
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Missing required price column '{col}' in input DataFrame.")

        # Robust Input Validation
        timestamps = df["timestamp"]
        if not pd.api.types.is_datetime64_any_dtype(timestamps):
            raise ValueError("timestamp column must be datetime64 dtype.")
        if not timestamps.is_monotonic_increasing:
            raise ValueError("Timestamps must be strictly monotonic increasing.")
        if timestamps.duplicated().any():
            raise ValueError("Timestamps contain duplicate entries.")

        for col in ["open", "high", "low", "close"]:
            if (df[col] <= 0).any():
                raise ValueError(f"Price column '{col}' contains non-positive values.")
            if df[col].isna().any():
                raise ValueError(f"Price column '{col}' contains NaN values.")

        if (df["high"] < df["low"]).any():
            raise ValueError("Price column 'high' cannot be strictly less than 'low'.")

        if self.atr_column in df.columns:
            if (df[self.atr_column] < 0).any():
                raise ValueError(f"ATR column '{self.atr_column}' contains negative values.")

        N = len(df)
        H = self.horizon

        # Initialize output DataFrame preserving the original index
        out = pd.DataFrame(index=df.index)

        # Baseline metrics calculation
        has_atr = self.atr_column in df.columns
        if self.cost_model.enable_volatility_scaling:
            if has_atr:
                atrs = df[self.atr_column].to_numpy(dtype=float)
                if baseline_atr is None:
                    valid_atrs = atrs[~np.isnan(atrs)]
                    baseline_atr = float(np.median(valid_atrs)) if len(valid_atrs) > 0 else 1.0
            else:
                atrs = np.ones(N, dtype=float)
                baseline_atr = 1.0
        else:
            atrs = np.ones(N, dtype=float)
            baseline_atr = 1.0

        candle_ranges = (df["high"] - df["low"]).to_numpy(dtype=float)
        if baseline_candle_range is None:
            valid_ranges = candle_ranges[~np.isnan(candle_ranges)]
            baseline_candle_range = float(np.median(valid_ranges)) if len(valid_ranges) > 0 else 1.0

        opens = df["open"].to_numpy(dtype=float)

        # Pre-allocate output arrays
        decision_ts = timestamps.copy()
        entry_ts = pd.Series([pd.NaT] * N, index=df.index, dtype=timestamps.dtype)
        exit_ts = pd.Series([pd.NaT] * N, index=df.index, dtype=timestamps.dtype)

        entry_indices = np.full(N, -1, dtype=int)
        exit_indices = np.full(N, -1, dtype=int)

        entry_bids = np.full(N, np.nan, dtype=float)
        exit_bids = np.full(N, np.nan, dtype=float)

        long_entry_fills = np.full(N, np.nan, dtype=float)
        long_exit_fills = np.full(N, np.nan, dtype=float)
        short_entry_fills = np.full(N, np.nan, dtype=float)
        short_exit_fills = np.full(N, np.nan, dtype=float)

        long_frictions = np.full(N, np.nan, dtype=float)
        short_frictions = np.full(N, np.nan, dtype=float)

        gross_returns_long = np.full(N, np.nan, dtype=float)
        gross_returns_short = np.full(N, np.nan, dtype=float)
        net_returns_long = np.full(N, np.nan, dtype=float)
        net_returns_short = np.full(N, np.nan, dtype=float)

        target_classes = np.full(N, np.nan, dtype=float)
        purge_reasons = np.full(N, None, dtype=object)
        is_purged = np.zeros(N, dtype=bool)

        # Boundary purge: any row where exit bar falls outside the partition
        # Decision index i: Entry = i + 1, Exit = i + 1 + H
        # Valid decision indices within partition: 0 <= i < N - (1 + H)
        max_valid_i = N - (1 + H)
        if max_valid_i < 0:
            # Entire partition is too short for horizon H
            purge_reasons[:] = PURGE_BOUNDARY_SPLIT_OVERFLOW
            is_purged[:] = True
            out["decision_timestamp"] = decision_ts
            out["entry_timestamp"] = entry_ts
            out["exit_timestamp"] = exit_ts
            out["entry_index"] = entry_indices
            out["exit_index"] = exit_indices
            out["entry_bid"] = entry_bids
            out["exit_bid"] = exit_bids
            out["long_entry_fill"] = long_entry_fills
            out["long_exit_fill"] = long_exit_fills
            out["short_entry_fill"] = short_entry_fills
            out["short_exit_fill"] = short_exit_fills
            out["long_friction"] = long_frictions
            out["short_friction"] = short_frictions
            out["gross_return_long"] = gross_returns_long
            out["gross_return_short"] = gross_returns_short
            out["net_return_long"] = net_returns_long
            out["net_return_short"] = net_returns_short
            out["target_class"] = target_classes
            out["purge_reason"] = purge_reasons
            out["is_purged"] = is_purged
            return out

        # Mark split overflow for tail rows
        purge_reasons[max_valid_i:] = PURGE_BOUNDARY_SPLIT_OVERFLOW
        is_purged[max_valid_i:] = True

        # Process valid slice [0, max_valid_i)
        valid_i = np.arange(max_valid_i)
        e_idx = valid_i + 1
        x_idx = valid_i + 1 + H

        entry_indices[:max_valid_i] = e_idx
        exit_indices[:max_valid_i] = x_idx

        e_ts = timestamps.iloc[e_idx].reset_index(drop=True)
        x_ts = timestamps.iloc[x_idx].reset_index(drop=True)

        # Assemble entry and exit timestamps with strict timezone preservation
        entry_ts = pd.concat(
            [
                e_ts,
                pd.Series([pd.NaT] * (N - max_valid_i), dtype=timestamps.dtype),
            ],
            ignore_index=True,
        ).set_axis(df.index)

        exit_ts = pd.concat(
            [
                x_ts,
                pd.Series([pd.NaT] * (N - max_valid_i), dtype=timestamps.dtype),
            ],
            ignore_index=True,
        ).set_axis(df.index)

        e_bid = opens[e_idx]
        x_bid = opens[x_idx]
        entry_bids[:max_valid_i] = e_bid
        exit_bids[:max_valid_i] = x_bid

        # Check market closures for entry and exit fills
        e_roll_closed = self.cost_model.is_rollover_closed_series(e_ts)
        x_roll_closed = self.cost_model.is_rollover_closed_series(x_ts)
        e_wknd_closed = self.cost_model.is_weekend_closed_series(e_ts)
        x_wknd_closed = self.cost_model.is_weekend_closed_series(x_ts)

        # Check Weekend crossing:
        # Time gap between entry and exit exceeds weekend_threshold_hours
        weekend_gap_threshold = pd.Timedelta(hours=self.weekend_threshold_hours)
        time_diffs = (x_ts.to_numpy() - e_ts.to_numpy())
        weekend_cross_mask = time_diffs > weekend_gap_threshold

        # Check Rollover crossing:
        # Entry before 17:00 NY, Exit at or after 18:00 NY on the same Mon-Thu civil day
        e_ny = e_ts.dt.tz_convert(TZ_NEW_YORK)
        x_ny = x_ts.dt.tz_convert(TZ_NEW_YORK)
        rollover_cross_mask = (
            (e_ny.dt.day_of_week < 4) & (x_ny.dt.day_of_week < 4) &
            (e_ny.dt.date == x_ny.dt.date) &
            (e_ny.dt.hour < 17) & (x_ny.dt.hour >= 18)
        ).to_numpy(dtype=bool)

        # Volatility inputs:
        # Pre-Trade Causality:
        # Entry at bar t+1 uses bar t volatility (valid_i)
        # Exit at bar t+1+H uses bar t+H volatility (valid_i + H)
        entry_prior_atr = atrs[valid_i]
        entry_prior_range = candle_ranges[valid_i]

        exit_prior_atr = atrs[valid_i + H]
        exit_prior_range = candle_ranges[valid_i + H]

        # Calculate dynamic spread and slippage via vectorized cost model methods
        entry_spread = self.cost_model.calculate_effective_spread_series(
            e_ts, prior_atrs=entry_prior_atr, baseline_atr=baseline_atr
        )
        entry_slip = self.cost_model.calculate_slippage_series(
            prior_candle_ranges=entry_prior_range, baseline_candle_range=baseline_candle_range
        )

        exit_spread = self.cost_model.calculate_effective_spread_series(
            x_ts, prior_atrs=exit_prior_atr, baseline_atr=baseline_atr
        )
        exit_slip = self.cost_model.calculate_slippage_series(
            prior_candle_ranges=exit_prior_range, baseline_candle_range=baseline_candle_range
        )

        comm = self.cost_model.commission_per_oz  # per oz per leg ($0.05)

        # Long Trade Pricing:
        # Entry: BUY at Ask = Bid + Spread + Slippage
        # Exit: SELL at Bid = Bid - Slippage
        long_e_fill = np.round(e_bid + entry_spread + entry_slip, 3)
        long_x_fill = np.round(x_bid - exit_slip, 3)
        long_fric = np.round(entry_spread + entry_slip + exit_slip + 2.0 * comm, 3)

        # Short Trade Pricing:
        # Entry: SELL at Bid = Bid - Slippage
        # Exit: BUY at Ask = Bid + Spread + Slippage
        short_e_fill = np.round(e_bid - entry_slip, 3)
        short_x_fill = np.round(x_bid + exit_spread + exit_slip, 3)
        short_fric = np.round(exit_spread + entry_slip + exit_slip + 2.0 * comm, 3)

        # Returns:
        g_ret_long = (x_bid - e_bid) / e_bid
        g_ret_short = (e_bid - x_bid) / e_bid

        # Net dollar PnL per oz and fractional returns
        net_pnl_l = (long_x_fill - long_e_fill) - 2.0 * comm
        net_ret_long = net_pnl_l / long_e_fill

        net_pnl_s = (short_e_fill - short_x_fill) - 2.0 * comm
        net_ret_short = net_pnl_s / short_e_fill

        # Store calculated economics
        long_entry_fills[:max_valid_i] = long_e_fill
        long_exit_fills[:max_valid_i] = long_x_fill
        short_entry_fills[:max_valid_i] = short_e_fill
        short_exit_fills[:max_valid_i] = short_x_fill

        long_frictions[:max_valid_i] = long_fric
        short_frictions[:max_valid_i] = short_fric

        gross_returns_long[:max_valid_i] = g_ret_long
        gross_returns_short[:max_valid_i] = g_ret_short
        net_returns_long[:max_valid_i] = net_ret_long
        net_returns_short[:max_valid_i] = net_ret_short

        # Evaluate Purge Policies in Priority Order:
        # 1. Closed market fills (Rollover or Weekend)
        # 2. Weekend Crossing
        # 3. Rollover Crossing (if policy == 'purge')
        for idx_rel in range(max_valid_i):
            if e_roll_closed[idx_rel] or x_roll_closed[idx_rel]:
                purge_reasons[idx_rel] = PURGE_ROLLOVER_CLOSED
                is_purged[idx_rel] = True
            elif e_wknd_closed[idx_rel] or x_wknd_closed[idx_rel]:
                purge_reasons[idx_rel] = PURGE_WEEKEND_CROSSING
                is_purged[idx_rel] = True
            elif self.weekend_policy == "purge" and weekend_cross_mask[idx_rel]:
                purge_reasons[idx_rel] = PURGE_WEEKEND_CROSSING
                is_purged[idx_rel] = True
            elif self.rollover_policy == "purge" and rollover_cross_mask[idx_rel]:
                purge_reasons[idx_rel] = PURGE_ROLLOVER_CROSSING
                is_purged[idx_rel] = True

        # Assign Targets for Non-Purged Rows
        non_purged_valid = (~is_purged[:max_valid_i])
        classes = np.zeros(max_valid_i, dtype=float)

        long_win = (net_ret_long > self.min_return_threshold) & (net_ret_long > net_ret_short)
        short_win = (net_ret_short > self.min_return_threshold) & (net_ret_short > net_ret_long)

        classes[long_win] = 1.0
        classes[short_win] = -1.0
        # remaining non-purged stay 0.0 (Neutral)

        # Write to final target array
        target_classes[:max_valid_i] = np.where(non_purged_valid, classes, np.nan)

        # Assemble output DataFrame
        out["decision_timestamp"] = decision_ts
        out["entry_timestamp"] = entry_ts
        out["exit_timestamp"] = exit_ts
        out["entry_index"] = entry_indices
        out["exit_index"] = exit_indices
        out["entry_bid"] = entry_bids
        out["exit_bid"] = exit_bids
        out["long_entry_fill"] = long_entry_fills
        out["long_exit_fill"] = long_exit_fills
        out["short_entry_fill"] = short_entry_fills
        out["short_exit_fill"] = short_exit_fills
        out["long_friction"] = long_frictions
        out["short_friction"] = short_frictions
        out["gross_return_long"] = gross_returns_long
        out["gross_return_short"] = gross_returns_short
        out["net_return_long"] = net_returns_long
        out["net_return_short"] = net_returns_short
        out["target_class"] = target_classes
        out["purge_reason"] = purge_reasons
        out["is_purged"] = is_purged

        return out

    def get_summary(self, labeled_df: pd.DataFrame) -> LabelingSummary:
        """Compute statistical summary and purge audit ledger."""
        total_rows = len(labeled_df)
        purged_mask = labeled_df["is_purged"].to_numpy(dtype=bool)
        purged_rows = int(purged_mask.sum())
        valid_rows = total_rows - purged_rows

        # Purge breakdown
        purge_reasons = labeled_df["purge_reason"].value_counts().to_dict()
        purge_counts = {
            PURGE_BOUNDARY_SPLIT_OVERFLOW: purge_reasons.get(PURGE_BOUNDARY_SPLIT_OVERFLOW, 0),
            PURGE_WEEKEND_CROSSING: purge_reasons.get(PURGE_WEEKEND_CROSSING, 0),
            PURGE_ROLLOVER_CLOSED: purge_reasons.get(PURGE_ROLLOVER_CLOSED, 0),
            PURGE_ROLLOVER_CROSSING: purge_reasons.get(PURGE_ROLLOVER_CROSSING, 0),
        }

        # Class balance on non-purged rows
        valid_classes = labeled_df.loc[~purged_mask, "target_class"].astype(int)
        class_counts = valid_classes.value_counts().to_dict()
        class_balance_counts = {
            1: class_counts.get(1, 0),
            -1: class_counts.get(-1, 0),
            0: class_counts.get(0, 0),
        }

        if valid_rows > 0:
            class_balance_percentages = {
                k: round(v / valid_rows * 100.0, 2)
                for k, v in class_balance_counts.items()
            }
        else:
            class_balance_percentages = {1: 0.0, -1: 0.0, 0: 0.0}

        return LabelingSummary(
            horizon=self.horizon,
            total_rows=total_rows,
            valid_rows=valid_rows,
            purged_rows=purged_rows,
            purge_counts=purge_counts,
            class_balance_counts=class_balance_counts,
            class_balance_percentages=class_balance_percentages,
            weekend_policy=self.weekend_policy,
            rollover_policy=self.rollover_policy,
            min_return_threshold=self.min_return_threshold,
        )
