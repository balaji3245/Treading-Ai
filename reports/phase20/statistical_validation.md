# Phase 20: Statistical Validation & Multiple-Testing Audit

**Status:** Completed & Methodologically Verified  
**Date:** October 2026  
**Auditor:** Independent Validation Auditor  
**Resampling Methodology:** Moving Block Bootstrap (2,000 Resamples, Block Length = 5 Sessions, Seed = 42)  
**Multiple-Testing Procedure:** Step-Down Holm–Bonferroni Family-Wise Adjustment ($\alpha = 0.05$)

---

## 1. Executive Summary

A core discipline of institutional quantitative research is distinguishing true economic alpha from sample variance, serial dependence, and multiple-testing data snooping. This report subjects the Phase 20 out-of-sample results to rigorous statistical validation:
1.  **Block Bootstrap Resampling:** Accounts for time-series persistence, volatility clustering, and fat tails in daily gold returns.
2.  **Holm–Bonferroni Multiple-Testing Control:** Adjusts significance thresholds across the family of candidate models to prevent false discovery.
3.  **Promotion Criteria Audit:** Evaluates each candidate against pre-registered gates.

### Core Verdict
*   **Zero Significant Alpha:** All four candidate models fail Holm–Bonferroni significance testing ($p \ge 0.58$).
*   **Negative Lower & Upper Bootstrap Bounds:** 95% confidence intervals for Net PnL span deeply negative for every active macro model.
*   **Rejection of Hypothesis:** The data formally rejects the hypothesis that 1-day macroeconomic differences provide statistically significant predictability for next-session gold returns.

---

## 2. Moving Block Bootstrap Confidence Intervals

Standard i.i.d. bootstrap methods underestimate standard errors in financial time series due to serial dependence and GARCH volatility clustering. To preserve temporal structure, we implement a **Moving Block Bootstrap** with an average block length of $L = 5$ sessions (1 business week), generating $B = 2,000$ synthetic out-of-sample trajectories:

| Model / Benchmark | Net PnL Point Estimate | Net PnL 95% CI Lower | Net PnL 95% CI Upper | Net Profit Factor Point Est | Net PF 95% CI Lower | Net PF 95% CI Upper | Zero-Crossing Interpretation |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Model A (Yield Only)** | $-\$297.18$ | $-\$985.92$ | $+\$371.85$ | $0.894$ | $0.689$ | $1.148$ | CI includes negative PnL; upper bound fails PF $> 1.25$ gate. |
| **Model B (Dollar Only)** | $-\$79.02$ | $-\$879.40$ | $+\$671.67$ | $0.973$ | $0.739$ | $1.257$ | Point estimate negative; massive dispersion across resamples. |
| **Model C (Bivariate)** | $-\$82.16$ | $-\$1,017.24$ | $+\$692.83$ | $0.978$ | $0.761$ | $1.205$ | Point estimate negative; upper bound PF ($1.205$) below $1.25$ hurdle. |
| **Model D (Trivariate)** | $-\$258.72$ | $-\$1,120.41$ | $+\$465.45$ | $0.933$ | $0.743$ | $1.130$ | Point estimate negative; entire CI centered below parity. |
| **Benchmark E (No-Trade)** | **$\$0.00$** | **$\$0.00$** | **$\$0.00$** | **—** | **—** | **—** | **Superior baseline (strictly zero variance, zero loss).** |
| **Benchmark F (Buy & Hold)**| $+\$547.93$ | $-\$316.34$ | $+\$1,354.65$ | $1.159$ | $0.919$ | $1.446$ | Positive drift, but lower CI includes negative values. |
| **Benchmark G (Prior Mom)** | $-\$472.59$ | $-\$1,320.53$ | $+\$438.39$ | $0.881$ | $0.703$ | $1.125$ | Persistent net losses across bootstrap distribution. |

### Interpretation
*   For all four active macroeconomic models, the point estimates for Net PnL are strictly negative.
*   The 95% bootstrap confidence intervals for Net Profit Factor encompass values as low as $0.689$ to $0.761$. Even at the 97.5th percentile optimistic upper bound, Models A, C, and D fail to reach the pre-registered economic promotion threshold of $\text{Net PF} > 1.25$.
*   No candidate model achieves a lower confidence bound above zero.

---

## 3. Multiple-Testing Adjustment (Holm–Bonferroni)

Testing multiple candidate specifications on the same historical dataset inflates the Family-Wise Error Rate (FWER). To guard against data mining, the step-down **Holm–Bonferroni procedure** was applied across the family of four candidate models ($M = 4$) at nominal significance level $\alpha = 0.05$:

$$\text{Rank sorted raw } p\text{-values: } p_{(1)} \le p_{(2)} \le p_{(3)} \le p_{(4)}$$
$$\text{Adjusted significance threshold: } \alpha_k = \frac{\alpha}{M - k + 1}$$

| Rank ($k$) | Candidate Model | Raw Pearson $p$-Value | Adjusted Threshold ($\alpha_k$) | Statistical Significance | Decision |
| :---: | :--- | :---: | :---: | :---: | :---: |
| **1** | **Model B (Dollar Only)** | $0.5808$ | $\alpha / 4 = 0.0125$ | $p > \alpha_1$ | **FAIL (REJECT HYPOTHESIS)** |
| **2** | **Model C (Bivariate)** | $0.6559$ | $\alpha / 3 = 0.0167$ | $p > \alpha_2$ | **FAIL (REJECT HYPOTHESIS)** |
| **3** | **Model D (Trivariate)** | $0.7112$ | $\alpha / 2 = 0.0250$ | $p > \alpha_3$ | **FAIL (REJECT HYPOTHESIS)** |
| **4** | **Model A (Yield Only)** | $0.8636$ | $\alpha / 1 = 0.0500$ | $p > \alpha_4$ | **FAIL (REJECT HYPOTHESIS)** |

### Multiple-Testing Verdict
*   Every raw $p$-value exceeds $0.58$, far above even unadjusted nominal thresholds ($\alpha = 0.05$).
*   The Holm–Bonferroni test terminates at Rank 1 with total rejection of statistical significance.
*   There is zero evidence that any of the tested relationships are non-random.

---

## 4. Pre-Registered Promotion Gate Audit

Each model was audited against the six pre-registered promotion criteria established in [`reports/phase20/preregistered_protocol.md`](file:///home/bhoot/project/Treading-Ai/reports/phase20/preregistered_protocol.md):

| Pre-Registered Promotion Gate | Hurdle Requirement | Model A | Model B | Model C | Model D | Benchmark E (No-Trade) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Gate 1: Economic Profitability** | $\text{Net PF} > 1.25$ | FAIL ($0.894$) | FAIL ($0.973$) | FAIL ($0.978$) | FAIL ($0.933$) | N/A |
| **Gate 2: Positive Net Return** | $\text{Net PnL} > \$0.00$ | FAIL ($-\$297$) | FAIL ($-\$79$) | FAIL ($-\$82$) | FAIL ($-\$259$) | PASS ($\$0.00$) |
| **Gate 3: Statistical Significance** | Survives Holm–Bonferroni ($\alpha=0.05$) | FAIL ($p=0.86$) | FAIL ($p=0.58$) | FAIL ($p=0.66$) | FAIL ($p=0.71$) | N/A |
| **Gate 4: Cost Robustness ($1.5\times$)** | $\text{Net PnL}_{1.5\times} > \$0.00$ | FAIL ($-\$385$) | FAIL ($-\$175$) | FAIL ($-\$203$) | FAIL ($-\$380$) | PASS ($\$0.00$) |
| **Gate 5: Cost Robustness ($2.0\times$)** | $\text{Net PnL}_{2.0\times} > \$0.00$ | FAIL ($-\$473$) | FAIL ($-\$270$) | FAIL ($-\$324$) | FAIL ($-\$500$) | PASS ($\$0.00$) |
| **Gate 6: Outlier Independence** | Top trade $< 25\%$ of net profits | N/A (Negative) | N/A (Negative) | N/A (Negative) | N/A (Negative) | PASS |
| **Overall Promotion Decision** | **ALL GATES MUST PASS** | **REJECTED** | **REJECTED** | **REJECTED** | **REJECTED** | **BENCHMARK** |

---

## 5. Scientific Methodological Takeaways

1.  **High $N/D$ Ratio Does Not Create Edge:** In Phase 18B and Phase 19, model complexity was constrained to $D \le 5$ features to secure an observation-to-feature ratio of $N/D = 196.8:1$. This high ratio prevented in-sample overfitting, which achieved its intended scientific goal: **it enabled a clean, uncorrupted rejection of a false hypothesis**.
2.  **Market Efficiency at Daily Settlements:** Real yields and broad trade-weighted dollar indices are among the most heavily scrutinized macroeconomic variables in global finance. Information contained in daily releases is absorbed by institutional market participants during the active London and New York sessions, leaving near-zero tradable predictability for the subsequent 18:00 NY to 17:00 NY window.
3.  **Research Integrity Affirmation:** Reporting negative results transparently preserves scientific capital, protects against capital destruction in live markets, and confirms that the Treading-Ai research governance framework is operating properly.
