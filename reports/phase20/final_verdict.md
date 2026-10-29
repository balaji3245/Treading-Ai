# Phase 20: Final Research Verdict & Strategic Evaluation

**Status:** Completed & Methodologically Verified  
**Date:** October 2026  
**Auditor:** Quantitative Researcher & Independent Validation Auditor  
**Primary Final Verdict:** `NO EVIDENCE OF PREDICTIVE EDGE`

---

## 1. Official Primary Verdict

```
NO EVIDENCE OF PREDICTIVE EDGE
```

### Definitive Statement
Valid out-of-sample testing across **516 institutional gold sessions (2023–2024)**, using official macroeconomic series acquired from the Federal Reserve Bank of St. Louis FRED under a pre-registered, frozen protocol, **produced zero statistically credible or economically viable evidence of a predictive edge**.

Every candidate model failed all pre-registered promotion criteria, generated negative net cumulative PnL after realistic execution and financing costs, and was outperformed by the zero-cost **No-Trade baseline**.

---

## 2. Empirical Evidence Summary

The final verdict is substantiated by the following verified empirical facts:

| Evaluation Domain | Metric / Hypothesis | Pre-Registered Promotion Gate | Empirical Result (2023–2024) | Gate Status |
| :--- | :--- | :---: | :---: | :---: |
| **Statistical Association** | Out-of-sample Pearson correlation ($r$) | $p < 0.05$ (adjusted) | **$|r| \le 0.0244$ ($p \ge 0.58$)** | **FAILED** |
| **Explanatory Power** | Regression $R^2$ on next-session return | $R^2 > 0.01$ | **$R^2 \le 0.0006$ ($< 0.06\%$)** | **FAILED** |
| **Directional Hit Rate** | Directional accuracy vs. $50.0\%$ null | Binomial $p < 0.05$ | **$49.73\%$ to $51.36\%$ ($p \ge 0.28$)** | **FAILED** |
| **Economic Profitability** | Out-of-sample Net Profit Factor | $\text{Net PF} > 1.25$ | **$0.894$ to $0.978$** | **FAILED** |
| **Net Financial Expectancy** | Cumulative Net PnL after baseline costs | $\text{Net PnL} > \$0.00$ | **$-\$79.02/\text{oz}$ to $-\$297.18/\text{oz}$** | **FAILED** |
| **Multiple-Testing Control**| Holm–Bonferroni step-down correction | Survives Family-Wise $\alpha=0.05$ | **All models rejected ($p \ge 0.58$)** | **FAILED** |
| **Cost Robustness** | Positive Net PnL under $1.5\times$ and $2.0\times$ costs | Positive net return | **Losses expand to $-\$500.40/\text{oz}$** | **FAILED** |
| **Benchmark Superiority** | Performance vs. No-Trade Baseline | Beat No-Trade Net PnL | **No-Trade ($\$0.00$) beats all active models** | **FAILED** |

---

## 3. Forensic Analysis: Why Did Macro Signals Fail?

A rigorous post-mortem identifies two fundamental reasons why daily macroeconomic changes fail to forecast next-session spot gold returns:

### 1. Market Efficiency & Immediate Information Incorporation
*   **Pricing Mechanism:** The US 10-Year Real Yield (`DFII10`) and Broad Dollar Index (`DTWEXBGS`) are compiled from the most liquid, heavily traded financial markets in the world (US Treasury market and global interbank FX).
*   **Information Speed:** By the time the Federal Reserve Board publishes H.10 exchange rates at 16:15 NY and the Treasury publishes constant maturity rates at 16:30 NY, global institutional market participants have already priced the day's macroeconomic news into spot gold throughout the active London and New York sessions.
*   **Arbitrage Decay:** Expecting that a published 1-day change in closing real yields or trade-weighted dollar indices would generate an unexploited, delayed move starting at 18:00 NY and lasting through 17:00 NY next day contradicts basic market efficiency. What little directional drift remains is pure noise ($|r| \le 0.024$).

### 2. Horizon Mismatch Between Macro Fundamentals and Daily Trading Friction
*   **Fundamental Reality:** The macroeconomic relationship between real yields, dollar strength, and gold valuation is genuine over **multi-month and multi-year horizons** (e.g. passive Buy-and-Hold gained $+\$547.93/\text{oz}$ during the 2023–2024 macro expansion).
*   **Noise at Daily Horizons:** On a day-to-day session basis ($23$ hours), gold price action is dominated by order flow imbalances, algorithmic liquidity sweeps, central bank physical purchases, and geopolitical headlines. Attempting to trade 1-day macro differences incurs friction of $\approx \$0.47/\text{oz}$ on every session, turning a $50.8\%$ win rate into a persistent financial loss.

---

## 4. Preservation of Research Integrity

Throughout Phase 20, strict scientific integrity standards were maintained:
1.  **Hypothesis Was Not Curve-Fit:** We did not test hundreds of moving-average crossovers, non-linear indicators, or optimized thresholds to engineer an artificial backtest profit. The pre-registered hypothesis was tested honestly, and its failure is recorded transparently.
2.  **Protected Partitions Remain Virgin:** Zero access occurred to the 2025 Validation partition (`val.parquet`) or 2026 Test partition (`test.parquet`). Their cryptographic SHA-256 hashes match baseline records perfectly.
3.  **Historical Deliverables Preserved:** All artifacts from Phases 1 through 19 remain intact and unmodified.

---

## 5. Strategic Recommendations & Next Justified Steps

The rejection of daily macro directional prediction closes the inquiry into 1-day macroeconomic session trading:

1.  **Cease Daily Macro Strategy Development:** Do not attempt further micro-tuning of 1-day macro diffs. The data proves that daily macro signals cannot overcome transaction friction in daily spot gold.
2.  **Acknowledge No-Trade Baseline:** The No-Trade baseline remains the undefeated institutional benchmark across M5 intraday models (Phases 11–17) and daily macro models (Phase 20).
3.  **Potential Future Research Directions (If Approved):**
    *   *Regime-Based Conditioning (Multi-Month):* Investigate whether macro variables should be used strictly as long-term regime filters (e.g., bull/bear regime gating across months) rather than daily trading signals.
    *   *Order Flow & Volatility Dynamics:* Evaluate whether high-timeframe edge exists in volatility modeling (e.g., ATR expansion forecasting, session range breakout filtering) rather than directional price forecasting.

**Final Principle:** In systematic quantitative research, an honest rejection is a victory. It prevents live capital destruction and directs research toward genuinely viable market phenomena.
