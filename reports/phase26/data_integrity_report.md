# PHASE 26: DATA INTEGRITY & PARTITION GOVERNANCE REPORT

**Hypothesis ID:** `HYP-24-NY-REVERSAL-EXHAUSTION`  
**Phase:** 26 — Locked Historical Evaluation  
**Dataset Scope:** 2023-01-01 to 2024-12-31 UTC (Evaluation Partition Only)  
**Execution Timestamp:** 2026-10-30T04:00:00 UTC  

---

## 1. Executive Data Boundaries & Partition Governance

To prevent data snooping, p-hacking, and holdout contamination, strict data boundaries were programmatically enforced:
1. **Authorized Partition:** Only processed 2023 and 2024 M5 historical data from `data/processed/XAUUSD/M5/` was ingested and analyzed.
2. **Protected Holdouts (2025 & 2026):**
   - 2025 Validation Partition (`val.parquet`) remained completely untouched.
   - 2026 Test Partition (`test.parquet`) remained completely untouched.
3. **Fail-Closed Verification:** Assertions confirmed all evaluated timestamps satisfy `2023-01-01 00:00:00 <= ts < 2025-01-01 00:00:00 UTC`.

---

## 2. Ingested Datasets & Cryptographic Checksums

### 2.1 Historical Evaluation Inventory (2023–2024)

| Dataset | Relative File Path | Row Count | File Size | SHA-256 Checksum |
| :--- | :--- | :--- | :--- | :--- |
| **XAUUSD M5 2023** | `data/processed/XAUUSD/M5/XAUUSD_M5_2023.parquet` | 61,794 | ~1.4 MB | `4b0a461b598ff7ef0491a077523daf9e24009c86677270f90a1a318a4b862c77` |
| **XAUUSD M5 2024** | `data/processed/XAUUSD/M5/XAUUSD_M5_2024.parquet` | 71,133 | ~1.9 MB | `1aa6027334f1bb7801be12553368e7420007fd6e2b0e20d26dcacd28076657d0` |
| **Total Evaluation** | Combined 2023–2024 Partition | **132,927** | ~3.3 MB | *Verified chronological sequence* |

### 2.2 Chronological Boundaries
- **Earliest Ingested Timestamp:** `2023-01-02 23:00:00+00:00 UTC`
- **Latest Ingested Timestamp:** `2024-12-31 21:55:00+00:00 UTC`
- **Boundary Audit:** Passed (`min_ts >= 2023-01-01` and `max_ts < 2025-01-01`).

### 2.3 Cryptographic Verification of Protected Holdout Partitions

Cryptographic SHA-256 hashes of the protected holdout stores were computed before and after evaluation:

| Partition | Storage Path | Expected SHA-256 | Evaluated SHA-256 | Integrity Status |
| :--- | :--- | :--- | :--- | :--- |
| **Validation 2025 (`val.parquet`)** | `data/features/XAUUSD_M5_features_val.parquet` | `7e9222e9dc0893601e24505912eeab78330670c4e70ebcc2fa462ff8d44a4f94` | `7e9222e9dc0893601e24505912eeab78330670c4e70ebcc2fa462ff8d44a4f94` | **100% UNTOUCHED** |
| **Test 2026 (`test.parquet`)** | `data/features/XAUUSD_M5_features_test.parquet` | `f95fd09a5d07666e3f1d9a72e840e2e97f3c058d11b6bb0c712b21dea86a5dec` | `f95fd09a5d07666e3f1d9a72e840e2e97f3c058d11b6bb0c712b21dea86a5dec` | **100% UNTOUCHED** |

---

## 3. Mandatory Prior-Use Disclosure

> [!WARNING]
> **Non-Pristine Data Status Disclosure:**  
> The 2023–2024 partition was previously utilized in Phase 19 (macro feature engineering), Phase 20 (daily macro directional model backtesting), and Phase 23 (London range breakout evaluation). While this dataset is strictly out-of-sample relative to the 2021–2022 development partition where `HYP-24` was formulated and frozen, **it is NOT virgin or globally pristine holdout data**. The results of this historical evaluation represent locked historical out-of-sample testing on non-pristine data.

---

## 4. Data Hygiene, Provider Anomalies & Missing Bar Audit

The 132,927 historical M5 bars were subjected to forensic sanity checks:
1. **High/Low Invariant:** Verified $\text{High} \ge \max(\text{Open}, \text{Close})$ and $\text{Low} \le \min(\text{Open}, \text{Close})$ across 100% of bars (0 violations).
2. **Regular Trading Sessions:**
   - 516 trading days exhibited full regular session volume ($N \ge 100$ M5 bars).
   - Weekend/holiday truncated sessions ($N < 100$ bars) were filtered from daily ATR calculations.
3. **Midday Missing Bar Anomaly in 2023:**
   - The historical data provider exhibited recurring 1-hour midday data gaps in early-to-mid 2023:
     - 60 regular days were missing the `11:55:00 UTC` consensus anchor bar.
     - 62 regular days were missing the `13:55:00 UTC` excursion measurement bar.
     - On these days, neither $\Delta P$ nor $\text{NER}$ could be computed. In strict accordance with the fail-closed protocol, no prices were imputed or interpolated, and these days were marked ineligible.
4. **Missing Entry Bars at 14:05:00 UTC:**
   - On **10 eligible days** with valid NER $\ge 0.320210$, the `14:05:00 UTC` entry bar was absent from the dataset:
     - `2023-03-13`, `2023-03-17`, `2023-04-06`, `2023-04-10`, `2023-04-27`, `2023-05-05`, `2023-06-13`, `2023-06-20`, `2023-07-17`, `2023-07-27`.
   - Adhering to the frozen fail-closed specification, trade entries were never assumed or shifted to arbitrary future bars. These 10 trades were skipped fail-closed (0 fill, 0 PnL).
   - Consequently, out of 87 eligible exhaustion days, exactly **77 trades were executed** (participation rate = 88.51%).

---

## 5. Prior-Day ATR20 Calculation & Zero Look-Ahead Audit

1. Daily True Range was computed from regular calendar daily bars:
   $$\text{TR}_d = \max(\text{High}_d - \text{Low}_d, |\text{High}_d - \text{Close}_{d-1}|, |\text{Low}_d - \text{Close}_{d-1}|)$$
2. Trailing 20-day ATR was shifted by 1 full day: `atr20_prior = atr20.shift(1)`.
3. On day $t$, `atr20_prior` reflects price action exclusively through day $t-1$. No current-day price information leaked into the excursion normalization.

---

## 6. Data Integrity Audit Verdict

```
DATA INTEGRITY AUDIT: PASS
- Authorized Evaluation Partition: 2023–2024 (132,927 M5 bars)
- Protected Holdouts (2025 Val / 2026 Test): 100% UNTOUCHED
- Prior-Use Disclosure: TRANSPARENTLY DOCUMENTED
- Fail-Closed Protocols: FULLY ENFORCED (10 MISSING ENTRY BARS SAFELY SKIPPED)
- Look-Ahead Leakage: ZERO DETECTED
```
