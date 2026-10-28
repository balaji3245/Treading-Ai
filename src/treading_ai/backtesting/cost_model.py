"""Configurable transaction cost, dynamic spread, slippage, and commission model.

Addresses bid-only price limitations in historical raw market data by providing
statistically grounded, regime-aware execution simulation for XAUUSD spot gold.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional, Union
import pandas as pd


@dataclass(frozen=True)
class TradeExecution:
    """Details of an executed simulated order."""
    action: str  # 'BUY' or 'SELL'
    nominal_bid: float
    effective_spread: float
    slippage: float
    commission_per_oz: float
    fill_price: float
    total_friction_per_oz: float
    timestamp: pd.Timestamp
    is_tradable: bool
    rejection_reason: Optional[str] = None


class ExecutionCostModel:
    """Configurable execution cost simulator for spot gold (XAUUSD).

    Replaces unrealistic constant-spread assumptions with session-aware,
    volatility-dependent dynamic spreads and execution slippage.
    """

    def __init__(
        self,
        base_spread_usd: float = 0.20,
        commission_per_lot_usd: float = 5.0,  # 1 standard lot = 100 oz ($0.05/oz)
        lot_size_oz: float = 100.0,
        base_slippage_usd: float = 0.05,
        enable_volatility_scaling: bool = True,
        volatility_spread_factor: float = 0.5,
        session_multipliers: Optional[Dict[str, float]] = None,
    ):
        """Initialize the execution cost model.

        Parameters
        ----------
        base_spread_usd : float
            Baseline bid-ask spread in USD during peak liquidity (e.g. $0.20/oz).
        commission_per_lot_usd : float
            Broker round-turn commission per 100 oz standard lot.
        lot_size_oz : float
            Ounces per lot (standard XAUUSD lot is 100 oz).
        base_slippage_usd : float
            Base execution slippage in USD per oz.
        enable_volatility_scaling : bool
            Whether to widen spreads and increase slippage during elevated volatility.
        volatility_spread_factor : float
            Sensitivity multiplier for volatility widening.
        session_multipliers : Optional[Dict[str, float]]
            Custom regime multipliers per trading session.
        """
        self.base_spread_usd = base_spread_usd
        self.commission_per_lot_usd = commission_per_lot_usd
        self.lot_size_oz = lot_size_oz
        self.commission_per_oz = commission_per_lot_usd / lot_size_oz
        self.base_slippage_usd = base_slippage_usd
        self.enable_volatility_scaling = enable_volatility_scaling
        self.volatility_spread_factor = volatility_spread_factor

        self.session_multipliers = session_multipliers or {
            "LONDON_NY_OVERLAP": 1.0,   # 13:00 to 17:00 UTC (Peak liquidity)
            "LONDON_MORNING": 1.15,     # 07:00 to 13:00 UTC
            "NY_AFTERNOON": 1.30,       # 17:00 to 21:00 UTC
            "ASIAN_SESSION": 1.80,      # 00:00 to 07:00 UTC (Lower liquidity)
            "DAILY_ROLL_BREAK": 12.0,   # 21:45 to 23:15 UTC (Illiquid roll / wide blowout)
        }

    def get_session_name(self, timestamp: Union[datetime, pd.Timestamp]) -> str:
        """Classify UTC timestamp into spot market session."""
        if not hasattr(timestamp, "tzinfo") or timestamp.tzinfo is None:
            ts_utc = pd.to_datetime(timestamp, utc=True)
        else:
            ts_utc = timestamp.astimezone(timezone.utc)

        hour = ts_utc.hour
        minute = ts_utc.minute

        # Daily roll window: 21:45 to 23:15 UTC
        if (hour == 21 and minute >= 45) or (hour == 22) or (hour == 23 and minute <= 15):
            return "DAILY_ROLL_BREAK"
        elif 13 <= hour < 17:
            return "LONDON_NY_OVERLAP"
        elif 7 <= hour < 13:
            return "LONDON_MORNING"
        elif 17 <= hour < 21:
            return "NY_AFTERNOON"
        else:
            return "ASIAN_SESSION"

    def calculate_effective_spread(
        self,
        timestamp: Union[datetime, pd.Timestamp],
        current_atr: Optional[float] = None,
        baseline_atr: Optional[float] = None,
    ) -> float:
        """Calculate dynamic bid-ask spread at a specific time and market condition."""
        session = self.get_session_name(timestamp)
        multiplier = self.session_multipliers.get(session, 1.0)
        spread = self.base_spread_usd * multiplier

        if self.enable_volatility_scaling and current_atr is not None and baseline_atr is not None and baseline_atr > 0:
            vol_ratio = current_atr / baseline_atr
            if vol_ratio > 1.0:
                spread *= (1.0 + self.volatility_spread_factor * (vol_ratio - 1.0))

        return round(spread, 3)

    def calculate_slippage(
        self,
        candle_range: Optional[float] = None,
        baseline_candle_range: Optional[float] = None,
    ) -> float:
        """Calculate execution slippage based on bar volatility."""
        slippage = self.base_slippage_usd
        if candle_range is not None and baseline_candle_range is not None and baseline_candle_range > 0:
            vol_ratio = candle_range / baseline_candle_range
            if vol_ratio > 1.0:
                slippage += 0.02 * (vol_ratio - 1.0)
        return round(slippage, 3)

    def simulate_execution(
        self,
        action: str,
        bid_price: float,
        timestamp: Union[datetime, pd.Timestamp],
        current_atr: Optional[float] = None,
        baseline_atr: Optional[float] = None,
        candle_range: Optional[float] = None,
        baseline_candle_range: Optional[float] = None,
    ) -> TradeExecution:
        """Simulate realistic order fill with spread, slippage, and commissions."""
        action_upper = action.upper()
        if action_upper not in ["BUY", "SELL"]:
            raise ValueError(f"Invalid action '{action}'. Must be 'BUY' or 'SELL'.")

        ts_utc = pd.to_datetime(timestamp, utc=True)
        session = self.get_session_name(ts_utc)

        # Reject trades during daily maintenance roll break (22:00 UTC)
        if session == "DAILY_ROLL_BREAK" and (ts_utc.hour == 22):
            return TradeExecution(
                action=action_upper,
                nominal_bid=bid_price,
                effective_spread=0.0,
                slippage=0.0,
                commission_per_oz=self.commission_per_oz,
                fill_price=bid_price,
                total_friction_per_oz=0.0,
                timestamp=ts_utc,
                is_tradable=False,
                rejection_reason="Market closed during daily settlement roll break (22:00-23:00 UTC)",
            )

        spread = self.calculate_effective_spread(ts_utc, current_atr, baseline_atr)
        slippage = self.calculate_slippage(candle_range, baseline_candle_range)

        # Execution pricing:
        # BUY (long entry / short exit): executed at ASK = BID + SPREAD + SLIPPAGE
        # SELL (short entry / long exit): executed at BID - SLIPPAGE
        if action_upper == "BUY":
            fill_price = round(bid_price + spread + slippage, 3)
            friction = round(spread + slippage + self.commission_per_oz, 3)
        else:
            fill_price = round(bid_price - slippage, 3)
            friction = round(slippage + self.commission_per_oz, 3)

        return TradeExecution(
            action=action_upper,
            nominal_bid=bid_price,
            effective_spread=spread,
            slippage=slippage,
            commission_per_oz=self.commission_per_oz,
            fill_price=fill_price,
            total_friction_per_oz=friction,
            timestamp=ts_utc,
            is_tradable=True,
            rejection_reason=None,
        )
