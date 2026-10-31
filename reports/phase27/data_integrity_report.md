# PHASE 27: DATA INTEGRITY & PARTITION GOVERNANCE REPORT

**Phase:** 27 — New Hypothesis Discovery & Research Design  
**Instrument:** XAUUSD (Spot Gold / US Dollar), M5 Timeframe  
**Execution Timestamp:** 2026-10-30T13:15:00 UTC  
**Baseline Git Commit:** `5038d33e4ff7e76d7f8d308da0b9b76132bfdc82`  

---

## 1. Executive Data Governance Mandate

Phase 27 enforces strict data partitioning rules to maintain scientific validity:
1. **Authorized Development Partition:** Only 2021–2022 historical M5 data from `data/processed/XAUUSD/M5/` is authorized for hypothesis generation, parameter estimation, and initial development backtesting.
2. **Prior-Use Disclosure:** 2023–2024 data was previously utilized in Phase 19–20 macro research, Phase 23 London breakout evaluation, and Phase 26 NY reversal evaluation. It is disclosed as non-pristine and is NOT used for exploratory discovery.
3. **Protected Holdouts (2025 & 2026):**
   - 2025 Validation Partition (`val.parquet`) remains strictly locked and untouched.
   - 2026 Test Holdout Partition (`test.parquet`) remains strictly locked and untouched.
4. **Fail-Closed Enforcement:** All data loading pipelines programmatically halt if any timestamp $\ge \text{2023-01-01 00:00:00 UTC}$ is present in the development pipeline.

---

## 2. Ingested Datasets & Cryptographic Checksums

### 2.1 Authorized Development Data Inventory (2021–2022)

| Dataset | Relative File Path | Row Count | File Size | SHA-256 Checksum |
| :--- | :--- | :--- | :--- | :--- |
| **XAUUSD M5 2021** | `data/processed/XAUUSD/M5/XAUUSD_M5_2021.parquet` | 70,686 | ~1.7 MB | `f4888b0e722b60fc60f813711fcd80ba26d24698482cfb37da560ec27647ca3e` |
| **XAUUSD M5 2022** | `data/processed/XAUUSD/M5/XAUUSD_M5_2022.parquet` | 70,928 | ~1.9 MB | `ee56686d8ad690af6b283c237a45944c65f8625eb414136447ae4e9b5a771350` |
| **Total Development** | Combined 2021–2022 Dataset | **141,614** | ~3.6 MB | *Verified chronological continuity* |

### 2.2 Chronological Boundaries
- **Earliest Development Timestamp:** `2021-01-03 23:00:00+00:00 UTC`
- **Latest Development Timestamp:** `2022-12-30 21:55:00+00:00 UTC`
- **Fail-Closed Boundary Assertion:** `max_timestamp < 2023-01-01 00:00:00 UTC` $\implies$ **PASSED**.

### 2.3 Cryptographic Verification of Protected Holdout Partitions

Cryptographic SHA-256 hashes of the protected holdout stores were computed before and after execution:

| Partition | Storage Path | Expected SHA-256 | Actual SHA-256 | Integrity Status |
| :--- | :--- | :--- | :--- | :--- |
| **Validation 2025 (`val.parquet`)** | `data/features/XAUUSD_M5_features_val.parquet` | `7e9222e9dc0893601e24505912eeab78330670c4e70ebcc2fa462ff8d44a4f94` | `7e9222e9dc0893601e24505912eeab78330670c4e70ebcc2fa462ff8d44a4f94` | **100% UNTOUCHED** |
| **Test 2026 (`test.parquet`)** | `data/features/XAUUSD_M5_features_test.parquet` | `f95fd09a5d07666e3f1d9a72e840e2e97f3c058d11b6bb0c712b21dea86a5dec` | `f95fd09a5d07666e3f1d9a72e840e2e97f3c058d11b6bb0c712b21dea86a5dec` | **100% UNTOUCHED** |

Neither file was opened, queried, or modified. Zero bars from 2025 or 2026 entered Phase 27.

---

## 3. Data Hygiene, Quality & Operational Bar Audits

1. **High/Low Invariant:** Verified $\text{High} \ge \max(\text{Open}, \text{Close})$ and $\text{Low} \le \min(\text{Open}, \text{Close})$ across 100% of bars (0 violations).
2. **Duplicate Timestamps:** 0 duplicate timestamps detected in the 141,614 rows.
3. **Timezone Convention:** All timestamps are strictly in Coordinated Universal Time (UTC), completely independent of regional Daylight Saving Time (DST) shifts.
4. **Regular Trading Sessions:**
   - 515 calendar days contained regular full trading volume ($N \ge 100$ M5 bars).
   - Partial weekend sessions (Sunday open 23:00–23:55 UTC, $N < 100$ bars) were filtered from daily ATR calculations.
5. **Operational Bars Presence in Development:**
   - Asian session boundaries (00:00 to 07:00 UTC): Complete across 495 regular trading days.
   - European open bars (08:00 to 09:00 UTC): Complete across 495 regular trading days.
   - LBMA PM Fix bars (14:00 to 15:05 UTC): Complete across 495 regular trading days.
   - COMEX pit close bars (18:25 to 18:30 UTC): Complete across 495 regular trading days.
   - Evening drift bars (18:30 to 21:55 UTC): Complete across 495 regular trading days.

---

## 4. Prior-Day Volatility Benchmark Integrity (Zero Look-Ahead)

1. Daily True Range was computed from regular calendar daily bars:
   $$\text{TR}_d = \max(\text{High}_d - \text{Low}_d, |\text{High}_d - \text{Close}_{d-1}|, |\text{Low}_d - \text{Close}_{d-1}|)$$
2. Trailing 20-day ATR was shifted by 1 full day: `atr20_prior = atr20.shift(1)`.
3. On day $t$, `atr20_prior` incorporates price action strictly through day $t-1$. No current-day price information is accessible to the strategy signals.

---

## 5. Data Integrity Audit Verdict

```
DATA INTEGRITY AUDIT: PASS
- Authorized Partition: 2021–2022 Development Data (141,614 M5 bars)
- Protected Holdouts (2025 Val / 2026 Test): 100% UNTOUCHED
- Prior-Use Disclosure: FULLY DOCUMENTED FOR 2023–2024
- Look-Ahead Bias: ZERO DETECTED
- Timezone Standard: UTC (DST INDEPENDENT)
```
