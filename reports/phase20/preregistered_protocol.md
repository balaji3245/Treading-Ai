# Phase 20: Pre-Registered Macroeconomic Hypothesis Testing Protocol

**Status:** Pre-Registered & Frozen Prior to Out-of-Sample Evaluation  
**Date:** October 2026  
**Auditor:** Quantitative Researcher & Independent Validation Auditor  
**Data Partition Governance:**
*   **Development / In-Sample Period:** 2021-03-11 through 2022-12-30 ($N_{\text{dev}} = 468$ daily sessions).
*   **Out-of-Sample Evaluation Period:** 2023-01-02 through 2024-12-31 ($N_{\text{oos}} = 516$ daily sessions).
*   **Protected Partitions:** Strict zero-access enforced for 2025 Validation (`val.parquet`) and 2026 Test (`test.parquet`).
*   **Protocol Hash (SHA-256):** Computed and logged prior to out-of-sample execution.

---

## 1. Primary Research Hypothesis

$$\mathcal{H}_1: \text{Daily changes in US 10-Year Real Treasury Yields and Broad US Dollar strength contain statistically credible,}$$
$$\text{out-of-sample predictive information for next-session XAUUSD excess returns net of execution and financing costs.}$$

### Expected Economic Directionality
Under standard macroeconomic pricing theory:
1.  **Real Interest Rate Hypothesis ($\beta_{\text{yield}} < 0$):** Gold is a non-yielding real asset. An increase in 10-Year TIPS real yield ($\Delta y_t > 0$) raises the opportunity cost of holding physical gold, negatively impacting next-session gold returns.
2.  **US Dollar Strength Hypothesis ($\beta_{\text{dollar}} < 0$):** Gold is globally denominated in USD. An increase in the trade-weighted US Dollar Index ($\Delta d_t > 0$) reduces international purchasing power, negatively impacting next-session gold returns.
3.  **Inflation Expectation Hypothesis ($\beta_{\text{inflation}} > 0$):** An increase in 10-Year breakeven inflation ($\Delta b_t > 0$) increases demand for inflation hedges, positively impacting next-session gold returns.

*Scientific Mandate:* These are theoretical hypotheses, not established facts for this dataset. They must be empirically tested out-of-sample without retrospective curve-fitting.

---

## 2. Input Data Series & Retrospective Limitations

The test evaluates the official macroeconomic series acquired in Phase 19:
*   **`DFII10`:** Market Yield on U.S. Treasury Securities at 10-Year Constant Maturity, Inflation-Indexed (FRED / US Treasury).
*   **`DTWEXBGS`:** Nominal Broad U.S. Dollar Index, goods-and-services trade-weighted against 26 trading partners (FRED / Federal Reserve Board H.10 Release). **Critical:** This is the Federal Reserve Broad Dollar Index, NOT the tradable 6-currency ICE DXY index.
*   **`T10YIE`:** 10-Year Breakeven Inflation Rate (FRED / St. Louis Fed / US Treasury).

### Point-in-Time Status: Retrospective Proxy
Phase 19 established that FRED daily CSVs record observation dates (`YYYY-MM-DD`) without intraday release timestamps, and `DTWEXBGS` historical trade weights reflect current-vintage annual recalculations. Therefore, this experiment is explicitly pre-registered as a **retrospective proxy**, not a certified point-in-time backtest.

---

## 3. Publication Lag & Alignment Policy

To prevent operational look-ahead bias, trade entry uses the **Conservative Availability Lag (Policy 1B)**:
*   **Decision Timestamp:** 17:45 New York Time (during the daily 17:00–18:00 NY rollover closure).
*   **Trade Entry Timestamp:** 18:00 New York Time (session open).
*   **Lag Rule:** Macro observation date must satisfy:
    $$\text{Macro Observation Date} \le \text{Entry Calendar Date} - 1 \text{ Business Day}$$
*   **Holiday Policy:** Forward-fill last observed market close up to a strict limit of 3 calendar days to bridge weekends and single-day market holidays. Unlimited forward-filling is strictly prohibited.
*   **Age Tracking:** The age of each observation $\Delta t_{\text{age}} = \text{Entry Date} - \text{Macro Date}$ is recorded for every session.

---

## 4. Target Return & Execution Definitions

### A. Target Variable
The prediction target is the next institutional gold session return:
$$\text{Return}_{t+1} = \frac{\text{Close}_{t+1} - \text{Open}_{t+1}}{\text{Open}_{t+1}}$$
$$\text{Gross PnL}_{t+1} (\$/\text{oz}) = \text{Close}_{t+1} - \text{Open}_{t+1}$$

*   **Holding Period:** Exactly 1 institutional trading day (18:00 NY entry to 17:00 NY exit next day, 23 trading hours).
*   **Pricing Basis:** HistData Bid quotes. Bid-only execution is evaluated with synthetic round-turn friction $C$.

### B. Transaction Cost & Financing Model
Baseline costs are pre-registered as follows:
*   **Broker Spread:** $\$0.20/\text{oz}$ round turn (broker quote $S = \$0.20$ crossed once across round-turn execution).
*   **Slippage:** $\$0.10/\text{oz}$ round turn ($\$0.05/\text{oz}$ on entry at 18:00 NY, $\$0.05/\text{oz}$ on exit at 17:00 NY).
*   **Overnight Financing (Swap):** 
    *   Standard sessions (held across 17:00 NY roll): $-\$0.12/\text{oz}$ per calendar day.
    *   Wednesday session (settling Friday for weekend delivery): $3\times$ swap debit ($-\$0.36/\text{oz}$).
*   **Baseline Round-Turn Friction ($C_{\text{base}}$):**
    *   Non-Wednesday session: $\$0.20 + \$0.10 + \$0.12 = \mathbf{\$0.42/\text{oz}}$.
    *   Wednesday session: $\$0.20 + \$0.10 + \$0.36 = \mathbf{\$0.66/\text{oz}}$.
    *   Average baseline cost per active trade: $\approx \mathbf{\$0.47/\text{oz}}$.
*   **Sensitivity Scenarios:**
    1.  **Baseline Costs ($1.0\times$):** As defined above.
    2.  **Elevated Costs ($1.5\times$):** Spread $\$0.30$, Slippage $\$0.15$, Swap $\$0.18$ ($\$0.54$ Wed) $\implies \approx \$0.70/\text{oz}$.
    3.  **Stressed Costs ($2.0\times$):** Spread $\$0.40$, Slippage $\$0.20$, Swap $\$0.24$ ($\$0.72$ Wed) $\implies \approx \$0.94/\text{oz}$.

---

## 5. Candidate Models & Benchmarks ($D \le 5$)

All features and standardization parameters are fit **strictly on Development Data (2021-03-11 to 2022-12-30)** and frozen prior to out-of-sample evaluation:

### Primary Candidate Models

1.  **Model A (Real-Yield Change Only):**
    *   Feature: $\Delta y_t = y_t - y_{t-1}$ (1-day change in 10Y TIPS real yield in percentage points).
    *   Signal: $\text{Position}_t = -\text{sign}(\Delta y_t)$. Long if real yields fell; Short if real yields rose.
2.  **Model B (Broad-Dollar Change Only):**
    *   Feature: $\Delta d_t = (d_t - d_{t-1}) / d_{t-1}$ (1-day percentage change in Broad Dollar Index).
    *   Signal: $\text{Position}_t = -\text{sign}(\Delta d_t)$. Long if dollar weakened; Short if dollar strengthened.
3.  **Model C (Bivariate Macro Model):**
    *   Features: Standardized $\tilde{\Delta y}_t$ and $\tilde{\Delta d}_t$ (using Development mean and std).
    *   Composite Score: $s_t = -0.5 \cdot \tilde{\Delta y}_t - 0.5 \cdot \tilde{\Delta d}_t$.
    *   Signal: $\text{Position}_t = \text{sign}(s_t)$.
4.  **Model D (Trivariate Macro Composite):**
    *   Features: Standardized $\tilde{\Delta y}_t$, $\tilde{\Delta d}_t$, and 1-day change in breakeven inflation $\tilde{\Delta b}_t$.
    *   Composite Score: $s_t = -0.4 \cdot \tilde{\Delta y}_t - 0.4 \cdot \tilde{\Delta d}_t + 0.2 \cdot \tilde{\Delta b}_t$.
    *   Signal: $\text{Position}_t = \text{sign}(s_t)$.

### Benchmark Models

5.  **Benchmark E (No-Trade Baseline):** Position = 0 for all sessions. Gross PnL = $\$0.00$, Costs = $\$0.00$, Net PnL = $\$0.00$. (Mandatory zero-return reference).
6.  **Benchmark F (Passive Buy-and-Hold):** Position = +1 (Long 1 oz) for every session. Pays overnight swap every session.
7.  **Benchmark G (Prior-Session Momentum):** $\text{Position}_t = \text{sign}(\text{Return}_{t-1})$.

---

## 6. Pre-Registered Evaluation Metrics & Statistical Controls

### A. Predictive Metrics
*   Pearson correlation ($r$) between continuous macro score and realized return, with two-tailed $t$-test $p$-value.
*   Regression $R^2$ on out-of-sample returns.
*   Directional accuracy (hit rate %) vs. 50.0% null.

### B. Trading & Economic Metrics
*   Gross PnL ($\$/\text{oz}$) and Net PnL ($\$/\text{oz}$).
*   Net Profit Factor: $\text{PF}_{\text{net}} = \sum \text{Net Wins} / \sum |\text{Net Losses}|$.
*   Maximum Drawdown ($\$/\text{oz}$ and peak-to-trough percentage).
*   Win Rate (%) and Total Active Trade Count.

### C. Statistical Uncertainty & Multiple-Testing Correction
*   **Stationary Bootstrap:** 2,000 resamples using block bootstrap (average block length = 5 sessions to account for residual serial dependence).
*   **Confidence Intervals:** 95% bootstrap confidence intervals for Net PnL and Net Profit Factor.
*   **Multiple-Testing Adjustment:** **Holm–Bonferroni correction** applied across the family of 4 candidate models ($M = 4$) at nominal $\alpha = 0.05$:
    *   Rank sorted $p$-values: $p_{(1)} \le p_{(2)} \le p_{(3)} \le p_{(4)}$.
    *   Thresholds: $\alpha / (M - k + 1)$ for $k = 1, \dots, 4$.

---

## 7. Pre-Registered Promotion Criteria

To earn promotion to further research phases, a candidate model must strictly satisfy **all** of the following criteria out-of-sample (2023–2024):
1.  **Economic Hurdle:** Out-of-sample Net Profit Factor $> 1.25$.
2.  **Positive Net PnL:** Net PnL after baseline costs must be strictly greater than $\$0.00$ (beating the No-Trade baseline).
3.  **Statistical Significance:** $p$-value must survive Holm–Bonferroni multiple-testing adjustment ($\alpha = 0.05$).
4.  **Cost Robustness:** Strategy must maintain positive net expectancy under $1.5\times$ and $2.0\times$ cost stress.
5.  **No Outlier Dependence:** Top single trade must account for less than 25% of total cumulative net profits.
6.  **Point-in-Time Caveat:** Even if numerical criteria pass, the model must be classified as **`PROMISING BUT POINT-IN-TIME UNVALIDATED`** rather than a proven live edge, due to FRED's historical vintage limitations.

*Commitment:* If all candidate models fail to meet these criteria, the result will be reported honestly and without optimization as **`NO EVIDENCE OF PREDICTIVE EDGE`**.
