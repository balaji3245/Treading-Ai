# PHASE 27 DECISION RECORD: NEW HYPOTHESIS DISCOVERY & RESEARCH DESIGN

**Phase:** 27 — New Hypothesis Discovery & Research Design  
**Repository:** `Treading-Ai`  
**Execution Timestamp:** 2026-10-30T13:40:00 UTC  
**Baseline Commit:** `5038d33e4ff7e76d7f8d308da0b9b76132bfdc82`  
**Evaluation Scope:** 2021-01-01 to 2022-12-31 UTC Development Partition ($N = 141,614$ M5 bars)  

---

## Final Formal Verdict

```
PHASE 27 VERDICT: FAIL — ALL CANDIDATE STRATEGIES REJECTED
```

*All five pre-registered candidate hypotheses failed the pre-registered development promotion gates on the authorized 2021–2022 development partition. No candidate qualifies for locked out-of-sample validation or further development. In strict adherence to scientific integrity, zero strategies are forced or curve-fitted.*

---

## 1. Candidate Hypothesis Decision Scorecard

| Hypothesis ID | Proposed Market Dynamic | Sample Size ($N$) | Net PnL (1.0×) | Net Profit Factor | Win Rate | Primary Failure Reason | Terminal Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **HYP-27-VOL-SHOCK-EXPANSION** | Asian volatility shock continuation | 49 | +$46.05 | 1.452 | 57.14% | Directional asymmetry (Long PF 0.923 $< 1.05$) | **REJECTED** |
| **HYP-27-LONDON-PM-FIX-IMBALANCE** | LBMA PM Fix auction momentum | 133 | +$73.53 | 1.284 | 48.12% | Directional asymmetry (Long PF 0.959) & Win Rate $< 50\%$ | **REJECTED** |
| **HYP-27-POST-COMEX-DRIFT-REVERSION** | Late NY illiquid drift reversion | 100 | +$23.55 | 1.311 | 55.00% | Expectancy (+$0.235/oz $< +\$0.50/oz); Fails at 2.0× costs | **REJECTED** |
| **HYP-27-CONSECUTIVE-RANGE-MOMENTUM** | Multi-day expansion continuation | 46 | +$64.90 | 1.453 | 45.65% | Severe Long collapse (Long PF 0.342); Win Rate 45.65% | **REJECTED** |
| **HYP-27-MONDAY-WEEKEND-GAP-REVERSION** | Monday Asian weekend gap fade | 40 | -$5.76 | 0.930 | 42.50% | Negative net expectancy (-$0.144/oz); Fails all gates | **REJECTED** |

**Summary:** **0 of 5 Hypotheses Qualified as Candidates for Further Research**.

---

## 2. Core Quantitative Rationale

1. **Failure of Directional Symmetry Across Momentum Strategies:**
   - Both `HYP-27-VOL-SHOCK-EXPANSION` (Long PF 0.923 vs Short PF 3.680), `HYP-27-LONDON-PM-FIX-IMBALANCE` (Long PF 0.959 vs Short PF 1.763), and `HYP-27-CONSECUTIVE-RANGE-MOMENTUM` (Long PF 0.342 vs Short PF 2.674) suffered severe directional asymmetry.
   - Long trades across all three momentum candidates incurred net losses during 2021–2022. Because gold experienced a broader macro consolidation with sharp downdrafts, upward momentum impulses frequently suffered immediate exhaustion and failed to follow through. Any strategy that functions exclusively on one side of the market is structurally fragile and violates the pre-registered symmetry gate ($\text{PF} \ge 1.05$).
2. **The Intraday Frictional Wall on Reversion Strategies:**
   - `HYP-27-POST-COMEX-DRIFT-REVERSION` produced a balanced directional hit rate (55.0% win rate, Long PF 1.427, Short PF 1.210). However, the average gross trade was only +$0.485/oz.
   - Baseline round-turn friction of $0.25/oz consumed 51.5% of gross profits, leaving a net expectancy of only +$0.235/oz (failing the $\ge +\$0.50/oz$ economic requirement). Under 2.0× stressed costs ($0.50/oz), the strategy became net negative. The edge is too thin to survive real-world execution.
   - `HYP-27-MONDAY-WEEKEND-GAP-REVERSION` failed completely, generating a negative net PnL (-$5.757/oz) as weekend gaps often reflected genuine fundamental repricing rather than liquidity vacuums.
3. **Statistical Significance & Multiple Testing Control:**
   - Under Holm–Bonferroni family-wise error rate control across the $m=5$ candidate hypotheses, zero hypotheses achieved statistical significance at $\alpha = 0.05$.
   - Moving-block bootstrap 95% confidence intervals for mean net expectancy spanned zero across all five strategies.

---

## 3. Anti-Overfitting & Research Governance Compliance

1. **Zero Post-Hoc Tuning:**
   - No thresholds, stop distances, or holding windows were relaxed, curve-fitted, or adjusted after observing development performance.
2. **Absolute Holdout Partition Isolation:**
   - The 2025 Validation Partition (`val.parquet`) and 2026 Test Partition (`test.parquet`) remain **100% untouched, uninspected, and pristine**.
3. **Transparent Negative Reporting:**
   - Scientific integrity requires acknowledging when empirical data does not support theoretical hypotheses. Rejecting all 5 candidates protects the research program from deploying illusory, curve-fitted models.

---

## 4. Scope of Authorization & Future Direction

1. **What is Prohibited:**
   - No hypothesis from Phase 27 is authorized for locked validation, parameter optimization, or live execution.
   - Live trading, paper trading, and broker connectivity remain strictly prohibited.
2. **Next Steps for Research:**
   - The failure of high-frequency intraday momentum and session-transition patterns on M5 XAUUSD confirms the findings of Phase 17: high-frequency intraday moves in spot gold have extremely low signal-to-noise ratios relative to transaction friction ($0.25–$0.50/oz).
   - Any future research must explore structurally different horizons (e.g. multi-day swing holding periods where expected price excursions exceed $15–$30/oz, rendering $0.25/oz friction negligible) or exogenous structural flow datasets.
