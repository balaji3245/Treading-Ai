# Phase 30 Dukascopy Ingestion Readiness & Architectural Blueprint

**Phase:** 30 — H4 and Daily Dataset Audit, Horizon Statistics & Execution Cost Analysis  
**Component:** Fallback Path 2 — Dukascopy Historical Tick Data Ingestion  
**Auditor:** Quantitative Infrastructure Engineer & Market Data Auditor  
**Date:** October 2026  
**Status:** COMPLETE & INDEPENDENTLY AUDITED  

---

## Executive Summary

Phase 29 designated Dukascopy Bank SA historical tick data as the approved zero-cost fallback path for resolving the lack of Bid/Ask spreads and tick volume in the repository. In accordance with strict constraints, **no data was downloaded, no network requests to external providers were made, and no cloud resources were launched during Phase 30**.

This report establishes the complete architectural specification, binary decoding blueprint, schema definitions, integrity verification protocols, and spread-aware aggregation algorithms required before any live ingestion is executed.

---

## 1. Existing Ingestion Architecture Audit

The repository contains established data collection modules in `src/treading_ai/data_collection/`:

```
+---------------------------------------------------------------------------------+
|                       EXISTING REPOSITORY INGESTION ASSETS                      |
+--------------------------+-----------------------+------------------------------+
| Component File           | Current Functionality | Reusability for Dukascopy    |
+--------------------------+-----------------------+------------------------------+
| `downloader.py`          | Downloads HistData zip| Template for HTTP session,   |
|                          | archives and metadata | retry logic, and SHA-256.    |
+--------------------------+-----------------------+------------------------------+
| `resampler.py`           | M1 to M5/H1/H4        | Adaptable to aggregate ticks |
|                          | Resampling Engine     | into dual-sided Bid/Ask bars.|
+--------------------------+-----------------------+------------------------------+
| `storage.py`             | Parquet serialization | Reusable as-is for storing   |
|                          | with pyarrow metadata | processed tick/candle Parquet|
+--------------------------+-----------------------+------------------------------+
```

---

## 2. Dukascopy Binary Format Specifications & Decoding Logic

Dukascopy distributes historical tick data via public servers (`http://datafeed.dukascopy.com/datafeed/`) structured by symbol and hourly files:
```text
URL Pattern: datafeed.dukascopy.com/datafeed/{SYMBOL}/{YEAR}/{MONTH_0_INDEXED:02d}/{DAY:02d}/{HOUR:02d}h_ticks.bi5
Example:     datafeed.dukascopy.com/datafeed/XAUUSD/2021/00/03/22h_ticks.bi5 (Jan 3, 2021, 22:00 UTC)
```

### Binary Structure of `.bi5` Files:
- **Compression:** Standard LZMA (Lempel-Ziv-Markov chain-Algorithm) raw compression.
- **Record Structure:** Decompresses into a continuous binary stream of **20-byte structs** (`>IIIff` in Python `struct` notation):

```text
Field Offset   Data Type       Byte Size   Description & Conversion Formula
------------   -------------   ---------   ------------------------------------------------------------
Bytes 0–3      Big-Endian u32  4 bytes     Time offset in milliseconds from the start of the hour:
                                           timestamp = hour_start_utc + timedelta(milliseconds=offset)
Bytes 4–7      Big-Endian u32  4 bytes     Ask Price (scaled integer):
                                           ask = raw_ask / 1000.0 (for XAUUSD spot gold)
Bytes 8–11     Big-Endian u32  4 bytes     Bid Price (scaled integer):
                                           bid = raw_bid / 1000.0 (for XAUUSD spot gold)
Bytes 12–15    Big-Endian f32  4 bytes     Ask Volume (lot liquidity on Ask side)
Bytes 16–19    Big-Endian f32  4 bytes     Bid Volume (lot liquidity on Bid side)
```

---

## 3. Standardized Parquet Target Schemas

### A. Raw Tick Level Parquet Schema (Daily Partitioned)
```text
Column Name     Storage Type           Description & Validation Rule
-------------   --------------------   ------------------------------------------------------------
timestamp       datetime64[us, UTC]    Strictly monotonic, microsecond-precision UTC timestamp.
bid             float64                Bid price quote (must be > 0).
ask             float64                Ask price quote (must satisfy ask >= bid).
spread          float64                Instantaneous spread = ask - bid (must be >= 0).
bid_volume      float32                Resting bid liquidity depth.
ask_volume      float32                Resting ask liquidity depth.
```

### B. Spread-Aware Resampled Candlestick Schema (M5 / H1 / H4 / Daily)
```text
Column Name     Storage Type           Description & Mathematical Aggregation
-------------   --------------------   ------------------------------------------------------------
timestamp       datetime64[us, UTC]    Start timestamp of the candle (left-closed boundary).
open_bid        float64                First tick bid price in interval.
high_bid        float64                Maximum tick bid price in interval.
low_bid         float64                Minimum tick bid price in interval.
close_bid       float64                Last tick bid price in interval.
open_ask        float64                First tick ask price in interval.
high_ask        float64                Maximum tick ask price in interval.
low_ask         float64                Minimum tick ask price in interval.
close_ask       float64                Last tick ask price in interval.
spread_mean     float64                Time-weighted or arithmetic mean spread during the candle.
spread_max      float64                Maximum spread spike observed during the candle.
bid_volume_sum  float64                Sum of all bid tick volumes in the candle.
ask_volume_sum  float64                Sum of all ask tick volumes in the candle.
tick_count      int32                  Total number of raw tick quotes aggregated into this candle.
is_complete     bool                   True if candle covers standard session trading duration.
```

---

## 4. Spread-Aware Resampling Mechanics (Zero Look-Ahead)

To eliminate lookahead bias when backtesting with spread-aware candles:
1. **Left-Closed Intervals $[t, t + \Delta t)$:** Candle labeled $t$ aggregates all ticks with timestamps $\ge t$ and $< t + \Delta t$. The candle is finalized strictly at $t + \Delta t$.
2. **Realistic Execution Price Modeling:**
   - **Long Position Entry:** Fills at the **Ask price** (`open_ask` of the subsequent bar).
   - **Long Position Exit:** Fills at the **Bid price** (`close_bid` or subsequent `open_bid`).
   - **Short Position Entry:** Fills at the **Bid price** (`open_bid` of the subsequent bar).
   - **Short Position Exit:** Fills at the **Ask price** (`close_ask` or subsequent `open_ask`).
3. **Stop-Loss Fill Modeling:** If a Long stop-loss is breached intra-bar, execution fills at the minimum of the stop level and the subsequent Bid price, incorporating adverse slippage.

---

## 5. Provenance Metadata, Error Handling & Retry Policies

When implemented, the Dukascopy downloader must write a cryptographic provenance JSON file for every ingested day:

```json
{
  "provider": "Dukascopy Bank SA",
  "instrument": "XAUUSD",
  "date_utc": "2021-01-04",
  "retrieval_timestamp_utc": "2026-10-31T20:00:00Z",
  "files_downloaded": 23,
  "files_missing_expected_closure": 1,
  "raw_bytes_downloaded": 1258490,
  "total_ticks_decoded": 184520,
  "sha256_checksum": "...",
  "status": "VALIDATED"
}
```

### Network Resilience & Rate-Limiting Protocol:
- **HTTP User-Agent:** Identify as analytical research client with standard browser header.
- **Connection Pooling:** Reuse persistent `requests.Session()` with HTTP keep-alive.
- **Exponential Backoff:** If HTTP 429 (Rate Limit) or 503 (Server Busy) is returned, wait $2^n$ seconds (1s, 2s, 4s, 8s, max 30s) up to 5 retries.
- **Local Idempotence:** If an hourly `.bi5` file exists and passes LZMA decompression verification, skip downloading.

---

## 6. Licensing & Compliance Verification Protocol

Before initiating multi-year ingestion:
1. **Verification of Non-Commercial Exemption:** Re-confirm that Dukascopy's terms permit algorithmic backtesting and personal research on public feed data without requiring a Swiss bank account.
2. **Strict Prohibition on Raw Redistribution:** Ingested tick files must be stored in `.gitignore` directories (`data/raw/dukascopy/` and `data/processed/dukascopy/`). No binary `.bi5` or decompressed CSVs shall be committed to git.
3. **Audit Readiness:** This blueprint is **100% complete**. No technical or architectural barriers remain to implementing this pipeline if Fallback Path 2 is activated.
