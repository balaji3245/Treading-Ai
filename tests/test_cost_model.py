"""Unit tests for configurable ExecutionCostModel."""

from datetime import datetime, timezone
import pytest
import pandas as pd

from treading_ai.backtesting.cost_model import ExecutionCostModel, TradeExecution


def test_cost_model_session_spreads():
    model = ExecutionCostModel(base_spread_usd=0.20)

    # 1. London/NY overlap (14:30 UTC): base multiplier 1.0 -> spread = $0.20
    t_overlap = pd.Timestamp("2026-01-07 14:30:00", tz="UTC")
    spread_overlap = model.calculate_effective_spread(t_overlap)
    assert spread_overlap == 0.20

    # 2. Asian session (03:00 UTC): multiplier 1.8 -> spread = $0.36
    t_asian = pd.Timestamp("2026-01-07 03:00:00", tz="UTC")
    spread_asian = model.calculate_effective_spread(t_asian)
    assert spread_asian == 0.36

    # 3. Roll break window (21:50 UTC): multiplier 12.0 -> spread = $2.40
    t_roll = pd.Timestamp("2026-01-07 21:50:00", tz="UTC")
    spread_roll = model.calculate_effective_spread(t_roll)
    assert spread_roll == 2.40


def test_cost_model_volatility_scaling():
    model = ExecutionCostModel(
        base_spread_usd=0.20,
        enable_volatility_scaling=True,
        volatility_spread_factor=0.5,
    )
    t = pd.Timestamp("2026-01-07 14:30:00", tz="UTC")

    # Double volatility (ATR = 2.0 vs baseline 1.0)
    # vol_ratio = 2.0 -> spread = 0.20 * (1 + 0.5 * 1.0) = 0.30
    spread_high_vol = model.calculate_effective_spread(t, current_atr=2.0, baseline_atr=1.0)
    assert spread_high_vol == 0.30


def test_cost_model_execution_fills():
    model = ExecutionCostModel(
        base_spread_usd=0.20,
        base_slippage_usd=0.05,
        commission_per_lot_usd=5.0,  # $0.05 / oz
    )
    t = pd.Timestamp("2026-01-07 14:00:00", tz="UTC")
    bid = 2650.00

    # BUY order: Ask = Bid + Spread ($0.20) + Slippage ($0.05) = 2650.25
    exec_buy = model.simulate_execution("BUY", bid_price=bid, timestamp=t)
    assert exec_buy.is_tradable is True
    assert exec_buy.action == "BUY"
    assert exec_buy.fill_price == 2650.25
    assert exec_buy.effective_spread == 0.20
    assert exec_buy.slippage == 0.05
    assert exec_buy.commission_per_oz == 0.05
    assert exec_buy.total_friction_per_oz == 0.30

    # SELL order: Execution = Bid - Slippage ($0.05) = 2649.95
    exec_sell = model.simulate_execution("SELL", bid_price=bid, timestamp=t)
    assert exec_sell.is_tradable is True
    assert exec_sell.action == "SELL"
    assert exec_sell.fill_price == 2649.95
    assert exec_sell.total_friction_per_oz == 0.10


def test_cost_model_rejects_closed_market():
    model = ExecutionCostModel()
    t_closed = pd.Timestamp("2026-01-07 22:30:00", tz="UTC")
    exec_closed = model.simulate_execution("BUY", bid_price=2650.00, timestamp=t_closed)

    assert exec_closed.is_tradable is False
    assert "Market closed" in exec_closed.rejection_reason
