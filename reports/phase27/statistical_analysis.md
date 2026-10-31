# PHASE 27: STATISTICAL ANALYSIS & EMPIRICAL PERFORMANCE REPORT

**Phase:** 27 — New Hypothesis Discovery & Research Design  
**Repository:** `Treading-Ai`  
**Dataset:** 2021-01-01 to 2022-12-30 UTC Development Partition ($N = 141,614$ M5 bars, 515 regular trading days)  
**Execution Timestamp:** 2026-10-30T13:25:00 UTC  

---

## 1. Executive Summary

Five genuinely distinct, economically motivated trading hypotheses were pre-registered in `hypothesis_registry.md` (SHA-256: `e51dfffc1e42e7f8312adaeba71d31aaf4532100942d7fbc3c01ac4c6b044337`) and evaluated on the authorized 2021–2022 development partition. 

### Core Empirical Findings:
- **Total Trades Generated:** 368 trades across the 5 candidate strategies.
- **Hypotheses Passing All Development Gates:** **0 / 5 (0.0%)**.
- **Hypotheses Classified as REJECTED:** **5 / 5 (100.0%)**.
- **Hypotheses Classified as INCONCLUSIVE:** **0 / 5 (0.0%)**.
- **Candidates Qualified for Out-of-Sample Testing:** **0 / 5 (0.0%)**.
- **Multiple Testing Adjustment (Holm–Bonferroni, $m=5$):** Zero hypotheses achieved statistical significance after family-wise error rate control at $\alpha = 0.05$.

In accordance with scientific integrity and anti-overfitting governance, **no hypothesis is forced or manufactured as a winner**. All five hypotheses fail pre-registered development promotion criteria and are formally rejected.

---

## 2. Hypothesis-by-Hypothesis Empirical Breakdown

### 2.1 HYP-27-VOL-SHOCK-EXPANSION (Post-Asian Volatility Shock Momentum)
- **Market Mechanism:** European opening continuation following extreme Asian True Range expansion ($\text{NAR} \ge 0.50$) with high directional conviction ($\ge 60\%$).
- **Trading Window:** Entry at 08:05:00 UTC Open, flat exit at 12:00:00 UTC Close.
- **Empirical Results:**
  - Sample Size ($N$): **49 trades** (Exceeds min $N \ge 35$).
  - Gross PnL: +$58.296/oz | Total Friction: $12.250/oz | Net PnL (1.0×): **+$46.046/oz**.
  - Net Expectancy: **+$0.940/oz** | Net Profit Factor: **1.452** | Win Rate: **57.14%** (28W / 21L).
  - Maximum Drawdown: **$18.207/oz**.
- **Directional Decomposition:**
  - Long Trades: 30 trades | Net PnL: **-$6.309/oz** | Profit Factor: **0.923** (FAILS GATE $\ge 1.05$).
  - Short Trades: 19 trades | Net PnL: **+$52.355/oz** | Profit Factor: **3.680**.
- **Statistical Inference:**
  - Moving-Block Bootstrap 95% CI (Expectancy): **[-$0.457/oz, +$2.207/oz]** (Spans zero).
  - Moving-Block Bootstrap 95% CI (Profit Factor): **[0.819, 2.545]** (Spans 1.0).
  - Exact Binomial Test vs 50% Null: $p = 0.1958$ (Not significant).
  - Holm–Bonferroni Corrected Threshold ($k=2$): $\alpha / 4 = 0.0125 \implies$ Not significant.
- **Failure Mode & Gate Evaluation:**
  - **FAILS Gate 5 (Directional Symmetry):** Long trades suffered a sub-1.0 profit factor (0.923), indicating that the strategy only worked on the short side during 2021–2022. Fading overnight upward expansions resulted in net losses.
  - **Verdict:** **REJECTED**.

---

### 2.2 HYP-27-LONDON-PM-FIX-IMBALANCE (LBMA PM Fix Auction Momentum)
- **Market Mechanism:** Directional post-auction momentum following large pre-fix institutional rebalancing displacement (14:00–15:00 UTC, $\text{FDR} \ge 0.20$).
- **Trading Window:** Entry at 15:05:00 UTC Open, flat exit at 17:00:00 UTC Close.
- **Empirical Results:**
  - Sample Size ($N$): **133 trades** (Exceeds min $N \ge 60$).
  - Gross PnL: +$106.777/oz | Total Friction: $33.250/oz | Net PnL (1.0×): **+$73.527/oz**.
  - Net Expectancy: **+$0.553/oz** | Net Profit Factor: **1.284** | Win Rate: **48.12%** (64W / 69L).
  - Maximum Drawdown: **$65.985/oz**.
- **Directional Decomposition:**
  - Long Trades: 68 trades | Net PnL: **-$6.353/oz** | Profit Factor: **0.959** (FAILS GATE $\ge 1.05$).
  - Short Trades: 65 trades | Net PnL: **+$79.880/oz** | Profit Factor: **1.763**.
- **Statistical Inference:**
  - Moving-Block Bootstrap 95% CI (Expectancy): **[-$0.496/oz, +$1.798/oz]** (Spans zero).
  - Moving-Block Bootstrap 95% CI (Profit Factor): **[0.777, 2.040]** (Spans 1.0).
  - Exact Binomial Test vs 50% Null: $p = 0.6985$ (Sub-50% win rate).
  - Holm–Bonferroni Corrected Threshold ($k=3$): $\alpha / 3 = 0.0167 \implies$ Not significant.
- **Failure Mode & Gate Evaluation:**
  - **FAILS Gate 3 (Win Rate $\ge 50\%$):** Observed win rate was only 48.12%.
  - **FAILS Gate 5 (Directional Symmetry):** Long trades produced net losses (-$6.35/oz, PF 0.959).
  - **High Drawdown:** Max drawdown of $65.98/oz exceeded the $45.00/oz risk threshold.
  - **Verdict:** **REJECTED**.

---

### 2.3 HYP-27-POST-COMEX-DRIFT-REVERSION (Late NY Illiquidity Drift Reversion)
- **Market Mechanism:** Fading late-evening illiquid price drift away from official COMEX settlement price (18:30–20:00 UTC).
- **Trading Window:** Entry at 20:05:00 UTC Open, flat exit at 21:55:00 UTC Close.
- **Empirical Results:**
  - Sample Size ($N$): **100 trades** (Exceeds min $N \ge 60$).
  - Gross PnL: +$48.546/oz | Total Friction: $25.000/oz | Net PnL (1.0×): **+$23.546/oz**.
  - Net Expectancy: **+$0.235/oz** (FAILS GATE $\ge +\$0.50/oz$).
  - Net Profit Factor: **1.311** | Win Rate: **55.00%** (55W / 45L).
  - Maximum Drawdown: **$15.246/oz**.
- **Directional Decomposition:**
  - Long Trades: 44 trades | Net PnL: **+$14.976/oz** | Profit Factor: **1.427** (PASSED $\ge 1.05$).
  - Short Trades: 56 trades | Net PnL: **+$8.570/oz** | Profit Factor: **1.210** (PASSED $\ge 1.05$).
- **Statistical Inference:**
  - Moving-Block Bootstrap 95% CI (Expectancy): **[-$0.319/oz, +$0.733/oz]** (Spans zero).
  - Moving-Block Bootstrap 95% CI (Profit Factor): **[0.692, 2.287]** (Spans 1.0).
  - Exact Binomial Test vs 50% Null: $p = 0.1841$.
  - Holm–Bonferroni Corrected Threshold ($k=1$): $\alpha / 5 = 0.010 \implies$ Not significant.
- **Failure Mode & Gate Evaluation:**
  - **FAILS Gate 1 (Economic Expectancy):** While directional symmetry (Long PF 1.427, Short PF 1.210) and win rate (55.0%) were balanced, the average net trade was only **+$0.235/oz**, falling well short of the +$0.50/oz gate.
  - **Friction Vulnerability:** Fixed transaction costs ($0.25/oz) consume **51.5%** of the gross trade profit ($0.485/oz). Under 2.0× stressed costs ($0.50/oz), the strategy turns net negative (-$1.45/oz, PF 0.983). The economic edge is too thin to survive institutional execution.
  - **Verdict:** **REJECTED**.

---

### 2.4 HYP-27-CONSECUTIVE-RANGE-MOMENTUM (Multi-Day Volatility Expansion Momentum)
- **Market Mechanism:** Trend continuation during London/US crossover following prior-day range expansion ($\text{TR}_{d-1} > \text{ATR20}$).
- **Trading Window:** Entry at 09:05:00 UTC Open, flat exit at 16:00:00 UTC Close.
- **Empirical Results:**
  - Sample Size ($N$): **46 trades** (Exceeds min $N \ge 40$).
  - Gross PnL: +$76.400/oz | Total Friction: $11.500/oz | Net PnL (1.0×): **+$64.900/oz**.
  - Net Expectancy: **+$1.411/oz** | Net Profit Factor: **1.453** | Win Rate: **45.65%** (21W / 25L).
  - Maximum Drawdown: **$39.188/oz**.
- **Directional Decomposition:**
  - Long Trades: 18 trades | Net PnL: **-$49.311/oz** | Profit Factor: **0.342** (CATASTROPHIC COLLAPSE).
  - Short Trades: 28 trades | Net PnL: **+$114.211/oz** | Profit Factor: **2.674**.
- **Statistical Inference:**
  - Moving-Block Bootstrap 95% CI (Expectancy): **[-$0.380/oz, +$4.005/oz]** (Spans zero).
  - Moving-Block Bootstrap 95% CI (Profit Factor): **[0.894, 2.672]** (Spans 1.0).
  - Exact Binomial Test vs 50% Null: $p = 0.7693$.
  - Holm–Bonferroni Corrected Threshold ($k=4$): $\alpha / 2 = 0.025 \implies$ Not significant.
- **Failure Mode & Gate Evaluation:**
  - **FAILS Gate 3 (Win Rate $\ge 50\%$):** Win rate was 45.65%.
  - **FAILS Gate 5 (Directional Symmetry):** Long trades collapsed completely (PF 0.342, -$49.31/oz). In 2021–2022, buying morning upward breakouts on expansion days suffered heavy losses, with all nominal gains coming from short trades.
  - **Verdict:** **REJECTED**.

---

### 2.5 HYP-27-MONDAY-WEEKEND-GAP-REVERSION (Monday Asian Gap Reversion)
- **Market Mechanism:** Fading Monday opening price gaps relative to Friday's benchmark close ($|\Delta P_{\text{gap}}| \ge 0.15 \times \text{ATR20}$).
- **Trading Window:** Entry at Monday 02:05:00 UTC Open, flat exit at Monday 07:00:00 UTC Close.
- **Empirical Results:**
  - Sample Size ($N$): **40 trades** (Exceeds min $N \ge 25$).
  - Gross PnL: +$4.243/oz | Total Friction: $10.000/oz | Net PnL (1.0×): **-$5.757/oz**.
  - Net Expectancy: **-$0.144/oz** | Net Profit Factor: **0.930** | Win Rate: **42.50%** (17W / 23L).
  - Maximum Drawdown: **$30.015/oz**.
- **Directional Decomposition:**
  - Long Trades: 20 trades | Net PnL: **-$26.969/oz** | Profit Factor: **0.476** (FAILS GATE).
  - Short Trades: 20 trades | Net PnL: **+$21.213/oz** | Profit Factor: **1.689**.
- **Statistical Inference:**
  - Moving-Block Bootstrap 95% CI (Expectancy): **[-$1.549/oz, +$1.687/oz]** (Deeply negative lower bound).
  - Moving-Block Bootstrap 95% CI (Profit Factor): **[0.416, 2.570]**.
  - Exact Binomial Test vs 50% Null: $p = 0.8659$.
  - Holm–Bonferroni Corrected Threshold ($k=5$): $\alpha / 1 = 0.050 \implies$ Not significant.
- **Failure Mode & Gate Evaluation:**
  - **FAILS ALL GATES:** Negative net expectancy (-$0.144/oz), profit factor $< 1.0$ (0.930), win rate $< 50\%$ (42.5%), negative net PnL at 1.5x (-$10.76/oz), and directional asymmetry (Long PF 0.476).
  - **Verdict:** **REJECTED**.

---

## 3. Multiple Hypothesis Testing Correction (Holm–Bonferroni)

To prevent false discovery when evaluating $m = 5$ candidate hypotheses concurrently, family-wise error rate (FWER) control was enforced via the step-down Holm–Bonferroni method at nominal $\alpha = 0.05$:

| Rank ($k$) | Hypothesis ID | Raw Binomial $p$-value | Holm–Bonferroni Threshold ($\frac{\alpha}{m - k + 1}$) | FWER Significant ($\le \alpha_{\text{HB}}$) |
| :--- | :--- | :--- | :--- | :--- |
| **1** | `HYP-27-POST-COMEX-DRIFT-REVERSION` | 0.1841 | $0.05 / 5 = \mathbf{0.01000}$ | **NO** |
| **2** | `HYP-27-VOL-SHOCK-EXPANSION` | 0.1958 | $0.05 / 4 = \mathbf{0.01250}$ | **NO** |
| **3** | `HYP-27-LONDON-PM-FIX-IMBALANCE` | 0.6985 | $0.05 / 3 = \mathbf{0.01667}$ | **NO** |
| **4** | `HYP-27-CONSECUTIVE-RANGE-MOMENTUM` | 0.7693 | $0.05 / 2 = \mathbf{0.02500}$ | **NO** |
| **5** | `HYP-27-MONDAY-WEEKEND-GAP-REVERSION` | 0.8659 | $0.05 / 1 = \mathbf{0.05000}$ | **NO** |

**Conclusion:** Not a single candidate hypothesis rejects the null hypothesis of random performance after multiple testing correction.

---

## 4. Overall Cross-Hypothesis Performance Matrix

| Hypothesis ID | $N$ | Net PnL (1.0×) | Expectancy | Net PF | Win Rate | Long PF | Short PF | Max DD | Final Classification |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `HYP-27-VOL-SHOCK-EXPANSION` | 49 | +$46.05 | +$0.940 | 1.452 | 57.14% | 0.923 | 3.680 | $18.21 | **REJECTED** |
| `HYP-27-LONDON-PM-FIX-IMBALANCE` | 133 | +$73.53 | +$0.553 | 1.284 | 48.12% | 0.959 | 1.763 | $65.99 | **REJECTED** |
| `HYP-27-POST-COMEX-DRIFT-REVERSION` | 100 | +$23.55 | +$0.235 | 1.311 | 55.00% | 1.427 | 1.210 | $15.25 | **REJECTED** |
| `HYP-27-CONSECUTIVE-RANGE-MOMENTUM` | 46 | +$64.90 | +$1.411 | 1.453 | 45.65% | 0.342 | 2.674 | $39.19 | **REJECTED** |
| `HYP-27-MONDAY-WEEKEND-GAP-REVERSION` | 40 | -$5.76 | -$0.144 | 0.930 | 42.50% | 0.476 | 1.689 | $30.02 | **REJECTED** |
