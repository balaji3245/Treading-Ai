# Phase 20B: Statistical Audit Record & Hypothesis Testing

**Document:** Statistical Audit Record & Hypothesis Testing  
**Phase:** PHASE 20B — FORMAL CORRECTIONS & RESEARCH CLOSURE  
**Auditor / Author:** Quantitative Researcher & Independent Validation Auditor  

---

## 1. Primary Research Hypothesis & Tested Models

The pre-registered research hypothesis $\mathcal{H}_1$ posited that daily changes in macroeconomic fundamentals possess predictive value for next-session institutional XAUUSD returns:
$$\mathcal{H}_1: \mathbb{E}[\text{Return}_{t+1} \mid \Delta \text{Macro}_t] \neq 0 \quad \text{net of realistic execution frictions.}$$

### Candidate Model Hypotheses
1.  **Model A (10-Year TIPS Real Yield):** $H_{1,A}: \beta_{\text{yield}} < 0$. Higher real yields increase physical gold holding opportunity costs, predicting negative next-session returns.
2.  **Model B (Broad Trade-Weighted US Dollar):** $H_{1,B}: \beta_{\text{dollar}} < 0$. Dollar appreciation reduces international purchasing power, predicting negative next-session returns.
3.  **Model C (Bivariate Macro Composite):** $H_{1,C}: s_t = -0.5 \tilde{\Delta y}_t - 0.5 \tilde{\Delta d}_t > 0 \implies \text{Return}_{t+1} > 0$.
4.  **Model D (Trivariate Macro Composite):** $H_{1,D}: s_t = -0.4 \tilde{\Delta y}_t - 0.4 \tilde{\Delta d}_t + 0.2 \tilde{\Delta b}_t > 0 \implies \text{Return}_{t+1} > 0$.

---

## 2. Linear & Non-Parametric Feature Association Record

The table below presents out-of-sample ($N = 516$ sessions, 2023–2024) predictive metrics between model scores and realized arithmetic session returns:

| Candidate Model | Pearson Correlation ($r$) | Pearson $p$-value | Spearman Rank Correlation ($\rho$) | Spearman $p$-value | OLS Slope ($\beta$) | OLS $R^2$ | OLS $p$-value |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Model A (Yield Only)** | +0.0076 | 0.8624 | +0.0152 | 0.7299 | +0.000072 | 0.000058 | 0.8624 |
| **Model B (Dollar Only)** | +0.0244 | 0.5794 | +0.0385 | 0.3824 | +0.000216 | 0.000597 | 0.5794 |
| **Model C (Bivariate)** | +0.0178 | 0.6865 | +0.0312 | 0.4795 | +0.000201 | 0.000317 | 0.6865 |
| **Model D (Trivariate)** | +0.0186 | 0.6724 | +0.0348 | 0.4307 | +0.000230 | 0.000346 | 0.6724 |

### Findings
*   All linear correlations are statistically indistinguishable from zero ($|r| \le 0.0244$, $p \ge 0.5794$).
*   All regression $R^2$ values are zero ($R^2 \le 0.0006$).
*   Non-parametric Spearman rank correlations confirm the absence of monotonic relationships ($\rho \le 0.0385$, $p \ge 0.3824$).

---

## 3. Directional Accuracy & Binomial Tests

Directional accuracy is evaluated strictly on active sessions:
$$\text{Directional Accuracy} = \frac{\sum_{t \in \text{Active}} \mathbb{I}\{\text{sign}(\text{Position}_t) == \text{sign}(\text{Realized PnL}_t)\}}{N_{\text{Active}}}$$

| Candidate Model | Total Sessions | Inactive Sessions | Active Sessions | Correct Active | Directional Accuracy | Null Hypothesis ($H_0$) | Binomial Test $p$-value |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Model A (Yield Only)** | 516 | 152 | 364 | 181 | **49.73%** | $p_{\text{hit}} \le 0.50$ | 0.5833 |
| **Model B (Dollar Only)** | 516 | 120 | 396 | 201 | **50.76%** | $p_{\text{hit}} \le 0.50$ | 0.4005 |
| **Model C (Bivariate)** | 516 | 0 | 516 | 263 | **50.97%** | $p_{\text{hit}} \le 0.50$ | 0.3444 |
| **Model D (Trivariate)** | 516 | 0 | 516 | 265 | **51.36%** | $p_{\text{hit}} \le 0.50$ | 0.2801 |

### Findings
*   Zero sessions in the out-of-sample period produced $\text{target\_pnl} == 0$.
*   No candidate model beats a 50.0% random coin toss at the $\alpha = 0.05$ significance level (all binomial $p \ge 0.28$).

---

## 4. Multiple-Testing Adjustment (Holm–Bonferroni)

To control the Family-Wise Error Rate (FWER) across the $M = 4$ primary candidate models, the Holm–Bonferroni step-down procedure was applied at nominal $\alpha = 0.05$:

$$\text{Sort } p_{(1)} \le p_{(2)} \le p_{(3)} \le p_{(4)}$$
$$\text{Reject if } p_{(k)} < \frac{\alpha}{M - k + 1}$$

| Step ($k$) | Candidate Model | Metric Tested | Raw $p$-value | Adjusted Threshold $\alpha_{(k)}$ | Rejection Outcome |
| :---: | :--- | :--- | :---: | :---: | :---: |
| **1** | Model B (Dollar Only) | Pearson $r$ ($+0.0244$) | **0.5794** | $\alpha / 4 = 0.0125$ | **FAIL TO REJECT** |
| **2** | Model D (Trivariate) | Pearson $r$ ($+0.0186$) | **0.6724** | $\alpha / 3 = 0.0167$ | **FAIL TO REJECT** |
| **3** | Model C (Bivariate) | Pearson $r$ ($+0.0178$) | **0.6865** | $\alpha / 2 = 0.0250$ | **FAIL TO REJECT** |
| **4** | Model A (Yield Only) | Pearson $r$ ($+0.0076$) | **0.8624** | $\alpha / 1 = 0.0500$ | **FAIL TO REJECT** |

**Conclusion:** The step-down algorithm terminates at Step 1 ($0.5794 > 0.0125$). No model survives multiple-testing correction.

---

## 5. Moving Block Bootstrap Confidence Intervals

### Implementation Protocol
*   **Resampling Unit:** Vector of daily session Net PnL ($N = 516$).
*   **Block Length:** $L = 5$ sessions (1 institutional trading week) to preserve short-range autocorrelation and volatility clustering.
*   **Resample Count:** $B = 2,000$ independent block-resampled synthetic histories.
*   **Undefined Denominators:** For Net Profit Factor, resamples with zero losses return `NaN` and are excluded from percentile calculation. In our execution, all 2,000 resamples contained non-zero losses ($0$ dropped).

### Reconciled Bootstrap 95% Confidence Intervals

| Candidate Model | Metric | Point Estimate | Reconciled 95% CI Lower | Reconciled 95% CI Upper | Valid Resamples |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Model A (Yield Only)** | Net PnL ($/\text{oz}$) | -$294.54 | -$983.28 | +$374.49 | 2,000 |
| | Net Profit Factor | 0.895 | 0.690 | 1.150 | 2,000 |
| **Model B (Dollar Only)** | Net PnL ($/\text{oz}$) | -$75.42 | -$875.80 | +$675.27 | 2,000 |
| | Net Profit Factor | 0.975 | 0.741 | 1.259 | 2,000 |
| **Model C (Bivariate)** | Net PnL ($/\text{oz}$) | -$81.92 | -$1017.00 | +$693.07 | 2,000 |
| | Net Profit Factor | 0.978 | 0.761 | 1.205 | 2,000 |
| **Model D (Trivariate)** | Net PnL ($/\text{oz}$) | -$258.48 | -$1120.17 | +$465.69 | 2,000 |
| | Net Profit Factor | 0.933 | 0.743 | 1.130 | 2,000 |

### Statistical Synthesis
1.  All 95% confidence intervals for Net PnL span deeply negative territory (down to $-\$1,120/\text{oz}$).
2.  The upper bounds of Net Profit Factor barely touch or fall below 1.25.
3.  The point estimates are all below 1.0 (indicating negative net expectancy).
4.  The empirical evidence overwhelmingly supports the null hypothesis of no predictive edge.
