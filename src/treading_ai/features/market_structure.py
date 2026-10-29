"""Causal Market Structure and Liquidity Engine for XAUUSD.

This module implements timestamp-safe, zero-lookahead market structure features:
- Swing Highs & Swing Lows (parameterized confirmation window N_L, N_R)
- Trend state: Higher Highs (HH), Higher Lows (HL), Lower Highs (LH), Lower Lows (LL)
- Break of Structure (BOS) and Change of Character (CHoCH) state machine
- Equal Highs (EQH) and Equal Lows (EQL) proxy detection
- Liquidity sweeps and sweep-and-reclaim patterns
- Fair Value Gaps (FVG) and causal mitigation tracking
- Dealing range Premium vs Discount equilibrium
- Support/Resistance causal clustering and retests
- Supply/Demand displacement origin candidates

CAUSALITY GUARANTEE:
A swing pivot at bar t - N_R is confirmed ONLY when bar t closes.
It is never accessible to the feature pipeline before bar t.
All features maintain strict causal temporal order.

NOTE ON LIQUIDITY AND SMC/ICT CONCEPTS:
On top-of-book, bid-only OHLC data, liquidity sweeps and order blocks are
price-pattern proxies and testable hypotheses, not proof of institutional order book depth.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd


@dataclass
class SwingPoint:
    """Represents a confirmed swing high or low."""
    bar_index: int
    timestamp: pd.Timestamp
    price: float
    is_high: bool
    confirmed_at_bar: int
    confirmed_at_timestamp: pd.Timestamp
    classification: str = ""  # 'HH', 'LH', 'HL', 'LL'
    is_broken: bool = False
    broken_at_bar: Optional[int] = None


@dataclass
class FVG:
    """Represents a Fair Value Gap."""
    bar_index: int
    timestamp: pd.Timestamp
    is_bullish: bool
    top: float
    bottom: float
    size: float
    is_mitigated: bool = False
    mitigated_at_bar: Optional[int] = None


class MarketStructureEngine:
    """Causal Market Structure & Liquidity Engine for OHLCV data."""

    def __init__(
        self,
        swing_left_bars: int = 5,
        swing_right_bars: int = 5,
        eqh_eql_atr_mult: float = 0.15,
        displacement_atr_mult: float = 1.5,
        max_active_fvgs: int = 20,
        max_active_swings: int = 20,
    ):
        """
        Initialize MarketStructureEngine.

        Args:
            swing_left_bars: Left confirmation window (N_L).
            swing_right_bars: Right confirmation window (N_R).
                A swing at t - N_R is confirmed when bar t closes.
            eqh_eql_atr_mult: Max distance as fraction of ATR to qualify as EQH/EQL.
            displacement_atr_mult: Min candle body / ATR to qualify as displacement.
            max_active_fvgs: Max unmitigated FVGs to track in active memory.
            max_active_swings: Max past confirmed swings to track for S/R zones.
        """
        self.swing_left_bars = swing_left_bars
        self.swing_right_bars = swing_right_bars
        self.eqh_eql_atr_mult = eqh_eql_atr_mult
        self.displacement_atr_mult = displacement_atr_mult
        self.max_active_fvgs = max_active_fvgs
        self.max_active_swings = max_active_swings

    def compute_features(self, df: pd.DataFrame, atr_series: Optional[pd.Series] = None) -> pd.DataFrame:
        """
        Compute all causal market structure features for the given OHLC dataframe.

        Args:
            df: DataFrame containing 'open', 'high', 'low', 'close', and DatetimeIndex or 'timestamp'.
            atr_series: Precomputed ATR series. If None, computes 14-period True Range rolling mean.

        Returns:
            DataFrame with market structure feature columns aligned with input df.
        """
        n_bars = len(df)
        if n_bars == 0:
            return pd.DataFrame()

        # Extract numpy arrays for high-performance iteration
        highs = df["high"].to_numpy(dtype=np.float64)
        lows = df["low"].to_numpy(dtype=np.float64)
        closes = df["close"].to_numpy(dtype=np.float64)
        opens = df["open"].to_numpy(dtype=np.float64)

        if atr_series is not None:
            atrs = atr_series.to_numpy(dtype=np.float64)
        else:
            # Fallback causal ATR(14)
            tr = np.maximum(
                highs - lows,
                np.maximum(
                    np.abs(highs - np.roll(closes, 1)),
                    np.abs(lows - np.roll(closes, 1))
                )
            )
            tr[0] = highs[0] - lows[0]
            atrs = pd.Series(tr).rolling(14, min_periods=1).mean().to_numpy(dtype=np.float64)

        timestamps = df.index if isinstance(df.index, pd.DatetimeIndex) else pd.to_datetime(df["timestamp"])

        # Allocate feature arrays
        # Swing features (initialized with causal running extrema before first confirmed swing)
        ms_swing_high = np.copy(highs)
        ms_swing_low = np.copy(lows)
        ms_bars_since_swing_high = np.zeros(n_bars, dtype=np.float64)
        ms_bars_since_swing_low = np.zeros(n_bars, dtype=np.float64)
        ms_is_new_swing_high = np.zeros(n_bars, dtype=np.int8)
        ms_is_new_swing_low = np.zeros(n_bars, dtype=np.int8)

        # Classification: 1=HH, 2=LH, 3=HL, 4=LL
        ms_swing_high_type = np.zeros(n_bars, dtype=np.int8)  # 1=HH, 2=LH
        ms_swing_low_type = np.zeros(n_bars, dtype=np.int8)   # 1=HL, 2=LL
        ms_trend_state = np.zeros(n_bars, dtype=np.int8)       # +1=Bullish, -1=Bearish, 0=Neutral

        # BOS & CHoCH
        ms_bos_bullish = np.zeros(n_bars, dtype=np.int8)
        ms_bos_bearish = np.zeros(n_bars, dtype=np.int8)
        ms_choch_bullish = np.zeros(n_bars, dtype=np.int8)
        ms_choch_bearish = np.zeros(n_bars, dtype=np.int8)
        ms_swing_high_broken = np.zeros(n_bars, dtype=np.int8)
        ms_swing_low_broken = np.zeros(n_bars, dtype=np.int8)

        # Liquidity & Sweeps
        ms_is_eqh = np.zeros(n_bars, dtype=np.int8)
        ms_is_eql = np.zeros(n_bars, dtype=np.int8)
        ms_sweep_high = np.zeros(n_bars, dtype=np.int8)
        ms_sweep_low = np.zeros(n_bars, dtype=np.int8)
        ms_sweep_reclaim_bullish = np.zeros(n_bars, dtype=np.int8)
        ms_sweep_reclaim_bearish = np.zeros(n_bars, dtype=np.int8)

        # Fair Value Gaps (100.0 ATR indicates no active FVG in vicinity)
        ms_fvg_bullish_formed = np.zeros(n_bars, dtype=np.int8)
        ms_fvg_bearish_formed = np.zeros(n_bars, dtype=np.int8)
        ms_fvg_bullish_size_atr = np.zeros(n_bars, dtype=np.float64)
        ms_fvg_bearish_size_atr = np.zeros(n_bars, dtype=np.float64)
        ms_active_fvg_bullish_count = np.zeros(n_bars, dtype=np.int16)
        ms_active_fvg_bearish_count = np.zeros(n_bars, dtype=np.int16)
        ms_dist_to_fvg_bullish_atr = np.full(n_bars, 100.0, dtype=np.float64)
        ms_dist_to_fvg_bearish_atr = np.full(n_bars, 100.0, dtype=np.float64)

        # Premium / Discount
        ms_equilibrium_price = (highs + lows) / 2.0
        ms_premium_discount_pct = np.full(n_bars, 0.5, dtype=np.float64)  # 0.5 = neutral equilibrium
        ms_in_discount = np.zeros(n_bars, dtype=np.int8)
        ms_in_premium = np.zeros(n_bars, dtype=np.int8)

        # Support & Resistance Causal Clusters (100.0 ATR indicates no nearby zone)
        ms_dist_to_support_atr = np.full(n_bars, 100.0, dtype=np.float64)
        ms_dist_to_resistance_atr = np.full(n_bars, 100.0, dtype=np.float64)
        ms_sr_rejection_bullish = np.zeros(n_bars, dtype=np.int8)
        ms_sr_rejection_bearish = np.zeros(n_bars, dtype=np.int8)

        # Supply / Demand Displacement (100.0 ATR indicates no nearby zone)
        ms_displacement_ratio = np.zeros(n_bars, dtype=np.float64)
        ms_is_bullish_displacement = np.zeros(n_bars, dtype=np.int8)
        ms_is_bearish_displacement = np.zeros(n_bars, dtype=np.int8)
        ms_dist_to_demand_zone_atr = np.full(n_bars, 100.0, dtype=np.float64)
        ms_dist_to_supply_zone_atr = np.full(n_bars, 100.0, dtype=np.float64)

        # State tracking variables
        confirmed_highs: List[SwingPoint] = []
        confirmed_lows: List[SwingPoint] = []
        active_bullish_fvgs: List[FVG] = []
        active_bearish_fvgs: List[FVG] = []
        active_demand_zones: List[Tuple[float, float, int]] = []  # (bottom, top, bar_idx)
        active_supply_zones: List[Tuple[float, float, int]] = []  # (bottom, top, bar_idx)

        current_trend = 0  # +1 Bullish, -1 Bearish, 0 Neutral
        last_high_class = ""
        last_low_class = ""

        nl = self.swing_left_bars
        nr = self.swing_right_bars

        # Main causal simulation loop
        for i in range(n_bars):
            cur_close = closes[i]
            cur_open = opens[i]
            cur_high = highs[i]
            cur_low = lows[i]
            cur_atr = atrs[i] if atrs[i] > 1e-4 else 1.0
            cur_ts = timestamps[i]

            # -------------------------------------------------------------
            # 1. Causal Swing Detection (Pivot confirmed strictly at bar i)
            # -------------------------------------------------------------
            pivot_idx = i - nr
            if pivot_idx >= nl:
                pivot_high = highs[pivot_idx]
                pivot_low = lows[pivot_idx]

                # Check if pivot_idx is a Swing High
                # Left check: highs[pivot_idx] > highs[pivot_idx - k] for k in 1..nl
                # Right check: highs[pivot_idx] >= highs[pivot_idx + k] for k in 1..nr
                is_high_candidate = True
                for k in range(1, nl + 1):
                    if highs[pivot_idx - k] >= pivot_high:
                        is_high_candidate = False
                        break
                if is_high_candidate:
                    for k in range(1, nr + 1):
                        if highs[pivot_idx + k] > pivot_high:
                            is_high_candidate = False
                            break

                if is_high_candidate:
                    # Classify HH vs LH
                    classification = ""
                    eqh_flag = 0
                    if len(confirmed_highs) > 0:
                        prev_high_price = confirmed_highs[-1].price
                        diff = abs(pivot_high - prev_high_price)
                        if diff <= self.eqh_eql_atr_mult * cur_atr:
                            eqh_flag = 1

                        if pivot_high > prev_high_price:
                            classification = "HH"
                        else:
                            classification = "LH"
                    else:
                        classification = "HH"

                    sp = SwingPoint(
                        bar_index=pivot_idx,
                        timestamp=timestamps[pivot_idx],
                        price=pivot_high,
                        is_high=True,
                        confirmed_at_bar=i,
                        confirmed_at_timestamp=cur_ts,
                        classification=classification,
                    )
                    confirmed_highs.append(sp)
                    if len(confirmed_highs) > self.max_active_swings:
                        confirmed_highs.pop(0)

                    ms_is_new_swing_high[i] = 1
                    ms_is_eqh[i] = eqh_flag
                    last_high_class = classification

                # Check if pivot_idx is a Swing Low
                is_low_candidate = True
                for k in range(1, nl + 1):
                    if lows[pivot_idx - k] <= pivot_low:
                        is_low_candidate = False
                        break
                if is_low_candidate:
                    for k in range(1, nr + 1):
                        if lows[pivot_idx + k] < pivot_low:
                            is_low_candidate = False
                            break

                if is_low_candidate:
                    classification = ""
                    eql_flag = 0
                    if len(confirmed_lows) > 0:
                        prev_low_price = confirmed_lows[-1].price
                        diff = abs(pivot_low - prev_low_price)
                        if diff <= self.eqh_eql_atr_mult * cur_atr:
                            eql_flag = 1

                        if pivot_low > prev_low_price:
                            classification = "HL"
                        else:
                            classification = "LL"
                    else:
                        classification = "LL"

                    sp = SwingPoint(
                        bar_index=pivot_idx,
                        timestamp=timestamps[pivot_idx],
                        price=pivot_low,
                        is_high=False,
                        confirmed_at_bar=i,
                        confirmed_at_timestamp=cur_ts,
                        classification=classification,
                    )
                    confirmed_lows.append(sp)
                    if len(confirmed_lows) > self.max_active_swings:
                        confirmed_lows.pop(0)

                    ms_is_new_swing_low[i] = 1
                    ms_is_eql[i] = eql_flag
                    last_low_class = classification

            # -------------------------------------------------------------
            # 2. Update Structural Trend State
            # -------------------------------------------------------------
            if last_high_class == "HH" and last_low_class == "HL":
                current_trend = 1  # Bullish
            elif last_high_class == "LH" and last_low_class == "LL":
                current_trend = -1  # Bearish
            elif last_high_class == "HH" and last_low_class == "LL":
                current_trend = 0  # Expanding / Neutral
            elif last_high_class == "LH" and last_low_class == "HL":
                current_trend = 0  # Compressing / Triangle

            ms_trend_state[i] = current_trend

            # -------------------------------------------------------------
            # 3. Reference Most Recent Confirmed Swings
            # -------------------------------------------------------------
            latest_high = confirmed_highs[-1] if len(confirmed_highs) > 0 else None
            latest_low = confirmed_lows[-1] if len(confirmed_lows) > 0 else None

            if latest_high is not None:
                ms_swing_high[i] = latest_high.price
                ms_bars_since_swing_high[i] = i - latest_high.bar_index
                ms_swing_high_type[i] = 1 if latest_high.classification == "HH" else 2
                ms_swing_high_broken[i] = 1 if latest_high.is_broken else 0

            if latest_low is not None:
                ms_swing_low[i] = latest_low.price
                ms_bars_since_swing_low[i] = i - latest_low.bar_index
                ms_swing_low_type[i] = 1 if latest_low.classification == "HL" else 2
                ms_swing_low_broken[i] = 1 if latest_low.is_broken else 0

            # -------------------------------------------------------------
            # 4. Break of Structure (BOS) and Change of Character (CHoCH)
            # -------------------------------------------------------------
            if latest_high is not None and not latest_high.is_broken:
                if cur_close > latest_high.price:
                    latest_high.is_broken = True
                    latest_high.broken_at_bar = i
                    if current_trend == 1:
                        ms_bos_bullish[i] = 1
                    else:
                        ms_choch_bullish[i] = 1
                        current_trend = 1  # Flipped bullish

            if latest_low is not None and not latest_low.is_broken:
                if cur_close < latest_low.price:
                    latest_low.is_broken = True
                    latest_low.broken_at_bar = i
                    if current_trend == -1:
                        ms_bos_bearish[i] = 1
                    else:
                        ms_choch_bearish[i] = 1
                        current_trend = -1  # Flipped bearish

            # -------------------------------------------------------------
            # 5. Liquidity Sweeps & Reclaim Candidates
            # -------------------------------------------------------------
            if latest_high is not None:
                # Pierce above swing high, but close below
                if cur_high > latest_high.price and cur_close < latest_high.price:
                    ms_sweep_high[i] = 1
                # Reclaim: previous bar closed above or swept, current bar closes back below
                if i >= 1 and highs[i - 1] > latest_high.price and cur_close < latest_high.price and cur_close < cur_open:
                    ms_sweep_reclaim_bearish[i] = 1

            if latest_low is not None:
                # Pierce below swing low, but close above
                if cur_low < latest_low.price and cur_close > latest_low.price:
                    ms_sweep_low[i] = 1
                # Reclaim: previous bar closed below or swept, current bar closes back above
                if i >= 1 and lows[i - 1] < latest_low.price and cur_close > latest_low.price and cur_close > cur_open:
                    ms_sweep_reclaim_bullish[i] = 1

            # -------------------------------------------------------------
            # 6. Fair Value Gaps (FVG) and Mitigation Tracking
            # -------------------------------------------------------------
            if i >= 2:
                # Bullish FVG: Low[i] > High[i-2]
                if cur_low > highs[i - 2]:
                    gap_size = cur_low - highs[i - 2]
                    fvg = FVG(
                        bar_index=i,
                        timestamp=cur_ts,
                        is_bullish=True,
                        top=cur_low,
                        bottom=highs[i - 2],
                        size=gap_size,
                    )
                    active_bullish_fvgs.append(fvg)
                    ms_fvg_bullish_formed[i] = 1
                    ms_fvg_bullish_size_atr[i] = gap_size / cur_atr

                # Bearish FVG: High[i] < Low[i-2]
                if cur_high < lows[i - 2]:
                    gap_size = lows[i - 2] - cur_high
                    fvg = FVG(
                        bar_index=i,
                        timestamp=cur_ts,
                        is_bullish=False,
                        top=lows[i - 2],
                        bottom=cur_high,
                        size=gap_size,
                    )
                    active_bearish_fvgs.append(fvg)
                    ms_fvg_bearish_formed[i] = 1
                    ms_fvg_bearish_size_atr[i] = gap_size / cur_atr

            # Check mitigations of active FVGs
            # Bullish FVG is mitigated if cur_low <= fvg.bottom
            active_bullish_fvgs = [
                f for f in active_bullish_fvgs
                if not (cur_low <= f.bottom)
            ]
            # Bearish FVG is mitigated if cur_high >= fvg.top
            active_bearish_fvgs = [
                f for f in active_bearish_fvgs
                if not (cur_high >= f.top)
            ]

            # Prune old active FVGs to maintain bounded memory
            if len(active_bullish_fvgs) > self.max_active_fvgs:
                active_bullish_fvgs = active_bullish_fvgs[-self.max_active_fvgs:]
            if len(active_bearish_fvgs) > self.max_active_fvgs:
                active_bearish_fvgs = active_bearish_fvgs[-self.max_active_fvgs:]

            ms_active_fvg_bullish_count[i] = len(active_bullish_fvgs)
            ms_active_fvg_bearish_count[i] = len(active_bearish_fvgs)

            if len(active_bullish_fvgs) > 0:
                # Distance to nearest bullish FVG (below current price)
                dists = [cur_close - f.top for f in active_bullish_fvgs if cur_close >= f.top]
                if dists:
                    ms_dist_to_fvg_bullish_atr[i] = min(dists) / cur_atr

            if len(active_bearish_fvgs) > 0:
                # Distance to nearest bearish FVG (above current price)
                dists = [f.bottom - cur_close for f in active_bearish_fvgs if f.bottom >= cur_close]
                if dists:
                    ms_dist_to_fvg_bearish_atr[i] = min(dists) / cur_atr

            # -------------------------------------------------------------
            # 7. Premium vs Discount Dealing Range
            # -------------------------------------------------------------
            if latest_high is not None and latest_low is not None:
                range_span = latest_high.price - latest_low.price
                if range_span > 1e-4:
                    eq_price = (latest_high.price + latest_low.price) / 2.0
                    ms_equilibrium_price[i] = eq_price
                    pos_pct = (cur_close - latest_low.price) / range_span
                    ms_premium_discount_pct[i] = pos_pct
                    if pos_pct < 0.5:
                        ms_in_discount[i] = 1
                    else:
                        ms_in_premium[i] = 1

            # -------------------------------------------------------------
            # 8. Causal Support & Resistance Clusters
            # -------------------------------------------------------------
            # Collect prices of recent unbroken swings
            res_candidates = [sp.price for sp in confirmed_highs if sp.price > cur_close]
            sup_candidates = [sp.price for sp in confirmed_lows if sp.price < cur_close]

            if res_candidates:
                nearest_res = min(res_candidates)
                dist_res = (nearest_res - cur_close) / cur_atr
                ms_dist_to_resistance_atr[i] = dist_res
                # Rejection near resistance: price within 0.3 ATR and upper shadow >= 0.4 candle range
                candle_span = cur_high - cur_low
                upper_shadow = cur_high - max(cur_open, cur_close)
                if dist_res <= 0.3 and candle_span > 1e-4 and (upper_shadow / candle_span) >= 0.4:
                    ms_sr_rejection_bearish[i] = 1

            if sup_candidates:
                nearest_sup = max(sup_candidates)
                dist_sup = (cur_close - nearest_sup) / cur_atr
                ms_dist_to_support_atr[i] = dist_sup
                # Rejection near support: price within 0.3 ATR and lower shadow >= 0.4 candle range
                candle_span = cur_high - cur_low
                lower_shadow = min(cur_open, cur_close) - cur_low
                if dist_sup <= 0.3 and candle_span > 1e-4 and (lower_shadow / candle_span) >= 0.4:
                    ms_sr_rejection_bullish[i] = 1

            # -------------------------------------------------------------
            # 9. Supply & Demand Displacement Origins
            # -------------------------------------------------------------
            candle_body = cur_close - cur_open
            disp_ratio = candle_body / cur_atr
            ms_displacement_ratio[i] = disp_ratio

            if disp_ratio >= self.displacement_atr_mult and i >= 1:
                ms_is_bullish_displacement[i] = 1
                # Demand zone is base candle [low, high] of previous bar
                active_demand_zones.append((lows[i - 1], highs[i - 1], i - 1))

            elif disp_ratio <= -self.displacement_atr_mult and i >= 1:
                ms_is_bearish_displacement[i] = 1
                # Supply zone is base candle [low, high] of previous bar
                active_supply_zones.append((lows[i - 1], highs[i - 1], i - 1))

            # Prune invalidated supply/demand zones
            active_demand_zones = [z for z in active_demand_zones if cur_low > z[0]]
            active_supply_zones = [z for z in active_supply_zones if cur_high < z[1]]

            if active_demand_zones:
                valid_demand = [z for z in active_demand_zones if cur_close >= z[1]]
                if valid_demand:
                    nearest_demand_top = max(z[1] for z in valid_demand)
                    ms_dist_to_demand_zone_atr[i] = (cur_close - nearest_demand_top) / cur_atr

            if active_supply_zones:
                valid_supply = [z for z in active_supply_zones if cur_close <= z[0]]
                if valid_supply:
                    nearest_supply_bottom = min(z[0] for z in valid_supply)
                    ms_dist_to_supply_zone_atr[i] = (nearest_supply_bottom - cur_close) / cur_atr

        # Build final features DataFrame
        features_dict = {
            # Swings
            "ms_swing_high": ms_swing_high,
            "ms_swing_low": ms_swing_low,
            "ms_bars_since_swing_high": ms_bars_since_swing_high,
            "ms_bars_since_swing_low": ms_bars_since_swing_low,
            "ms_is_new_swing_high": ms_is_new_swing_high,
            "ms_is_new_swing_low": ms_is_new_swing_low,
            "ms_swing_high_type": ms_swing_high_type,
            "ms_swing_low_type": ms_swing_low_type,
            "ms_trend_state": ms_trend_state,
            # BOS / CHoCH
            "ms_bos_bullish": ms_bos_bullish,
            "ms_bos_bearish": ms_bos_bearish,
            "ms_choch_bullish": ms_choch_bullish,
            "ms_choch_bearish": ms_choch_bearish,
            "ms_swing_high_broken": ms_swing_high_broken,
            "ms_swing_low_broken": ms_swing_low_broken,
            # Liquidity / Sweeps
            "ms_is_eqh": ms_is_eqh,
            "ms_is_eql": ms_is_eql,
            "ms_sweep_high": ms_sweep_high,
            "ms_sweep_low": ms_sweep_low,
            "ms_sweep_reclaim_bullish": ms_sweep_reclaim_bullish,
            "ms_sweep_reclaim_bearish": ms_sweep_reclaim_bearish,
            # Fair Value Gaps
            "ms_fvg_bullish_formed": ms_fvg_bullish_formed,
            "ms_fvg_bearish_formed": ms_fvg_bearish_formed,
            "ms_fvg_bullish_size_atr": ms_fvg_bullish_size_atr,
            "ms_fvg_bearish_size_atr": ms_fvg_bearish_size_atr,
            "ms_active_fvg_bullish_count": ms_active_fvg_bullish_count,
            "ms_active_fvg_bearish_count": ms_active_fvg_bearish_count,
            "ms_dist_to_fvg_bullish_atr": ms_dist_to_fvg_bullish_atr,
            "ms_dist_to_fvg_bearish_atr": ms_dist_to_fvg_bearish_atr,
            # Premium / Discount
            "ms_equilibrium_price": ms_equilibrium_price,
            "ms_premium_discount_pct": ms_premium_discount_pct,
            "ms_in_discount": ms_in_discount,
            "ms_in_premium": ms_in_premium,
            # Support / Resistance
            "ms_dist_to_support_atr": ms_dist_to_support_atr,
            "ms_dist_to_resistance_atr": ms_dist_to_resistance_atr,
            "ms_sr_rejection_bullish": ms_sr_rejection_bullish,
            "ms_sr_rejection_bearish": ms_sr_rejection_bearish,
            # Displacement & Supply/Demand
            "ms_displacement_ratio": ms_displacement_ratio,
            "ms_is_bullish_displacement": ms_is_bullish_displacement,
            "ms_is_bearish_displacement": ms_is_bearish_displacement,
            "ms_dist_to_demand_zone_atr": ms_dist_to_demand_zone_atr,
            "ms_dist_to_supply_zone_atr": ms_dist_to_supply_zone_atr,
        }

        features_df = pd.DataFrame(features_dict, index=df.index)
        return features_df
