"""Triple-Barrier Strategy Simulator for Spot Gold (XAUUSD).

Simulates realistic, conservative intraday trade execution with volatility barriers:
- Profit-taking barrier: pt_atr * ATR
- Stop-loss barrier: sl_atr * ATR
- Maximum holding period: max_holding_bars (Time limit)
- Ambiguity rule: Conservative stop-first assumption when both barriers crossed in the same bar.
- Gap rule: Conservative open-price execution when a barrier is crossed via gap.
- Market closure protection: Fills prohibited during rollover and weekend closures.
- Friction accounting: Bid-only institutional execution with dynamic spread, slippage, and commissions.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from treading_ai.backtesting.cost_model import ExecutionCostModel


@dataclass(frozen=True)
class TripleBarrierTrade:
    """Detailed record of a triple-barrier simulated trade."""
    signal_index: int
    signal_timestamp: pd.Timestamp
    direction: int  # +1 (Long) or -1 (Short)
    entry_index: int
    entry_timestamp: pd.Timestamp
    entry_bid: float
    entry_fill: float
    entry_spread: float
    entry_slippage: float
    exit_index: int
    exit_timestamp: pd.Timestamp
    exit_bid: float
    exit_fill: float
    exit_spread: float
    exit_slippage: float
    exit_reason: str  # 'TARGET', 'STOP', 'TIME_LIMIT'
    bars_held: int
    commission: float
    total_friction: float
    gross_pnl: float
    net_pnl: float
    gross_return: float
    net_return: float
    is_gap_exit: bool
    is_ambiguous_same_bar: bool


@dataclass(frozen=True)
class TripleBarrierMetrics:
    """Summary metrics of triple-barrier backtest performance."""
    strategy_name: str
    scenario_name: str
    total_bars: int
    tradable_bars: int
    n_eligible_signals: int
    n_executed_entries: int
    n_completed_trades: int
    n_capacity_rejected: int
    n_closure_rejected: int
    trade_frequency_pct: float
    market_exposure_pct: float
    max_concurrent_positions: int
    avg_concurrent_positions: float
    avg_bars_held: float
    # Barrier hit distribution
    n_target_hits: int
    n_stop_hits: int
    n_time_limit_exits: int
    pct_target_hits: float
    pct_stop_hits: float
    pct_time_limit: float
    # PnL metrics ($/oz)
    gross_pnl_usd: float
    net_pnl_usd: float
    total_spread_usd: float
    total_slippage_usd: float
    total_commission_usd: float
    total_friction_usd: float
    avg_net_pnl_per_trade: float
    median_net_pnl_per_trade: float
    avg_gross_return_bps: float
    avg_net_return_bps: float
    win_rate_gross: float
    win_rate_net: float
    profit_factor_gross: float
    profit_factor_net: float
    max_drawdown_usd: float
    drawdown_convention: str
    # Long vs Short
    long_trades: int
    long_gross_pnl: float
    long_net_pnl: float
    long_win_rate_net: float
    short_trades: int
    short_gross_pnl: float
    short_net_pnl: float
    short_win_rate_net: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_name": self.strategy_name,
            "scenario_name": self.scenario_name,
            "total_bars": self.total_bars,
            "tradable_bars": self.tradable_bars,
            "n_eligible_signals": self.n_eligible_signals,
            "n_executed_entries": self.n_executed_entries,
            "n_completed_trades": self.n_completed_trades,
            "n_capacity_rejected": self.n_capacity_rejected,
            "n_closure_rejected": self.n_closure_rejected,
            "trade_frequency_pct": self.trade_frequency_pct,
            "market_exposure_pct": self.market_exposure_pct,
            "max_concurrent_positions": self.max_concurrent_positions,
            "avg_concurrent_positions": self.avg_concurrent_positions,
            "avg_bars_held": self.avg_bars_held,
            "n_target_hits": self.n_target_hits,
            "n_stop_hits": self.n_stop_hits,
            "n_time_limit_exits": self.n_time_limit_exits,
            "pct_target_hits": self.pct_target_hits,
            "pct_stop_hits": self.pct_stop_hits,
            "pct_time_limit": self.pct_time_limit,
            "gross_pnl_usd": self.gross_pnl_usd,
            "net_pnl_usd": self.net_pnl_usd,
            "total_spread_usd": self.total_spread_usd,
            "total_slippage_usd": self.total_slippage_usd,
            "total_commission_usd": self.total_commission_usd,
            "total_friction_usd": self.total_friction_usd,
            "avg_net_pnl_per_trade": self.avg_net_pnl_per_trade,
            "median_net_pnl_per_trade": self.median_net_pnl_per_trade,
            "avg_gross_return_bps": self.avg_gross_return_bps,
            "avg_net_return_bps": self.avg_net_return_bps,
            "win_rate_gross": self.win_rate_gross,
            "win_rate_net": self.win_rate_net,
            "profit_factor_gross": self.profit_factor_gross,
            "profit_factor_net": self.profit_factor_net,
            "max_drawdown_usd": self.max_drawdown_usd,
            "drawdown_convention": self.drawdown_convention,
            "long_trades": self.long_trades,
            "long_gross_pnl": self.long_gross_pnl,
            "long_net_pnl": self.long_net_pnl,
            "long_win_rate_net": self.long_win_rate_net,
            "short_trades": self.short_trades,
            "short_gross_pnl": self.short_gross_pnl,
            "short_net_pnl": self.short_net_pnl,
            "short_win_rate_net": self.short_win_rate_net,
        }

    def summary_table(self) -> str:
        lines = [
            f"=== Triple-Barrier Backtest: {self.strategy_name} [{self.scenario_name}] ===",
            f"Trades: Completed={self.n_completed_trades:,} (Long: {self.long_trades:,}, Short: {self.short_trades:,}) | CapRejected={self.n_capacity_rejected:,} | ClosRejected={self.n_closure_rejected:,}",
            f"Exit Reasons: Target={self.n_target_hits:,} ({self.pct_target_hits:.1%}) | Stop={self.n_stop_hits:,} ({self.pct_stop_hits:.1%}) | TimeLimit={self.n_time_limit_exits:,} ({self.pct_time_limit:.1%})",
            f"Holding: Avg Bars={self.avg_bars_held:.1f} bars ({self.avg_bars_held * 5:.1f}m) | Exposure={self.market_exposure_pct:.2f}% | Max Concurrent={self.max_concurrent_positions}",
            f"Gross PnL: ${self.gross_pnl_usd:+,.2f}/oz | Net PnL: ${self.net_pnl_usd:+,.2f}/oz | Total Friction: ${self.total_friction_usd:,.2f}/oz",
            f"Friction Breakdown: Spread=${self.total_spread_usd:,.2f}/oz | Slippage=${self.total_slippage_usd:,.2f}/oz | Comm=${self.total_commission_usd:,.2f}/oz",
            f"Per-Trade Net PnL: Mean=${self.avg_net_pnl_per_trade:+,.3f}/oz ({self.avg_net_return_bps:+,.2f} bps) | Median=${self.median_net_pnl_per_trade:+,.3f}/oz",
            f"Win Rate (Net): {self.win_rate_net:.2%} (Gross: {self.win_rate_gross:.2%})",
            f"Profit Factor (Net): {self.profit_factor_net:.3f} (Gross: {self.profit_factor_gross:.3f})",
            f"Max Drawdown: -${self.max_drawdown_usd:,.2f}/oz ({self.drawdown_convention})",
            f"Long Side Net PnL: ${self.long_net_pnl:+,.2f}/oz (Win: {self.long_win_rate_net:.2%})",
            f"Short Side Net PnL: ${self.short_net_pnl:+,.2f}/oz (Win: {self.short_win_rate_net:.2%})",
        ]
        return "\n".join(lines)


class TripleBarrierSimulator:
    """Simulates realistic triple-barrier execution with conservative fill pricing.

    Parameters
    ----------
    pt_atr : float, default=2.0
        Profit-taking barrier multiplier in units of ATR.
    sl_atr : float, default=1.0
        Stop-loss barrier multiplier in units of ATR.
    max_holding_bars : int, default=24
        Maximum holding bars before vertical time exit.
    cost_model : Optional[ExecutionCostModel]
        Cost simulator for dynamic spread, slippage, and commission.
    mode : str, default='non_overlapping'
        'non_overlapping' (single-position capacity=1) or 'overlapping'.
    conservative_stop_first : bool, default=True
        Resolves ambiguous same-bar barrier touches with conservative stop-first.
    """

    def __init__(
        self,
        pt_atr: float = 2.0,
        sl_atr: float = 1.0,
        max_holding_bars: int = 24,
        cost_model: Optional[ExecutionCostModel] = None,
        mode: str = "non_overlapping",
        conservative_stop_first: bool = True,
        baseline_atr: float = 1.153,
        baseline_candle_range: float = 1.050,
        atr_column: str = "atr_14",
    ) -> None:
        self.pt_atr = pt_atr
        self.sl_atr = sl_atr
        self.max_holding_bars = max_holding_bars
        self.cost_model = cost_model or ExecutionCostModel()
        self.mode = mode
        self.conservative_stop_first = conservative_stop_first
        self.baseline_atr = baseline_atr
        self.baseline_candle_range = baseline_candle_range
        self.atr_column = atr_column

    def simulate(
        self,
        df: pd.DataFrame,
        signals: Union[np.ndarray, pd.Series],
        strategy_name: str = "TripleBarrierStrategy",
        scenario_name: str = "Baseline Costs",
        mask: Optional[Union[np.ndarray, pd.Series]] = None,
    ) -> Tuple[TripleBarrierMetrics, List[TripleBarrierTrade]]:
        """Simulate trade execution on market data."""
        if mask is not None:
            mask_arr = np.asarray(mask, dtype=bool)
            full_signals = np.zeros(len(df), dtype=int)
            full_signals[mask_arr] = np.asarray(signals, dtype=int)
        else:
            full_signals = np.asarray(signals, dtype=int)

        n_rows = len(df)
        if len(full_signals) != n_rows:
            raise ValueError(f"Signal length ({len(full_signals)}) does not match DataFrame rows ({n_rows})")

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
        market_closed_series = self.cost_model.is_market_closed_series(timestamps)
        weekend_gap_threshold = pd.Timedelta(hours=24.0)

        trades: List[TripleBarrierTrade] = []
        n_eligible_signals = int(np.sum(full_signals != 0))
        n_capacity_rejected = 0
        n_closure_rejected = 0

        H_max = self.max_holding_bars
        tradable_bars = max(0, n_rows - (1 + H_max))

        concurrent_positions = np.zeros(n_rows, dtype=int)
        active_until_bar = -1

        comm_per_oz = self.cost_model.commission_per_oz
        comm_round_turn = 2.0 * comm_per_oz

        for i in range(tradable_bars):
            sig = full_signals[i]
            if sig == 0:
                continue

            # Position capacity check
            if self.mode == "non_overlapping":
                if i < active_until_bar:
                    n_capacity_rejected += 1
                    continue

            entry_idx = i + 1
            entry_ts = timestamps.iloc[entry_idx]

            # Closure check at entry
            if market_closed_series[entry_idx]:
                n_closure_rejected += 1
                continue

            entry_bid = opens[entry_idx]
            entry_atr = atrs[i]
            entry_range = candle_ranges[i]

            entry_spread = self.cost_model.calculate_effective_spread(
                timestamp=entry_ts,
                current_atr=entry_atr,
                baseline_atr=self.baseline_atr,
            )
            entry_slippage = self.cost_model.calculate_slippage(
                candle_range=entry_range,
                baseline_candle_range=self.baseline_candle_range,
            )

            if sig == 1:
                # Long Buy at Ask = Bid + Spread + Slippage
                entry_fill = entry_bid + entry_spread + entry_slippage
                pt_barrier = entry_fill + self.pt_atr * entry_atr
                sl_barrier = entry_fill - self.sl_atr * entry_atr
                entry_spread_stored = entry_spread
            else:
                # Short Sell at Bid = Bid - Slippage (zero spread on selling at bid)
                entry_fill = entry_bid - entry_slippage
                pt_barrier = entry_fill - self.pt_atr * entry_atr
                sl_barrier = entry_fill + self.sl_atr * entry_atr
                entry_spread_stored = 0.0

            # -------------------------------------------------------------
            # Scan forward from entry_idx up to entry_idx + H_max
            # -------------------------------------------------------------
            exit_reason = None
            exit_bar_idx = -1
            exit_bid = np.nan
            exit_spread = 0.0
            exit_slippage = 0.0
            is_gap = False
            is_ambiguous = False
            weekend_aborted = False

            for k in range(entry_idx, min(n_rows, entry_idx + H_max)):
                bar_ts = timestamps.iloc[k]

                # Weekend closure abort: do not cross weekend
                if (bar_ts - entry_ts) > weekend_gap_threshold:
                    weekend_aborted = True
                    break

                b_open = opens[k]
                b_high = highs[k]
                b_low = lows[k]
                k_atr = atrs[k - 1] if k > 0 else entry_atr
                k_range = candle_ranges[k - 1] if k > 0 else entry_range

                if sig == 1:
                    # Long checks:
                    # Gap check at open
                    gap_stop = (k > entry_idx) and (b_open <= sl_barrier)
                    gap_target = (k > entry_idx) and (b_open >= pt_barrier)

                    touch_target = b_high >= pt_barrier
                    touch_stop = b_low <= sl_barrier

                    if gap_stop:
                        exit_reason = "STOP"
                        exit_bar_idx = k
                        exit_bid = b_open  # Fills at gap open price
                        is_gap = True
                    elif gap_target:
                        exit_reason = "TARGET"
                        exit_bar_idx = k
                        exit_bid = b_open  # Fills at gap open price
                        is_gap = True
                    elif touch_target and touch_stop:
                        is_ambiguous = True
                        exit_reason = "STOP" if self.conservative_stop_first else "TARGET"
                        exit_bar_idx = k
                        exit_bid = sl_barrier if exit_reason == "STOP" else pt_barrier
                    elif touch_stop:
                        exit_reason = "STOP"
                        exit_bar_idx = k
                        exit_bid = sl_barrier
                    elif touch_target:
                        exit_reason = "TARGET"
                        exit_bar_idx = k
                        exit_bid = pt_barrier

                    if exit_reason is not None:
                        # Exit: Long sells at Bid - Slippage
                        exit_slippage = self.cost_model.calculate_slippage(
                            candle_range=k_range,
                            baseline_candle_range=self.baseline_candle_range,
                        )
                        exit_spread = 0.0
                        break

                else:
                    # Short checks:
                    gap_stop = (k > entry_idx) and (b_open >= sl_barrier)
                    gap_target = (k > entry_idx) and (b_open <= pt_barrier)

                    touch_target = b_low <= pt_barrier
                    touch_stop = b_high >= sl_barrier

                    if gap_stop:
                        exit_reason = "STOP"
                        exit_bar_idx = k
                        exit_bid = b_open
                        is_gap = True
                    elif gap_target:
                        exit_reason = "TARGET"
                        exit_bar_idx = k
                        exit_bid = b_open
                        is_gap = True
                    elif touch_target and touch_stop:
                        is_ambiguous = True
                        exit_reason = "STOP" if self.conservative_stop_first else "TARGET"
                        exit_bar_idx = k
                        exit_bid = sl_barrier if exit_reason == "STOP" else pt_barrier
                    elif touch_stop:
                        exit_reason = "STOP"
                        exit_bar_idx = k
                        exit_bid = sl_barrier
                    elif touch_target:
                        exit_reason = "TARGET"
                        exit_bar_idx = k
                        exit_bid = pt_barrier

                    if exit_reason is not None:
                        # Exit: Short buys at Ask = Bid + Spread + Slippage
                        exit_spread = self.cost_model.calculate_effective_spread(
                            timestamp=bar_ts,
                            current_atr=k_atr,
                            baseline_atr=self.baseline_atr,
                        )
                        exit_slippage = self.cost_model.calculate_slippage(
                            candle_range=k_range,
                            baseline_candle_range=self.baseline_candle_range,
                        )
                        break

            if weekend_aborted:
                n_closure_rejected += 1
                continue

            # Vertical Time-Limit Exit
            if exit_reason is None:
                exit_reason = "TIME_LIMIT"
                exit_bar_idx = min(n_rows - 1, entry_idx + H_max)
                exit_ts = timestamps.iloc[exit_bar_idx]
                exit_bid = opens[exit_bar_idx]
                t_atr = atrs[exit_bar_idx - 1]
                t_range = candle_ranges[exit_bar_idx - 1]

                if sig == 1:
                    exit_spread = 0.0
                    exit_slippage = self.cost_model.calculate_slippage(t_range, self.baseline_candle_range)
                else:
                    exit_spread = self.cost_model.calculate_effective_spread(exit_ts, t_atr, self.baseline_atr)
                    exit_slippage = self.cost_model.calculate_slippage(t_range, self.baseline_candle_range)

            # Check market closure at exit
            if market_closed_series[exit_bar_idx]:
                n_closure_rejected += 1
                continue

            # Compute execution fills and PnL
            bars_held = max(1, exit_bar_idx - entry_idx)

            if sig == 1:
                # Long: Exit fill = Bid - Slippage
                exit_fill = exit_bid - exit_slippage
                total_friction = entry_spread_stored + entry_slippage + exit_slippage + comm_round_turn
                gross_pnl = exit_bid - entry_bid
                net_pnl = gross_pnl - total_friction
                gross_ret = gross_pnl / entry_bid
                net_ret = net_pnl / entry_fill
            else:
                # Short: Exit fill = Ask = Bid + Spread + Slippage
                exit_fill = exit_bid + exit_spread + exit_slippage
                total_friction = exit_spread + entry_slippage + exit_slippage + comm_round_turn
                gross_pnl = entry_bid - exit_bid
                net_pnl = gross_pnl - total_friction
                gross_ret = gross_pnl / entry_bid
                net_ret = net_pnl / entry_fill

            trade = TripleBarrierTrade(
                signal_index=i,
                signal_timestamp=timestamps.iloc[i],
                direction=sig,
                entry_index=entry_idx,
                entry_timestamp=entry_ts,
                entry_bid=entry_bid,
                entry_fill=entry_fill,
                entry_spread=entry_spread_stored,
                entry_slippage=entry_slippage,
                exit_index=exit_bar_idx,
                exit_timestamp=timestamps.iloc[exit_bar_idx],
                exit_bid=exit_bid,
                exit_fill=exit_fill,
                exit_spread=exit_spread,
                exit_slippage=exit_slippage,
                exit_reason=exit_reason,
                bars_held=bars_held,
                commission=comm_round_turn,
                total_friction=total_friction,
                gross_pnl=gross_pnl,
                net_pnl=net_pnl,
                gross_return=gross_ret,
                net_return=net_ret,
                is_gap_exit=is_gap,
                is_ambiguous_same_bar=is_ambiguous,
            )
            trades.append(trade)

            # Update concurrency & lockout
            concurrent_positions[entry_idx:exit_bar_idx + 1] += 1
            if self.mode == "non_overlapping":
                active_until_bar = exit_bar_idx

        # -------------------------------------------------------------
        # Aggregate Performance Metrics
        # -------------------------------------------------------------
        n_completed = len(trades)
        bars_in_market = int(np.sum(concurrent_positions > 0))
        market_exposure_pct = float(bars_in_market / tradable_bars * 100.0) if tradable_bars > 0 else 0.0
        max_concurrent = int(np.max(concurrent_positions)) if len(concurrent_positions) > 0 else 0
        avg_concurrent = float(np.mean(concurrent_positions)) if len(concurrent_positions) > 0 else 0.0
        trade_freq_pct = float(n_completed / tradable_bars * 100.0) if tradable_bars > 0 else 0.0
        drawdown_desc = "Nominal peak-to-trough drop ($/oz) under 1-oz position sizing"

        if n_completed == 0:
            return (
                TripleBarrierMetrics(
                    strategy_name=strategy_name,
                    scenario_name=scenario_name,
                    total_bars=n_rows,
                    tradable_bars=tradable_bars,
                    n_eligible_signals=n_eligible_signals,
                    n_executed_entries=0,
                    n_completed_trades=0,
                    n_capacity_rejected=n_capacity_rejected,
                    n_closure_rejected=n_closure_rejected,
                    trade_frequency_pct=0.0,
                    market_exposure_pct=0.0,
                    max_concurrent_positions=0,
                    avg_concurrent_positions=0.0,
                    avg_bars_held=0.0,
                    n_target_hits=0,
                    n_stop_hits=0,
                    n_time_limit_exits=0,
                    pct_target_hits=0.0,
                    pct_stop_hits=0.0,
                    pct_time_limit=0.0,
                    gross_pnl_usd=0.0,
                    net_pnl_usd=0.0,
                    total_spread_usd=0.0,
                    total_slippage_usd=0.0,
                    total_commission_usd=0.0,
                    total_friction_usd=0.0,
                    avg_net_pnl_per_trade=0.0,
                    median_net_pnl_per_trade=0.0,
                    avg_gross_return_bps=0.0,
                    avg_net_return_bps=0.0,
                    win_rate_gross=0.0,
                    win_rate_net=0.0,
                    profit_factor_gross=0.0,
                    profit_factor_net=0.0,
                    max_drawdown_usd=0.0,
                    drawdown_convention=drawdown_desc,
                    long_trades=0,
                    long_gross_pnl=0.0,
                    long_net_pnl=0.0,
                    long_win_rate_net=0.0,
                    short_trades=0,
                    short_gross_pnl=0.0,
                    short_net_pnl=0.0,
                    short_win_rate_net=0.0,
                ),
                trades,
            )

        gross_pnls = np.array([t.gross_pnl for t in trades], dtype=float)
        net_pnls = np.array([t.net_pnl for t in trades], dtype=float)
        gross_rets = np.array([t.gross_return for t in trades], dtype=float)
        net_rets = np.array([t.net_return for t in trades], dtype=float)
        frictions = np.array([t.total_friction for t in trades], dtype=float)
        spreads = np.array([t.entry_spread + t.exit_spread for t in trades], dtype=float)
        slippages = np.array([t.entry_slippage + t.exit_slippage for t in trades], dtype=float)
        commissions = np.array([t.commission for t in trades], dtype=float)
        directions = np.array([t.direction for t in trades], dtype=int)
        bars_held_arr = np.array([t.bars_held for t in trades], dtype=float)

        gross_pnl_usd = float(np.sum(gross_pnls))
        net_pnl_usd = float(np.sum(net_pnls))
        total_spread_usd = float(np.sum(spreads))
        total_slippage_usd = float(np.sum(slippages))
        total_commission_usd = float(np.sum(commissions))
        total_friction_usd = float(np.sum(frictions))

        avg_gross_return_bps = float(np.mean(gross_rets) * 10_000)
        avg_net_return_bps = float(np.mean(net_rets) * 10_000)
        avg_net_pnl_per_trade = float(np.mean(net_pnls))
        median_net_pnl_per_trade = float(np.median(net_pnls))
        avg_bars_held = float(np.mean(bars_held_arr))

        win_rate_gross = float(np.mean(gross_pnls > 0))
        win_rate_net = float(np.mean(net_pnls > 0))

        gross_wins = np.sum(gross_pnls[gross_pnls > 0])
        gross_losses = np.abs(np.sum(gross_pnls[gross_pnls < 0]))
        profit_factor_gross = float(gross_wins / gross_losses) if gross_losses > 0 else (100.0 if gross_wins > 0 else 0.0)

        net_wins = np.sum(net_pnls[net_pnls > 0])
        net_losses = np.abs(np.sum(net_pnls[net_pnls < 0]))
        profit_factor_net = float(net_wins / net_losses) if net_losses > 0 else (100.0 if net_wins > 0 else 0.0)

        # Drawdown calculation
        cum_net = np.cumsum(net_pnls)
        running_max = np.maximum.accumulate(cum_net)
        drawdowns = running_max - cum_net
        max_dd_usd = float(np.max(drawdowns)) if len(drawdowns) > 0 else 0.0

        # Exit reasons breakdown
        reasons = [t.exit_reason for t in trades]
        n_targets = int(np.sum([r == "TARGET" for r in reasons]))
        n_stops = int(np.sum([r == "STOP" for r in reasons]))
        n_times = int(np.sum([r == "TIME_LIMIT" for r in reasons]))

        # Long vs Short
        long_mask = directions == 1
        short_mask = directions == -1
        long_cnt = int(np.sum(long_mask))
        short_cnt = int(np.sum(short_mask))

        long_gross = float(np.sum(gross_pnls[long_mask])) if long_cnt > 0 else 0.0
        long_net = float(np.sum(net_pnls[long_mask])) if long_cnt > 0 else 0.0
        long_win_net = float(np.mean(net_pnls[long_mask] > 0)) if long_cnt > 0 else 0.0

        short_gross = float(np.sum(gross_pnls[short_mask])) if short_cnt > 0 else 0.0
        short_net = float(np.sum(net_pnls[short_mask])) if short_cnt > 0 else 0.0
        short_win_net = float(np.mean(net_pnls[short_mask] > 0)) if short_cnt > 0 else 0.0

        metrics = TripleBarrierMetrics(
            strategy_name=strategy_name,
            scenario_name=scenario_name,
            total_bars=n_rows,
            tradable_bars=tradable_bars,
            n_eligible_signals=n_eligible_signals,
            n_executed_entries=n_completed,
            n_completed_trades=n_completed,
            n_capacity_rejected=n_capacity_rejected,
            n_closure_rejected=n_closure_rejected,
            trade_frequency_pct=trade_freq_pct,
            market_exposure_pct=market_exposure_pct,
            max_concurrent_positions=max_concurrent,
            avg_concurrent_positions=avg_concurrent,
            avg_bars_held=avg_bars_held,
            n_target_hits=n_targets,
            n_stop_hits=n_stops,
            n_time_limit_exits=n_times,
            pct_target_hits=float(n_targets / n_completed),
            pct_stop_hits=float(n_stops / n_completed),
            pct_time_limit=float(n_times / n_completed),
            gross_pnl_usd=gross_pnl_usd,
            net_pnl_usd=net_pnl_usd,
            total_spread_usd=total_spread_usd,
            total_slippage_usd=total_slippage_usd,
            total_commission_usd=total_commission_usd,
            total_friction_usd=total_friction_usd,
            avg_net_pnl_per_trade=avg_net_pnl_per_trade,
            median_net_pnl_per_trade=median_net_pnl_per_trade,
            avg_gross_return_bps=avg_gross_return_bps,
            avg_net_return_bps=avg_net_return_bps,
            win_rate_gross=win_rate_gross,
            win_rate_net=win_rate_net,
            profit_factor_gross=profit_factor_gross,
            profit_factor_net=profit_factor_net,
            max_drawdown_usd=max_dd_usd,
            drawdown_convention=drawdown_desc,
            long_trades=long_cnt,
            long_gross_pnl=long_gross,
            long_net_pnl=long_net,
            long_win_rate_net=long_win_net,
            short_trades=short_cnt,
            short_gross_pnl=short_gross,
            short_net_pnl=short_net,
            short_win_rate_net=short_win_net,
        )
        return metrics, trades

    @staticmethod
    def compute_aggregate_metrics(
        trades: List[TripleBarrierTrade],
        total_bars: int = 0,
        tradable_bars: int = 0,
        n_eligible_signals: int = 0,
        n_capacity_rejected: int = 0,
        n_closure_rejected: int = 0,
        strategy_name: str = "AggregatedStrategy",
        scenario_name: str = "Baseline Costs",
    ) -> TripleBarrierMetrics:
        """Compute aggregate backtest metrics across multiple walk-forward folds from trade records.

        Calculates portfolio metrics directly from underlying trade records rather than
        averaging fold-level profit factors.
        """
        n_completed = len(trades)
        drawdown_desc = "Nominal peak-to-trough drop ($/oz) under 1-oz position sizing"

        if n_completed == 0:
            return TripleBarrierMetrics(
                strategy_name=strategy_name,
                scenario_name=scenario_name,
                total_bars=total_bars,
                tradable_bars=tradable_bars,
                n_eligible_signals=n_eligible_signals,
                n_executed_entries=0,
                n_completed_trades=0,
                n_capacity_rejected=n_capacity_rejected,
                n_closure_rejected=n_closure_rejected,
                trade_frequency_pct=0.0,
                market_exposure_pct=0.0,
                max_concurrent_positions=0,
                avg_concurrent_positions=0.0,
                avg_bars_held=0.0,
                n_target_hits=0,
                n_stop_hits=0,
                n_time_limit_exits=0,
                pct_target_hits=0.0,
                pct_stop_hits=0.0,
                pct_time_limit=0.0,
                gross_pnl_usd=0.0,
                net_pnl_usd=0.0,
                total_spread_usd=0.0,
                total_slippage_usd=0.0,
                total_commission_usd=0.0,
                total_friction_usd=0.0,
                avg_net_pnl_per_trade=0.0,
                median_net_pnl_per_trade=0.0,
                avg_gross_return_bps=0.0,
                avg_net_return_bps=0.0,
                win_rate_gross=0.0,
                win_rate_net=0.0,
                profit_factor_gross=0.0,
                profit_factor_net=0.0,
                max_drawdown_usd=0.0,
                drawdown_convention=drawdown_desc,
                long_trades=0,
                long_gross_pnl=0.0,
                long_net_pnl=0.0,
                long_win_rate_net=0.0,
                short_trades=0,
                short_gross_pnl=0.0,
                short_net_pnl=0.0,
                short_win_rate_net=0.0,
            )

        gross_pnls = np.array([t.gross_pnl for t in trades], dtype=float)
        net_pnls = np.array([t.net_pnl for t in trades], dtype=float)
        gross_rets = np.array([t.gross_return for t in trades], dtype=float)
        net_rets = np.array([t.net_return for t in trades], dtype=float)
        frictions = np.array([t.total_friction for t in trades], dtype=float)
        spreads = np.array([t.entry_spread + t.exit_spread for t in trades], dtype=float)
        slippages = np.array([t.entry_slippage + t.exit_slippage for t in trades], dtype=float)
        commissions = np.array([t.commission for t in trades], dtype=float)
        directions = np.array([t.direction for t in trades], dtype=int)
        bars_held_arr = np.array([t.bars_held for t in trades], dtype=float)

        gross_pnl_usd = float(np.sum(gross_pnls))
        net_pnl_usd = float(np.sum(net_pnls))
        total_spread_usd = float(np.sum(spreads))
        total_slippage_usd = float(np.sum(slippages))
        total_commission_usd = float(np.sum(commissions))
        total_friction_usd = float(np.sum(frictions))

        avg_gross_return_bps = float(np.mean(gross_rets) * 10_000)
        avg_net_return_bps = float(np.mean(net_rets) * 10_000)
        avg_net_pnl_per_trade = float(np.mean(net_pnls))
        median_net_pnl_per_trade = float(np.median(net_pnls))
        avg_bars_held = float(np.mean(bars_held_arr))

        win_rate_gross = float(np.mean(gross_pnls > 0))
        win_rate_net = float(np.mean(net_pnls > 0))

        gross_wins = np.sum(gross_pnls[gross_pnls > 0])
        gross_losses = np.abs(np.sum(gross_pnls[gross_pnls < 0]))
        profit_factor_gross = float(gross_wins / gross_losses) if gross_losses > 0 else (100.0 if gross_wins > 0 else 0.0)

        net_wins = np.sum(net_pnls[net_pnls > 0])
        net_losses = np.abs(np.sum(net_pnls[net_pnls < 0]))
        profit_factor_net = float(net_wins / net_losses) if net_losses > 0 else (100.0 if net_wins > 0 else 0.0)

        cum_net = np.cumsum(net_pnls)
        running_max = np.maximum.accumulate(cum_net)
        drawdowns = running_max - cum_net
        max_dd_usd = float(np.max(drawdowns)) if len(drawdowns) > 0 else 0.0

        reasons = [t.exit_reason for t in trades]
        n_targets = int(np.sum([r == "TARGET" for r in reasons]))
        n_stops = int(np.sum([r == "STOP" for r in reasons]))
        n_times = int(np.sum([r == "TIME_LIMIT" for r in reasons]))

        long_mask = directions == 1
        short_mask = directions == -1
        long_cnt = int(np.sum(long_mask))
        short_cnt = int(np.sum(short_mask))

        long_gross = float(np.sum(gross_pnls[long_mask])) if long_cnt > 0 else 0.0
        long_net = float(np.sum(net_pnls[long_mask])) if long_cnt > 0 else 0.0
        long_win_net = float(np.mean(net_pnls[long_mask] > 0)) if long_cnt > 0 else 0.0

        short_gross = float(np.sum(gross_pnls[short_mask])) if short_cnt > 0 else 0.0
        short_net = float(np.sum(net_pnls[short_mask])) if short_cnt > 0 else 0.0
        short_win_net = float(np.mean(net_pnls[short_mask] > 0)) if short_cnt > 0 else 0.0

        trade_freq_pct = float(n_completed / tradable_bars * 100.0) if tradable_bars > 0 else 0.0

        return TripleBarrierMetrics(
            strategy_name=strategy_name,
            scenario_name=scenario_name,
            total_bars=total_bars,
            tradable_bars=tradable_bars,
            n_eligible_signals=n_eligible_signals,
            n_executed_entries=n_completed,
            n_completed_trades=n_completed,
            n_capacity_rejected=n_capacity_rejected,
            n_closure_rejected=n_closure_rejected,
            trade_frequency_pct=trade_freq_pct,
            market_exposure_pct=0.0,
            max_concurrent_positions=1,
            avg_concurrent_positions=0.0,
            avg_bars_held=avg_bars_held,
            n_target_hits=n_targets,
            n_stop_hits=n_stops,
            n_time_limit_exits=n_times,
            pct_target_hits=float(n_targets / n_completed),
            pct_stop_hits=float(n_stops / n_completed),
            pct_time_limit=float(n_times / n_completed),
            gross_pnl_usd=gross_pnl_usd,
            net_pnl_usd=net_pnl_usd,
            total_spread_usd=total_spread_usd,
            total_slippage_usd=total_slippage_usd,
            total_commission_usd=total_commission_usd,
            total_friction_usd=total_friction_usd,
            avg_net_pnl_per_trade=avg_net_pnl_per_trade,
            median_net_pnl_per_trade=median_net_pnl_per_trade,
            avg_gross_return_bps=avg_gross_return_bps,
            avg_net_return_bps=avg_net_return_bps,
            win_rate_gross=win_rate_gross,
            win_rate_net=win_rate_net,
            profit_factor_gross=profit_factor_gross,
            profit_factor_net=profit_factor_net,
            max_drawdown_usd=max_dd_usd,
            drawdown_convention=drawdown_desc,
            long_trades=long_cnt,
            long_gross_pnl=long_gross,
            long_net_pnl=long_net,
            long_win_rate_net=long_win_net,
            short_trades=short_cnt,
            short_gross_pnl=short_gross,
            short_net_pnl=short_net,
            short_win_rate_net=short_win_net,
        )
