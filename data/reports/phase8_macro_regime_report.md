# Phase 8 Research Report: Macro Volatility Regime Detection & Cost-Adjusted Feasibility Analysis

**Asset:** XAUUSD (Spot Gold)  
**Timeframe:** M5 Intraday  
**Research Period:** 2021–2024 (Expanding-Window Walk-Forward Folds)  
**Validation Partition (2025):** Preserved / Uninspected (Zero Data Snooping)  
**Test Partition (2026):** Strictly Frozen and Untouched  
**Author:** Senior Quantitative Research Engineer, Financial ML Auditor, Risk Specialist  
**Artifact Date:** October 2026  
**Final Classification:** **REJECT** (No Credible Cost-Adjusted Edge Identified)

---

## 1. Executive Summary

This study investigated whether historical XAUUSD M5 data contains identifiable **volatility-expansion regimes** where price movement is large enough to overcome realistic transaction friction, and whether such regimes possess **directional predictability** that can be systematically exploited out-of-sample.

### Core Quantitative Findings:
1. **Identifiable & Statistically Distinct Volatility Regimes:**  
   Using strictly causal trailing metrics (trailing 288-bar median ATR and trailing 500-bar percentile rank), the market partitions cleanly into four distinct regimes:
   - **LOW Volatility:** 96,214 bars ($36.89\%$), mean episode duration $2.16\text{h}$ (25.9 bars).
   - **NORMAL Volatility:** 74,658 bars ($28.62\%$), mean episode duration $0.89\text{h}$ (10.7 bars).
   - **HIGH Volatility (Expansion):** 49,119 bars ($18.83\%$), mean episode duration $0.82\text{h}$ (9.8 bars).
   - **EXTREME Volatility (Surge):** 40,830 bars ($15.65\%$), mean episode duration $1.96\text{h}$ (23.5 bars).
2. **Abundant Absolute Price Movement (Descriptive Feasibility Passed):**  
   Over an $H=24$ bar holding horizon (2 hours):
   - In the **HIGH regime**, the median absolute terminal price movement is **$\$2.65/\text{oz}$** ($7.57\times$ baseline round-turn friction of $\$0.35/\text{oz}$).
   - In the **EXTREME regime**, median terminal movement expands to **$\$3.40/\text{oz}$** ($9.71\times$ baseline friction).
   - $92.2\%$ of HIGH regime bars and $94.1\%$ of EXTREME regime bars experience forward price movement exceeding $\$0.35/\text{oz}$.
   - Outlier concentration is low (top 1% of movements account for only $6.4\% - 7.4\%$ of total movement), proving that expansion is structurally persistent, not an artifact of rare news spikes.
   - All four pre-registered descriptive feasibility gates **PASSED**, justifying progression to predictive experiments.
3. **The Core Quantitative Paradox: Movement $\ne$ Directional Edge:**  
   While absolute price movement in expansion regimes is plentiful, **directional movement is essentially symmetric Brownian noise**:
   - A causal momentum breakout rule executed exclusively in HIGH/EXTREME regimes incurred **$-\$2,369.45/\text{oz}$** in net losses across 3,656 trades ($\text{PF}_{\text{net}} = 0.708$, net win rate $44.5\%$).
   - A directional Machine Learning model (Logistic Regression) fit strictly on expanding training folds and gated exclusively to HIGH/EXTREME regimes produced **$-\$2,064.29/\text{oz}$** (unfiltered, $\text{PF}_{\text{net}} = 0.796$), **$-\$1,567.70/\text{oz}$** (threshold 0.50, $\text{PF}_{\text{net}} = 0.806$), and **$-\$709.48/\text{oz}$** (threshold 0.60, $\text{PF}_{\text{net}} = 0.881$).
   - Net PnL was negative in every single training fold across all tested models.
4. **Dominance of the No-Trade Baseline:**  
   Regime-gated directional strategies cut losses relative to ungated baseline trading (e.g. $-\$709.48$ vs $-\$1,410.58$), confirming that abstaining during low-volatility regimes saves transaction costs. However, in active trading, **no strategy produced positive net expectancy**. The No-Trade baseline ($\$0.00$) remains strictly superior.
5. **Final Classification:** **REJECT**. Volatility expansion provides ample movement, but directional prediction on M5 bars fails to establish a positive net expectancy after transaction costs.

---

## 2. Causal Regime Detection Framework

### 2.1 Zero-Lookahead Architectural Rules
- **Lagged Baseline Median:** The historical reference baseline is computed strictly using trailing past bars:
  $$\text{Baseline ATR}_t = \text{median}(\text{ATR}_{t-288}, \dots, \text{ATR}_{t-1})$$
  Bar $t$ is strictly shifted out of its own baseline calculation.
- **Lagged Percentile Rank:** The percentile rank of current ATR is calculated over the trailing 500-bar window $[t-500 : t-1]$.
- **Causal Expansion Ratio:**
  $$\text{Expansion Ratio}_t = \frac{\text{ATR}_t}{\text{Baseline ATR}_t}$$
- **Classification Rules:**
  - **LOW:** $\text{Expansion Ratio}_t < 0.85$ or $\text{Percentile}_t < 0.33$
  - **NORMAL:** $0.85 \le \text{Expansion Ratio}_t \le 1.25$ ($0.33 \le \text{Percentile}_t \le 0.67$)
  - **HIGH:** $1.25 < \text{Expansion Ratio}_t \le 1.60$ ($0.67 < \text{Percentile}_t \le 0.90$)
  - **EXTREME:** $\text{Expansion Ratio}_t > 1.60$ or $\text{Percentile}_t > 0.90$
- **Truncation Invariance:** Automated regression tests verified that truncating the dataset at any arbitrary bar $K$ produces identical historical regime labels for all preceding bars $0 \dots K$.

---

## 3. Descriptive Regime Analysis (2021–2024 Training Period)

Across the 260,821 M5 bars in the 2021–2024 training dataset:

### 3.1 Regime Frequencies and Proportions
| Volatility Regime | Total M5 Bars | Share of Time | Independent Episodes | Mean Duration (Hours) | Median Duration (Hours) | Mean Peak Expansion Ratio |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **LOW** | 96,214 | 36.89% | 3,716 | 2.16h (25.9 bars) | 0.83h (10 bars) | 0.89x |
| **NORMAL** | 74,658 | 28.62% | 6,996 | 0.89h (10.7 bars) | 0.58h (7 bars) | 1.07x |
| **HIGH** | 49,119 | 18.83% | 5,001 | 0.82h (9.8 bars) | 0.58h (7 bars) | 1.37x |
| **EXTREME** | 40,830 | 15.65% | 1,738 | 1.96h (23.5 bars) | 1.58h (19 bars) | 2.07x |
| **Total / Overall** | 260,821 | 100.00% | 17,451 | 1.25h (15.0 bars) | 0.67h (8 bars) | — |

### 3.2 Empirical Markov 1-Step Transition Matrix
Empirical conditional probabilities $P(\text{Regime}_{t+1} \mid \text{Regime}_t)$:

| Current Regime ($\text{Regime}_t$) | $\rightarrow$ LOW ($t+1$) | $\rightarrow$ NORMAL ($t+1$) | $\rightarrow$ HIGH ($t+1$) | $\rightarrow$ EXTREME ($t+1$) |
| :--- | :---: | :---: | :---: | :---: |
| **From LOW** | **96.14%** | 3.82% | 0.03% | 0.01% |
| **From NORMAL** | 4.97% | **90.63%** | 4.33% | 0.07% |
| **From HIGH** | 0.00% | 6.75% | **89.82%** | 3.43% |
| **From EXTREME** | 0.00% | 0.00% | 4.26% | **95.74%** |

**Markov Insights:**
- Strong temporal persistence across all regimes ($89.8\% - 96.1\%$ probability of remaining in the same state).
- Direct transitions between non-adjacent states (e.g. LOW $\rightarrow$ EXTREME or EXTREME $\rightarrow$ LOW) are near zero ($<0.01\%$). Market volatility evolves progressively through intermediate states.

### 3.3 Trading Session Distribution
Volatility regimes exhibit pronounced intraday seasonality aligned with global financial market liquidity:

| Market Session | Local / UTC Window | LOW Regime | NORMAL Regime | HIGH Regime | EXTREME Regime |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Asian Session** | 00:00–08:00 UTC | **59.3%** | 30.2% | 8.9% | 1.6% |
| **London Morning** | 08:00–13:00 UTC | 11.2% | **49.5%** | 32.0% | 7.4% |
| **London/NY Overlap** | 13:00–16:30 UTC | 1.2% | 7.5% | 24.7% | **66.6%** |
| **NY Afternoon** | 16:30–21:00 UTC | 35.7% | 30.2% | 22.9% | 11.1% |
| **Daily Rollover Window** | 21:00–23:00 UTC | **80.0%** | 12.2% | 4.5% | 3.3% |

**Key Finding:** Over two-thirds ($66.6\%$) of all EXTREME volatility observations occur during the **London/New York overlap window (13:00–16:30 UTC)**. In contrast, the Asian session and the post-17:00 NY rollover window are dominated by LOW volatility ($59.3\%$ and $80.0\%$).

### 3.4 Weekday Distribution
| Weekday | LOW Regime | NORMAL Regime | HIGH Regime | EXTREME Regime |
| :--- | :---: | :---: | :---: | :---: |
| **Monday** | 40.2% | 28.1% | 18.2% | 13.5% |
| **Tuesday** | 36.1% | 28.9% | 18.8% | 16.2% |
| **Wednesday** | 35.5% | 29.2% | 19.1% | 16.2% |
| **Thursday** | 34.8% | 29.4% | 19.3% | 16.5% |
| **Friday** | 37.9% | 27.5% | 18.7% | 15.9% |

Volatility is relatively uniform Tuesday through Friday, with a slight elevation of low-volatility conditions on Monday mornings prior to European open.

---

## 4. Cost-Adjusted Price Movement Feasibility

To determine if price movements in expansion regimes are economically meaningful relative to execution costs, forward movements were measured over $H \in \{6, 12, 24, 48\}$ bars:
- **Base Round-Turn Friction:** $\$0.35/\text{oz}$ ($\$0.20$ spread + $2\times \$0.05$ slippage + $\$0.10$ commission).
- **$2\times$ Friction Stress:** $\$0.60/\text{oz}$ ($\$0.40$ spread + $2\times \$0.10$ slippage + $\$0.10$ commission).
- **$3\times$ Friction Stress:** $\$0.85/\text{oz}$ ($\$0.60$ spread + $2\times \$0.15$ slippage + $\$0.10$ commission).

### 4.1 Movement Distributions Across Horizons ($H=6, 12, 24, 48$)

#### Horizon $H=24$ Bars (2 Hours) — Primary Benchmark:
| Volatility Regime | Median Move ($/\text{oz}$) | Mean Move ($/\text{oz}$) | P75 Move ($/\text{oz}$) | P90 Move ($/\text{oz}$) | High-Low Span ($/\text{oz}$) | Base Cost Ratio | % > Base Cost | 2x Cost Ratio | 3x Cost Ratio | Top 1% Share |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **LOW** | $\$1.82$ | $\$2.41$ | $\$3.08$ | $\$4.74$ | $\$4.24$ | **5.20x** | 89.0% | 3.03x | 2.14x | 7.1% |
| **NORMAL** | $\$2.21$ | $\$2.95$ | $\$3.78$ | $\$5.95$ | $\$5.15$ | **6.31x** | 91.0% | 3.68x | 2.60x | 7.8% |
| **HIGH** | $\$2.65$ | $\$3.45$ | $\$4.45$ | $\$6.87$ | $\$5.98$ | **7.57x** | 92.2% | 4.42x | 3.12x | 7.4% |
| **EXTREME** | $\$3.40$ | $\$4.57$ | $\$5.97$ | $\$9.42$ | $\$7.76$ | **9.71x** | 94.1% | 5.67x | 4.00x | 6.4% |
| **ALL REGIMES** | $\$2.25$ | $\$3.10$ | $\$3.98$ | $\$6.42$ | $\$5.38$ | **6.44x** | 91.0% | 3.76x | 2.65x | 7.7% |

#### Horizon Scaling in the HIGH Volatility Regime:
| Forward Horizon | Median Move ($/\text{oz}$) | Mean Move ($/\text{oz}$) | High-Low Span ($/\text{oz}$) | Base Cost Ratio | % Exceeding Base Cost |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **$H=6$ (30 min)** | $\$1.37$ | $\$1.84$ | $\$3.34$ | **3.91x** | 85.5% |
| **$H=12$ (1 hour)** | $\$1.91$ | $\$2.53$ | $\$4.54$ | **5.45x** | 89.6% |
| **$H=24$ (2 hours)** | $\$2.65$ | $\$3.45$ | $\$5.98$ | **7.57x** | 92.2% |
| **$H=48$ (4 hours)** | $\$3.75$ | $\$4.83$ | $\$7.97$ | **10.71x** | 94.6% |

### 4.2 Outlier Concentration Analysis
A critical concern in volatility analysis is whether apparent movement is driven by a handful of catastrophic tail events.
- In the HIGH regime, the top 1% largest moves account for only **$7.4\%$** of total cumulative movement.
- In the EXTREME regime, the top 1% largest moves account for only **$6.4\%$** of total movement.
- **Finding:** Movement is broad-based and structural throughout the entire distribution, rather than being concentrated in idiosyncratic news spikes.

---

## 5. Pre-Registered Feasibility Gate Evaluation

Before proceeding to predictive experiments, four quantitative feasibility criteria were pre-registered:

| Gate Criterion | Target Threshold | Observed Value (HIGH Regime) | Result |
| :--- | :--- | :--- | :---: |
| **1. Movement Magnitude** | Median terminal move over $H=24 \ge 3.0\times$ base cost ($\ge \$1.05/\text{oz}$) | **$\$2.65/\text{oz}$ ($7.57\times$)** | **PASS** |
| **2. Independent Sample Size** | $\ge 400$ independent episodes across 2021–2024 ($\ge 100/\text{yr}$) | **5,001 episodes** | **PASS** |
| **3. Regime Persistence** | Mean duration $\ge 6.0$ bars ($30\text{ minutes}$) | **9.8 bars ($0.82\text{ hours}$)** | **PASS** |
| **4. Outlier Resilience** | Top 1% movement share $\le 15.0\%$ of total movement | **7.4%** | **PASS** |
| **Overall Feasibility Gate** | All 4 gates must pass to justify predictive modeling | **4 of 4 Passed** | **GATE PASSED** |

---

## 6. Causal Predictive Experiments in High-Volatility Regimes

Having established that price movement in expansion regimes is large enough to support transaction friction, we tested whether identifying the regime at bar $t$ close enables **directional profitability** under strict single-position non-overlapping execution across the three chronological walk-forward folds (2021–2024).

### 6.1 Strategies Tested:
1. **`MomentumBreakout_HighRegimeOnly`:** Enters in the direction of the 1-hour price change ($\text{Close}_t > \text{Close}_{t-12}$) only when bar $t$ is in HIGH or EXTREME volatility.
2. **`LR_Unfiltered_HighRegimeOnly`:** Evaluates the `LogisticRegressionBaseline` multiclass classifier fit strictly on each fold's training data, executing trades only when bar $t$ is in HIGH or EXTREME volatility.
3. **`LR_Thresh0.50_HighRegimeOnly`:** Regime-gated model requiring probability $\ge 0.50$.
4. **`LR_Thresh0.60_HighRegimeOnly`:** Regime-gated model requiring probability $\ge 0.60$.
5. **`LR_Thresh0.60_Ungated_Reference`:** Phase 6 benchmark (threshold 0.60 across all regimes).
6. **`NoTrade_Baseline`:** Zero trading benchmark.

### 6.2 Aggregate Performance Across Walk-Forward Folds (2021–2024)
All aggregate metrics are calculated from underlying trade records under strict non-overlapping capacity = 1:

| Strategy | Completed Trades | Gross PnL ($/\text{oz}$) | Total Friction ($/\text{oz}$) | Net PnL ($/\text{oz}$) | Profit Factor (Net) | Net Win Rate | $2\times$ Costs Net | $3\times$ Costs Net | Positive Folds |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **MomentumBreakout (High/Extr Only)** | 3,656 | -$208.56 | $2,160.89 | **-$2,369.45** | 0.708 | 44.53% | -$4,009.87 | -$5,650.29 | 0 / 3 |
| **LR Unfiltered (High/Extr Only)** | 3,631 | +$87.83 | $2,152.12 | **-$2,064.29** | 0.796 | 45.55% | -$3,698.51 | -$5,332.73 | 0 / 3 |
| **LR Thresh=0.50 (High/Extr Only)** | 2,849 | +$140.48 | $1,708.18 | **-$1,567.70** | 0.806 | 45.81% | -$2,846.17 | -$4,124.64 | 0 / 3 |
| **LR Thresh=0.60 (High/Extr Only)** | 1,531 | +$268.14 | $977.62 | **-$709.48** | 0.881 | 47.39% | -$1,429.94 | -$2,150.40 | 0 / 3 |
| **LR Thresh=0.60 (Ungated Reference)** | 2,669 | +$210.28 | $1,620.86 | **-$1,410.58** | 0.821 | 46.35% | -$2,646.74 | -$3,882.90 | 0 / 3 |
| **No-Trade Baseline** | 0 | $0.00 | $0.00 | **$0.00** | 0.000 | 0.00% | $0.00 | $0.00 | 3 / 3 |

### 6.3 Detailed Fold-by-Fold Breakdown

#### Fold 1 (Eval 2022):
- **MomentumBreakout (High Only):** 1,277 trades | Gross: -$328.36 | Net: **-$1,042.47** | $\text{PF}_{\text{net}} = 0.689$ | WinNet: 43.77%
- **LR Unfiltered (High Only):** 1,256 trades | Gross: +$83.99 | Net: **-$628.26** | $\text{PF}_{\text{net}} = 0.798$ | WinNet: 46.02%
- **LR Thresh=0.50 (High Only):** 1,077 trades | Gross: +$94.29 | Net: **-$511.08** | $\text{PF}_{\text{net}} = 0.811$ | WinNet: 46.80%
- **LR Thresh=0.60 (High Only):** 661 trades | Gross: +$198.25 | Net: **-$197.40** | $\text{PF}_{\text{net}} = 0.887$ | WinNet: 48.41%
- **LR Thresh=0.60 (Ungated):** 1,149 trades | Gross: +$197.22 | Net: **-$499.38** | $\text{PF}_{\text{net}} = 0.821$ | WinNet: 46.91%

#### Fold 2 (Eval 2023):
- **MomentumBreakout (High Only):** 1,110 trades | Gross: +$365.21 | Net: **-$254.51** | $\text{PF}_{\text{net}} = 0.895$ | WinNet: 46.31%
- **LR Unfiltered (High Only):** 1,108 trades | Gross: +$216.29 | Net: **-$395.48** | $\text{PF}_{\text{net}} = 0.842$ | WinNet: 47.47%
- **LR Thresh=0.50 (High Only):** 726 trades | Gross: +$42.57 | Net: **-$374.76** | $\text{PF}_{\text{net}} = 0.802$ | WinNet: 46.83%
- **LR Thresh=0.60 (High Only):** 232 trades | Gross: +$112.61 | Net: **-$27.42** | $\text{PF}_{\text{net}} = 0.962$ | WinNet: 48.28%
- **LR Thresh=0.60 (Ungated):** 426 trades | Gross: +$94.09 | Net: **-$150.69** | $\text{PF}_{\text{net}} = 0.860$ | WinNet: 47.42%

#### Fold 3 (Eval 2024):
- **MomentumBreakout (High Only):** 1,269 trades | Gross: -$245.41 | Net: **-$1,072.47** | $\text{PF}_{\text{net}} = 0.741$ | WinNet: 43.50%
- **LR Unfiltered (High Only):** 1,267 trades | Gross: -$212.45 | Net: **-$1,040.55** | $\text{PF}_{\text{net}} = 0.748$ | WinNet: 43.17%
- **LR Thresh=0.50 (High Only):** 1,046 trades | Gross: +$3.62 | Net: **-$681.86** | $\text{PF}_{\text{net}} = 0.807$ | WinNet: 43.79%
- **LR Thresh=0.60 (High Only):** 638 trades | Gross: -$42.72 | Net: **-$484.66** | $\text{PF}_{\text{net}} = 0.795$ | WinNet: 45.45%
- **LR Thresh=0.60 (Ungated):** 1,094 trades | Gross: -$81.03 | Net: **-$760.51** | $\text{PF}_{\text{net}} = 0.782$ | WinNet: 44.70%

---

## 7. Comparative Analysis: Regime Gating vs Ungated Trading

### Did Regime Gating Help?
Comparing `LR_Thresh0.60_HighRegimeOnly` directly against `LR_Thresh0.60_Ungated_Reference`:
- **Trade Count:** Reduced from 2,669 to 1,531 trades (a $42.6\%$ reduction by avoiding low/normal regimes).
- **Gross PnL:** Increased from $+\$210.28/\text{oz}$ to $+\$268.14/\text{oz}$ (gross alpha per trade increased from $+\$0.079$ to $+\$0.175/\text{oz}$).
- **Total Friction:** Decreased from $\$1,620.86/\text{oz}$ to $\$977.62/\text{oz}$ (a $\$643.24/\text{oz}$ friction saving).
- **Net PnL:** Net loss cut nearly in half (from **$-\$1,410.58/\text{oz}$** to **$-\$709.48/\text{oz}$**).
- **Profit Factor:** Improved from $0.821 \rightarrow 0.881$.

> [!NOTE]
> Gating trades strictly to high-volatility regimes provided genuine economic value: it pruned unprofitable low-volatility churn and improved trade-level efficiency. **However, it did not cross the zero line.** A less negative active strategy is still inferior to the No-Trade baseline.

---

## 8. Quantitative Limitations & Statistical Controls

1. **Synthetic Cost Disclosures:**  
   Execution costs were modeled with baseline spread ($\$0.20/\text{oz}$), slippage ($\$0.05/\text{oz}$ per side), and commission ($\$0.10/\text{oz}$ round-turn). These assumptions are conservative relative to standard retail conditions, but are **not broker-calibrated from live tick data**. During extreme volatility surges (e.g. US CPI/NFP releases), true institutional spreads can widen beyond $\$0.80 - \$1.50/\text{oz}$, meaning real-world friction in EXTREME regimes is likely higher than modeled.
2. **Drawdown Convention:**  
   Drawdown is computed as continuous peak-to-trough drop of cumulative net PnL in USD per troy ounce under fixed single-unit (1-oz) exposure. It cannot be converted to account-level percentage drawdown without explicit capital, margin, and position-sizing assumptions.
3. **Absence of Intrabar Ordering:**  
   All M5 simulations respect causal open-to-close or open-to-open boundaries. Intrabar tick ordering is never fabricated from OHLC data.

---

## 9. Final Classification & Research Recommendations

### Final Classification: **`REJECT`**

There is **no credible evidence** that volatility-expansion regimes contain sufficient directional predictability to produce positive net expectancy after transaction costs.

### Summary of Hypotheses Tested Across Phases 4–8:
- **Phase 4 (M5 Fixed-Horizon Direction Baselines):** Gross alpha $\approx 0$, friction dominates $\rightarrow$ **REJECT**.
- **Phase 5 (Selective Probability Thresholding):** Improves precision but trade frequency drops; net PnL remains negative $\rightarrow$ **REJECT**.
- **Phase 6 (Longer Horizons $H=24, 48$):** Gross alpha increases but friction remains insurmountable $\rightarrow$ **REJECT**.
- **Phase 7 (Volatility-Scaled Triple Barrier):** Tight stop cuts win rate to $31\%$; net PnL remains negative $\rightarrow$ **REJECT**.
- **Phase 8 (Macro Volatility Regimes):** Absolute movement is abundant ($7.5\times$ friction), but directional predictability is absent ($\text{win rate} \approx 47\%$) $\rightarrow$ **REJECT**.

### Defensible Next Research Directions:
1. **Direction-Agnostic / Volatility-Harvesting Strategies:**  
   Since high-volatility regimes reliably produce large price excursions ($\$2.65 - \$3.40/\text{oz}$) without directional bias, directional prediction on M5 bars is the wrong mathematical formulation. Future research should investigate **direction-agnostic structures** (e.g. straddles, volatility breakout expansion with trailing brackets, or volatility options).
2. **Macro Calendar Shock Isolation:**  
   EXTREME volatility is concentrated in the London/NY overlap (13:00–16:30 UTC), predominantly driven by scheduled US macroeconomic data releases (CPI, NFP, FOMC). Investigating post-announcement momentum over multi-hour horizons rather than continuous M5 bar-by-bar classification represents a defensible hypothesis.
