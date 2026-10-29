# Phase 15: Research Integrity, Reproducibility, and Statistical Validity Audit

**Audit Date**: October 29, 2026  
**Lead Auditor**: Senior Quantitative Research Engineer & Financial ML Auditor  
**Repository**: `balaji3245/Treading-Ai`  
**Target Candidates**: Candidate 5 (Peak Liquidity Session Swing, $H=96$), Candidate 0–6 Suite (Phase 13 & 14)  
**Dataset Under Scope**: Historical XAUUSD 5-Minute Data, 2021-01-03 to 2024-12-31 (260,821 bars)  
**Protected Partitions**: 2025 Validation Partition (70,759 bars — UNINSPECTED); 2026 Test Partition (28,868 bars — FROZEN)  

---

## 1. Executive Summary & Audit Verdict

### Final Audit Verdict

$$\mathbf{RESEARCH\ PIPELINE\ VERIFIED\ —\ EDGE\ UNPROVEN}$$

### Executive Synopsis
An independent forensic audit was conducted on the Treading-AI research pipeline across Phases 11 through 14, focusing on Candidate 5 (Peak Liquidity Session Swing, $H=96$ bars / 8 hours), its antecedent candidates, the causal feature pipeline, walk-forward validation splits, and statistical testing methodologies.

The audit confirms that the quantitative research infrastructure is **operationally sound, causally strict, and free of fatal look-ahead bias, cross-partition leakage, or PnL accounting errors**. Reported performance figures across Phase 13 and Phase 14 reproduce with bitwise and sub-penny precision from raw execution records.

However, Candidate 5 **fails to demonstrate a statistically significant or economically viable trading edge**. Its negative net PnL ($-\$73.72/\text{oz}$), net profit factor ($0.974$), negative net expectancy ($-\$0.139/\text{trade}$), moving-block bootstrap confidence interval spanning zero ($[-\$1.19, +\$1.02]$), and profound dependence on a post-hoc selected session window mandate that the candidate remain disqualified. The **No-Trade Baseline remains the benchmark**.

---

## 2. Independent Reproduction Audit & Artifact Parity

### Verification of Reported Metrics
All primary metrics reported in `reports/phase13_higher_timeframe_research.md` and `reports/phase14_candidate5_robustness_audit.md` were independently recalculated directly from the raw experiment artifacts (`reports/phase13_htf_experiment_results.json` and `reports/phase14_candidate5_diagnostic_data.json`) and underlying trade arrays.

| Metric | Phase 13 Reported | Phase 14 Audited | Phase 15 Independent Recalculation | Parity Status |
| :--- | :---: | :---: | :---: | :---: |
| **Total Trades** | 531 | 531 | 531 | **EXACT MATCH** |
| **Holding Horizon** | 96 bars (8.0h) | 96 bars (8.0h) | 96 bars (8.0h) | **EXACT MATCH** |
| **Gross PnL** | $+\$265.08/\text{oz}$ | $+\$265.08/\text{oz}$ | $+\$265.0809999999972/\text{oz}$ | **EXACT MATCH** |
| **Total Friction** | $\$338.80/\text{oz}$ | $\$338.80/\text{oz}$ | $\$338.804/\text{oz}$ | **EXACT MATCH** |
| **Net PnL (Base)** | $-\$73.72/\text{oz}$ | $-\$73.72/\text{oz}$ | $-\$73.72300000000284/\text{oz}$ | **EXACT MATCH** |
| **Net PnL (Stress)** | $-\$207.33/\text{oz}$ | $-\$207.33/\text{oz}$ | $-\$207.33400000000282/\text{oz}$ | **EXACT MATCH** |
| **Gross Expectancy** | $+\$0.499/\text{trade}$ | $+\$0.499/\text{trade}$ | $+\$0.49921092278718865/\text{trade}$ | **EXACT MATCH** |
| **Friction Expectancy** | $\$0.638/\text{trade}$ | $\$0.638/\text{trade}$ | $\$0.6380489642184557/\text{trade}$ | **EXACT MATCH** |
| **Net Expectancy** | $-\$0.139/\text{trade}$ | $-\$0.139/\text{trade}$ | $-\$0.13883804143126713/\text{trade}$ | **EXACT MATCH** |
| **Gross Profit Factor**| 1.101 | 1.101 | 1.1013279073847755 | **EXACT MATCH** |
| **Net Profit Factor** | 0.974 | 0.974 | 0.9736358389233895 | **EXACT MATCH** |
| **Net Win Rate** | 48.2% | 48.21% | 48.21092278719397% | **EXACT MATCH** |
| **Max Drawdown** | $\$440.31/\text{oz}$ | $\$440.31/\text{oz}$ | $\$440.3070000000018/\text{oz}$ | **EXACT MATCH** |
| **Overlap Violations** | 0 | 0 | 0 | **EXACT MATCH** |

### Fold and Calendar Year Decomposition Parity

```
+---------------------------------------------------------------------------------------------------------+
| Partition / Split  | Trades | Gross PnL ($) | Friction ($) | Net PnL ($)  | Net Exp ($) | Net PF  | Win Rate|
+--------------------+--------+---------------+--------------+--------------+-------------+---------+---------+
| Fold 1 (2022 OOS)  |   208  |   +72.23      |    125.77    |   -53.54     |   -0.257    |  0.948  |  47.12% |
| Fold 2 (2023 OOS)  |   142  |    +5.12      |     82.88    |   -77.76     |   -0.548    |  0.887  |  47.89% |
| Fold 3 (2024 OOS)  |   181  |  +187.73      |    130.15    |   +57.57     |   +0.318    |  1.053  |  49.72% |
+--------------------+--------+---------------+--------------+--------------+-------------+---------+---------+
| Total Aggregate    |   531  |  +265.08      |    338.80    |   -73.72     |   -0.139    |  0.974  |  48.21% |
+--------------------+--------+---------------+--------------+--------------+-------------+---------+---------+
```

### Artifact Paths and Integrity Check
- **Phase 13 Experiment Script**: `scripts/run_phase13_htf_research.py` (27,213 bytes, SHA verified)
- **Phase 13 Output Report**: `reports/phase13_higher_timeframe_research.md` (23,007 bytes)
- **Phase 13 Results JSON**: `reports/phase13_htf_experiment_results.json` (20,660 bytes)
- **Phase 14 Audit Script**: `scripts/audit_candidate5_deep.py` (29,059 bytes)
- **Phase 14 Output Report**: `reports/phase14_candidate5_robustness_audit.md` (23,030 bytes)
- **Phase 14 Diagnostic JSON**: `reports/phase14_candidate5_diagnostic_data.json` (10,310 bytes)

**Reproducibility Assessment**: **100% REPRODUCIBLE**. No discrepancies, data tampering, or metric divergences exist between the raw experiment outputs and the published Phase 13/14 reports.

---

## 3. Causal Integrity & Leakage Prevention Audit

The codebase was scrutinized line-by-line for six critical failure modes common in quantitative ML backtests:

### 3.1 Look-Ahead Bias in Market Structure Features
- **Component**: `treading_ai.features.market_structure.MarketStructureEngine`
- **Audit Findings**:
  1. Swing Highs and Swing Lows require $N_L=5$ left bars and $N_R=5$ right bars.
  2. The pivot confirmation mechanism strictly requires $N_R$ subsequent lower highs (or higher lows) to complete before emitting the event.
  3. A pivot occurring at bar index $i$ is confirmed and visible to the agent only at bar index $i + N_R$, never at bar index $i$.
  4. Truncation Invariance: Slicing the dataframe at any arbitrary bar $T$ and computing market structure features produces bitwise identical features to computing on the full dataset up to $T$.
  5. Distance to unformed structures (e.g. Fair Value Gaps, unbroken SR levels) is initialized to a neutral finite sentinel ($100.0 \times \text{ATR}$), preventing NaNs from creating look-ahead signals during model fitting.
- **Evidence Path**: `tests/test_features_pipeline.py` (`test_pivot_confirmation_timing`, `test_truncation_invariance`).

### 3.2 Feature Leakage Across Timeframes
- **Component**: `treading_ai.features.multi_timeframe.MultiTimeframeAligner`
- **Audit Findings**:
  1. High-timeframe bars (H1, H4) are aggregated strictly from completed lower-timeframe bars.
  2. To merge H1/H4 indicators into M5 candles, the aligner defines `available_timestamp = bar_open + duration`.
  3. Merging is performed via a backward `as_of` join on `available_timestamp <= m5_bar_open`.
  4. For example, an H1 bar opening at 12:00:00 closes at 13:00:00; its features become visible to the M5 execution stream strictly at the 13:00:00 M5 candle or later. No M5 candle between 12:00:00 and 12:55:00 receives information from the 12:00-13:00 H1 bar.
- **Evidence Path**: `src/treading_ai/features/multi_timeframe.py` (lines 85–130).

### 3.3 Label Leakage & Pre-Trade Execution Independence
- **Component**: `treading_ai.models.labeling.CausalDirectionalLabeler`
- **Audit Findings**:
  1. Decision occurs at bar $t$ close.
  2. Simulated entry executes at bar $t+1$ Open.
  3. Simulated exit executes at bar $t+1+H$ Open.
  4. Pre-Trade Volatility Causality: Entry fill costs (spread and slippage) depend strictly on bar $t$ ATR and candle range, never bar $t+1$ ATR or range. Exit fill costs depend strictly on bar $t+H$ ATR and candle range, never bar $t+1+H$ range.
  5. Synthetic corruption of bar $t+1$ and bar $t+1+H$ completed high/low ranges produces zero change in fill prices or net returns.
- **Evidence Path**: `tests/test_phase3_labeling.py` (`test_no_bar_uses_own_completed_range_to_price_open`).

### 3.4 Walk-Forward Fold Boundary Purging
- **Component**: `treading_ai.models.walk_forward.ChronologicalWalkForward`
- **Audit Findings**:
  1. In expanding walk-forward splits, the boundary between the training fold and out-of-sample test fold requires strict purging of horizon $H$ and embargo $E$ bars.
  2. Code inspection: `clean_train_idxs = train_idxs[:-purge_window]`, where `purge_window = 1 + horizon + embargo`.
  3. This guarantees that labels in the training set cannot peek into the out-of-sample evaluation period, eliminating cross-fold return leakage.
- **Evidence Path**: `src/treading_ai/models/walk_forward.py` (lines 45–90).

---

## 4. Partition Boundary & Data Protection Verification

A strict zero-access rule governs the out-of-sample validation and test datasets. The repository was audited to verify that data boundaries are enforced in code, rather than merely asserted in narrative text.

### 4.1 Physical File Boundaries
```
data/features/
├── XAUUSD_M5_features_train.parquet   (260,821 rows | 2021-01-03 -> 2024-12-31) [ACTIVE RESEARCH]
├── XAUUSD_M5_features_val.parquet     ( 70,759 rows | 2025-01-01 -> 2025-12-31) [PROTECTED - UNTOUCHED]
└── XAUUSD_M5_features_test.parquet    ( 28,868 rows | 2026-01-01 -> 2026-06-30) [FROZEN - STRICT PROHIBITION]
```

### 4.2 Code Inspection for Data Access
A comprehensive filesystem search across all research scripts (`scripts/run_phase*.py`, `scripts/audit_*.py`) confirms:
1. `XAUUSD_M5_features_val.parquet` has **ZERO read occurrences** across Phases 11, 12, 13, 14, and 15.
2. `XAUUSD_M5_features_test.parquet` has **ZERO read occurrences** across the entire repository.
3. Every script explicitly anchors its data ingest to:
   ```python
   train_path = Path("data/features/XAUUSD_M5_features_train.parquet")
   train_df = pd.read_parquet(train_path)
   ```
4. Partition boundaries are physically isolated and enforced at the file I/O layer. No automated script, test harness, or diagnostic utility has accessed or evaluated the protected partitions.

---

## 5. Selection Bias & Historical Search Space Audit

### 5.1 Candidate 5 Discovery Lineage
Candidate 5 did not emerge from an a priori theoretical hypothesis; it was discovered through iterative diagnostic decompositions of historical failures:

```
[Phase 4: Baselines]
  -> Fixed-horizon intraday (H=6, H=12). All failed due to spread friction ($1.20 round-turn vs small moves).
       |
[Phase 9B/10/11: Market Structure & Adaptive Retraining]
  -> Challenger Candidate D evaluated across 2021-2024. Lost -$895.74/oz.
       |
[Phase 12: Forensic Error Audit]
  -> Candidate D trades were decomposed across 5 intraday session windows.
  -> Finding: Asian session lost -$166.66/oz, while London/NY Overlap gained +$343.66/oz gross.
       |
[Phase 13: Higher Timeframe Research]
  -> Candidate 5 was synthesized post-hoc specifically to restrict trading to the London/NY Overlap
     (12:00-16:30 UTC) and extend horizon to H=96 (8h).
       |
[Phase 14: Forensic Robustness Audit]
  -> Sensitivity testing revealed extreme instability across horizon, threshold, direction, and season.
```

### 5.2 Estimated Historical Search Space
To evaluate the true multiple testing burden, all documented parameter sweeps and candidate evaluations conducted on the 2021–2024 training data were cataloged:

| Research Dimension | Variations Tested Across Phases 4–14 |
| :--- | :--- |
| **Holding Horizons** | $H \in \{6, 12, 24, 48, 72, 84, 96, 108, 120, 288\}$ (10 horizons) |
| **Probability Thresholds** | $\tau \in \{0.50, 0.55, 0.60, 0.65, 0.70\}$ (5 thresholds) |
| **Session Windows** | Asian, London Morning, London/NY Overlap, NY Afternoon, Daily Rollover (5 windows) |
| **Feature Sets** | Technicals-only, Technicals + Market Structure (FVG/SR/BOS), MTF H1/H4 (3 architectures) |
| **Model Families** | Dummy, Logistic Regression, Random Forest, XGBoost, Error-Retrained Adaptive (5 algorithms) |
| **Formal Candidate Variants** | Incumbent, Cand A, Cand B, Cand C, Cand D, Cand 0, Cand 1, Cand 2, Cand 3, Cand 4, Cand 5, Cand 6 (12 candidates) |

### 5.3 Selection-Bias Magnitude Determination
While the documented configurations exceed 50 distinct trial specifications, researchers engaged in exploratory ad-hoc script runs and iterative error inspections throughout earlier phases without recording every intermediate diagnostic run in an immutable centralized ledger.

**Formal Determination**: Per audit requirements, the **selection-bias magnitude must be formally classified as QUANTITATIVELY UNBOUNDED AND UNKNOWN**. 

Because Candidate 5 was designed after observing that the London/NY Overlap was the most profitable window in prior failed experiments on the exact same dataset, its nominal gross profitability ($+\$265.08/\text{oz}$) is heavily contaminated by retrospective data snooping.

---

## 6. Moving-Block Bootstrap & Statistical Methodology Audit

### 6.1 Bootstrap Implementation Verification
Candidate 5's return distribution was evaluated using a moving-block bootstrap (`block_bootstrap_ci` in `scripts/audit_candidate5_deep.py`):
- **Resample Count**: $B = 2,000$ bootstrap iterations.
- **Statistic**: Arithmetic Mean Net Expectancy per trade ($\mu$).
- **Percentile Interval**: Empirical 2.5% and 97.5% quantiles.

### 6.2 Block Size Choice & Trade Dependence Audit
- **Block Size**: 10 contiguous trades.
- **Physical Duration**:
  - Each trade holds for 96 M5 bars ($8.0$ active trading hours).
  - Positions are strictly non-overlapping (at most one position at any time).
  - 10 contiguous trades represent 80 active trading hours spanning approximately 10 trading sessions ($\sim 2$ calendar weeks).
- **Serial Correlation Analysis**:
  - Net return autocorrelation at Lag 1: $r_1 = +0.0518$
  - Net return autocorrelation at Lag 2: $r_2 = -0.0546$
  - Lags 3–10: All $|r_k| < 0.06$.
- **Audit Assessment**:
  - The serial autocorrelation of trade returns is low, indicating that individual non-overlapping trades behave largely as independent samples.
  - However, market volatility regimes and spread conditions persist over multi-week horizons. Selecting a block size of 10 trades ($80$ trading hours / $14$ calendar days) preserves local volatility clustering and macro-regime dependency. The block-size choice is **methodologically sound and conservative**.

### 6.3 Confidence Interval and Hypothesis Test
- **Observed Net Expectancy**: $-\$0.1388/\text{trade}$
- **Moving-Block Bootstrap 95% CI**: $[-\$1.1885, +\$1.0242/\text{trade}]$
- **Parametric Two-Sided t-test**: $t = -0.2231, \quad p = 0.8236$
- **Wilcoxon Signed-Rank Test**: $p = 0.4407$

**Statistical Conclusion**: The 95% bootstrap confidence interval broadly straddles zero. The null hypothesis of zero edge ($H_0: \mu = 0$) cannot be rejected at any conventional significance level ($\alpha = 0.05, 0.10$). The reported statistical metrics **fully and unambiguously support the conclusion that Candidate 5 has no proven statistical edge**.

---

## 7. Prespecified vs. Exploratory Status of Subgroups

In Phase 14, detailed breakdowns by calendar season and trade direction were reported. The audit evaluated whether these findings represent pre-registered research hypotheses or post-hoc observations.

```
+---------------------------------------------------------------------------------------------------------+
| Subgroup Decomposition  | Trades | Gross PnL ($) | Friction ($) | Net PnL ($)  | Net Exp ($) | Win Rate |
+-------------------------+--------+---------------+--------------+--------------+-------------+----------+
| Summer (EDT/BST)        |   338  |   -138.28     |    213.92    |   -352.19    |   -1.042    |  43.20%  |
| Winter (EST/GMT)        |   193  |   +403.36     |    124.89    |   +278.47    |   +1.443    |  57.00%  |
+-------------------------+--------+---------------+--------------+--------------+-------------+----------+
| Long Positions          |   257  |   +193.98     |    126.75    |    +67.24    |   +0.262    |  49.42%  |
| Short Positions         |   274  |    +71.10     |    212.06    |   -140.96    |   -0.514    |  47.08%  |
+-------------------------+--------+---------------+--------------+--------------+-------------+----------+
```

### Audit Findings:
1. **Pre-Specification Status**:
   - In the Phase 13 research specification, the hypothesis focused strictly on holding horizon extension ($H=24 \to 288$) and liquidity session filtering.
   - Seasonal and directional breakdowns were **NOT** prespecified hypotheses.
2. **Post-Hoc Nature**:
   - The winter outperformance ($+\$278.47$ vs Summer $-\$352.19$) and long outperformance ($+\$67.24$ vs Short $-\$140.96$) were discovered post-hoc in Phase 14 while attempting to explain the failure of Folds 1 and 2.
3. **Risk of Data Snooping**:
   - Gold underwent a massive macro bull run in late 2023 and 2024, heavily flattering Long trades and Winter quarters in Fold 3.
   - Filtering the strategy to "Longs only in Winter" would represent classical retrospective overfitting (narrative fallacy).
4. **Classification**:
   - **EXPLORATORY POST-HOC FINDINGS ONLY**. These patterns cannot be used as strategy filters or promotion justifications without prospective, pre-registered testing on untouched out-of-sample data.

---

## 8. Cost Model Realism & Execution Validity

### 8.1 Synthetic vs. Executable Cost Structure
The HistData source dataset provides Bid prices only. All transaction costs in the Treading-AI pipeline are **synthetic mathematical approximations**:

| Component | Modeled Value | Real-World Market Condition | Divergence Risk |
| :--- | :--- | :--- | :--- |
| **Base Spread** | $\$0.20/\text{oz}$ ($2.0$ pips) | Tight during London/NY ($1.5–2.5$ pips); widens sharply during CPI/FOMC ($5.0–15.0$ pips) | Moderate |
| **Base Slippage**| $\$0.05/\text{oz}$ | Limit orders face non-fill risk; market orders during volatility face asymmetric negative slippage | High |
| **Commission** | $\$0.05/\text{oz}$ per leg ($\$5/\text{lot}$) | Standard institutional prime-of-brokerage schedule | Low |
| **Rollover Break**| $12.0\times$ spread penalty ($2.40/\text{oz}$) | Retail brokers routinely widen gold spreads to $\$3.00–\$8.00$ at 17:00 NY | Low |
| **Queue Priority**| Instantaneous at Bid/Ask | Real order book priority requires limit queue simulation | High |
| **Intra-Candle** | Order of High vs Low unobservable | M5 OHLC cannot resolve whether stop or target was hit first | Critical (if stops used) |

### 8.2 Empirical Cost Stress & Break-Even Analysis
- **Base Cost Scenario**: Round-turn friction $\approx \$0.638/\text{trade}$. Net PnL = $-\$73.72/\text{oz}$.
- **Stressed Cost Scenario** (Spread $\$0.30$, Slippage $\$0.075$): Round-turn friction $\approx \$0.890/\text{trade}$. Net PnL plunges to $-\$207.33/\text{oz}$.
- **Break-Even Multiplier**: Candidate 5 requires a cost multiplier of $\le 0.782$ (equivalent to a maximum base spread of $\$0.156/\text{oz}$ or $1.56$ pips) to achieve zero net PnL.
- **Execution Validity Determination**:
  - The backtest does **NOT** prove executable profitability in live markets.
  - Because costs are synthetic and calculated from bid-only data, any strategy with a marginal or negative edge in backtesting will suffer even steeper losses when exposed to live execution queue friction, asymmetric slippage, and spread widening during economic releases.

---

## 9. Identified Defects, Remediation & Regression Testing

### 9.1 Identified Defect: Static Weekend Threshold on Multi-Session Horizons
- **Severity**: Low / Latent Research Tooling Bug.
- **Component**: `treading_ai.models.labeling.CausalDirectionalLabeler`
- **Description**:
  The constructor parameter `weekend_threshold_hours` was hardcoded to default to `24.0` hours. For intraday horizons ($H \le 48$), this reliably purged weekend crossings. However, for Candidate 6 ($H=288$ bars = $24.0$ trading hours), a standard weekday position enters Monday 08:00 and exits Tuesday 09:00. Because the market closes for 1 hour during the daily settlement rollover (17:00–18:00 NY), the elapsed wall-clock time is $25.0$ hours.
  With `weekend_threshold_hours = 24.0`, the labeler flagged **100% of weekday trades as weekend crossings (`PURGE_WEEKEND_CROSSING`)**, wiping out all valid labels for $H \ge 288$.
- **Remediation**:
  Updated `CausalDirectionalLabeler.__init__` to dynamically scale the weekend gap threshold whenever `weekend_threshold_hours is None`:
  $$\text{threshold\_hours} = \max\left(24.0, \frac{H \times 5}{60} + 20.0\right)$$
  For $H=288$, this establishes a threshold of $44.0$ hours. This safely exceeds the 25-hour daily rollover span while strictly catching the 49-hour weekend market closure (Friday 17:00 NY to Sunday 18:00 NY).

### 9.2 Regression Test Implementation
A dedicated regression test was added to the test suite to permanently prevent regression of this defect:
- **Test File**: `tests/test_phase3_labeling.py`
- **Test Function**: `test_long_horizon_weekend_threshold_regression()`
- **Verification Assertions**:
  1. For $H=288$, `weekend_threshold_hours` auto-scales to $>25.0$ hours ($44.0$ hours).
  2. Across 600 continuous weekday bars, zero rows are purged with `PURGE_WEEKEND_CROSSING`.
  3. Exactly $1+H$ ($289$) boundary overflow rows and $12$ daily settlement rollover rows are purged.
  4. Exactly $299$ valid labels are generated.

### 9.3 Test Suite Execution Results
The full project test suite was executed to verify system-wide stability:
```bash
PYTHONPATH=src .venv/bin/pytest tests/ -q
........................................................................ [ 46%]
........................................................................ [ 92%]
............                                                             [100%]
156 passed in 2.70s
```
**Test Status**: **156/156 PASSED (100% Pass Rate)** across 23 test modules.

---

## 10. Audit Findings & Governance Directives

### 10.1 Summary of Audit Findings

| Item | Dimension | Status / Classification | Severity |
| :---: | :--- | :--- | :---: |
| **F-01** | Metric Parity | Bitwise and sub-penny reproduction confirmed across all Phase 13/14 artifacts | **INFORMATIONAL** |
| **F-02** | Causal Integrity | Verified. Pivots, MTF joins, and fills strictly causally isolated | **RESOLVED** |
| **F-03** | Data Protection | 2025 Validation and 2026 Test partitions have zero access footprint | **COMPLIANT** |
| **F-04** | Selection Bias | Lineage traced to Phase 12 error diagnosis; search space unbounded | **HIGH (Methodological)** |
| **F-05** | Statistical Edge | Net expectancy $-\$0.139$; bootstrap CI includes 0; $p=0.824$; unproven | **HIGH (Economic)** |
| **F-06** | Subgroup Analysis | Winter vs Summer and Long vs Short are post-hoc exploratory findings | **CAUTIONARY** |
| **F-07** | Cost Realism | Synthetic costs only; bid-only data cannot confirm real-market fills | **LIMITATION** |
| **F-08** | Tooling Defect | Dynamic weekend threshold implemented and verified with regression tests | **RESOLVED** |

### 10.2 Final Governance Directives
1. **Candidate 5 Disqualification Upheld**:
   Candidate 5 is definitively rejected from promotion. It possesses no statistically defensible net edge over the No-Trade Baseline.
2. **Preserve Partition Sealing**:
   The protected 2025 Validation partition must remain strictly sealed. It must **NOT** be unsealed to "test" Candidate 5, seasonal filters, or threshold variations. Unsealing validation on a failed, selection-biased candidate would fatally compromise the research integrity of future phases.
3. **Frozen 2026 Test Partition**:
   The 2026 Test partition remains completely frozen and untouchable.
4. **Transition to Phase 16**:
   Any prospective future phase must address the root cause of negative expectancy: developing truly orthogonal, causal market-regime signals with positive gross expectancy before entering session or execution filtering.

---
*Report produced and verified under Phase 15 Research Integrity & Statistical Validity Protocol.*
