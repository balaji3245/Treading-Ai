# RESEARCH INVENTORY & AUDIT OF PRIOR FINDINGS: PHASE 24

**Phase:** 24 — New Hypothesis Discovery & Pre-Registration  
**Repository:** `Treading-Ai`  
**Instrument:** XAUUSD (Spot Gold / US Dollar)  
**Execution Timestamp:** 2026-10-30T03:40:00 UTC  
**Status:** COMPLETE HISTORICAL RESEARCH AUDIT  

---

## 1. Executive Summary & Purpose

Before formulating any new quantitative trading hypothesis, sound scientific methodology mandates an exhaustive audit of all previously tested and falsified research directions. 

The mandate of Phase 24 is to **prevent circular research, pseudo-discovery, and parameter recycling**. No hypothesis may be considered if it directly or indirectly repackages ideas, features, models, or timing windows that failed in previous phases.

The Phase 23 out-of-sample verdict is permanently recorded as:
```
PHASE 23 VERDICT: REJECT
```
Hypothesis `HYP-21-ASIAN-LONDON-EXPANSION` is formally closed and will not be revived, modified, or re-tuned.

---

## 2. Exhaustive Trajectory of Prior Research (Phases 1–23)

```
====================================================================================================
RESEARCH PARADIGM 1: INTRADAY M5 MACHINE LEARNING DIRECTIONAL PREDICTION (Phases 1–16)
====================================================================================================
Core Concept:
  "Supervised ML models (GBDT, Random Forests, Adaptive Ensembles) trained on M5 price-action features
   and technical indicators can predict directional price movement over forward horizons (H=12 to 288)."
Key Files:
  - scripts/run_phase4_evaluation.py
  - scripts/run_phase11_controlled_experiment.py
  - scripts/run_phase13_htf_research.py
  - scripts/run_phase16_model_capability_assessment.py
  - reports/phase16/phase16_model_capability_report.md
Features & Targets:
  - 232 engineered features: RSI (14, 28), MACD, Bollinger Bands, ATR ratios, moving average crossovers.
  - Multi-timeframe aggregates across M5, M15, M30, H1, H4.
  - Continuous forward log-return labels across H=12 (1h), H=24 (2h), H=48 (4h), H=96 (8h), H=288 (24h).
Empirical Results:
  - Out-of-fold directional accuracy collapsed to 42.1%–45.8% (sub-random).
  - Gross Profit Factors ranged between 0.88 and 1.04.
  - Frictions ($0.40/oz base) produced catastrophic net drawdowns across all walk-forward folds.
Verdict:
  - PERMANENTLY REJECTED — Frictions dominate intraday moves; M5 technical indicators lack predictive edge.

====================================================================================================
RESEARCH PARADIGM 2: STRUCTURAL FEASIBILITY & THE INTRADAY COST WALL (Phases 17–18B)
====================================================================================================
Core Concept:
  "Diagnostic forensic audit to identify the fundamental mathematical reasons for model failure."
Key Files:
  - scripts/run_phase17_feasibility_diagnostic.py
  - scripts/run_phase18a_independent_audit.py
  - scripts/run_phase18b_corrected_diagnostics.py
  - reports/phase17/phase17_feasibility_report.md
  - reports/phase18b/macro_research_feasibility.md
Key Structural Findings:
  1. The Intraday Cost Wall:
     - Median M5 price moves for short horizons ($1.57 for H=12; $2.26 for H=24) are too small relative to
       round-turn friction ($0.40/oz). Frictions consume 17.7% to 38.2% of the median price excursion.
     - Required breakeven win rate is 58.9% to 63.3%; actual model win rates were 42%–45%.
  2. Degrees-of-Freedom & Serial Correlation Collapse:
     - Continuous rolling M5 steps create 95.8% to 99.6% serial label overlap.
     - Apparent sample size of N = 241,524 collapses to an effective independent sample size N_eff = 704
       for H=288 and N_eff = 2,516 for H=96.
  3. Feature Multicollinearity:
     - 180 of 232 features were mathematically redundant (29 PCA components explain 80% variance).
Verdict:
  - METHODOLOGY HALTED — High-frequency M5 indicator forecasting is structurally incapable of beating friction.

====================================================================================================
RESEARCH PARADIGM 3: DAILY MACROECONOMIC YIELD & DOLLAR REGRESSION (Phases 19–20B)
====================================================================================================
Core Concept:
  "Daily changes in US 10-Year Real Yields (FRED DFII10), Broad US Dollar Index (DTWEXBGS), and Breakeven
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
Empirical Results (2023–2024 Evaluation, N = 516 Daily Sessions):
  - Linear correlation: Pearson |r| <= 0.0244, p >= 0.5794 (indistinguishable from white noise).
  - Ordinary least squares R^2 <= 0.0006.
  - Directional hit rates: 49.73% to 51.36% (fails exact binomial test vs 50% coin toss, p >= 0.28).
  - All four macro regression models suffered net losses (-$294.54 to -$75.42/oz, PF 0.895 to 0.978).
Verdict:
  - PERMANENTLY CLOSED — Daily FRED macro changes have zero predictive edge for next-session returns.

====================================================================================================
RESEARCH PARADIGM 4: ASIAN COMPRESSION & LONDON MORNING EXPANSION (Phases 21–23)
====================================================================================================
Core Concept:
  "Volatility compression during the Asian session (00:00–07:00 UTC) triggers a directional range expansion
   breakout upon the opening of institutional London trading (07:05–09:00 UTC), held until 12:00 UTC."
Hypothesis ID:
  HYP-21-ASIAN-LONDON-EXPANSION
Key Files:
  - scripts/run_phase22_development_backtest.py
  - scripts/run_phase22_independent_audit.py
  - scripts/run_phase23_oos_evaluation.py
  - scripts/run_phase23_independent_audit.py
  - reports/phase22/backtest_results_development.md
  - reports/phase23/statistical_analysis.md
  - reports/phase23/phase23_decision.md
Empirical Trajectory:
  1. Development Partition (2021–2022, N = 101 trades):
     - Net PnL (1.0x baseline): +$42.438/oz, Net PF: 1.263, Win Rate: 54.46%.
     - Directional symmetry: Long +$13.93/oz (PF 1.171); Short +$28.51/oz (PF 1.355).
  2. Out-of-Sample Partition (2023–2024, N = 89 trades):
     - Win rate collapsed to 43.82% (39 wins, 50 losses, binomial p = 0.2891).
     - Directional collapse: Short trades lost -$41.933/oz (win rate 27.03%, Net PF 0.633).
     - Net Expectancy 95% bootstrap CI spanned zero: [-$0.855, +$2.299]/oz.
     - Maximum drawdown doubled to $61.558/oz.
     - 4 trades held past rollover due to midday data gaps accounted for all nominal profits;
       when strictly capped at 12:00 UTC, net PnL was +$5.68/oz (1.0x) and negative at 1.5x/2.0x.
Verdict:
  - FORMALLY REJECTED — Fails out-of-sample statistical significance and directional stability.
```

---

## 3. Catalog of Verified Repository Benchmarks

The project maintains four benchmark baselines established in Phase 20B and verified across 2023–2024:

| Benchmark ID | Benchmark Name | Strategy Description | 2023–2024 Net PnL | Turnover Cycles |
| :--- | :--- | :--- | :--- | :--- |
| **Benchmark E** | No-Trade Baseline | Cash position ($0.00 exposure, zero turnover, zero risk) | **$0.00/oz** | 0 |
| **Benchmark F1** | Daily Long-Only Strategy | Enters 18:00 NY, exits 17:00 NY daily (includes holding swap) | **+$548.17/oz** | 516 |
| **Benchmark F2** | Continuous Buy-and-Hold | Single 2-year position (1 round-turn + financing swap) | **+$710.23/oz** | 1 |
| **Benchmark G** | Prior-Session Momentum | Daily trend-following on prior-session return | **-$472.35/oz** | 516 |

---

## 4. Absolute Rule-Out Criteria for Phase 24 Candidates

Any newly proposed candidate hypothesis must be **disqualified immediately** if it exhibits any of the following duplicate characteristics:

1. **Indicator Recycling:** Must NOT use rolling RSI, MACD, Bollinger Bands, Stochastics, ATR trailing bands, or moving average crosses on M5 bars.
2. **Rolling Overlapping Targets:** Must NOT predict continuous forward $H$-bar returns ($H=12$ to $288$) on overlapping steps.
3. **Daily Macro Regression:** Must NOT use daily 1-day differences in FRED `DFII10`, `DTWEXBGS`, or `T10YIE`.
4. **Session Breakout Momentum:** Must NOT revive London morning range breakouts, Asian boundary penetrations, or volatility compression ratios.
5. **Cost-Vulnerable Horizons:** Must NOT propose holding periods where expected move is $< \$5.00/\text{oz}$, where fixed friction ($C \ge \$0.25/\text{oz}$) consumes $> 10\%$ of gross returns.
6. **Uncontrolled Overnight Rollover:** Must NOT hold open positions across the daily rollover window (21:00–22:00 UTC) without explicit swap financing accounting.
