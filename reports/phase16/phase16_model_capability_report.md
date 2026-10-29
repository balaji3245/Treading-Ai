# PHASE 16: AI MODEL CAPABILITY ASSESSMENT & BENCHMARK AUDIT

**Date:** 2026-10-29  
**Status:** COMPLETE — EVALUATION-ONLY AUDIT  
**Scope:** Historical 2021–2024 Research / Training Data Only  
**Protected Partitions:** 2025 Validation & 2026 Test Partitions Confirmed Untouched (Zero-Access Audit Verified)  
**Deliverable Artifacts:**
- Evaluation Script: [`scripts/run_phase16_model_capability_assessment.py`](file:///home/bhoot/project/Treading-Ai/scripts/run_phase16_model_capability_assessment.py)
- Predictive Metrics: [`reports/phase16/phase16_predictive_metrics.json`](file:///home/bhoot/project/Treading-Ai/reports/phase16/phase16_predictive_metrics.json)
- Economic Metrics: [`reports/phase16/phase16_economic_metrics.json`](file:///home/bhoot/project/Treading-Ai/reports/phase16/phase16_economic_metrics.json)
- Out-of-Fold Predictions: [`reports/phase16/phase16_oof_predictions.parquet`](file:///home/bhoot/project/Treading-Ai/reports/phase16/phase16_oof_predictions.parquet)
- Unit & Invariant Test Suite: [`tests/test_phase16_model_capability.py`](file:///home/bhoot/project/Treading-Ai/tests/test_phase16_model_capability.py)

---

## 1. Executive Summary & Model Verdicts

This Phase 16 assessment conducts an exhaustive, statistically rigorous evaluation of all existing Treading-Ai models and benchmark baselines on the historical 2021–2024 research partition. This phase is strictly evaluation-only: no hyperparameters were tuned, no new strategies were introduced, and no execution assumptions were relaxed.

### Primary Audit Finding
**No existing Treading-Ai model demonstrates credible predictive capability beyond simple naive baselines, and every tested model produces negative net expectancy under realistic transaction costs.**

The **No-Trade economic baseline ($0.00 net P&L, 0 trades, 0 drawdown)** remains strictly superior to every candidate strategy evaluated.

### Model Governance Verdict Summary

| Model / System | Horizon / Features | Out-of-Fold Accuracy | Balanced Accuracy | ROC-AUC (OvR) | Net P&L (Base $0.20) | Net Expectancy | Net PF | 95% Confidence Interval (Net P&L) | Verdict |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **No-Trade Baseline** | N/A | N/A | N/A | N/A | **$0.00** | **$0.0000** | **N/A** | [$0.00, $0.00] | **BENCHMARK / SUPERIOR** |
| **Majority-Class Baseline ($H=24$)** | $H=24$ | 43.95% | 33.33% | 0.5000 | -$4,609.75 | -$0.5663 | 0.731 | [-$5,482.11, -$3,745.22] | **BASELINE (REJECT)** |
| **Heuristic RSI+Mom ($H=24$)** | $H=24$ | 27.59% | 33.01% | 0.4998 | -$4,485.18 | -$0.6164 | 0.722 | [-$5,312.44, -$3,658.01] | **REJECT** |
| **Incumbent Model** | $H=24$ (190 feat) | 42.59% | 35.05% | 0.5539 | -$1,370.41 | -$0.5031 | 0.814 | [-$2,073.42, -$599.92] | **REJECT** |
| **Market Structure Model** | $H=24$ (232 feat) | 42.57% | 35.06% | 0.5544 | -$1,443.58 | -$0.5236 | 0.810 | [-$2,185.34, -$672.10] | **REJECT** |
| **Adaptive Challenger** | $H=24$ (Error-Gated) | 42.57% | 35.06% | 0.5544 | -$895.74 | -$0.5072 | 0.825 | [-$1,421.80, -$345.12] | **REJECT** |
| **Majority-Class Baseline ($H=96$)** | $H=96$ | 48.71% | 33.33% | 0.5000 | -$809.02 | -$0.3858 | 0.905 | [-$1,452.10, -$165.40] | **BASELINE (REJECT)** |
| **Heuristic RSI+Mom ($H=96$)** | $H=96$ | 24.86% | 32.73% | 0.4957 | -$518.69 | -$0.2549 | 0.938 | [-$1,120.45, +$92.11] | **REJECT** |
| **Phase 13 Candidate 5** | $H=96$ (232 feat) | 46.41% | 33.30% | 0.5164 | -$73.72 | -$0.1388 | 0.974 | [-$678.62, +$578.03] | **REJECT** |

---

## 2. Mandatory Data Partition Protection Audit

In strict compliance with governance rules, **zero evaluation, query, or loading** of the protected 2025 validation dataset (`XAUUSD_M5_features_val.parquet`) or the frozen 2026 test dataset (`XAUUSD_M5_features_test.parquet`) was performed.

### Cryptographic Checksum Verification
Both files were hashed prior to execution and immediately verified following the run. Checksums remain identical to baseline records:

```bash
# SHA-256 Checksums
Val Partition:  7e9222e9dc0893601e24505912eeab78330670c4e70ebcc2fa462ff8d44a4f94  data/features/XAUUSD_M5_features_val.parquet
Test Partition: f95fd09a5d07666e3f1d9a72e840e2e97f3c058d11b6bb0c712b21dea86a5dec  data/features/XAUUSD_M5_features_test.parquet
```

Automated verification tests in [`tests/test_phase16_model_capability.py`](file:///home/bhoot/project/Treading-Ai/tests/test_phase16_model_capability.py) inspect the AST and runtime behavior of [`scripts/run_phase16_model_capability_assessment.py`](file:///home/bhoot/project/Treading-Ai/scripts/run_phase16_model_capability_assessment.py) to guarantee that neither string literal nor file descriptor to `val.parquet` or `test.parquet` exists in the evaluation pipeline.

### Chronological Walk-Forward Folds
Evaluation was conducted strictly across 3 expanding walk-forward folds within the historical 2021–2024 training dataset (`XAUUSD_M5_features_train.parquet`, 260,821 M5 bars):

1. **Fold 1:**
   - Training Partition: 2021-03-11 00:00 to 2021-12-31 21:55 (57,249 bars)
   - Evaluation Partition: 2022-01-02 23:00 to 2022-12-30 21:55 (70,864 bars)
2. **Fold 2:**
   - Training Partition: 2021-03-11 00:00 to 2022-12-30 21:55 (128,113 bars)
   - Evaluation Partition: 2023-01-02 23:00 to 2023-12-29 21:55 (61,611 bars)
3. **Fold 3:**
   - Training Partition: 2021-03-11 00:00 to 2023-12-29 21:55 (189,724 bars)
   - Evaluation Partition: 2024-01-01 23:00 to 2024-12-31 21:50 (71,072 bars)
- **Total Out-of-Fold Observations:** 203,547 bars (spanning 2022 through 2024).

---

## 3. Predictive Capability Assessment

### 3.1 Class Geometry & Imbalance
Directional labels are ternary:
- Class `-1`: Short Win (price dropped by at least friction hurdle without hitting stop)
- Class `0`: Neutral / Dead Zone (price movement stayed within transaction cost bounds)
- Class `+1`: Long Win (price rose by at least friction hurdle without hitting stop)

Across the out-of-fold evaluation period (2022–2024):
- **$H=24$ (2 Hours):**
  - Total valid observations: 199,754 bars (3,793 weekend/boundary purged)
  - Class `-1`: 83,639 (41.87%)
  - Class `0`: 28,316 (14.18%)
  - Class `+1`: 87,799 (43.95%)
  - **Majority-Class Accuracy Baseline:** **43.95%**
  - **Balanced Accuracy Chance Level:** **33.33%**
- **$H=96$ (8 Hours):**
  - Total valid observations: 188,389 bars (15,158 weekend/boundary purged)
  - Class `-1`: 85,739 (45.51%)
  - Class `0`: 10,879 (5.77%)
  - Class `+1`: 91,771 (48.71%)
  - **Majority-Class Accuracy Baseline:** **48.71%**
  - **Balanced Accuracy Chance Level:** **33.33%**

### 3.2 Predictive Metric Comparison

| Model | Acc | Bal Acc | Macro F1 | ROC-AUC (OvR) | PR-AUC (OvR) | Brier Score | Log Loss | ECE |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Majority Baseline ($H=24$)** | **0.4395** | 0.3333 | 0.2036 | 0.5000 | 0.3333 | **0.6114** | **1.0028** | 0.0006 |
| **Heuristic RSI+Mom ($H=24$)** | 0.2759 | 0.3301 | 0.2761 | 0.4998 | 0.3339 | 0.8946 | 1.4325 | 0.4178 |
| **Incumbent LR ($H=24$)** | 0.4259 | 0.3505 | 0.3412 | 0.5539 | 0.3665 | 0.6415 | 1.0397 | 0.1034 |
| **Market Structure LR ($H=24$)** | 0.4257 | 0.3506 | 0.3389 | 0.5544 | 0.3659 | 0.6395 | 1.0371 | 0.1015 |
| **Adaptive Challenger ($H=24$)** | 0.4257 | 0.3506 | 0.3389 | 0.5544 | 0.3659 | 0.6395 | 1.0371 | 0.1015 |
| **Majority Baseline ($H=96$)** | **0.4871** | 0.3333 | 0.2184 | 0.5000 | 0.3333 | **0.5532** | **0.8757** | 0.0004 |
| **Heuristic RSI+Mom ($H=96$)** | 0.2486 | 0.3273 | 0.2407 | 0.4957 | 0.3320 | 0.9069 | 1.4468 | 0.4450 |
| **Candidate 5 LR ($H=96$)** | 0.4641 | 0.3330 | 0.3190 | 0.5164 | 0.3367 | 0.6348 | 0.9943 | 0.1590 |

### 3.3 Critical Predictive Findings
1. **Raw Accuracy Deficit:**
   - On $H=24$, the Incumbent (42.59%) and Market Structure (42.57%) models achieve *lower* accuracy than predicting the unconditional majority class (43.95%).
   - On $H=96$, Candidate 5 (46.41%) underperforms naive majority-class guessing (48.71%) by 2.30 percentage points overall, and by 8.63 percentage points in Fold 3 (44.32% vs 52.95%).
2. **Probability & Calibration Degradation:**
   - **Log Loss:** The naive majority-class baseline achieves Log Loss of **1.0028** ($H=24$) and **0.8757** ($H=96$). All ML models show *higher* (worse) cross-entropy loss: Incumbent is 1.0397, Market Structure is 1.0371, and Candidate 5 is 0.9943.
   - **Brier Score:** The naive baseline Brier score is **0.6114** ($H=24$) and **0.5532** ($H=96$). The ML models produce strictly worse quadratic probability errors: Incumbent is 0.6415, Candidate 5 is 0.6348.
   - In statistical terms, fitting 190 to 232 continuous features via logistic regression injects estimation noise and miscalibrated probability dispersion relative to the empirical sample mean.
3. **The Fallacy of Marginal ROC-AUC > 0.50:**
   - The Incumbent achieves a one-vs-rest macro ROC-AUC of 0.5539. In financial literature, researchers occasionally mistake ROC-AUC ~ 0.55 for an "exploitable directional edge."
   - Here, because transaction costs impose a fixed friction penalty on every trade, a nominal discrimination ability of 0.55 across raw price moves is entirely insufficient to offset bid-ask spread and slippage. Balanced accuracy remains stuck at 35.05% (vs 33.33% chance level).
4. **Candidate 5 Discrimination Collapse:**
   - For $H=96$, Candidate 5 achieves a balanced accuracy of **33.30%** (identical to random guessing) and an ROC-AUC of **0.5164** (indistinguishable from noise).

### 3.4 Moving Block Bootstrap Confidence Intervals (Predictive)
To account for serial correlation in M5 financial time series, we computed 500-replicate Moving Block Bootstraps with a block size of $L = 288$ bars (exactly 1 full trading day):

- **Incumbent Model ($H=24$):**
  - Accuracy: `0.4259` [95% CI: `0.4187`, `0.4339`]
  - Balanced Accuracy: `0.3505` [95% CI: `0.3450`, `0.3571`]
  - Macro F1: `0.3412` [95% CI: `0.3347`, `0.3488`]
  - Log Loss: `1.0397` [95% CI: `1.0315`, `1.0490`]
  - Brier Score: `0.6415` [95% CI: `0.6362`, `0.6473`]
- **Candidate 5 Model ($H=96$):**
  - Accuracy: `0.4641` [95% CI: `0.4554`, `0.4727`]
  - Balanced Accuracy: `0.3330` [95% CI: `0.3283`, `0.3380`]
  - Macro F1: `0.3190` [95% CI: `0.3117`, `0.3259`]
  - Log Loss: `0.9943` [95% CI: `0.9856`, `1.0041`]
  - Brier Score: `0.6348` [95% CI: `0.6293`, `0.6406`]

---

## 4. Calibration & Selective Threshold Analysis

A common hypothesis in quantitative trading is that while an ML model may have poor average accuracy, restricting trades to high-confidence predictions ($\hat{P}(\text{direction}) > \tau$) isolates a profitable, high-precision edge.

We tested selective thresholds from $\tau = 0.50$ to $\tau = 0.70$ on out-of-fold data:

### Selective Threshold Results

#### Incumbent Model ($H=24$)
| Threshold ($\tau$) | Signal Count | Coverage % | Long Precision | Short Precision | Combined Precision |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **0.50** | 107,358 | 53.75% | 43.88% | 44.12% | 44.03% |
| **0.55** | 69,211 | 34.65% | 43.47% | 44.85% | 44.38% |
| **0.60** | 42,306 | 21.18% | 44.40% | 45.27% | 44.96% |
| **0.65** | 23,484 | 11.76% | 44.16% | 46.47% | 45.54% |
| **0.70** | 12,868 | 6.44% | 46.67% | 47.07% | **46.89%** |

#### Candidate 5 Model ($H=96$)
| Threshold ($\tau$) | Signal Count | Coverage % | Long Precision | Short Precision | Combined Precision |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **0.50** | 162,030 | 86.01% | 48.43% | 45.64% | 46.66% |
| **0.55** | 128,685 | 68.31% | 48.66% | 45.40% | 46.53% |
| **0.60** | 98,507 | 52.29% | 48.88% | 44.80% | 46.14% |
| **0.65** | 71,292 | 37.85% | 48.54% | 44.70% | 45.93% |
| **0.70** | 47,336 | 25.13% | 48.80% | 45.16% | **46.34%** |

### Calibration Audit Conclusion
- **Monotonic Precision Failure:** For Candidate 5, raising the confidence threshold from 0.50 to 0.70 causes combined precision to *decline* from 46.66% to 46.34%.
- **Sub-Baseline Accuracy:** For Candidate 5 at $\tau = 0.70$, Long precision (48.80%) is barely above the unconditional prior (48.71%), while Short precision (45.16%) is strictly worse than flipping a coin.
- **Inadequate Hurdle Clearance:** For the Incumbent at $\tau = 0.70$, combined precision reaches 46.89%, which falls far short of the ~53.5% precision required to break even against $0.20/oz round-turn spread friction.
- The models exhibit high Expected Calibration Error (ECE: 0.1034 for Incumbent, 0.1590 for Candidate 5), confirming severe probability distortion in the tails.

---

## 5. Economic Evaluation & Cost Sensitivity

Economic performance was simulated using the causal execution simulator with realistic transaction friction:
- **Base Scenario:** $0.20/oz half-turn spread ($0.40 round-turn) + $0.00 commission.
- **Stress Scenario:** $0.30/oz half-turn spread ($0.60 round-turn) + $0.00 commission.
- **Frictionless Scenario:** $0.00/oz spread (theoretical gross pricing).

### 5.1 Out-of-Fold Economic Performance Table (Base Scenario)

| Model | Total Trades | Gross P&L | Total Costs | Net P&L | Net Expectancy | Gross Expectancy | Net PF | Max Drawdown | Win Rate (Net) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **No-Trade Baseline** | **0** | **$0.00** | **$0.00** | **$0.00** | **$0.0000** | **$0.0000** | **N/A** | **$0.00** | **N/A** |
| **Majority Baseline ($H=24$)** | 8,140 | +$191.25 | $4,801.00 | -$4,609.75 | -$0.5663 | +$0.0235 | 0.731 | $4,624.43 | 44.02% |
| **Heuristic RSI+Mom ($H=24$)** | 7,276 | -$153.14 | $4,332.04 | -$4,485.18 | -$0.6164 | -$0.0210 | 0.722 | $4,510.52 | 43.14% |
| **Incumbent LR ($H=24$)** | 2,724 | +$274.53 | $1,644.94 | -$1,370.41 | -$0.5031 | +$0.1008 | 0.814 | $1,460.72 | 44.57% |
| **Market Structure LR ($H=24$)** | 2,757 | +$217.98 | $1,661.56 | -$1,443.58 | -$0.5236 | +$0.0791 | 0.810 | $1,507.02 | 44.36% |
| **Adaptive Challenger ($H=24$)** | 1,766 | +$175.39 | $1,071.13 | -$895.74 | -$0.5072 | +$0.0993 | 0.825 | $927.28 | 45.41% |
| **Majority Baseline ($H=96$)** | 2,097 | +$433.66 | $1,242.68 | -$809.02 | -$0.3858 | +$0.2068 | 0.905 | $1,242.90 | 47.97% |
| **Heuristic RSI+Mom ($H=96$)** | 2,035 | +$691.72 | $1,210.42 | -$518.69 | -$0.2549 | +$0.3399 | 0.938 | $684.81 | 47.76% |
| **Phase 13 Candidate 5** | 531 | +$265.08 | $338.80 | -$73.72 | -$0.1388 | +$0.4992 | 0.974 | $440.31 | 48.21% |

### 5.2 Chronological Per-Fold Breakdown

#### Fold 1 (2022 Out-of-Fold)
- Incumbent: 1,027 trades, Gross +$112.45, Costs $620.40, **Net -$507.95**, Net PF 0.798
- Adaptive Challenger: 651 trades, Gross +$88.42, Costs $395.20, **Net -$306.78**, Net PF 0.812
- Candidate 5: 208 trades, Gross +$72.23, Costs $125.77, **Net -$53.54**, Net PF 0.948

#### Fold 2 (2023 Out-of-Fold)
- Incumbent: 852 trades, Gross +$45.18, Costs $514.80, **Net -$469.62**, Net PF 0.785
- Adaptive Challenger: 563 trades, Gross +$12.35, Costs $341.60, **Net -$329.25**, Net PF 0.791
- Candidate 5: 142 trades, Gross +$5.12, Costs $82.88, **Net -$77.76**, Net PF 0.887

#### Fold 3 (2024 Out-of-Fold)
- Incumbent: 845 trades, Gross +$116.90, Costs $509.74, **Net -$392.84**, Net PF 0.858
- Adaptive Challenger: 552 trades, Gross +$74.62, Costs $334.33, **Net -$259.71**, Net PF 0.871
- Candidate 5: 181 trades, Gross +$187.73, Costs $130.15, **Net +$57.57**, Net PF 1.053

### 5.3 Cost Stress Sensitivity & Break-Even Friction

| Model | Frictionless Net P&L | Base ($0.20) Net P&L | Stress ($0.30) Net P&L | Break-Even Cost Multiplier | Break-Even Half Spread |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Incumbent LR** | +$274.53 | -$1,370.41 | -$1,995.87 | 0.1669 | $0.0334 / oz |
| **Market Structure LR** | +$217.98 | -$1,443.58 | -$2,077.14 | 0.1312 | $0.0262 / oz |
| **Adaptive Challenger** | +$175.39 | -$895.74 | -$1,298.30 | 0.1637 | $0.0327 / oz |
| **Candidate 5** | +$265.08 | -$73.72 | -$207.33 | 0.7824 | $0.1565 / oz |

### 5.4 Statistical Significance & Uncertainty (Trade Bootstraps)
We conducted 1,000 trade-level bootstrap resamples and calculated one-sample $t$-tests and Wilcoxon signed-rank tests against zero:

- **Incumbent LR ($H=24$):**
  - Net Expectancy: `-$0.5031` [95% CI: `-$0.7612`, `-$0.2202`]
  - Net P&L: `-$1,370.41` [95% CI: `-$2,073.42`, `-$599.92`]
  - Profit Factor: `0.814` [95% CI: `0.730`, `0.913`]
  - $p$-value ($t$-test): $5.82 \times 10^{-6}$ (significantly negative)
  - $p$-value (Wilcoxon): $1.41 \times 10^{-5}$ (significantly negative)
- **Candidate 5 ($H=96$):**
  - Net Expectancy: `-$0.1388` [95% CI: `-$1.2780`, `+$1.0886`]
  - Net P&L: `-$73.72` [95% CI: `-$678.62`, `+$578.03`]
  - Profit Factor: `0.974` [95% CI: `0.776`, `1.235`]
  - $p$-value ($t$-test): `0.8236` (statistically indistinguishable from zero)
  - $p$-value (Wilcoxon): `0.4407` (statistically indistinguishable from zero)

### 5.5 Directional & Regime Asymmetry in Candidate 5
A breakdown of Candidate 5's 531 trades reveals severe structural asymmetry:
- **Long Trades:** 257 trades, Net P&L **+$67.24**, Win Rate 49.42%
- **Short Trades:** 274 trades, Net P&L **-$140.96**, Win Rate 47.08%

During 2024 (Fold 3), spot gold surged from ~$2,060/oz to over $2,600/oz (+26% macro rally). Candidate 5's Fold 3 profit (+$57.57) was driven entirely by passive long exposure during this secular bull market. When short signals were executed in the same regime, they suffered severe systematic losses. 

Candidate 5 demonstrates zero short-side predictive capability, failed in Folds 1 and 2, has a bootstrap 95% confidence interval centered near zero [-$678.62, +$578.03], and remains overall unprofitable (-$73.72).

---

## 6. Statistical Integrity, Multiple Testing & Selection Bias Audit

### 6.1 Target Leakage & Look-Ahead Bias Audit
- **Feature Computation:** All 232 feature columns (including market structure swing highs/lows, liquidity regimes, momentum, and volatility) use backward-looking rolling windows only (`shift(1)` where applicable).
- **Labeling Alignment:** Labels are aligned to execution bar open timestamps, properly purging weekend boundary gaps ($H=24$ and $H=96$) as verified in the Phase 15B audit.
- **Out-of-Fold Isolation:** Each fold model was fitted strictly on prior chronological partitions. No future bars contaminated training weights.

### 6.2 Selection Bias & Multiple Testing Risk Inherited from Prior Phases
A critical integrity requirement is auditing how Candidate 5 was created:
- In Phase 13, researchers evaluated multiple holding horizons ($H \in \{12, 24, 48, 72, 96, 120, 288\}$) and multiple session filters (Asian, London open, London/NY overlap, New York close).
- Out of dozens of combinations tested on the **same 2021–2024 training data**, Candidate 5 ($H=96$, 12:00–16:30 UTC) was selected *retrospectively* because it happened to lose the least money (-$73.72 vs -$1,370.41).
- This is a textbook example of **selection bias / data mining penalty**: selecting the best-performing parameter combination on a historical dataset without an independent validation partition guarantees that its apparent outperformance over other candidates is largely overfitted variance.
- When evaluated with an unadjusted two-tailed test, $p = 0.824$. When adjusting for multiple comparisons via family-wise error rate (Bonferroni or Holm-Bonferroni across tested candidates), the adjusted $p$-value approaches $1.0$.

---

## 7. Model Governance Decisions & Verdicts

Based on the empirical evidence, the formal verdicts under Phase 16 governance rules are:

### 1. Incumbent Model ($H=24$, 190 Features)
- **Verdict: REJECT**
- **Justification:** Gross profits (+ $274.53) are consumed nearly 6x by transaction friction ($1,644.94), resulting in -$1,370.41 net loss. Net expectancy (-$0.503/trade) and Net PF (0.814) are statistically significantly negative ($p < 10^{-5}$). Accuracy (42.59%) and calibration (Log Loss 1.0397, Brier 0.6415) are strictly inferior to the naive majority-class baseline.

### 2. Market Structure Model ($H=24$, 232 Features)
- **Verdict: REJECT**
- **Justification:** Adding 42 market structure features slightly degraded economic performance (-$1,443.58 net loss) and failed to improve predictive calibration (Log Loss 1.0371, Balanced Accuracy 35.06%). It provides zero statistically measurable benefit over the incumbent.

### 3. Adaptive Challenger ($H=24$, Error-Gated Policy)
- **Verdict: REJECT**
- **Justification:** Although error gating successfully eliminated 991 unprofitable trades (reducing trade count by 36%), net expectancy per trade remained virtually unchanged (-$0.5072/trade vs -$0.5031/trade). Net P&L remained deeply negative (-$895.74 across all 3 folds). The error classifier merely filtered volume without establishing a positive edge.

### 4. Phase 13 Candidate 5 ($H=96$, London/NY Overlap Policy)
- **Verdict: REJECT**
- **Justification:** 
  1. Negative net P&L (-$73.72) and negative net expectancy (-$0.1388/trade) after transaction costs.
  2. The 95% bootstrap confidence interval [-$678.62, +$578.03] heavily covers zero ($p = 0.824$).
  3. Directional asymmetry confirms that its Fold 3 gain was entirely passive long drift during the 2024 gold bull market, while short trades lost -$140.96.
  4. Predictive discrimination on $H=96$ is non-existent (Balanced Accuracy 33.30% vs 33.33% chance; ROC-AUC 0.5164).
  5. It suffers severe retrospective selection bias from Phase 13 exploration.

### 5. Simple Heuristic & Non-ML Baselines (RSI + Momentum)
- **Verdict: REJECT**
- **Justification:** Massive losses (-$4,485.18 on $H=24$; -$518.69 on $H=96$) and severe miscalibration.

### 6. No-Trade Baseline
- **Verdict: BENCHMARK / SUPERIOR ECONOMIC BASELINE**
- **Justification:** With $0.00 net P&L, 0 trades, and 0 drawdown, doing nothing strictly dominates every candidate model and baseline in the Treading-Ai repository.

---

## 8. Summary of Proven Facts vs Unproven Claims

### What the Evidence Proves
1. **Spread friction dominates signal magnitude:** At $H=24$, average price movements (~$2.50/oz) are too small relative to round-turn friction ($0.40/oz base, $0.60/oz stress) to support active trading without >54% directional precision.
2. **Current models lack directional edge:** Neither the 190 base technical features nor the 42 causal market-structure features produce probability estimates superior to the empirical class frequencies.
3. **Selective confidence filtering fails:** Probability thresholds up to 0.70 fail to isolate a subpopulation of trades with positive expectancy.
4. **No model has established an actionable edge:** Under strict out-of-fold walk-forward validation on 2021–2024 data, no model produces positive net expectancy.

### What Remains Unproven
1. Whether any causal machine learning model can reliably forecast gold directional returns net of transaction costs at M5/M15/H1 timeframes.
2. Whether higher-timeframe features (H4, D1 macro fundamentals) or alternative execution structures (limit-order book market making, multi-day holding periods) can overcome transaction friction.
3. How any of these models would behave on the uninspected 2025 validation or frozen 2026 test partitions.

---

## 9. Final Governance Directive

1. **Lock Historical Models:** All evaluated models (Incumbent, Market Structure, Adaptive Challenger, and Candidate 5) are formally **REJECTED** and retired from production consideration.
2. **Preserve Data Boundary:** The 2025 validation partition (`XAUUSD_M5_features_val.parquet`) and 2026 test partition (`XAUUSD_M5_features_test.parquet`) MUST REMAIN UNTOUCHED until a research hypothesis demonstrates statistically significant out-of-fold edge on training data that survives transaction cost stress and multiple-testing adjustments.
3. **No-Trade Benchmark:** The economic benchmark for all future research remains **$0.00**. Any proposed strategy that fails to beat $0.00 net of costs must be rejected immediately.
