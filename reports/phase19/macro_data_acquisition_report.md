# Phase 19: Macroeconomic Data Acquisition & Quality Report

**Status:** Completed & Methodologically Verified  
**Date:** October 2026  
**Role:** Quantitative Researcher, Financial Data Engineer, Independent Backtesting Auditor  
**Data Partition Governance:** Strict zero-access enforced for 2025 Validation (`val.parquet`, SHA-256 `7e9222...`) and 2026 Test (`test.parquet`, SHA-256 `f95fd0...`). Only 2021–2024 training data evaluated.  
**Primary Final Verdict:** `DATA ACQUIRED — POINT-IN-TIME LIMITATIONS REMAIN`

---

## Executive Summary

Phase 19 executes the macroeconomic data acquisition and integrity verification specified during Phase 18B. Following the rejection of high-frequency intraday M5 directional strategies due to cost friction ($\sim \$0.60/\text{oz}$ friction vs. $\$2.26/\text{oz}$ median move), this phase acquires the external macroeconomic series required to test daily macro-horizon hypotheses for spot gold (XAUUSD).

All three mandatory macroeconomic series—**US 10-Year Real Yield (`DFII10`)**, **Broad Trade-Weighted US Dollar Index (`DTWEXBGS`)**, and **10-Year Breakeven Inflation Rate (`T10YIE`)**—have been acquired from the official Federal Reserve Bank of St. Louis FRED repository. Raw downloaded files are archived separately from processed datasets with cryptographic SHA-256 checksums.

Gold market data integrity audits confirm **984 institutional daily sessions** across 2021–2024 (standard session = 276 M5 bars). Under a conservative 1-business-day publication lag with holiday forward-fill (limit = 3 days), **984 of 984 gold sessions (100.0%)** have complete macroeconomic coverage, providing an observation-to-feature ratio of **$196.8:1$ for $D \le 5$ pre-specified features**.

However, because FRED daily CSVs omit exact intraday publication timestamps and broad dollar trade weights reflect current-vintage annual revisions rather than point-in-time vintages, the primary verdict is formally rendered as **`DATA ACQUIRED — POINT-IN-TIME LIMITATIONS REMAIN`**.

---

## 1. Mandatory Data Sources & Provenance

### A. Series Identification & Documentation

The three macroeconomic series were retrieved from official Federal Reserve Bank of St. Louis FRED endpoints:

| Series Identifier | Canonical Series Title | Compiling Agency / Source | Frequency | Units | Target Start | Target End | Raw File Name |
| :--- | :--- | :--- | :--- | :--- | :---: | :---: | :--- |
| **`DFII10`** | Market Yield on U.S. Treasury Securities at 10-Year Constant Maturity, Inflation-Indexed | U.S. Department of the Treasury via FRED | Daily | Percent | 2021-01-01 | 2024-12-31 | `DFII10_raw.csv` |
| **`DTWEXBGS`** | Nominal Broad U.S. Dollar Index (Goods and Services Trade-Weighted) | Board of Governors of the Federal Reserve System (H.10) via FRED | Daily (Business Days) | Index Jan 2006 = 100 | 2021-01-01 | 2024-12-31 | `DTWEXBGS_raw.csv` |
| **`T10YIE`** | 10-Year Breakeven Inflation Rate | Federal Reserve Bank of St. Louis / U.S. Treasury via FRED | Daily | Percent | 2021-01-01 | 2024-12-31 | `T10YIE_raw.csv` |

#### Official Documentation References
*   FRED API Documentation: [https://fred.stlouisfed.org/docs/api/fred/](https://fred.stlouisfed.org/docs/api/fred/)
*   `DFII10` Series Page: [https://fred.stlouisfed.org/series/DFII10](https://fred.stlouisfed.org/series/DFII10)
*   `DTWEXBGS` Series Page: [https://fred.stlouisfed.org/series/DTWEXBGS](https://fred.stlouisfed.org/series/DTWEXBGS)
*   `T10YIE` Series Page: [https://fred.stlouisfed.org/series/T10YIE](https://fred.stlouisfed.org/series/T10YIE)

### B. Critical Distinction: `DTWEXBGS` vs. ICE US Dollar Index (`DXY`)

A fundamental distinction must be maintained across all project documentation:
*   **ICE US Dollar Index (`DXY`):** A tradable financial index based on a fixed geometric weighted average of six currencies (EUR 57.6%, JPY 13.6%, GBP 11.9%, CAD 9.1%, SEK 4.2%, CHF 3.6%). DXY prices in continuous real-time on the Intercontinental Exchange (ICE) and requires proprietary commercial licensing.
*   **Federal Reserve Broad Dollar Index (`DTWEXBGS`):** A macroeconomic index calculated by the Federal Reserve Board based on bilateral goods-and-services trade flows with **26 major US trading partners** (including China, Mexico, Canada, the Euro Area, Japan, the UK, South Korea, etc.). Trade weights are updated annually by the Federal Reserve based on annual trade data.
*   **Methodological Rule:** `DTWEXBGS` is the authorized public proxy for broad US dollar strength. It is **NOT** the ICE DXY index. It must be explicitly labeled as the Broad Trade-Weighted US Dollar Index in all files, models, and reports.

### C. Access Requirements, API Keys & Data Licensing
*   **Licensing:** Public Domain (U.S. Government Work). Under Title 17, U.S. Code, works of the U.S. Government (Treasury yield calculations and Federal Reserve Board statistical releases) are not subject to copyright protection in the United States.
*   **Access Requirements:** FRED public download endpoints (`https://fred.stlouisfed.org/graph/fredgraph.csv?id=...`) permit direct programmatic retrieval without mandatory API keys for non-commercial research.
*   **Credential Security:** No API keys or credentials were used or committed.

---

## 2. Data Acquisition Architecture & File Integrity

### A. Raw Data Isolation & Cryptographic Provenance

Downloaded raw data files are archived strictly unmodified in `data/raw/macro/`:

```
data/
├── raw/
│   └── macro/
│       ├── acquisition_metadata.json
│       ├── DFII10_raw.csv
│       ├── DTWEXBGS_raw.csv
│       └── T10YIE_raw.csv
└── processed/
    └── macro/
        ├── macro_daily_cleaned.parquet
        ├── macro_gold_aligned.parquet
        └── macro_processing_metadata.json
```

#### Cryptographic Checksums (SHA-256)

| Artifact Path | SHA-256 Checksum | Total Rows | File Size |
| :--- | :--- | :---: | :---: |
| `data/raw/macro/DFII10_raw.csv` | `a9c922a6fc6a2308671bb9c0b3f674d8d43cd71e32d841c8b90b8d5d23c4aa8f` | 6,215 | 98.7 KB |
| `data/raw/macro/DTWEXBGS_raw.csv` | `52ed35bba07de8f730eea2049815d2c26cb547392ab2cb970c12ee23b0f03946` | 5,431 | 104.1 KB |
| `data/raw/macro/T10YIE_raw.csv` | `6bde5720f15b648c68a3a5d97857b61075de8fab1357430dca47e6941a3658ad` | 6,216 | 97.7 KB |
| `data/processed/macro/macro_daily_cleaned.parquet` | `f7ae56f57e1e3d7d8c8e4fb74ef088fcf3398d76684c530af98874288019937d` | 6,215 | 88.3 KB |
| `data/processed/macro/macro_gold_aligned.parquet` | `7171f82488b34b2e62e092a298e41d64758fb85a0393418ce3971440f12bff89` | 984 | 48.7 KB |

### B. Acquisition Reproducibility
*   **Script:** [`scripts/acquire_macro_data.py`](file:///home/bhoot/project/Treading-Ai/scripts/acquire_macro_data.py)
*   **Execution:** Idempotent. Validates on-disk files against SHA-256 hashes and fetches fresh copies from official FRED endpoints if missing.

---

## 3. Macroeconomic Series Diagnostics (2021–2024 Target Window)

The target research window spans from **2021-01-01 to 2024-12-31** (1,043 business day rows in FRED). Detailed quality metrics are summarized below:

| Diagnostic Metric | `DFII10` (10Y Real Yield) | `DTWEXBGS` (Broad Dollar) | `T10YIE` (10Y Breakeven Inflation) |
| :--- | :---: | :---: | :---: |
| **Full Historical Span** | 2003-01-02 to 2026-10-27 | 2006-01-02 to 2026-10-23 | 2003-01-02 to 2026-10-28 |
| **Full Observation Count** | 6,214 | 5,430 | 6,215 |
| **Duplicate Dates Count** | **0** | **0** | **0** |
| **Strict Date Monotonicity** | **True** | **True** | **True** |
| **2021–2024 Calendar Rows** | 1,043 | 1,043 | 1,043 |
| **Valid Observations Count** | **1,000** | **999** | **1,000** |
| **Holiday / Missing Count** | 43 | 44 | 43 |
| **Missing Ratio** | 4.12% | 4.22% | 4.12% |
| **Minimum Value** | -1.19% | 110.50 | 2.01% |
| **Maximum Value** | +2.52% | 129.28 | 3.02% |
| **Mean Value** | +0.78% | 119.25 | 2.36% |
| **Standard Deviation** | 1.23% | 4.48 | 0.17% |

### Observations on Missing Values
*   Missing observations in FRED daily series are not randomly missing data; they correspond exclusively to **official Federal Reserve Bank and bond market holidays** (e.g. New Year's Day, Martin Luther King Jr. Day, Presidents' Day, Good Friday, Memorial Day, Juneteenth, Independence Day, Labor Day, Columbus Day, Veterans Day, Thanksgiving, Christmas).
*   FRED represents market closures with empty strings `""` or periods `"."`. These were converted strictly to `np.nan` during initial ingestion without synthetic imputation.

---

## 4. Gold Data Integrity & Institutional Daily Aggregation

### A. Gold M5 Training Data Audit
*   **Path:** `data/features/XAUUSD_M5_features_train.parquet`
*   **Total M5 Bars:** 260,821 bars (2021-03-11 18:00:00 UTC to 2024-12-31 21:50:00 UTC)
*   **Timestamp Convention:** Timezone-aware UTC (`+00:00`). Strictly monotonic increasing.
*   **Duplicate Timestamps:** **0**
*   **OHLC Invariants:**
    *   $\text{High} < \text{Low}$: **0**
    *   $\text{Open} > \text{High}$ or $\text{Open} < \text{Low}$: **0**
    *   $\text{Close} > \text{High}$ or $\text{Close} < \text{Low}$: **0**
    *   Non-finite values (NaN / Inf): **0**
*   **Quotation Convention:** HistData raw feed represents **Bid quotes only**. In backtests, Ask prices must be simulated via `ExecutionCostModel` ($\$0.20$ base spread + dynamic session multipliers).

### B. Institutional Session Definition & Refutation of $H=288$
*   **Institutional Gold Session:** Continuous trading begins at **18:00 New York Time** and settles at **17:00 New York Time** the following calendar day (23 trading hours).
*   **Daily Maintenance Roll Closure:** 17:00 to 18:00 NY (1 hour closure, Mon–Thu).
*   **Weekend Closure:** Friday 17:00 NY to Sunday 18:00 NY.
*   **Standard Session Bar Count:**
    $$23 \text{ trading hours} \times 12 \text{ M5 bars/hour} = \mathbf{276 \text{ M5 bars per standard day}}$$
*   **Refutation of $H=288$:** Rolling 288 M5 bars assumes 24 continuous hours. Because trading halts for 1 hour every day, a 288-bar rolling window shifts relative to daily New York settlement by 12 bars (1 hour) every single day. $H=288$ is an intraday window, not a calendar or institutional trading day.

### C. Empirical Session Breakdown (2021–2024)

Aggregating the 260,821 M5 bars into institutional daily bars yields **984 daily sessions**:

| Session Category | Bar Count | Session Count | Percentage | Operational Rationale |
| :--- | :---: | :---: | :---: | :--- |
| **Standard Session** | 276 | 671 | 68.19% | Standard full trading day (18:00 NY to 17:00 NY). |
| **Near-Standard Session** | 275 | 113 | 11.48% | Single bar missing during quiet rollover maintenance. |
| **Friday Early Close** | 204 | 42 | 4.27% | Friday trading closes at 17:00 NY without preceding Sunday open. |
| **Friday Early Close (Alt)** | 192 | 39 | 3.96% | Friday early settlement or holiday weekend closure. |
| **Minor Irregular Sessions** | 272–274 | 41 | 4.17% | Brief liquidity gaps during Asian session quiet hours. |
| **Holiday / Partial Sessions** | $< 250$ | 78 | 7.93% | Thanksgiving, Christmas Eve, New Year, Memorial Day early closes. |
| **Total Daily Sessions** | — | **984** | **100.0%** | Full 2021–2024 research sample. |

---

## 5. Macro–Gold Alignment Audit

To eliminate execution lookahead, macroeconomic releases must be aligned with the decision timestamp of each gold session:
*   **Decision Time:** 17:45 New York Time (during the 17:00–18:00 NY rollover closure).
*   **Trade Entry Time:** 18:00 New York Time (the opening bar of the new institutional session).
*   **Holding Period:** 1 institutional trading day (exiting at 17:00 NY settlement next day).

### A. Comparison of Publication Lag Policies

| Alignment Policy | Lag Rule | Rationale & Mechanism | Complete Sessions ($N$) | Lost Sessions ($N$) | Coverage Pct | Look-Ahead Risk Status |
| :--- | :--- | :--- | :---: | :---: | :---: | :--- |
| **Policy 1: Conservative Availability Lag (Strict No-Ffill)** | $\text{Macro Date} \le \text{Entry Date} - 1$ | Requires macro observation dated strictly before the calendar date of entry. | 976 | 8 | 99.19% | **ZERO Execution Look-Ahead Risk**. 8 sessions dropped due to cross-agency holiday differences. |
| **Policy 1B: Conservative Lag with Holiday Forward-Fill (limit=3)** | $\text{Macro Date} \le \text{Entry Date} - 1$ (ffill $\le 3\text{d}$) | Forward-fills last known closing yield across weekends/holidays (max 3 days). | **984** | **0** | **100.0%** | **ZERO Execution Look-Ahead Risk**. Non-traded assets maintain prior close until reopening. |
| **Policy 2: Same-Day Release Policy** | $\text{Macro Date} \le \text{Entry Date}$ | Assumes daily release at 16:15–17:00 NY is available for 18:00 NY entry. | 980 | 4 | 99.59% | **HIGH Execution Look-Ahead Risk** if server delays occur after 17:00 NY. |

#### Holiday Forward-Fill Justification
Under Policy 1B, carrying the last known settlement yield/index across weekend and single-day market holidays (maximum 3 calendar days) reflects authentic institutional practice. When bond markets close for Good Friday or Veterans Day, the opportunity cost of capital remains anchored to the Thursday settlement until markets reopen on Monday.

### B. Sample Size & Complexity Feasibility for Phase 20
*   **Usable Observations ($N$):** **984 daily sessions** (or 976 under strict no-ffill).
*   **Proposed Model Complexity ($D$):** **$\le 5$ pre-specified explanatory features**.
*   **Observation-to-Feature Ratio:**
    $$\frac{N}{D} = \frac{984}{5} = \mathbf{196.8:1}$$
*   **Sample Sufficiency Verdict:** **SUFFICIENT**. The $196.8:1$ ratio comfortably exceeds the mandatory statistical threshold of $150:1$, guaranteeing that parsimonious linear macro models will not suffer from catastrophic overparameterization.

---

## 6. Point-in-Time Limitations & Forensic Caveats

While the conservative 1-business-day lag eliminates real-time execution timing risks, the data cannot be classified as fully point-in-time safe due to two unresolvable retrospective limitations:
1.  **Absence of Intraday Publication Timestamps:** FRED daily CSVs record observation dates (`YYYY-MM-DD`), not exact millisecond publication timestamps. Historical server delays cannot be audited retrospectively.
2.  **Current-Vintage Trade Weights in `DTWEXBGS`:** The Federal Reserve Board updates bilateral goods-and-services trade weights annually. In standard FRED downloads, historical series reflect current-vintage calculations, introducing retrospective look-ahead bias from future trade weights.
3.  **Proxy Discrepancy:** `DTWEXBGS` is an annual trade-weighted basket of 26 currencies, not the tradable 6-currency ICE DXY index.

*Conclusion:* The data is viable for research under explicit acknowledgment of these limitations, but claims of absolute point-in-time perfection are scientifically unjustified.

---

## 7. Deliverables & Verification Checklist

- [x] Raw data archived in `data/raw/macro/` (`DFII10_raw.csv`, `DTWEXBGS_raw.csv`, `T10YIE_raw.csv`).
- [x] Processed datasets generated in `data/processed/macro/` (`macro_daily_cleaned.parquet`, `macro_gold_aligned.parquet`).
- [x] Full quality diagnostics exported to `reports/phase19/data_quality_results.json`.
- [x] Point-in-time integrity audit documented in `reports/phase19/point_in_time_integrity_audit.md`.
- [x] Reproducible acquisition script: `scripts/acquire_macro_data.py`.
- [x] Validation and alignment script: `scripts/validate_macro_data.py`.
- [x] Dedicated test suite created: `tests/test_phase19_macro_data.py` (12/12 passing).
- [x] Full repository test suite executed: 208/208 tests passing.
- [x] Strict data partition isolation: Zero access to 2025 validation or 2026 test partitions.

---

## 8. Primary Verdict

```
DATA ACQUIRED — POINT-IN-TIME LIMITATIONS REMAIN
```

**Verdict Rationale:** All three mandatory macroeconomic series (`DFII10`, `DTWEXBGS`, `T10YIE`) were successfully acquired from official FRED endpoints and aligned with 984 institutional gold sessions across 2021–2024. While a conservative 1-business-day availability lag guarantees zero execution lookahead, the absence of historical publication timestamp logs and the use of current-vintage annual trade weights in `DTWEXBGS` prevent declaring the dataset fully point-in-time safe. Research planning for Phase 20 may proceed subject to these documented constraints.
