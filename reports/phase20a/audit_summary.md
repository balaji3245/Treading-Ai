# Phase 20A: Independent Forensic Audit Summary

**Audit Phase:** PHASE 20A — INDEPENDENT FORENSIC AUDIT  
**Date:** October 2026  
**Auditor Role:** Independent Quantitative Researcher & Python Code Auditor  
**Final Audit Verdict:** **`PHASE 20 PARTIALLY INVALID — CORRECTIONS REQUIRED`**  

---

## 1. Executive Summary

An independent forensic audit of Phase 20 (*Pre-Registered Macroeconomic Hypothesis Test*) was conducted to evaluate data integrity, accounting precision, benchmark correctness, statistical rigor, and macroeconomic alignment.

The audit confirms Phase 20's primary economic conclusion: **daily changes in US 10-Year Real Yields (`DFII10`), the Broad US Dollar Index (`DTWEXBGS`), and Breakeven Inflation (`T10YIE`) possess no predictive edge for next-session XAUUSD returns out-of-sample (2023–2024)**. Net of realistic execution frictions, all four macro models (A, B, C, D) lose money (-$294.54 to -$75.42/oz) and fail all promotion hurdles.

However, the audit identified **two significant implementation errors and one misleading benchmark label** in Phase 20's code:
1. **Benchmark F Mislabeling and Excessive Turnover Friction:** Phase 20 labeled `pos_F = 1.0` as "Passive Buy-and-Hold", but subjected it to daily round-turn spread ($0.20) and slippage ($0.10) for 516 consecutive sessions ($154.80 in friction). This is in fact a **Daily Long-Only Strategy**. True continuous Buy-and-Hold enters once, exits once, captures overnight gap returns (+$7.55/oz), and incurs holding swap ($86.64/oz), achieving **+$710.23/oz net PnL** rather than the reported **+$547.93/oz**.
2. **Wednesday Triple-Swap Rollover Off-by-One Timing Shift:** In `run_phase20_macro_test.py:309-311`, triple swap was debited when `entry_dow == 2` (Wednesday 18:00 NY entry). Under spot gold $T+2$ value date settlement conventions, holding across the Wednesday 17:00 NY roll corresponds to trade date Wednesday, which enters on Tuesday evening (`settlement_dow == 2`). This created a 1-session shift in triple swap debits, overstating baseline costs by $0.24 to $3.60 across models.
3. **Short Position Swap Asymmetry:** Phase 20 applied an unverified -$0.12/day debit to short positions identically to longs. While retail brokers charge asymmetrical debits, institutional spot short positions pay near-zero financing. Even if short swap is completely eliminated ($0.00), Model B improves to -$42.06/oz and Model C to -$50.12/oz, remaining strictly net negative.

---

## 2. Cryptographic and Data Partition Governance

| Invariant / Check | Expected Specification | Actual Audit Verification | Status |
| :--- | :--- | :--- | :--- |
| **Protocol Hash** | `82d47383a2b65265ed3bebc5080aa3e259941f7508286dd377bb8dff8f92969c` | [preregistered_protocol.md](file:///home/bhoot/project/Treading-Ai/reports/phase20/preregistered_protocol.md) computed: `82d47383a2b65265ed3bebc5080aa3e259941f7508286dd377bb8dff8f92969c` | **VERIFIED** |
| **2025 Validation Partition** | SHA-256: `7e9222e9dc0893601e24505912eeab78330670c4e70ebcc2fa462ff8d44a4f94` | Exact match confirmed via byte stream; 0 rows read/queried | **PROTECTED / ZERO ACCESS** |
| **2026 Test Partition** | SHA-256: `f95fd09a5d07666e3f1d9a72e840e2e97f3c058d11b6bb0c712b21dea86a5dec` | Exact match confirmed via byte stream; 0 rows read/queried | **PROTECTED / ZERO ACCESS** |
| **Data Scope** | 2021-03-11 to 2024-12-31 | Total 984 institutional daily sessions (468 Dev, 516 OOS) | **VERIFIED** |

---

## 3. Findings Register

| Finding ID | Component | Description | File & Line | Severity |
| :--- | :--- | :--- | :--- | :--- |
| **FIND-20A-01** | Benchmark F | Labeled as "Passive Buy-and-Hold" but charged round-turn spread ($0.20) and slippage ($0.10) every session ($154.80 total friction). Missed overnight roll gaps (+$7.55/oz). Understated Buy-and-Hold Net PnL by $162.30/oz. | [run_phase20_macro_test.py:304](file:///home/bhoot/project/Treading-Ai/scripts/run_phase20_macro_test.py#L304) | **CRITICAL (Reporting / Benchmark)** |
| **FIND-20A-02** | Cost Accounting | Wednesday triple swap applied to Wednesday 18:00 NY entry (`entry_dow == 2`) instead of Tuesday 18:00 NY entry settling Wednesday (`settlement_dow == 2`). 1-session timing shift. | [run_phase20_macro_test.py:309-311](file:///home/bhoot/project/Treading-Ai/scripts/run_phase20_macro_test.py#L309-L311) | **MODERATE (Accounting Precision)** |
| **FIND-20A-03** | Cost Accounting | Short position swap debited -$0.12/day without empirical validation (retail proxy assumption). | [run_phase20_macro_test.py:311](file:///home/bhoot/project/Treading-Ai/scripts/run_phase20_macro_test.py#L311) | **LOW (Proxy Sensitivity)** |
| **FIND-20A-04** | Statistical Testing | Holm-Bonferroni correction applied exclusively to Pearson correlation $p$-values ($M=4$). Trading PnL metrics were evaluated as threshold gates rather than formal hypothesis tests. | [run_phase20_macro_test.py:411-430](file:///home/bhoot/project/Treading-Ai/scripts/run_phase20_macro_test.py#L411-L430) | **LOW (Methodological Clarity)** |
| **FIND-20A-05** | Directional Accuracy | Inactive positions (`pos == 0`) were correctly excluded from numerator and denominator. Formula reproduces identically. | [run_phase20_macro_test.py:183-184](file:///home/bhoot/project/Treading-Ai/scripts/run_phase20_macro_test.py#L183-L184) | **VERIFIED CORRECT** |

---

## 4. Side-by-Side Reconciliation Table (1.0× Baseline Costs)

All values are in USD per troy ounce ($/oz) over the 516 out-of-sample sessions (2023–2024):

| Model / Benchmark | Active Trades | Gross PnL | Phase 20 Costs | Corrected Costs | Phase 20 Net PnL | Corrected Net PnL | Cost Diff | Net PF (Corr) | Max DD (USD) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Model A (Yield Only)** | 364 | -$121.74 | $175.44 | $172.80 | -$297.18 | **-$294.54** | -$2.64 | 0.895 | $489.26 |
| **Model B (Dollar Only)** | 396 | +$112.02 | $191.04 | $187.44 | -$79.02 | **-$75.42** | -$3.60 | 0.975 | $401.78 |
| **Model C (Bivariate)** | 516 | +$159.52 | $241.68 | $241.44 | -$82.16 | **-$81.92** | -$0.24 | 0.978 | $458.50 |
| **Model D (Trivariate)** | 516 | -$17.04 | $241.68 | $241.44 | -$258.72 | **-$258.48** | -$0.24 | 0.933 | $454.12 |
| **Benchmark E (No-Trade)** | 0 | $0.00 | $0.00 | $0.00 | $0.00 | **$0.00** | $0.00 | N/A | $0.00 |
| **Benchmark F (Daily Long-Only)** | 516 | +$789.61 | $241.68 | $241.44 | +$547.93 | **+$548.17** | -$0.24 | 1.159 | $298.54 |
| **Benchmark F (Continuous B&H)** | 1 | +$797.17 | N/A | $86.94 | N/A | **+$710.23** | -$154.50 | N/A | $285.34 |
| **Benchmark G (Momentum)** | 516 | -$230.91 | $241.68 | $241.44 | -$472.59 | **-$472.35** | -$0.24 | 0.881 | $721.46 |

---

## 5. Audit Conclusion & Final Action

The final audit verdict is **`PHASE 20 PARTIALLY INVALID — CORRECTIONS REQUIRED`**.

*   Phase 20's primary scientific conclusion—that macro variables fail to predict next-session gold returns—is **confirmed and reinforced**. None of the models achieve statistical significance, directional hit rates hover between 49.7% and 51.4%, and net PnL is deeply negative across all models under every cost scenario.
*   However, the benchmark mislabeling and Wednesday rollover timing error require formal correction in project records.
*   Next action: Reject all macro models for live deployment or execution; preserve corrected metrics in [corrected_results.json](file:///home/bhoot/project/Treading-Ai/reports/phase20a/corrected_results.json); continue maintaining strict zero-access protections on 2025/2026 data partitions.
