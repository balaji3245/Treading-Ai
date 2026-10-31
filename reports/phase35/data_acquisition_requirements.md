# Phase 35: Confirmatory Market Data Acquisition Requirements

**Document Type:** Technical Specification & Vendor-Neutral Acquisition Checklist  
**Author:** Senior Quantitative Research Auditor & Financial Data Governance Engineer  
**System:** Treading-Ai (XAUUSD Research-Only)  
**Date:** November 2026  
**Status:** DRAFT FOR STAKEHOLDER REVIEW  

---

## 1. Executive Summary & Objective

Phase 34 established that no verified independent confirmatory dataset currently exists in the Treading-Ai workspace to evaluate the Phase 33 swing hypotheses. To enable future Mode B Confirmatory Research without compromising project governance, this document defines a rigorous, vendor-neutral data acquisition specification.

### Mandatory Directives:
1. **Zero Provider Endorsement:** No external data provider is certified or assumed compliant without physical, verified proof.
2. **Zero Financial Outlay / Zero Download:** This specification is planning and documentation only. No data was purchased, downloaded, or ingested in Phase 35 ($0.00 spent).
3. **Institutional Standards:** Any candidate dataset evaluated for acquisition must pass 100% of the mandatory criteria detailed below.

---

## 2. Vendor-Neutral Technical Acquisition Checklist

The following 8-category checklist defines the minimum operational, mathematical, and legal requirements for an independent XAUUSD market data feed:

| Category | Technical Specification | Mandatory Criteria | Disqualifying Defects |
| :--- | :--- | :--- | :--- |
| **1. Historical Coverage & Timestamps** | Temporal depth and resolution | • Continuous coverage across at least 3 to 5 full calendar years.<br>• M1 bar resolution or tick-level bid/ask timestamps.<br>• Monotonically increasing, ISO-8601 UTC timestamps with millisecond or second precision. | • Less than 3 full years of data.<br>• Unordered or duplicate timestamps.<br>• Unspecified or ambiguous timezone formatting. |
| **2. Bid & Ask / Spread Data** | True market liquidity and crossing friction | • Explicit, simultaneous Bid and Ask prices for every bar or tick.<br>• Realized spread history capturing volatility widening and market rollover expansion. | • Single synthetic mid-price or bid-only price series.<br>• Zero-spread assumptions.<br>• Unrecorded spread spikes during news releases. |
| **3. Missing Data & Gap Transparency** | Feed reliability and auditability | • Complete source-feed gap logs and server disconnect documentation.<br>• Defensible methodology distinguishing low-liquidity quiet minutes from network outages. | • Silent synthetic imputation or forward-filling of missing sessions without metadata.<br>• Unexplained multi-hour dropouts during peak market sessions. |
| **4. Timezone, DST, & Session Metadata** | Calendar and session boundary fidelity | • Documented session boundary rules (e.g. 17:00 NY close).<br>• Explicit calendar defining scheduled exchange/broker market closures and maintenance breaks.<br>• Deterministic handling of US Eastern Standard Time (EST) vs Eastern Daylight Time (EDT) shifts. | • Constant fixed UTC offset assuming no DST.<br>• Absence of documentation regarding holiday closures or daily rollover halts. |
| **5. Provenance & Reproducibility** | Data custody and cryptographic verification | • Verifiable institutional source (regulated exchange, Tier-1 ECN, or major bullion dealer).<br>• Immutable raw archive with published SHA-256 cryptographic hashes.<br>• Deterministic, reproducible extraction and parsing pipeline. | • Anonymous, unverified web aggregators.<br>• Inability to reproduce byte-level extracts from source archives.<br>• Ambiguous quote aggregation methods. |
| **6. Licensing & Legal Governance** | Permitted research and commercial use | • Transparent terms of service explicitly granting rights for quantitative research, backtesting, and model development.<br>• Perpetual archival rights for research replication and academic/audit verification. | • Restrictive non-commercial licenses prohibiting automated data storage or reprocessing.<br>• Unclear redistribution or intellectual property terms. |
| **7. Cost & Acquisition Budget** | Financial governance and cost sustainability | • Transparent, predictable fee structure (open-source public domain, academic research grant, or one-time fee).<br>• Zero recurring subscription dependencies that violate workstation self-sufficiency. | • Mandatory cloud hosting or proprietary vendor lock-in.<br>• Hidden per-query or egress fees. |
| **8. Infrastructure Compatibility** | Integration with Treading-Ai engine | • Direct parseability to standard tabular formats (Parquet, Arrow, CSV).<br>• Compatibility with `treading_ai/resampler.py` and `MultiTimeframeSwingPipeline`.<br>• Compatible volume semantics (tick volume or real contract volume). | • Proprietary binary formats requiring closed-source SDKs.<br>• Incompatible schema requiring destructive pipeline redesign. |

---

## 3. Analysis of Candidate Market Data Architectures

To assist future acquisition planning, four structural data architectures are compared below:

```
+------------------------------------+--------------------------+----------------------------+-----------------------------+
| Architecture                       | Spread & Cost Fidelity   | Calendar & Session Clarity | Acquisition & Storage Cost  |
+------------------------------------+--------------------------+----------------------------+-----------------------------+
| 1. True ECN Tick Data              | Exceptional              | Variable                   | High storage (~50 GB/yr);   |
|    (e.g. Dukascopy / LMAX)         | (Real Bid/Ask ticks)     | (Broker-specific calendar) | Free/Low cost               |
+------------------------------------+--------------------------+----------------------------+-----------------------------+
| 2. Regulated Futures Data          | Superior                 | Authoritative              | Requires paid licensing;    |
|    (CME COMEX Gold Futures GC)     | (Centralized order book) | (Official CME schedule)    | Contract stitching overhead |
+------------------------------------+--------------------------+----------------------------+-----------------------------+
| 3. Historical Pre-2021 OTC M1 Data | Poor                     | Unverified                 | Low storage (<2 GB/yr);     |
|    (e.g. HistData 2015–2020)       | (Bid-only, 0 volume)     | (No published calendar)    | Free public download        |
+------------------------------------+--------------------------+----------------------------+-----------------------------+
| 4. Broker Daily/H4 Bar Feeds       | Inadequate               | Low                        | Minimal storage (<50 MB);   |
|    (MetaTrader broker exports)     | (No intra-bar path)      | (Opaque broker rules)      | Low reliability             |
+------------------------------------+--------------------------+----------------------------+-----------------------------+
```

### Critical Architecture Insights:
1. **The Intraday Path Requirement:** Swing trading evaluation on H4 bars requires M1 or tick-level underlying data to resolve intra-bar path dependency (determining whether Stop Loss or Take Profit occurred first). Daily or H4-only datasets (Architecture 4) are mathematically disqualified.
2. **The Spread Dilemma:** Publicly available free M1 datasets (Architecture 3) provide only a single price series (synthetic bid or mid) with zero spread. Simulating realistic swing execution requires either real tick Bid/Ask feeds (Architecture 1) or a rigorously calibrated spread model based on historical volatility.
3. **The Futures Alternative:** CME COMEX Gold Futures (Architecture 2) provide an authoritative exchange calendar and real transaction volume, but introduce roll yields, quarterly expiry stitching, and paid commercial data licensing costs.

---

## 4. Evidentiary Categorization

### Verified Facts:
- No data meeting all 8 checklist categories currently exists in the project workspace outside of previously evaluated partitions and protected holdouts.
- Free HistData M1 feeds fail Category 2 (lack bid/ask spreads) and Category 4 (lack an authoritative session/holiday calendar).
- Phase 35 incurred $0.00 in spending and initiated zero external downloads.

### Assumptions:
- It is assumed that acquiring a compliant dataset under Architecture 1 (Dukascopy ECN tick) or Architecture 2 (CME futures) is technically feasible in a future funded phase.

### Recommendations:
1. Maintain strict adherence to the checklist; do not acquire or ingest any dataset that fails Category 1, Category 4, or Category 5.
2. Prioritize data sources that provide authentic, simultaneous Bid and Ask quotes to eliminate synthetic spread assumptions.
3. Await explicit stakeholder budget and governance authorization before initiating any data acquisition phase.
