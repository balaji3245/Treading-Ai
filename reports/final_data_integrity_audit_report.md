# Final Data-Integrity Audit Report: Treading-AI Phase 1

**Audit Execution Date**: 2026-10-28T18:38:00Z  
**Target Instrument**: XAU/USD (Spot Gold)  
**Historical Period Audited**: 2021-01-03 to 2026-10-23  
**Final Verdict**: **CONDITIONAL PASS**  

---

## 1. Verified Historical Periods and Candle Counts

All requested raw archives have been downloaded, unzipped, and verified on local disk with SHA-256 cryptographic hashes and ZIP CRC-32 integrity checks. Original raw files in `data/raw/` remain 100% bitwise untouched.

| Period | Format | Status | CSV Rows (M1) | Size | SHA-256 Hash | UTC Timestamp Range |
| :--- | :---: | :---: | :---: | :---: | :--- | :--- |
| **2021** | Annual ZIP | `VERIFIED` | 353,446 | 22.25 MB | `d819ff95bfd37c8621fe22765d7fe4eb67440498b0451cfbf15c614b14e6eeb2` | 2021-01-03 23:00 to 2021-12-31 21:58 |
| **2022** | Annual ZIP | `VERIFIED` | 354,628 | 22.32 MB | `bf411f17616ea15a9ff9408b0313a48e895ec0f663fc90a6e60b9435caeb65d3` | 2022-01-02 23:00 to 2022-12-30 21:57 |
| **2023** | Annual ZIP | `VERIFIED` | 308,812 | 19.44 MB | `74c909dc31bb95aa6395ec6060c2aa2d59be7fe34c97ea83c18c5e638971f1bc` | 2023-01-02 23:00 to 2023-12-29 21:57 |
| **2024** | Annual ZIP | `VERIFIED` | 355,652 | 22.39 MB | `03dec44d896173b069d27f8a846f488691500f40d4ce7c10b27b3d37a858ff53` | 2024-01-01 23:00 to 2024-12-31 21:57 |
| **2025** | Annual ZIP | `VERIFIED` | 354,011 | 22.28 MB | `1b302280d4679eeec5aeead17bc384b66df825b42d6c1b3f6f1947e4521782e4` | 2025-01-01 23:00 to 2025-12-31 21:57 |
| **2026_01** | Monthly ZIP | `VERIFIED` | 28,827 | 1.81 MB | `4c162eec9d3381a1bb7270e599aa7f8dfce8d745a305e9ca15b172a6b29f7993` | 2026-01-01 23:00 to 2026-01-30 21:58 |
| **2026_02** | Monthly ZIP | `VERIFIED` | 27,429 | 1.73 MB | `8bc7ee80145be8429fa8a0bb38f292d3c90e0b3c65c69781682708fb180630fc` | 2026-02-01 23:06 to 2026-02-27 21:58 |
| **2026_03** | Monthly ZIP | `VERIFIED` | 30,595 | 1.93 MB | `4bfc42a1d820d82992d9d9f9a46dc1db32fa89b21f3f4c6b249e0a6d0ee3c042` | 2026-03-01 23:00 to 2026-04-01 04:58 |
| **2026_04** | Monthly ZIP | `VERIFIED` | 28,976 | 1.82 MB | `d11647ce8f5a2f58e1f57ce5625bf3ba9a101f3f38d39e9ce6d2cfa23467f561` | 2026-04-01 05:00 to 2026-05-01 04:58 |
| **2026_05** | Monthly ZIP | `VERIFIED` | 28,822 | 1.81 MB | `b3420ff39f50669d67b223ffc8bc0eb7bb2c88f117c06eb695781a70cc3bc4f7` | 2026-05-01 05:00 to 2026-06-01 04:58 |
| **2026_06** | Monthly ZIP | `QUARANTINED` | 30,144 | 1.90 MB | `dc6c524ef6d9620b2297eb06fe73e343a41c2c54cb432e39958dc1d053704efc` | 2026-06-01 05:00 to 2026-07-01 04:58 |
| **2026_07** | Monthly ZIP | `QUARANTINED` | 31,414 | 1.98 MB | `7e3767433cfa5cff86e74659b8a1c97a5ee2fc0be73fe01b31a221f7e0293121` | 2026-07-01 05:00 to 2026-07-31 21:58 |
| **2026_08** | Monthly ZIP | `QUARANTINED` | 29,437 | 1.85 MB | `fe8fde1f64244f777e5fc70cf7e2f5b66d400e9323df061dc11c7576a086da36` | 2026-08-02 23:00 to 2026-09-01 04:58 |
| **2026_09** | Monthly ZIP | `QUARANTINED` | 29,321 | 1.85 MB | `522b95f74656ca895420364998aafe98e7ee72f3e5e40786f0a39088ff45fcf3` | 2026-09-01 05:00 to 2026-10-01 04:58 |
| **2026_10** | Monthly ZIP | `QUARANTINED` | 23,416 | 1.47 MB | `2a113f40114090400b9a67bb1d97779d8c9735a1fffae2ff2b1448b15e47fbdf` | 2026-10-01 05:00 to 2026-10-23 21:58 |

- **Total Ingested Raw M1 Candlesticks**: **2,014,930 rows**
- **Verified Clean M1 Candlesticks (Production Parquet)**: **1,870,898 rows** (2021 through 2026_05)

---

## 2. Missing or Unavailable Periods

- **2026_11 (November 2026)**: Verified `UNAVAILABLE` on source. HistData download token `tk=""` is empty because November 2026 has not concluded.
- **2026_12 (December 2026)**: Verified `UNAVAILABLE` on source. HistData download token `tk=""` is empty because December 2026 has not concluded.
- **Monthly downloads for 2021–2025**: HistData's operational rule packages completed years exclusively as consolidated annual archives; individual months for completed years return empty tokens and are serviced via the annual archive.

---

## 3. Duplicate Timestamp Forensic Investigation

### 2025 Dataset Analysis (`DAT_ASCII_XAUUSD_M1_2025.csv`)
- **Total Duplicate Rows**: 120 (60 pairs)
- **Unique Duplicate Timestamps**: 60 (from `20251026 190000` to `20251026 195900` EST)
- **Identical Rows**: **60 pairs** (100% bitwise identical Open, High, Low, Close, Volume)
- **Conflicting Rows**: **0 pairs**
- **Occurrence Indices**: Block 1 (rows 290113–290172), Block 2 (rows 290173–290232)
- **Root Cause**: On Sunday, October 26, 2025, European Daylight Saving Time ended at 01:00 UTC (clock fell back 1 hour). The server recording the feed repeated the 19:00:00 to 19:59:00 EST window.
- **Multi-Year Pattern**: Cross-year audit of 2021, 2022, 2023, 2024, and 2025 revealed this exact 60-candle identical repetition in EVERY single annual archive on the last Sunday of October (Oct 31 2021, Oct 30 2022, Oct 29 2023, Oct 27 2024, Oct 26 2025). In all 5 years, Conflicting = 0, Identical = 60.
- **Deterministic Downstream Policy**: In `process_timeframes.py`, when `--clean-duplicates` is passed, the pipeline asserts that `conflicting_duplicates_count == 0`. If any conflicting prices are detected, execution strictly aborts. If all duplicates are 100% identical, duplicate instances are removed with `keep='first'` and sorted chronologically, preserving raw CSVs untouched.

### 2026 H2 Monthly Extracts (`2026_06` through `2026_10`)
- **Discovery**: Unlike the clean annual archives, recent preliminary monthly extracts for 2026 contain raw feeder anomalies with conflicting duplicate timestamps:
  - 2026_06: 26 conflicting timestamp pairs
  - 2026_07: 264 conflicting timestamp pairs
  - 2026_08: 98 conflicting timestamp pairs
  - 2026_09: 344 conflicting timestamp pairs
  - 2026_10: 289 conflicting timestamp pairs
- **Quantitative Action**: As per strict financial data engineering standards ("Do not silently remove conflicting rows"), months 2026_06 through 2026_10 are safely **quarantined** in raw storage and excluded from production Parquet datasets until HistData releases its consolidated annual archive or a deterministic multi-source price reconciliation rule is approved.

---

## 4. Processed Data Verification by Timeframe

Multi-timeframe Parquet datasets generated for production periods (2021, 2022, 2023, 2024, 2025, 2026_01–2026_05) using session-aligned H4 anchoring (`offset='2h'`):

| Timeframe | Candles | Complete | Incomplete | Nulls | Infinities | Non-Positive | Inversions | Duplicates | Status |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **M1** | 1,870,898 | 1,870,898 | 0 | 0 | 0 | 0 | 0 | 0 | **PASS** |
| **M5** | 374,288 | 373,873 | 415 | 0 | 0 | 0 | 0 | 0 | **PASS** |
| **M15** | 124,770 | 124,388 | 382 | 0 | 0 | 0 | 0 | 0 | **PASS** |
| **M30** | 62,390 | 62,031 | 359 | 0 | 0 | 0 | 0 | 0 | **PASS** |
| **H1** | 31,209 | 30,876 | 333 | 0 | 0 | 0 | 0 | 0 | **PASS** |
| **H4** | 8,358 | 6,454 | 1,904 | 0 | 0 | 0 | 0 | 0 | **PASS** |

### Leakage and Incomplete Candle Validation
- **No Lookahead Leakage**: Verified that higher timeframe bars contain strictly constituent candles in `[T, T + timeframe)`. Prices at `T + timeframe` are never leaked into the preceding bar (regression test `test_no_lookahead_leakage`).
- **Incomplete Candles Explicitly Flagged**: Bars truncated by market closures (e.g. daily roll break at 22:00 UTC or Friday weekend close) are marked with `is_complete=False` and tracked with exact `bar_count`.
- **Reproducibility**: Re-resampling and Parquet serialization verified bitwise identical across consecutive runs (`audit_reproducibility` status: `PASS`).

---

## 5. Automated Tests and Results

### Test Suite Execution
- **Command**: `PYTHONPATH=src .venv/bin/pytest -v tests/`
- **Result**: **27 PASSED** in 0.36 seconds
- **Breakdown**:
  - `tests/test_downloader.py`: 9 passed (URL generation, token extraction, unavailable periods, raw CSV metadata, mocked monthly pipeline, mocked annual archive, cache hits, HTTP retries, corrupt ZIP detection).
  - `tests/test_orchestrator.py`: 1 passed (Multi-period coverage synchronization and report generation).
  - `tests/test_resampler.py`: 7 passed (OHLCV math, all timeframes, incomplete candle detection, non-fabrication of empty periods, invalid timeframe rejection, H4 session alignment, lookahead leakage prevention).
  - `tests/test_storage.py`: 3 passed (Parquet round-trip, column projection, chunked streaming).
  - `tests/test_validator.py`: 7 passed (Clean data, anomaly detection, direct gap classification, multi-timeframe gap classification, dataframe gap classification, report serialization, identical vs conflicting duplicate regression test).

### Mocked vs Live Verification Distinction
- **Unit/Regression Tests (Mocked / Synthetic)**: All 27 tests in `tests/` execute against deterministic synthetic data and mocked HTTP fixtures. They run offline in CI/CD without network access.
- **Source-Download Verification (Live)**: Conducted via `scripts/sync_data.py` and `scripts/audit_data_integrity.py` connecting live to `histdata.com`. Verified 15 real archives, validating HTTP response tokens, ZIP structures, CSV record parsing, and SHA-256 hashes against actual broker quotes.

---

## 6. Remaining Risks

1. **Bid-Only Quotations**: HistData XAUUSD quotes reflect Bid prices only. Backtesting models must account for a dynamic Bid-Ask spread (typically $0.15–$0.35 in liquid market hours).
2. **Zero Volume Metric**: HistData removes broker-specific volume (`volume = 0`). Future feature engineering must not rely on raw volume without secondary source enrichment.
3. **2026 H2 Raw Quarantined Months**: Months 2026_06 through 2026_10 remain quarantined due to uncleaned preliminary broker feed duplicates. 5.5 years of clean verified data (2021–2026_05: 1.87M M1 bars) are immediately available for feature engineering.

---

## 7. Final Verdict

### **CONDITIONAL PASS**

- **Historical Coverage**: **PASS** (15 periods downloaded, CRC/SHA verified, 2 unreleased future periods proven unavailable).
- **Duplicate Forensics**: **PASS** (100% identical DST duplicates proven across 2021–2025; raw files preserved untouched; conflicting duplicate protection enforced).
- **Multi-Timeframe Data Integrity**: **PASS** (1,870,898 clean M1 bars and all derived timeframes verified with 0 errors, 0 nulls, 0 inversions).
- **Automated Tests**: **PASS** (27/27 unit/regression tests passing).
- **Condition**: Raw monthly datasets `2026_06` through `2026_10` must remain quarantined from model training until HistData's consolidated annual archive is released or an approved multi-quote reconciliation rule is applied.
