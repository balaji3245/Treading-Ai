# BACKTEST RESULTS: 2021–2022 DEVELOPMENT PARTITION

**Phase:** 22 — Controlled Development  
**Hypothesis ID:** `HYP-21-ASIAN-LONDON-EXPANSION`  
**Dataset:** 2021-01-01 to 2022-12-31 UTC (70,686 + 70,928 = 141,614 M5 bars)  
**Execution Timestamp:** 2026-10-30T02:57:33 UTC  
**Status:** In-Sample Development Evidence (NOT YET VALIDATED OUT-OF-SAMPLE)  

---

## 1. Executive Summary

A deterministic, event-based backtest of `HYP-21-ASIAN-LONDON-EXPANSION` was executed across the two-year development partition (2021–2022). Across 495 calendar trading days with valid prior 20-day ATR and Asian session boundaries, 124 days (25.05%) satisfied the frozen volatility compression criterion ($CR \le 0.281865$). 

From these 124 eligible days, 101 days produced a confirmed breakout during the 07:05–09:00 UTC window (81.45% trade participation rate). The strategy generated **+$42.44/oz net PnL** under 1.0× baseline costs ($0.25/oz round-turn), with a net Profit Factor of **1.263** and a win rate of **54.46%** (55 wins, 46 losses). Directional balance between Long (48 trades) and Short (53 trades) was nearly symmetric, with both sides generating positive net returns.

> [!WARNING]
> **DEVELOPMENT RESULTS DISCLAIMER:**  
> These metrics represent strictly in-sample development performance used to confirm engineering correctness and methodology viability. They do **NOT** prove statistical profitability, live alpha, or market predictive edge.

---

## 2. Participation & Trade Breakdown

| Metric | Count | Percentage |
| :--- | :--- | :--- |
| **Total Calendar Days Analyzed** | 495 days | 100.0% |
| **Eligible Compressed Days ($CR \le 0.281865$)** | 124 days | 25.05% |
| **Non-Compressed Days ($CR > 0.281865$)** | 371 days | 74.95% |
| **Executed Trades** | **101 trades** | 81.45% of eligible |
| **Compressed Days Without Breakout** | 23 days | 18.55% of eligible |
| **Long Trades** | 48 trades | 47.52% of trades |
| **Short Trades** | 53 trades | 52.48% of trades |

### Exit Reasons Breakdown
- **Scheduled Time Exit at 12:00:00 UTC Close:** **83 trades** (82.18%)
- **Stop-Loss Execution:** **18 trades** (17.82%)
- **Stop-Loss Gap Slippage:** 0 trades (0.0%)
- **Adverse Entry Gap Aborts:** 0 trades (0.0%)

---

## 3. Financial Performance Across Cost Tiers

### Exact Formula Definitions:
- **Gross PnL:** $\sum_{i=1}^{N} (\text{Exit Price}_i - \text{Entry Price}_i) \times \text{Direction}_i$
- **Net PnL:** $\text{Gross PnL} - (N \times C_{\text{round-turn}})$
- **Net Expectancy per Trade:** $\frac{\text{Net PnL}}{N}$
- **Net Profit Factor (PF):**
  $$\text{Net PF} = \frac{\sum_{i: \text{Net PnL}_i > 0} \text{Net PnL}_i}{\sum_{i: \text{Net PnL}_i < 0} |\text{Net PnL}_i|}$$
- **Maximum Drawdown:** Calculated on cumulative trade-by-trade net equity:
  $$\text{DD}_k = \max_{j \le k}(\text{CumNetPnL}_j) - \text{CumNetPnL}_k$$
  $$\text{Max DD} = \max_k (\text{DD}_k)$$

### Performance Table:

| Metric | 1.0× Baseline ($0.25/oz) | 1.5× Elevated ($0.375/oz) | 2.0× Stressed ($0.50/oz) |
| :--- | :--- | :--- | :--- |
| **Gross PnL ($/oz)** | **+$67.688** | **+$67.688** | **+$67.688** |
| **Total Friction ($/oz)** | $25.250 | $37.875 | $50.500 |
| **Net PnL ($/oz)** | **+$42.438** | **+$29.813** | **+$17.188** |
| **Net Expectancy / Trade ($/oz)** | **+$0.420** | **+$0.295** | **+$0.170** |
| **Winning Trades** | 55 (54.46%) | 54 (53.47%) | 51 (50.50%) |
| **Losing Trades** | 46 (45.54%) | 47 (46.53%) | 50 (49.50%) |
| **Scratch Trades ($0.00)** | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) |
| **Net Profit Factor** | **1.263** | **1.178** | **1.099** |
| **Maximum Drawdown ($/oz)** | **$30.659** | **$32.409** | **$34.231** |
| **Max Drawdown (% of price)** | 0.30% | 0.32% | 0.34% |

---

## 4. Directional Symmetry & Sub-Cohort Analysis

Performance was evaluated separately for Long and Short trades under the baseline 1.0× cost model to verify that returns are not driven by a structural market drift or single-direction anomaly.

| Cohort | Trade Count | Win Rate | Net PnL ($/oz) | Net Profit Factor | Avg Trade ($/oz) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Long Trades** | 48 | 54.17% (26W / 22L) | **+$13.926** | 1.171 | +$0.290 |
| **Short Trades** | 53 | 54.72% (29W / 24L) | **+$28.512** | 1.355 | +$0.538 |
| **Total** | **101** | **54.46% (55W / 46L)** | **+$42.438** | **1.263** | **+$0.420** |

Both directions exhibited profitable net expectancy, with Short trades showing slightly higher expectancy (+$0.538 vs +$0.290) and win rate (54.72% vs 54.17%).

---

## 5. Trade Return Distribution Statistics

Statistical properties of the trade-level net PnL distribution (1.0× cost assumption):

| Distribution Metric | Net Value ($/oz) |
| :--- | :--- |
| **Sample Size ($N$)** | 101 |
| **Mean** | +$0.420 |
| **Median** | +$0.520 |
| **Standard Deviation ($\sigma$)** | $9.324 |
| **Interquartile Range (IQR)** | $8.640 |
| **Minimum (Largest Loss)** | -$18.890 |
| **25th Percentile ($Q_1$)** | -$4.460 |
| **75th Percentile ($Q_3$)** | +$4.180 |
| **Maximum (Largest Win)** | +$31.390 |
| **Skewness** | +0.472 |
| **Kurtosis** | 2.186 |

The distribution exhibits moderate positive skewness (+0.472), reflecting the favorable asymmetric risk-reward of expansion breakouts (maximum win of +$31.39/oz versus maximum loss of -$18.89/oz).

---

## 6. Engineering Integrity Verifications

1. **Zero Look-Ahead Bias:**
   - Daily ATR20 computed on prior days strictly using `shift(1)`.
   - Compression threshold evaluated strictly at 07:00 UTC when Asian session closes.
   - Breakout verified on completed bar closes; trade executed on next bar Open.
2. **One Trade Per Day:**
   - Verified across all 495 calendar days. Exactly 101 days had 1 trade; 394 days had 0 trades. No day ever executed 2 or more trades.
3. **No Cross-Weekend or Overnight Holding:**
   - All trades entered after 07:05 UTC and closed at or before 12:00 UTC. Maximum holding duration was 4 hours 55 minutes. Zero overnight or weekend exposure.
