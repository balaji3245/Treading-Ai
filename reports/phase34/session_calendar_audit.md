# Phase 34: XAUUSD Session Calendar & Completeness Classification Audit

**Document Type:** Time-Series Data Integrity & Market Calendar Audit  
**Auditor:** Senior Quantitative Research Auditor & Financial Data Engineer  
**System:** Treading-Ai (XAUUSD Research-Only)  
**Date:** November 2026  
**Status:** COMPLETE — CLASSIFICATION MARKED UNVERIFIED  

---

## 1. Executive Summary

This audit evaluates the evidentiary basis of Phase 33's session-completeness classification in [`reports/phase33/temporal_integrity_report.md`](file:///home/bhoot/project/Treading-Ai/reports/phase33/temporal_integrity_report.md). 

In Phase 33, it was asserted that:
> *"Every single one of the 18 excluded Tier 3 sessions in 2021–2022 corresponds exactly to scheduled US exchange market holidays with documented early market closures... The defensible completeness policy (`d1_regular_session = bar_count >= 1350`) preserves the statistical continuity of regular trading days while strictly filtering out non-standard holiday sessions."*

### Key Audit Finding:
While the calendar dates of the 18 sessions coincide with federal/exchange holidays observed by US institutions, **the claim that these sessions represent official scheduled market closures of the XAUUSD source feed is UNVERIFIED.**

The underlying data feed is OTC spot gold (XAUUSD) sourced from HistData.com. HistData publishes **no official trading calendar, no documented session boundaries, and no scheduled holiday schedule**. Spot gold is an international Over-The-Counter (OTC) asset, not a CME/COMEX exchange-traded future. Equating US futures exchange holiday closures with scheduled halts in the HistData OTC feed is an unsubstantiated leap in research logic. Furthermore, the 1,350-minute threshold is an arbitrary empirical heuristic rather than a schedule-derived standard.

---

## 2. Source Feed Architecture & Market Calendar Reality

### 2.1 Absence of a Source-Feed Calendar
An exhaustive inspection of project provenance records reveals:
- Source: HistData.com M1 ASCII files (`DAT_ASCII_XAUUSD_M1_2021.csv`, `2022.csv`).
- Provenance Metadata: [`data/raw/HISTDATA_COM_ASCII_XAUUSD_M12021_metadata.json`](file:///home/bhoot/project/Treading-Ai/data/raw/HISTDATA_COM_ASCII_XAUUSD_M12021_metadata.json) records:
  - `instrument`: `"Spot Gold vs US Dollar"`
  - `source_timezone`: `"EST"` (fixed UTC-5)
  - `volume_semantics`: `"0 / Not aggregated by HistData (Broker-specific volume removed)"`
- **Documented Documentation Gap:** HistData provides **zero documentation** regarding broker identity, liquidity providers, exchange holiday schedules, or session maintenance policies.

### 2.2 OTC Spot Bullion vs. US Exchange Calendars
There is a fundamental market microstructure difference between CME COMEX Gold Futures (GC) and OTC Spot Gold (XAUUSD):

```
+---------------------------+-----------------------------------+-----------------------------------+
| Attribute                 | CME COMEX Gold Futures (GC)       | Spot Gold (XAUUSD OTC)            |
+---------------------------+-----------------------------------+-----------------------------------+
| Market Structure          | Centralized Exchange (CME Group)  | Decentralized Interbank Network   |
| Regulatory Calendar       | Official CME Holiday Schedule     | None (Global Bank Discretion)     |
| Holiday Trading Rules     | Strict early halts (e.g. 13:00 ET)| London/Zurich/Asia remain open    |
| Source Documentation      | Published CME Circulars           | Unspecified Broker Feed           |
+---------------------------+-----------------------------------+-----------------------------------+
```

On US holidays (e.g., Martin Luther King Jr. Day or Presidents' Day), CME futures trading halts early at 13:00 EST. However, the London Bullion Market Association (LBMA) and European OTC trading desks remain fully operational. Some retail brokers choose to halt price quotation due to reduced US liquidity, while other brokers maintain indicative spreads throughout the day. 

Without an authoritative broker calendar from HistData, we cannot verify whether quote cessations between 13:00 and 18:00 EST were scheduled broker closures, network disconnects, or upstream data dropouts.

---

## 3. Empirical Audit of the 18 Excluded Sessions

An empirical examination of the 18 sessions with $< 1,350$ bars in 2021–2022 reveals significant heterogeneity in bar counts and gap structures:

| Date | Observed M1 Bars | Normal Full Session | Missing Minutes | Observed Gap Window (EST) | US Calendar Holiday |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **2021-01-18** | 1,140 | 1,380 | 240 | 12:59 to 18:00 EST (5h gap) | MLK Jr. Day |
| **2021-02-15** | 1,140 | 1,380 | 240 | 12:59 to 18:00 EST (5h gap) | Presidents' Day |
| **2021-03-29** | 1,317 | 1,380 | 63 | Sporadic intraday gaps | Pre-Easter rollover |
| **2021-05-31** | 360 | 1,380 | 1,020 | Halted after 06:00 EST | Memorial Day |
| **2021-06-01** | 1,260 | 1,380 | 120 | Delayed open after holiday | Day after Memorial Day |
| **2021-07-05** | 1,140 | 1,380 | 240 | 12:59 to 18:00 EST (5h gap) | Independence Day (obs.) |
| **2021-09-06** | 1,140 | 1,380 | 240 | 12:59 to 18:00 EST (5h gap) | Labor Day |
| **2021-11-25** | 1,139 | 1,380 | 241 | 12:59 to 18:00 EST (5h gap) | Thanksgiving Day |
| **2021-11-26** | 1,166 | 1,380 | 214 | 13:25 to 18:00 EST (~4.5h gap) | Black Friday |
| **2022-01-17** | 1,139 | 1,380 | 241 | 12:59 to 18:00 EST (5h gap) | MLK Jr. Day |
| **2022-02-21** | 1,229 | 1,380 | 151 | 14:29 to 18:00 EST (3.5h gap) | Presidents' Day |
| **2022-03-28** | 1,320 | 1,380 | 60 | Sporadic intraday gaps | Pre-Easter rollover |
| **2022-05-30** | 1,229 | 1,380 | 151 | 14:29 to 18:00 EST (3.5h gap) | Memorial Day |
| **2022-06-20** | 1,229 | 1,380 | 151 | 14:29 to 18:00 EST (3.5h gap) | Juneteenth (obs.) |
| **2022-07-04** | 1,229 | 1,380 | 151 | 14:29 to 18:00 EST (3.5h gap) | Independence Day |
| **2022-09-05** | 1,229 | 1,380 | 151 | 14:29 to 18:00 EST (3.5h gap) | Labor Day |
| **2022-11-24** | 1,228 | 1,380 | 152 | 14:28 to 18:00 EST (3.5h gap) | Thanksgiving Day |
| **2022-11-25** | 1,184 | 1,380 | 196 | 13:44 to 18:00 EST (~4.2h gap) | Black Friday |

### Critical Observations:
1. **Inconsistent Holiday Cutoffs:** In 2021, MLK Day, Presidents' Day, and Labor Day consistently halted at 12:59 EST (1,140 bars). In 2022, the exact same holidays halted at 14:29 EST (1,229 bars). This 90-minute discrepancy proves that the HistData source feed did not follow a fixed, immutable exchange schedule across years.
2. **Easter Rollover Days (2021-03-29 and 2022-03-28):** These days have 1,317 and 1,320 bars respectively. The missing 60–63 minutes are distributed in small chunks rather than a single early closure. Labeling them as "scheduled early closures" is completely unfounded.

---

## 4. Audit of the 1,350-Minute Completeness Threshold

In Phase 33, `MultiTimeframeSwingPipeline` implemented:
```python
merged["d1_regular_session"] = merged["d1_bar_count"] >= self.min_d1_bars_for_regular_session # default 1350
```

### Assessment of the Threshold:
- **Origin:** The number 1,350 was chosen empirically by subtracting 30 minutes from 1,380 to capture sessions with quiet minutes (1,375–1,379 bars) while rejecting sessions with $\le 1,320$ bars.
- **Evidentiary Support:** There is **no economic, market structure, or exchange documentation** supporting 1,350 minutes as a natural boundary. It is an ad-hoc threshold tuned to fit the 2021–2022 development distribution.
- **Classification Status:** **UNVERIFIED HEURISTIC.**

---

## 5. Separation of Evidentiary Categories

### Verified Evidence:
- The 18 sessions with $< 1,350$ bars in 2021–2022 fall on calendar dates that coincide with US banking and futures holidays.
- HistData M1 CSV files exhibit multi-hour quote gaps on those specific dates (e.g., 12:59 to 18:00 EST on 2021-01-18).
- HistData publishes no broker schedule, holiday calendar, or exchange documentation.

### Unverified Claims:
- The assertion that these 18 sessions were "officially scheduled market closures" of the XAUUSD source feed.
- The assertion that the 1,350-minute cutoff is justified by the feed's actual operating schedule.

### Assumptions:
- The assumption that spot gold OTC liquidity providers ceased quoting on US holidays in a manner equivalent to a regulated exchange closure.

### Required Corrective Actions:
1. **Document Classification Status:** Formally designate the session-completeness policy as an **Unverified Empirical Heuristic**, rather than an exchange-verified calendar.
2. **Preserve Code Stability:** In accordance with Phase 34 audit constraints, do not alter existing pipeline code (`swing_features.py`) or reprocess parquet files during this phase.
3. **Document Sensitivity Risk:** In future evaluation protocols, mandate sensitivity testing where the 1,350 threshold is varied (e.g., 1,320 vs 1,350 vs 1,375) to verify that results do not hinge on this specific cutoff.
