# PHASE 25: DATA INTEGRITY & PARTITION GOVERNANCE REPORT

**Hypothesis ID:** `HYP-24-NY-REVERSAL-EXHAUSTION`  
**Phase:** 25 — Controlled Development Backtest  
**Evaluation Scope:** 2021-01-01 to 2022-12-31 UTC (Development Partition Only)  
**Execution Timestamp:** 2026-10-30T03:45:00 UTC  

---

## 1. Executive Data Governance Mandate

Phase 25 development strictly enforces partition boundaries to prevent data snooping, p-hacking, and out-of-sample data contamination:
1. **Authorized Development Partition:** Only 2021–2022 historical M5 bar data was loaded, transformed, or evaluated.
2. **Prohibited Partitions:**
   - **2023–2024 Data:** Completely unread, unqueried, and uninspected during strategy development and threshold calibration.
   - **2025 Validation Partition (`val.parquet`):** Protected out-of-sample dataset; strictly untouched.
   - **2026 Test Partition (`test.parquet`):** Pristine final holdout dataset; strictly untouched.
3. **Fail-Closed Enforcement:** All data loading pipelines enforce programmatic assertion stops if any timestamp on or after `2023-01-01 00:00:00 UTC` is present.

---

## 2. Input Datasets & Cryptographic File Hashes

### 2.1 Development Data Inventory (2021–2022)

| Dataset | Relative Path | Row Count | File Size | SHA-256 Checksum |
| :--- | :--- | :--- | :--- | :--- |
| **XAUUSD M5 2021** | `data/processed/XAUUSD/M5/XAUUSD_M5_2021.parquet` | 70,686 | ~2.5 MB | `f4888b0e722b60fc60f813711fcd80ba26d24698482cfb37da560ec27647ca3e` |
| **XAUUSD M5 2022** | `data/processed/XAUUSD/M5/XAUUSD_M5_2022.parquet` | 70,928 | ~2.5 MB | `ee56686d8ad690af6b283c237a45944c65f8625eb414136447ae4e9b5a771350` |
| **Total Development** | Combined 2021–2022 Data | **141,614** | ~5.0 MB | *Verified chronological continuity* |

### 2.2 Chronological Boundaries
- **Earliest Timestamp:** `2021-01-03 23:00:00+00:00 UTC`
- **Latest Timestamp:** `2022-12-30 21:55:00+00:00 UTC`
- **Temporal Check:** Max timestamp `< 2023-01-01 00:00:00 UTC` $\implies$ **PASSED (Fail-Closed Check Verified)**

### 2.3 Cryptographic Verification of Protected Partitions

To guarantee zero accidental modification or data leakage, cryptographic SHA-256 hashes of the protected feature stores were computed before and after execution:

| Partition | Expected SHA-256 | Actual Evaluated SHA-256 | Integrity Status |
| :--- | :--- | :--- | :--- |
| **Validation 2025 (`val.parquet`)** | `7e9222e9dc0893601e24505912eeab78330670c4e70ebcc2fa462ff8d44a4f94` | `7e9222e9dc0893601e24505912eeab78330670c4e70ebcc2fa462ff8d44a4f94` | **UNTOUCHED / INTACT** |
| **Test 2026 (`test.parquet`)** | `f95fd09a5d07666e3f1d9a72e840e2e97f3c058d11b6bb0c712b21dea86a5dec` | `f95fd09a5d07666e3f1d9a72e840e2e97f3c058d11b6bb0c712b21dea86a5dec` | **UNTOUCHED / INTACT** |

---

## 3. Data Completeness & Missing Bar Handling

### 3.1 Calendar Day Coverage
- Across the two-year development span (730 calendar days), trading on XAUUSD occurs 5 days per week.
- Total days with M5 market data: **521 days**.
- Days with full regular trading ($N \ge 100$ M5 bars): **495 days**.
- Partial weekend sessions ($N < 100$ bars, e.g. Sunday open 23:00–23:55 UTC): **26 days** (properly excluded from daily ATR computation to prevent volatility distortion).

### 3.2 Key Operational Bar Audits
For each of the 495 regular trading days, the presence of critical protocol bars was audited:
1. **Consensus Anchor Bar (`11:55:00 UTC`):** Present in 495 / 495 days (100.0%).
2. **Excursion Measurement Bar (`13:55:00 UTC`):** Present in 495 / 495 days (100.0%).
3. **Execution Entry Bar (`14:05:00 UTC`):** Present in 495 / 495 days (100.0%).
4. **Pit Close Bar (`18:25:00 UTC`):** Present in 495 / 495 days (100.0%).
5. **Intrabar Window (`14:05` to `18:25`):** 53 bars per day expected; 100% complete across all 124 executed trade days.

### 3.3 Fail-Closed Missing-Bar Protocol
In strict adherence to the frozen protocol, missing bars are never imputed, interpolated, or backfilled. If any critical operational bar is absent on a given trading day:
- If `11:55` or `13:55` bar is missing: NER cannot be calculated $\implies$ Trade status = `SKIPPED_MISSING_DATA` (0 trade executed).
- If `14:05` entry bar is missing: Order cannot fill $\implies$ Trade status = `SKIPPED_MISSING_ENTRY` (0 trade executed).
- If `18:25` exit bar is missing while position is open: Position closes on the last available bar prior to 18:30 UTC $\implies$ Fail-closed liquidation.

---

## 4. Prior-Day ATR20 Calculation & Zero Look-Ahead Audit

The trailing ATR calculation was forensically inspected to confirm zero look-ahead bias:
1. **Daily True Range ($\text{TR}_d$):**
   - Computed from completed calendar daily bars: $\text{TR}_d = \max(\text{High}_d - \text{Low}_d, |\text{High}_d - \text{Close}_{d-1}|, |\text{Low}_d - \text{Close}_{d-1}|)$.
2. **Shift Constraint:**
   - Trailing 20-day simple moving average is shifted by 1 full day: `atr20_prior = atr20.shift(1)`.
   - On day $t$, `atr20_prior[t]` incorporates price action up to day $t-1$ only. The current day's high, low, or close is never accessed.
3. **Warmup Requirement:**
   - The first 20 trading days of 2021 serve as warmup. Trades prior to day 21 are disabled until 20 valid prior daily TR values exist.

---

## 5. Threshold Calibration Integrity

The excursion exhaustion threshold was calibrated strictly on the 2021–2022 development partition:
- Evaluated daily NER sample: $N = 495$ calendar days.
- Mean NER: $0.2458$. Median ($Q_2$) NER: $0.2194$.
- 75th Percentile ($Q_3$):
  $$\theta_{\text{exhaustion}} = 0.320210$$
- In accordance with the pre-registered protocol, this threshold is **frozen permanently**. No re-optimization, tuning, or sliding window recalibration was performed.

---

## 6. Data Integrity Audit Verdict

```
DATA INTEGRITY AUDIT: PASS
- Authorized Partition: 2021–2022 (141,614 M5 bars)
- Protected Partitions (2025 Val / 2026 Test): 100% UNTOUCHED
- 2023–2024 Data: STRICTLY UNINSPECTED DURING DEVELOPMENT
- Fail-Closed Constraints: FULLY VERIFIED
- Look-Ahead Bias: ZERO DETECTED
```
