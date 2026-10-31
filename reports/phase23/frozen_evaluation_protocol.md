# FROZEN EVALUATION PROTOCOL: PHASE 23

**Document Version:** 1.0.0 (FROZEN)  
**Hypothesis ID:** `HYP-21-ASIAN-LONDON-EXPANSION`  
**Phase:** 23 — Locked Out-of-Sample Evaluation  
**Status:** FROZEN PROTOCOL EXECUTION  
**Evaluation Partition:** 2023-01-01 to 2024-12-31 UTC  
**Baseline Commit:** `5038d33e4ff7e76d7f8d308da0b9b76132bfdc82`  

---

## 1. Governance & Protocol Invariants

Phase 23 executes a locked out-of-sample evaluation of `HYP-21-ASIAN-LONDON-EXPANSION` strictly following the frozen specification developed and audited in Phase 22.

### Mandatory Directives:
1. **Zero Parameter Tuning:** The compression threshold remains immutable at $\tau_{\text{compression}} = 0.281865$ (first quartile calibrated on 2021–2022 development data). No sliding, re-calibration, or parameter optimization is permitted.
2. **Strategy Rule Immutability:** Asian session (00:00–07:00 UTC), breakout monitoring (07:05–09:00 UTC), next-bar Open entry, stop-loss at opposite Asian boundary, same-bar stop precedence, open-gap slippage handling, and scheduled 12:00 UTC exit remain strictly identical to Phase 22.
3. **Partition Boundary Integrity:** The evaluation dataset comprises exclusively the 2023 and 2024 M5 processed partitions (`132,927` bars spanning `2023-01-02 23:00` to `2024-12-31 21:55` UTC).
4. **Prior Use Disclosure:** In compliance with quantitative integrity standards, it is explicitly disclosed that the 2023–2024 partition was previously accessed during Phase 19 (macro data acquisition) and Phase 20 (macro hypothesis testing). Although out-of-sample relative to `HYP-21-ASIAN-LONDON-EXPANSION` development, this partition is **not globally pristine**.
5. **Protected Partition Lockdown:** Zero access, querying, inspection, or processing of the protected 2025 validation (`val.parquet`) or 2026 test (`test.parquet`) partitions is permitted.

---

## 2. Frozen Strategy Specification Summary

| Component | Rule Definition | Implementation Parameter |
| :--- | :--- | :--- |
| **Asian Session Window** | Completed M5 bars from 00:00:00 to 07:00:00 UTC | `00:00` to `06:55` (84 bars) |
| **Volatility Benchmark** | Trailing 20-day True Range on daily bars ($\ge 100$ bars) | Shifted by 1 day (`shift(1)`) |
| **Compression Criterion** | $CR_t = \frac{\text{Asia Range}_t}{\text{ATR}_{20, t}^{\text{prior}}} \le \tau$ | $\tau_{\text{compression}} = 0.281865$ |
| **Breakout Monitoring** | Completed M5 bars whose close falls between 07:05 and 09:00 UTC | `07:00` to `08:55` (24 bars) |
| **Entry Timing** | Open of M5 bar immediately following first confirmed breakout close | `entry_idx = trigger_idx + 1` |
| **Entry Abort Rule** | Next bar Open breaching stop level aborts trade | Zero fill on adverse entry gap |
| **Initial Stop-Loss** | Placed at opposite Asian boundary | Low for Long; High for Short |
| **Intrabar Order of Ops** | Stop-loss evaluated before scheduled exit on every bar | Stop check precedes time exit |
| **Open Gap Stop Slippage** | Bar opening past stop executed at Open price | Realizes full gap slippage |
| **Scheduled Exit** | Time-based flat exit at 12:00:00 UTC Close | `11:55` bar close |
| **Trading Frequency** | Maximum of exactly 1 trade per calendar day | Enforced globally |

---

## 3. Transaction Cost & Friction Models

Performance is reported under three standardized transaction friction tiers:

1. **1.0× Baseline Cost:** $0.20/oz spread + $0.05/oz slippage = **$0.25/oz round-turn**.
2. **1.5× Elevated Cost:** $0.30/oz spread + $0.075/oz slippage = **$0.375/oz round-turn**.
3. **2.0× Stressed Cost:** $0.40/oz spread + $0.10/oz slippage = **$0.50/oz round-turn**.
4. **Overnight Financing (Swap):** $0.00/oz verified for all standard trades exiting by 12:00 UTC.

---

## 4. Pre-Registered Out-of-Sample Decision Criteria

To achieve a `PASS` verdict in Phase 23, the frozen strategy must satisfy **all** of the following quantitative gates on the 2023–2024 out-of-sample partition:

1. **Economic Viability:** Net PnL must be strictly positive under baseline costs ($0.25/oz) and remain non-negative under 1.5× cost stress.
2. **Statistical Significance:** The primary uncertainty metric (moving-block bootstrap 95% confidence interval for mean net expectancy) must strictly exclude zero (lower bound > $0.00/oz).
3. **Directional Robustness:** Both Long and Short directional sub-cohorts must demonstrate economic stability (Net Profit Factor $\ge 1.0$). Massive directional breakdown constitutes a failure of structural symmetry.
4. **Execution Integrity:** 100% of trades must adhere to intraday session boundaries without unauthorized overnight rollover.

Failure of any core gate mandates a formal **REJECT** decision.
