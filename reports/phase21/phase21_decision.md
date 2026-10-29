# Phase 21: Final Research Decision & Gate Verdict

**Phase:** PHASE 21 — NEW HYPOTHESIS DISCOVERY & RESEARCH DESIGN  
**Date:** October 2026  
**Auditor / Researcher:** Quantitative Researcher & Systematic Trading Specialist  

---

## 1. Final Decision & Gate Verdict

### **`PHASE 21 HYPOTHESIS APPROVED FOR DEVELOPMENT`**

> [!IMPORTANT]
> **Scientific Caveat:** Approval means strictly that the selected hypothesis (`HYP-21-ASIAN-LONDON-EXPANSION`) is economically grounded, mathematically defined, non-duplicative, technically feasible, and falsifiable with pre-registered statistical gates. **Approval does NOT imply that a profitable trading strategy has been discovered or that positive net expectancy is guaranteed.**

---

## 2. Summary of Research Audit & Pre-Conditions Verified

### A. Prior Research Formally Ruled Out
1.  **Intraday M5 ML Directional Forecasting (Phases 1–16):** Tabular GBDT, Random Forests, Multi-timeframe structure, and rolling oscillators (RSI, MACD, Bollinger) were permanently ruled out due to transaction cost dominance (costs consumed 18%–38% of median moves) and degrees-of-freedom collapse (99% serial overlap).
2.  **Daily Macro Fundamentals (Phases 19–20B):** FRED 10Y TIPS real yields (`DFII10`), Broad Dollar (`DTWEXBGS`), and Breakeven Inflation (`T10YIE`) were permanently ruled out following out-of-sample falsification ($|r| \le 0.0244, p \ge 0.58$, Net PnL negative across all models).

### B. Files and Data Sources Verified
1.  **`data/features/XAUUSD_M5_features_train.parquet`:**
    *   260,821 M5 bars verified spanning 2021-03-11 through 2024-12-31.
    *   UTC datetime64 timestamps verified; clean OHLC pricing quotes confirmed.
    *   Volume limitation verified (`volume == 0.0`); hypothesis relies strictly on OHLC.
2.  **Protected Partitions Cryptographically Confirmed:**
    *   Validation Partition (`val.parquet`): SHA-256 `7e9222e9dc0893601e24505912eeab78330670c4e70ebcc2fa462ff8d44a4f94` (Zero access maintained).
    *   Test Partition (`test.parquet`): SHA-256 `f95fd09a5d07666e3f1d9a72e840e2e97f3c058d11b6bb0c712b21dea86a5dec` (Zero access maintained).

---

## 3. Selected Hypothesis Specification

*   **Identifier:** `HYP-21-ASIAN-LONDON-EXPANSION`
*   **Market Mechanism:** Liquidity transition from Asian inventory equilibrium (00:00–07:00 UTC) to European institutional price discovery (07:00–12:00 UTC). Range compression during Asia conditions directional expansion when London opens.
*   **Observation Unit:** Exactly one non-overlapping discrete trade per qualifying day (eliminates horizon overlap).
*   **Execution Window:** Enters on first M5 breakout between 07:05 and 09:00 UTC; exits at 12:00 UTC close.
*   **Cost Advantage:** Zero overnight swap financing ($0.00); liquid morning spread ($0.20) + slippage ($0.05) = $0.25/oz friction vs $8.00–$14.00/oz expected move (friction drag $\approx 2.5\%$, avoiding the intraday cost wall).
*   **Pre-Registered Rejection Hurdle:** Out-of-sample Net Profit Factor $\le 1.25$, directional hit rate $\le 52.0\%$, or failure to beat Benchmark E ($0.00).

---

## 4. Remaining Uncertainties & Operational Risks

1.  **Macro News Release Volatility:** Major UK/European macroeconomic releases occurring at 07:00–08:30 UTC could generate false breakout spikes (whipsaws) that hit the stop loss.
2.  **Structural Stability Across Regimes:** In strong macro trending years (e.g. 2024 gold rally), long breakouts may perform significantly better than short breakouts. The strategy must demonstrate viability across both sides.
3.  **Spread Widening during Early London Open:** While wholesale London morning spreads average $0.15–$0.20, occasional liquidity gaps at 07:00 UTC could cause temporary spread spikes up to $0.35.

---

## 5. Scope & Mandatory Restrictions for Phase 22 (Development)

Upon advancing to Phase 22:
- Development, calibration of $\tau_{\text{compression}}$, and exploratory analysis must use **strictly the Development Partition (2021-03-11 to 2022-12-30)**.
- Thresholds must be locked prior to scoring the 2023–2024 partition.
- The 2025 Validation and 2026 Test partitions remain **strictly protected and inaccessible**.
- No parameter sweeps or curve-fitting.
