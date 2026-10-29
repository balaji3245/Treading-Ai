# Treading-AI — Phase 14 Research Audit Report
## Forensic Robustness Audit, Independent Reproduction, and Selection-Bias Assessment of Candidate 5 (Peak Liquidity Session Swing)

**Asset:** XAUUSD (Spot Gold)  
**Timeframe:** M5 Intraday with Multi-Timeframe Alignment  
**Candidate Under Audit:** Candidate 5 (London/NY Overlap, $H=96$ bars / 8.0 hours)  
**Evaluation Scope:** 2021–2024 Historical Training Partition Only (260,821 M5 Bars)  
**Protected 2025 Validation Partition:** UNINSPECTED & PRESERVED  
**Frozen 2026 Test Partition:** FROZEN & COMPLETELY UNTOUCHED  
**Date of Audit:** October 2026  
**Auditor / Role:** Senior Quantitative Research Engineer, Financial ML Auditor, and Microstructure Specialist  
**Test Suite Status:** 155 passed in 2.92s (100% pass rate across 23 test modules)  

---

## FINAL VERDICT

```
========================================================================================
FINAL VERDICT: PROMISING BUT STATISTICALLY INCONCLUSIVE
DECISION GATE RECOMMENDATION: REJECT PROMOTION
========================================================================================
1. Independent Reproduction:
   All Phase 13 reported metrics reproduced down to the cent across 531 raw trades.
   Capacity control is mathematically verified (zero overlap violations).
2. Promising Characteristics:
   Gross alpha expanded 5x over the incumbent to +$0.499/trade (Gross PF: 1.101).
   Total net losses contracted by 94.6% (-$1,370.41 down to -$73.72/oz).
   The Long side achieved net profitability after friction (+$67.24/oz across 257 trades).
   In Winter months (EST/GMT), the strategy achieved net profitability (+$278.47/oz).
3. Disqualifying Weaknesses & Lack of Robustness:
   Aggregate net PnL remains negative (-$73.72/oz, Net PF: 0.974).
   Fails chronological fold consistency (Fold 1: -$53.54, Fold 2: -$77.76; 2022 and 2023 lost).
   Summer performance collapsed (-$352.19/oz net loss, 43.2% win rate).
   Block bootstrap 95% CI spans zero ([-$1.19, +$1.02/trade], p = 0.824).
   Significant parameter-selection bias: Candidate 5 was designed post-hoc using Phase 12
   session error diagnostics on the exact same 2021-2024 training data.
4. Decision Gate Mandate:
   Candidate 5 is REJECTED for promotion. The No-Trade Baseline ($0.00) remains superior.
   Protected 2025 Validation and frozen 2026 Test partitions MUST remain untouched.
========================================================================================
```

---

## 1. Executive Summary & Audit Objectives

In Phase 13, Candidate 5 (Peak Liquidity Session Swing) emerged as the single most improved configuration in the Treading-AI project, compressing cumulative net losses from $-\$1,370.41/\text{oz}$ down to $-\$73.72/\text{oz}$, generating $+\$265.08/\text{oz}$ in gross profit, and turning the Long side net profitable ($+\$67.24/\text{oz}$).

However, scientific discipline demands that an apparent improvement not be mistaken for a validated trading edge. Phase 14 was conducted as an adversarial forensic audit to determine:
1. Are the results mathematically reproducible from raw trade execution logs?
2. Did session filtering introduce subtle lookahead, clock leakage, or overlapping position distortions?
3. How does performance hold up across individual years, seasons (summer vs. winter DST), volatility regimes, and holding horizons?
4. How much of Candidate 5's performance is attributable to post-hoc parameter-selection bias?
5. Does Candidate 5 satisfy objective economic criteria for strategy qualification?

---

## 2. Section 1: Independent Reproduction of Candidate 5 Results

We conducted an independent recalculation directly from trade-by-trade execution records across all three chronological walk-forward folds.

### 2.1 Metric-by-Metric Parity Table

```
========================================================================================
INDEPENDENT REPRODUCTION & VERIFICATION TABLE (CANDIDATE 5, N = 531 TRADES)
========================================================================================
Metric                          Phase 13 Reported   Phase 14 Reproduced   Parity Status
----------------------------------------------------------------------------------------
Trade Count                                   531                   531     EXACT MATCH
Gross PnL ($/oz)                         +$265.08              +$265.08     EXACT MATCH
Total Friction ($/oz)                     $338.80               $338.80     EXACT MATCH
Net PnL ($/oz)                            -$73.72               -$73.72     EXACT MATCH
Gross Expectancy ($/trade)                +$0.499               +$0.499     EXACT MATCH
Friction Expectancy ($/trade)              $0.638                $0.638     EXACT MATCH
Net Expectancy ($/trade)                  -$0.139               -$0.139     EXACT MATCH
Net Win Rate (%)                            48.2%                 48.2%     EXACT MATCH
Gross Profit Factor                         1.101                 1.101     EXACT MATCH
Net Profit Factor                           0.974                 0.974     EXACT MATCH
Maximum Drawdown ($/oz)                   $440.31               $440.31     EXACT MATCH
Break-Even Cost Multiplier                 0.782x                0.782x     EXACT MATCH
Break-Even Base Spread ($/oz)           $0.156/oz             $0.156/oz     EXACT MATCH
Overlap Position Violations                     0                     0     VERIFIED (0)
========================================================================================
```

### 2.2 Position Capacity & Fill Integrity
- **Non-Overlapping Verification:** We checked the temporal ordering of all consecutive trades within each fold. In 100% of cases ($531/531$), $\text{entry\_index}_{k} \ge \text{exit\_index}_{k-1}$. The strategy strictly held at most a single 1-oz position at any instant.
- **Deductive Parity:** Fill-based reconciliation confirmed that $(\text{Exit Fill} - \text{Entry Fill} - \text{Commission}) == \text{Net PnL}$ for Long trades and $(\text{Entry Fill} - \text{Exit Fill} - \text{Commission}) == \text{Net PnL}$ for Short trades across all 531 records with zero numerical errors ($< 10^{-6}$).

---

## 3. Section 2: Session Timing & Daylight-Saving Audit

The Phase 13 report described the entry window as "12:00–16:30 UTC". We performed a granular forensic audit of how timestamps and sessions are evaluated in code.

### 3.1 Local Clock Evaluation vs. Static UTC Window

The actual implementation in [`ExecutionCostModel.get_session_name`](file:///home/bhoot/project/Treading-Ai/src/treading_ai/backtesting/cost_model.py#L218) does **not** evaluate a static UTC window. Instead, it converts timestamps dynamically to local clocks:

```python
# From src/treading_ai/backtesting/cost_model.py
ts_ny = ts_utc.astimezone(ZoneInfo("America/New_York"))
ts_london = ts_utc.astimezone(ZoneInfo("Europe/London"))

min_london = ts_london.hour * 60 + ts_london.minute
min_ny = ts_ny.hour * 60 + ts_ny.minute

london_active = (8 * 60 <= min_london < 16 * 60 + 30) and ts_london.weekday() < 5
ny_active = (8 * 60 <= min_ny < 17 * 60) and ts_ny.weekday() < 5

if london_active and ny_active:
    return "LONDON_NY_OVERLAP"
```

### 3.2 The Impact of Daylight Saving Time (DST)
Because London operates on GMT (UTC+0) in winter and BST (UTC+1) in summer, while New York operates on EST (UTC-5) in winter and EDT (UTC-4) in summer:
- **In Summer (April–October):**
  * London is BST (08:00–16:30 BST = 07:00–15:30 UTC).
  * New York is EDT (08:00–17:00 EDT = 12:00–21:00 UTC).
  * The actual overlap is **12:00 to 15:30 UTC** (3.5 hours).
- **In Winter (November–March):**
  * London is GMT (08:00–16:30 GMT = 08:00–16:30 UTC).
  * New York is EST (08:00–17:00 EST = 13:00–22:00 UTC).
  * The actual overlap is **13:00 to 16:30 UTC** (3.5 hours).

*Audit Finding:* Describing the entry window as "12:00–16:30 UTC" was a descriptive shorthand representing the union envelope of summer and winter hours. The actual software engine correctly tracked dynamic local trading hours without lookahead.

### 3.3 The Seasonal Performance Divergence (Winter vs. Summer)

When we decomposed Candidate 5's trades by season, we discovered an extreme performance asymmetry:

```
========================================================================================
SEASONAL PERFORMANCE DECOMPOSITION (WINTER VS. SUMMER)
========================================================================================
Season                  Trades   Gross PnL    Friction    Net PnL     Net Win%   Net Exp
----------------------------------------------------------------------------------------
Winter (EST / GMT)         193   +$403.36      $124.89   +$278.47      57.0%    +$1.443/t
Summer (EDT / BST)         338   -$138.28      $213.91   -$352.19      43.2%    -$1.042/t
----------------------------------------------------------------------------------------
Net Seasonal Spread       -145   +$541.64      -$89.02   +$630.66     +13.8%    +$2.485/t
========================================================================================
```

*Critical Discovery:*
1. **Winter is Highly Profitable:** In winter months (193 trades), Candidate 5 produced **+$278.47/oz in net profits** ($+\$1.443/\text{trade}$ net expectancy, 57.0% net win rate, Gross PnL +$403.36/oz).
2. **Summer Suffered Severe Losses:** In summer months (338 trades), Candidate 5 suffered **-$352.19/oz in net losses** ($-\$1.042/\text{trade}$ net expectancy, 43.2% win rate).
3. **Microstructure Explanation:** During winter, New York opens at 13:00 UTC and London closes at 16:30 UTC, aligning with peak US morning macroeconomic releases (CPI, NFP, GDP at 13:30 UTC) while European banks are fully active. In summer, the overlap shifts earlier (12:00–15:30 UTC), missing the late US session momentum.

---

## 4. Section 3: Subgroup & Stability Analysis

### 4.1 Chronological Fold & Yearly Stability

```
========================================================================================
YEARLY & FOLD-LEVEL PERFORMANCE BREAKDOWN
========================================================================================
Period / Slice          Trades   Gross PnL    Friction    Net PnL     Gross PF   Net PF
----------------------------------------------------------------------------------------
Fold 1 (Eval 2022)         208    +$72.23      $125.77    -$53.54      1.075     0.948
Fold 2 (Eval 2023)         142     +$5.12       $82.88    -$77.76      1.008     0.887
Fold 3 (Eval 2024)         181   +$187.73      $130.15    +$57.57      1.186     1.053
----------------------------------------------------------------------------------------
Year 2022                  208    +$72.23      $125.77    -$53.54      1.075     0.948
Year 2023                  142     +$5.12       $82.88    -$77.76      1.008     0.887
Year 2024                  181   +$187.73      $130.15    +$57.57      1.186     1.053
========================================================================================
```

*Finding:* Candidate 5 is **temporally unstable**. It produced net losses in both 2022 ($-\$53.54$) and 2023 ($-\$77.76$), turning net positive only in 2024 ($+\$57.57$). A strategy that loses money in two out of three years cannot be characterized as robust.

---

### 4.2 Directional Asymmetry: Long Bull-Market Reliance

```
========================================================================================
DIRECTIONAL BREAKDOWN (LONG VS. SHORT)
========================================================================================
Direction               Trades   Gross PnL    Friction    Net PnL     Gross PF   Net PF
----------------------------------------------------------------------------------------
Long Positions             257   +$193.98      $126.75    +$67.24      1.168     1.055
Short Positions            274    +$71.10      $212.06   -$140.96      1.049     0.911
========================================================================================
```

*Finding:* The entire positive net edge was confined to **Long positions** (+$67.24/oz net profit, Net PF: 1.055). Short positions generated positive gross PnL ($+\$71.10/oz$), but after execution friction ($-\$212.06/oz$), the Short side lost $-\$140.96/\text{oz}$. The Long outperformance coincided with the massive multi-year secular gold rally from $\$1,800$ to $\$2,700/\text{oz}$ during 2022–2024.

---

### 4.3 Volatility Regime Stability

```
========================================================================================
VOLATILITY REGIME STABILITY
========================================================================================
Regime (at Entry)       Trades   Gross PnL    Friction    Net PnL     Gross PF   Net PF
----------------------------------------------------------------------------------------
Normal Volatility          281   +$155.80      $163.67     -$7.86      1.100     0.995
High Volatility            250   +$109.28      $175.14    -$65.86      1.103     0.943
Low Volatility               0      $0.00        $0.00      $0.00      0.000     0.000
========================================================================================
```

*Finding:* The causal regime filter successfully suppressed all trades during low-volatility compression (0 trades in Low Volatility). In Normal volatility, the strategy came within $\$7.86/\text{oz}$ of breaking even (Net PF: 0.995). In High volatility, expanded slippage widened net drag ($-\$65.86/\text{oz}$).

---

## 5. Section 4: Uncertainty Estimation & Serial Dependence

To evaluate whether Candidate 5's $-\$0.139/\text{trade}$ net expectancy is statistically distinguishable from zero or positive alpha, we implemented a **Moving Block Bootstrap** (block size = 10 trades $\approx 80$ trading hours) to account for potential serial correlation:

```
========================================================================================
STATISTICAL UNCERTAINTY & INFERENCE (BLOCK BOOTSTRAP, 2,000 RESAMPLES)
========================================================================================
Metric                              Point Estimate         95% Block Bootstrap CI
----------------------------------------------------------------------------------------
Gross Expectancy ($/trade)             +$0.4992             [-$0.5503, +$1.6757]
Friction Expectancy ($/trade)           $0.6380             [+$0.6200, +$0.6550]
Net Expectancy ($/trade)               -$0.1388             [-$1.1885, +$1.0242]
Autocorrelation Lag 1 (Net PnL)         +0.0518             Weak positive persistence
Autocorrelation Lag 2 (Net PnL)         -0.0546             Negligible
Parametric t-statistic                  -0.2231             p = 0.8236
Wilcoxon Signed-Rank Statistic         68,095.0             p = 0.4407
========================================================================================
```

### Statistical Conclusions
1. **The 95% Confidence Interval Heavily Spans Zero:** The moving block bootstrap 95% CI is $[-\$1.19, +\$1.02/\text{trade}]$. Because zero is centered near the middle of this interval, we cannot reject the null hypothesis of zero edge.
2. **Hypothesis Testing is Inconclusive:** Parametric ($p = 0.824$) and non-parametric ($p = 0.441$) p-values are far above the standard $\alpha = 0.05$ threshold.
3. **Statistical Summary:** There is **no statistically verifiable proof of positive alpha**. The data is fully consistent with a random walk dragged down by $\$0.64/\text{trade}$ in transaction costs.

---

## 6. Section 5: Parameter Sensitivity & Cliff-Edge Analysis

To test whether the 96-bar horizon and 0.60 probability threshold represent a robust parameter plateau or an overfitted local peak, we mapped the parameter response surface across adjacent horizons ($H \in [72, 84, 96, 108, 120]$) and probability thresholds ($[0.50, 0.55, 0.60, 0.65]$) using Fold 1:

```
========================================================================================
HORIZON SENSITIVITY RESPONSE SURFACE (EVALUATION FOLD 1)
========================================================================================
Horizon (H)    Hours    Trades   Gross PnL    Friction    Net PnL     Net PF    Net Win%
----------------------------------------------------------------------------------------
H = 72 bars     6.0h       195   +$199.85     $102.30    +$97.55      1.114      50.8%
H = 84 bars     7.0h       204   +$106.63     $118.45    -$11.81      0.988      47.5%
H = 96 bars     8.0h       208    +$72.23     $125.77    -$53.54      0.948      47.1%
H = 108 bars    9.0h       218    +$91.07     $184.09    -$93.02      0.913      45.9%
H = 120 bars   10.0h       218   +$247.03     $115.08   +$131.95      1.139      50.9%
========================================================================================
```

```
========================================================================================
PROBABILITY THRESHOLD SENSITIVITY (EVALUATION FOLD 1, H = 96 BARS)
========================================================================================
Threshold      Trades   Gross PnL    Friction    Net PnL     Net PF    Net Win%   Net Exp
----------------------------------------------------------------------------------------
0.50              244    -$75.39     $141.80   -$217.19      0.829      48.0%   -$0.890/t
0.55              229    +$25.63     $138.59   -$112.96      0.903      47.2%   -$0.493/t
0.60              208    +$72.23     $125.77    -$53.54      0.948      47.1%   -$0.257/t
0.65              176   +$145.08     $107.49    +$37.58      1.046      48.3%   +$0.214/t
========================================================================================
```

### Critical Findings on Sensitivity
1. **Horizon Oscillation (Cliff-Edge Risk):**
   - As horizon shifts from $H=72$ ($+\$97.55$) to $H=84$ ($-\$11.81$) to $H=96$ ($-\$53.54$) to $H=108$ ($-\$93.02$) and then back up to $H=120$ ($+\$131.95$), performance swings wildly from positive to negative.
   - This jagged, non-monotonic response curve indicates that performance is driven by **timing noise around specific candle closes**, rather than a broad, resilient economic regime.
2. **Threshold Monotonicity:**
   - As probability threshold increases from $0.50$ to $0.65$, net PnL improves smoothly from $-\$217.19$ to $+\$37.58/\text{oz}$. Selective trading successfully concentrates on higher-confidence signals.

---

## 7. Section 6: Parameter-Selection Bias Assessment

A vital mandate of Phase 14 was tracing the exact lineage of Candidate 5:

1. **How Candidate 5 was Discovered:**
   - In Phase 12, session decomposition of Candidate D showed that the **London/NY Overlap generated +$343.66/oz in gross profits**, while Asian trading lost $-\$166.66/oz$.
   - In Phase 13, Candidate 5 was created specifically to isolate this London/NY Overlap window.
2. **Selection Bias Implication:**
   - Candidate 5 was **not** an a priori theoretical hypothesis formulated before observing the data. It was constructed post-hoc based on empirical anomalies discovered in Phase 12 on the **exact same 2021–2024 training dataset**.
   - Testing a strategy on the same historical sample that suggested its parameters inevitably inflates apparent performance.
3. **Status:**
   - Candidate 5 is strictly an **exploratory research candidate**, not an independently confirmed strategy.

---

## 8. Section 7: Economic Decision Gate Evaluation

We evaluated Candidate 5 against the pre-registered Decision Gate criteria:

```
========================================================================================
DECISION GATE EVALUATION (CANDIDATE 5)
========================================================================================
Criterion                               Requirement            Actual Result   Status
----------------------------------------------------------------------------------------
1. Net Expectancy                       > $0.00/trade          -$0.139/trade   FAIL
2. Net Profit Factor                    > 1.000                0.974           FAIL
3. Chronological Consistency            Positive in all folds  1 / 3 positive  FAIL
4. Spread-Stress Robustness             Net PnL > $0.00        -$207.33        FAIL
5. Trade Sample Size                    >= 100 trades          531 trades      PASS
----------------------------------------------------------------------------------------
DECISION GATE RECOMMENDATION:           REJECT PROMOTION
========================================================================================
```

### Justification for Rejection
- Although Candidate 5 lost 94.6% less money than the incumbent and achieved positive net PnL in 2024 and on Long trades, its overall net expectancy is negative ($-\$0.139/\text{trade}$), its Net Profit Factor is below 1 ($0.974$), and it failed in Folds 1 and 2.
- Promoting an unprofitable strategy violates the foundational mandate of this quantitative project.

---

## 9. Final Recommendations & Future Research Directives

1. **Investigate the Winter Overlap Mechanism:**
   The massive $+ \$278.47/\text{oz}$ net profit during winter months (13:00–16:30 UTC) deserves focused exploratory research. Why does gold exhibit strong follow-through in winter and mean-reverting chop in summer? Is this driven by US economic data release schedules (8:30 AM EST vs. 8:30 AM EDT)?
2. **Explore Asymmetric Volatility Trailing Stops:**
   Candidate 5 used a rigid 96-bar fixed-time exit. Incorporating trailing stop exits (e.g., $2.0\times \text{ATR}$ target, $1.0\times \text{ATR}$ stop) during the London/NY Overlap could eliminate the adverse drift observed at the end of the 8-hour window.
3. **Preserve Protected Partitions:**
   **Under no circumstances should the 2025 Validation partition or frozen 2026 Test partition be unsealed.** All future research must remain strictly confined to the 2021–2024 training partition.

---

## 10. Final Verification Checklist & Verdict

- [x] Exact independent reproduction verified across all 531 raw trades.
- [x] Zero overlapping positions or duplicate fills verified.
- [x] Session timing and daylight-saving mechanics audited across BST, GMT, EDT, and EST.
- [x] Seasonal (winter vs summer), fold-level, and yearly stability decomposed.
- [x] Moving block bootstrap confidence intervals computed accounting for serial correlation.
- [x] Horizon and threshold parameter sensitivity mapped.
- [x] Selection bias and multiple testing lineage documented.
- [x] Economic Decision Gate evaluated and documented.
- [x] Full test suite executed (155 tests passing in 2.92s).

```
========================================================================================
FINAL VERDICT:
PROMISING BUT STATISTICALLY INCONCLUSIVE
DECISION GATE RECOMMENDATION: REJECT PROMOTION
========================================================================================
```
