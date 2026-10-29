# Phase 18B: Daily/Weekly Macro Research Feasibility Assessment

**Status:** Completed & Methodologically Verified  
**Date:** October 2026  
**Objective:** Evaluate whether a daily/weekly macro-horizon gold research redesign is statistically and economically viable before any implementation.  
**Scope:** Research Design & Feasibility Audit Only. No model training, strategy implementation, or live trading.  
**Final Verdict:** `MACRO RESEARCH FEASIBLE AFTER DATA ACQUISITION`

---

## Executive Summary

Phase 17 and Phase 18A proved that high-frequency M5 intraday models fail primarily because transaction friction ($\sim \$0.60/\text{oz}$) consumes $26.6\%$ of the median 2-hour price move ($\$2.26/\text{oz}$). At multi-hour and daily horizons, transaction cost friction drops to $4.0\%\text{--}6.0\%$ of median price movement ($\$10.06/\text{oz}$ at $H=288$), dramatically lowering the empirical break-even hurdle.

However, moving to a daily macro horizon fundamentally alters the research paradigm:
1.  **Data Frequency Reality:** An institutional gold trading day contains **276 M5 bars**, not 288 bars. Across 2021–2024, exactly **984 institutional daily bars** exist.
2.  **Macro Feature Inventory:** **Zero macroeconomic variables** (real yields, dollar index, breakeven inflation, central bank flows) exist in the local repository.
3.  **Sample-to-Feature Dimensionality:** With only $N = 984$ daily observations, the existing 232-feature set would result in an overparameterization ratio of $N/D = 4.2:1$, guaranteeing catastrophic overfitting. Model complexity must be strictly constrained to **$D \le 5$ pre-specified explanatory variables**.

**Verdict:** The macroeconomic research redesign is economically and statistically viable **only after external macroeconomic data is acquired** under a pre-registered protocol.

---

## 1. Data Feasibility Assessment

### A. Existing Dataset Inventory & Timestamp Alignment

The existing local dataset consists strictly of intraday M5 quotes:
*   **Path:** `data/features/XAUUSD_M5_features_train.parquet`
*   **Time Span:** 2021-03-11 00:00:00 to 2024-12-31 21:55:00 UTC
*   **Total Rows:** 260,821 bars
*   **Time Frequency:** 5-minute intervals (M5)

### B. Construction of Institutional Daily OHLC Bars

Can genuine daily OHLC bars be constructed reliably from the local M5 dataset? **Yes.**

In institutional gold trading, the market calendar operates as follows:
*   **Daily Session Start:** 18:00 New York Time (22:00 or 23:00 UTC depending on Daylight Saving Time).
*   **Daily Session End (Settlement):** 17:00 New York Time the following day.
*   **Daily Trading Duration:** Exactly 23 hours of continuous trading.
*   **Daily Maintenance Rollover Gap:** 17:00 to 18:00 New York Time (1 hour closure, Mon–Thu).
*   **Weekend Closure:** Friday 17:00 New York Time to Sunday 18:00 New York Time.

#### Standard Session Bar Count
$$23 \text{ hours} \times 12 \text{ bars/hour} = \mathbf{276 \text{ M5 bars per standard daily session}}$$

#### Refutation of the $H=288$ Calendar Day Equivalence
In prior research phases, $H = 288$ bars was colloquially referred to as "the 24-hour daily horizon."
*   **Flaw:** 288 M5 bars represents 24.0 hours of *uninterrupted continuous trading*. Because spot gold trading halts for 1 hour every day at 17:00 NY, a rolling window of 288 bars spans across the daily closure gap and shifts its alignment relative to the New York settlement by 12 bars (1 hour) every single day.
*   **Methodological Rule:** $H=288$ is an intraday rolling window, **not a true daily bar**. Genuine daily research must aggregate M5 bars according to institutional New York session boundaries (17:00 NY close to 17:00 NY close).

#### Empirical Daily Aggregation (2021–2024)
Aggregating the 260,821 M5 bars into institutional daily bars yields:
*   **Total Institutional Daily Bars ($N$):** **984 bars**
    *   2021: 210 bars (dataset begins March 11, 2021)
    *   2022: 258 bars
    *   2023: 257 bars
    *   2024: 259 bars
*   **Approximate Weekly Bars:** **196 bars**

### C. Local Macro Variables Inventory

An exhaustive audit of all 232 columns in `XAUUSD_M5_features_train.parquet` confirms:
*   **Locally Available Macroeconomic Series:** **ZERO (0)**
*   **Existing Feature Composition:** Exclusively intraday technical indicators (RSI, ATR, EMA distances, MACD, Bollinger Bands, rolling volatility, multi-timeframe H1/H4 momentum, and time-of-day cyclicals).

*Methodological Rule:* Under no circumstances will technical indicators (such as 200-period moving averages or ATR) be relabeled as "macro features," nor will synthetic macro series be simulated. Authentic macroeconomic research requires acquiring verified external series.

---

## 2. Sample-Size & Statistical Feasibility

### A. Dimensionality Constraint & Overparameterization Risk

A transition from high-frequency M5 modeling ($N = 260,821$) to daily modeling ($N = 984$) causes a **$265\times$ reduction in sample size**.

*   **Risk of Using Existing Feature Set:**
    If the existing 232 features were fitted against 984 daily bars, the sample-to-feature ratio would be:
    $$\frac{N}{D} = \frac{984}{232} \approx 4.24 \text{ observations per feature}$$
    In time-series modeling with serial correlation, an $N/D$ ratio of $4.2$ guarantees catastrophic in-sample overfitting, spurious correlation, and total out-of-sample breakdown.
*   **Strict Complexity Bound:**
    To maintain statistical validity ($N/D \ge 150:1$), any daily macro research design must restrict itself to a **maximum of $D \le 5$ pre-specified explanatory variables**:
    $$\frac{N}{D} = \frac{984}{5} = \mathbf{196.8 \text{ observations per feature}}$$

### B. Accounting for Market Realities

When designing a macro empirical study, the following real-world factors must be rigorously handled:
1.  **Publication Lags & Release Timing:** Macroeconomic data (e.g. CPI, nonfarm payrolls, GDP) are released with delays ranging from weeks to months. Using nominal calendar timestamps results in fatal look-ahead bias. All macro indicators must use the **release timestamp**, not the reference period.
2.  **Data Revisions:** Series like GDP and Nonfarm Payrolls undergo substantial revisions. Historical backtests must use point-in-time (unrevised first-release) vintages.
3.  **Market Holidays:** US holidays (Thanksgiving, Independence Day, Labor Day) close fixed-income markets (Treasuries) while international spot gold continues light trading. Alignment must handle non-overlapping holiday calendars without forward-filling prices.

---

## 3. External Data Acquisition Specification

To enable genuine macroeconomic research, the following external data series must be acquired prior to model development:

| Variable Name | Economic Rationale | Target Source | Canonical Series ID | Publication Frequency | Point-in-Time Lag Rule |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **US 10-Year Real Yield** | Primary opportunity cost of holding non-yielding physical gold. | Federal Reserve Economic Data (FRED) | `DFII10` (10-Year TIPS) | Daily (Market Close) | Available 16:00 NY; usable for 18:00 NY entry. |
| **US Dollar Index (DXY)** | Gold is globally denominated in USD; dollar purchasing power directly drives gold valuation. | ICE / Federal Reserve | `DTWEXBGS` / `DX-Y.NYB` | Continuous / Daily Close | Sliced at 16:30 NY settlement. |
| **10-Year Breakeven Inflation** | Market-implied long-term inflation hedge demand. | FRED / US Treasury | `T10YIE` | Daily (Market Close) | Available 16:00 NY; usable for 18:00 NY entry. |
| **Fed Funds Policy Expectations** | Anticipated monetary policy shifts and real rate trajectories. | CME FedWatch / Fed Funds Futures (`ZQ`) | Front-Month & Second-Month Futures | Daily Close | Sliced at 17:00 NY daily settlement. |
| **Central Bank / ETF Holdings** | Physical gold investment flow proxy. | World Gold Council / Bloomberg | SPDR Gold Shares (`GLD` Shares Out) | Daily / Weekly | Released post-market; lagged 1 full session. |

### Data Quality & Verification Requirements
1.  **Format:** Parquet format with explicit timezone UTC timestamps.
2.  **Alignment Key:** Institutional Gold Session Date (defined as 17:00 NY to 17:00 NY).
3.  **Audit Trail:** Cryptographic SHA-256 hash generated upon ingest and permanently recorded.

---

## 4. Pre-Registered Macro Research Protocol

Before executing any models or backtests, the research design is pre-registered as follows:

### A. Primary Hypothesis
$$\mathcal{H}_1: \text{Daily changes in US 10-Year Real Yields } (\Delta y_{t}^{\text{real}}) \text{ and US Dollar Index momentum } (\Delta \text{DXY}_t) \text{ negatively forecast next-day spot gold excess returns net of execution costs and overnight financing debits.}$$

$$\mathbb{E}[R_{t+1}^{\text{gold}} \mid \Delta y_t^{\text{real}} < 0, \Delta \text{DXY}_t < 0] > \text{Transaction Friction} + \text{Swap Debit}$$

### B. Pre-Specified Explanatory Features ($D \le 5$)
1.  `d1_real_yield_change`: $\text{TIPS}_{10Y}(t) - \text{TIPS}_{10Y}(t-1)$ (in basis points).
2.  `d5_real_yield_momentum`: $\text{TIPS}_{10Y}(t) - \text{TIPS}_{10Y}(t-5)$ (5-day rolling change).
3.  `d1_dxy_log_return`: $\ln(\text{DXY}_t / \text{DXY}_{t-1})$.
4.  `d5_dxy_momentum`: $\ln(\text{DXY}_t / \text{DXY}_{t-5})$.
5.  `d1_breakeven_change`: $\text{BE}_{10Y}(t) - \text{BE}_{10Y}(t-1)$.

### C. Target Variable & Holding Horizon
*   **Target:** Next-day institutional settlement return:
    $$y_t = \frac{\text{Close}_{t+1} - \text{Open}_{t+1}}{\text{Open}_{t+1}}$$
*   **Execution Timing:**
    *   Decision Time: 17:15 NY (after macro daily closing releases are published).
    *   Entry Time: 18:00 NY (market open of the new institutional session).
    *   Exit Time: 17:00 NY next calendar day (market close/settlement).
    *   Holding Horizon: Exactly 1 institutional day (23 trading hours).

### D. Benchmark Baselines
Every candidate model must be benchmarked against:
1.  **No-Trade Baseline:** Net $\text{PnL} = \$0.00$ (the mandatory hurdle for positive expectancy).
2.  **Passive Buy-and-Hold:** Long 1 oz throughout the evaluation period.
3.  **Prior-Day Directional Momentum:** Long if $R_t^{\text{gold}} > 0$, Short if $R_t^{\text{gold}} < 0$.

### E. Execution Cost & Financing Assumptions
*   **Broker Spread:** $\$0.20/\text{oz}$ (institutional spot gold spread).
*   **Slippage:** $\$0.05/\text{oz}$ on entry and $\$0.05/\text{oz}$ on exit.
*   **Overnight Financing (Swap):** Because positions are held across the 17:00 NY roll, financing must be charged:
    *   Long Swap: $-\$0.12/\text{oz}$ per day (equivalent to $\approx -0.02\%$ daily debit).
    *   Wednesday Rollover: $3\times$ swap charged for weekend settlement.
*   **Total Modeled Daily Cost:** **$\sim \$0.42/\text{oz}$ per trade** (compared to median daily movement of $\$10.06/\text{oz}$, cost friction is $\approx 4.17\%$).

### F. Chronological Data Partitioning (Strictly Preserving Protected Data)

Under no circumstances will the protected 2025 validation partition (`val.parquet`) or frozen 2026 test partition (`test.parquet`) be touched.

The 2021–2024 training dataset ($N = 984$ daily bars) will be split chronologically:
*   **Development / Initial Model Fitting:** 2021-03-11 to 2022-12-30 ($\approx 468$ daily bars). Used for parameter tuning, lag selection, and cross-validation.
*   **Internal Out-of-Sample Evaluation:** 2023-01-02 to 2024-12-31 ($\approx 516$ daily bars). Evaluated strictly out-of-fold without re-tuning.

### G. Economic Promotion Gate & Multiple-Testing Controls
*   **Economic Hurdle:** **Net Profit Factor $> 1.25$** across the out-of-sample evaluation period (2023–2024), net of spread, slippage, and overnight swap.
*   **Multiple Testing & Statistical Controls:**
    *   Adjustment of $p$-values via the Holm-Bonferroni correction to penalize multiple model evaluations.
    *   Stationary Bootstrap (Politis & Romano) with block length calibrated to residual return autocorrelation.
    *   Explicit acknowledgment: Meeting the Net $\text{PF} > 1.25$ gate is a necessary screening filter, not standalone proof of future profitability.

---

## 5. Final Verdict & Justification

### Final Verdict Choice
```
MACRO RESEARCH FEASIBLE AFTER DATA ACQUISITION
```

### Justification & Limitations
1.  **Economic & Statistical Viability:** Aggregating M5 data to institutional daily bars (276 M5 bars/session) is fully reproducible and expands median move size from $\$2.26/\text{oz}$ to $\$10.06/\text{oz}$, reducing cost friction from $26.6\%$ to $\sim 4.2\%$.
2.  **Data Prerequisite:** Zero macroeconomic series exist locally. Model training cannot occur until external series (TIPS real yields, DXY, breakeven inflation) are formally acquired and validated against the Data Acquisition Specification.
3.  **Strict Dimensionality Invariant:** With $N = 984$, model complexity must not exceed $D \le 5$ explanatory features to prevent overparameterization.
4.  **Governance Invariant:** Protected 2025 validation and frozen 2026 test partitions remain completely uninspected and intact.
