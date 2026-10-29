# Phase 19: Point-in-Time Integrity Audit & Macro–Gold Alignment Specification

**Status:** Completed & Methodologically Verified  
**Date:** October 2026  
**Auditor:** Independent Quantitative Backtesting Auditor  
**Primary Finding:** `DATA ACQUIRED — POINT-IN-TIME LIMITATIONS REMAIN`  
**Governing Rule:** Valid data is a prerequisite for testing an edge, not evidence that an edge exists.

---

## 1. Executive Summary & Audit Mandate

In backtesting macroeconomic trading models, point-in-time (PIT) integrity is the primary line of defense against look-ahead bias and spurious out-of-sample performance. A common failure mode in quantitative finance is conflating the **observation date** ($T$) of a macroeconomic time series with its **availability timestamp** ($t_{\text{avail}}$).

This audit evaluates the point-in-time integrity of the three macroeconomic series acquired in Phase 19:
1.  **US 10-Year Real Yield (`DFII10`)**
2.  **Broad Trade-Weighted US Dollar Index (`DTWEXBGS`)**
3.  **10-Year Breakeven Inflation Rate (`T10YIE`)**

### Core Findings
1.  **Observation Date $\ne$ Availability Timestamp:** Series dated day $T$ reflect market prices recorded during day $T$ and are never available at the start of day $T$.
2.  **Unobservable Intraday Release Timestamps:** FRED daily CSV downloads provide calendar dates (`YYYY-MM-DD`) without intraday publication timestamps. Historical network latencies and release delays cannot be verified.
3.  **Retrospective Vintages in `DTWEXBGS`:** The Federal Reserve Board updates bilateral goods-and-services trade weights annually. Standard FRED downloads reflect current-vintage trade weights applied retrospectively across historical dates.
4.  **Mitigation via Conservative Lag:** Applying a **conservative 1-business-day publication lag** ($\text{Macro Date} \le \text{Entry Date} - 1$) guarantees that macro observations were published at least 24 hours prior to trade entry, eliminating same-day execution timing risks.
5.  **Audit Ruling:** While the conservative lag policy prevents operational execution lookahead, the dataset cannot be certified as fully point-in-time safe due to retrospective vintage trade-weight revisions. The formal verdict is **`DATA ACQUIRED — POINT-IN-TIME LIMITATIONS REMAIN`**.

---

## 2. Forensic Analysis of Acquired Series

### A. US 10-Year Real Yield (`DFII10`)

*   **Compiling Agency:** U.S. Department of the Treasury (Office of Debt Management).
*   **Methodology:** Derived from the Treasury's daily inflation-indexed yield curve (TIPS constant maturity curve). Calculated from bid closing prices gathered by the Federal Reserve Bank of New York around 15:30 Eastern Time.
*   **Observation Date:** Stamped as date $T$. This represents the date of the market closing quotes from which the yield was estimated.
*   **Publication Timing:** Published on the U.S. Treasury website each business day between **15:30 and 17:00 Eastern Time** (typically 16:00–16:30 ET).
*   **Earliest Legitimate Trading Use:**
    *   *Intraday Gold Model:* Cannot be used prior to 17:00 NY on date $T$.
    *   *Institutional Daily Session:* Trading starts at 18:00 NY on date $T$ (for date $T+1$ settlement). Under ideal server conditions, date $T$ TIPS yield is known before 18:00 NY.
    *   *Conservative Audit Policy:* To guard against delayed postings, date $T$ TIPS yield is guaranteed available only for sessions starting on date $T+1$ or later (a 1-business-day lag).
*   **Revision Policy:** Treasury constant maturity yield curve rates are final upon publication. Retrospective revisions are extremely rare and occur only in the event of documented calculation or quoting errors.

---

### B. Broad Trade-Weighted US Dollar Index (`DTWEXBGS`)

*   **Compiling Agency:** Board of Governors of the Federal Reserve System.
*   **Statistical Release:** Federal Reserve Statistical Release H.10, "Foreign Exchange Rates".
*   **Methodology:** A broad, goods-and-services trade-weighted geometric average of the bilateral foreign exchange values of the U.S. dollar against the currencies of 26 major US trading partners.
*   **Observation Date:** Stamped as business day $T$.
*   **Publication Timing:** Published daily at **16:15 Eastern Time** on the Federal Reserve Board website.
*   **Earliest Legitimate Trading Use:** Can be used at 18:00 NY on date $T$ under same-day assumptions, or at 18:00 NY on date $T+1$ under conservative lag rules.
*   **Critical Retrospective Revision Limitation:**
    *   The trade weights assigned to each of the 26 trading partners are updated **annually** based on annual bilateral merchandise trade data from the U.S. Census Bureau.
    *   When the Federal Reserve updates weights annually, historical index values are recalculated using revised trade weights.
    *   Standard FRED downloads provide the **current vintage** of `DTWEXBGS`. Using this historical series in backtests introduces retrospective lookahead: the historical dollar index values incorporate future knowledge of annual trade flow shifts.
    *   *Forensic Impact:* High-frequency currency trades would be severely corrupted. For daily directional gold models, the trade weight drift between adjacent years is small (typically $< 0.5\%$ weight shift per partner), but it remains an unresolvable look-ahead imperfection.

---

### C. 10-Year Breakeven Inflation Rate (`T10YIE`)

*   **Compiling Agency:** Federal Reserve Bank of St. Louis / U.S. Department of the Treasury.
*   **Methodology:** Spreads the nominal 10-year Treasury constant maturity yield (`DGS10`) against the 10-year inflation-indexed Treasury constant maturity yield (`DFII10`):
    $$\text{T10YIE}_t = \text{DGS10}_t - \text{DFII10}_t$$
*   **Observation Date:** Stamped as date $T$.
*   **Publication Timing:** Derived immediately upon release of Treasury daily constant maturity yields (~16:00–17:00 Eastern Time).
*   **Earliest Legitimate Trading Use:** 18:00 NY on date $T+1$ under the conservative lag policy.
*   **Revision Policy:** Constant maturity spreads are fixed once published. Historical revisions are near zero.

---

## 3. Publication Lag Policy & Execution Timing

### A. Gold Session Decision Timeline

The institutional gold trading session operates on the following schedule:
*   **Rollover Closure:** 17:00 to 18:00 New York Time (market halted).
*   **Decision Timestamp ($t_{\text{decision}}$):** **17:45 New York Time**. The quantitative model evaluates all features and issues a trade order.
*   **Trade Entry Timestamp ($t_{\text{entry}}$):** **18:00 New York Time**. The trade fills at the opening price of the first M5 candle of the new session.
*   **Holding Period:** Exactly 23 hours (276 M5 bars).
*   **Trade Exit Timestamp ($t_{\text{exit}}$):** **17:00 New York Time** the following calendar day (at session close/settlement).

```
                      17:00 NY             17:45 NY        18:00 NY                       17:00 NY (Next Day)
                         |                     |               |                                  |
Day T-1 Macro Published -|                     |               |                                  |
                         |-- Rollover Pause ---|-- Decision ---|-- Entry (Session Open) ----------|-- Exit (Settlement)
Day T Macro Published? --| (16:15 - 17:00 NY)  |               |                                  |
```

### B. Evaluation of Candidate Publication Lag Policies

#### Policy 1: Conservative Availability Lag (MANDATORY PROJECT POLICY)
$$\text{Permitted Macro Observation Date} \le \text{Entry Calendar Date} - 1 \text{ Business Day}$$

*   **Mechanics:** For a session entering at 18:00 NY on Tuesday, the model is permitted to use macroeconomic observations dated **Monday or earlier**. For a session entering at 18:00 NY on Sunday (Monday session open), the model uses observations dated **Friday or earlier**.
*   **Integrity Guarantee:** Guarantees that all macroeconomic inputs were published and publicly archived at least **24 hours prior to decision time**.
*   **Look-Ahead Protection:** Eliminates 100% of execution timing risk resulting from server downtime, late releases, after-hours corrections, or release calendar anomalies.
*   **Empirical Match Rate:** **976 of 984 sessions (99.2%)** under strict no-ffill; **984 of 984 sessions (100.0%)** with holiday forward-fill (limit = 3 days).

#### Policy 2: Same-Day Release Policy (REJECTED AS LOOK-AHEAD RISK)
$$\text{Permitted Macro Observation Date} \le \text{Entry Calendar Date}$$

*   **Mechanics:** For a session entering at 18:00 NY on Tuesday, the model uses macroeconomic data dated Tuesday afternoon (released between 16:15 and 17:00 NY).
*   **Fatal Flaw:** If a FRED or Treasury release is delayed past 17:45 NY due to technical issues, holiday schedules, or network latency, the model assumes data that did not exist at decision time.
*   **Audit Decision:** **REJECTED**. Same-day macro execution introduces unverified intraday timing assumptions.

---

## 4. Macro–Gold Alignment Specification

The alignment dataset [`data/processed/macro/macro_gold_aligned.parquet`](file:///home/bhoot/project/Treading-Ai/data/processed/macro/macro_gold_aligned.parquet) establishes a verified schema connecting every gold session to its legitimate macroeconomic inputs:

### A. Data Schema

| Field Name | Type | Description | PIT Integrity Rule |
| :--- | :--- | :--- | :--- |
| `settlement_date` | `string` | Institutional gold settlement date (`YYYY-MM-DD`). | NY settlement calendar. |
| `entry_ts_ny` | `string` | Trade entry timestamp in New York time (`YYYY-MM-DD 18:00:00-04/05:00`). | Opening bar of session. |
| `decision_ts_ny` | `string` | Decision timestamp in New York time (`YYYY-MM-DD 17:45:00-04/05:00`). | 15 min prior to entry. |
| `session_open_price` | `float64` | Gold open price at entry (Bid). | HistData Bid quote. |
| `session_high_price` | `float64` | Maximum gold price during session. | Strictly active session bars. |
| `session_low_price` | `float64` | Minimum gold price during session. | Strictly active session bars. |
| `session_close_price` | `float64` | Gold settlement price at 17:00 NY (Bid). | Exit price. |
| `session_n_m5_bars` | `int64` | Number of M5 bars in session (276 standard). | Invariant check. |
| `macro_obs_date` | `string` | Calendar observation date of macro series. | $\le \text{Entry Date} - 1$. |
| `dfii10_real_yield` | `float64` | 10-Year TIPS Real Yield (Percent). | Legitimate prior value. |
| `dtwexbgs_broad_dollar`| `float64` | Broad Trade-Weighted Dollar Index (Jan 2006=100). | Legitimate prior value. |
| `t10yie_breakeven_inflation`| `float64` | 10-Year Breakeven Inflation Rate (Percent). | Legitimate prior value. |
| `is_complete_holiday_ffill`| `bool` | True if all 3 macro variables are present with holiday ffill $\le 3\text{d}$. | 100.0% of sessions. |
| `point_in_time_status` | `string` | `CONSERVATIVE_LAG_VERIFIED_CURRENT_VINTAGE` | Mandatory limitation flag. |

---

## 5. Summary of Point-in-Time Limitations & Risks

To ensure total transparency, all remaining point-in-time imperfections are cataloged:

| Limitation / Risk Domain | Severity | Source / Mechanism | Impact on Research | Remediation / Audit Policy |
| :--- | :---: | :--- | :--- | :--- |
| **Intraday Release Timing** | **LOW** | FRED daily CSVs lack exact millisecond publication timestamps. | Minor for daily strategies; severe for intraday models. | Conservative 1-business-day lag ensures publication $\ge 24\text{h}$ prior to entry. |
| **Retrospective Vintages** | **MEDIUM** | `DTWEXBGS` trade weights undergo annual retrospective revisions. | Historical broad dollar levels reflect slightly adjusted future trade weights. | Disclosed as an inherent limitation of public FRED series; weights drift $< 0.5\%/\text{yr}$. |
| **Proxy Discrepancy** | **MEDIUM** | `DTWEXBGS` is a 26-currency annual trade-weighted index, not the 6-currency tradable ICE DXY. | Macro dollar pressure may diverge from high-frequency speculative FX flows. | Explicitly labeled as Broad Trade-Weighted Dollar, not ICE DXY. |
| **Bid-Only Gold Quotes** | **MEDIUM** | HistData quotes reflect Bid prices; Ask prices are unobserved. | Direct execution cannot observe real-time spread widening. | Evaluated with `ExecutionCostModel` ($\$0.20$ base + session multipliers). |
| **Holiday Forward-Fill** | **LOW** | Carrying Friday yields across weekend/Monday bank holidays. | 8 sessions reflect non-traded prior close prices. | Justified: Non-traded debt securities retain prior settlement until markets reopen. |

---

## 6. Recommendations for Phase 20

Based on this forensic audit, the following protocol is recommended for Phase 20:

1.  **Strict Enforcement of Conservative Lag:** All candidate models must use the aligned dataset [`data/processed/macro/macro_gold_aligned.parquet`](file:///home/bhoot/project/Treading-Ai/data/processed/macro/macro_gold_aligned.parquet) generated under Policy 1B. Same-day macro execution is prohibited.
2.  **Constraint on Model Complexity:** Model complexity must remain strictly bounded to **$D \le 5$ pre-specified explanatory variables** to preserve the $196.8:1$ observation-to-feature ratio on the $N=984$ sample.
3.  **No Automatic Execution:** Phase 20 must be formally reviewed and pre-registered before fitting any model.
4.  **Final Principle:** Valid data is a prerequisite for testing an edge, not evidence that an edge exists. Meeting data quality standards does not imply that macroeconomic features possess predictive alpha for spot gold.
