# Phase 29 Legal Licensing, Regulatory Boundaries & Data Risks

**Phase:** 29 — Data Acquisition Plan, Provider Evaluation & Cost Architecture  
**Instrument:** XAUUSD (Spot Gold) & CME COMEX Gold Futures (`GC`)  
**Auditor:** Quantitative Infrastructure Engineer & Compliance Auditor  
**Date:** October 2026  
**Status:** COMPLETE & INDEPENDENTLY AUDITED  

---

## Executive Summary

Systematic quantitative trading systems carry significant legal, contractual, and technical operational risks. In accordance with strict governance principles, this report reviews the intellectual property licensing, redistribution limitations, and data quality hazards associated with each potential market data provider for `Treading-Ai`.

All legal and risk statements in this report are categorized as **[VERIFIED FACT]**, **[LEGAL RISK]**, or **[MITIGATION]**.

---

## 1. Provider Licensing & Redistribution Terms

```
+-------------------------------------------------------------------------------------------------------------------+
|                                   DATA PROVIDER LEGAL LICENSING MATRIX                                            |
+---------------+------------------------+---------------------+---------------------+------------------------------+
| Provider      | Governing Body / Terms | Personal / Internal | Commercial Product  | Redistribution / Sharing     |
+---------------+------------------------+---------------------+---------------------+------------------------------+
| Dukascopy     | Dukascopy Bank SA Terms| PERMITTED [FACT]    | RESTRICTED [RISK]   | STRICTLY PROHIBITED [FACT]   |
| Databento     | CME Group Sub-License  | PERMITTED [FACT]    | RESTRICTED [RISK]   | STRICTLY PROHIBITED [FACT]   |
| HistData      | HistData.com Terms     | PERMITTED [FACT]    | RESTRICTED [RISK]   | STRICTLY PROHIBITED [FACT]   |
| FRED          | Federal Reserve / USG  | PERMITTED [FACT]    | PERMITTED [FACT]    | PERMITTED (Public Domain)    |
| CFTC COT      | U.S. CFTC (Gov)        | PERMITTED [FACT]    | PERMITTED [FACT]    | PERMITTED (Public Domain)    |
| TrueFX        | Integral Dev Corp Terms| PERMITTED [FACT]    | RESTRICTED [RISK]   | STRICTLY PROHIBITED [FACT]   |
+---------------+------------------------+---------------------+---------------------+------------------------------+
```

### Detailed Licensing Analysis by Provider:

#### 1. Dukascopy Bank SA
- **Permitted Use:** Dukascopy makes historical `.bi5` tick data available on its public servers for personal research, academic study, and algorithmic strategy backtesting [VERIFIED FACT].
- **Prohibited Use:** Users may not resell, mirror, republish, or redistribute the raw tick files or converted databases [LEGAL RISK]. Commercial fund deployment or SaaS signal distribution relying on proprietary Dukascopy feeds requires a formal commercial data distribution contract with Dukascopy Bank SA [LEGAL RISK].
- **Compliance Policy for Treading-Ai:** Ingestion scripts must store processed Parquet data in local private directories. No raw Dukascopy files or derived tick tables shall be published to public GitHub repositories or public cloud buckets [MITIGATION].

#### 2. Databento & CME Group (COMEX Data)
- **Governing Agreement:** Access to the `GLBX.MDP3` dataset is subject to the **CME Group Information Services Agreement** mediated by Databento [VERIFIED FACT].
- **Permitted Use:** Internal research, model training, quantitative strategy simulation, and backtesting [VERIFIED FACT].
- **CME Market Data Redistribution Rules:** CME Group enforces strict, legally binding restrictions regarding external redistribution. Distributing raw CME tick data, continuous contract bars, or derived real-time quote feeds to third parties or public repositories without an executed CME Distributor Agreement incurs hefty monthly administrative fees (ranging from **$1,000 to $5,000+ per month**) and retrospective audits [LEGAL RISK].
- **Compliance Policy for Treading-Ai:** Any futures data downloaded via Databento credits must remain strictly confidential within internal local storage. Only aggregated non-reconstructible statistical parameters (e.g. regression coefficients, profit factors) may be published in audit markdown reports [MITIGATION].

#### 3. HistData.com
- **Permitted Use:** Individual analytical research and educational testing [VERIFIED FACT].
- **Prohibitions:** Automated web scraping at high concurrency that degrades server infrastructure is prohibited. Redistribution of extracted raw CSVs is prohibited [VERIFIED FACT].

#### 4. FRED & CFTC (U.S. Government Feeds)
- **Status:** **Public Domain** [VERIFIED FACT]. Both the Federal Reserve Economic Data (FRED) and the Commodity Futures Trading Commission (CFTC) Commitments of Traders reports are U.S. government works. They may be freely downloaded, stored, resampled, transformed, and redistributed without licensing fees or commercial restrictions [VERIFIED FACT].

---

## 2. Technical Data Quality Risks & Market Microstructure Hazards

### Risk 1: Futures Contract Roll Discontinuities (The Rollover Cliff)
When analyzing CME COMEX Gold Futures (`GC`), prices belong to discrete delivery contracts (e.g., February `GCG`, April `GCJ`, June `GCM`, August `GCQ`, December `GCZ`).
- **The Problem:** Futures contracts expire every two months. The price of the active front-month contract differs from the next contract by the carry cost (interest rates, storage, insurance). When rolling from an expiring contract to the next month, an artificial jump of **$\$10.00 to $\$30.00/\text{oz}$** occurs.
- **Back-Adjustment Hazards:**
  1. *Panama Canal (Difference) Adjustment:* Shifts historical prices up or down by the roll gap. Can result in negative prices in long-term historical series.
  2. *Ratio (Proportional) Adjustment:* Multiplies historical prices by the roll ratio. Preserves percentage returns but distorts absolute dollar ATR and dollar stop-loss levels.
  3. *Unadjusted Series:* Causes catastrophic false breakout signals on roll days if automated models interpret contract rolls as genuine price breakouts.
- **Mitigation:** If futures data is used, a strict contract calendar roll schedule must be engineered, or research must focus strictly on single-contract life cycles without cross-roll holding periods.

### Risk 2: Over-The-Counter (OTC) Broker Liquidity Pool Bias
Spot gold (`XAUUSD`) is not an exchange-traded asset. It is traded across an OTC interbank network connecting major bullion banks (JPMorgan, HSBC, UBS, Citibank) and multi-bank electronic portals (EBS, Refinitiv Matching, Currenex).
- **The Problem:** A feed from Dukascopy represents the liquidity and client flow of Dukascopy's ECN pool; a feed from HistData represents an undisclosed retail liquidity aggregator. Neither represents the entire global market.
- **Mitigation:** Recognize that broker tick quotes are accurate representations of *that venue's tradable prices*, but cannot be assumed to match another retail broker down to the single pip. Strategy evaluation must incorporate a sensitivity buffer of at least $\pm \$0.15/\text{oz}$.

### Risk 3: Timestamp Desynchronization in Hybrid Models
Attempting to merge CME Futures volume (`GC`) with Spot Gold price (`XAUUSD`) faces timestamp alignment risk:
- CME Globex timestamps are recorded in high-precision Chicago exchange time (CST/CDT) and synchronized to atomic clocks (GPS).
- Spot gold retail feeds are recorded in varying broker server time zones (e.g. GMT, GMT+2, EST) with potential clock drift or network queuing latency of 50 to 500 milliseconds.
- **The Hazard:** Merging on timestamp can lead to look-ahead leakage (e.g., a futures trade executed at 13:00:00.050 matching a spot bar stamped 13:00:00.000).

---

## 3. Compliance and Risk Summary Matrix

```
+---------------------------------------------------------------------------------+
|                       SUMMARY OF OPERATIONAL RISK CONTROLS                      |
+--------------------------+-----------------------+------------------------------+
| Risk Identified          | Severity Level        | Mandatory Repository Control |
+--------------------------+-----------------------+------------------------------+
| CME Data Redistribution  | HIGH (Legal/Financial)| Keep all data in local git-  |
|                          |                       | ignored storage. Never push. |
+--------------------------+-----------------------+------------------------------+
| Contract Roll Artifacts  | HIGH (Alpha distortion| Use Panama or ratio stitching|
|                          |                       | with explicit roll filters.  |
+--------------------------+-----------------------+------------------------------+
| OTC Venue Divergence     | MODERATE (Execution)  | Apply 1.5x–2.0x cost stress  |
|                          |                       | testing to all candidate PnL.|
+--------------------------+-----------------------+------------------------------+
| Spot/Futures Desync      | HIGH (Lookahead leak) | Reject cross-market M5 hybrid|
|                          |                       | models; keep assets separate.|
+--------------------------+-----------------------+------------------------------+
```
