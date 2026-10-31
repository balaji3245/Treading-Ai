# Phase 33: Multi-Timeframe Feature Dictionary

**System:** Treading-Ai Quantitative Research Engine  
**Asset:** Spot Gold (XAUUSD)  
**Pipeline Module:** `src/treading_ai/features/swing_features.py`  
**Temporal Resolution:** Dual-Timeframe (H4 Execution Bars & D1 Macro Bars)  
**Date:** November 2026  

---

## 1. Overview & Architectural Principles

The Phase 33 feature pipeline constructs stationary, causal, and scale-invariant quantitative signals designed specifically for multi-day swing hypothesis evaluation. 

### Mandatory Invariants:
1. **Decision Causality:** A feature associated with decision timestamp $T$ uses only market observations finalized strictly at or before $T$.
2. **Explicit Timestamps:** Every row carries an explicit execution decision timestamp (`h4_decision_ts`) and an explicit macro data availability timestamp (`d1_available_ts`).
3. **Session Alignment:** Daily (D1) bars close at 17:00:00 New York Time (21:00 UTC during EDT, 22:00 UTC during EST). An H4 candle closing prior to 17:00 NY merges strictly with the $D-1$ daily bar.
4. **Stationarity:** Raw price levels are converted to returns, percentage ATR, normalized z-scores, or geometric ratios to ensure statistical stationarity across multi-year regimes.
5. **No Lookahead:** All rolling channel extremes (Donchian) are shifted by 1 period so that the bar being evaluated does not contribute to its own boundary.

---

## 2. Daily (D1) Feature Specifications

Daily features capture the structural macroeconomic, trend, and volatility regime of the gold market. Extracted via `D1FeatureExtractor`.

| Feature Name | Type | Mathematical Formula | Lookback | Stationarity | Description & Role |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `d1_available_ts` | `datetime64[ns, UTC]` | $\text{Timestamp}_{\text{date}} + 17:00 \text{ NY} \to \text{UTC}$ | N/A | Deterministic | The exact UTC instant when the D1 session finalized. Used as the right-hand key in backward `merge_asof`. |
| `d1_ret_1` | `float64` | $(C_D - C_{D-1}) / C_{D-1}$ | 1 day | Stationary | 1-day percentage return. |
| `d1_ret_3` | `float64` | $(C_D - C_{D-3}) / C_{D-3}$ | 3 days | Stationary | 3-day percentage return capturing multi-day momentum. |
| `d1_ret_5` | `float64` | $(C_D - C_{D-5}) / C_{D-5}$ | 5 days | Stationary | 1-week percentage return. |
| `d1_ret_10` | `float64` | $(C_D - C_{D-10}) / C_{D-10}$ | 10 days | Stationary | 2-week percentage return. |
| `d1_ema_10` | `float64` | $\text{EMA}(C, \text{span}=10)$ | 10 days | Non-stationary | Fast daily moving average. |
| `d1_ema_20` | `float64` | $\text{EMA}(C, \text{span}=20)$ | 20 days | Non-stationary | Intermediate daily baseline and swing anchor. |
| `d1_ema_50` | `float64` | $\text{EMA}(C, \text{span}=50)$ | 50 days | Non-stationary | Macro trend filter boundary. |
| `d1_trend_regime` | `int32` | $\begin{cases} +1 & \text{EMA}_{20} > \text{EMA}_{50} \\ -1 & \text{EMA}_{20} < \text{EMA}_{50} \\ 0 & \text{otherwise} \end{cases}$ | 50 days | Stationary discrete | Dominant macro trend direction. Filters counter-trend swing trades. |
| `d1_trend_slope_20`| `float64` | $(\text{EMA}_{20, D} - \text{EMA}_{20, D-5}) / \text{EMA}_{20, D-5}$ | 5 days | Stationary | 5-day rate of change of 20-day EMA. Confirms trend acceleration. |
| `d1_tr` | `float64` | $\max(H_D - L_D, \|H_D - C_{D-1}\|, \|L_D - C_{D-1}\|)$ | 1 day | Scale-variant | Daily True Range in USD/oz. |
| `d1_atr_14` | `float64` | $\text{EWM}_{\alpha=1/14}(TR)$ | 14 days | Scale-variant | 14-day Wilder smoothed Average True Range in USD/oz. |
| `d1_atr_pct` | `float64` | $\text{ATR}_{14} / C_D$ | 14 days | Stationary | Volatility as a percentage of spot price. |
| `d1_atr_10` | `float64` | $\text{EWM}_{\alpha=1/10}(TR)$ | 10 days | Scale-variant | Fast ATR measuring short-term daily volatility. |
| `d1_atr_50` | `float64` | $\text{EWM}_{\alpha=1/50}(TR)$ | 50 days | Scale-variant | Slow ATR measuring baseline macro volatility. |
| `d1_vol_compression_ratio` | `float64` | $\text{ATR}_{10} / (\text{ATR}_{50} + \epsilon)$ | 50 days | Stationary | Ratio of fast to slow volatility. Values $< 0.85$ indicate volatility compression. |
| `d1_rolling_std_20`| `float64` | $\sqrt{\frac{1}{20}\sum (C_i - \bar{C})^2}$ | 20 days | Scale-variant | 20-day rolling standard deviation of daily closes. |
| `d1_adx_14` | `float64` | Wilder's $\text{ADX}(14)$ | 14 days | Stationary $[0, 100]$ | Average Directional Index. Values $< 20.0$ indicate non-trending, range-bound regimes. |
| `d1_donchian_high_20` | `float64` | $\max_{i=1}^{20} High_{D-i}$ | 20 days | Non-stationary | Highest high of preceding 20 days (shifted by 1 bar). |
| `d1_donchian_low_20` | `float64` | $\min_{i=1}^{20} Low_{D-i}$ | 20 days | Non-stationary | Lowest low of preceding 20 days (shifted by 1 bar). |

---

## 3. 4-Hour (H4) Feature Specifications

H4 features capture intermediate-horizon price action, swing pullbacks, candlestick geometry, and local breakout dynamics. Extracted via `H4FeatureExtractor`.

| Feature Name | Type | Mathematical Formula | Lookback | Stationarity | Description & Role |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `h4_decision_ts` | `datetime64[ns, UTC]` | $\text{Timestamp}_t + 4\text{ hours}$ | N/A | Deterministic | The exact UTC instant when the H4 bar closed and signals can be acted upon. |
| `h4_ret_1` | `float64` | $(C_t - C_{t-1}) / C_{t-1}$ | 4 hours | Stationary | 1-bar percentage return. |
| `h4_ret_3` | `float64` | $(C_t - C_{t-3}) / C_{t-3}$ | 12 hours | Stationary | 3-bar (half-day) percentage return. |
| `h4_ret_6` | `float64` | $(C_t - C_{t-6}) / C_{t-6}$ | 24 hours | Stationary | 6-bar (1 full day) percentage return. |
| `h4_ret_12` | `float64` | $(C_t - C_{t-12}) / C_{t-12}$ | 48 hours | Stationary | 12-bar (2 full days) percentage return. |
| `h4_ema_10` | `float64` | $\text{EMA}(C, \text{span}=10)$ | 40 hours | Non-stationary | Short-term trend guide and trailing stop benchmark. |
| `h4_ema_20` | `float64` | $\text{EMA}(C, \text{span}=20)$ | 80 hours | Non-stationary | Intermediate dynamic support/resistance benchmark. |
| `h4_ema_50` | `float64` | $\text{EMA}(C, \text{span}=50)$ | 200 hours | Non-stationary | H4 baseline trend filter. |
| `h4_trend_regime` | `int32` | $\begin{cases} +1 & \text{EMA}_{20} > \text{EMA}_{50} \\ -1 & \text{EMA}_{20} < \text{EMA}_{50} \\ 0 & \text{otherwise} \end{cases}$ | 50 bars | Stationary discrete | H4 local trend regime. |
| `h4_tr` | `float64` | $\max(H_t - L_t, \|H_t - C_{t-1}\|, \|L_t - C_{t-1}\|)$ | 4 hours | Scale-variant | True Range of current H4 candle. |
| `h4_atr_14` | `float64` | $\text{EWM}_{\alpha=1/14}(TR)$ | 56 hours | Scale-variant | 14-bar Wilder smoothed ATR in USD/oz. Used for position sizing and stop distance. |
| `h4_atr_pct` | `float64` | $\text{ATR}_{14} / C_t$ | 56 hours | Stationary | ATR as percentage of spot price. |
| `h4_tr_expansion` | `float64` | $\text{TR}_t / (\text{RollingMedian}_{20}(\text{TR}) + \epsilon)$ | 80 hours | Stationary | True Range relative to rolling 20-bar median. Identifies volatility surges ($\ge 1.40$). |
| `h4_pullback_depth_atr` | `float64` | $(C_t - \text{EMA}_{20}) / (\text{ATR}_{14} + \epsilon)$ | 80 hours | Stationary | Distance of close from EMA20 normalized by ATR. Quantifies pullback discount/premium. |
| `h4_body_ratio` | `float64` | $\|C_t - O_t\| / (H_t - L_t + \epsilon)$ | 4 hours | Stationary $[0, 1]$ | Proportion of candle range occupied by the real body. Measures candle conviction. |
| `h4_upper_wick_ratio` | `float64` | $(H_t - \max(O_t, C_t)) / (H_t - L_t + \epsilon)$ | 4 hours | Stationary $[0, 1]$ | Proportion of candle range occupied by upper shadow. Measures overhead selling rejection. |
| `h4_lower_wick_ratio` | `float64` | $(\min(O_t, C_t) - L_t) / (H_t - L_t + \epsilon)$ | 4 hours | Stationary $[0, 1]$ | Proportion of candle range occupied by lower shadow. Measures buying absorption. |
| `h4_donchian_high_20` | `float64` | $\max_{i=1}^{20} High_{t-i}$ | 80 hours | Non-stationary | Highest high of previous 20 H4 bars (shifted by 1 bar). |
| `h4_donchian_low_20` | `float64` | $\min_{i=1}^{20} Low_{t-i}$ | 80 hours | Non-stationary | Lowest low of previous 20 H4 bars (shifted by 1 bar). |
| `h4_channel_breakout_long` | `float64` | $(C_t - \text{DonchianHigh}_{20}) / (\text{ATR}_{14} + \epsilon)$ | 80 hours | Stationary | Normalized distance above upper Donchian boundary. $>0$ indicates bullish breakout. |
| `h4_channel_breakout_short` | `float64` | $(\text{DonchianLow}_{20} - C_t) / (\text{ATR}_{14} + \epsilon)$ | 80 hours | Stationary | Normalized distance below lower Donchian boundary. $>0$ indicates bearish breakout. |
| `h4_rsi_14` | `float64` | Standard Wilder's $\text{RSI}(14)$ | 56 hours | Stationary $[0, 100]$ | 14-period Relative Strength Index. Identifies local overbought ($\ge 70$) and oversold ($\le 30$) states. |

---

## 4. Cross-Timeframe Alignment & Completeness Features

Constructed by `MultiTimeframeSwingPipeline` via backward as-of alignment.

| Feature Name | Type | Mathematical Formula | Lookback | Stationarity | Description & Role |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `cross_trend_alignment` | `int32` | $\begin{cases} +1 & \text{h4\_regime} = +1 \land \text{d1\_regime} = +1 \\ -1 & \text{h4\_regime} = -1 \land \text{d1\_regime} = -1 \\ 0 & \text{divergent} \end{cases}$ | Combined | Stationary discrete | Multi-timeframe trend confluence indicator. Used to filter out conflicting signals. |
| `cross_h4_d1_zscore` | `float64` | $(C_t - \text{EMA}_{20}(D1)_D) / (\text{RollingStd}_{20}(D1)_D + \epsilon)$ | Combined | Stationary | Normalized statistical distance of H4 price from daily dynamic value anchor. Drives `H-Swing-03`. |
| `cross_vol_expansion_in_d1_compression` | `bool` | $\text{h4\_tr\_expansion} > 1.30 \land \text{d1\_vol\_compression\_ratio} < 0.80$ | Combined | Boolean | Confluence of local H4 expansion out of a daily consolidation base. Drives `H-Swing-02`. |
| `cross_pullback_in_d1_trend` | `bool` | $(\text{d1}=+1 \land \text{pb} < -0.5) \lor (\text{d1}=-1 \land \text{pb} > +0.5)$ | Combined | Boolean | Identifies whether an H4 pullback is aligned with the prevailing macro daily trend. Drives `H-Swing-01`. |
| `h4_eligible` | `bool` | `df_h4['is_complete']` | 1 bar | Boolean | Confirms H4 bar contains standard constituent 240 M1 bars (or valid 180 M1 rollover bar). |
| `d1_regular_session` | `bool` | `df_d1['bar_count'] >= 1350` | 1 day | Boolean | Confirms D1 session was an open 23-hour trading day (accommodating 1–5 quiet minutes). Excludes early holiday closes. |
| `swing_signal_eligible` | `bool` | `h4_eligible & d1_regular_session` | Combined | Boolean | Master filter: Only rows with `swing_signal_eligible == True` can generate trade signals. |

---

## 5. Hypothesis Feature Mapping

| Feature | `H-Swing-01` (Trend Pullback) | `H-Swing-02` (Volatility Breakout) | `H-Swing-03` (Range Mean Reversion) |
| :--- | :---: | :---: | :---: |
| `d1_trend_regime` | Primary Filter | — | — |
| `d1_trend_slope_20` | Primary Filter | — | — |
| `d1_vol_compression_ratio` | — | Primary Filter | — |
| `d1_adx_14` | — | — | Primary Filter |
| `h4_pullback_depth_atr` | Trigger Condition | — | — |
| `h4_body_ratio` | — | Confirmation | — |
| `h4_upper_wick_ratio` | Short Trigger | — | — |
| `h4_lower_wick_ratio` | Long Trigger | — | — |
| `h4_tr_expansion` | — | Trigger Condition | — |
| `h4_channel_breakout_long` | — | Long Trigger | — |
| `h4_channel_breakout_short` | — | Short Trigger | — |
| `cross_h4_d1_zscore` | — | — | Trigger Condition |
| `h4_rsi_14` | — | — | Exhaustion Trigger |
| `swing_signal_eligible` | Mandatory Gate | Mandatory Gate | Mandatory Gate |
