# Treading-AI — Phase 9A: Complete AI Architecture Audit

**Asset:** XAUUSD (Spot Gold)  
**Timeframe:** M5 Intraday  
**Audit Date:** October 2026  
**Auditor:** Senior Quantitative Research Engineer, ML Engineer, Microstructure Researcher, and Production ML Architect  
**Scope:** Complete Codebase, Data Pipeline, Features, Models, Backtesting, Trade Logging, and Governance  
**Mode:** AUDIT ONLY (Zero Source Code Modifications)  
**Status of 2026 Test Partition:** FROZEN & COMPLETELY UNTOUCHED  
**Status of 2025 Validation Partition:** PRESERVED & UNINSPECTED  

---

## Section 1 — Executive Summary

### 1.1 Current System Maturity Assessment
The Treading-AI project possesses an **exceptionally mature, professional data-engineering and causal backtesting foundation**, but remains in an **immature, static prototype state regarding market analysis, trade auditing, and adaptive machine learning**:

1. **What Genuinely Works (Institutional Quality):**
   - **Data Cleaning & Resampling:** M1 $\rightarrow$ M5/H1/H4 resampling preserves strict left-closed candle semantics, filters incomplete candles, flags missing constituent bars, and avoids fabricating fills across market gaps ([`resampler.py`](file:///home/bhoot/project/Treading-Ai/src/treading_ai/preprocessing/resampler.py)).
   - **Temporal Causality & Boundary Alignment:** Higher-timeframe (H1, H4) features are merged onto M5 bars strictly through backward as-of merges on candle closing timestamps ($\text{timestamp} + \text{duration}$), ensuring complete zero-lookahead causality ([`multi_timeframe.py`](file:///home/bhoot/project/Treading-Ai/src/treading_ai/features/multi_timeframe.py)).
   - **Market Microstructure & Rollover Logic:** Timezone-aware handling of New York rollover closure (Mon–Thu 17:00–18:00 NY), European/US DST transitions, weekend market closures, and pre-weekend squaring ([`cost_model.py`](file:///home/bhoot/project/Treading-Ai/src/treading_ai/backtesting/cost_model.py), [`time_features.py`](file:///home/bhoot/project/Treading-Ai/src/treading_ai/features/time_features.py)).
   - **Execution & Cost Accounting:** Bid-only pricing approximations (Long buys Ask, sells Bid; Short sells Bid, buys Ask), dynamic spread expansion, slippage modeling, and exact parity:
     $$\text{Net PnL} = \text{Gross PnL} - (\text{Spread} + \text{Slippage} + \text{Commission})$$
     Verified with 0 double-counting across all simulated trades.
   - **Validation Methodology:** Expanding-window chronological walk-forward cross-validation (2021–2024) with strict boundary purging ($1+H$ bars) and frozen 2026 test partition isolation.

2. **The Critical Blockers:**
   - **Absence of Net Alpha:** Across Phases 4 through 8, every evaluated directional model, selective probability threshold, multi-horizon window ($H=6, 24, 48$), triple-barrier configuration, and macro-regime gating policy produced **negative net expectancy after transaction costs**. In all phases, the active strategies were strictly dominated by the **No-Trade baseline ($\$0.00$)**.
   - **Total Absence of Market Structure & Order Flow Features:** While the system computes 191 generic continuous indicators (returns, ATR, EMAs, RSI, MACD, Bollinger Bands), it has **zero market structure features**: no swing highs/lows, no Higher Highs / Lower Lows, no Break of Structure (BOS), no Change of Character (CHoCH), no Fair Value Gaps (FVG), no order blocks, and no causal Support/Resistance zones.
   - **Absence of Trade Journaling & Error Analysis:** Simulated trades are evaluated only as aggregate summary statistics. The system has **no persistent trade journal**, does not record decision reasoning, does not track Maximum Favorable Excursion (MFE) or Maximum Adverse Excursion (MAE), and cannot classify trade failure causes (e.g., bad entry vs regime mismatch vs friction drag).
   - **Zero Adaptive or Self-Learning Capability:** The codebase contains **no active learning, no similar-case retrieval, and no failure-pattern feedback loop**. Models are trained statically in batch scripts. What has previously been referred to as "research iterations" were manual engineer script invocations, not automated system learning.

3. **Can the System Currently Generate & Evaluate Reliable Research Signals?**
   - **For Signal Generation:** **PARTIAL**. The system can causally generate signals from its existing 191 indicators and models, but its hypothesis space is severely impoverished due to the absence of market structure and price-action logic.
   - **For Evaluation:** **YES**. The evaluation pipeline is rigorous, causal, and trustworthy.

---

## Section 2 — Architecture Map

The diagram below maps the actual physical architecture of the Treading-AI codebase, distinguishing fully functional operational components from missing or disconnected blocks:

```
+---------------------------------------------------------------------------------------------------------+
|                                        DATA PIPELINE (FUNCTIONAL)                                       |
+---------------------------------------------------------------------------------------------------------+
| Raw HistData M1 CSV/ZIPs                                                                                |
|   └── src/treading_ai/data_collection/downloader.py                                                     |
|       └── Data Integrity & Validation (Duplicate checks, Gap classification, DST conversion)            |
|           └── src/treading_ai/validation/validator.py                                                   |
|               └── Timeframe Resampling (M1 -> M5, M15, M30, H1, H4, left-closed, incomplete candle flags)  |
|                   └── src/treading_ai/preprocessing/resampler.py                                        |
|                       └── Continuous Parquet Storage (data/processed/XAUUSD/<TF>/)                      |
|                           └── src/treading_ai/preprocessing/storage.py                                  |
+---------------------------------------------------------------------------------------------------------+
                                                     │
                                                     ▼
+---------------------------------------------------------------------------------------------------------+
|                                    FEATURE ENGINEERING (FUNCTIONAL)                                     |
+---------------------------------------------------------------------------------------------------------+
| Base M5 Technical Features (Returns, Volatility, Parkinson, Garman-Klass, ATR, EMAs, RSI, MACD, BB)     |
|   └── src/treading_ai/features/technical.py                                                             |
| Cyclical & Session Features (Harmonics, London, NY, Asian, Overlap, Rollover, Friday close, Sunday open)|
|   └── src/treading_ai/features/time_features.py                                                         |
| Higher Timeframe Alignment (H1, H4 backward as-of merge on completed candle close, max_staleness=4d)    |
|   └── src/treading_ai/features/multi_timeframe.py                                                       |
| Partitioning (Warmup drop, NaN ffill & assert zero NaN/Inf, split into Train/Val/Test Parquet)          |
|   └── src/treading_ai/features/pipeline.py -> data/features/XAUUSD_M5_features_[train|val|test].parquet |
+---------------------------------------------------------------------------------------------------------+
                                                     │
                                                     ▼
+---------------------------------------------------------------------------------------------------------+
|                                 MODEL & LABELING LAYER (FUNCTIONAL)                                     |
+---------------------------------------------------------------------------------------------------------+
| Causal Directional Labeling (H=6, 24, 48 bars, weekend & split boundary purge)                         |
|   └── src/treading_ai/models/labeling.py                                                                |
| Triple-Barrier Labeling (2.0 ATR Target, 1.0 ATR Stop, 24 bars, stop-first ambiguity resolution)        |
|   └── src/treading_ai/models/triple_barrier_labeler.py                                                  |
| Macro Volatility Regime Detection (Trailing 288-bar median ATR baseline, trailing percentile, LOW..EXTR)|
|   └── src/treading_ai/models/macro_regime.py                                                            |
| Baseline Classifiers (MajorityClass, DirectionalHeuristic [RSI+Mom], LogisticRegression, RandomForest)  |
|   └── src/treading_ai/models/baselines.py                                                               |
| Chronological Expanding Walk-Forward Validator (3 splits across 2021-2024, boundary purging)            |
|   └── src/treading_ai/models/walk_forward.py                                                            |
+---------------------------------------------------------------------------------------------------------+
                                                     │
                                                     ▼
+---------------------------------------------------------------------------------------------------------+
|                                POLICY & EXECUTION ENGINE (FUNCTIONAL)                                   |
+---------------------------------------------------------------------------------------------------------+
| Selective Trading Policy (Probability thresholding, capacity=1 lockout, non-overlapping vs overlapping) |
|   └── src/treading_ai/policies/selective.py                                                             |
| Execution Cost Model ($0.20 base spread, session multipliers, volatility spread, slippage, commission)   |
|   └── src/treading_ai/backtesting/cost_model.py                                                         |
| Economic Evaluator (Fixed-horizon trade-level simulation, $/oz accounting, friction reconciliation)     |
|   └── src/treading_ai/backtesting/economic_evaluator.py                                                 |
| Triple-Barrier Simulator (Variable holding simulation, stop-first, open gap fills, capacity lockout)    |
|   └── src/treading_ai/backtesting/triple_barrier_simulator.py                                           |
+---------------------------------------------------------------------------------------------------------+
                                                     │
                                                     ▼
+---------------------------------------------------------------------------------------------------------+
|                                    RESEARCH REPORTS (FUNCTIONAL)                                        |
+---------------------------------------------------------------------------------------------------------+
| Static JSON Reports & Markdown Summaries (data/reports/phase[4..8]_*.json, data/reports/*.md)           |
+---------------------------------------------------------------------------------------------------------+

===========================================================================================================
                                       MISSING & DISCONNECTED BLOCKS
===========================================================================================================
 [MISSING] Market Structure Engine (Swing H/L, BOS, CHoCH, Liquidity Pools, Fair Value Gaps, Causal S/R)
 [MISSING] Persistent Trade Journal & Context Recorder (No database, no trade reasoning, no MFE/MAE)
 [MISSING] Trade Failure & Error Attribution Engine (No post-trade diagnostic classification)
 [MISSING] Similar-Case Historical Pattern Retrieval (No vector store, no state-space embedding)
 [MISSING] Continuous Self-Learning Pipeline (No adaptive updating, no automated retraining loop)
 [MISSING] Model Governance & Rollback Registry (No model artifact versioning, no automated gatekeeper)
===========================================================================================================
```

---

## Section 3 — Market Analysis Capability Matrix

Each capability below was independently audited against the actual source code in `src/treading_ai/`:

| Capability Category | Specific Feature / Concept | Implementation & Test Status | Source Code Reference | Microstructure & Data Limitations |
| :--- | :--- | :--- | :--- | :--- |
| **Market Structure** | Swing Highs & Lows | **NOT IMPLEMENTED** | None | Requires causal left/right confirmation window (e.g. $N$-bar pivot). |
| | Higher Highs / Higher Lows / LH / LL | **NOT IMPLEMENTED** | None | Dependent on swing detection state machine. |
| | Break of Structure (BOS) | **NOT IMPLEMENTED** | None | Dependent on confirmed swing level breaks. |
| | Change of Character (CHoCH) | **NOT IMPLEMENTED** | None | Dependent on structural trend-flip classification. |
| | Trend vs Range Classification | **PARTIALLY IMPLEMENTED** | [`technical.py:139-160`](file:///home/bhoot/project/Treading-Ai/src/treading_ai/features/technical.py#L139-L160), [`macro_regime.py:132-159`](file:///home/bhoot/project/Treading-Ai/src/treading_ai/models/macro_regime.py#L132-L159) | Uses EMA slopes/ratios and ATR expansion, but lacks structural swing classification. |
| **Liquidity Analysis** | Equal Highs & Equal Lows (EQH/EQL) | **NOT IMPLEMENTED** | None | Proxy only; bid-only data cannot verify true liquidity cluster depth. |
| | Buy-Side & Sell-Side Liquidity Zones | **NOT IMPLEMENTED** | None | True book depth is unobservable in top-of-book HistData. |
| | Liquidity Sweep Detection | **NOT IMPLEMENTED** | None | Requires detecting price piercing key levels and rapidly reclaiming. |
| | Sweep-and-Reclaim Patterns | **NOT IMPLEMENTED** | None | Dependent on sweep detection. |
| **Support & Resistance** | Causal Zone Detection | **NOT IMPLEMENTED** | None | Must be constructed from strictly historical price rejection clusters. |
| | Zone Retests & Rejection | **NOT IMPLEMENTED** | None | Dependent on zone detection. |
| | Breakouts and False Breakouts | **PARTIALLY IMPLEMENTED** | [`technical.py:200-204`](file:///home/bhoot/project/Treading-Ai/src/treading_ai/features/technical.py#L200-L204), [`run_macro_regime_research.py:305-310`](file:///home/bhoot/project/Treading-Ai/scripts/run_macro_regime_research.py#L305-L310) | Bollinger Band %B/Bandwidth and basic momentum breakout tested; no horizontal level S/R false-break engine. |
| | Zone Strength & Invalidation | **NOT IMPLEMENTED** | None | Dependent on zone detection. |
| **Supply & Demand** | Candidate Supply/Demand Zones | **NOT IMPLEMENTED** | None | Imbalance origin detection not built. |
| | Zone Origin & Departure Strength | **NOT IMPLEMENTED** | None | Displacement metrics exist as returns, but unmapped to zones. |
| | Retest Behaviour & Invalidation | **NOT IMPLEMENTED** | None | Dependent on zone engine. |
| **Price Action** | Candlestick Patterns | **PARTIALLY IMPLEMENTED** | [`technical.py:62-73`](file:///home/bhoot/project/Treading-Ai/src/treading_ai/features/technical.py#L62-L73) | Single-candle geometry (`candle_return`, `candle_span`, `body_to_range`) exists; multi-candle patterns absent. |
| | Rejection Wicks | **PARTIALLY IMPLEMENTED** | [`technical.py:70-71`](file:///home/bhoot/project/Treading-Ai/src/treading_ai/features/technical.py#L70-L71) | `upper_shadow` and `lower_shadow` continuous ratios computed; no thresholded rejection wick signal. |
| | Momentum and Displacement | **IMPLEMENTED AND TESTED** | [`technical.py:56-61,162-205`](file:///home/bhoot/project/Treading-Ai/src/treading_ai/features/technical.py#L56-L61) | Multi-period returns (`ret_1` to `ret_60`), log returns, MACD histogram, and EMA slope tested in [`test_features_technical.py`](file:///home/bhoot/project/Treading-Ai/tests/test_features_technical.py). |
| | Breakout & Reversal Setups | **PARTIALLY IMPLEMENTED** | [`baselines.py:95-176`](file:///home/bhoot/project/Treading-Ai/src/treading_ai/models/baselines.py#L95-L176) | Simple heuristic RSI+momentum rule and momentum breakout tested; structural multi-candle reversal setups absent. |
| **Technical Analysis** | ATR & Volatility Regimes | **IMPLEMENTED AND TESTED** | [`technical.py:114-136`](file:///home/bhoot/project/Treading-Ai/src/treading_ai/features/technical.py#L114-L136), [`macro_regime.py:82-160`](file:///home/bhoot/project/Treading-Ai/src/treading_ai/models/macro_regime.py#L82-L160) | ATR(7, 14, 28), NATR, Parkinson, Garman-Klass, CausalRegimeDetector (LOW..EXTREME) tested in [`test_phase8_macro_regime.py`](file:///home/bhoot/project/Treading-Ai/tests/test_phase8_macro_regime.py). |
| | EMA Moving Averages | **IMPLEMENTED AND TESTED** | [`technical.py:138-160`](file:///home/bhoot/project/Treading-Ai/src/treading_ai/features/technical.py#L138-L160) | EMA(9, 21, 50, 200), distance to EMA, EMA slope, EMA ratios tested in [`test_features_technical.py`](file:///home/bhoot/project/Treading-Ai/tests/test_features_technical.py). |
| | Volume-Weighted Average Price (VWAP) | **NOT TESTABLE WITH CURRENT DATA** | None | HistData contains only tick volume, not institutional transaction volume. True volume-weighted pricing is unavailable. |
| | RSI & Oscillators | **IMPLEMENTED AND TESTED** | [`technical.py:167-205`](file:///home/bhoot/project/Treading-Ai/src/treading_ai/features/technical.py#L167-L205) | RSI(14), normalized RSI, MACD, Bollinger Bands tested in [`test_features_technical.py`](file:///home/bhoot/project/Treading-Ai/tests/test_features_technical.py). |
| | Multi-Timeframe Alignment | **IMPLEMENTED AND TESTED** | [`multi_timeframe.py:47-132`](file:///home/bhoot/project/Treading-Ai/src/treading_ai/features/multi_timeframe.py#L47-L132) | Causal backward as-of alignment of H1 and H4 indicators onto M5 tested in [`test_features_multi_timeframe.py`](file:///home/bhoot/project/Treading-Ai/tests/test_features_multi_timeframe.py). |
| **SMC / ICT Hypotheses** | Order Block Candidates | **NOT IMPLEMENTED** | None | Bid-only OHLC cannot observe actual order book resting institutional liquidity. Proxy algorithms must be explicitly declared as proxies. |
| | Fair Value Gaps (FVG) | **NOT IMPLEMENTED** | None | Causal 3-candle imbalance ($H_{t-2} < L_t$ or $L_{t-2} > H_t$) is readily implementable on M5 data, but absent. |
| | Premium vs Discount Pricing | **NOT IMPLEMENTED** | None | Dependent on swing range calculation (e.g. $50\%$ equilibrium level of recent dealing range). |
| | Liquidity Sweeps & Displacement | **NOT IMPLEMENTED** | None | Absent from existing feature extraction. |
| **Market Context** | Market Trading Sessions | **IMPLEMENTED AND TESTED** | [`time_features.py:74-100`](file:///home/bhoot/project/Treading-Ai/src/treading_ai/features/time_features.py#L74-L100) | Timezone-aware London, NY, Overlap, Asian, cyclical time harmonics tested across DST transitions in [`test_features_time.py`](file:///home/bhoot/project/Treading-Ai/tests/test_features_time.py). |
| | Daily Rollover Settlement Window | **IMPLEMENTED AND TESTED** | [`cost_model.py:126-138`](file:///home/bhoot/project/Treading-Ai/src/treading_ai/backtesting/cost_model.py#L126-L138), [`time_features.py:108-115`](file:///home/bhoot/project/Treading-Ai/src/treading_ai/features/time_features.py#L108-L115) | Mon–Thu 17:00–18:00 NY closure and $12\times$ spread expansion tested in [`test_phase3_labeling.py`](file:///home/bhoot/project/Treading-Ai/tests/test_phase3_labeling.py). |
| | Scheduled Macroeconomic Events | **NOT TESTABLE WITH CURRENT DATA** | None | No economic calendar dataset (CPI, NFP, FOMC) exists in repository. |

---

## Section 4 — Model and Strategy Inventory

Every predictive model, decision policy, and strategy module in the codebase was examined:

### 1. Majority-Class Baseline
- **File Path:** [`src/treading_ai/models/baselines.py:49-93`](file:///home/bhoot/project/Treading-Ai/src/treading_ai/models/baselines.py#L49-L93)
- **Status:** IMPLEMENTED AND TESTED ([`test_phase4_baselines.py`](file:///home/bhoot/project/Treading-Ai/tests/test_phase4_baselines.py)).
- **Input Features:** None (computes empirical priors of training classes).
- **Target Label:** Multi-class $\{-1, 0, 1\}$.
- **Training Procedure:** Calculates class frequencies on training split.
- **Signal Logic:** Always predicts the most frequent class (typically Neutral `0`).
- **Evaluation:** Net PnL = $\$0.00$ (trades = 0, flat).
- **Weaknesses:** Trivial benchmark null hypothesis.
- **Reproducibility:** 100% deterministic.

### 2. Directional Heuristic (RSI + Momentum)
- **File Path:** [`src/treading_ai/models/baselines.py:95-176`](file:///home/bhoot/project/Treading-Ai/src/treading_ai/models/baselines.py#L95-L176)
- **Status:** IMPLEMENTED AND TESTED ([`test_phase4_baselines.py`](file:///home/bhoot/project/Treading-Ai/tests/test_phase4_baselines.py)).
- **Input Features:** `rsi_14`, `ret_10`.
- **Target Label:** Multi-class $\{-1, 0, 1\}$.
- **Training Procedure:** Non-fitted deterministic rule.
- **Signal Logic:** Long if `rsi_14 > 55` and `ret_10 > +0.0005`; Short if `rsi_14 < 45` and `ret_10 < -0.0005`; else 0.
- **Evaluation (Phase 4):** Net PnL = $-\$2,897.40/\text{oz}$, $\text{PF}_{\text{net}} = 0.582$, Net Win Rate = $36.4\%$.
- **Weaknesses:** Naive momentum chasing buys tops and sells bottoms in mean-reverting intraday gold.
- **Reproducibility:** 100% deterministic.

### 3. Multiclass Logistic Regression Baseline
- **File Path:** [`src/treading_ai/models/baselines.py:178-258`](file:///home/bhoot/project/Treading-Ai/src/treading_ai/models/baselines.py#L178-L258)
- **Status:** IMPLEMENTED AND TESTED ([`test_phase4_baselines.py`](file:///home/bhoot/project/Treading-Ai/tests/test_phase4_baselines.py)).
- **Input Features:** All 191 technical, time, and multi-timeframe feature columns.
- **Target Label:** Causal directional label $\{-1, 0, 1\}$ over horizon $H$.
- **Training Procedure:** Fits `StandardScaler` strictly on training split, then fits `sklearn.linear_model.LogisticRegression(C=1.0, max_iter=300, random_state=42)`.
- **Signal Logic:** Argmax probability $\{-1, 0, 1\}$ or probability thresholded via `SelectiveTradingPolicy`.
- **Evaluation:**
  - *Phase 4 ($H=6$, Unfiltered):* Net PnL = $-\$7,719.16/\text{oz}$, $\text{PF}_{\text{net}} = 0.655$.
  - *Phase 5 ($H=6$, Threshold 0.60):* Net PnL = $-\$895.95/\text{oz}$, $\text{PF}_{\text{net}} = 0.793$.
  - *Phase 6 ($H=24$, Threshold 0.60):* Net PnL = $-\$1,340.90/\text{oz}$, $\text{PF}_{\text{net}} = 0.835$.
  - *Phase 8 ($H=24$, Regime-gated, Threshold 0.60):* Net PnL = $-\$709.48/\text{oz}$, $\text{PF}_{\text{net}} = 0.881$.
- **Weaknesses:** Linear decision boundary cannot resolve complex interaction non-linearities. Solver generates `ConvergenceWarning` at `max_iter=300`.
- **Reproducibility:** 100% reproducible with fixed `random_state=42`.

### 4. Random Forest Baseline
- **File Path:** [`src/treading_ai/models/baselines.py:260-337`](file:///home/bhoot/project/Treading-Ai/src/treading_ai/models/baselines.py#L260-L337)
- **Status:** IMPLEMENTED AND TESTED ([`test_phase4_baselines.py`](file:///home/bhoot/project/Treading-Ai/tests/test_phase4_baselines.py)).
- **Input Features:** All 191 feature columns.
- **Target Label:** Multi-class $\{-1, 0, 1\}$.
- **Training Procedure:** `RandomForestClassifier(n_estimators=100, max_depth=10, min_samples_leaf=50, random_state=42, n_jobs=-1)`.
- **Signal Logic:** Argmax of predicted class probabilities.
- **Evaluation (Phase 4):** Net PnL = $-\$4,621.50/\text{oz}$, $\text{PF}_{\text{net}} = 0.684$, Accuracy = $47.8\%$.
- **Weaknesses:** High computational cost on 260k rows; prone to over-predicting the majority neutral class.
- **Reproducibility:** 100% reproducible with fixed seed.

### 5. Selective Trading Policy (Probability Thresholding & Capacity Control)
- **File Path:** [`src/treading_ai/policies/selective.py:36-190`](file:///home/bhoot/project/Treading-Ai/src/treading_ai/policies/selective.py#L36-L190)
- **Status:** IMPLEMENTED AND TESTED ([`test_phase5_selective.py`](file:///home/bhoot/project/Treading-Ai/tests/test_phase5_selective.py)).
- **Input Features:** Model probabilities $P(y=-1)$, $P(y=0)$, $P(y=1)$.
- **Logic:**
  - Abstains ($0$) unless $\max(P_{\text{long}}, P_{\text{short}}) \ge \text{threshold}$.
  - Non-overlapping single-position capacity control: locks out subsequent signals for $H$ bars while a trade is open.
- **Evaluation:** Successfully reduced trade frequency by $60\% - 85\%$, pruning unprofitable trades and improving profit factor from $0.65 \rightarrow 0.88$, but net PnL remained negative.
- **Reproducibility:** 100% deterministic.

### 6. Triple-Barrier Strategy (Volatility-Scaled Exits)
- **File Path:** Labeler: [`src/treading_ai/models/triple_barrier_labeler.py`](file:///home/bhoot/project/Treading-Ai/src/treading_ai/models/triple_barrier_labeler.py), Simulator: [`src/treading_ai/backtesting/triple_barrier_simulator.py`](file:///home/bhoot/project/Treading-Ai/src/treading_ai/backtesting/triple_barrier_simulator.py)
- **Status:** IMPLEMENTED AND TESTED ([`test_phase7_triple_barrier.py`](file:///home/bhoot/project/Treading-Ai/tests/test_phase7_triple_barrier.py)).
- **Configuration:** Profit Target = $2.0 \times \text{ATR}$, Stop Loss = $1.0 \times \text{ATR}$, Max Holding = 24 bars.
- **Execution Rules:** Conservative stop-first handling for ambiguous same-bar breaches, gap-through fills at open, weekend & boundary purging.
- **Evaluation (Phase 7):** Net PnL = $-\$4,368.24/\text{oz}$ across 8,174 trades ($\text{PF}_{\text{net}} = 0.674$).
- **Weaknesses:** The $1.0 \times \text{ATR}$ stop is too close to local noise; $68.0\%$ of trades stopped out, resulting in a net win rate collapse to $31.4\%$.
- **Reproducibility:** 100% deterministic.

### 7. Macro Volatility Regime Policy
- **File Path:** [`src/treading_ai/models/macro_regime.py`](file:///home/bhoot/project/Treading-Ai/src/treading_ai/models/macro_regime.py)
- **Status:** IMPLEMENTED AND TESTED ([`test_phase8_macro_regime.py`](file:///home/bhoot/project/Treading-Ai/tests/test_phase8_macro_regime.py)).
- **Logic:** Identifies LOW, NORMAL, HIGH, EXTREME regimes using trailing 288-bar median ATR and 500-bar percentile rank. Gates directional signals to HIGH/EXTREME regimes.
- **Evaluation (Phase 8):** Gating cut losses from $-\$1,410.58$ down to $-\$709.48/\text{oz}$ and improved profit factor from $0.821 \rightarrow 0.881$, but net PnL remained negative across all folds.
- **Weaknesses:** High volatility provides large price swings ($\$2.65 - \$3.40/\text{oz}$), but directional prediction on M5 bars is essentially symmetric Brownian motion ($\text{win rate} \approx 47\%$).

---

## Section 5 — Data Leakage and Evaluation Risks

A rigorous audit of potential leakage and methodological risks was conducted:

| Risk Category | Specific Failure Mode | Severity | File Reference | Audit Verification & Findings |
| :--- | :--- | :---: | :--- | :--- |
| **Lookahead Leakage** | Feature computation using future rows | **NONE (CLEAN)** | [`technical.py:58-60`](file:///home/bhoot/project/Treading-Ai/src/treading_ai/features/technical.py#L58-L60) | All returns use `.pct_change(k)` / `.shift(k)`. Backward filling (`.bfill()`) was completely eradicated in Phase 2. Zero future information leakage. |
| **Multi-Timeframe Leakage** | Merging incomplete higher-timeframe bars | **NONE (CLEAN)** | [`multi_timeframe.py:101-128`](file:///home/bhoot/project/Treading-Ai/src/treading_ai/features/multi_timeframe.py#L101-L128) | Backward as-of merge explicitly anchors on `_available_timestamp = timestamp + duration`. An M5 bar at 10:55 UTC cannot access the 10:00–11:00 H1 bar until 11:00 UTC. Verified in [`test_features_multi_timeframe.py`](file:///home/bhoot/project/Treading-Ai/tests/test_features_multi_timeframe.py). |
| **Preprocessing Leakage** | Fitting scalers on full dataset or evaluation splits | **NONE (CLEAN)** | [`baselines.py:219-221`](file:///home/bhoot/project/Treading-Ai/src/treading_ai/models/baselines.py#L219-L221) | `StandardScaler` is instantiated and fit strictly inside `model.fit()` on the fold's training split. Test split is isolated. Verified in [`test_phase4_baselines.py:test_scaler_fit_strictly_on_train`](file:///home/bhoot/project/Treading-Ai/tests/test_phase4_baselines.py). |
| **Execution Causality** | Opening fill priced using current bar's completed range | **NONE (CLEAN)** | [`cost_model.py:168-175`](file:///home/bhoot/project/Treading-Ai/src/treading_ai/backtesting/cost_model.py#L168-L175) | Order fill at bar $t+1$ Open strictly receives volatility metrics finalized on or before bar $t$. Synthetic tests confirm zero dependency on bar $t+1$ range. Verified in [`test_phase3_labeling.py`](file:///home/bhoot/project/Treading-Ai/tests/test_phase3_labeling.py). |
| **Partition Contamination** | Inadvertent leakage into 2026 Test partition | **NONE (CLEAN)** | [`config.py:78-79`](file:///home/bhoot/project/Treading-Ai/src/treading_ai/config.py#L78-L79) | 2026 Test partition (`XAUUSD_M5_features_test.parquet`) has zero read/write references across all research and backtest scripts. Regression tests verify it remains frozen. |
| **Bid-Only Market Limitation** | Unobserved Ask prices and Level 2 depth | **MEDIUM** | [`cost_model.py:44-52`](file:///home/bhoot/project/Treading-Ai/src/treading_ai/backtesting/cost_model.py#L44-L52) | HistData provides only Bid quotes. Ask prices are synthetic approximations via session-dependent spread models ($0.20 base). True order book depth, liquidity depletion, and queue delays are unobservable. |
| **Tick Volume Limitation** | HistData volume is tick frequency, not contract volume | **MEDIUM** | [`technical.py:21`](file:///home/bhoot/project/Treading-Ai/src/treading_ai/features/technical.py#L21) | In Forex/Gold OTC markets, tick count measures update frequency, not traded lot size. Volume-weighted indicators (VWAP) cannot be accurately computed. |
| **Solver Convergence** | Logistic Regression solver reaches iteration limit | **LOW** | [`baselines.py:196`](file:///home/bhoot/project/Treading-Ai/src/treading_ai/models/baselines.py#L196) | L-BFGS hits `max_iter=300` in training folds. While models fit successfully, optimization does not reach full asymptotic convergence on 191 features without higher iterations or feature selection. |

---

## Section 6 — Trade Auditing and Self-Learning Gap Analysis

The long-term project vision requires the AI to record every decision, audit failures, learn from recurring mistakes, and prevent repeated errors. Here is the strict audit of where the system stands:

### 6.1 What the System Currently Does
1. **Logs Aggregate Performance:** Evaluates total trades, gross/net PnL, profit factors, win rates, drawdowns, and friction breakdowns per fold.
2. **Records In-Memory Trade Instances:** Stores entry/exit timestamps, fills, and individual PnL during a simulation run.
3. **Applies Fixed Rules:** Applies static thresholding and capacity lockout.

### 6.2 What is Completely Missing
1. **No Persistent Trade Journal:**  
   Simulated trades are discarded after script execution. There is no SQL database, Parquet journal table, or append-only log storing individual trade records with market context.
2. **No Decision Reasoning Attribution:**  
   The system records *that* a model predicted BUY or SELL, but does **not record *why***:
   - What was the market structure state at signal time?
   - What were the top contributing features (SHAP / feature attributions)?
   - Which higher-timeframe indicators supported or contradicted the trade?
   - What was the expected trade invalidation level?
3. **No Intrabar Excursion Tracking (MFE / MAE):**  
   Neither `EconomicEvaluator` nor `TripleBarrierSimulator` records the Maximum Favorable Excursion (how far the trade went into profit before exiting) or Maximum Adverse Excursion (maximum drawdown experienced while open).
4. **No Failure Classification Taxonomy:**  
   The system cannot categorize trade losses into distinct error buckets:
   - *Type A: Analytical Error* (reasoning was flawed; e.g. buying into major resistance).
   - *Type B: Timing / Execution Error* (direction was right, but entered too late or stopped out by spread).
   - *Type C: Regime Mismatch* (model assumed a trend during low-volatility compression).
   - *Type D: Unavoidable Friction / Noise* (trade was statistically sound, but lost within normal variance).
5. **No Similar-Case Historical Retrieval:**  
   The system cannot search historical memory for previous market states similar to the current candle to evaluate past outcomes.
6. **No Feedback Loop or Self-Learning:**  
   There is **no automated learning pipeline**. The model does not adjust its weights, rules, or thresholds based on audited mistakes. Every model fit is an offline batch script run from scratch.

---

## Section 7 — Prioritized Remediation Plan

To bridge the gap between the current static baseline engine and an evidence-driven, adaptive market-analysis AI, we propose a disciplined, four-phase engineering roadmap.

```
+---------------------------------------------------------------------------------------------------------+
|                                    PHASED REMEDIATION ROADMAP                                           |
+---------------------------------------------------------------------------------------------------------+
| Phase 9B: Causal Market Structure & Liquidity Engine                                                    |
|   └── Swings, BOS, CHoCH, Fair Value Gaps (FVG), Causal Support/Resistance Zones                        |
+---------------------------------------------------------------------------------------------------------+
                                                     │
                                                     ▼
+---------------------------------------------------------------------------------------------------------+
| Phase 10: Persistent Trade Journal & Decision Reasoning Recorder                                        |
|   └── Trade Database, Feature Attribution, Invalidation Levels, MFE/MAE Excursion Tracking              |
+---------------------------------------------------------------------------------------------------------+
                                                     │
                                                     ▼
+---------------------------------------------------------------------------------------------------------+
| Phase 11: Trade Error Attribution & Failure Taxonomy Engine                                             |
|   └── Post-Trade Diagnostic Classification, Regime Mismatch Detection, Friction Drag Auditing           |
+---------------------------------------------------------------------------------------------------------+
                                                     │
                                                     ▼
+---------------------------------------------------------------------------------------------------------+
| Phase 12: Controlled Model Governance & Challenger Validation Engine                                    |
|   └── Model Registry, Case-Based Memory Retrieval, Walk-Forward Challenger Gates, Automated Rollback    |
+---------------------------------------------------------------------------------------------------------+
```

### Phase 9B: Causal Market Structure & Liquidity Engine
- **Objective:** Implement causal, mathematically rigorous market structure and price-action features (Swing Highs/Lows, BOS, CHoCH, Fair Value Gaps [FVG], and causal Support/Resistance zones) on M5, H1, and H4 timeframes.
- **Files Affected:**
  - `src/treading_ai/features/market_structure.py` (New)
  - `src/treading_ai/features/pipeline.py` (Integrate new structure features)
  - `tests/test_features_market_structure.py` (New)
- **Dependencies:** Existing `TimeframeResampler` and `MultiTimeframeAligner`.
- **Tests Required:**
  - Causal pivot confirmation: no swing point labeled until confirmation window ($N$ bars) has elapsed.
  - Zero forward-looking leakage in BOS and CHoCH detection.
  - FVG causal formation ($H_{t-2} < L_t$ or $L_{t-2} > H_t$) and mitigation tracking.
  - Truncation invariance: historical structure remains identical when data is truncated.
- **Acceptance Criteria:** 100% causal structure features; passing unit tests; regenerated training feature dataset with verified row/column counts.
- **Data Required:** 2021–2024 Training partition only.

### Phase 10: Persistent Trade Journal & Decision Reasoning Recorder
- **Objective:** Build an institutional trade recording system that logs every signal (BUY, SELL, NO-TRADE), market state snapshot, decision reasoning, expected invalidation price, and full trade lifecycle with MFE/MAE.
- **Files Affected:**
  - `src/treading_ai/audit/trade_journal.py` (New)
  - `src/treading_ai/backtesting/economic_evaluator.py` (Hook into journal recorder)
  - `tests/test_trade_journal.py` (New)
- **Dependencies:** Phase 9B structure engine.
- **Tests Required:**
  - Exact reconciliation between trade journal entries and backtest summary metrics.
  - Accurate MFE/MAE calculation across all simulated trades.
  - Serialization and reload round-trip testing.
- **Acceptance Criteria:** Every simulated trade logs full market context, MFE, MAE, friction breakdown, and decision reasoning to persistent Parquet/SQLite storage.
- **Data Required:** 2021–2024 Training partition only.

### Phase 11: Trade Error Attribution & Failure Taxonomy Engine
- **Objective:** Automatically audit completed trades from the Trade Journal and classify failure causes into distinct diagnostic buckets (Analytical Error, Timing Error, Regime Mismatch, Friction Drag).
- **Files Affected:**
  - `src/treading_ai/audit/error_classifier.py` (New)
  - `tests/test_error_classifier.py` (New)
- **Dependencies:** Phase 10 Trade Journal.
- **Tests Required:**
  - Deterministic classification of synthetic error scenarios.
  - Statistical independence of error categories.
- **Acceptance Criteria:** Automated diagnostic report breaking down failure causes across walk-forward folds.
- **Data Required:** 2021–2024 Training partition only.

### Phase 12: Controlled Model Governance & Challenger Validation Engine
- **Objective:** Implement a production ML model governance framework: model artifact registry, versioning, automated challenger evaluation against pre-registered gates, and rollback capability.
- **Files Affected:**
  - `src/treading_ai/governance/model_registry.py` (New)
  - `src/treading_ai/governance/challenger_gate.py` (New)
  - `tests/test_model_governance.py` (New)
- **Dependencies:** Phases 9B, 10, 11.
- **Tests Required:**
  - Challenger gate strictly prevents promotion of models failing out-of-sample cost hurdles.
  - Automated rollback verification.
  - Drift detection sensitivity tests.
- **Acceptance Criteria:** End-to-end model registry with immutable experiment records, pre-registered approval gates, and zero unverified self-learning claims.
- **Data Required:** 2021–2024 Training partition; 2025 Validation partition accessed ONCE only if a challenger qualifies under locked training criteria.

---

## Section 8 — Recommended Production Architecture

Instead of rewriting the codebase, the recommended architecture **reuses the proven, institutional-grade components** while introducing modular engines for Market Structure, Trade Auditing, and Governance:

```
+---------------------------------------------------------------------------------------------------------+
|                                    RECOMMENDED PRODUCTION ARCHITECTURE                                  |
+---------------------------------------------------------------------------------------------------------+

  1. DATA & PREPROCESSING LAYER (RETAIN & REUSE)
     - HistData M1 Ingestion, Validation, Timezone Conversion, M5/H1/H4 Resampling, Parquet Storage
     - [RETAINED AS-IS: src/treading_ai/data_collection/, validation/, preprocessing/]

  2. CAUSAL FEATURE & STRUCTURE ENGINE (ENHANCE)
     - Technical Features (Returns, Volatility, ATR, EMAs, RSI, MACD, BB) [RETAINED]
     - Time & Session Features (London, NY, Asian, Overlap, Rollover) [RETAINED]
     - Multi-Timeframe Alignment (H1, H4 backward as-of merge) [RETAINED]
     - [NEW: src/treading_ai/features/market_structure.py] (Causal Swings, BOS, CHoCH, FVG, Causal S/R)

  3. MARKET REGIME & CONTEXT ENGINE (RETAIN & EXPAND)
     - Causal Volatility Regimes (LOW, NORMAL, HIGH, EXTREME) [RETAINED]
     - Market Structure State (Bullish Trending, Bearish Trending, Premium/Discount Range) [NEW]

  4. DECISION & REASONING ENGINE (EXPAND)
     - Probabilistic Classifiers & Selective Thresholding [RETAINED]
     - Explainable Reasoning Formulator (Combines Structure + Regimes + Model Probabilities) [NEW]
     - Explicit Invalidation Level Definer (Pre-Trade Stop & Invalidation Anchors) [NEW]

  5. EXECUTION & COST SIMULATOR (RETAIN & REUSE)
     - Execution Cost Model ($0.20 spread, session multipliers, slippage, commission) [RETAINED]
     - Non-Overlapping Single-Position Capacity Control [RETAINED]
     - Triple-Barrier Simulator (Stop-first, open gap fills) [RETAINED]

  6. PERSISTENT TRADE JOURNAL & AUDIT ENGINE (NEW CORE COMPONENT)
     - [NEW: src/treading_ai/audit/trade_journal.py] (Logs Signal, Context, Reasoning, MFE, MAE, Outcome)
     - [NEW: src/treading_ai/audit/error_classifier.py] (Attribution: Analysis vs Timing vs Regime vs Friction)

  7. MODEL GOVERNANCE & CHALLENGER VALIDATOR (NEW CORE COMPONENT)
     - [NEW: src/treading_ai/governance/model_registry.py] (Immutable artifacts, lineage, rollback)
     - [NEW: src/treading_ai/governance/challenger_gate.py] (Pre-registered walk-forward challenger tests)
```

---

## Section 9 — Go / No-Go Decision

### Definitive Recommendation: **PROCEED TO PHASE 9B (Causal Market Structure & Liquidity Engine)**

### Rigorous Evidence-Based Justification:
1. **The Machine Learning Models Have Exhausted the Current Feature Space:**  
   Across Phases 4, 5, 6, 7, and 8, we evaluated Logistic Regression, Random Forest, multi-horizon targets, probability thresholds, triple-barrier exits, and volatility-regime gating. **All 41+ configurations failed to produce positive net expectancy.** Fitting more complex machine learning models or attempting "self-learning" on the existing 191 indicators is guaranteed to fail because the input features represent purely continuous momentum and oscillator math without any understanding of market structure.
2. **Gold Intraday Microstructure Requires Structural Anchors:**  
   XAUUSD price action is driven by liquidity sweeps, swing structure breaks, session opens, and reaction to key price levels. The current model cannot tell whether the price is at a 4-hour swing high, inside a Fair Value Gap, or testing a multi-day support zone. It only knows that `rsi_14 = 52.3` and `ema_slope_50 = 0.0001`.
3. **No Self-Learning Can Occur Without Trade Journaling & Attribution:**  
   Attempting to build an adaptive learning AI before creating a persistent trade journal and error classification taxonomy is building on sand. The system cannot learn from its mistakes until it can explicitly record and categorize them.
4. **Immediate Action:**  
   Execute **Phase 9B** strictly inside the 2021–2024 training dataset. Implement causal swing detection, BOS, CHoCH, and FVG features with comprehensive unit tests proving zero future leakage, and evaluate whether market-structure features improve out-of-sample directional edge before building the trade journal in Phase 10.
