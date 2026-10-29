# Phase 20A: Macro Feature and Leakage Audit

**Document:** Macro Feature and Leakage Audit  
**Target Dataset:** [macro_gold_aligned.parquet](file:///home/bhoot/project/Treading-Ai/data/processed/macro/macro_gold_aligned.parquet)  
**Alignment Script:** [validate_macro_data.py](file:///home/bhoot/project/Treading-Ai/scripts/validate_macro_data.py)  
**Auditor:** Quantitative Researcher & Independent Code Auditor  

---

## 1. Feature Construction & Mathematical Invariants

In [run_phase20_macro_test.py:254-256](file:///home/bhoot/project/Treading-Ai/scripts/run_phase20_macro_test.py#L254-L256):
```python
df["d1_real_yield"] = df["dfii10_real_yield"].diff()
df["d1_broad_dollar"] = df["dtwexbgs_broad_dollar"].pct_change()
df["d1_breakeven_inflation"] = df["t10yie_breakeven_inflation"].diff()
```

### A. Difference Formula Verification
*   **`d1_real_yield`:** $\Delta y_t = y_t - y_{t-1}$. Correct 1-day arithmetic difference in percentage points of 10-Year TIPS yield.
*   **`d1_broad_dollar`:** $\Delta d_t = (d_t - d_{t-1}) / d_{t-1}$. Correct 1-day percentage change in the Trade-Weighted Broad Dollar Index.
*   **`d1_breakeven_inflation`:** $\Delta b_t = b_t - b_{t-1}$. Correct 1-day arithmetic difference in percentage points of 10-Year breakeven inflation.

### B. Forward-Fill Dynamics & Zero-Change Behavior
In the alignment script [validate_macro_data.py:260-262](file:///home/bhoot/project/Treading-Ai/scripts/validate_macro_data.py#L260-L262), macroeconomic series were forward-filled up to a strict limit of 3 calendar days (`macro_ffill3`) to bridge weekends and single-day US market holidays:
*   **Zero-Difference Occurrences:** When two consecutive institutional gold trading sessions point to the exact same macroeconomic observation date (e.g. over a weekend or holiday), the aligned value remains unchanged:
    $$\Delta y_t = y_t - y_{t-1} = 0.0$$
*   **Model Position Treatment:** In Model A:
    $$\text{pos}_t = -\text{sign}(\Delta y_t) = -\text{sign}(0.0) = 0.0$$
    The model stays completely **flat / inactive** (`pos == 0`) when no new macroeconomic data has been observed.
*   **Monday Evening Inactivity Finding:** Under Conservative Lag Policy 1B:
    $$\text{Macro Observation Date} \le \text{Entry Date} - 1 \text{ Calendar Day}$$
    *   For Sunday 18:00 NY entry (`entry_date` is Sunday), `Entry Date - 1` is Saturday. The latest available FRED observation is **Friday**.
    *   For Monday 18:00 NY entry (`entry_date` is Monday), `Entry Date - 1` is Sunday. The latest available FRED observation is **still Friday**.
    *   Consequently, on **102 out of 105 Monday evening sessions**, `d1_real_yield` was exactly $0.0$, and Model A correctly placed no trade. This accounts for why Model A executed only 364 trades across 516 sessions ($70.5\%$ participation).

---

## 2. Temporal Alignment & Leakage Audit

### A. Session Boundary Alignment
| Milestone | Timestamp (New York Time) | Operational Activity | Information State |
| :--- | :--- | :--- | :--- |
| **Market Rollover Maintenance** | 17:00–18:00 NY daily | Spot gold trading halted for clearing / roll | Spreads widen; low liquidity |
| **Decision Time** | **17:45 NY daily** | Features computed; signals generated | Macro data through $\le \text{Entry Date} - 1$ |
| **Trade Entry** | **18:00 NY daily** | Position entered at session open price | Strictly follows decision time |
| **Holding Interval** | 18:00 NY to 17:00 NY next day | Exactly 23 institutional trading hours | No interim position changes |
| **Trade Exit** | **17:00 NY next day** | Position liquidated at session close price | Exact session settlement |

### B. Look-Ahead & Target Leakage Check
1.  **Look-Ahead Leakage:** **NONE DETECTED**. Because the conservative lag rule forces $\text{Macro Date} \le \text{Entry Date} - 1$, macroeconomic observations used at 17:45 NY were released at least 24 hours prior to trade execution.
2.  **Target Leakage:** **NONE DETECTED**. Features use only macroeconomic differentials $\Delta y_t, \Delta d_t, \Delta b_t$. The prediction target $\text{Close}_{t+1} - \text{Open}_{t+1}$ is strictly out-of-sample forward price action.
3.  **Standardization Leakage:** **NONE DETECTED**. Feature normalization parameters (means and standard deviations) were fitted **strictly on the Development partition (2021-03-11 to 2022-12-30)** and frozen prior to scoring the out-of-sample period (2023–2024).

---

## 3. Retrospective Proxy Limitations (Mandatory Caveats)

While the data contains no programmatic look-ahead bugs, the audit confirms that **this dataset cannot be classified as fully point-in-time safe** due to two structural limitations of FRED data:

1.  **Missing Intraday Publication Timestamps:** FRED daily series provide observation calendar dates (`YYYY-MM-DD`), but do not provide exact timestamped record-creation metadata indicating whether a release occurred at 16:15 NY, 17:00 NY, or the following morning. The Conservative Lag Rule ($\le \text{Entry Date} - 1$) successfully mitigates this risk by forcing a 24-hour buffer, but true intraday arrival verification is absent.
2.  **Annual Re-weighting of Broad Dollar Index (`DTWEXBGS`):** The Federal Reserve Board recalculates the trade weights for the 26 trading partners annually and retrospectively restates historical index levels. The historical Broad Dollar series acquired from FRED reflects current-vintage re-weighted calculations, which were not available in real time in 2021 or 2022.

### Audit Policy Determination
The dataset classification must remain **`RETROSPECTIVE PROXY`**. It is scientifically valid for hypothesis testing and research falsification, but cannot be treated as a point-in-time production backtest.
