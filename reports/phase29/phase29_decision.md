# PHASE 29 DECISION RECORD: DATA ACQUISITION & RESEARCH HORIZON ARCHITECTURE

**Phase:** 29 — Data Acquisition Plan, Provider Evaluation & Cost Architecture  
**Repository:** `Treading-Ai`  
**Execution Timestamp:** 2026-10-31T14:30:00 UTC  
**Baseline Commit:** `5038d33e4ff7e76d7f8d308da0b9b76132bfdc82`  
**Decision Authority:** Quantitative Infrastructure Engineer, Market Data Analyst & Cloud Cost Auditor  

---

## Final Formal Verdict

```
=================================================================================
PHASE 29 FORMAL VERDICT: APPROVE DUAL-TRACK DATA ARCHITECTURE
=================================================================================
PRIMARY PATH:  PATH 1 — MULTI-DAY SWING RESEARCH ON H4 / DAILY (ZERO COST)
FALLBACK PATH: PATH 2 — DUKASCOPY HISTORICAL TICK BID/ASK DATA INGESTION (ZERO COST)
AWS ACTION:    LOCAL WORKSTATION DEFAULT ($0.00 CLOUD SPEND AUTHORIZED)
=================================================================================
```

*The Data Architecture and Feasibility Audit has completed. In accordance with cost-conscious quantitative engineering principles, Treading-Ai approves a dual-track data architecture that eliminates high-frequency intraday friction traps, incurs zero financial expenditure on data or cloud services, and establishes a scientifically defensible statistical research design for future research phases.*

---

## 1. Evaluation & Justification of Approved Paths

```
+-------------------------------------------------------------------------------------------------------------------+
|                                     STRATEGIC PATH SELECTION SCORECARD                                            |
+--------------------------+------------------------------------------------+---------------------------------------+
| Evaluation Criteria      | PRIMARY: Path 1 (H4/Daily Swing + FRED)        | FALLBACK: Path 2 (Dukascopy Tick Feed)|
+--------------------------+------------------------------------------------+---------------------------------------+
| 1. Data Quality          | Excellent for multi-day trends; clean OHLC     | Excellent for microstructure; millsec |
|                          | Session-aligned H4 eliminates roll splits.     | synchronized Bid/Ask quotes & volume. |
+--------------------------+------------------------------------------------+---------------------------------------+
| 2. Total Direct Cost     | **$0.00** (Uses existing local repository data)| **$0.00** (Free public Dukascopy feed)|
+--------------------------+------------------------------------------------+---------------------------------------+
| 3. Cloud / Infra Cost    | **$0.00** (Processed entirely on local SSD)    | **$0.00** (Processed locally on NVMe) |
+--------------------------+------------------------------------------------+---------------------------------------+
| 4. Research Usefulness   | Solves the M5 friction wall. Targets $25–$70/oz| Enables empirical measurement of      |
|                          | macro moves driven by real rates and inflation | dynamic spreads, news spikes & slippag|
+--------------------------+------------------------------------------------+---------------------------------------+
| 5. Implementation Effort | **Low** (Resampler already supports H4/Daily;  | **Medium** (Requires LZMA .bi5 decoder|
|                          | macro series already verified and cached).     | and binary tick ingestion pipeline).  |
+--------------------------+------------------------------------------------+---------------------------------------+
| 6. Licensing & Legal     | Fully compliant (Public domain FRED; HistData  | Fully compliant for non-commercial    |
|                          | personal backtesting license).                 | research; no redistribution.          |
+--------------------------+------------------------------------------------+---------------------------------------+
| 7. Frictional Immunity   | **Immune** ($0.50 cost on $50 move = 1.0% drag)| High accuracy (spread directly traded)|
+--------------------------+------------------------------------------------+---------------------------------------+
```

---

## 2. Statistical Research Design for Future Discovery

To ensure that future research avoids the methodological blindspots and severe underpowering observed in Phase 27, all future quantitative hypothesis discovery must strictly adhere to the following framework:

### A. Horizon Re-Orientation
- **Mandatory Horizon Floor:** Hypotheses targeting holding windows under 1 hour or average excursions under **$\$10.00/\text{oz}$** are **prohibited**.
- **Approved Horizons:** Multi-session holding windows (H4) and multi-day swing positions (1 to 10 trading days), where macro-economic drivers (real interest rates, inflation expectations, central bank gold purchases, and sovereign currency debasement) create trending regimes exceeding $\$25.00/\text{oz}$.

### B. Statistical Power & Sample Size Nuance
> [!NOTE]
> **Methodological Clarification on Statistical Power:**  
> In Phase 28, the audit demonstrated that Phase 27 candidate strategies were underpowered to detect a small intraday edge ($\delta = \$0.50/\text{oz}$) because standard errors ($\text{SE} \sim \$0.60–\$1.40$) dwarfed the target effect.  
> However, an arbitrary universal requirement of $80\%$ statistical power must **not** be imposed mechanically on low-frequency multi-day swing models. In financial economics:
> 1. Multi-day swing strategies generate relatively few trades ($25$ to $50$ trades per year).
> 2. Requiring $N = 1,000+$ trades for $80\%$ power would require **$20$ to $40$ years of continuous history**, during which the macroeconomic regime (e.g. Bretton Woods, gold standard, fiat regime, post-2008 QE) undergoes structural breaks. Non-stationarity invalidates pooling across multi-decade samples.
> 3. **The Solution:** Rather than relying exclusively on single-hypothesis $t$-tests under unrealistic power assumptions, future phases must employ:
>    - **Stationary Block Bootstrapping:** To compute empirical confidence intervals for expectancy and Profit Factor without assuming Gaussian returns.
>    - **False Discovery Rate (FDR) Control:** Using Benjamini-Hochberg procedures when evaluating multiple candidate features.
>    - **Economic Significance Gates:** Demanding that net profit factor exceed $1.25$ and net expectancy exceed at least **$5.0\times$ the round-turn transaction cost**.

### C. Serial Dependence and Overlapping Trade Handling
- In multi-day swing strategies where positions can be held across multiple days, rolling forward returns naturally induce moving-average serial correlation in the error term.
- To eliminate serial correlation distortion:
  1. Calculate the effective degrees of freedom using the Bartlett-corrected sample size:
     $$N_{\text{eff}} = N \cdot \frac{1 - \rho_1}{1 + \rho_1}$$
  2. Implement strict non-overlapping trade logic (a new trade cannot enter until the existing open position has reached an exit boundary).

### D. Separation of Development, Validation, and Testing
- **Development Partition (2021–2022):** Used exclusively for exploratory research, parameter estimation, and preliminary gating.
- **Historical Out-of-Sample Partition (2023–2024):** Used as a secondary historical checkpoint.
- **Protected Holdouts (2025 Validation & 2026 Test):** Remain **100% sealed and untouched**. They shall only be accessed via formal, locked evaluation protocols after a hypothesis has passed all pre-registered development gates.

---

## 3. Explicit Prohibitions & Scientific Guardrails

In adherence to the core mandate:
1. **No Strategy Generation in Phase 29:** Zero trading strategies, rules, or predictive machine learning models were developed or fitted during Phase 29.
2. **No Data Purchases or Subscriptions:** Zero capital was expended. All evaluated options operate entirely on free or public-domain assets.
3. **No Cloud Resource Creation:** No AWS instances, S3 buckets, or managed cloud services were launched.
4. **No Access to Protected Partitions:** The cryptographic hashes of `val.parquet` (`7e9222e9...`) and `test.parquet` (`f95fd09a...`) remain untouched and verified.
5. **No Promise of Inevitable Profitability:** Sourcing higher-resolution data or expanding to higher timeframes does **not** guarantee that a profitable market anomaly exists. Financial markets are highly competitive and may exhibit weak-form efficiency across all liquid horizons.

---

## 4. Phase 30 Actionable Implementation Roadmap

```
+---------------------------------------------------------------------------------+
|                       PHASE 30 TECHNICAL EXECUTION ROADMAP                      |
+-------------------+-------------------------------------------------------------+
| Step              | Operational Action Plan                                     |
+-------------------+-------------------------------------------------------------+
| 1. Data Prep      | Run existing `process_timeframes.py` to generate clean H4   |
|                   | and Daily Parquet datasets with NY close alignment.         |
+-------------------+-------------------------------------------------------------+
| 2. Macro Merge    | Build feature integration script aligning daily FRED series |
|                   | (DFII10 real yields, DTWEXBGS dollar index) to H4/Daily bars|
|                   | with strict zero-lookahead (T+1 publication lag enforcement)|
+-------------------+-------------------------------------------------------------+
| 3. Pre-Register   | Formulate and pre-register a single, economically sound     |
|    Hypothesis     | macro-regime swing hypothesis before running backtests.     |
+-------------------+-------------------------------------------------------------+
| 4. Controlled Dev | Evaluate the pre-registered hypothesis strictly on the      |
|                   | 2021–2022 development partition with full transaction costs.|
+-------------------+-------------------------------------------------------------+
```
