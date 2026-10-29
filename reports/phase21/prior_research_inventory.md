# Phase 21: Evidence-Based Inventory of Prior Research

**Phase:** PHASE 21 — NEW HYPOTHESIS DISCOVERY & RESEARCH DESIGN  
**Date:** October 2026  
**Auditor / Researcher:** Quantitative Researcher & Systematic Trading Specialist  
**Status:** COMPLETE RESEARCH AUDIT & INVENTORY  

---

## 1. Executive Summary & Purpose

Before proposing any new trading hypothesis for spot gold (XAUUSD), this document establishes an exhaustive, evidence-based inventory of all models, mechanisms, features, horizons, and hypotheses previously tested and permanently rejected across Phases 1 through 20B.

The mandate of Phase 21 is to **avoid duplicate research** and ensure that any newly proposed hypothesis addresses a **genuinely distinct market mechanism** rather than repackaging previously falsified ideas.

---

## 2. Inventory of Prior Research & Rejected Hypotheses

```
====================================================================================================
RESEARCH PARADIGM 1: INTRADAY M5 MACHINE LEARNING DIRECTIONAL PREDICTION (Phases 1–16)
====================================================================================================
Hypothesis:
  "Supervised ML models (GBDT, Random Forests, Adaptive Ensembles) trained on M5 price-action 
   features can predict directional price moves over intraday forward horizons (H=12 to H=288)."
Key Files:
  - scripts/run_phase4_evaluation.py
  - scripts/run_phase11_controlled_experiment.py
  - scripts/run_phase13_htf_research.py
  - scripts/run_phase16_model_capability_assessment.py
  - reports/phase16/phase16_model_capability_report.md
Features Tested:
  - 232 engineered features: RSI (14, 28), MACD, Bollinger Bands, ATR ratios, rolling log returns, 
    candlestick shadows/spans, multi-timeframe moving averages (M5, M15, M30, H1, H4).
Models Tested:
  - Incumbent Model (H=24 bars / 2 hours)
  - Market Structure Model (Multi-timeframe features)
  - Adaptive Challenger Model (Online learning / rolling retraining)
Horizons Audited:
  - H=12 (1 hr), H=24 (2 hr), H=48 (4 hr), H=72 (6 hr), H=96 (8 hr), H=120 (10 hr), H=288 (24 hr).
Empirical Results:
  - Out-of-fold directional win rates collapsed to 42.1%–45.8%.
  - Gross Profit Factors ranged from 0.88 to 1.04 (no statistical edge over noise).
  - Net PnL was deeply negative across all models and walk-forward folds after baseline friction ($0.40/oz).
Final Verdict:
  - REJECTED — Frictions dominate price moves; predictions indistinguishable from noise.

====================================================================================================
RESEARCH PARADIGM 2: STRUCTURAL FEASIBILITY & FRICTION DIAGNOSTIC (Phases 17–18B)
====================================================================================================
Hypothesis:
  "Diagnostic investigation to determine whether any intraday M5 directional trading edge is feasible."
Key Files:
  - scripts/run_phase17_feasibility_diagnostic.py
  - scripts/run_phase18a_independent_audit.py
  - scripts/run_phase18b_corrected_diagnostics.py
  - reports/phase17/phase17_feasibility_report.md
  - reports/phase18b/macro_research_feasibility.md
Structural Findings:
  1. The Intraday Cost Wall:
     - Fixed round-turn friction ($0.40/oz base, $0.60/oz stress) consumes 17.7% to 38.2% of the median 
       intraday price move ($1.57 for H=12; $2.26 for H=24).
     - Required break-even win rate is 58.9% to 63.3%. Actual model win rates are 42%–45%.
     - Unconditional MFE/MAE ratio is exactly 1.000 (symmetric Brownian random walk).
  2. Degrees-of-Freedom Collapse:
     - Rolling M5 horizons create 95.8% to 99.6% serial overlap.
     - Apparent sample size of N = 241,524 collapses to an effective independent sample size 
       N_eff = 2,516 for H=96, and just N_eff = 704 for H=288.
  3. Feature Multicollinearity:
     - Out of 232 features, 180 are mathematically redundant dimensions (29 PCA components explain 80% variance).
  4. Macro Drift Masquerade:
     - Apparent outperformance of H=96 in 2024 was driven entirely by passive beta during gold's historic 
       +26% rally ($2,060 to $2,600+), while short trades collapsed to 42.3% precision.
Final Verdict:
  - STOP CURRENT APPROACH — Intraday M5 directional prediction is structurally incapable of beating spread.

====================================================================================================
RESEARCH PARADIGM 3: PRE-REGISTERED MACROECONOMIC HYPOTHESIS TEST (Phases 19–20B)
====================================================================================================
Hypothesis:
  "Daily changes in US 10-Year Real Yields (DFII10), Broad US Dollar Index (DTWEXBGS), and Breakeven 
   Inflation (T10YIE) forecast next-session XAUUSD excess returns net of costs."
Key Files:
  - scripts/acquire_macro_data.py
  - scripts/validate_macro_data.py
  - scripts/run_phase20_macro_test.py
  - scripts/run_phase20a_independent_audit.py
  - scripts/run_phase20b_closure.py
  - reports/phase20/results.json
  - reports/phase20a/corrected_results.json
  - reports/phase20b/corrected_metrics.json
Empirical Results (Out-of-Sample 2023–2024, N = 516 Sessions):
  - Linear correlations: Pearson |r| <= 0.0244, p >= 0.5794 (indistinguishable from zero).
  - Regression R^2: R^2 <= 0.0006.
  - Directional Hit Rates: 49.73% to 51.36% (fails binomial test vs 50% coin toss, p >= 0.28).
  - Corrected Net PnL (1.0x costs):
      * Model A (Yield Only):       -$294.54/oz  (Net PF: 0.895)
      * Model B (Dollar Only):      -$75.42/oz   (Net PF: 0.975)
      * Model C (Bivariate):        -$81.92/oz   (Net PF: 0.978)
      * Model D (Trivariate):       -$258.48/oz  (Net PF: 0.933)
  - Holm–Bonferroni Step-Down (M=4): 0 hypotheses rejected (all p > 0.57).
  - Zero Short Swap Sensitivity: All models remain net negative (-$259.38 to -$42.06/oz).
Final Verdict:
  - PHASE 20 CLOSED — NO PREDICTIVE EDGE.
```

---

## 3. Verified Benchmark Suite & Performance Baselines

The table below catalogs the formal benchmarks established and certified in Phase 20B across the 2023–2024 evaluation window:

| Benchmark ID | Formal Name | Operational Mechanism | 2023–2024 Gross PnL | 2023–2024 Costs | 2023–2024 Net PnL | Active Executions |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| **Benchmark E** | No-Trade Baseline | Cash position ($0.00 exposure, zero friction) | $0.00 | $0.00 | **$0.00/oz** | 0 |
| **Benchmark F1** | Daily Long-Only Strategy | Enters 18:00 NY, exits 17:00 NY daily (516 turnover cycles + swap) | +$789.61 | $241.44 | **+$548.17/oz** | 516 |
| **Benchmark F2** | Continuous Buy-and-Hold | Single 2-year position (1 round turn + holding swap + roll gaps) | +$797.17 | $86.94 | **+$710.23/oz** | 1 |
| **Benchmark G** | Prior-Session Momentum | Enters in direction of prior session return (516 turnover cycles + swap) | -$230.91 | $241.44 | **-$472.35/oz** | 516 |

---

## 4. Rule-Out Criteria for New Hypotheses

Any candidate hypothesis proposed in Phase 21 must be ruled out if it exhibits any of the following duplicate characteristics:

1.  **Duplicate Indicator Class:** Must NOT use rolling RSI, MACD, Bollinger Bands, Stochastics, or moving average crossovers on M5 bars.
2.  **Duplicate Prediction Target:** Must NOT predict continuous forward $H$-bar returns on overlapping M5 time steps ($H=12$ to $H=288$).
3.  **Duplicate Macro Features:** Must NOT rely on daily 1-day differences in FRED `DFII10`, `DTWEXBGS`, or `T10YIE` to forecast next-day close-to-open or open-to-close returns.
4.  **Cost-Vulnerable Time Horizon:** Must NOT propose holding periods where the expected move is less than $\$4.00/\text{oz}$, because fixed bid-ask spread and slippage ($C \ge \$0.20-\$0.40$) would consume $> 10\%$ of the gross move.
5.  **Overnight Rollover Traps:** If holding across the 17:00 NY daily rollover, financing costs ($-\$0.12/\text{oz}$ daily, $-\$0.36/\text{oz}$ Wednesday) and spread widening must be accounted for explicitly.
