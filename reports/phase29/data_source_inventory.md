# Phase 29 Data Source Inventory & Current Repository Assets

**Phase:** 29 — Data Acquisition Plan, Provider Evaluation & Cost Architecture  
**Instrument:** XAUUSD (Spot Gold / US Dollar) & CME Gold Futures (`GC`)  
**Auditor:** Quantitative Research Infrastructure Engineer & Cloud Cost Auditor  
**Date:** October 2026  
**Status:** COMPLETE & VERIFIED  

---

## Executive Summary

Following the Phase 28 audit verdict (`IMPROVE DATA FIRST`), this document provides a comprehensive technical inventory of all existing market data assets, ingestion pipelines, storage schemas, and cloud infrastructure within the `Treading-Ai` repository.

### Key Inventory Findings:
1. **Existing Price Data:** Sourced exclusively from HistData.com M1 ASCII files, aggregated into multi-timeframe Parquet partitions (M1, M5, M15, M30, H1, H4) covering 2021 through 2024 (and sealed 2025/2026 partitions).
2. **Missing Essential Fields:** 
   - Quotes represent **single-price Bid quotes only**; simultaneous Ask quotes and bid-ask spreads are completely absent ($0\%$ coverage).
   - The `volume` series is **100.0% zero** across all 141,614 bars in the 2021–2022 development partition. Tick volume, traded contract volume, and order-book depth do not exist.
3. **Macro Data Assets:** Three daily macroeconomic series (10Y Real Yield `DFII10`, Broad USD Index `DTWEXBGS`, and 10Y Breakeven Inflation `T10YIE`) are fetched from the Federal Reserve Bank of St. Louis (FRED) and stored in `data/raw/macro/`.
4. **Resampling Architecture:** `src/treading_ai/preprocessing/resampler.py` implements an alignment-aware resampling engine that constructs M5, M15, M30, H1, and H4 candles with explicit session anchoring to 22:00 UTC (17:00 NY close).
5. **AWS / Cloud Footprint:** Currently **zero**. The repository contains no AWS configuration files, credentials, `~/.aws` profiles, or active cloud resources. All compute and storage are 100% local.

---

## 1. Inventory of Existing Historical Market Data

### A. Processed Parquet Datasets (`data/processed/XAUUSD/`)

The repository stores processed market data in Apache Parquet format (snappy compressed) partitioned by timeframe and year:

```
+-------------------------------------------------------------------------------------------------------------------+
|                                     EXISTING MARKET DATASET INVENTORY                                             |
+-----------+--------------------+----------------+----------------------+--------------------+---------------------+
| Timeframe | Calendar Coverage  | File Count     | Approx. Row Count    | Total Disk Size    | Governance Partition|
+-----------+--------------------+----------------+----------------------+--------------------+---------------------+
| M1        | 2021-01 to 2026-05 | 10 Parquet files| ~1,850,000 bars      | ~45.0 MB           | Dev, Val, Test      |
| M5        | 2021-01 to 2026-05 | 10 Parquet files| ~380,000 bars        | ~9.8 MB            | Dev, Val, Test      |
| M15       | 2021-01 to 2026-05 | 10 Parquet files| ~127,000 bars        | ~3.4 MB            | Dev, Val, Test      |
| M30       | 2021-01 to 2026-05 | 10 Parquet files| ~63,500 bars         | ~1.8 MB            | Dev, Val, Test      |
| H1        | 2021-01 to 2026-05 | 10 Parquet files| ~31,800 bars         | ~1.1 MB            | Dev, Val, Test      |
| H4        | 2021-01 to 2026-05 | 10 Parquet files| ~7,950 bars          | ~348 KB            | Dev, Val, Test      |
+-----------+--------------------+----------------+----------------------+--------------------+---------------------+
```

*Note: In strict compliance with governance rules, the 2025 Validation (`val.parquet`) and 2026 Test (`test.parquet`) partitions remain crypographically sealed and uninspected.*

### B. Development Partition Data Schema (2021–2022)

```text
Column Name     Storage Type         Verified Semantic Reality
-------------   ------------------   --------------------------------------------------------------
timestamp       datetime64[us, UTC]  Standard UTC timestamp indicating the start of the candle.
open            float64              Bid Open price from HistData feed.
high            float64              Bid High price during the candle.
low             float64              Bid Low price during the candle.
close           float64              Bid Close price at the end of the candle.
volume          float64              CONSTANT 0.0 (100.0% zeros). Entirely unusable.
bar_count       int32                Number of constituent M1 bars aggregated into this candle.
is_complete     bool                 True if constituent M1 count matches expected session length.
```

---

## 2. Inventory of Macroeconomic Assets (`data/raw/macro/`)

The repository contains three daily benchmark macroeconomic series fetched directly from the Federal Reserve Bank of St. Louis (FRED):

```
+-------------------------------------------------------------------------------------------------------------------+
|                                       MACROECONOMIC DATA ASSETS                                                   |
+----------+-------------------------------------------------------+-------------+-------------+--------------------+
| Series ID| Series Description                                    | Frequency   | Date Range  | Observation Count  |
+----------+-------------------------------------------------------+-------------+-------------+--------------------+
| DFII10   | 10-Year Treasury Inflation-Indexed Security (Real Yld)| Daily       | 2003 – 2026 | 6,214 observations |
| DTWEXBGS | Nominal Broad U.S. Dollar Index (Trade-Weighted)     | Daily (Bus.)| 2006 – 2026 | 5,430 observations |
| T10YIE   | 10-Year Breakeven Inflation Rate                      | Daily       | 2003 – 2026 | 6,215 observations |
+----------+-------------------------------------------------------+-------------+-------------+--------------------+
```

- **Provenance:** Documented in [acquisition_metadata.json](file:///home/bhoot/project/Treading-Ai/data/raw/macro/acquisition_metadata.json).
- **Licensing:** Public Domain (U.S. Government work / FRED API terms).
- **Research Utility:** Excellent for identifying macro interest rate regimes and real-yield trends on H4/Daily horizons.

---

## 3. Existing Ingestion & Processing Scripts

The repository contains modular, well-tested Python components for data acquisition and transformation:

### 1. `scripts/download_data.py` & `src/treading_ai/data_collection/downloader.py`
- Automates retrieval of monthly and annual zip archives from `HistData.com`.
- Extracts ASCII CSV files into `data/raw/`.
- Writes JSON metadata recording SHA-256 hashes, source URLs, and file sizes.

### 2. `scripts/process_timeframes.py` & `src/treading_ai/preprocessing/resampler.py`
- Ingests raw M1 CSV files.
- Converts fixed Eastern Standard Time (EST = UTC-5) to UTC timestamps.
- Performs deterministic deduplication if identical timestamps are encountered.
- Validates OHLC integrity invariants ($H \ge \max(O, C)$, $L \le \min(O, C)$, positive prices).
- Aggregates M1 bars into M5, M15, M30, H1, and H4 candles.
- Supports session-aligned H4 resampling anchored to 22:00 UTC (17:00 NY close), preventing candle splits across the daily rollover break.

### 3. `src/treading_ai/preprocessing/storage.py`
- Manages Parquet file serialization using `pyarrow`.
- Embeds standardized schema metadata (source, symbol, timeframe, timezone).

### 4. `scripts/acquire_macro_data.py`
- Downloads daily macroeconomic indicators from FRED with automated cryptographic checksum verification.

---

## 4. Current Data Limitations & Technical Deficiencies

As audited in Phase 28, the existing dataset imposes four structural barriers to quantitative research:

```
+---------------------------------------------------------------------------------+
|                       CURRENT DATA LIMITATION SUMMARY                           |
+-------------------+--------------------+----------------------------------------+
| Dimension         | Current Status     | Research Failure Mode                  |
+-------------------+--------------------+----------------------------------------+
| Bid / Ask Quotes  | 0% Ask Quotes      | Backtests execute at synthetic midpoint|
|                   | Single Bid series  | Conceals real spread at entry/exit.    |
+-------------------+--------------------+----------------------------------------+
| Volume            | 100% Zeros         | VWAP, volume profile, liquidity flow,  |
|                   | No tick volume     | and absorption models are impossible.  |
+-------------------+--------------------+----------------------------------------+
| Market Depth      | 0% Depth           | Market impact, slippage curves, and    |
|                   | No Level 2 / DOM   | queue delay cannot be modeled.         |
+-------------------+--------------------+----------------------------------------+
| Timeframe Noise   | M5 Dominance       | Intraday moves ($0.44/oz) are crushed  |
|                   | SNR < 0.06%        | by $0.25–$0.50/oz transaction friction.|
+-------------------+--------------------+----------------------------------------+
```

---

## 5. Existing AWS & Cloud Infrastructure Audit

A comprehensive inspection of the repository and environment confirmed:
- **AWS Profiles:** `~/.aws/` does **not exist**.
- **Environment Variables:** No `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, or `AWS_DEFAULT_REGION` are defined.
- **Python Dependencies:** Neither `boto3`, `botocore`, nor `s3fs` are installed in the active virtual environment (`.venv/`) or listed in `requirements.txt`.
- **Active Cloud Resources:** **Zero**. The project operates strictly on local Linux compute.
- **Documented Cloud Budget:** No AWS budget, cloud credits, or cloud billing records are documented in the repository.

### Infrastructure Finding:
Any cloud infrastructure proposed for Phase 29 must be designed from scratch with strict zero-cost local defaults and non-committal budget boundaries.
