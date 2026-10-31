# PHASE 26 DECISION RECORD: LOCKED HISTORICAL EVALUATION

**Hypothesis ID:** `HYP-24-NY-REVERSAL-EXHAUSTION`  
**Phase:** 26 — Locked Historical Evaluation  
**Repository:** `Treading-Ai`  
**Authoritative Protocol:** `reports/phase24/frozen_evaluation_protocol.md`  
**Baseline Commit:** `5038d33e4ff7e76d7f8d308da0b9b76132bfdc82`  
**Execution Timestamp:** 2026-10-30T04:15:00 UTC  

---

## Final Formal Verdict

```
PHASE 26 VERDICT: FAIL — STRATEGY REJECTED
```

*Hypothesis `HYP-24-NY-REVERSAL-EXHAUSTION` failed all 7 pre-registered promotion gates on the 2023–2024 historical evaluation partition. The hypothesis is permanently rejected. No further development, optimization, or live deployment is authorized.*

---

## 1. Decision Rationale & Evaluation Summary

1. **Catastrophic Failure Across All Promotion Gates:**
   - In accordance with the pre-registered protocol, `HYP-24` was evaluated on the 2023–2024 evaluation partition using frozen parameters ($\theta_{\text{exhaustion}} = 0.320210$, stop multiplier $0.75$, 14:05 UTC entry, 18:30 UTC exit).
   - The strategy failed **0 of 7 gates**:
     - Net Expectancy: **-$2.323 / \text{oz}** (Gate: $\ge +\$0.50 \implies$ **FAIL**)
     - Net Profit Factor: **0.551** (Gate: $\ge 1.25 \implies$ **FAIL**)
     - Directional Win Rate: **42.86%** (Gate: $\ge 52.5\% \implies$ **FAIL**)
     - Friction Stress (1.5×): **-$188.528 / \text{oz}** (Gate: $> 0 \implies$ **FAIL**)
     - Directional Symmetry: **Long PF 0.367 / Short PF 0.824** (Gate: $\ge 1.10 \implies$ **FAIL**)
     - Bootstrap Expectancy 95% CI Lower Bound: **-$4.156 / \text{oz}** (Gate: $> 0 \implies$ **FAIL**)
     - Maximum Drawdown: **$178.903 / \text{oz}** (Gate: $\le \$45.00 \implies$ **FAIL**)
2. **Economic Fragility & Macro Regime Sensitivity:**
   - The strategy's positive performance during the 2021–2022 development cycle (+178.831 USD/oz net PnL, PF 1.586) proved to be an artifact of a specific range-bound, consolidation regime in gold.
   - When exposed to the persistent secular trend expansion of 2023–2024 (SVB banking crisis, geopolitical shocks, and sovereign central bank accumulation driving continuous new all-time highs), the counter-trend fading mechanism broke down completely. Morning overextensions turned into aggressive runaway momentum, resulting in heavy stop-loss executions (38.96% of trades) and severe capital destruction.
3. **Severe Directional Decay:**
   - Long trades (fading downward morning dips) collapsed completely to a 32.43% win rate and a 0.367 profit factor, losing -$150.654/oz. Short trades also failed with a profit factor of 0.824.

---

## 2. Anti-Overfitting & Governance Compliance

In strict compliance with institutional quantitative research standards:
1. **No Post-Hoc Tuning:**
   - Parameters, thresholds, stop distances, and holding periods were NOT re-optimized, tuned, or curve-fitted after observing 2023–2024 performance.
2. **Rejection is Final:**
   - `HYP-24-NY-REVERSAL-EXHAUSTION` is declared formally dead. It will not be retrofitted with filters or modified and re-tested on the same 2023–2024 partition.
3. **Holdout Partition Inviolability:**
   - The 2025 Validation Partition (`val.parquet`) and 2026 Test Partition (`test.parquet`) remain **100% untouched and pristine**. Zero data from 2025 or 2026 was inspected or queried.

---

## 3. Scope of Impact & Closure

1. **Hypothesis Lifecycle Status:**
   - `HYP-24-NY-REVERSAL-EXHAUSTION`: **PERMANENTLY REJECTED**.
2. **Prohibitions:**
   - Live trading, paper trading, or broker execution is strictly prohibited.
   - Presenting 2023–2024 as valid out-of-sample evidence for any revived version of this strategy is prohibited.
3. **Archival:**
   - All evaluation logs, trade ledgers, metrics, and audit reconciliation files are permanently archived under `reports/phase26/`.
