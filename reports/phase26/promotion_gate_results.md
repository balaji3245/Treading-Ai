# PHASE 26: PROMOTION GATE EVALUATION & SCORECARD

**Hypothesis ID:** `HYP-24-NY-REVERSAL-EXHAUSTION`  
**Phase:** 26 — Locked Historical Evaluation  
**Authoritative Protocol:** `reports/phase24/frozen_evaluation_protocol.md`  
**Evaluation Scope:** 2023-01-01 to 2024-12-31 UTC Partition  
**Evaluation Timestamp:** 2026-10-30T04:12:00 UTC  

---

## 1. Formal Promotion Gate Scorecard

Every pre-registered promotion gate codified in Phase 24 and evaluated in Phase 25 was applied to the 2023–2024 historical evaluation partition without modification or relaxation:

| Gate # | Promotion Gate Description | Pre-Registered Threshold | Phase 25 Dev Result (2021–2022) | Phase 26 Eval Result (2023–2024) | Gate Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Gate 1** | **Net Expectancy per Trade** | $\ge +\$0.50 / \text{oz}$ | +$1.442 / \text{oz}$ | **-$2.323 / \text{oz}$** | **FAIL** |
| **Gate 2** | **Net Profit Factor** | $\ge 1.25$ | 1.586 | **0.551** | **FAIL** |
| **Gate 3** | **Directional Win Rate** | $\ge 52.5\%$ | 58.06% | **42.86%** | **FAIL** |
| **Gate 4** | **Friction Stress Tolerance** | Net PnL $> \$0.00$ at 1.5× costs | +$163.331 / \text{oz}$ | **-$188.528 / \text{oz}$** | **FAIL** |
| **Gate 5** | **Directional Symmetry** | Long PF $\ge 1.10$ AND Short PF $\ge 1.10$ | Long 1.629 / Short 1.554 | **Long 0.367 / Short 0.824** | **FAIL** |
| **Gate 6** | **Statistical Significance** | Bootstrap 95% CI Lower Bound $> \$0.00$ | +$0.273 / \text{oz}$ | **-$4.156 / \text{oz}$** | **FAIL** |
| **Gate 7** | **Maximum Drawdown** | $\le \$45.00 / \text{oz}$ | $36.301 / \text{oz}$ | **$178.903 / \text{oz}$** | **FAIL** |

**Total Gates Passed:** **0 / 7 (100% Failure Rate)**  
**Overall Evaluation Outcome:** **REJECTED**

---

## 2. Gate-by-Gate Detailed Analysis

### Gate 1: Net Expectancy per Trade
- **Requirement:** $\ge +\$0.50/\text{oz}$ after 1.0× baseline friction ($0.25/oz).
- **Observed:** **-$2.323/\text{oz}$**.
- **Analysis:** Average trade lost -$2.32/oz. Across 77 trades, this resulted in an aggregate loss of -$178.903/oz, failing the gate by $2.823/oz.

### Gate 2: Net Profit Factor
- **Requirement:** $\ge 1.25$.
- **Observed:** **0.551**.
- **Analysis:** Gross winning PnL ($108.64/oz) was overshadowed by gross losing PnL ($287.54/oz). A profit factor of 0.551 indicates that for every $1 lost, the strategy recovered only 55 cents.

### Gate 3: Directional Win Rate
- **Requirement:** $\ge 52.5\%$.
- **Observed:** **42.86%** (33 wins, 44 losses).
- **Analysis:** Dropped by 15.20 percentage points from development (58.06% $\rightarrow$ 42.86%). The strategy failed to maintain a basic directional edge.

### Gate 4: Friction Stress Tolerance (1.5× Cost)
- **Requirement:** Positive Net PnL under $0.375/oz friction.
- **Observed:** **-$188.528/\text{oz}$** (PF = 0.533).
- **Analysis:** The strategy failed even before costs (gross PnL = -$159.653/oz). Adding elevated friction merely compounded existing losses.

### Gate 5: Directional Symmetry
- **Requirement:** Both Long and Short sub-cohorts must achieve Net Profit Factor $\ge 1.10$.
- **Observed:** Long PF = **0.367**; Short PF = **0.824**.
- **Analysis:** Both wings failed decisively. Long trades (fading downside morning drops) suffered a complete collapse (win rate 32.43%, PF 0.367), losing -$150.654/oz. Short trades (fading upside rallies) also lost money (-$28.248/oz, PF 0.824).

### Gate 6: Statistical Significance (Bootstrap CI Lower Bound)
- **Requirement:** 95% moving-block bootstrap confidence interval lower bound for mean net expectancy must strictly exceed $0.00/oz.
- **Observed:** 95% CI = **[-$4.156 / \text{oz}, +$0.149 / \text{oz}]**.
- **Analysis:** The lower bound is -$4.156/oz. The null hypothesis of zero edge cannot be rejected in a positive direction; rather, performance is deeply negative.

### Gate 7: Maximum Peak-to-Trough Drawdown
- **Requirement:** Peak-to-trough equity drawdown $\le \$45.00/\text{oz}$.
- **Observed:** **$178.903/\text{oz}$**.
- **Analysis:** Maximum drawdown exceeded the allowable limit by nearly $4\times$. The cumulative equity curve never recovered after initial trades, declining almost monotonically.

---

## 3. Comparative Summary: Development vs. Evaluation

```
               DEVELOPMENT (2021–2022)       EVALUATION (2023–2024)
Metric               Result   Gate                 Result   Gate
------------------------------------------------------------------
Trades Executed        124     —                     77      —
Win Rate             58.06%   PASS                 42.86%   FAIL
Net Expectancy     +$1.442/oz PASS               -$2.323/oz FAIL
Net Profit Factor    1.586    PASS                  0.551   FAIL
Long PF              1.629    PASS                  0.367   FAIL
Short PF             1.554    PASS                  0.824   FAIL
Max Drawdown       $36.301/oz PASS               $178.903/oz FAIL
Bootstrap Lower CI +$0.273/oz PASS               -$4.156/oz FAIL
Net PnL (1.0x)    +$178.831   PASS               -$178.903  FAIL
```

The stark divergence between the development partition and the evaluation partition demonstrates that `HYP-24-NY-REVERSAL-EXHAUSTION` was an in-sample phenomenon tied to the 2021–2022 market regime. It does not generalize out-of-sample.
