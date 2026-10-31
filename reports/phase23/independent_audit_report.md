# INDEPENDENT FORENSIC AUDIT REPORT: PHASE 23

**Hypothesis ID:** `HYP-21-ASIAN-LONDON-EXPANSION`  
**Phase:** 23 — Locked Out-of-Sample Evaluation  
**Auditor Role:** Independent Quantitative Code Auditor & Methodological Reviewer  
**Audit Timestamp:** 2026-10-30T03:30:00 UTC  
**Evaluation Partition:** 2023–2024 Out-of-Sample Data  

---

## 1. Executive Verdict & Core Findings

```
AUDIT VERDICT: PASS WITH CRITICAL FINDINGS (HYPOTHESIS FAILS GATES)
```

### Executive Summary:
An independent clean-room forensic audit of Phase 23 was conducted by reconstructing all trades directly from raw 2023–2024 M5 parquet bars via `scripts/run_phase23_independent_audit.py`.

1. **Trade Reconstruction:** Every single one of the 89 out-of-sample trades in `reports/phase23/evaluation_trades.csv` was independently reconstructed. **Zero discrepancies (0/89)** were found in dates, entry timestamps, entry prices, stop levels, exit timestamps, exit prices, exit reasons, gross PnL, or net PnL.
2. **Data Governance Verification:** Cryptographic checksums verify that the protected 2025 validation (`val.parquet`) and 2026 test (`test.parquet`) partitions remain **100% untouched and unmodified**.
3. **Audit Finding 1 (Severe Structural Failure):** Out-of-sample win rate dropped to 43.82% (39W / 50L). Short trades collapsed completely, generating a win rate of only 27.03% (PF 0.633, -$41.93/oz loss), proving that the strategy lacks directional robustness.
4. **Audit Finding 2 (Statistical Insignificance):** The moving-block bootstrap 95% confidence interval for mean net expectancy spans `[-$0.855, +$2.299]/oz`, failing to establish statistical edge over the $0 no-trade baseline.
5. **Audit Finding 3 (Midday Gap Distortion):** On 4 days in early 2023, data gaps between 11:00 and 12:00 UTC caused the implementation to hold positions until evening rollover (20:55 to 23:55 UTC), violating the daytime holding assumption and generating +$62.96/oz gross. When strictly capped at 12:00 UTC, net PnL collapses to +$5.68/oz and turns negative under 1.5× friction.

---

## 2. Scope, Commit Hash, & Checksums

- **Git Commit Baseline:** `5038d33e4ff7e76d7f8d308da0b9b76132bfdc82`
- **Working Tree:** Clean

### Cryptographic File Checksums:

| File Path | Description | SHA-256 Checksum |
| :--- | :--- | :--- |
| `data/processed/XAUUSD/M5/XAUUSD_M5_2023.parquet` | Raw 2023 Evaluation Bars (61,794 rows) | `4b0a461b598ff7ef0491a077523daf9e24009c86677270f90a1a318a4b862c77` |
| `data/processed/XAUUSD/M5/XAUUSD_M5_2024.parquet` | Raw 2024 Evaluation Bars (71,133 rows) | `1aa6027334f1bb7801be12553368e7420007fd6e2b0e20d26dcacd28076657d0` |
| `scripts/run_phase23_oos_evaluation.py` | Locked Out-of-Sample Engine | `85a9df67d6c56b0250bb7f9c8ef79c882bbd5e493b827cb34ca6a3fc0ee140ff` |
| `reports/phase23/evaluation_trades.csv` | Reconstructed Trade Log (89 trades) | `c9735d6cbdfa13cbdf9790be643033d8e9e144a69622d64f0b20cb374cfb2680` |
| `reports/phase23/evaluation_metrics.json` | Generated Metrics JSON | `01026046e8c89bdf0175b9f71c4d9bc27da64ca81b894d30a84d41ea87d3d258` |
| `scripts/run_phase23_independent_audit.py` | Forensic Audit Script | `b85dfd785a2bc3a195b0f19c969376d499ba54ea7432f81498b584d4a8ee1b6d` |
| `tests/test_phase23_evaluation.py` | Phase 23 Automated Test Suite | `69083329bb2a84976451e06497f1f3a2c59a35e8fa37d8000455dbd76378e9f2` |
| `data/features/XAUUSD_M5_features_val.parquet` | Protected 2025 Validation Partition | `7e9222e9dc0893601e24505912eeab78330670c4e70ebcc2fa462ff8d44a4f94` |
| `data/features/XAUUSD_M5_features_test.parquet` | Protected 2026 Test Partition | `f95fd09a5d07666e3f1d9a72e840e2e97f3c058d11b6bb0c712b21dea86a5dec` |

---

## 3. Independent Trade-Log Reconciliation

All 89 trades executed across the 2023–2024 partition were audited against the raw price series:

| Field Checked | Phase 23 Output | Audit Reconstruction | Discrepancies |
| :--- | :--- | :--- | :--- |
| **Trade Count** | 89 | 89 | **0** |
| **Dates & Direction** | 89 / 89 | 89 / 89 | **0** |
| **Entry Timestamps & Prices** | 89 / 89 | 89 / 89 | **0** |
| **Stop Prices** | 89 / 89 | 89 / 89 | **0** |
| **Exit Timestamps & Prices** | 89 / 89 | 89 / 89 | **0** |
| **Exit Reasons** | 89 / 89 | 89 / 89 | **0** |
| **Gross PnL (±$0.001)** | 89 / 89 | 89 / 89 | **0** |
| **Net PnL 1.0× (±$0.001)** | 89 / 89 | 89 / 89 | **0** |
| **Net PnL 1.5× (±$0.001)** | 89 / 89 | 89 / 89 | **0** |
| **Net PnL 2.0× (±$0.001)** | 89 / 89 | 89 / 89 | **0** |

Reconciliation Status: **100.0% EXACT MATCH (0 discrepancies).**

---

## 4. Forensic Investigation of Data Gap Anomaly

The audit investigated the 4 trades labeled `LAST_AVAILABLE_BAR_EXIT`:
1. `2023-03-08` (LONG): Entered 07:15 UTC at 1814.545. Bars missing from 11:00 to 12:00 UTC. Exited at 23:55 UTC Close at 1815.175 (Net PnL +$0.38/oz).
2. `2023-03-09` (LONG): Entered 07:20 UTC at 1817.785. Bars missing after 10:55 UTC. Exited at 20:55 UTC Close at 1830.485 (Net PnL +$12.45/oz).
3. `2023-04-13` (LONG): Entered 07:10 UTC at 2024.275. Bars missing from 11:00 to 12:00 UTC. Exited at 22:55 UTC Close at 2039.874 (Net PnL +$15.35/oz).
4. `2023-04-14` (SHORT): Entered 07:05 UTC at 2037.525. Bars missing from 11:00 to 12:00 UTC. Exited at 20:55 UTC Close at 2003.498 (Net PnL +$33.78/oz).

### Audit Assessment:
These 4 trades violated the daytime holding assumption by carrying positions past the 21:00 UTC daily rollover window and holding into Friday evening. Together, they contributed **+$62.96/oz in gross PnL**. When positions are liquidated at the last available bar prior to 12:00 UTC (10:55 UTC), gross PnL drops by **-$61.58/oz**, resulting in total out-of-sample net PnL of **+$5.676/oz** at 1.0× friction and **-$5.45/oz** at 1.5× friction.

---

## 5. Automated Test Suite Verification

The Phase 23 evaluation test suite (`tests/test_phase23_evaluation.py`) was executed:

```bash
PYTHONPATH=src:. .venv/bin/pytest tests/test_phase23_evaluation.py -v
```

```text
============================= test session starts ==============================
collected 6 items

tests/test_phase23_evaluation.py::test_phase23_protected_partitions_unmodified PASSED [ 16%]
tests/test_phase23_evaluation.py::test_phase23_evaluation_data_boundaries PASSED [ 33%]
tests/test_phase23_evaluation.py::test_phase23_frozen_strategy_parameters PASSED [ 50%]
tests/test_phase23_evaluation.py::test_phase23_metrics_reconciliation PASSED [ 66%]
tests/test_phase23_evaluation.py::test_phase23_directional_failure_verification PASSED [ 83%]
tests/test_phase23_evaluation.py::test_phase23_decision_is_reject PASSED [100%]

============================== 6 passed in 0.65s ===============================
```

Full repository regression run: **265 passed across 34 test modules**.

---

## 6. Confirmation of Protected Dataset Integrity

It is explicitly certified that:
- `data/features/XAUUSD_M5_features_val.parquet` (2025): SHA-256 `7e9222...` (**UNTOUCHED**).
- `data/features/XAUUSD_M5_features_test.parquet` (2026): SHA-256 `f95fd0...` (**UNTOUCHED**).
- Zero rows or timestamps from 2025 or 2026 were accessed, queried, or analyzed.

---

## 7. Audit Recommendation

The implementation of the backtesting engine is verified mathematically correct and reproducible. However, because the hypothesis fails out-of-sample statistical significance, suffers severe directional collapse on Short trades, and exhibits sensitivity to execution gap anomalies, the hypothesis does not satisfy research promotion gates.

**Final Audit Recommendation:** Confirm the formal verdict of **REJECT**. Do NOT promote the strategy or touch the protected 2025 validation or 2026 test partitions.
