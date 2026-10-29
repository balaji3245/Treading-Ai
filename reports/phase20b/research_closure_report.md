# Phase 20B: Formal Corrections & Research Closure Report

**Phase:** PHASE 20B — FORMAL CORRECTIONS & RESEARCH CLOSURE  
**Date:** October 2026  
**Auditor / Researcher:** Quantitative Researcher & Independent Validation Auditor  
**Final Closure Verdict:** **`PHASE 20 CLOSED — NO PREDICTIVE EDGE`**  

---

## 1. Executive Summary & Final Verdict

This report formally closes Phase 20 (*Pre-Registered Macroeconomic Hypothesis Test*) by incorporating all findings and accounting corrections established during the Phase 20A independent forensic audit.

### Final Verdict: **`PHASE 20 CLOSED — NO PREDICTIVE EDGE`**

**Scientific Disposition:**
1.  **Hypothesis Rejection:** Daily macroeconomic changes in US 10-Year Real Yields (`DFII10`), the Broad US Dollar Index (`DTWEXBGS`), and Breakeven Inflation (`T10YIE`) possess **zero statistically credible predictive information** for next-session institutional XAUUSD returns.
2.  **Directional Randomness:** Out-of-sample directional accuracies hover between **49.7% and 51.4%**, statistically indistinguishable from a fair coin toss (binomial $p \ge 0.23$).
3.  **Universal Net Losses:** After accounting for realistic execution frictions (spread and slippage) and financing costs, **every active macro model produces negative net returns** (-$294.54 to -$75.42/oz) over the 516-session out-of-sample period (2023–2024).
4.  **Failure of Promotion Gates:** All models fail the pre-registered hurdle of Net Profit Factor $> 1.25$ and fail Holm–Bonferroni multiple testing adjustment ($p \ge 0.5794$).
5.  **Research Termination:** In accordance with the pre-registered protocol, no parameter search, signal retraining, or strategy tweaking was performed. Research on this daily macro directional hypothesis is **permanently closed**.

---

## 2. Incorporation of Phase 20A Audit Findings

| Audit Finding | Issue in Phase 20 Implementation | Phase 20B Formal Resolution | File Reference |
| :--- | :--- | :--- | :--- |
| **Benchmark F Mislabeling** | Phase 20 labeled `pos_F = 1.0` as "Passive Buy-and-Hold", but charged daily turnover friction ($0.30/oz) 516 times ($154.80 friction) and discarded overnight roll gaps (+$7.55/oz). Understated Buy-and-Hold Net PnL by $162.30/oz. | Formally split into two distinct benchmarks:<br>1. **Benchmark F1 (Daily Long-Only Strategy):** 516 daily cycles, Net PnL = **+$548.17/oz**.<br>2. **Benchmark F2 (Continuous Buy-and-Hold):** Single 2-year position, Net PnL = **+$710.23/oz**. | [benchmark_definitions_formal.md](file:///home/bhoot/project/Treading-Ai/reports/phase20b/benchmark_definitions_formal.md) |
| **Wednesday Swap Timing** | Phase 20 applied $3\times$ swap on Wednesday 18:00 NY entry (`entry_dow == 2`). Under $T+2$ spot gold settlement, the roll across Wednesday 17:00 NY occurs on trade date Wednesday (`settlement_dow == 2`, entered Tuesday 18:00 NY). | Corrected swap allocation to `settlement_dow == 2`. Total 2-year swap reduced from $86.88 to $86.64/oz. Reconciled net PnL impact: +$0.24 to +$3.60 across models. | [reconciliation_side_by_side.md](file:///home/bhoot/project/Treading-Ai/reports/phase20b/reconciliation_side_by_side.md) |
| **Short Position Swap Asymmetry** | Phase 20 debited -$0.12/day on short positions identically to longs without empirical evidence. | Formally classified short swap as an **unverified retail proxy**. Conducted zero-short-swap sensitivity; all models remain net negative (-$259.38 to -$42.06/oz). | [reconciliation_side_by_side.md](file:///home/bhoot/project/Treading-Ai/reports/phase20b/reconciliation_side_by_side.md) |
| **Point-in-Time Limitations** | Annual recalculation of `DTWEXBGS` trade weights and absence of intraday release timestamps in FRED daily CSVs. | Formally maintained the mandatory classification **`RETROSPECTIVE PROXY`**. | [corrected_metrics.json](file:///home/bhoot/project/Treading-Ai/reports/phase20b/corrected_metrics.json) |

---

## 3. Cryptographic Governance & Partition Invariants

All data partitions and pre-registered protocol documents were verified cryptographically prior to formal closure:

```text
Protocol SHA-256: 82d47383a2b65265ed3bebc5080aa3e259941f7508286dd377bb8dff8f92969c (MATCH CONFIRMED)
Validation Partition (2025): 7e9222e9dc0893601e24505912eeab78330670c4e70ebcc2fa462ff8d44a4f94 (STRICT ZERO-ACCESS)
Test Partition (2026):       f95fd09a5d07666e3f1d9a72e840e2e97f3c058d11b6bb0c712b21dea86a5dec (STRICT ZERO-ACCESS)
```

No data from 2025 or 2026 was read, loaded, queried, or inspected at any point during Phase 20, 20A, or 20B.

---

## 4. Reconciled Performance Summary (1.0× Baseline Costs)

All values are expressed in USD per troy ounce ($/oz) over the 516 out-of-sample sessions (2023–2024):

| Model / Benchmark | Active Trades | Gross PnL | Corrected Total Costs | Corrected Net PnL | Net PnL Diff vs Phase 20 | Corrected Net PF | Win Rate (%) | Directional Hit Rate (%) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Model A (Yield Only)** | 364 | -$121.74 | $172.80 | **-$294.54** | +$2.64 | 0.895 | 45.33% | 49.73% |
| **Model B (Dollar Only)** | 396 | +$112.02 | $187.44 | **-$75.42** | +$3.60 | 0.975 | 47.73% | 50.76% |
| **Model C (Bivariate)** | 516 | +$159.52 | $241.44 | **-$81.92** | +$0.24 | 0.978 | 47.09% | 50.97% |
| **Model D (Trivariate)** | 516 | -$17.04 | $241.44 | **-$258.48** | +$0.24 | 0.933 | 46.12% | 51.36% |
| **Benchmark E (No-Trade)** | 0 | $0.00 | $0.00 | **$0.00** | $0.00 | N/A | 0.00% | 0.00% |
| **Benchmark F1 (Daily Long-Only)** | 516 | +$789.61 | $241.44 | **+$548.17** | +$0.24 | 1.159 | 53.68% | 52.91% |
| **Benchmark F2 (Continuous B&H)** | 1 | +$797.17 | $86.94 | **+$710.23** | +$162.30 | N/A | 100.00% | N/A |
| **Benchmark G (Prior Momentum)** | 516 | -$230.91 | $241.44 | **-$472.35** | +$0.24 | 0.881 | 43.60% | 46.71% |

---

## 5. Formal Disposition & Project Records

1.  **Phase 20 Status:** **CLOSED AND TERMINATED**.
2.  **Artifact Preservation:** Original Phase 20 artifacts ([reports/phase20/](file:///home/bhoot/project/Treading-Ai/reports/phase20/)) and Phase 20A audit artifacts ([reports/phase20a/](file:///home/bhoot/project/Treading-Ai/reports/phase20a/)) remain preserved as immutable historical records.
3.  **Active Canonical Record:** [reports/phase20b/corrected_metrics.json](file:///home/bhoot/project/Treading-Ai/reports/phase20b/corrected_metrics.json) is the definitive, corrected quantitative reference for Phase 20.
4.  **No Live Trading Integration:** No broker bridges, automated order routers, or Telegram alert pipelines will be constructed for this strategy.
