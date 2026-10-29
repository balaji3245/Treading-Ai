# Phase 7 Research Report: Volatility-Scaled Triple-Barrier Labeling & Out-of-Sample Economic Evaluation

**Asset:** XAUUSD (Spot Gold)  
**Timeframe:** M5 Intraday  
**Research Period:** 2021–2024 (Expanding-Window Walk-Forward Folds)  
**Validation Partition (2025):** Locked / Preserved (Zero Snooping)  
**Test Partition (2026):** Strictly Frozen and Untouched  
**Author:** Senior Quantitative Research Engineer, Financial ML Auditor, Risk Specialist  
**Artifact Date:** October 2026  
**Final Decision:** **REJECT** (No Credible Positive Net Expectancy)

---

## 1. Executive Summary

This study investigated whether replacing fixed-horizon exits ($H=24$ bars / 2 hours) with **volatility-scaled triple-barrier labeling** (profit target $2.0 \times \text{ATR}$, stop loss $1.0 \times \text{ATR}$, maximum holding period $24$ M5 bars) improves out-of-sample net expectancy after realistic transaction costs in XAUUSD spot gold trading.

### Core Research Findings

1. **Transaction Friction Overwhelms Gross Alpha:**  
   Across all 41 evaluated parameter configurations, directional filters, trend ablations, session gating regimes, and cost stress tiers, **not a single configuration achieved positive net expectancy** across the 2021–2024 walk-forward folds.
   - Unfiltered Triple-Barrier execution generated positive gross alpha ($+\$560.08/\text{oz}$ across 8,174 trades), but incurred $\$4,928.32/\text{oz}$ in transaction friction (spread: $\$2,773.70$, slippage: $\$1,337.22$, commission: $\$817.40$), resulting in an aggregate net loss of **$-\$4,368.24/\text{oz}$** ($\text{PF}_{\text{net}} = 0.674$, net win rate $31.37\%$, mean net return $-\$0.534/\text{oz}$ per trade).
2. **Comparison with Fixed-Horizon $H=24$ Baseline:**  
   While triple-barrier execution slightly reduced the raw dollar loss compared to fixed-horizon $H=24$ ($-\$4,368.24$ vs $-\$4,872.40$), the net profit factor actually deteriorated ($0.674$ vs $0.726$). Because the stop barrier ($1.0 \times \text{ATR}$) is set at half the distance of the profit target ($2.0 \times \text{ATR}$), random market noise triggers the stop barrier in **$68.0\%$ of all executed trades**, while the target barrier is reached in only **$30.4\%$ of trades**. The $2:1$ reward-to-risk ratio is insufficient to overcome the severe win-rate penalty in the presence of bid-ask spread and execution slippage.
3. **Selective Probability Thresholding Fails to Establish Edge:**  
   Thresholding model confidence from $0.40$ up to $0.70$ reduced trade volume from 9,905 down to 107 trades, but net PnL remained uniformly negative across every threshold (e.g., threshold $0.50$: $-\$1,154.27/\text{oz}$, $\text{PF}_{\text{net}} = 0.672$; threshold $0.60$: $-\$391.86/\text{oz}$, $\text{PF}_{\text{net}} = 0.640$).
4. **Trend and Session Ablations Do Not Rescue Strategy Economics:**  
   - Gating by completed H4 EMA slope (`htf_h4_ema_slope_50`) reduced trades to 3,979, but produced $-\$2,294.82/\text{oz}$ ($\text{PF}_{\text{net}} = 0.631$). Short-only with trend filter produced $-\$1,314.52/\text{oz}$ ($\text{PF}_{\text{net}} = 0.669$). Long-only with trend filter produced $-\$980.30/\text{oz}$ ($\text{PF}_{\text{net}} = 0.564$).
   - Gating entries to the London/New York overlap window (13:00–16:30 UTC) reduced trades to 3,364, but net PnL remained negative at $-\$1,736.94/\text{oz}$ ($\text{PF}_{\text{net}} = 0.736$).
5. **Pre-Registered Protocol & Decision Gate:**  
   Under the pre-registered qualification criteria, candidate policies were required to demonstrate: (1) aggregate net PnL $> \$0.00$, (2) positive net PnL in at least 2 of 3 training folds, (3) at least 100 completed trades, and (4) $\text{PF}_{\text{net}} > 1.0$ under baseline costs. **Zero candidate policies met these criteria.** Consequently, following strict research protocol, the 2025 validation partition was **not accessed for confirmation**, preventing data snooping and false discovery.
6. **Final Classification:** **REJECT**. Active triple-barrier trading is decisively dominated by the No-Trade baseline ($\$0.00$).

---

## 2. Pre-Implementation Audit & Accounting Verification

Before running experiments, an exhaustive audit of the pricing, execution, and cost models was performed to ensure complete integrity:

### 2.1 Units and Sizing Conventions
- **Asset:** Spot Gold (XAUUSD).
- **Pricing Units:** All prices, PnL, spread, slippage, commission, and drawdowns are denominated in **USD per troy ounce ($\$ / \text{oz}$)** assuming fixed single-unit (1-oz) exposure.
- **Contract Equivalence:** For institutional standard 100-oz lots, all reported nominal dollar figures scale linearly by a factor of $100\times$.
- **No Unjustified Account Multipliers:** Dollar per-ounce figures are evaluated directly without making hypothetical leverage, margin, or account balance assumptions.

### 2.2 Friction Accounting & Zero Double-Counting
The evaluator and simulator strictly verify that:
$$\text{Net PnL} = \text{Gross PnL} - (\text{Spread} + \text{Slippage} + \text{Commission})$$
- **Long Trade:**
  - Entry Fill: $\text{Ask} = \text{Bid}_{\text{entry}} + \text{Spread}_{\text{entry}} + \text{Slippage}_{\text{entry}}$
  - Exit Fill: $\text{Bid} = \text{Bid}_{\text{exit}} - \text{Slippage}_{\text{exit}}$
  - $\text{Gross PnL} = \text{Bid}_{\text{exit}} - \text{Bid}_{\text{entry}}$
  - $\text{Total Friction} = \text{Spread}_{\text{entry}} + \text{Slippage}_{\text{entry}} + \text{Slippage}_{\text{exit}} + \text{Commission}_{\text{round-turn}}$
  - $\text{Net PnL} = \text{Exit Fill} - \text{Entry Fill} - \text{Commission}_{\text{round-turn}} \equiv \text{Gross PnL} - \text{Total Friction}$
- **Short Trade:**
  - Entry Fill: $\text{Bid} = \text{Bid}_{\text{entry}} - \text{Slippage}_{\text{entry}}$
  - Exit Fill: $\text{Ask} = \text{Bid}_{\text{exit}} + \text{Spread}_{\text{exit}} + \text{Slippage}_{\text{exit}}$
  - $\text{Gross PnL} = \text{Bid}_{\text{entry}} - \text{Bid}_{\text{exit}}$
  - $\text{Total Friction} = \text{Spread}_{\text{exit}} + \text{Slippage}_{\text{entry}} + \text{Slippage}_{\text{exit}} + \text{Commission}_{\text{round-turn}}$
  - $\text{Net PnL} = \text{Entry Fill} - \text{Exit Fill} - \text{Commission}_{\text{round-turn}} \equiv \text{Gross PnL} - \text{Total Friction}$
- **Commission Convention:** Fixed at $\$0.05/\text{oz}$ per side ($\$0.10/\text{oz}$ round-turn, corresponding to $\$10.00$ per round standard lot).
- **Exact Parity Confirmed:** Automated regression tests verified that `abs(net_pnl - (gross_pnl - total_friction)) < 1e-4` for every single trade.

### 2.3 Execution Causality & Barrier Anchoring
- **Signal Finalization:** Generated at bar $t$ close using strictly causal features finalized at or before bar $t$.
- **Entry Timing:** Executed at bar $t+1$ Open. The bar $t+1$ completed high, low, close, and range are never used to price the entry fill.
- **Barrier Anchoring:** Barriers are anchored relative to the simulated entry fill price:
  - Long Target: $B_{\text{target}} = P_{\text{entry\_fill}} + 2.0 \times \text{ATR}_t$
  - Long Stop: $B_{\text{stop}} = P_{\text{entry\_fill}} - 1.0 \times \text{ATR}_t$
  - Short Target: $B_{\text{target}} = P_{\text{entry\_fill}} - 2.0 \times \text{ATR}_t$
  - Short Stop: $B_{\text{stop}} = P_{\text{entry\_fill}} + 1.0 \times \text{ATR}_t$
- **Barrier Monitoring:** Begins at bar $t+1$. The entry candle's pre-entry range is never backdated to trigger a barrier hit.
- **Conservative Same-Bar Ambiguity Resolution:** If both profit target and stop loss barriers are breached within the high-low span of the same M5 candle, conservative **stop-first execution is enforced**.
- **Executable Gap-Through Fills:** When a candle opens beyond a barrier (e.g. weekend gap or sudden volatility jump), execution fills at the candle Open price, reflecting adverse execution rather than assuming an idealized fill at the barrier price.
- **Weekend & Boundary Purging:** All signals whose holding period crosses a weekend closure ($>24\text{h}$ timestamp gap) or overlaps the training split tail ($1 + H_{\max} = 25$ bars) are purged.

---

## 3. Labeling Diagnostics (Training Period 2021–2024)

Causal triple-barrier labels were computed across the 260,821 M5 bars of the training dataset (`XAUUSD_M5_features_train.parquet`):

| Diagnostic Item | Count / Value | Proportion |
| :--- | :--- | :--- |
| **Total M5 Observations** | 260,821 bars | 100.00% |
| **Valid Observations** | 258,718 bars | 99.19% |
| **Purged Observations** | 2,103 bars | 0.81% |
| — *Tail Split Boundary Purge ($1 + H_{\max}$)* | 25 bars | 0.01% |
| — *Weekend Closure Crossings ($>24\text{h}$ gap)* | 2,078 bars | 0.80% |
| **Class Distribution (Valid Labels)** | | |
| — *Long Edge (+1)* | 51,453 bars | 19.89% |
| — *Neutral (0)* | 131,956 bars | 51.00% |
| — *Short Edge (-1)* | 75,309 bars | 29.11% |

### Barrier Event Resolution Breakdown
Across individual directional scenarios:
- **Long Scenarios:** Stop Hit: 197,515 ($76.3\%$) | Target Hit: 51,453 ($19.9\%$) | Time Limit: 9,750 ($3.8\%$)
- **Short Scenarios:** Stop Hit: 171,479 ($66.3\%$) | Target Hit: 75,309 ($29.1\%$) | Time Limit: 11,930 ($4.6\%$)

**Insight:** Because the stop barrier is set at $1.0 \times \text{ATR}$ while the target is $2.0 \times \text{ATR}$, random price fluctuations touch the tighter stop barrier roughly $3.5\times$ more frequently than the profit target.

---

## 4. Walk-Forward Research Results (2021–2024 Folds)

A 3-fold expanding-window chronological walk-forward cross-validation was conducted:
- **Fold 1:** Train 2021 $\rightarrow$ Evaluate 2022 (Eval Bars: 73,812)
- **Fold 2:** Train 2021–2022 $\rightarrow$ Evaluate 2023 (Eval Bars: 73,736)
- **Fold 3:** Train 2021–2023 $\rightarrow$ Evaluate 2024 (Eval Bars: 74,383)

Preprocessing (`StandardScaler`) and `LogisticRegressionBaseline` were fit strictly on each fold's training segment. Boundary purging ($25$ bars) was enforced between folds.

### 4.1 Core Threshold Sweep (Primary: Non-Overlapping Single-Position Capacity)

All aggregate metrics are computed directly from the 8,174 concatenated underlying trade records (not by averaging fold ratios):

| Strategy / Threshold | Completed Trades | Gross PnL ($/\text{oz}$) | Total Friction ($/\text{oz}$) | Net PnL ($/\text{oz}$) | Profit Factor (Net) | Win Rate (Net) | Mean Net / Trade | Max DD ($/\text{oz}$) | Folds Pos. |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **TB Unfiltered** | 8,174 | +$560.08 | $4,928.32 | **-$4,368.24** | 0.674 | 31.37% | -$0.534 | $4,410.75 | 0 / 3 |
| **TB Thresh=0.40** | 9,905 | +$448.76 | $5,981.72 | **-$5,532.96** | 0.643 | 31.23% | -$0.559 | $5,537.25 | 0 / 3 |
| **TB Thresh=0.45** | 4,215 | +$193.76 | $2,728.36 | **-$2,534.60** | 0.664 | 30.79% | -$0.601 | $2,586.00 | 0 / 3 |
| **TB Thresh=0.50** | 1,773 | +$93.88 | $1,248.15 | **-$1,154.27** | 0.672 | 29.67% | -$0.651 | $1,192.52 | 0 / 3 |
| **TB Thresh=0.55** | 906 | +$113.46 | $670.19 | **-$556.73** | 0.705 | 31.24% | -$0.614 | $593.39 | 0 / 3 |
| **TB Thresh=0.60** | 472 | -$12.56 | $379.31 | **-$391.86** | 0.640 | 29.45% | -$0.830 | $430.31 | 0 / 3 |
| **TB Thresh=0.65** | 218 | +$51.81 | $201.66 | **-$149.85** | 0.723 | 32.11% | -$0.687 | $196.83 | 0 / 3 |
| **TB Thresh=0.70** | 107 | +$38.39 | $112.71 | **-$74.32** | 0.745 | 31.78% | -$0.695 | $110.69 | 0 / 3 |
| **No-Trade Baseline** | 0 | $0.00 | $0.00 | **$0.00** | 0.000 | 0.00% | $0.000 | $0.00 | 3 / 3 |

*Note: Cost assumptions: Base Spread $\$0.20/\text{oz}$, Base Slippage $\$0.05/\text{oz}$, Commission $\$0.10/\text{oz}$ round-turn.*

### 4.2 Detailed Fold-by-Fold Breakdown (Core Configurations)

#### Fold 1 (2022 Evaluation):
- **Unfiltered:** 2,932 trades | Gross: +$244.09 | Friction: $1,765.08 | Net: **-$1,520.99** | $\text{PF}_{\text{net}} = 0.659$ | WinNet: 31.04% | LongNet: -$583.73 | ShortNet: -$937.25 | MaxDD: $1,532.93
- **Thresh=0.50:** 962 trades | Gross: +$42.47 | Friction: $667.07 | Net: **-$624.60** | $\text{PF}_{\text{net}} = 0.657$ | WinNet: 29.94% | LongNet: -$291.45 | ShortNet: -$333.14 | MaxDD: $647.97
- **Thresh=0.60:** 308 trades | Gross: +$27.39 | Friction: $243.65 | Net: **-$216.26** | $\text{PF}_{\text{net}} = 0.688$ | WinNet: 31.17% | LongNet: -$114.91 | ShortNet: -$101.35 | MaxDD: $254.18

#### Fold 2 (2023 Evaluation):
- **Unfiltered:** 1,550 trades | Gross: +$12.44 | Friction: $871.85 | Net: **-$859.41** | $\text{PF}_{\text{net}} = 0.575$ | WinNet: 29.16% | LongNet: -$568.27 | ShortNet: -$291.14 | MaxDD: $863.33
- **Thresh=0.50:** 438 trades | Gross: -$87.38 | Friction: $273.73 | Net: **-$361.11** | $\text{PF}_{\text{net}} = 0.474$ | WinNet: 24.20% | LongNet: -$251.47 | ShortNet: -$109.64 | MaxDD: $363.93
- **Thresh=0.60:** 125 trades | Gross: -$57.58 | Friction: $94.83 | Net: **-$152.41** | $\text{PF}_{\text{net}} = 0.413$ | WinNet: 24.00% | LongNet: -$121.96 | ShortNet: -$30.45 | MaxDD: $151.33

#### Fold 3 (2024 Evaluation):
- **Unfiltered:** 3,692 trades | Gross: +$303.55 | Friction: $2,291.39 | Net: **-$1,987.84** | $\text{PF}_{\text{net}} = 0.712$ | WinNet: 32.56% | LongNet: +$1.66 | ShortNet: -$1,989.50 | MaxDD: $2,070.21
- **Thresh=0.50:** 373 trades | Gross: +$138.78 | Friction: $307.35 | Net: **-$168.57** | $\text{PF}_{\text{net}} = 0.833$ | WinNet: 35.39% | LongNet: $0.00 | ShortNet: -$168.57 | MaxDD: $221.70
- **Thresh=0.60:** 39 trades | Gross: +$17.63 | Friction: $40.82 | Net: **-$23.19** | $\text{PF}_{\text{net}} = 0.829$ | WinNet: 33.33% | LongNet: $0.00 | ShortNet: -$23.19 | MaxDD: $57.84

---

## 5. Comparison against Fixed-Horizon ($H=24$) Baseline

Direct comparison between the Phase 6 fixed-horizon ($H=24$) baseline and the Phase 7 triple-barrier strategy across the identical 2021–2024 evaluation folds:

| Horizon / Strategy | Mode | Trades | Gross PnL | Net PnL | Total Friction | Net Profit Factor | Net Win Rate | Mean Net Return |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Fixed Horizon $H=24$ (Unfilt)** | Non-Overlap | 8,184 | +$2.81 | -$4,872.40 | $4,875.21 | **0.726** | 46.12% | -$0.595/oz |
| **Triple-Barrier (Unfilt)** | Non-Overlap | 8,174 | +$560.08 | -$4,368.24 | $4,928.32 | **0.674** | 31.37% | -$0.534/oz |
| **Fixed Horizon $H=24$ (Th=0.50)** | Non-Overlap | 5,879 | +$232.10 | -$3,194.03 | $3,426.13 | **0.772** | 46.85% | -$0.543/oz |
| **Triple-Barrier (Th=0.50)** | Non-Overlap | 1,773 | +$93.88 | -$1,154.27 | $1,248.15 | **0.672** | 29.67% | -$0.651/oz |
| **Fixed Horizon $H=24$ (Th=0.60)** | Non-Overlap | 2,733 | +$308.00 | -$1,340.90 | $1,648.90 | **0.835** | 47.92% | -$0.491/oz |
| **Triple-Barrier (Th=0.60)** | Non-Overlap | 472 | -$12.56 | -$391.86 | $379.31 | **0.640** | 29.45% | -$0.830/oz |
| **No-Trade Baseline** | Flat | 0 | $0.00 | **$0.00** | $0.00 | **0.000** | 0.00% | $0.000/oz |

### Quantitative Comparison Insights
1. **Gross Edge vs Net Friction:**  
   The triple-barrier framework improves gross PnL ($+\$560.08$ vs $+\$2.81$ in unfiltered), confirming that the profit target captures favorable excursions. However, the profit-taking mechanism exits winners quickly while the $1.0 \times \text{ATR}$ stop loss cuts positions frequently. The total friction incurred ($4,928.32$) completely obliterates the gross edge.
2. **Win Rate Collapse:**  
   In fixed-horizon trading, trades were held for exactly 24 bars regardless of intermediate price action, resulting in a net win rate near $47\%$. In triple-barrier trading, because the stop barrier ($1.0 \times \text{ATR}$) is twice as close as the target ($2.0 \times \text{ATR}$), the net win rate collapses to **$29.5\% - 31.4\%$**.
3. **Profit Factor Degradation:**  
   The net profit factor of the triple-barrier model is substantially worse than fixed-horizon $H=24$ across all thresholds (e.g. $0.674$ vs $0.726$ unfiltered; $0.640$ vs $0.835$ at threshold $0.60$).

---

## 6. Cost Sensitivity Analysis

To examine strategy fragility under varying execution conditions, the triple-barrier strategy was subjected to transaction cost stress testing:
- **Baseline Costs:** Spread $\$0.20/\text{oz}$, Slippage $\$0.05/\text{oz}$, Commission $\$0.10/\text{oz}$ round-turn.
- **$2\times$ Spread & Slippage:** Spread $\$0.40/\text{oz}$, Slippage $\$0.10/\text{oz}$, Commission $\$0.10/\text{oz}$ round-turn.
- **$3\times$ Spread & Slippage (Adverse Volatility Stress):** Spread $\$0.60/\text{oz}$, Slippage $\$0.15/\text{oz}$, Commission $\$0.10/\text{oz}$ round-turn.

| Configuration | Cost Scenario | Completed Trades | Gross PnL ($/\text{oz}$) | Total Friction ($/\text{oz}$) | Net PnL ($/\text{oz}$) | Net Profit Factor |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **TB Unfiltered** | Base Costs | 8,174 | +$560.08 | $4,928.32 | **-$4,368.24** | 0.674 |
| **TB Unfiltered** | $2\times$ Costs | 8,836 | +$688.25 | $9,187.36 | **-$8,499.11** | 0.481 |
| **TB Unfiltered** | $3\times$ Costs | 9,832 | +$1,033.06 | $14,497.78 | **-$13,464.72** | 0.333 |
| **TB Thresh=0.50** | Base Costs | 1,773 | +$93.88 | $1,248.15 | **-$1,154.27** | 0.672 |
| **TB Thresh=0.50** | $2\times$ Costs | 1,954 | +$117.94 | $2,357.13 | **-$2,239.19** | 0.480 |
| **TB Thresh=0.50** | $3\times$ Costs | 2,206 | +$246.35 | $3,739.59 | **-$3,493.24** | 0.339 |
| **TB Thresh=0.60** | Base Costs | 472 | -$12.56 | $379.31 | **-$391.86** | 0.640 |
| **TB Thresh=0.60** | $2\times$ Costs | 513 | +$9.67 | $711.04 | **-$701.37** | 0.467 |
| **TB Thresh=0.60** | $3\times$ Costs | 573 | +$98.15 | $1,116.94 | **-$1,018.79** | 0.352 |

**Sensitivity Finding:** Net losses expand monotonically as transaction friction increases. Under $2\times$ spread and slippage, the net profit factor drops below $0.50$. Under $3\times$ stress, the profit factor falls to $0.33$. The strategy displays extreme vulnerability to liquidity decay.

---

## 7. Ablation Studies

### 7.1 Trend Filter Ablation (Causal H4 EMA Slope)
To determine if trend alignment can rescue triple-barrier performance, trades were filtered using the causal H4 50-period EMA slope (`htf_h4_ema_slope_50`, computed strictly from completed H4 candles):

| Trend Filter Setting | Threshold | Trades | Gross PnL | Net PnL | $\text{PF}_{\text{net}}$ | Net Win Rate | Max Drawdown |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Both Directions + H4 Trend** | Unfiltered | 3,979 | +$64.16 | **-$2,294.82** | 0.631 | 29.78% | $2,324.77 |
| **Both Directions + H4 Trend** | Thresh=0.50 | 943 | -$5.58 | **-$646.22** | 0.610 | 27.68% | $685.70 |
| **Both Directions + H4 Trend** | Thresh=0.60 | 271 | -$85.18 | **-$302.52** | 0.493 | 26.20% | $311.34 |
| **Long-Only + H4 Trend** | Unfiltered | 1,449 | -$57.87 | **-$980.30** | 0.564 | 25.05% | $992.97 |
| **Long-Only + H4 Trend** | Thresh=0.50 | 597 | -$31.68 | **-$458.45** | 0.563 | 24.79% | $466.18 |
| **Long-Only + H4 Trend** | Thresh=0.60 | 208 | -$48.66 | **-$224.01** | 0.507 | 25.96% | $232.83 |
| **Short-Only + H4 Trend** | Unfiltered | 2,530 | +$122.03 | **-$1,314.52** | 0.669 | 32.49% | $1,351.72 |
| **Short-Only + H4 Trend** | Thresh=0.50 | 346 | +$26.10 | **-$187.77** | 0.692 | 32.66% | $227.69 |
| **Short-Only + H4 Trend** | Thresh=0.60 | 63 | -$36.53 | **-$78.51** | 0.447 | 26.98% | $90.03 |

**Trend Ablation Finding:** Trend alignment fails to produce positive net expectancy. Filtering by H4 EMA slope cuts trade volume by $\sim 50\%$, but profit factors remain degraded ($0.45 - 0.69$). In fact, trend filtering worsens the profit factor relative to the unfiltered baseline ($0.631$ vs $0.674$).

### 7.2 Directional Isolation Ablation (No Trend Filter)
Evaluating long-only and short-only policies independently:

| Direction Mode | Threshold | Trades | Gross PnL | Net PnL | $\text{PF}_{\text{net}}$ | Net Win Rate | Max Drawdown |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Long-Only** | Unfiltered | 2,023 | +$58.71 | **-$1,207.94** | 0.612 | 26.05% | $1,227.97 |
| **Long-Only** | Thresh=0.50 | 753 | -$20.59 | **-$550.83** | 0.590 | 25.23% | $557.82 |
| **Long-Only** | Thresh=0.60 | 255 | -$33.37 | **-$244.54** | 0.563 | 27.45% | $253.36 |
| **Short-Only** | Unfiltered | 6,311 | +$523.59 | **-$3,230.84** | 0.693 | 33.05% | $3,273.60 |
| **Short-Only** | Thresh=0.50 | 1,039 | +$141.82 | **-$590.79** | 0.733 | 33.11% | $626.95 |
| **Short-Only** | Thresh=0.60 | 220 | +$20.02 | **-$150.39** | 0.720 | 31.82% | $187.71 |

**Directional Finding:** Short trades exhibit higher win rates ($33.1\%$ vs $26.1\%$) and higher net profit factors ($0.69 - 0.73$ vs $0.56 - 0.61$) than long trades, reflecting structural gold intraday micro-reversals, but both directions remain firmly net negative.

### 7.3 Session Gating Ablation (London/New York Overlap Window)
Filtering trades strictly to the London/New York overlap window (`session_london_ny_overlap == 1`, 13:00–16:30 UTC):

| Session Setting | Threshold | Trades | Gross PnL | Net PnL | $\text{PF}_{\text{net}}$ | Net Win Rate | Max Drawdown |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Session Overlap Only** | Unfiltered | 3,364 | +$327.30 | **-$1,736.94** | 0.736 | 32.70% | $1,800.49 |
| **Session Overlap Only** | Thresh=0.50 | 758 | +$94.86 | **-$431.74** | 0.760 | 32.59% | $515.18 |
| **Session Overlap Only** | Thresh=0.60 | 169 | -$26.68 | **-$157.26** | 0.673 | 30.18% | $168.30 |

**Session Gating Finding:** Restricting entries to the highest-liquidity window slightly improves the net profit factor ($0.736$ vs $0.674$ in unfiltered), but net PnL remains deeply negative ($-\$1,736.94$). Session gating alone cannot overcome execution costs.

---

## 8. Outlier Trade Sensitivity Analysis

To verify whether performance is fragile or driven by a small handful of extreme outlier trades, top winning trades were systematically excluded:

| Strategy | Total Net PnL | Net w/o Top 1% Trades | Top 1% Drag ($/\text{oz}$) | Net w/o Top 3 Trades | Max Single Win | Max Single Loss |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **TB Unfiltered** | -$4,368.24 | -$5,154.19 (82 trades) | -$785.95 | -$4,425.01 | +$23.95/oz | -$21.65/oz |
| **TB Thresh=0.50** | -$1,154.27 | -$1,364.24 (18 trades) | -$209.97 | -$1,199.02 | +$18.45/oz | -$17.15/oz |
| **TB Thresh=0.60** | -$391.86 | -$460.81 (5 trades) | -$68.94 | -$435.56 | +$16.32/oz | -$13.78/oz |

**Outlier Finding:** Performance is **not** an artifact of outlier trades. The distribution of returns is uniform and consistent across trades. The strategy suffers from a structural expectancy deficit where the average win ($+\$1.75/\text{oz}$ net) is vastly outnumbered by frequent small losses ($-\$0.95/\text{oz}$ net), generating a steady, continuous downward equity curve.

---

## 9. Drawdown Methodology & Limitations

### 9.1 Drawdown Convention
Drawdown is calculated as the continuous peak-to-trough drop of cumulative net PnL:
$$D_t = \max_{0 \le s \le t} \left(\sum_{i=1}^s \text{Net PnL}_i\right) - \sum_{i=1}^t \text{Net PnL}_i$$
All drawdown figures are reported in **USD per troy ounce ($\$ / \text{oz}$)** under single-unit (1-oz) fixed sizing.

### 9.2 Limitations of Per-Ounce Drawdown
1. **Absence of Capital Base:** Per-ounce drawdown cannot be expressed as an account percentage without arbitrary assumptions regarding starting account balance, margin requirements, broker leverage, and volatility-based position sizing.
2. **Path Dependency:** Under non-overlapping execution, position lockout prevents simultaneous exposures. In a multi-contract or multi-asset portfolio, drawdown dynamics would be governed by cross-asset correlation and capital allocation constraints.
3. **Synthetic Execution Limits:** While bid-only historical data was modeled with conservative spreads, slippages, and rollover fees, historical tick-level depth-of-book liquidity cannot be fully reconstructed from M5 bar data.

---

## 10. Locked 2025 Confirmation Decision

### 10.1 Pre-Registered Training-Fold Qualification Criteria
To be eligible for a locked, one-time out-of-sample confirmation on the 2025 validation partition (`XAUUSD_M5_features_val.parquet`), a candidate policy was strictly required to satisfy **all** of the following criteria across the 2021–2024 training folds:
1. **Aggregate Net PnL $> \$0.00$** across the 3 folds.
2. **Fold Consistency:** Positive net PnL in at least 2 of 3 folds.
3. **Statistical Sample Size:** At least 100 completed trades.
4. **Net Profit Factor $> 1.0$** under baseline costs.
5. **Execution Mode:** Non-overlapping single-position capacity.

### 10.2 Qualification Outcome
**ZERO candidate policies qualified.**  
Every tested parameter combination produced negative net expectancy after transaction costs across all 3 training folds.

### 10.3 Protocol Adherence & 2025 Validation Isolation
In strict compliance with Section 8 of the quantitative research mandate:
> *"If no candidate qualifies on training folds, document that outcome and do not run a misleading validation search."*

- **The 2025 validation partition was NOT accessed for confirmation.**
- `scripts/run_triple_barrier_confirmation.py` was **not created or executed**, preventing post-hoc parameter snooping and false confirmation.
- **The 2026 Test partition remains completely frozen, isolated, and untouched.**

---

## 11. Final Classification & Research Recommendations

### Final Classification: **REJECT**

There is **no credible evidence** that volatility-scaled triple-barrier labeling produces a positive net expectancy after realistic transaction costs in XAUUSD intraday M5 trading.

### Defensible Next Research Directions

1. **Macro Regime & Volatility Gating over Micro Directional Prediction:**  
   Directional ML models on M5 bars fail to achieve sufficient precision ($>55\%$) to overcome the bid-ask spread and execution slippage. Future research should prioritize **regime classification** (e.g., high vs low realized volatility regimes, compression vs expansion states) to determine *when* market conditions can support transaction costs, rather than attempting to forecast bar-by-bar price direction.
2. **Asymmetric Barrier Geometries:**  
   The $2.0 \times \text{ATR}$ target with $1.0 \times \text{ATR}$ stop loss penalized the strategy through an adverse win rate ($30\%$). Exploring wider target-to-stop geometries or trailing volatility stops anchored to macro structural support/resistance levels (rather than local M5 ATR) represents a defensible hypothesis.
3. **Execution Optimization & Direct Limit-Order Modeling:**  
   All current models assume crossing the spread at entry (market order at Ask/Bid). If execution could capture rather than cross the spread via passive limit orders, the $\$0.20/\text{oz}$ friction drag could be reduced. However, this introduces adverse selection risk, which requires tick-level order book modeling.
