# Phase 32 Audit Report: H4 Schedule-Aware Completeness Engine

**Auditor:** Senior Quantitative Software Engineer, Financial Data Engineer, and Time-Series Integrity Auditor  
**Date:** 2026-11-01  
**Project:** Treading-Ai — XAUUSD Research-Only System  
**Audit Scope:** Track B — H4 Completeness Classification & Price Integrity  
**Target Code:** `src/treading_ai/preprocessing/resampler.py:get_h4_scheduled_active_minutes`, `resample_candle_series`  

---

## 1. Executive Summary & Audit Verdict

This audit independently reviewed the Schedule-Aware H4 Completeness Engine implemented in Phase 31.

### Verdict Summary:
- **Completeness Classification:** **PASS (Mathematically & Chronologically Sound)**. The schedule-aware logic correctly recovers 494 legitimate rollover candles (248 in 2021, 246 in 2022) where scheduled active minutes was exactly 180.
- **Selective Recovery Verification:** **PASS (Zero Naive Rule Flaws)**. The engine did **not** blindly mark every 180-bar candle complete. The 4 anomalous 180-bar candles caused by US holiday early closes (July 5, 2021 and Sep 6, 2021) and European DST switch gaps (March 28, 2021 and March 27, 2022) were independently evaluated and strictly maintained as `is_complete=False`.
- **OHLC Price Invariance:** **PASS (100% Exact Numerical Parity)**. Every single Open, High, Low, Close, Volume, and Bar Count value across all 3,086 H4 candles in 2021 and 2022 matches the raw M1 source aggregation with strictly **0.000000000000 deviation**.
- **Completeness Recovery Rate:** Increased H4 complete candle coverage from **81.1% (2,502/3,086)** to **97.1% (2,996/3,086)**, eliminating the artificial 16.1% data dropout on daily rollover transitions.

---

## 2. Track B1: Schedule Logic & Expected Active Duration

### 2.1 The Schedule Calculation Implementation
In `resampler.py`:
```python
@staticmethod
def get_h4_scheduled_active_minutes(start_ts_utc: pd.Timestamp) -> int:
    mins = pd.date_range(start=start_ts_utc, periods=240, freq="1min")
    mins_ny = mins.tz_convert(TZ_NEW_YORK)
    # Daily rollover closure: Mon-Thu 17:00-18:00 NY
    is_roll = (mins_ny.day_of_week < 4) & (mins_ny.hour == 17)
    # Weekend closure: Fri >= 17:00, Sat, Sun < 18:00
    w = mins_ny.day_of_week
    h = mins_ny.hour
    is_wknd = ((w == 4) & (h >= 17)) | (w == 5) | ((w == 6) & (h < 18))
    closed_count = int((is_roll | is_wknd).sum())
    return 240 - closed_count
```

### 2.2 Timezone & Interval Evaluation
1. **Candle Interval:** Each H4 candle represents a left-closed, left-labeled interval $[T_{\text{start}}, T_{\text{start}} + 240\text{m})$.
2. **Local NY Clock Conversion:** Each of the 240 constituent minutes is converted to `America/New_York`. This dynamically accounts for Daylight Saving Time shifts (March and November), ensuring that:
   - In summer (EDT, UTC-4), the 17:00–18:00 NY rollover window falls at 21:00–22:00 UTC.
   - In winter (EST, UTC-5), the 17:00–18:00 NY rollover window falls at 22:00–23:00 UTC.
3. **Rollover Window Spanned:**
   - For a summer candle starting at 18:00 UTC (14:00 NY):
     - The candle spans [18:00, 22:00) UTC = [14:00, 18:00) NY.
     - Active trading: 14:00 to 17:00 NY (180 minutes).
     - Rollover break: 17:00 to 18:00 NY (60 minutes).
     - `closed_count = 60` $\implies$ `expected_active = 180`.
   - For a winter candle starting at 22:00 UTC (17:00 NY):
     - The candle spans [22:00, 02:00) UTC = [17:00, 21:00) NY.
     - Rollover break: 17:00 to 18:00 NY (60 minutes).
     - Active trading: 18:00 to 21:00 NY (180 minutes).
     - `closed_count = 60` $\implies$ `expected_active = 180`.
4. **Standard Active Candles:**
   - Candles at 02:00, 06:00, 10:00, 14:00 UTC do not intersect scheduled closures.
   - `closed_count = 0` $\implies$ `expected_active = 240`.

---

## 3. Track B2: Selective Recovery vs Missing Data Isolation

To verify that the engine does not blindly declare every 180-bar candle complete, we audited all 498 candles with `bar_count == 180` across 2021 and 2022:

### 3.1 Audit of the 498 180-Bar Candles

| Category | 2021 Count | 2022 Count | Total | Classification | Audit Verification Finding |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Mon–Thu Rollover Candles** | 197 | 198 | **395** | `is_complete = True` | Spanned Mon-Thu 17:00–18:00 NY break. All 180 active minutes observed. |
| **Friday Weekend Close Candles** | 33 | 32 | **65** | `is_complete = True` | Friday 14:00–18:00 NY (market closed at 17:00 NY). All 180 active minutes observed. |
| **Sunday Market Open Candles** | 18 | 16 | **34** | `is_complete = True` | Sunday 17:00–21:00 NY (market opened at 18:00 NY). All 180 active minutes observed. |
| **US Holiday Early Close (July 5)** | 1 | 0 | **1** | `is_complete = False` | July 5, 2021 14:00 UTC (US Independence Day). Truncated active session. |
| **US Holiday Early Close (Sep 6)** | 1 | 0 | **1** | `is_complete = False` | Sep 6, 2021 14:00 UTC (US Labor Day). Truncated active session. |
| **European DST Shift Discrepancy** | 1 | 1 | **2** | `is_complete = False` | March 28, 2021 & March 27, 2022 22:00 UTC (Feeder clock mismatch). |
| **Total 180-Bar Candles** | **251** | **247** | **498** | - | - |

**Critical Audit Proof:** 
- Exactly **494 candles** had `expected_active == 180` and `bar_count == 180` $\implies$ `is_complete = True`.
- Exactly **4 candles** had `expected_active == 240` and `bar_count == 180` $\implies$ `is_complete = False`.
- If a naive rule `bar_count in (180, 240)` had been used, all 4 anomalous candles would have been falsely marked complete. The schedule-aware logic successfully isolated them.

---

## 4. Track B3: OHLC Price Invariance Verification

We performed an independent mathematical audit comparing the H4 dataset generated in Phase 31 against an independent re-aggregation of raw M1 source data:

| Metric | Permitted 2021 H4 Partition | Permitted 2022 H4 Partition | Invariance Status |
| :--- | :--- | :--- | :--- |
| **Total H4 Candles** | 1,539 | 1,547 | Exact Match |
| **Max Open Difference** | 0.000000000000 | 0.000000000000 | 100% Identical |
| **Max High Difference** | 0.000000000000 | 0.000000000000 | 100% Identical |
| **Max Low Difference** | 0.000000000000 | 0.000000000000 | 100% Identical |
| **Max Close Difference**| 0.000000000000 | 0.000000000000 | 100% Identical |
| **Max Volume Difference**| 0.000000000000 | 0.000000000000 | 100% Identical |
| **Max Bar Count Diff** | 0 | 0 | 100% Identical |
| **`is_complete` Differences** | 0 | 0 | 100% Identical |

**Finding:** The H4 price time series was uncorrupted by the completeness correction.

---

## 5. Track B4: False-Positive & False-Negative Risk Analysis

### 5.1 False-Positive Completeness Risk
- **Definition:** An incomplete or corrupt candle erroneously flagged as `is_complete=True`.
- **Evaluation:**
  - If 1 or more minutes are missing during an active session, `bar_count < expected_active` $\implies$ `is_complete = False`.
  - If a rollover candle has only 179 bars (1 minute dropout during the 3 active hours), `179 == 180` is False $\implies$ `is_complete = False`.
  - If an unscheduled holiday early close occurs during a candle where 240 minutes was expected, `expected_active` is calculated as 240 $\implies$ `is_complete = False`.
- **Risk Level:** **Extremely Low (Conservative)**.

### 5.2 False-Negative Completeness Risk
- **Definition:** A valid trading candle erroneously flagged as `is_complete=False`.
- **Evaluation:**
  - A standard 240-minute active candle that has 239 bars because a single quiet minute had no trades is flagged `is_complete = False`.
  - While mathematically strict, this is consistent with the project's zero-tolerance definition of completeness across all timeframes (M5, M15, M30, H1).
- **Risk Level:** **Low (Strict Invariant Preserved)**.

---

## 6. Audit Findings & Corrective Action Matrix

| Finding ID | Severity | File / Function | Description | Impact | Recommended Corrective Action |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **B-01** | Low | `resampler.py:get_h4_scheduled_active_minutes` | Calculates scheduled closure dynamically on each call via `pd.date_range`. Runtime is ~0.55s per year. | Minor performance overhead during bulk backtest resampling. | Pre-compute or cache standard session start hours in UTC (e.g., set expected minutes by hour in NY time). Not urgent. |
| **B-02** | Low | `resampler.py:resample_candle_series` | Lacks an explicit holiday calendar integration in `get_h4_scheduled_active_minutes`. | Correctly marks holiday early closes as incomplete (conservative). | Maintain current conservative behavior; holiday early closes *should* be flagged incomplete. |

**Track B Final Decision:** **PASS** (Schedule-aware logic is mathematically verified, zero false positives detected, and OHLC data is 100% intact).
