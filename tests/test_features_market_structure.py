"""Tests for Causal Market Structure and Liquidity Engine."""

import numpy as np
import pandas as pd
import pytest

from treading_ai.features.market_structure import MarketStructureEngine, SwingPoint, FVG


@pytest.fixture
def sample_ohlc_df():
    """Create synthetic OHLC data with known structure patterns."""
    n_bars = 60
    base_time = pd.Timestamp("2024-01-08 00:00:00+00:00")
    timestamps = [base_time + pd.Timedelta(minutes=5 * i) for i in range(n_bars)]

    # Create synthetic price path with clear swing highs and lows
    # Pattern:
    # 0..10: rising to a peak at bar 10 (High=2050.0)
    # 11..20: falling to a trough at bar 20 (Low=2010.0)
    # 21..30: rising to a higher peak at bar 30 (High=2060.0) -> HH & BOS!
    # 31..40: falling to a higher trough at bar 40 (Low=2025.0) -> HL!
    # 41..50: rising to another peak at bar 50 (High=2070.0)
    # 51..59: falling
    close_prices = np.zeros(n_bars)
    for i in range(11):
        close_prices[i] = 2020.0 + 3.0 * i  # ends at 2050
    for i in range(11, 21):
        close_prices[i] = 2050.0 - 4.0 * (i - 10)  # ends at 2010
    for i in range(21, 31):
        close_prices[i] = 2010.0 + 5.0 * (i - 20)  # ends at 2060
    for i in range(31, 41):
        close_prices[i] = 2060.0 - 3.5 * (i - 30)  # ends at 2025
    for i in range(41, 51):
        close_prices[i] = 2025.0 + 4.5 * (i - 40)  # ends at 2070
    for i in range(51, n_bars):
        close_prices[i] = 2070.0 - 2.0 * (i - 50)

    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": close_prices - 0.5,
            "high": close_prices + 1.0,
            "low": close_prices - 1.0,
            "close": close_prices,
            "volume": 100.0,
        },
        index=pd.DatetimeIndex(timestamps),
    )
    return df


class TestMarketStructureCausality:
    """Rigorous tests confirming causality and zero future lookahead."""

    def test_pivot_confirmation_timing(self, sample_ohlc_df):
        """A swing high at bar 10 with N_R=5 MUST be confirmed at bar 15, not earlier."""
        engine = MarketStructureEngine(swing_left_bars=5, swing_right_bars=5)
        features = engine.compute_features(sample_ohlc_df)

        # Bar 10 has the highest price in the first 20 bars
        # Peak is at index 10. With N_R=5, confirmation occurs at bar 10 + 5 = 15.
        # Before bar 15, bar 10 cannot be known as a swing high!
        for i in range(15):
            assert features["ms_is_new_swing_high"].iloc[i] == 0

        # At bar 15, it must be confirmed
        assert features["ms_is_new_swing_high"].iloc[15] == 1
        assert features["ms_swing_high"].iloc[15] == pytest.approx(sample_ohlc_df["high"].iloc[10])
        assert features["ms_bars_since_swing_high"].iloc[15] == 5.0

        # At bar 16, it remains confirmed, and bars_since increases to 6
        assert features["ms_is_new_swing_high"].iloc[16] == 0
        assert features["ms_swing_high"].iloc[16] == pytest.approx(sample_ohlc_df["high"].iloc[10])
        assert features["ms_bars_since_swing_high"].iloc[16] == 6.0

    def test_truncation_invariance(self, sample_ohlc_df):
        """Features computed up to bar T must be bitwise identical whether computed on df[:T] or df."""
        engine = MarketStructureEngine(swing_left_bars=5, swing_right_bars=5)

        full_features = engine.compute_features(sample_ohlc_df)
        truncated_features = engine.compute_features(sample_ohlc_df.iloc[:35])

        # Compare row 30 in both
        for col in full_features.columns:
            val_full = full_features[col].iloc[30]
            val_trunc = truncated_features[col].iloc[30]
            if np.isnan(val_full):
                assert np.isnan(val_trunc), f"NaN mismatch on {col} at row 30"
            else:
                assert val_full == pytest.approx(val_trunc), f"Lookahead mismatch on {col} at row 30"


class TestMarketStructureStateMachine:
    """Tests for trend classification, Higher Highs/Lows, BOS, and CHoCH."""

    def test_hh_and_hl_trend_classification(self, sample_ohlc_df):
        """Verify HH and HL identification and trend state transitions."""
        engine = MarketStructureEngine(swing_left_bars=5, swing_right_bars=5)
        features = engine.compute_features(sample_ohlc_df)

        # High 1 at bar 10 confirmed at bar 15 (price = 2051.0)
        # Low 1 at bar 20 confirmed at bar 25 (price = 2009.0)
        # High 2 at bar 30 confirmed at bar 35 (price = 2061.0 > 2051.0) -> HH!
        assert features["ms_is_new_swing_high"].iloc[35] == 1
        assert features["ms_swing_high_type"].iloc[35] == 1  # 1=HH

        # Low 2 at bar 40 confirmed at bar 45 (price = 2024.0 > 2009.0) -> HL!
        assert features["ms_is_new_swing_low"].iloc[45] == 1
        assert features["ms_swing_low_type"].iloc[45] == 1  # 1=HL

        # Once both HH and HL are confirmed, trend must be Bullish (+1)
        assert features["ms_trend_state"].iloc[45] == 1

    def test_bos_detection(self, sample_ohlc_df):
        """When price crosses above the confirmed swing high, BOS or CHoCH is triggered."""
        engine = MarketStructureEngine(swing_left_bars=5, swing_right_bars=5)
        features = engine.compute_features(sample_ohlc_df)

        # First swing high is confirmed at bar 15 (price = 2051.0)
        # Between bars 21..30, price rises from 2010 to 2060.
        # At some bar in 21..30, close exceeds 2051.0, triggering break of structure!
        bos_or_choch_sum = (features["ms_bos_bullish"] + features["ms_choch_bullish"]).sum()
        assert bos_or_choch_sum >= 1


class TestFairValueGaps:
    """Tests for causal Fair Value Gap detection and mitigation."""

    def test_bullish_fvg_formation_and_mitigation(self):
        """Bullish FVG: Low[t] > High[t-2]. Formed at bar t, mitigated when price drops to gap."""
        base_time = pd.Timestamp("2024-01-08 00:00:00+00:00")
        timestamps = [base_time + pd.Timedelta(minutes=5 * i) for i in range(10)]

        # Bar 0: Low=2000, High=2005
        # Bar 1: Huge displacement upward Open=2005, High=2025, Low=2004, Close=2024
        # Bar 2: Open=2024, Low=2015, High=2030, Close=2028 -> Low[2]=2015 > High[0]=2005!
        # Gap is [2005, 2015], size=10.0
        # Bar 3: stays above (Low=2018) -> active
        # Bar 4: drops into gap (Low=2004 <= 2005) -> mitigated!
        df = pd.DataFrame(
            {
                "open": [2001, 2005, 2024, 2025, 2020, 2004, 2010, 2010, 2010, 2010],
                "high": [2005, 2025, 2030, 2030, 2025, 2010, 2015, 2015, 2015, 2015],
                "low":  [2000, 2004, 2015, 2018, 2012, 2004, 2008, 2008, 2008, 2008],
                "close": [2004, 2024, 2028, 2022, 2018, 2008, 2012, 2012, 2012, 2012],
                "volume": [100] * 10,
            },
            index=pd.DatetimeIndex(timestamps),
        )

        engine = MarketStructureEngine(swing_left_bars=2, swing_right_bars=2)
        features = engine.compute_features(df)

        # Bar 2 forms bullish FVG
        assert features["ms_fvg_bullish_formed"].iloc[2] == 1
        assert features["ms_active_fvg_bullish_count"].iloc[2] == 1

        # Bar 3 maintains active FVG
        assert features["ms_active_fvg_bullish_count"].iloc[3] == 1

        # Bar 5 low=2004 dips <= 2005 (mitigated!)
        assert features["ms_active_fvg_bullish_count"].iloc[5] == 0


class TestLiquiditySweepsAndReclaims:
    """Tests for liquidity sweep and sweep-and-reclaim price patterns."""

    def test_liquidity_sweep_high(self):
        """High pierces swing high, but close finishes below it."""
        base_time = pd.Timestamp("2024-01-08 00:00:00+00:00")
        timestamps = [base_time + pd.Timedelta(minutes=5 * i) for i in range(20)]

        # Establish confirmed swing high at bar 2 (confirmed at bar 5 with N_L=2, N_R=2, price=2050)
        highs = [2040, 2045, 2050, 2045, 2040, 2042, 2044, 2046, 2055, 2048] + [2040] * 10
        lows  = [h - 5.0 for h in highs]
        opens = [h - 3.0 for h in highs]
        closes = [h - 2.0 for h in highs]
        # At bar 8: High=2055 > 2050, but Close=2048 < 2050 -> Sweep!
        closes[8] = 2048.0
        lows[8] = 2042.0

        df = pd.DataFrame(
            {"open": opens, "high": highs, "low": lows, "close": closes, "volume": 100},
            index=pd.DatetimeIndex(timestamps),
        )
        engine = MarketStructureEngine(swing_left_bars=2, swing_right_bars=2)
        features = engine.compute_features(df)

        # Bar 8 sweeps swing high
        assert features["ms_sweep_high"].iloc[8] == 1


class TestPremiumDiscountDealingRange:
    """Tests for equilibrium price and premium/discount percentile."""

    def test_dealing_range_calculations(self, sample_ohlc_df):
        """Range between confirmed swing high and swing low."""
        engine = MarketStructureEngine(swing_left_bars=5, swing_right_bars=5)
        features = engine.compute_features(sample_ohlc_df)

        # After both high (bar 10 confirmed bar 15) and low (bar 20 confirmed bar 25) are known:
        # High = 2051.0, Low = 2009.0 -> Eq = 2030.0
        assert not np.isnan(features["ms_equilibrium_price"].iloc[26])
        eq = features["ms_equilibrium_price"].iloc[26]
        assert eq == pytest.approx(2030.0, abs=1.0)

        # At bar 26, close is ~2040 (which is > 2030) -> Premium
        assert features["ms_in_premium"].iloc[26] == 1
        assert features["ms_in_discount"].iloc[26] == 0
