"""Economic Backtesting Engine for Financial Signal Evaluation.

Strict Execution Causality & Cost Modeling:
- Signal timing: Prediction finalized at bar t close (index i).
- Entry timing: Order executes at bar t+1 Open (index i+1).
  Volatility inputs (ATR, candle range) finalized on or before bar t.
- Exit timing: Order executes at bar t+1+H Open (index i+1+H).
  Volatility inputs finalized on or before bar t+H.
- Market Closures: No fills permitted during Daily Rollover (Mon-Thu 17:00-18:00 NY)
  or Weekend Closure (Fri 17:00 NY to Sun 18:00 NY).
- Pricing Convention: Institutional spot gold bid-only approximation.
- Harsher cost sensitivity scenario: 2x spread and 2x slippage.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from treading_ai.backtesting.cost_model import ExecutionCostModel


@dataclass(frozen=True)
class TradeRecord:
    """Detailed record of a single simulated trade."""
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
    commission: float
    total_friction: float
    gross_pnl: float
    net_pnl: float
    gross_return: float
    net_return: float
    holding_bars: int


@dataclass(frozen=True)
class EconomicMetrics:
    """Comprehensive summary metrics of financial and economic backtest performance.

    All PnL and friction values are denominated in USD per troy ounce ($/oz)
    for spot gold (XAUUSD) based on 1-oz unit position sizing.
    """
    model_name: str
    scenario_name: str  # e.g. "Baseline Costs" or "Harsher Costs (2x)"
    total_bars: int
    tradable_bars: int
    # Signal and trade counts
    n_eligible_signals: int  # non-zero candidate signals emitted
    n_executed_entries: int  # orders that successfully entered at t+1 Open
    n_completed_trades: int  # trades that reached exit at t+1+H Open
    n_trades_rejected_closure: int
    n_signals_long: int
    n_signals_short: int
    n_signals_neutral: int
    # Exposure & frequency
    trade_frequency_pct: float  # completed trades / tradable bars
    market_exposure_pct: float  # % of bars with active market exposure
    max_concurrent_positions: int
    avg_concurrent_positions: float
    coverage_ratio: float  # executed trades / tradable bars
    # PnL metrics ($/oz)
    gross_pnl_usd: float  # cumulative $/oz
    net_pnl_usd: float    # cumulative $/oz
    # Cost breakdowns ($/oz)
    total_spread_usd: float
    total_slippage_usd: float
    total_commission_usd: float
    total_friction_usd: float
    # Per-trade metrics
    avg_gross_return_bps: float
    avg_net_return_bps: float
    avg_net_pnl_per_trade: float  # $/oz
    median_net_pnl_per_trade: float  # $/oz
    # Risk and ratios
    win_rate_gross: float
    win_rate_net: float
    profit_factor_gross: float
    profit_factor_net: float
    max_drawdown_usd: float  # $/oz peak-to-trough
    max_drawdown_pct: float  # relative to mean gold price
    drawdown_convention: str
    turnover_lots: float
    # Long vs Short breakdown
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
            "model_name": self.model_name,
            "scenario_name": self.scenario_name,
            "total_bars": self.total_bars,
            "tradable_bars": self.tradable_bars,
            "n_eligible_signals": self.n_eligible_signals,
            "n_executed_entries": self.n_executed_entries,
            "n_completed_trades": self.n_completed_trades,
            "n_trades_rejected_closure": self.n_trades_rejected_closure,
            "n_signals_long": self.n_signals_long,
            "n_signals_short": self.n_signals_short,
            "n_signals_neutral": self.n_signals_neutral,
            "trade_frequency_pct": self.trade_frequency_pct,
            "market_exposure_pct": self.market_exposure_pct,
            "max_concurrent_positions": self.max_concurrent_positions,
            "avg_concurrent_positions": self.avg_concurrent_positions,
            "coverage_ratio": self.coverage_ratio,
            "gross_pnl_usd": self.gross_pnl_usd,
            "net_pnl_usd": self.net_pnl_usd,
            "total_spread_usd": self.total_spread_usd,
            "total_slippage_usd": self.total_slippage_usd,
            "total_commission_usd": self.total_commission_usd,
            "total_friction_usd": self.total_friction_usd,
            "avg_gross_return_bps": self.avg_gross_return_bps,
            "avg_net_return_bps": self.avg_net_return_bps,
            "avg_net_pnl_per_trade": self.avg_net_pnl_per_trade,
            "median_net_pnl_per_trade": self.median_net_pnl_per_trade,
            "win_rate_gross": self.win_rate_gross,
            "win_rate_net": self.win_rate_net,
            "profit_factor_gross": self.profit_factor_gross,
            "profit_factor_net": self.profit_factor_net,
            "max_drawdown_usd": self.max_drawdown_usd,
            "max_drawdown_pct": self.max_drawdown_pct,
            "drawdown_convention": self.drawdown_convention,
            "turnover_lots": self.turnover_lots,
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
        """Formatted summary table representation."""
        lines = [
            f"=== Economic Backtest: {self.model_name} [{self.scenario_name}] ===",
            f"Signals: Eligible={self.n_eligible_signals:,} | Executed Entries={self.n_executed_entries:,} | Completed Trades={self.n_completed_trades:,} | Rejected Closures={self.n_trades_rejected_closure:,}",
            f"Exposure: Market Exposure={self.market_exposure_pct:.2f}% | Max Concurrent={self.max_concurrent_positions} | Avg Concurrent={self.avg_concurrent_positions:.2f} | Trade Freq={self.trade_frequency_pct:.2f}%",
            f"Gross PnL: ${self.gross_pnl_usd:+,.2f}/oz | Net PnL: ${self.net_pnl_usd:+,.2f}/oz | Total Friction: ${self.total_friction_usd:,.2f}/oz",
            f"Friction Breakdown: Spread=${self.total_spread_usd:,.2f}/oz | Slippage=${self.total_slippage_usd:,.2f}/oz | Comm=${self.total_commission_usd:,.2f}/oz",
            f"Per-Trade Net PnL: Mean=${self.avg_net_pnl_per_trade:+,.3f}/oz ({self.avg_net_return_bps:+,.2f} bps) | Median=${self.median_net_pnl_per_trade:+,.3f}/oz",
            f"Win Rate (Net): {self.win_rate_net:.2%} (Gross: {self.win_rate_gross:.2%})",
            f"Profit Factor (Net): {self.profit_factor_net:.3f} (Gross: {self.profit_factor_gross:.3f})",
            f"Max Drawdown: -${self.max_drawdown_usd:,.2f}/oz ({self.drawdown_convention})",
            f"Long Side Net PnL: ${self.long_net_pnl:+,.2f}/oz (Win: {self.long_win_rate_net:.2%}, Trades: {self.long_trades:,})",
            f"Short Side Net PnL: ${self.short_net_pnl:+,.2f}/oz (Win: {self.short_win_rate_net:.2%}, Trades: {self.short_trades:,})",
        ]
        return "\n".join(lines)


class EconomicEvaluator:
    """Simulates economic performance with strict pre-trade causality and bid-only pricing.

    Parameters
    ----------
    cost_model : ExecutionCostModel
        Execution cost model simulating dynamic spread, slippage, and commission.
    horizon : int, default=6
        Holding period in bars.
    baseline_atr : float, default=1.153
        Fixed baseline ATR for volatility scaling.
    baseline_candle_range : float, default=1.050
        Fixed baseline candle range for slippage scaling.
    """

    def __init__(
        self,
        cost_model: Optional[ExecutionCostModel] = None,
        horizon: int = 6,
        baseline_atr: float = 1.153,
        baseline_candle_range: float = 1.050,
    ) -> None:
        self.cost_model = cost_model or ExecutionCostModel()
        self.horizon = horizon
        self.baseline_atr = baseline_atr
        self.baseline_candle_range = baseline_candle_range

    def evaluate(
        self,
        df: pd.DataFrame,
        signals: Union[np.ndarray, pd.Series],
        model_name: str = "Model",
        scenario_name: str = "Baseline Costs",
        mask: Optional[Union[np.ndarray, pd.Series]] = None,
    ) -> Tuple[EconomicMetrics, List[TradeRecord]]:
        r"""Simulate trades and compute economic performance metrics.

        Parameters
        ----------
        df : pd.DataFrame
            Underlying OHLC dataframe with timestamps and volatility metrics.
            Must contain ['timestamp', 'open', 'high', 'low', 'close'].
        signals : Union[np.ndarray, pd.Series]
            Predictions $\in \{-1, 0, 1\}$ corresponding to rows of df (or rows where mask is True).
        model_name : str
            Identifier for the model.
        scenario_name : str
            Cost scenario label.
        mask : Optional[Union[np.ndarray, pd.Series]]
            Boolean filter for evaluation rows (e.g. valid non-purged rows).
        """
        if mask is not None:
            mask_arr = np.asarray(mask, dtype=bool)
            full_signals = np.zeros(len(df), dtype=int)
            full_signals[mask_arr] = np.asarray(signals, dtype=int)
        else:
            full_signals = np.asarray(signals, dtype=int)

        n_rows = len(df)
        if len(full_signals) != n_rows:
            raise ValueError(f"Signal length ({len(full_signals)}) does not match DataFrame rows ({n_rows}).")

        timestamps = pd.to_datetime(df["timestamp"], utc=True)
        opens = df["open"].to_numpy(dtype=float)
        highs = df["high"].to_numpy(dtype=float)
        lows = df["low"].to_numpy(dtype=float)

        if "atr_14" in df.columns:
            atrs = df["atr_14"].to_numpy(dtype=float)
        else:
            ranges = highs - lows
            atrs = pd.Series(ranges).rolling(14, min_periods=1).mean().to_numpy()

        ranges = highs - lows

        trades: List[TradeRecord] = []
        n_rejected_closure = 0
        n_eligible_signals = int(np.sum(full_signals != 0))
        n_long_signals = int(np.sum(full_signals == 1))
        n_short_signals = int(np.sum(full_signals == -1))
        n_neutral_signals = int(np.sum(full_signals == 0))

        H = self.horizon
        tradable_bars = max(0, n_rows - (1 + H))

        # Vectorized market closure lookup for speed
        market_closed_series = self.cost_model.is_market_closed_series(timestamps)

        # Track concurrent active positions per bar
        concurrent_positions = np.zeros(n_rows, dtype=int)

        for i in range(n_rows):
            sig = full_signals[i]
            if sig == 0:
                continue

            # Boundary overflow: Cannot enter or exit within split
            if i + 1 + H >= n_rows:
                continue

            entry_idx = i + 1
            exit_idx = i + 1 + H

            # Reject trades attempting to execute during market closure
            if market_closed_series[entry_idx] or market_closed_series[exit_idx]:
                n_rejected_closure += 1
                continue

            # Record active position occupancy from entry to exit
            concurrent_positions[entry_idx:exit_idx] += 1

            # Pre-trade causal volatility metrics:
            entry_atr = atrs[i]
            entry_range = ranges[i]
            exit_atr = atrs[i + H]
            exit_range = ranges[i + H]

            entry_bid = opens[entry_idx]
            exit_bid = opens[exit_idx]
            entry_ts = timestamps.iloc[entry_idx]
            exit_ts = timestamps.iloc[exit_idx]

            comm_per_oz = self.cost_model.commission_per_oz
            comm_round_turn = 2.0 * comm_per_oz

            if sig == 1:
                # LONG TRADE:
                # Entry: Buy at Ask = Bid + Spread + Slippage
                entry_spread = self.cost_model.calculate_effective_spread(
                    timestamp=entry_ts,
                    current_atr=entry_atr,
                    baseline_atr=self.baseline_atr,
                )
                entry_slippage = self.cost_model.calculate_slippage(
                    candle_range=entry_range,
                    baseline_candle_range=self.baseline_candle_range,
                )
                entry_fill = entry_bid + entry_spread + entry_slippage

                # Exit: Sell at Bid = Bid - Slippage
                exit_spread = 0.0
                exit_slippage = self.cost_model.calculate_slippage(
                    candle_range=exit_range,
                    baseline_candle_range=self.baseline_candle_range,
                )
                exit_fill = exit_bid - exit_slippage

                total_friction = entry_spread + entry_slippage + exit_slippage + comm_round_turn
                gross_pnl = exit_bid - entry_bid
                net_pnl = gross_pnl - total_friction
                gross_ret = gross_pnl / entry_bid
                net_ret = net_pnl / entry_fill

            else:
                # SHORT TRADE:
                # Entry: Sell at Bid = Bid - Slippage
                entry_spread = 0.0
                entry_slippage = self.cost_model.calculate_slippage(
                    candle_range=entry_range,
                    baseline_candle_range=self.baseline_candle_range,
                )
                entry_fill = entry_bid - entry_slippage

                # Exit: Buy at Ask = Bid + Spread + Slippage
                exit_spread = self.cost_model.calculate_effective_spread(
                    timestamp=exit_ts,
                    current_atr=exit_atr,
                    baseline_atr=self.baseline_atr,
                )
                exit_slippage = self.cost_model.calculate_slippage(
                    candle_range=exit_range,
                    baseline_candle_range=self.baseline_candle_range,
                )
                exit_fill = exit_bid + exit_spread + exit_slippage

                total_friction = exit_spread + entry_slippage + exit_slippage + comm_round_turn
                gross_pnl = entry_bid - exit_bid
                net_pnl = gross_pnl - total_friction
                gross_ret = gross_pnl / entry_bid
                net_ret = net_pnl / entry_fill

            trade = TradeRecord(
                signal_index=i,
                signal_timestamp=timestamps.iloc[i],
                direction=sig,
                entry_index=entry_idx,
                entry_timestamp=entry_ts,
                entry_bid=entry_bid,
                entry_fill=entry_fill,
                entry_spread=entry_spread,
                entry_slippage=entry_slippage,
                exit_index=exit_idx,
                exit_timestamp=exit_ts,
                exit_bid=exit_bid,
                exit_fill=exit_fill,
                exit_spread=exit_spread,
                exit_slippage=exit_slippage,
                commission=comm_round_turn,
                total_friction=total_friction,
                gross_pnl=gross_pnl,
                net_pnl=net_pnl,
                gross_return=gross_ret,
                net_return=net_ret,
                holding_bars=H,
            )
            trades.append(trade)

        n_completed = len(trades)
        n_executed_entries = n_completed  # In this execution model, validated entries execute and hold for H bars

        # Exposure and concurrency metrics
        bars_in_market = int(np.sum(concurrent_positions > 0))
        market_exposure_pct = float(bars_in_market / tradable_bars * 100.0) if tradable_bars > 0 else 0.0
        max_concurrent = int(np.max(concurrent_positions)) if len(concurrent_positions) > 0 else 0
        avg_concurrent = float(np.mean(concurrent_positions)) if len(concurrent_positions) > 0 else 0.0
        trade_freq_pct = float(n_completed / tradable_bars * 100.0) if tradable_bars > 0 else 0.0

        drawdown_desc = "Nominal peak-to-trough drop ($/oz) under 1-oz position sizing"

        if n_completed == 0:
            return (
                EconomicMetrics(
                    model_name=model_name,
                    scenario_name=scenario_name,
                    total_bars=n_rows,
                    tradable_bars=tradable_bars,
                    n_eligible_signals=n_eligible_signals,
                    n_executed_entries=0,
                    n_completed_trades=0,
                    n_trades_rejected_closure=n_rejected_closure,
                    n_signals_long=n_long_signals,
                    n_signals_short=n_short_signals,
                    n_signals_neutral=n_neutral_signals,
                    trade_frequency_pct=0.0,
                    market_exposure_pct=0.0,
                    max_concurrent_positions=0,
                    avg_concurrent_positions=0.0,
                    coverage_ratio=0.0,
                    gross_pnl_usd=0.0,
                    net_pnl_usd=0.0,
                    total_spread_usd=0.0,
                    total_slippage_usd=0.0,
                    total_commission_usd=0.0,
                    total_friction_usd=0.0,
                    avg_gross_return_bps=0.0,
                    avg_net_return_bps=0.0,
                    avg_net_pnl_per_trade=0.0,
                    median_net_pnl_per_trade=0.0,
                    win_rate_gross=0.0,
                    win_rate_net=0.0,
                    profit_factor_gross=0.0,
                    profit_factor_net=0.0,
                    max_drawdown_usd=0.0,
                    max_drawdown_pct=0.0,
                    drawdown_convention=drawdown_desc,
                    turnover_lots=0.0,
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

        win_rate_gross = float(np.mean(gross_pnls > 0))
        win_rate_net = float(np.mean(net_pnls > 0))

        gross_wins = np.sum(gross_pnls[gross_pnls > 0])
        gross_losses = np.abs(np.sum(gross_pnls[gross_pnls < 0]))
        profit_factor_gross = float(gross_wins / gross_losses) if gross_losses > 0 else (100.0 if gross_wins > 0 else 0.0)

        net_wins = np.sum(net_pnls[net_pnls > 0])
        net_losses = np.abs(np.sum(net_pnls[net_pnls < 0]))
        profit_factor_net = float(net_wins / net_losses) if net_losses > 0 else (100.0 if net_wins > 0 else 0.0)

        # Cumulative equity and drawdown ($/oz)
        cum_net = np.cumsum(net_pnls)
        running_max = np.maximum.accumulate(cum_net)
        drawdowns = running_max - cum_net
        max_dd_usd = float(np.max(drawdowns)) if len(drawdowns) > 0 else 0.0

        avg_price = float(np.mean(opens))
        max_dd_pct = float(max_dd_usd / avg_price * 100.0) if avg_price > 0 else 0.0

        turnover_lots = float(n_completed * 1.0)

        long_mask = directions == 1
        short_mask = directions == -1

        long_trades_cnt = int(np.sum(long_mask))
        short_trades_cnt = int(np.sum(short_mask))

        long_gross = float(np.sum(gross_pnls[long_mask])) if long_trades_cnt > 0 else 0.0
        long_net = float(np.sum(net_pnls[long_mask])) if long_trades_cnt > 0 else 0.0
        long_win_net = float(np.mean(net_pnls[long_mask] > 0)) if long_trades_cnt > 0 else 0.0

        short_gross = float(np.sum(gross_pnls[short_mask])) if short_trades_cnt > 0 else 0.0
        short_net = float(np.sum(net_pnls[short_mask])) if short_trades_cnt > 0 else 0.0
        short_win_net = float(np.mean(net_pnls[short_mask] > 0)) if short_trades_cnt > 0 else 0.0

        coverage_ratio = float(n_completed / tradable_bars) if tradable_bars > 0 else 0.0

        metrics = EconomicMetrics(
            model_name=model_name,
            scenario_name=scenario_name,
            total_bars=n_rows,
            tradable_bars=tradable_bars,
            n_eligible_signals=n_eligible_signals,
            n_executed_entries=n_executed_entries,
            n_completed_trades=n_completed,
            n_trades_rejected_closure=n_rejected_closure,
            n_signals_long=n_long_signals,
            n_signals_short=n_short_signals,
            n_signals_neutral=n_neutral_signals,
            trade_frequency_pct=trade_freq_pct,
            market_exposure_pct=market_exposure_pct,
            max_concurrent_positions=max_concurrent,
            avg_concurrent_positions=avg_concurrent,
            coverage_ratio=coverage_ratio,
            gross_pnl_usd=gross_pnl_usd,
            net_pnl_usd=net_pnl_usd,
            total_spread_usd=total_spread_usd,
            total_slippage_usd=total_slippage_usd,
            total_commission_usd=total_commission_usd,
            total_friction_usd=total_friction_usd,
            avg_gross_return_bps=avg_gross_return_bps,
            avg_net_return_bps=avg_net_return_bps,
            avg_net_pnl_per_trade=avg_net_pnl_per_trade,
            median_net_pnl_per_trade=median_net_pnl_per_trade,
            win_rate_gross=win_rate_gross,
            win_rate_net=win_rate_net,
            profit_factor_gross=profit_factor_gross,
            profit_factor_net=profit_factor_net,
            max_drawdown_usd=max_dd_usd,
            max_drawdown_pct=max_dd_pct,
            drawdown_convention=drawdown_desc,
            turnover_lots=turnover_lots,
            long_trades=long_trades_cnt,
            long_gross_pnl=long_gross,
            long_net_pnl=long_net,
            long_win_rate_net=long_win_net,
            short_trades=short_trades_cnt,
            short_gross_pnl=short_gross,
            short_net_pnl=short_net,
            short_win_rate_net=short_win_net,
        )
        return metrics, trades
