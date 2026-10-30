# STATISTICAL INFERENCE & UNCERTAINTY REPORT: PHASE 22

**Phase:** 22 — Controlled Development  
**Hypothesis ID:** `HYP-21-ASIAN-LONDON-EXPANSION`  
**Dataset:** 2021–2022 Development Partition  
**Execution Timestamp:** 2026-10-30T02:57:33 UTC  
**Status:** Methodological Statistical Evaluation  

---

## 1. Statistical Methodology & Framing

In accordance with quantitative research governance, statistical claims of profitability cannot be asserted based solely on point estimates or arbitrary backtest metrics. This report evaluates the development performance of `HYP-21-ASIAN-LONDON-EXPANSION` under rigorous statistical inference:
1. **Primary Uncertainty Measure:** Mean Net Expectancy per trade, evaluated via stationary moving-block bootstrap (block length $b = 5$) to account for potential serial dependence and volatility clustering.
2. **Secondary Uncertainty Measure:** Net Profit Factor (PF), with explicit handling of edge cases (zero-loss resamples).
3. **Directional Accuracy Null Hypothesis:** Two-sided Exact Binomial Test against the random-walk null ($p_0 = 0.50$).
4. **Multiple Testing & Multiplicity Awareness:** Recognition that the compression threshold was calibrated during exploratory research in Phase 21.

---

## 2. Primary Metric: Net Expectancy per Trade

The primary measure of economic edge is the mean net dollar return per executed trade ($N = 101$ trades under 1.0× baseline costs of $0.25/oz):

$$\mu = \frac{1}{N} \sum_{i=1}^{N} \text{Net PnL}_i$$

### Moving-Block Bootstrap Methodology:
- **Resamples ($B$):** 2,000 resamples.
- **Block Length ($b$):** 5 trades (preserves short-term autocorrelation and volatility clustering).
- **Confidence Level:** 95% two-sided ($\alpha = 0.05$).

### Primary Metric Results:
- **Point Estimate ($\hat{\mu}$):** **+$0.420/oz**
- **Bootstrap Mean:** +$0.426/oz
- **Bootstrap Standard Error ($SE$):** $0.463/oz
- **95% Confidence Interval:** **[-$0.466/oz, +$1.352/oz]**

> [!IMPORTANT]
> **STATISTICAL INTERPRETATION OF PRIMARY METRIC:**  
> The 95% bootstrap confidence interval for net expectancy spans from **-$0.466/oz to +$1.352/oz**. Because the interval includes zero (and negative values), the hypothesis that true net expectancy is zero ($\mathcal{H}_0: \mu = 0$) **CANNOT be rejected at the 5% significance level** even on the development partition. The sample size ($N = 101$) and trade return variance ($\sigma = $9.32/oz) yield insufficient power to statistically distinguish the observed +$0.42/oz point estimate from zero.

---

## 3. Secondary Metric: Net Profit Factor

Net Profit Factor is defined as the ratio of gross gains to gross losses after round-turn transaction friction:

$$\text{Net PF} = \frac{\sum_{i: \text{Net PnL}_i > 0} \text{Net PnL}_i}{\sum_{i: \text{Net PnL}_i < 0} |\text{Net PnL}_i|}$$

### Undefined Profit Factor & Zero-Loss Resample Policy:
If a bootstrap resample contains zero losing trades, the denominator equals zero, rendering the Profit Factor undefined ($\infty$). 
- **Registered Handling Policy:** Any resample yielding zero losses produces `NaN` and is excluded from percentile ranking. The count of valid resamples must be reported.
- **Empirical Occurrence:** Across 2,000 block resamples of length 5 on the 101 executed trades, **0 resamples produced zero losses**. All 2,000 resamples were valid.

### Secondary Metric Results:
- **Point Estimate:** **1.263**
- **Bootstrap Median:** 1.258
- **95% Bootstrap Confidence Interval:** **[0.751, 2.111]**
- **Valid Resamples:** 2,000 / 2,000 (100.0%)

> [!NOTE]
> The 95% confidence interval for Net Profit Factor spans **[0.751, 2.111]**, which contains the neutral/unprofitable threshold of 1.0. This confirms that the observed PF of 1.263 is consistent with sampling variability around a breakeven strategy.

---

## 4. Directional Win Rate & Exact Binomial Test

The strategy generated 55 wins and 46 losses on 101 executed trades:
- **Observed Win Rate:** $\hat{p} = \frac{55}{101} = 54.46\%$
- **Null Hypothesis:** $\mathcal{H}_0: p = 0.50$ (Directional coin-toss null)
- **Alternative Hypothesis:** $\mathcal{H}_1: p \neq 0.50$ (Two-sided test)

### Exact Binomial Test Calculation:
$$P(X \ge 55 \text{ or } X \le 46 \mid N=101, p=0.50) = 2 \times \sum_{k=55}^{101} \binom{101}{k} (0.50)^{101}$$
$$\mathbf{p\text{-value} = 0.2131}$$

### Decision:
At $\alpha = 0.05$, $p = 0.2131 > 0.05$. The observed win rate of 54.46% does **NOT** achieve statistical significance over a 50% random benchmark.

---

## 5. Multiple Testing & Multiplicity Awareness

Quantitative integrity mandates full accounting of the research trajectory:
1. **Calibration Precedent:** In Phase 21, the compression quantile threshold ($Q_1$) was calibrated on this same 2021–2022 dataset. Consequently, positive development performance is partially expected due to in-sample alignment.
2. **Promotion Gate Fallacy:** Passing individual heuristic gates (such as positive gross PnL or win rate > 50%) does NOT constitute statistical significance. Correlated metrics evaluated on the same sample must not be conflated with independent confirmatory evidence.
3. **True Out-of-Sample Test Requirement:** The only valid test of whether `HYP-21-ASIAN-LONDON-EXPANSION` possesses an authentic market anomaly is strict, locked out-of-sample evaluation on the uncalibrated 2023–2024 partition, without parameter modification.

---

## 6. Summary of Statistical Findings

| Metric | Point Estimate | 95% Confidence Interval | Neutral / Null Reference | Statistically Significant at $\alpha = 0.05$? |
| :--- | :--- | :--- | :--- | :--- |
| **Net Expectancy / Trade** | +$0.420/oz | [-$0.466, +$1.352] | $0.000/oz | **NO** (Spans zero) |
| **Net Profit Factor** | 1.263 | [0.751, 2.111] | 1.000 | **NO** (Spans < 1.0) |
| **Win Rate** | 54.46% | [44.25%, 64.40%] | 50.00% | **NO** ($p = 0.2131$) |

**Final Statistical Conclusion:** The development partition provides proof of engineering correctness and economic plausibility, but **does not establish statistical edge**. Validation requires uncompromised out-of-sample testing.
