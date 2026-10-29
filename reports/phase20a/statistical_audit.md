# Phase 20A: Statistical Testing & Methodology Audit

**Document:** Statistical Testing & Methodology Audit  
**Target Code:** [run_phase20_macro_test.py:93-131](file:///home/bhoot/project/Treading-Ai/scripts/run_phase20_macro_test.py#L93-L131) & [run_phase20_macro_test.py:378-430](file:///home/bhoot/project/Treading-Ai/scripts/run_phase20_macro_test.py#L378-L430)  
**Protocol:** [preregistered_protocol.md:110-143](file:///home/bhoot/project/Treading-Ai/reports/phase20/preregistered_protocol.md#L110-L143)  
**Auditor:** Quantitative Researcher & Independent Code Auditor  

---

## 1. Hypothesis Alignment Audit

### A. Pre-Registered Primary Hypotheses
The pre-registered primary hypothesis $\mathcal{H}_1$ asserted that daily changes in 10-Year Real Yields (`DFII10`) and the Broad Dollar Index (`DTWEXBGS`) contain predictive information for next-session gold returns net of costs.

Under economic theory:
1.  **Real Yield:** $\beta_{\text{yield}} < 0$ (rising yields increase opportunity cost of gold).
2.  **Dollar Strength:** $\beta_{\text{dollar}} < 0$ (stronger USD reduces international dollar purchasing power).
3.  **Inflation Expectation:** $\beta_{\text{breakeven}} > 0$ (rising inflation increases hedging demand).

### B. What Did the Statistical Tests Actually Test?
1.  **Pearson Correlation ($r$) and Two-Tailed $p$-value:**
    *   Tests the null hypothesis:
        $$H_0: \rho(\text{Score}, \text{Return}) = 0 \quad \text{vs.} \quad H_1: \rho \neq 0$$
    *   *Audit Verification:* Pearson correlation tests strictly for **linear association** between continuous normalized macro scores and unadjusted returns. It does **not** test trading strategy profitability, execution viability, or net positive expectancy.
2.  **Binomial Hit Rate Test:**
    *   Tests whether the directional accuracy differs from a random coin toss:
        $$H_0: p_{\text{correct}} \le 0.50 \quad \text{vs.} \quad H_1: p_{\text{correct}} > 0.50$$
    *   All four models yielded $p > 0.28$, failing to reject the 50% random walk null.
3.  **Separation of Statistical and Economic Gates:**
    *   Phase 20 appropriately separated statistical significance (Holm-Bonferroni on Pearson $r$) from economic feasibility ($\text{Net Profit Factor} > 1.25$ and $\text{Net PnL} > 0$).
    *   Correlation significance was **never** presented as sufficient evidence for trading profitability. Both criteria were enforced simultaneously as conjunctive gates.

---

## 2. Multiple-Testing Correction Audit (Holm–Bonferroni)

### A. Hypothesis Family & Test Count
*   **Family Scope:** The primary candidate model family was defined as:
    $$\mathcal{F} = \{\text{Model A (Yield Only)}, \text{Model B (Dollar Only)}, \text{Model C (Bivariate)}, \text{Model D (Trivariate)}\}$$
*   **Total Tests ($M$):** $M = 4$.
*   **Family Integrity:** Benchmarks E, F, and G were appropriately excluded from the hypothesis family, as benchmarks serve as control baselines rather than candidate strategy hypotheses.

### B. Reproduction of Holm–Bonferroni Step-Down Procedure
Nominal family-wise error rate was set at $\alpha = 0.05$. Step-down thresholds:
$$\alpha_{(k)} = \frac{\alpha}{M - k + 1}$$

| Rank ($k$) | Candidate Model | Metric Tested | Raw $p$-value | Step-Down Threshold $\alpha_{(k)}$ | Rejection Decision | Status |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: |
| **1** | Model B (Dollar Only) | Pearson $r = +0.0244$ | **0.5794** | $\alpha / 4 = 0.0125$ | Fail to Reject $H_0$ | **CONFIRMED** |
| **2** | Model D (Trivariate) | Pearson $r = +0.0186$ | **0.6724** | $\alpha / 3 = 0.0167$ | Fail to Reject $H_0$ | **CONFIRMED** |
| **3** | Model C (Bivariate) | Pearson $r = +0.0178$ | **0.6865** | $\alpha / 2 = 0.0250$ | Fail to Reject $H_0$ | **CONFIRMED** |
| **4** | Model A (Yield Only) | Pearson $r = +0.0076$ | **0.8624** | $\alpha / 1 = 0.0500$ | Fail to Reject $H_0$ | **CONFIRMED** |

Because Rank 1 ($p = 0.5794$) fails to meet $\alpha_{(1)} = 0.0125$, the step-down procedure terminates immediately. No candidate model demonstrates statistically detectable predictive signal.

---

## 3. Moving Block Bootstrap Audit

### A. Algorithm & Resampling Unit Inspection
In [run_phase20_macro_test.py:93-131](file:///home/bhoot/project/Treading-Ai/scripts/run_phase20_macro_test.py#L93-L131):
*   **Resampling Unit:** The resampled array is the **vector of daily session Net PnL** across the out-of-sample period ($N = 516$ time steps). Resampling is performed on daily time-series blocks, **not on isolated trades**.
*   **Preservation of Temporal Dependence:** Because consecutive trading sessions exhibit volatility clustering and potential residual autocorrelation, block resampling is mandatory. A block length of $L = 5$ sessions corresponds to **one institutional trading week** (Sunday evening to Friday close). This preserves intra-week dependencies.
*   **Number of Blocks:** $k = \lceil N / L \rceil = \lceil 516 / 5 \rceil = 104$ blocks. Each synthetic resample has length $\ge 516$ and is sliced to exactly $N = 516$.

### B. Treatment of Undefined Net Profit Factors
In [run_phase20_macro_test.py:385-388](file:///home/bhoot/project/Treading-Ai/scripts/run_phase20_macro_test.py#L385-L388):
```python
def net_pf_stat(arr):
    wins = np.sum(arr[arr > 0])
    losses = -np.sum(arr[arr < 0])
    return float(wins / losses) if losses > 0 else float("nan")
```
And in [run_phase20_macro_test.py:122-123](file:///home/bhoot/project/Treading-Ai/scripts/run_phase20_macro_test.py#L122-L123):
```python
if not np.isnan(val) and not np.isinf(val):
    boot_stats.append(val)
```
*Audit Verification:* If a bootstrap resample generates zero losing sessions, `net_pf_stat` returns `NaN`. The bootstrap accumulator explicitly filters out `NaN` and `Inf` before taking empirical percentiles ($2.5\%$ and $97.5\%$). In our audit reproduction, all $2,000$ resamples for Models A–D had non-zero losses, resulting in exactly $2,000$ valid bootstrap statistics ($0\%$ dropped).

### C. Independent Reproduction of 95% Bootstrap Confidence Intervals

| Candidate Model | Metric | Point Estimate | Phase 20 Reported 95% CI | Phase 20A Reconstructed 95% CI | Exact Match? |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Model A (Yield Only)** | Net PnL ($/\text{oz}$) | -$297.18 | [-$985.92, +$371.85] | [-$985.92, +$371.85] | **YES (Identical)** |
| | Net Profit Factor | 0.894 | [0.689, 1.148] | [0.689, 1.148] | **YES (Identical)** |
| **Model B (Dollar Only)** | Net PnL ($/\text{oz}$) | -$79.02 | [-$879.40, +$671.67] | [-$879.40, +$671.67] | **YES (Identical)** |
| | Net Profit Factor | 0.973 | [0.739, 1.257] | [0.739, 1.257] | **YES (Identical)** |
| **Model C (Bivariate)** | Net PnL ($/\text{oz}$) | -$82.16 | [-$1017.24, +$692.83] | [-$1017.24, +$692.83] | **YES (Identical)** |
| | Net Profit Factor | 0.978 | [0.761, 1.205] | [0.761, 1.205] | **YES (Identical)** |
| **Model D (Trivariate)** | Net PnL ($/\text{oz}$) | -$258.72 | [-$1120.41, +$465.45] | [-$1120.41, +$465.45] | **YES (Identical)** |
| | Net Profit Factor | 0.933 | [0.743, 1.130] | [0.743, 1.130] | **YES (Identical)** |

---

## 4. Statistical Conclusion

1.  **Rigorous Implementation:** The moving block bootstrap and Holm–Bonferroni algorithms were correctly implemented and fully reproduced.
2.  **No False Discoveries:** All lower bounds for Net PnL are deeply negative (down to $-\$1,120/\text{oz}$), and all 95% confidence intervals for Net Profit Factor span below 1.0 (indicating that true expectancy is indistinguishable from, or worse than, breakeven).
3.  **Hypothesis Rejection Confirmed:** The statistical audit confirms that Phase 20's primary macroeconomic hypothesis $\mathcal{H}_1$ must be firmly rejected.
