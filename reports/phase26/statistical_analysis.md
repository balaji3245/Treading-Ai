# PHASE 26: STATISTICAL ANALYSIS & EMPIRICAL PERFORMANCE REPORT

**Hypothesis ID:** `HYP-24-NY-REVERSAL-EXHAUSTION`  
**Phase:** 26 — Locked Historical Evaluation  
**Evaluation Scope:** 2023-01-01 to 2024-12-31 UTC (132,927 M5 Bars)  
**Execution Timestamp:** 2026-10-30T04:05:00 UTC  

---

## 1. Executive Summary & Evaluation Verdict

The frozen hypothesis `HYP-24-NY-REVERSAL-EXHAUSTION` was evaluated across the designated 2023–2024 historical evaluation partition ($N = 516$ regular trading days). 

Following the frozen protocol, days exhibiting morning excursion exhaustion ($\text{NER}_t \ge \theta_{\text{exhaustion}} = 0.320210$) triggered counter-trend entry at 14:05:00 UTC Open with a trailing stop-loss of $0.75 \times |\Delta P_t|$ and a scheduled COMEX pit-close exit at 18:30:00 UTC.

### Core Empirical Findings:
- **Eligible Days:** 87 calendar days (16.86% of trading sessions).
- **Executed Trades:** 77 trades (88.51% participation; 10 trades skipped fail-closed due to missing 14:05 provider entry bars).
- **Gross PnL:** **-$159.653 / \text{oz}**.
- **Net PnL (1.0× Baseline Friction @ $0.25/oz):** **-$178.903 / \text{oz}**.
- **Net Expectancy per Trade:** **-$2.323 / \text{oz}** (Gate: $\ge +\$0.50/\text{oz} \implies$ **FAILED**).
- **Net Profit Factor:** **0.551** (Gate: $\ge 1.25 \implies$ **FAILED**).
- **Directional Win Rate:** **42.86%** (33 wins, 44 losses; Gate: $\ge 52.5\% \implies$ **FAILED**).
- **Maximum Equity Drawdown:** **$178.903 / \text{oz}** (Gate: $\le \$45.00/\text{oz} \implies$ **FAILED**).
- **Directional Symmetry:** Long PF = **0.367**, Short PF = **0.824** (Gate: $\ge 1.10 \implies$ **FAILED**).
- **Bootstrap 95% CI (Expectancy):** **[-$4.156, +$0.149] / \text{oz}** (Gate: Lower bound $> \$0.00/\text{oz} \implies$ **FAILED**).

The strategy failed every single pre-registered promotion gate. The apparent mean-reverting edge documented on 2021–2022 development data did not persist into the 2023–2024 evaluation partition.

---

## 2. Performance Across Cost Tiers

Performance was evaluated across the pre-registered baseline and cost-stress tiers:

| Metric | 1.0× Baseline ($0.25/oz) | 1.5× Elevated ($0.375/oz) | 2.0× Stressed ($0.500/oz) |
| :--- | :--- | :--- | :--- |
| **Gross PnL ($/oz)** | -$159.653 | -$159.653 | -$159.653 |
| **Total Friction Assessed ($/oz)** | $19.250 | $28.875 | $38.500 |
| **Net PnL ($/oz)** | **-$178.903** | **-$188.528** | **-$198.153** |
| **Net Expectancy / Trade ($/oz)** | **-$2.323** | **-$2.448** | **-$2.573** |
| **Net Profit Factor** | **0.551** | **0.533** | **0.516** |
| **Winning Trades Count** | 33 | 33 | 32 |
| **Losing Trades Count** | 44 | 44 | 45 |
| **Directional Win Rate (%)** | **42.86%** | **42.86%** | **41.56%** |
| **Maximum Drawdown ($/oz)** | **$178.903** | **$188.528** | **$198.153** |
| **Max Drawdown (% of Asset)** | 1.79% | 1.89% | 1.98% |

Gross PnL is negative (-$159.65/oz) prior to any transaction costs. The strategy's failure is not an artifact of transaction friction; the underlying market directional edge was completely inverted.

---

## 3. Directional Sub-Cohort Breakdown

Evaluating Long and Short trades independently reveals severe structural breakdown across both wings of the strategy:

| Sub-Cohort | Trade Count | Share (%) | Net PnL ($/oz) | Win Rate (%) | Net Profit Factor | Gate ($\ge 1.10$) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Long Trades (Fade Drop)** | 37 | 48.05% | -$150.654 | 32.43% | **0.367** | **FAILED** |
| **Short Trades (Fade Rally)** | 40 | 51.95% | -$28.248 | 52.50% | **0.824** | **FAILED** |
| **Combined Strategy** | **77** | **100.00%** | **-$178.903** | **42.86%** | **0.551** | **FAILED** |

### Sub-Cohort Observations:
1. **Catastrophic Long Collapse:** Fading morning downside moves suffered a brutal win rate of 32.43% (12 wins, 25 losses) and a net profit factor of 0.367. In 2023–2024, morning downward drops in XAUUSD were not temporary liquidity exhaustions; they frequently initiated persistent afternoon selloffs or failed to rebound before the 18:30 UTC pit close.
2. **Short Sub-Cohort Failure:** Fading morning upside moves also failed (PF 0.824 $< 1.0$). In a powerful secular bull market with central bank accumulation and geopolitical tension, morning rallies consistently demonstrated momentum follow-through rather than mean reversion.

---

## 4. Exit Reason & Execution Distribution

| Exit Type | Count | Percentage | Cumulative Net Impact |
| :--- | :--- | :--- | :--- |
| **Scheduled Time Exit (18:30:00 UTC Close)** | 45 | 58.44% | Mixed (frequent small losses/wins) |
| **Stop-Loss Execution ($0.75 \times \|\Delta P_t\|$)** | 30 | 38.96% | Severe cumulative loss driver |
| **Open-Gap Stop Slippage Execution** | 1 | 1.30% | Adverse slippage realized |
| **Session Close Fallback (Missing Bar)** | 1 | 1.30% | Truncated session close |
| **Total Executions** | **77** | **100.00%** | Full execution fidelity |

In the 2021–2022 development partition, stop-losses occurred in only 18.55% of trades. In 2023–2024, stop-outs surged to **38.96%** (more than double the development rate). This demonstrates that morning excursions frequently developed into runaway intraday trend legs that blew through the $0.75 \times |\Delta P_t|$ stop barrier.

---

## 5. Statistical Inference & Uncertainty Bounds

### 5.1 Moving-Block Bootstrap (Primary Metric: Mean Net Expectancy)
- **Resamples ($B$):** 2,000
- **Block Length ($b$):** 5 trades
- **Point Estimate:** **-$2.323 / \text{oz}**
- **Bootstrap Mean:** -$2.327 / \text{oz}
- **Bootstrap Standard Error:** $1.096 / \text{oz}
- **95% Bootstrap Confidence Interval:** **[-$4.156 / \text{oz}, +$0.149 / \text{oz}]**
- **Gate Evaluation:** The lower bound (-$4.156/oz) is deeply negative, and the point estimate is negative. **FAILED**.

### 5.2 Moving-Block Bootstrap (Secondary Metric: Net Profit Factor)
- **Point Estimate:** **0.551**
- **Bootstrap Mean:** 0.602
- **95% Bootstrap Confidence Interval:** **[0.315, 1.035]**
- **Gate Evaluation:** Well below the 1.25 promotion gate. **FAILED**.

### 5.3 Directional Win Rate
- **Observed Wins:** 33 / 77 (42.86%)
- **Two-Sided Exact Binomial Test vs 50% Null:** $p = 0.2543$ (Not statistically distinguishable from 50%, but substantially below the 52.5% promotion gate).

---

## 6. Comparison Against Benchmarks

| Strategy / Benchmark | 2023–2024 Net PnL ($/oz) | Net Profit Factor | Max Drawdown ($/oz) |
| :--- | :--- | :--- | :--- |
| **No-Trade Cash Baseline** | **$0.000** | N/A | **$0.000** |
| **HYP-24-NY-REVERSAL-EXHAUSTION** | **-$178.903** | **0.551** | **$178.903** |
| **Continuous Buy-and-Hold Gold** | +$598.000 | 1.820 | $145.000 |

The strategy dramatically underperformed the zero-return cash baseline by -$178.903/oz, incurring a maximum peak-to-trough drawdown of $178.903/oz.

---

## 7. Forensic Diagnosis: Why Did HYP-24 Fail?

1. **Macro Regime Transition:**
   - **2021–2022 (Development Regime):** Gold was range-bound ($1,680–$2,070) amid aggressive Fed rate hikes and a surging US Dollar. Morning US macro data releases produced sharp initial overreactions that institutional market makers systematically absorbed and faded in the New York afternoon.
   - **2023–2024 (Evaluation Regime):** The macro regime shifted into powerful secular trend persistence:
     - *March 2023:* Silicon Valley Bank (SVB) collapse sparked intense flight-to-safety trend expansion.
     - *Late 2023:* Geopolitical conflict in the Middle East sparked sustained momentum buying.
     - *2024:* Unprecedented global central bank gold accumulation (PBOC, RBI, etc.) and anticipated Western rate cuts propelled gold into uncharted all-time highs above $2,600/oz.
2. **Breakdown of Counter-Trend Premises:**
   - In a runaway secular trend regime, large morning excursions ($\text{NER} \ge 0.320210$) represent institutional trend initiation rather than liquidity exhaustion. Fading these moves amounted to counter-trend knife-catching, resulting in a 38.96% stop-out rate and heavy drawdown.
3. **Overfitting to Consolidation Regimes:**
   - The strategy's positive performance in 2021–2022 was heavily regime-conditional. Without an exogenous regime filter to disable counter-trend execution during secular trend expansion, the strategy is economically fragile.
