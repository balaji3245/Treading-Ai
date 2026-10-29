# Phase 20: Out-of-Sample Empirical Results Report

**Status:** Completed & Methodologically Verified  
**Date:** October 2026  
**Evaluation Window:** 2023-01-02 to 2024-12-31 ($N_{\text{oos}} = 516$ Institutional Sessions)  
**Development Window:** 2021-03-11 to 2022-12-30 ($N_{\text{dev}} = 468$ Institutional Sessions)  
**Primary Verdict:** `NO EVIDENCE OF PREDICTIVE EDGE`

---

## 1. Executive Summary

This report delivers the out-of-sample empirical evaluation of the pre-registered macroeconomic hypothesis for spot gold (XAUUSD). All feature standardization parameters, model weights, and directional rules were fit exclusively on the 2021–2022 Development period and frozen prior to running the 2023–2024 Out-of-Sample evaluation.

### Core Findings
1.  **Predictive Failure:** Out-of-sample linear correlation between daily macroeconomic signals and next-session gold returns is statistically indistinguishable from zero ($|r| \le 0.0244, p \ge 0.58$). Regression $R^2$ is effectively zero ($R^2 \le 0.0006$).
2.  **Coin-Flip Directional Accuracy:** Directional hit rates across candidate models range from **$49.7\%$ to $51.4\%$**, failing two-tailed binomial significance tests against a random coin toss ($p \ge 0.28$).
3.  **Cost Friction Dominates:** Net of realistic execution and financing costs ($\$0.42\text{--}\$0.66/\text{oz}$ round turn), **every active macroeconomic model loses money** ($-\$79.02/\text{oz}$ to $-\$297.18/\text{oz}$), producing Net Profit Factors strictly below parity ($0.894$ to $0.978$).
4.  **No-Trade Baseline Superiority:** The **No-Trade baseline ($\$0.00$)** outperforms all four active macroeconomic models.
5.  **Rejection of Promotion:** All candidate models fail the pre-registered promotion threshold of $\text{Net PF} > 1.25$ and fail multiple-testing corrections.

---

## 2. Predictive Quality Metrics (Out-of-Sample 2023–2024)

Predictive metrics evaluate the raw statistical association between the pre-registered macroeconomic scores and realized next-session arithmetic returns ($R_{t+1}$), independent of trading execution:

| Candidate Model | Predictive Feature Specification | Pearson Correlation ($r$) | Pearson $p$-Value | Spearman Rank ($\rho$) | OLS $R^2$ | Directional Accuracy | Binomial Test $p$-Value |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Model A (Yield Only)** | 1-Day $\Delta \text{TIPS}_{10Y}$ Real Yield (`DFII10`) | $+0.0076$ | $0.8636$ | $-0.0082$ | $0.0001$ | $49.73\%$ | $0.5625$ |
| **Model B (Dollar Only)** | 1-Day $\% \Delta \text{Broad Dollar}$ (`DTWEXBGS`) | $+0.0244$ | $0.5808$ | $+0.0365$ | $0.0006$ | $50.76\%$ | $0.4008$ |
| **Model C (Bivariate)** | Equal-weighted Yield + Dollar Composite | $+0.0197$ | $0.6559$ | $+0.0131$ | $0.0004$ | $50.97\%$ | $0.3460$ |
| **Model D (Trivariate)** | Yield + Dollar + Breakeven Inflation Composite | $+0.0163$ | $0.7112$ | $+0.0271$ | $0.0003$ | $51.36\%$ | $0.2836$ |

### Interpretation of Predictive Metrics
*   **Correlation Collapse:** The expected negative economic relationship ($\beta < 0$) completely vanished out-of-sample. Pearson correlation coefficients are near zero ($+0.0076$ to $+0.0244$), with two-tailed $p$-values exceeding $0.58$.
*   **Zero Explanatory Power:** Regression $R^2$ values indicate that 1-day macro differences explain less than **$0.06\%$** of the variance in next-session gold returns.
*   **Statistical Non-Significance:** Binomial tests confirm that a $50.76\%$ or $51.36\%$ directional accuracy on $N=516$ sessions is fully consistent with pure sampling noise around a $50.0\%$ null.

---

## 3. Trading Performance Across Candidate Models & Benchmarks

Trading performance evaluates normalized 1 oz contracts held from 18:00 NY entry to 17:00 NY exit next day under baseline transaction costs (Spread $\$0.20/\text{oz}$, Slippage $\$0.10/\text{oz}$, Overnight Swap $-\$0.12/\text{oz}$ standard, $-\$0.36/\text{oz}$ Wednesday):

### Baseline Cost Scenario ($1.0\times$ Friction: Average $\approx \$0.47/\text{oz}$)

| Model / Benchmark | Active Trades | Gross PnL ($\$/\text{oz}$) | Total Costs ($\$/\text{oz}$) | Net PnL ($\$/\text{oz}$) | Win Rate | Net Profit Factor | Max Drawdown ($\$/\text{oz}$) | Max DD Pct | Avg Net PnL / Trade |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Model A (Yield Only)** | 364 | $-\$121.74$ | $\$175.44$ | **$-\$297.18$** | $48.35\%$ | **$0.894$** | $\$387.55$ | $3.86\%$ | $-\$0.82$ |
| **Model B (Dollar Only)** | 396 | $+\$112.02$ | $\$191.04$ | **$-\$79.02$** | $48.99\%$ | **$0.973$** | $\$433.85$ | $4.21\%$ | $-\$0.20$ |
| **Model C (Bivariate)** | 516 | $+\$159.52$ | $\$241.68$ | **$-\$82.16$** | $49.81\%$ | **$0.978$** | $\$447.56$ | $4.40\%$ | $-\$0.16$ |
| **Model D (Trivariate)** | 516 | $-\$17.04$ | $\$241.68$ | **$-\$258.72$** | $50.00\%$ | **$0.933$** | $\$495.85$ | $4.86\%$ | $-\$0.50$ |
| **Benchmark E (No-Trade)** | **0** | **$\$0.00$** | **$\$0.00$** | **$\$0.00$** | **—** | **—** | **$\$0.00$** | **$0.00\%$** | **$\$0.00$** |
| **Benchmark F (Buy & Hold)**| 516 | $+\$789.61$ | $\$241.68$ | **$+\$547.93$** | $52.13\%$ | **$1.159$** | $\$300.84$ | $2.96\%$ | $+\$1.06$ |
| **Benchmark G (Prior Mom)** | 516 | $-\$230.91$ | $\$241.68$ | **$-\$472.59$** | $48.45\%$ | **$0.881$** | $\$740.05$ | $7.34\%$ | $-\$0.92$ |

---

## 4. Transaction Cost Sensitivity Analysis

To verify whether models fail due to transaction friction or underlying predictive bankruptcy, models were evaluated across elevated ($1.5\times$) and stressed ($2.0\times$) cost environments:

| Strategy | $1.0\times$ Baseline Net PnL | $1.0\times$ Net PF | $1.5\times$ Elevated Net PnL | $1.5\times$ Net PF | $2.0\times$ Stressed Net PnL | $2.0\times$ Net PF | Cost Fragility Assessment |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Model A (Yield Only)** | $-\$297.18$ | $0.894$ | $-\$384.90$ | $0.865$ | $-\$472.62$ | $0.837$ | Unprofitable gross; costs steepen losses. |
| **Model B (Dollar Only)** | $-\$79.02$ | $0.973$ | $-\$174.54$ | $0.942$ | $-\$270.06$ | $0.912$ | Small gross gain wiped out by $1.0\times$ costs. |
| **Model C (Bivariate)** | $-\$82.16$ | $0.978$ | $-\$203.00$ | $0.947$ | $-\$323.84$ | $0.917$ | Gross $+\$159.52$ completely overcome by costs. |
| **Model D (Trivariate)** | $-\$258.72$ | $0.933$ | $-\$379.56$ | $0.903$ | $-\$500.40$ | $0.875$ | Unprofitable gross; severe cost drag. |
| **Benchmark F (Buy & Hold)**| $+\$547.93$ | $1.159$ | $+\$427.09$ | $1.122$ | $+\$306.25$ | $1.086$ | Profitable across all costs due to macro bull trend. |
| **Benchmark G (Prior Mom)** | $-\$472.59$ | $0.881$ | $-\$593.43$ | $0.853$ | $-\$714.27$ | $0.826$ | Severe mean-reversion whipsaws. |

---

## 5. Detailed Model-by-Model Analysis

### Model A: Real Yield Change Only (`d1_real_yield`)
*   **Hypothesis:** $\Delta y_t > 0 \implies \text{Short}$; $\Delta y_t < 0 \implies \text{Long}$.
*   **Empirical Result:** Gross PnL was negative ($-\$121.74/\text{oz}$) even before costs. Out-of-sample correlation was positive ($r = +0.0076$), contradicting the economic hypothesis. Directional hit rate ($49.73\%$) was below $50\%$.
*   **Verdict:** **COMPLETE REJECTION**.

### Model B: Broad Dollar Index Change Only (`d1_broad_dollar`)
*   **Hypothesis:** $\Delta d_t > 0 \implies \text{Short}$; $\Delta d_t < 0 \implies \text{Long}$.
*   **Empirical Result:** Achieved a marginal positive gross return of $+\$112.02/\text{oz}$ over 396 trades (Gross PF $1.039$). However, total baseline transaction costs were $\$191.04/\text{oz}$, producing a net loss of $-\$79.02/\text{oz}$ (Net PF $0.973$). Directional hit rate was $50.76\%$ ($p = 0.40$).
*   **Verdict:** **REJECTED (COST FRICTION DOMINATES)**.

### Model C: Bivariate Macro Composite (Yield + Dollar)
*   **Hypothesis:** Combining yields and dollar strength filters noise and creates a robust directional signal.
*   **Empirical Result:** Generated gross profits of $+\$159.52/\text{oz}$ across 516 sessions ($100\%$ exposure). However, transaction friction of $\$241.68/\text{oz}$ turned cumulative performance negative to $-\$82.16/\text{oz}$ (Net PF $0.978$). Under $2.0\times$ costs, net losses expanded to $-\$323.84/\text{oz}$.
*   **Verdict:** **REJECTED (FAILED PROMOTION HURDLE)**.

### Model D: Trivariate Macro Composite (Yield + Dollar + Inflation)
*   **Hypothesis:** Adding breakeven inflation expectations improves signal timing.
*   **Empirical Result:** Underperformed Model C across all dimensions. Gross PnL was negative ($-\$17.04/\text{oz}$) and net PnL was $-\$258.72/\text{oz}$ (Net PF $0.933$). Breakeven inflation added zero out-of-sample alpha.
*   **Verdict:** **COMPLETE REJECTION**.

---

## 6. Critical Methodological Distinctions

This empirical test confirms two fundamental quantitative backtesting principles:
1.  **Directional Accuracy Above 50% Is Not Proof of Profitability:** Model C achieved a $50.97\%$ hit rate and Model D achieved $51.36\%$. Both models lost money net of costs. In spot gold, small win rate edges ($< 52\%$) cannot overcome the combined friction of bid-ask spread, slippage, and overnight swap debits.
2.  **Positive Gross Return Is Not Proof of an Edge:** Model B ($+\$112.02$) and Model C ($+\$159.52$) generated positive gross PnL. Neither strategy is tradable because market friction exceeds the gross margin.

*Conclusion:* The pre-registered macroeconomic models provide **no credible, cost-adjusted predictive edge** for daily spot gold.
