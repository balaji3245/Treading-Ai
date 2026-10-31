# Phase 33: Multi-Timeframe Swing Hypothesis Pre-Registration

**Document Type:** Quantitative Research Specification & Hypothesis Pre-Registration  
**Asset Class:** Spot Gold (XAUUSD)  
**Execution Context:** Swing Trading (Multi-Hour to Multi-Day Holding Periods)  
**Timeframes:** 4-Hour (H4) Execution / 1-Day (D1) Macro Regime  
**Status:** FROZEN & PRE-REGISTERED (Prior to any outcome or profitability testing)  
**Research Date:** November 2026  

---

## 1. Executive Summary & Research Governance

This document establishes the pre-registered scientific specification for three candidate swing-trading hypotheses in spot gold (XAUUSD). To safeguard against data snooping, p-hacking, and post-hoc rationalization, all hypotheses, mathematical indicators, entry/exit rules, holding horizons, transaction cost tiers, and falsification criteria are formally codified **prior to conducting any outcome analysis or strategy backtesting**.

### Research Integrity Principles:
1. **No Profitability Testing in Phase 33:** This phase engineers causal features and pre-registers hypotheses. Zero backtests, equity curve evaluations, or parameter optimizations were executed.
2. **Exploratory Status of 2021–2022 Data:** The 2021–2022 dataset has been used in earlier exploratory phases (Phase 2–31). It is strictly treated as exploratory development data. Pre-registration does not eliminate historical data-mining bias on this partition.
3. **Protected Partitions Untouched:** The 2025 Validation (`val.parquet`) and 2026 Test (`test.parquet`) partitions remain strictly quarantined and unread.
4. **Hypothesis Cap:** Exactly three economically motivated hypotheses are pre-registered below.

---

## 2. Hypothesis 1 (H-Swing-01): D1 Trend Regime Filtered H4 Pullback Continuation

### 2.1 Economic Rationale
Gold (XAUUSD) is a macro-driven asset heavily influenced by real interest rates, US dollar liquidity cycles, and institutional asset allocation. Macro trends on the Daily (D1) timeframe exhibit multi-week inertia driven by sovereign reserve flows and macroeconomic repricing. Within an established macro trend, shorter-term liquidity fluctuations (e.g., intra-week margin rebalancing, session-specific news events) periodically cause temporary counter-trend pullbacks on the H4 timeframe. Once counter-trend selling or buying exhausts into dynamic support/resistance (20-period EMA), institutional liquidity re-engages in the direction of the dominant macro regime.

### 2.2 Exact Feature Definitions
All features are defined causally at the close of H4 candle $t$ (`h4_decision_ts`):
1. **Macro Trend Regime ($d1\_trend\_regime$):**
   $$\text{EMA}_{20}(D1) > \text{EMA}_{50}(D1) \implies +1 \quad (\text{Bullish})$$
   $$\text{EMA}_{20}(D1) < \text{EMA}_{50}(D1) \implies -1 \quad (\text{Bearish})$$
   Evaluated strictly on the latest completed D1 candle ($d1\_available\_ts \le h4\_decision\_ts$).
2. **Macro Trend Slope ($d1\_trend\_slope\_20$):**
   $$\frac{\text{EMA}_{20}(D1)_D - \text{EMA}_{20}(D1)_{D-5}}{\text{EMA}_{20}(D1)_{D-5}} > 0 \quad (\text{for Longs}), \quad < 0 \quad (\text{for Shorts})$$
3. **H4 Pullback Depth Normalized by ATR ($h4\_pullback\_depth\_atr$):**
   $$\text{PullbackDepth}_{t} = \frac{\text{Close}_{t} - \text{EMA}_{20}(H4)_{t}}{\text{ATR}_{14}(H4)_{t}}$$
   - Long setup requires a discount pullback: $-1.50 \le \text{PullbackDepth}_{t} \le -0.25$.
   - Short setup requires a premium pullback: $+0.25 \le \text{PullbackDepth}_{t} \le +1.50$.
4. **H4 Candlestick Exhaustion & Reversal Confirmation:**
   - Long setup: Bullish reversal candle ($Close_t > Open_t$) with lower wick absorbing liquidity:
     $$\text{h4\_lower\_wick\_ratio}_t = \frac{\min(Open_t, Close_t) - Low_t}{High_t - Low_t} \ge 0.25$$
   - Short setup: Bearish reversal candle ($Close_t < Open_t$) with upper wick rejecting liquidity:
     $$\text{h4\_upper\_wick\_ratio}_t = \frac{High_t - \max(Open_t, Close_t)}{High_t - Low_t} \ge 0.25$$
5. **Eligibility Flag:** $\text{swing\_signal\_eligible}_t == \text{True}$.

### 2.3 Signal & Earliest Permitted Entry Timestamp
- **Signal Generation:** Evaluated at the exact close of H4 candle $t$ (`h4_decision_ts`).
- **Earliest Permitted Entry:** At the open of H4 candle $t+1$ (`timestamp + 4h`). Zero execution within the formation candle.

### 2.4 Directional Rules
- **Long Entry Rule:**
  - $d1\_trend\_regime == +1$
  - $d1\_trend\_slope\_20 > 0.0$
  - $-1.50 \le h4\_pullback\_depth\_atr \le -0.25$
  - $Close_t > Open_t$ and $h4\_lower\_wick\_ratio \ge 0.25$
  - $\text{swing\_signal\_eligible} == \text{True}$
- **Short Entry Rule:**
  - $d1\_trend\_regime == -1$
  - $d1\_trend\_slope\_20 < 0.0$
  - $+0.25 \le h4\_pullback\_depth\_atr \le +1.50$
  - $Close_t < Open_t$ and $h4\_upper\_wick\_ratio \ge 0.25$
  - $\text{swing\_signal\_eligible} == \text{True}$

### 2.5 Holding Period Definition
- Minimum holding duration: 1 H4 bar (4 hours).
- Target holding duration: 3 to 12 H4 bars (12 to 48 hours).
- Maximum holding period (Time Stop): 18 H4 bars (72 hours / 3 trading days).

### 2.6 Target and Stop Methodology
- **Initial Protective Stop Loss:**
  - Long: $\text{Entry} - 1.50 \times \text{ATR}_{14}(H4)_t$.
  - Short: $\text{Entry} + 1.50 \times \text{ATR}_{14}(H4)_t$.
- **Take-Profit Target:**
  - Long: $\text{Entry} + 3.00 \times \text{ATR}_{14}(H4)_t$ (Reward-to-Risk ratio = 2.0:1).
  - Short: $\text{Entry} - 3.00 \times \text{ATR}_{14}(H4)_t$ (Reward-to-Risk ratio = 2.0:1).

### 2.7 Exit Conditions
Position is liquidated immediately at the first occurrence of:
1. Protective Stop Loss hit (intra-bar breach of stop level).
2. Take-Profit Target hit (intra-bar breach of target level).
3. Trend Invalidation Exit: If $d1\_trend\_regime$ flips opposite to position direction at any completed D1 close.
4. Time Stop: Position closed at market after 18 H4 bars if neither target nor stop has been triggered.

### 2.8 Expected Trade Frequency & Sample Size
- Expected frequency: 35 to 55 trades per year.
- Expected 2-year development sample (2021–2022): 70 to 110 trades.
- Statistical concern: Low sample size increases variance in Sharpe and Calmar ratios. Evaluation requires rigorous bootstrap resampling.

### 2.9 Main Failure Modes
- **Chop / Whip-saw Regimes:** Consecutive false macro trend signals when gold oscillates in a prolonged multi-week trading range.
- **Deep Liquidity Cascades:** Pullbacks that fail to find support at EMA20 and collapse through stop loss due to unexpected geopolitical de-escalation or hawkish Fed shocks.
- **Weekend Rollover Gaps:** Price gaps over the weekend bypassing stop loss.

### 2.10 Transaction-Cost Assumptions & Sensitivity
- Must be evaluated across the three unverified swap tiers: $0.08, $0.12, and $0.18/oz/day financing cost.
- Spread friction: Baseline 2.5 pips ($0.25/oz), stressed up to 4.0 pips ($0.40/oz).
- Slippage allowance: 1.0 pip ($0.10/oz).

### 2.11 Conditions That Would Falsify the Hypothesis
The hypothesis is falsified if:
- Net expectancy across all trades after baseline costs ($0.12 swap, 2.5 pip spread) is $\le \$0.00/\text{oz}$.
- Win rate is $< 35\%$ with a 2:1 profit-to-loss target.
- Long and short components diverge radically (e.g., Long Sharpe $> 1.0$ while Short Sharpe $< -0.5$).
- Maximum peak-to-trough drawdown exceeds $15.0\%$ of capital.

### 2.12 Evaluation Criteria
- Annualized Net Sharpe Ratio $\ge 0.60$ after full friction.
- Net Profit Factor $\ge 1.30$.
- Bootstrap $p$-value $< 0.05$ against a zero-expectancy permutation baseline.

---

## 3. Hypothesis 2 (H-Swing-02): H4 Volatility Breakout Conditioned on D1 Volatility Compression

### 3.1 Economic Rationale
Financial markets alternate between phases of volatility compression (consolidation, inventory absorption, order book balance) and volatility expansion (liquidity cascades, momentum runs, structural repricing). When spot gold enters an extended period of daily volatility compression (where short-term ATR contracts significantly below long-term ATR), capital accumulates along key chart boundaries. An explosive breakout on the H4 timeframe accompanied by an expansion in True Range signals the resolution of the consolidation regime and the inception of a directional swing expansion.

### 3.2 Exact Feature Definitions
1. **D1 Volatility Compression Ratio ($d1\_vol\_compression\_ratio$):**
   $$\text{CompressionRatio}_D = \frac{\text{ATR}_{10}(D1)_D}{\text{ATR}_{50}(D1)_D} < 0.85$$
   Indicates that 10-day daily volatility has compressed by at least 15% below its 50-day average. Evaluated causally from completed D1 candle.
2. **H4 True Range Expansion ($h4\_tr\_expansion$):**
   $$\text{TRExpansion}_t = \frac{\text{TR}(H4)_t}{\text{RollingMedian}_{20}(\text{TR}(H4))_t} \ge 1.40$$
   Requires current H4 bar True Range to expand by at least 40% above its 20-bar median.
3. **20-Period H4 Donchian Breakout ($h4\_channel\_breakout\_long$, $h4\_channel\_breakout\_short$):**
   $$\text{DonchianHigh20}_t = \max_{i=1}^{20} High_{t-i}$$
   $$\text{DonchianLow20}_t = \min_{i=1}^{20} Low_{t-i}$$
   - Bullish Breakout: $Close_t > \text{DonchianHigh20}_t$.
   - Bearish Breakout: $Close_t < \text{DonchianLow20}_t$.
   (Note: The Donchian channels are strictly shifted by 1 bar to prevent current bar contamination).
4. **Candlestick Directional Impulsion:**
   - Long: $Close_t - Open_t \ge 0.60 \times (High_t - Low_t)$ (strong bull body).
   - Short: $Open_t - Close_t \ge 0.60 \times (High_t - Low_t)$ (strong bear body).
5. **Eligibility Flag:** $\text{swing\_signal\_eligible}_t == \text{True}$.

### 3.3 Signal & Earliest Permitted Entry Timestamp
- **Signal Timestamp:** Close of breakout H4 bar $t$ (`h4_decision_ts`).
- **Earliest Permitted Entry:** Open of H4 bar $t+1$.

### 3.4 Directional Rules
- **Long Entry Rule:**
  - $d1\_vol\_compression\_ratio < 0.85$
  - $h4\_tr\_expansion \ge 1.40$
  - $Close_t > \text{DonchianHigh20}_t$
  - $h4\_body\_ratio_t \ge 0.60$ and $Close_t > Open_t$
  - $\text{swing\_signal\_eligible} == \text{True}$
- **Short Entry Rule:**
  - $d1\_vol\_compression\_ratio < 0.85$
  - $h4\_tr\_expansion \ge 1.40$
  - $Close_t < \text{DonchianLow20}_t$
  - $h4\_body\_ratio_t \ge 0.60$ and $Close_t < Open_t$
  - $\text{swing\_signal\_eligible} == \text{True}$

### 3.5 Holding Period Definition
- Minimum holding duration: 2 H4 bars (8 hours).
- Target holding duration: 6 to 18 H4 bars (24 to 72 hours).
- Maximum holding period: 24 H4 bars (96 hours / 4 trading days).

### 3.6 Target and Stop Methodology
- **Initial Protective Stop Loss:**
  - Placed at the opposite extreme of the breakout candle:
    - Long: $\text{Low}_t - 0.25 \times \text{ATR}_{14}(H4)_t$.
    - Short: $\text{High}_t + 0.25 \times \text{ATR}_{14}(H4)_t$.
- **Trailing Stop:**
  - Once price reaches $+1.50 \times \text{Risk}$, move stop loss to Breakeven ($\text{Entry}$).
  - Trail behind the 10-period EMA of H4.
- **Profit Target:** Dynamic exit via trailing stop or 24-bar time stop.

### 3.7 Exit Conditions
1. Trailing stop or initial stop triggered.
2. Invalidation: H4 candle closes back inside the Donchian channel.
3. Time Stop: 24 H4 bars elapsed.

### 3.8 Expected Trade Frequency & Sample Size
- Expected frequency: 20 to 35 trades per year.
- Expected 2-year development sample (2021–2022): 40 to 70 trades.
- High selectivity, low trade frequency.

### 3.9 Main Failure Modes
- **False Breakouts ("Bull/Bear Traps"):** Breakout triggers stop-hunt above previous highs, followed by immediate mean-reversion back into the range.
- **High Volatility Slippage:** Breakout candles often close rapidly during London/New York overlap, risking execution slippage at market open.

### 3.10 Transaction-Cost Assumptions & Sensitivity
- Overnight swaps over 2 to 4 days require robustness under $0.18/oz/day tier.
- Entry slippage must be modeled at 1.5 pips ($0.15/oz) to account for momentum order fill degradation.

### 3.11 Conditions That Would Falsify the Hypothesis
- Net expectancy after costs $\le \$0.00/\text{oz}$.
- Win rate $< 30\%$ and average win/loss ratio $< 2.2$.
- Over 60% of breakout trades reversed into stop loss within 2 bars.

### 3.12 Evaluation Criteria
- Annualized Net Sharpe Ratio $\ge 0.55$.
- Net Profit Factor $\ge 1.35$.
- Average trade duration $\ge 16$ hours (confirming swing capture rather than scalping noise).

---

## 4. Hypothesis 3 (H-Swing-03): Multi-Day Mean Reversion to Dynamic D1 Value Zone in Low-Trend Regime

### 4.1 Economic Rationale
In the absence of strong macroeconomic trends (e.g., during neutral central bank policy windows or balanced physical gold demand), spot gold oscillates within bounded value areas determined by institutional inventory balancing. When daily trend strength is demonstrably weak (ADX < 20.0), extreme extensions of H4 prices away from the 20-day daily moving average represent temporary liquidity over-extensions. These extremes are subject to mean-reverting gravitational pull back toward the D1 value anchor (20-day EMA).

### 4.2 Exact Feature Definitions
1. **D1 Trend Strength Filter ($d1\_adx\_14$):**
   $$d1\_adx\_14_D < 20.0$$
   Confirms that the daily market is in a non-trending, range-bound regime. Evaluated from completed D1 candle.
2. **Cross-Timeframe Extension Z-Score ($cross\_h4\_d1\_zscore$):**
   $$\text{CrossZScore}_t = \frac{\text{Close}(H4)_t - \text{EMA}_{20}(D1)_D}{\text{RollingStd}_{20}(D1)_D}$$
   - Overbought Threshold: $\text{CrossZScore}_t \ge +2.00$.
   - Oversold Threshold: $\text{CrossZScore}_t \le -2.00$.
3. **H4 Momentum Divergence / Exhaustion ($h4\_rsi\_14$):**
   - For Short (Overbought): $h4\_rsi\_14_t \ge 70.0$ and $Close_t < Open_t$ (bearish exhaustion candle).
   - For Long (Oversold): $h4\_rsi\_14_t \le 30.0$ and $Close_t > Open_t$ (bullish exhaustion candle).
4. **Eligibility Flag:** $\text{swing\_signal\_eligible}_t == \text{True}$.

### 4.3 Signal & Earliest Permitted Entry Timestamp
- **Signal Timestamp:** Close of exhaustion H4 bar $t$ (`h4_decision_ts`).
- **Earliest Permitted Entry:** Open of H4 bar $t+1$.

### 4.4 Directional Rules
- **Long Entry Rule (Oversold Mean Reversion):**
  - $d1\_adx\_14 < 20.0$
  - $cross\_h4\_d1\_zscore \le -2.00$
  - $h4\_rsi\_14 \le 30.0$ and $Close_t > Open_t$
  - $\text{swing\_signal\_eligible} == \text{True}$
- **Short Entry Rule (Overbought Mean Reversion):**
  - $d1\_adx\_14 < 20.0$
  - $cross\_h4\_d1\_zscore \ge +2.00$
  - $h4\_rsi\_14 \ge 70.0$ and $Close_t < Open_t$
  - $\text{swing\_signal\_eligible} == \text{True}$

### 4.5 Holding Period Definition
- Minimum holding duration: 2 H4 bars (8 hours).
- Target holding duration: 6 to 18 H4 bars (24 to 72 hours).
- Maximum holding period: 18 H4 bars (72 hours).

### 4.6 Target and Stop Methodology
- **Take-Profit Target (Value Anchor):**
  - Exit when H4 price reaches the completed 20-day D1 EMA: $\text{EMA}_{20}(D1)_D$.
- **Protective Stop Loss:**
  - Long: $\text{Entry} - 1.75 \times \text{ATR}_{14}(H4)_t$.
  - Short: $\text{Entry} + 1.75 \times \text{ATR}_{14}(H4)_t$.

### 4.7 Exit Conditions
1. Price crosses the D1 20-day EMA value anchor.
2. Protective stop loss breached.
3. Regime Invalidation: $d1\_adx\_14$ rises above $25.0$ at a subsequent D1 close (indicating trend breakout).
4. Time Stop: 18 H4 bars elapsed.

### 4.8 Expected Trade Frequency & Sample Size
- Expected frequency: 15 to 30 trades per year.
- Expected 2-year development sample (2021–2022): 30 to 60 trades.

### 4.9 Main Failure Modes
- **Runaway Trend Transition:** Regime transitions abruptly from consolidation to violent trend breakout due to unexpected geopolitical escalation or emergency monetary policy actions.
- **Persistent Volatility Expansion:** Prolonged dislocation where price stays beyond 2 standard deviations for multiple weeks.

### 4.10 Transaction-Cost Assumptions & Sensitivity
- Multi-day holding in spot gold exposes mean reversion to adverse swap decay. Must be robust under the $0.18/oz/day swap scenario.

### 4.11 Conditions That Would Falsify the Hypothesis
- Net expectancy after costs $\le \$0.00/\text{oz}$.
- Win rate $< 45\%$ (mean-reversion strategies typically require $\ge 50\%$ win rate given sub-2.0 payoff ratios).
- Max drawdown $> 12.0\%$.

### 4.12 Evaluation Criteria
- Annualized Net Sharpe Ratio $\ge 0.65$.
- Net Profit Factor $\ge 1.30$.
- Positive net payoff after deducting 3 days of financing swap.

---

## 5. Comparative Hypothesis Matrix

| Property | Hypothesis 1 (`H-Swing-01`) | Hypothesis 2 (`H-Swing-02`) | Hypothesis 3 (`H-Swing-03`) |
| :--- | :--- | :--- | :--- |
| **Family** | Trend Pullback Continuation | Volatility Breakout | Range Mean Reversion |
| **Macro Driver** | D1 EMA Trend + Slope | D1 ATR Compression | D1 Low ADX Regime |
| **Execution Trigger** | H4 EMA20 Pullback + Wick | H4 Donchian Break + TR Spike | H4 Z-Score Extension + RSI |
| **Holding Horizon** | 12 to 72 Hours | 24 to 96 Hours | 24 to 72 Hours |
| **Reward/Risk Ratio** | ~2.0 : 1 | Dynamic (Trailing Stop) | ~1.2 : 1 to 1.5 : 1 |
| **Expected Annual Trades** | 35 – 55 | 20 – 35 | 15 – 30 |
| **Primary Risk** | Deep liquidation cascades | False breakout bull/bear traps | Runaway trend transition |
| **Falsification Metric** | Net Expectancy $\le \$0.00$ | Net Expectancy $\le \$0.00$ | Net Expectancy $\le \$0.00$ |

---

## 6. Pre-Registration Declaration & Attestation

We hereby attest that:
1. Hypotheses `H-Swing-01`, `H-Swing-02`, and `H-Swing-03` were formulated and finalized **prior to running any backtest, performance simulation, or parameter optimization**.
2. Thresholds ($0.85$ compression, $1.40$ TR expansion, $\pm 2.0$ Z-score, $20.0$ ADX) are fixed economic heuristics, not optimized constants.
3. No strategy profitability claims are made in this document.
4. Evaluation is deferred to a future phase in accordance with `evaluation_protocol.md`.
