# DATA INTEGRITY & GOVERNANCE REPORT: PHASE 23

**Phase:** 23 — Locked Out-of-Sample Evaluation  
**Hypothesis ID:** `HYP-21-ASIAN-LONDON-EXPANSION`  
**Execution Timestamp:** 2026-10-30T03:27:15 UTC  
**Evaluation Partition:** 2023-01-01 to 2024-12-31 UTC  

---

## 1. Partition Inventory & Cryptographic Hashes

The evaluation dataset was constructed strictly from the processed M5 parquet files for 2023 and 2024 located in `data/processed/XAUUSD/M5/`.

| Partition File | File Path | Row Count | File Size | SHA-256 Checksum |
| :--- | :--- | :--- | :--- | :--- |
| **XAUUSD_M5_2023.parquet** | `data/processed/XAUUSD/M5/XAUUSD_M5_2023.parquet` | 61,794 | ~1.4 MB | `4b0a461b598ff7ef0491a077523daf9e24009c86677270f90a1a318a4b862c77` |
| **XAUUSD_M5_2024.parquet** | `data/processed/XAUUSD/M5/XAUUSD_M5_2024.parquet` | 71,133 | ~1.9 MB | `1aa6027334f1bb7801be12553368e7420007fd6e2b0e20d26dcacd28076657d0` |
| **Total Evaluation Bars** | — | **132,927** | — | **Verified 2023–2024 Partition** |

### Timestamp Range Verification:
- **Earliest Timestamp:** `2023-01-02 23:00:00+00:00`
- **Latest Timestamp:** `2024-12-31 21:55:00+00:00`
- **Lower Fail-Closed Boundary:** `2023-01-01 00:00:00+00:00` (Passed: `min_ts >= 2023-01-01`)
- **Upper Fail-Closed Boundary:** `2025-01-01 00:00:00+00:00` (Passed: `max_ts < 2025-01-01`)

---

## 2. Cryptographic Verification of Protected Datasets

The repository's protected validation (2025) and test (2026) feature datasets were independently audited prior to evaluation:

| Protected Partition | File Path | Expected SHA-256 | Actual SHA-256 | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Validation (2025)** | `data/features/XAUUSD_M5_features_val.parquet` | `7e9222e9dc0893601e24505912eeab78330670c4e70ebcc2fa462ff8d44a4f94` | `7e9222e9dc0893601e24505912eeab78330670c4e70ebcc2fa462ff8d44a4f94` | **UNMODIFIED** |
| **Test (2026)** | `data/features/XAUUSD_M5_features_test.parquet` | `f95fd09a5d07666e3f1d9a72e840e2e97f3c058d11b6bb0c712b21dea86a5dec` | `f95fd09a5d07666e3f1d9a72e840e2e97f3c058d11b6bb0c712b21dea86a5dec` | **UNMODIFIED** |

Neither file was opened, queried, or modified. Zero bars from 2025 or 2026 entered the evaluation.

---

## 3. Mandatory Prior-Use Disclosure

> [!IMPORTANT]
> **Prior-Use Disclosure:**  
> The 2023–2024 partition was previously utilized in Phase 19 (macro data acquisition) and Phase 20 (macro hypothesis testing on daily XAUUSD returns). While 2023–2024 is strictly out-of-sample relative to the development of `HYP-21-ASIAN-LONDON-EXPANSION` (which used only 2021–2022 data), **it is not globally pristine**. This partition must not be treated as virgin data for multiple hypothesis testing adjustments.

---

## 4. Critical Data Hygiene & Gap Discovery

During data audit, structural properties of the 132,927 M5 bars were analyzed:

1. **High/Low Invariant:** Verified that $\text{High} \ge \max(\text{Open}, \text{Close})$ and $\text{Low} \le \min(\text{Open}, \text{Close})$ across 100% of rows (0 violations).
2. **Midday Missing Bar Anomaly:**  
   On four distinct trading days in early 2023, the data provider exhibited an unannounced 1-hour gap between 11:00 and 12:00 UTC:
   - `2023-03-08`: Bars missing from 11:00:00 to 11:55:00 UTC (12 bars absent).
   - `2023-03-09`: Session truncated after 10:55:00 UTC (bars absent through rest of day).
   - `2023-04-13`: Bars missing from 11:00:00 to 11:55:00 UTC (12 bars absent).
   - `2023-04-14`: Bars missing from 11:00:00 to 11:55:00 UTC (12 bars absent).

### Forensic Impact of the Gap Anomaly:
Because the bar timestamped `11:55:00` UTC was missing on these days, the backtesting engine's fallback logic (`LAST_AVAILABLE_BAR_EXIT`) did not trigger at midday. Instead, the engine held positions through the entire New York afternoon until the end of the day (`20:55` or `23:55` UTC). 

This unintended holding interval crossed the 21:00/22:00 UTC daily rollover window and Friday close. Forensically, these 4 trades generated +$62.96/oz in gross PnL. When positions are strictly capped at the last bar $\le 11:55$ UTC (10:55:00 UTC), their gross PnL drops to +$1.38/oz. This anomaly is fully accounted for in the statistical and audit reports.
