# FROZEN EVALUATION PROTOCOL: HYP-24-NY-REVERSAL-EXHAUSTION

**Document Version:** 1.0.0 (FROZEN PROTOCOL PRE-REGISTRATION)  
**Hypothesis ID:** `HYP-24-NY-REVERSAL-EXHAUSTION`  
**Phase:** 24 — New Hypothesis Discovery & Pre-Registration  
**Instrument:** XAUUSD (Spot Gold / US Dollar)  
**Status:** FROZEN PROTOCOL CODIFIED PRIOR TO BACKTESTING  

---

## 1. Mathematical Definitions & Operational Specification

All operations, timing boundaries, and execution rules are defined strictly in **Coordinated Universal Time (UTC)**.

### 1.1 Baseline Consensus Anchor ($P_{\text{base}}$)
The pre-release reference baseline is defined as the closing price of the M5 bar closing at 12:00:00 UTC:
$$P_{\text{base}, t} = \text{Close}_{\text{11:55:00 UTC bar on day } t}$$

### 1.2 Prior Daily Volatility Benchmark ($\text{ATR}_{20}^{\text{prior}}$)
Calculated from completed calendar daily bars ($N \ge 100$ bars) and shifted by 1 full day (`shift(1)`), preventing current-day look-ahead leakage:
$$\text{TR}_d = \max\Big(\text{High}_d - \text{Low}_d, |\text{High}_d - \text{Close}_{d-1}|, |\text{Low}_d - \text{Close}_{d-1}|\Big)$$
$$\text{ATR}_{20, t}^{\text{prior}} = \frac{1}{20} \sum_{k=1}^{20} \text{TR}_{t-k}$$

### 1.3 Morning Excursion Vector & Normalized Excursion Ratio
The US morning excursion is measured across completed bars up to 14:00:00 UTC (the `13:55` M5 bar close):
$$P_{\text{14:00}, t} = \text{Close}_{\text{13:55:00 UTC bar on day } t}$$
$$\Delta P_t = P_{\text{14:00}, t} - P_{\text{base}, t}$$
$$\text{NER}_t = \frac{|\Delta P_t|}{\text{ATR}_{20, t}^{\text{prior}}}$$

### 1.4 Excursion Exhaustion Eligibility Condition
A trading day qualifies for counter-trend entry if and only if the Normalized Excursion Ratio exceeds the frozen threshold:
$$\text{NER}_t \ge \theta_{\text{exhaustion}}$$
- **Calibration Source:** 75th percentile ($Q_3$) of $\text{NER}_t$ estimated strictly on the 2021–2022 development partition.
- **Frozen Threshold Rule:** Once estimated on 2021–2022 development data in Phase 25, this value is permanently locked for out-of-sample testing.

---

## 2. Order Execution & Deterministic Order of Operations

### 2.1 Trade Entry Mechanics
- **Timing:** Open of the M5 bar immediately following the 14:00:00 UTC measurement (`14:05:00 UTC Open`).
- **Entry Price:** $\text{Open}_{\text{14:00:00 bar}}$ (timestamped `14:00:00` or `14:05:00` UTC).
- **Direction:** Counter-trend fading of the morning excursion:
  $$\text{Direction}_t = \begin{cases} -1 \text{ (SHORT)} & \text{if } \Delta P_t > 0 \text{ (Fade upward overshoot)} \\ +1 \text{ (LONG)} & \text{if } \Delta P_t < 0 \text{ (Fade downward overshoot)} \end{cases}$$

### 2.2 Stop-Loss Placement & Slippage Handling
- **Stop Distance:** Positioned at $75\%$ of the morning excursion beyond entry price:
  $$\text{Stop Distance}_t = 0.75 \times |\Delta P_t|$$
  - **For Short Trades:** $\text{Stop Price} = \text{Entry Price} + \text{Stop Distance}_t$
  - **For Long Trades:** $\text{Stop Price} = \text{Entry Price} - \text{Stop Distance}_t$
- **Adverse Open Gap Rule:** If a bar opens beyond the stop level, execution fills at the bar Open price (full adverse slippage realized).
- **Adverse Entry Gap Abort:** If the entry bar opens beyond the stop price, the trade is aborted immediately (zero fill).

### 2.3 Scheduled Time Exit & Intrabar Order of Operations
- **Holding Period:** 14:05:00 to 18:30:00 UTC (4 hours 25 minutes, 53 M5 bars).
- **Scheduled Time Exit:** Flat exit at `18:30:00 UTC Close` (the `18:25` M5 bar close, coinciding with the official COMEX pit close).
- **Intrabar Precedence:** On every bar $j \in [t_{\text{entry}}, t_{\text{exit}}]$, stop-loss evaluation strictly precedes scheduled time exit evaluation.

---

## 3. Transaction Cost & Financing Model

Every trade is assessed round-turn transaction friction:
$$\text{Gross PnL} = (\text{Exit Price} - \text{Entry Price}) \times \text{Direction}$$
$$\text{Net PnL} = \text{Gross PnL} - C_{\text{round-turn}}$$

| Cost Scenario | Round-Turn Spread ($/oz) | Round-Turn Slippage ($/oz) | Total Friction ($/oz) |
| :--- | :--- | :--- | :--- |
| **1.0× Baseline** | $0.20 | $0.05 | **$0.25** |
| **1.5× Elevated** | $0.30 | $0.075 | **$0.375** |
| **2.0× Stressed** | $0.40 | $0.10 | **$0.50** |

- **Overnight Financing (Swap):** **$0.00/oz** across 100% of trades. Positions enter at 14:05 UTC and liquidate at 18:30 UTC, terminating 2.5 hours prior to the 21:00 UTC daily rollover window. Zero overnight or weekend holding.

---

## 4. Pre-Registered Promotion Gates & Rejection Thresholds

To pass controlled development (Phase 25) and subsequent out-of-sample evaluation, `HYP-24-NY-REVERSAL-EXHAUSTION` must satisfy **all** of the following quantitative criteria:

1. **Economic Edge:**
   - Net Expectancy per trade $\ge +\$0.50/\text{oz}$ after 1.0× baseline friction ($0.25/oz).
   - Net Profit Factor $\ge 1.25$.
   - Directional Win Rate $\ge 52.5\%$.
   - Positive net PnL maintained under 1.5× elevated cost stress ($0.375/oz).
2. **Directional Symmetry Gate:**
   - Both Long and Short directional sub-cohorts must achieve Net Profit Factor $\ge 1.10$.
   - Any directional breakdown (e.g. either side failing with PF $< 1.0$) mandates immediate rejection.
3. **Statistical Significance Gate:**
   - Primary Metric: Moving-block bootstrap 95% confidence interval ($B = 2,000, b = 5$) for mean net expectancy must strictly exclude zero (lower bound $> \$0.00/\text{oz}$).
   - Outperformance over the $0 no-trade cash baseline must be statistically established at $\alpha = 0.05$.
4. **Drawdown Boundary:**
   - Maximum peak-to-trough equity drawdown must not exceed $\$45.00/\text{oz}$ ($< 0.50\%$ of asset price).
