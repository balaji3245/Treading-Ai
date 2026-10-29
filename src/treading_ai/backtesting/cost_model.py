"""Configurable transaction cost, dynamic spread, slippage, and commission model.

Addresses bid-only price limitations in historical raw market data by providing
statistically grounded, regime-aware execution simulation for XAUUSD spot gold.

Bid-Only Execution Convention & Cost Causality Documentation:
--------------------------------------------------------------
1. Market Price Limitation:
   Raw historical broker data for XAUUSD (e.g. HistData) contains solely Bid quotes
   (Open, High, Low, Close). True Ask prices are unobserved in the historical record.

2. Bid-Only Execution Approximation:
   In institutional spot gold trading, Long entries and Short exits execute at the Ask
   price, while Long exits and Short entries execute at the Bid price. We model fills as:
   - Long Entry (Buy): Executed at Ask = Bid + Effective Spread + Slippage
   - Long Exit (Sell): Executed at Bid = Bid - Slippage
   - Short Entry (Sell): Executed at Bid = Bid - Slippage
   - Short Exit (Buy): Executed at Ask = Bid + Effective Spread + Slippage
   - Commission: Institutional ECN commission of $5.00 / 100 oz standard lot ($0.05/oz)
     charged symmetrically on every execution leg ($0.10/oz round-turn).

3. Deterministic Cost Friction & PnL Drag:
   - Gross Long PnL ($/oz): Bid_exit - Bid_entry
   - Net Long PnL ($/oz):
       (Bid_exit - Slippage_exit) - (Bid_entry + Spread_entry + Slippage_entry) - 2 * Comm
       = (Bid_exit - Bid_entry) - (Spread_entry + Slippage_entry + Slippage_exit + 2 * Comm)
   - Gross Short PnL ($/oz): Bid_entry - Bid_exit
   - Net Short PnL ($/oz):
       (Bid_entry - Slippage_entry) - (Bid_exit + Spread_exit + Slippage_exit) - 2 * Comm
       = (Bid_entry - Bid_exit) - (Spread_exit + Slippage_entry + Slippage_exit + 2 * Comm)
   - Because Spread >= 0, Slippage >= 0, and Commission >= 0:
       Total Friction (Long) = Spread_entry + Slippage_entry + Slippage_exit + 2 * Comm > 0
       Total Friction (Short) = Spread_exit + Slippage_entry + Slippage_exit + 2 * Comm > 0
   - In every market state, Net PnL < Gross PnL. Transaction costs strictly drag performance
     and cannot under any circumstance improve a trade's PnL.
   - Long and Short execution conventions are structurally symmetric: each side incurs exactly
     one spread charge, two slippage charges, and two commission charges.

4. Distinguishing Assumptions from Broker-Verified Execution Data:
   - Broker-Verified Data:
     * Raw historical timestamps and Bid price series.
     * Institutional standard contract size: 100 troy ounces per lot.
     * Institutional broker commission schedule ($5.00/lot = $0.05/oz per side).
   - Modeling Assumptions:
     * Synthetic Ask price construction via session-dependent base spread ($0.20 base).
     * Macro session liquidity multipliers (Asian 1.8x, London Morning 1.15x,
       London/NY Overlap 1.0x, NY Afternoon 1.30x, Daily Roll Break 12.0x).
     * Volatility scaling: Spread expands by 0.5x when ATR exceeds baseline ATR.
     * Slippage model: Base slippage ($0.05/oz) expanding by $0.02/oz per unit excess
       bar range over baseline range.
     * Instant fill execution at candle Open without unmodeled order queue delay.

5. Pre-Trade Execution Causality:
   - Order fill at bar t+1 Open uses strictly volatility inputs finalized on or before bar t.
   - Order fill at bar t+1+H Open uses strictly volatility inputs finalized on or before bar t+H.
   - Under no circumstances does a bar's opening fill depend on its own completed High, Low,
     range, or future ATR.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Optional, Union
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd

TZ_NEW_YORK = ZoneInfo("America/New_York")
TZ_LONDON = ZoneInfo("Europe/London")
TZ_TOKYO = ZoneInfo("Asia/Tokyo")


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

    Strict Execution Causality & Timezone-Aware Rollover:
    - Pre-Trade Causal Pricing: Order fill at bar t+1 Open uses strictly volatility metrics
      finalized on or before bar t. Bar t+1's completed range or future ATR is never accessed.
    - Canonical Rollover Policy: Gold settlement closure occurs Monday through Thursday
      at 17:00:00 to 18:00:00 New York Time (America/New_York).
      - In summer (EDT): 21:00 to 22:00 UTC.
      - In winter (EST): 22:00 to 23:00 UTC.
    - Bid-Only Execution Modeling:
      - Long Entry (Buy): Executed at Ask = Bid + Spread + Slippage.
      - Long Exit (Sell): Executed at Bid - Slippage.
      - Short Entry (Sell): Executed at Bid - Slippage.
      - Short Exit (Buy): Executed at Ask = Bid + Spread + Slippage.
      - Commission: Applied symmetrically on entry and exit ($0.05/oz round-trip per leg = $0.10/oz total).
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
        self.base_spread_usd = base_spread_usd
        self.commission_per_lot_usd = commission_per_lot_usd
        self.lot_size_oz = lot_size_oz
        self.commission_per_oz = commission_per_lot_usd / lot_size_oz
        self.base_slippage_usd = base_slippage_usd
        self.enable_volatility_scaling = enable_volatility_scaling
        self.volatility_spread_factor = volatility_spread_factor

        self.session_multipliers = session_multipliers or {
            "LONDON_NY_OVERLAP": 1.0,   # Peak liquidity (London & NY both open)
            "LONDON_MORNING": 1.15,     # European morning before NY open
            "NY_AFTERNOON": 1.30,       # US afternoon after London close
            "ASIAN_SESSION": 1.80,      # Tokyo/Asian trading hours
            "DAILY_ROLL_BREAK": 12.0,   # Illiquid rollover window (spread expansion)
            "WEEKEND_CLOSED": 0.0,      # Market closure (non-tradable)
        }

    def _to_utc_timestamp(self, timestamp: Union[datetime, pd.Timestamp]) -> pd.Timestamp:
        """Helper to ensure timestamp is a timezone-aware UTC pd.Timestamp."""
        if not hasattr(timestamp, "tzinfo") or timestamp.tzinfo is None:
            return pd.to_datetime(timestamp, utc=True)
        return pd.Timestamp(timestamp).tz_convert(timezone.utc)

    def is_rollover_closed(self, timestamp: Union[datetime, pd.Timestamp]) -> bool:
        """Determine whether the market is officially closed for daily settlement rollover.

        In spot gold (XAUUSD), the market closes Monday through Thursday at 17:00:00 to 18:00:00
        New York local time (America/New_York).
        - Summer (EDT): 21:00 to 22:00 UTC.
        - Winter (EST): 22:00 to 23:00 UTC.
        """
        ts_utc = self._to_utc_timestamp(timestamp)
        ts_ny = ts_utc.astimezone(TZ_NEW_YORK)
        # Monday (0) through Thursday (3) during the 17:00 hour
        return ts_ny.weekday() < 4 and ts_ny.hour == 17

    def is_rollover_closed_series(self, timestamps: pd.Series) -> np.ndarray:
        """Vectorized determination of daily settlement rollover closures (Mon-Thu 17:00-18:00 NY)."""
        if not pd.api.types.is_datetime64_any_dtype(timestamps):
            ts_utc = pd.to_datetime(timestamps, utc=True)
        elif timestamps.dt.tz is None:
            ts_utc = timestamps.dt.tz_localize("UTC")
        else:
            ts_utc = timestamps.dt.tz_convert("UTC")
        ts_ny = ts_utc.dt.tz_convert(TZ_NEW_YORK)
        closed = (ts_ny.dt.day_of_week < 4) & (ts_ny.dt.hour == 17)
        return closed.to_numpy(dtype=bool)

    def is_weekend_closed(self, timestamp: Union[datetime, pd.Timestamp]) -> bool:
        """Determine whether the spot market is closed for the weekend.

        Spot gold closes Friday at 17:00:00 New York Time and reopens
        Sunday at 18:00:00 New York Time (America/New_York).
        """
        ts_utc = self._to_utc_timestamp(timestamp)
        ts_ny = ts_utc.astimezone(TZ_NEW_YORK)
        w = ts_ny.weekday()
        if w == 4:  # Friday
            return ts_ny.hour >= 17
        elif w == 5:  # Saturday
            return True
        elif w == 6:  # Sunday
            return ts_ny.hour < 18
        return False

    def is_weekend_closed_series(self, timestamps: pd.Series) -> np.ndarray:
        """Vectorized determination of weekend market closures."""
        if not pd.api.types.is_datetime64_any_dtype(timestamps):
            ts_utc = pd.to_datetime(timestamps, utc=True)
        elif timestamps.dt.tz is None:
            ts_utc = timestamps.dt.tz_localize("UTC")
        else:
            ts_utc = timestamps.dt.tz_convert("UTC")
        ts_ny = ts_utc.dt.tz_convert(TZ_NEW_YORK)
        w = ts_ny.dt.day_of_week
        h = ts_ny.dt.hour
        closed = ((w == 4) & (h >= 17)) | (w == 5) | ((w == 6) & (h < 18))
        return closed.to_numpy(dtype=bool)

    def is_market_closed(self, timestamp: Union[datetime, pd.Timestamp]) -> bool:
        """Determine whether the spot market is closed (daily rollover or weekend closure)."""
        return self.is_rollover_closed(timestamp) or self.is_weekend_closed(timestamp)

    def is_market_closed_series(self, timestamps: pd.Series) -> np.ndarray:
        """Vectorized determination of general market closure."""
        return self.is_rollover_closed_series(timestamps) | self.is_weekend_closed_series(timestamps)

    def get_session_name(self, timestamp: Union[datetime, pd.Timestamp]) -> str:
        """Classify timestamp into spot market session using timezone-aware local clocks."""
        ts_utc = self._to_utc_timestamp(timestamp)

        # 1. Weekend market closure (Friday 17:00 NY to Sunday 18:00 NY)
        if self.is_weekend_closed(ts_utc):
            return "WEEKEND_CLOSED"

        ts_ny = ts_utc.astimezone(TZ_NEW_YORK)
        ts_london = ts_utc.astimezone(TZ_LONDON)

        # 2. Rollover window (Monday-Thursday 17:00-18:00 NY, plus 15m pre/post buffer)
        if ts_ny.weekday() < 4:
            if ts_ny.hour == 17 or (ts_ny.hour == 16 and ts_ny.minute >= 45) or (ts_ny.hour == 18 and ts_ny.minute <= 15):
                return "DAILY_ROLL_BREAK"

        # 3. London Session (08:00-16:30 London) and NY Session (08:00-17:00 NY)
        min_london = ts_london.hour * 60 + ts_london.minute
        min_ny = ts_ny.hour * 60 + ts_ny.minute
        london_active = (8 * 60 <= min_london < 16 * 60 + 30) and ts_london.weekday() < 5
        ny_active = (8 * 60 <= min_ny < 17 * 60) and ts_ny.weekday() < 5

        if london_active and ny_active:
            return "LONDON_NY_OVERLAP"
        elif london_active and not ny_active:
            return "LONDON_MORNING"
        elif ny_active and not london_active:
            return "NY_AFTERNOON"
        else:
            return "ASIAN_SESSION"

    def get_session_name_series(self, timestamps: pd.Series) -> pd.Series:
        """Vectorized classification of timestamps into market sessions."""
        if not pd.api.types.is_datetime64_any_dtype(timestamps):
            ts_utc = pd.to_datetime(timestamps, utc=True)
        elif timestamps.dt.tz is None:
            ts_utc = timestamps.dt.tz_localize("UTC")
        else:
            ts_utc = timestamps.dt.tz_convert("UTC")

        ts_ny = ts_utc.dt.tz_convert(TZ_NEW_YORK)
        ts_london = ts_utc.dt.tz_convert(TZ_LONDON)

        weekend_closed = self.is_weekend_closed_series(ts_utc)

        roll_break = (~weekend_closed) & (ts_ny.dt.day_of_week < 4) & (
            (ts_ny.dt.hour == 17) |
            ((ts_ny.dt.hour == 16) & (ts_ny.dt.minute >= 45)) |
            ((ts_ny.dt.hour == 18) & (ts_ny.dt.minute <= 15))
        )

        min_london = ts_london.dt.hour * 60 + ts_london.dt.minute
        london_active = (~weekend_closed) & (min_london >= 8 * 60) & (min_london < 16 * 60 + 30) & (ts_london.dt.day_of_week < 5)

        min_ny = ts_ny.dt.hour * 60 + ts_ny.dt.minute
        ny_active = (~weekend_closed) & (min_ny >= 8 * 60) & (min_ny < 17 * 60) & (ts_ny.dt.day_of_week < 5)

        sessions = np.full(len(timestamps), "ASIAN_SESSION", dtype=object)
        sessions[ny_active & (~london_active) & (~roll_break) & (~weekend_closed)] = "NY_AFTERNOON"
        sessions[london_active & (~ny_active) & (~roll_break) & (~weekend_closed)] = "LONDON_MORNING"
        sessions[london_active & ny_active & (~roll_break) & (~weekend_closed)] = "LONDON_NY_OVERLAP"
        sessions[roll_break] = "DAILY_ROLL_BREAK"
        sessions[weekend_closed] = "WEEKEND_CLOSED"
        return pd.Series(sessions, index=timestamps.index)

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

    def calculate_effective_spread_series(
        self,
        timestamps: pd.Series,
        prior_atrs: Optional[Union[np.ndarray, pd.Series]] = None,
        baseline_atr: Optional[float] = None,
    ) -> np.ndarray:
        """Vectorized effective spread calculation with exact scalar parity."""
        sessions = self.get_session_name_series(timestamps)
        mult_map = self.session_multipliers
        multipliers = sessions.map(mult_map).to_numpy(dtype=float)
        spread = self.base_spread_usd * multipliers

        if self.enable_volatility_scaling and prior_atrs is not None and baseline_atr is not None and baseline_atr > 0:
            atrs_arr = np.asarray(prior_atrs, dtype=float)
            vol_ratio = atrs_arr / baseline_atr
            scale_mask = vol_ratio > 1.0
            spread = np.where(scale_mask, spread * (1.0 + self.volatility_spread_factor * (vol_ratio - 1.0)), spread)

        return np.round(spread, 3)

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

    def calculate_slippage_series(
        self,
        prior_candle_ranges: Optional[Union[np.ndarray, pd.Series]] = None,
        baseline_candle_range: Optional[float] = None,
    ) -> np.ndarray:
        """Vectorized slippage calculation with exact scalar parity."""
        if prior_candle_ranges is None:
            return np.full(1, self.base_slippage_usd)
        ranges_arr = np.asarray(prior_candle_ranges, dtype=float)
        slippage = np.full(len(ranges_arr), self.base_slippage_usd, dtype=float)
        if baseline_candle_range is not None and baseline_candle_range > 0:
            vol_ratio = ranges_arr / baseline_candle_range
            scale_mask = vol_ratio > 1.0
            slippage = np.where(scale_mask, slippage + 0.02 * (vol_ratio - 1.0), slippage)
        return np.round(slippage, 3)

    def simulate_causal_fill(
        self,
        action: str,
        nominal_bid: float,
        timestamp: Union[datetime, pd.Timestamp],
        prior_atr: Optional[float] = None,
        baseline_atr: Optional[float] = None,
        prior_candle_range: Optional[float] = None,
        baseline_candle_range: Optional[float] = None,
    ) -> TradeExecution:
        """Simulate realistic order fill with strict pre-trade causality.

        Parameters
        ----------
        action : str
            Order action: 'BUY' (long entry / short exit) or 'SELL' (short entry / long exit).
        nominal_bid : float
            Nominal bid price observed at execution instant (e.g. Open of bar t+1).
        timestamp : Union[datetime, pd.Timestamp]
            Execution timestamp (e.g. Open timestamp of bar t+1).
        prior_atr : Optional[float]
            ATR finalized on prior completed bar (bar t), NEVER future bar t+1.
        baseline_atr : Optional[float]
            Baseline ATR for volatility spread scaling.
        prior_candle_range : Optional[float]
            High - Low range of prior completed bar (bar t), NEVER future bar t+1.
        baseline_candle_range : Optional[float]
            Baseline candle range for slippage scaling.
        """
        action_upper = action.upper()
        if action_upper not in ["BUY", "SELL"]:
            raise ValueError(f"Invalid action '{action}'. Must be 'BUY' or 'SELL'.")

        ts_utc = self._to_utc_timestamp(timestamp)

        # Reject trades during daily settlement rollover or weekend market closures
        if self.is_market_closed(ts_utc):
            if self.is_rollover_closed(ts_utc):
                reason = "Market closed during daily settlement rollover (17:00-18:00 New York Time)"
            else:
                reason = "Market closed for weekend (Friday 17:00 to Sunday 18:00 New York Time)"
            return TradeExecution(
                action=action_upper,
                nominal_bid=nominal_bid,
                effective_spread=0.0,
                slippage=0.0,
                commission_per_oz=self.commission_per_oz,
                fill_price=nominal_bid,
                total_friction_per_oz=0.0,
                timestamp=ts_utc,
                is_tradable=False,
                rejection_reason=reason,
            )

        spread = self.calculate_effective_spread(ts_utc, current_atr=prior_atr, baseline_atr=baseline_atr)
        slippage = self.calculate_slippage(candle_range=prior_candle_range, baseline_candle_range=baseline_candle_range)

        # Bid-Only Execution Pricing:
        # BUY (long entry / short exit): executed at ASK = BID + SPREAD + SLIPPAGE
        # SELL (short entry / long exit): executed at BID - SLIPPAGE
        if action_upper == "BUY":
            fill_price = round(nominal_bid + spread + slippage, 3)
            friction = round(spread + slippage + self.commission_per_oz, 3)
        else:
            fill_price = round(nominal_bid - slippage, 3)
            friction = round(slippage + self.commission_per_oz, 3)

        return TradeExecution(
            action=action_upper,
            nominal_bid=nominal_bid,
            effective_spread=spread,
            slippage=slippage,
            commission_per_oz=self.commission_per_oz,
            fill_price=fill_price,
            total_friction_per_oz=friction,
            timestamp=ts_utc,
            is_tradable=True,
            rejection_reason=None,
        )

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
        """Backwards-compatible execution simulator routing to causal fill logic."""
        return self.simulate_causal_fill(
            action=action,
            nominal_bid=bid_price,
            timestamp=timestamp,
            prior_atr=current_atr,
            baseline_atr=baseline_atr,
            prior_candle_range=candle_range,
            baseline_candle_range=baseline_candle_range,
        )
