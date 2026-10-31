# DATA INTEGRITY & GOVERNANCE REPORT: PHASE 24

**Phase:** 24 — New Hypothesis Discovery & Pre-Registration  
**Repository:** `Treading-Ai`  
**Execution Timestamp:** 2026-10-30T03:48:00 UTC  
**Environment:** Linux (Python 3.14.4)  

---

## 1. Governance Directives & Partition Protection

Phase 24 establishes strict data governance and partition isolation protocols for all future evaluation of hypothesis `HYP-24-NY-REVERSAL-EXHAUSTION`:

1. **Authorized Development Partition:** Only the verified 2021–2022 processed M5 dataset may be utilized for threshold estimation ($\theta_{\text{exhaustion}}$) and exploratory modeling in Phase 25.
2. **Prior-Use Disclosure for 2023–2024:** The 2023–2024 dataset was previously accessed in Phases 19–20 (macro research) and Phase 23 (Asian-London breakout evaluation). It is disclosed as **not globally pristine**.
3. **Protected Validation & Test Partitions:** The 2025 validation (`val.parquet`) and 2026 test (`test.parquet`) partitions remain **100% untouched, locked, and unqueried**. Under no circumstances may they be loaded during exploratory research.

---

## 2. Dataset Inventory & Cryptographic Checksums

### 2.1 Authorized Development Data (2021–2022)

| File Name | Absolute Path | Rows | Size | SHA-256 Checksum |
| :--- | :--- | :--- | :--- | :--- |
| **XAUUSD_M5_2021.parquet** | `data/processed/XAUUSD/M5/XAUUSD_M5_2021.parquet` | 70,686 | ~1.6 MB | `f4888b0e722b60fc60f813711fcd80ba26d24698482cfb37da560ec27647ca3e` |
| **XAUUSD_M5_2022.parquet** | `data/processed/XAUUSD/M5/XAUUSD_M5_2022.parquet` | 70,928 | ~1.6 MB | `ee56686d8ad690af6b283c237a45944c65f8625eb414136447ae4e9b5a771350` |
| **Total Development Partition** | — | **141,614** | — | **Permitted for Phase 25 Development** |

- **Development Timestamps:** `2021-01-03 23:00:00+00:00` to `2022-12-30 21:55:00+00:00` UTC.

### 2.2 Locked Out-of-Sample Partition (2023–2024)

| File Name | Absolute Path | Rows | Size | SHA-256 Checksum |
| :--- | :--- | :--- | :--- | :--- |
| **XAUUSD_M5_2023.parquet** | `data/processed/XAUUSD/M5/XAUUSD_M5_2023.parquet` | 61,794 | ~1.4 MB | `4b0a461b598ff7ef0491a077523daf9e24009c86677270f90a1a318a4b862c77` |
| **XAUUSD_M5_2024.parquet** | `data/processed/XAUUSD/M5/XAUUSD_M5_2024.parquet` | 71,133 | ~1.9 MB | `1aa6027334f1bb7801be12553368e7420007fd6e2b0e20d26dcacd28076657d0` |
| **Total Out-of-Sample Partition** | — | **132,927** | — | **Reserved for Phase 26 Validation** |

- **Out-of-Sample Timestamps:** `2023-01-02 23:00:00+00:00` to `2024-12-31 21:55:00+00:00` UTC.

### 2.3 Protected Partitions (2025–2026)

| Partition | Absolute Path | Expected SHA-256 | Actual SHA-256 | Audit Status |
| :--- | :--- | :--- | :--- | :--- |
| **Validation (2025)** | `data/features/XAUUSD_M5_features_val.parquet` | `7e9222e9dc0893601e24505912eeab78330670c4e70ebcc2fa462ff8d44a4f94` | `7e9222e9dc0893601e24505912eeab78330670c4e70ebcc2fa462ff8d44a4f94` | **UNMODIFIED** |
| **Test (2026)** | `data/features/XAUUSD_M5_features_test.parquet` | `f95fd09a5d07666e3f1d9a72e840e2e97f3c058d11b6bb0c712b21dea86a5dec` | `f95fd09a5d07666e3f1d9a72e840e2e97f3c058d11b6bb0c712b21dea86a5dec` | **UNMODIFIED** |

---

## 3. Leakage Prevention & Methodological Controls

1. **Chronological Splits:**
   - Development Phase 25 will strictly load rows where `timestamp < 2023-01-01 00:00:00 UTC`.
   - Out-of-sample Phase 26 will strictly load rows where `2023-01-01 <= timestamp < 2025-01-01 UTC`.
   - Fail-closed runtime checks will be embedded in all loader modules.
2. **Look-Ahead Prevention:**
   - Baseline price $P_{\text{base}}$ is anchored strictly at the completed `11:55` UTC bar close.
   - Excursion magnitude $\Delta P$ is evaluated strictly at the completed `13:55` UTC bar close.
   - Entry occurs at the next bar Open (`14:00` or `14:05` UTC Open).
   - $\text{ATR}_{20}$ uses completed daily bars shifted by 1 full day (`shift(1)`).
3. **No-Overlap Labeling:**
   - At most one trade per calendar day is permitted.
   - Positions exit by `18:30:00 UTC`, ensuring zero inter-day or inter-trade serial correlation overlap.
