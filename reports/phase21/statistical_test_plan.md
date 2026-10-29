# Phase 21: Statistical Test Plan & Pre-Registered Validation Protocol

**Phase:** PHASE 21 — NEW HYPOTHESIS DISCOVERY & RESEARCH DESIGN  
**Date:** October 2026  
**Auditor / Researcher:** Quantitative Researcher & Systematic Trading Specialist  
**Target Hypothesis:** `HYP-21-ASIAN-LONDON-EXPANSION`  
**Status:** PRE-REGISTERED VALIDATION PROTOCOL & TESTING STANDARDS  

---

## 1. Primary Metrics & Economic Promotion Gates

To prevent retroactive metric substitution, all evaluation criteria are pre-registered prior to any model implementation:

### A. Primary Economic Metrics
1.  **Net Profit Factor ($\text{PF}_{\text{net}}$):**
    $$\text{PF}_{\text{net}} = \frac{\sum_{d \in \text{Trades}} \max(0, \text{Net PnL}_d)}{\sum_{d \in \text{Trades}} |\min(0, \text{Net PnL}_d)|}$$
    *Promotion Hurdle:* $\mathbf{\text{PF}_{\text{net}} > 1.25}$ on out-of-sample data after baseline friction.
2.  **Cumulative Net PnL ($\$/\text{oz}$):**
    $$\text{Net PnL}_{\text{total}} = \sum_{d \in \text{Trades}} \text{Net PnL}_d$$
    *Promotion Hurdle:* Strictly positive ($\mathbf{> \$0.00/\text{oz}}$), beating Benchmark E (No-Trade).
3.  **Average Net Trade Expectancy ($\mu_{\text{net}}$):**
    $$\mu_{\text{net}} = \frac{\text{Net PnL}_{\text{total}}}{N_{\text{trades}}}$$
    *Promotion Hurdle:* $\mathbf{\mu_{\text{net}} \ge +\$1.00/\text{oz}}$ per trade.

---

## 2. Benchmark Suite & Opportunity-Cost Comparisons

The candidate strategy will be evaluated directly against the four formal project benchmarks established in Phase 20B:

1.  **Benchmark E (No-Trade Baseline):** Strategy must outperform $\$0.00$ net return.
2.  **Benchmark F1 (Daily Long-Only Strategy):** Evaluates whether the strategy generates genuine long/short alpha beyond unconditional long market beta.
3.  **Benchmark F2 (Continuous Buy-and-Hold):** Opportunity-cost benchmark for physical bullion holding.
4.  **Benchmark G (Prior-Session Momentum):** Evaluates whether the Asian-London compression mechanism adds value beyond simple 1-day trend following.

---

## 3. Transaction Cost & Sensitivity Scenarios

All performance metrics will be calculated across three pre-registered cost tiers:

| Cost Scenario | Broker Bid-Ask Spread | Slippage (Entry + Exit) | Overnight Swap | Round-Turn Friction ($C$) | Minimum Required Net Move |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **1. Baseline Costs ($1.0\times$)** | $\$0.20/\text{oz}$ | $\$0.05/\text{oz}$ | $\$0.00/\text{oz}$ | **$\$0.25/\text{oz}$** | $\$0.25/\text{oz}$ |
| **2. Elevated Costs ($1.5\times$)** | $\$0.30/\text{oz}$ | $\$0.075/\text{oz}$ | $\$0.00/\text{oz}$ | **$\$0.375/\text{oz}$** | $\$0.375/\text{oz}$ |
| **3. Stressed Costs ($2.0\times$)** | $\$0.40/\text{oz}$ | $\$0.10/\text{oz}$ | $\$0.00/\text{oz}$ | **$\$0.50/\text{oz}$** | $\$0.50/\text{oz}$ |

*Pre-Registered Requirement:* The strategy must maintain positive net PnL ($\text{Net PnL} > 0$) across **all three cost scenarios** to be considered robust against liquidity dry-ups.

---

## 4. Hypothesis Testing & Multiple-Testing Adjustments

### A. Test 1: Directional Accuracy vs. 50% Random Walk
*   **Null Hypothesis ($H_{0,1}$):** $\pi_{\text{hit}} \le 0.50$ (breakouts expand directionally with probability no greater than chance).
*   **Alternative Hypothesis ($H_{1,1}$):** $\pi_{\text{hit}} > 0.50$.
*   **Statistical Test:** One-tailed Exact Binomial Test:
    $$\text{p-value} = \sum_{k = k_{\text{obs}}}^{N} \binom{N}{k} (0.50)^k (0.50)^{N-k}$$
*   **Rejection Threshold:** $p < 0.05$.

### B. Test 2: Regime Conditioning Effect (Welch's Two-Sample $t$-Test)
*   **Null Hypothesis ($H_{0,2}$):** $\mu_{\text{compressed}} \le \mu_{\text{uncompressed}}$ (breakouts on compressed Asian days produce returns no higher than breakouts on uncompressed Asian days).
*   **Alternative Hypothesis ($H_{1,2}$):** $\mu_{\text{compressed}} > \mu_{\text{uncompressed}}$.
*   **Statistical Test:** One-tailed Welch's two-sample $t$-test (robust to unequal variances).
*   **Non-Parametric Confirmation:** Mann–Whitney $U$ test.
*   **Rejection Threshold:** $p < 0.05$.

### C. Test 3: Multiple-Testing Control (Holm–Bonferroni)
If the development phase evaluates multiple compression thresholds (e.g. $Q_1$, $Q_{10\%}$, $Q_{15\%}$, $M = 3$ candidate thresholds), the **Holm–Bonferroni step-down correction** is mandatory:
$$\alpha_{(k)} = \frac{\alpha}{M - k + 1}$$
A threshold configuration is promoted only if its $p$-value survives the step-down threshold at nominal $\alpha = 0.05$.

---

## 5. Serial Correlation & Resampling Methodology

### A. Non-Overlapping Horizon Advantage
Unlike Phases 1–16, where rolling M5 horizons produced 99% serial autocorrelation and inflated sample sizes by $96\times$, `HYP-21` evaluates **at most one trade per calendar day**. The observation unit is non-overlapping, preserving degrees of freedom.

### B. Moving Block Bootstrap Protocol
To account for residual volatility clustering across consecutive trading days:
*   **Resampling Unit:** Vector of daily Net PnLs ($N_{\text{trades}}$).
*   **Block Length:** $L = 5$ trading days (1 trading week).
*   **Resample Count:** $B = 2,000$ independent synthetic histories.
*   **Statistical Gate:** The **95% Bootstrap Confidence Interval Lower Bound for Net Profit Factor must be strictly $> 1.00$**:
    $$\text{CI}_{0.025}(\text{PF}_{\text{net}}) > 1.00$$

---

## 6. Sample Size & Statistical Power Rationale

*   **Available Out-of-Sample Period (2023–2024):** 516 institutional trading days.
*   **Expected Compression Frequency:** $Q_1 \implies 25\%$ of days = $\approx 129$ trading days.
*   **Expected Breakout Trigger Rate:** Based on historical London volatility dynamics, $\approx 65\%-75\%$ of compressed Asian sessions produce a confirmed breakout between 07:05 and 09:00 UTC.
*   **Expected Out-of-Sample Trade Count ($N_{\text{oos}}$):** $\mathbf{N \approx 85 \text{ to } 97 \text{ trades}}$.
*   **Statistical Power:** For an independent sample of $N = 90$ trades, a one-tailed $t$-test achieves **$> 80\%$ statistical power ($\beta \le 0.20$) at $\alpha = 0.05$** to detect an economic edge of effect size Cohen's $d = 0.30$ (equivalent to an average net trade return of $\approx +\$1.20/\text{oz}$ with daily volatility $\approx \$4.00/\text{oz}$).
*   **Conclusion:** The sample size is statistically viable and does not rely on rare-event illusions.

---

## 7. Risk Constraints & Failure Criteria

A candidate model will be immediately terminated if:
1.  **Maximum Drawdown:** Peak-to-trough drawdown exceeds **$\$1,000/\text{oz}$** ($\ge 10.0\%$ on a hypothetical $\$10,000$ single-ounce account).
2.  **Outlier Dominance:** The single most profitable trade contributes **$\ge 25.0\%$** of total cumulative net PnL.
3.  **Long/Short Asymmetry:** More than $80\%$ of cumulative net profits originate from one directional side during a directional macro trending year.
