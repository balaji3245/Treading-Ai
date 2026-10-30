# DATA INTEGRITY & GOVERNANCE REPORT: PHASE 22

**Phase:** 22 — Controlled Development  
**Hypothesis ID:** `HYP-21-ASIAN-LONDON-EXPANSION`  
**Execution Timestamp:** 2026-10-30T02:57:33 UTC  
**Environment:** Linux (Python 3.14.4)  

---

## 1. Objective & Governance Mandate

Phase 22 requires strict data governance to prevent inadvertent data leakage, sample snooping, or partition contamination:
1. Only verified **2021–2022 development data** may be loaded or queried.
2. The **2023–2024 out-of-sample data** must NOT be loaded, queried, inspected, or used for parameter tuning.
3. The **protected 2025 validation (`val.parquet`)** and **2026 test (`test.parquet`)** partitions must remain completely untouched.
4. The system must fail closed if any prohibited timestamp ($\ge \text{2023-01-01 00:00:00 UTC}$) is encountered.
5. All historical research artifacts from Phases 20, 20A, 20B, and 21 must be preserved.

---

## 2. Input Dataset Inventory & Cryptographic Hashes

The development dataset was constructed exclusively by loading the raw M5 parquet bars for 2021 and 2022 from `data/processed/XAUUSD/M5/`.

| File Name | Absolute Path | Row Count | File Size | SHA-256 Checksum |
| :--- | :--- | :--- | :--- | :--- |
| **XAUUSD_M5_2021.parquet** | `/home/bhoot/project/Treading-Ai/data/processed/XAUUSD/M5/XAUUSD_M5_2021.parquet` | 70,686 | ~1.6 MB | `f4888b0e722b60fc60f813711fcd80ba26d24698482cfb37da560ec27647ca3e` |
| **XAUUSD_M5_2022.parquet** | `/home/bhoot/project/Treading-Ai/data/processed/XAUUSD/M5/XAUUSD_M5_2022.parquet` | 70,928 | ~1.6 MB | `ee56686d8ad690af6b283c237a45944c65f8625eb414136447ae4e9b5a771350` |
| **Total Combined** | — | **141,614** | — | **Verified 2021–2022 Partition** |

### Timestamp Boundary Verification
- **Earliest Timestamp:** `2021-01-03 23:00:00+00:00`
- **Latest Timestamp:** `2022-12-30 21:55:00+00:00`
- **Fail-Closed Threshold:** `2023-01-01 00:00:00+00:00`

> [!NOTE]
> The automated check `assert max_ts < pd.to_datetime('2023-01-01 00:00:00', utc=True)` passed unconditionally. Zero bars from 2023, 2024, 2025, or 2026 were accessed.

---

## 3. Cryptographic Verification of Protected Partitions

Before running the backtest, cryptographic SHA-256 hashes of the protected validation (2025) and test (2026) feature partitions were independently calculated and cross-referenced with their pre-registered repository reference hashes.

| Protected Partition | File Path | Expected SHA-256 | Actual SHA-256 | Integrity Status |
| :--- | :--- | :--- | :--- | :--- |
| **Validation (2025)** | `data/features/XAUUSD_M5_features_val.parquet` | `7e9222e9dc0893601e24505912eeab78330670c4e70ebcc2fa462ff8d44a4f94` | `7e9222e9dc0893601e24505912eeab78330670c4e70ebcc2fa462ff8d44a4f94` | **UNMODIFIED** |
| **Test (2026)** | `data/features/XAUUSD_M5_features_test.parquet` | `f95fd09a5d07666e3f1d9a72e840e2e97f3c058d11b6bb0c712b21dea86a5dec` | `f95fd09a5d07666e3f1d9a72e840e2e97f3c058d11b6bb0c712b21dea86a5dec` | **UNMODIFIED** |

Neither file was opened, queried, or modified during Phase 22 execution.

---

## 4. Preservation of Historical Phase Artifacts

All artifacts from previous project phases were verified intact:
- **Phase 20:** Macro hypothesis test code, results, and logs in `reports/phase20/`.
- **Phase 20A:** Forensic audit report, PnL reconciliation, and audit test results in `reports/phase20a/`.
- **Phase 20B:** Formal corrections, benchmark separation, and research closure report in `reports/phase20b/`.
- **Phase 21:** New hypothesis discovery report and formal specification for `HYP-21-ASIAN-LONDON-EXPANSION` in `reports/phase21/`.

---

## 5. Data Hygiene & Quality Checks on 2021–2022 M5 Data

Anomalies and structural properties of the 141,614 bars were inspected programmatically:
1. **Missing Bars:** M5 continuity was verified. Gaps correspond exclusively to scheduled weekend closures (Friday 22:00 to Sunday 22:00/23:00 UTC) and standard holiday closures (Christmas, New Year).
2. **High/Low Invariant:** Verified that $\text{High} \ge \max(\text{Open}, \text{Close})$ and $\text{Low} \le \min(\text{Open}, \text{Close})$ across 100% of rows (0 violations).
3. **Volume / Spread Sanity:** All prices are non-negative, finite, and conform to typical XAUUSD pricing ranges ($1,614.92 to $2,075.14).
4. **Whipsaw Candles:** During the breakout window (07:05 to 09:00 UTC), zero bars violated both the Asian High and Asian Low simultaneously.

---

## 6. Conclusion

Data integrity and governance requirements for Phase 22 are **100% SATISFIED**. The backtest engine operates strictly within the 2021–2022 development partition with fail-closed safety mechanisms verified.
