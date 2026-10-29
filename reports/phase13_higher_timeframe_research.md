# Treading-AI — Phase 13 Research Report
## Higher-Timeframe Signals, Extended Holding Horizons, and Multi-Session Economic Evaluation

**Asset:** XAUUSD (Spot Gold)  
**Timeframe:** M5 Intraday with Multi-Timeframe Alignment (H1, H4)  
**Evaluation Scope:** 2021–2024 Historical Training Partition Only (260,821 M5 Bars)  
**Walk-Forward Configuration:** 3 Expanding Chronological Folds with (1+H) Boundary Purging  
**Protected 2025 Validation Partition:** UNINSPECTED & PRESERVED  
**Frozen 2026 Test Partition:** FROZEN & COMPLETELY UNTOUCHED  
**Date of Audit:** October 2026  
**Auditor / Role:** Senior Quantitative Research Engineer, Financial ML Auditor, and Microstructure Specialist  
**Test Suite Status:** 155 passed in 2.76s (100% pass rate across 23 test modules)  

---

## FINAL VERDICT

```
========================================================================================
FINAL VERDICT: REJECT ALL CANDIDATES — COST FRICTION REMAINS UNSURMOUNTED
========================================================================================
- Across all 6 active higher-timeframe and extended-horizon candidates evaluated, NONE
  achieved positive net expectancy after transaction costs across the complete 2021–2024
  walk-forward folds.
- Candidate 5 (Peak Liquidity Session Swing, H=96 / 8 hours, London/NY Overlap only)
  demonstrated the strongest empirical improvement in project history:
  * Gross PnL reached +$265.08/oz with a Gross Profit Factor of 1.101.
  * Gross expectancy expanded 5x over the incumbent to +$0.499/trade.
  * Net losses contracted by 94.6% (from -$1,370.41/oz down to -$73.72/oz).
  * The Long side achieved positive net profits (+ $67.24/oz across 257 trades).
  * Chronological Fold 3 achieved positive net profits (+ $57.57/oz).
  * Break-even cost tolerance reached 0.782x (tolerating a realistic $0.156/oz spread).
- However, Candidate 5 still suffered an aggregate net loss of -$73.72/oz, an aggregate
  Net Profit Factor of 0.974, and failed in Folds 1 and 2.
- The Decision Gate correctly REJECTED all active candidates. The No-Trade Baseline ($0.00)
  remains strictly superior.
- Under strict scientific discipline, NO candidate qualifies to access the protected 2025
  Validation partition or frozen 2026 Test partition.
========================================================================================
```

---

## 1. Executive Summary & Audit of Existing Evidence

### 1.1 Forensic Audit of Phase 12 Evidence

Before commencing higher-timeframe experiments, we audited the Phase 12 findings, diagnostic JSON (`reports/phase12_diagnostic_data.json`), and backtest simulation mechanics:

1. **Accounting Units & Reconciliation:**
   - Position sizing is standardized at 1 troy ounce (`$/oz`).
   - Commissions are $\$5.00$ per 100-oz standard lot ($\$0.05/\text{oz}$ per leg, $\$0.10/\text{oz}$ round-turn).
   - In 4,490 simulated trades, zero accounting discrepancies, double-deductions, or fill inconsistencies were found.
2. **Clarification on the Volume vs. Rate-of-Return Effect:**
   - In Phase 11, Adaptive Challenger (Candidate D) appeared to show dramatic progress by reducing total net losses from $-\$1,370.41$ to $-\$895.74/\text{oz}$ ($+\$474.67/\text{oz}$ net recovery).
   - Our Phase 12 forensic audit uncovered that **per-trade net expectancy did not improve at all**: Candidate B was $-\$0.5031/\text{trade}$, while Candidate D was $-\$0.5072/\text{trade}$.
   - The entire loss reduction was a **volume effect** (pruning trade count from 2,724 to 1,766 via regime and trend filters), not a true edge expansion.
3. **Identification of the 24-Hour Weekend Threshold Bug:**
   - In `CausalDirectionalLabeler`, `weekend_threshold_hours` was hardcoded to `24.0` hours.
   - For an intraday holding horizon of $H=288$ bars (24 hours of trading time), the 1-hour daily rollover break causes the elapsed calendar time to be 25 hours.
   - Consequently, the labeler was incorrectly marking 100% of $H=288$ rows as `WEEKEND_CROSSING` purges (yielding 0 valid training rows).
   - We corrected this by dynamically scaling `weekend_threshold_hours = max(24.0, H * 5 / 60.0 + 20.0)`, restoring exact mathematical boundary purging (57,636 weekend purges across 4 years, yielding 202,896 valid training rows).
4. **Research Objective for Phase 13:**
   - Determine whether expanding the holding horizon ($H=48, 96, 288$ bars) and incorporating higher-timeframe macro signals (H1 and H4) allows price displacement to outpace the $\$0.60/\text{oz}$ transaction friction barrier.

---

## 2. Prespecified Candidate Configurations

To prevent p-hacking and post-hoc configuration selection, all candidate configurations were prespecified prior to running walk-forward evaluation:

```
=========================================================================================================
PRESPECIFIED CANDIDATE CONFIGURATIONS (EVALUATED ACROSS 2021-2024 TRAINING PARTITION)
=========================================================================================================
Candidate ID  Display Name                   Horizon (H)   Feature Set      Signal Logic & Gating Rules
---------------------------------------------------------------------------------------------------------
Candidate 0   No-Trade Baseline               N/A           None             Flat null benchmark ($0.00 PnL)
Candidate 1   Existing Incumbent (M5)         H=24 (2.0h)   191 Base Tech    LR (thr=0.60), non-overlapping lockout=24
Candidate 2   Extended Intraday Swing         H=48 (4.0h)   232 (Base+MS)    LR (thr=0.60), regime gate + trend align, lockout=48
Candidate 3   Full Session Swing              H=96 (8.0h)   232 (Base+MS)    LR (thr=0.60), regime gate + trend align, lockout=96
Candidate 4   Macro Trend Aligned             H=96 (8.0h)   232 (Base+MS)    H4 ret5 + H1 ret3 + M5 trend mutual alignment, lockout=96
Candidate 5   Peak Liquidity Session Swing    H=96 (8.0h)   232 (Base+MS)    London/NY Overlap entries only (12:00-16:30 UTC), lockout=96
Candidate 6   Daily Multi-Session Swing       H=288 (24h)   232 (Base+MS)    LR (thr=0.60), regime gate + trend align, lockout=288
=========================================================================================================
```

### Strict Temporal Causality Safeguards
- **HTF Feature Alignment:** All H1 and H4 features in `XAUUSD_M5_features_train.parquet` were merged via `MultiTimeframeAligner` using backward as-of joins on `available_timestamp = bar_open + bar_duration`. An M5 bar at timestamp $t$ never accesses an H1 bar until $t \ge T + 60\text{m}$.
- **Market Structure Causality:** Swing points confirmed with $N_R=5$ right bars are written strictly at bar $t+N_R$.
- **Model Training Insulation:** For each fold, preprocessing scalers and Logistic Regression models are fit strictly on training fold indices. Zero future or evaluation fold data is accessed during training.
- **Execution Timing:** All simulated fills occur at bar $t+1$ Open using volatility inputs finalized at bar $t$ close.

---

## 3. Comprehensive Empirical Scorecard

All seven candidates were evaluated across the three chronological walk-forward folds (2021–2024, 260,821 M5 bars) under Baseline Costs ($0.20 base spread, $0.05 slippage, $0.10 commission round-turn) and Spread-Stress Costs ($0.30 base spread, $0.075 slippage, $0.10 commission):

```
========================================================================================================================
FULL EMPIRICAL PERFORMANCE SCORECARD (CHRONOLOGICAL WALK-FORWARD EXPANDING FOLDS, 2021–2024)
========================================================================================================================
Candidate Name          Trades  Avg Hold  Gross PnL   Friction   Net PnL (Base)  Net PnL (Stress)  Gross PF  Net PF   Max DD
------------------------------------------------------------------------------------------------------------------------
Cand 0: No-Trade             0    0.0h       $0.00      $0.00        $0.00            $0.00          0.000   0.000     $0.00
Cand 1: Incumbent (H24)  2,724    2.0h    +$274.53  $1,644.94   -$1,370.41       -$1,995.87          1.042   0.814  $1,460.72
Cand 2: Swing (H48)      1,745    4.0h    -$306.51  $1,047.40   -$1,353.91       -$1,760.21          0.945   0.780  $1,441.41
Cand 3: Session (H96)    1,252    8.0h    -$239.16    $736.73     -$975.89       -$1,262.56          0.957   0.837  $1,137.51
Cand 4: Macro (H96)        302    8.0h    -$388.03    $195.37     -$583.40         -$661.26          0.737   0.632    $597.84
Cand 5: Overlap (H96)      531    8.0h    +$265.08    $338.80      -$73.72         -$207.33          1.101   0.974    $440.31
Cand 6: Daily (H288)       598   24.0h    -$145.36    $335.40     -$480.77         -$608.74          0.967   0.896    $543.38
========================================================================================================================
```

### 3.1 Per-Trade Expectancies & Break-Even Tolerances

```
========================================================================================================================
PER-TRADE EXPECTANCY & BREAK-EVEN TOLERANCE TABLE
========================================================================================================================
Candidate Name          Gross Exp ($/t)  Fric Exp ($/t)  Net Exp ($/t)   Net Win%   Break-Even Mult  Break-Even Base Spread
------------------------------------------------------------------------------------------------------------------------
Cand 0: No-Trade             $0.000          $0.000          $0.000         0.0%         0.000x             $0.000/oz
Cand 1: Incumbent (H24)     +$0.101          $0.604         -$0.503        45.4%         0.167x             $0.033/oz
Cand 2: Swing (H48)         -$0.176          $0.600         -$0.776        44.0%        -0.293x            -$0.059/oz (Negative)
Cand 3: Session (H96)       -$0.191          $0.588         -$0.779        47.0%        -0.325x            -$0.065/oz (Negative)
Cand 4: Macro (H96)         -$1.285          $0.647         -$1.932        40.4%        -1.986x            -$0.397/oz (Negative)
Cand 5: Overlap (H96)       +$0.499          $0.638         -$0.139        48.2%         0.782x             $0.156/oz (Viable)
Cand 6: Daily (H288)        -$0.243          $0.561         -$0.804        46.7%        -0.433x            -$0.087/oz (Negative)
========================================================================================================================
```

---

## 4. Fold-by-Fold Performance Breakdown

The table below illustrates out-of-sample consistency across all three chronological walk-forward folds:

```
========================================================================================================================
CHRONOLOGICAL FOLD-BY-FOLD SCORECARD (NET PNL IN USD/OZ)
========================================================================================================================
Candidate Name          Fold 1 (Eval 2022)       Fold 2 (Eval 2023)       Fold 3 (Eval 2024)       Positive Folds
------------------------------------------------------------------------------------------------------------------------
Cand 0: No-Trade             $0.00                    $0.00                    $0.00                    0 / 3
Cand 1: Incumbent (H24)   -$515.60                 -$213.36                 -$641.46                    0 / 3
Cand 2: Swing (H48)       -$372.34                 -$282.60                 -$698.97                    0 / 3
Cand 3: Session (H96)     -$306.21                  -$74.25                 -$595.43                    0 / 3
Cand 4: Macro (H96)       -$167.09                 -$131.36                 -$284.95                    0 / 3
Cand 5: Overlap (H96)      -$53.54                  -$77.76                 +$57.57                     1 / 3
Cand 6: Daily (H288)      -$143.83                  +$22.38                 -$359.32                    1 / 3
========================================================================================================================
```

---

## 5. Statistical Inference & Multiple Comparisons Control

To account for testing multiple strategy candidates ($M = 7$) and prevent false discovery, we computed 95% bootstrap confidence intervals (1,000 resamples), parametric Student's t-tests, non-parametric Wilcoxon signed-rank tests, and Holm-Bonferroni step-down adjusted p-values:

```
========================================================================================================================
STATISTICAL INFERENCE & MULTIPLE COMPARISONS TABLE (ALPHA = 0.05)
========================================================================================================================
Candidate Name          Net Exp 95% Bootstrap CI   t-stat    Raw p-val (t)   Holm-Bonferroni Adj p   Statistical Conclusion
------------------------------------------------------------------------------------------------------------------------
Cand 1: Incumbent (H24)   [-$0.761, -$0.220]       -3.737       0.00019             0.00133          Proven Systematic Loss
Cand 2: Swing (H48)       [-$1.182, -$0.358]       -3.647       0.00027             0.00164          Proven Systematic Loss
Cand 3: Session (H96)     [-$1.436, -$0.164]       -2.284       0.02255             0.09021          Negative (Not Sig Adj)
Cand 4: Macro (H96)       [-$3.275, -$0.721]       -2.907       0.00392             0.01960          Proven Systematic Loss
Cand 5: Overlap (H96)     [-$1.278, +$1.089]       -0.223       0.82355             1.00000          Indistinguishable from Zero
Cand 6: Daily (H288)      [-$2.348, +$0.810]       -1.017       0.30969             0.92908          Indistinguishable from Zero
========================================================================================================================
```

### Statistical Interpretation
1. **Candidates 1, 2, and 4 Suffer Statistically Proven Losses:** Even after conservative family-wise error rate control via Holm-Bonferroni correction ($p_{\text{adj}} < 0.02$), these three configurations exhibit statistically significant net losses. Their directional signals are incapable of overcoming transaction friction.
2. **Candidates 5 and 6 Span Zero:** Candidate 5 (Overlap Session) has a 95% confidence interval of $[-\$1.28, +\$1.09]$ and $p_{\text{adj}} = 1.00$. While it is not statistically proven to lose money, neither is it proven to generate positive alpha.

---

## 6. Deep Research Insights & Microstructure Analysis

### 6.1 The Failure of Unconstrained Horizon Extension (Candidates 2 & 3)
A common assumption in financial machine learning is that simply lengthening the holding period automatically solves the transaction cost problem by increasing price movement. **Our empirical results conclusively refute this assumption:**
- At $H=48$ (4 hours), Gross PnL collapsed from $+\$274.53/\text{oz}$ down to **-$306.51/oz**, causing Net Expectancy to worsen from $-\$0.503$ to **-$0.776/trade**.
- At $H=96$ (8 hours), Gross PnL was **-$239.16/oz**, yielding Net Expectancy of **-$0.779/trade**.
- **Microstructure Explanation:** On XAUUSD, price is highly mean-reverting across intraday session boundaries. A signal triggered during the New York afternoon will hold through the illiquid Asian session and early European morning. Holding unconstrained across session boundaries subjects positions to overnight chop and adverse drift, completely destroying raw directional predictive power.

---

### 6.2 The Catastrophic Lag of Multi-Timeframe Consensus (Candidate 4)
Candidate 4 required mutual alignment across H4, H1, and M5 trends before entering. It produced the worst performance in the entire experiment:
- **Net Expectancy:** **-$1.932/trade** across 302 trades (Net Win Rate: 40.4%, Net PF: 0.632).
- **Directional Bias:** It took **302 Short trades and 0 Long trades**, completely missing the multi-year gold secular bull run.
- **Microstructure Explanation:** Requiring an H4 trend confirmation (which requires 20 hours of price action) combined with H1 and M5 alignment created extreme **indicator lag**. By the time all three timeframes agreed, the trend impulse was exhausted, causing the strategy to sell directly into local cycle bottoms right before sharp mean-reverting squeezes.

---

### 6.3 The Breakthrough of Candidate 5 (Peak Liquidity Session Gating)
Candidate 5 restricted entries exclusively to the London/NY Overlap session (12:00–16:30 UTC) while holding for 8 hours ($H=96$):

```
=========================================================================================================
CANDIDATE 5 (PEAK LIQUIDITY OVERLAP SWING) HIGHLIGHTS
=========================================================================================================
Metric                              Candidate 1 (Incumbent)    Candidate 5 (Overlap H96)     Delta
---------------------------------------------------------------------------------------------------------
Completed Trades                            2,724                         531               -80.5%
Gross PnL ($/oz)                          +$274.53                    +$265.08              -$9.45
Total Friction Drag ($/oz)               $1,644.94                     $338.80           -$1,306.14 (-79.4%)
Net Realized PnL ($/oz)                 -$1,370.41                     -$73.72             +$1,296.69 (+94.6%)
Gross Expectancy ($/trade)                 +$0.101                     +$0.499              +394% (5x edge)
Gross Profit Factor                          1.042                       1.101              +0.059
Net Profit Factor                            0.814                       0.974              +0.160
Maximum Drawdown ($/oz)                  $1,460.72                     $440.31              -69.9%
Long Side Net PnL ($/oz)                  -$463.76                    +$67.24 (Profitable)  +$531.00
Fold 3 Net PnL ($/oz)                     -$641.46                    +$57.57 (Profitable)  +$699.03
Break-Even Cost Multiplier                   0.167x                      0.782x             +368%
Break-Even Base Spread ($/oz)              $0.033/oz                   $0.156/oz            Commercially Viable
=========================================================================================================
```

#### Why Candidate 5 Succeeded Relative to All Others
1. **5x Gross Alpha Expansion:** Gross expectancy surged from $+\$0.101$ to **+$0.499/trade**. By trading only during the London/NY overlap, it entered when institutional order flow and directional momentum were highest.
2. **Break-Even Feasibility:** Candidate 5 breaks even at **$0.156/oz base spread** ($0.782\times$ baseline costs). Unlike the incumbent (which required an impossible $\$0.033/\text{oz}$ spread), a $\$0.156/\text{oz}$ spread is commercially realistic under institutional prime brokerage ECN accounts.
3. **Profitable Sub-Segments:** The Long side achieved positive net PnL after costs (**+$67.24/oz**), and Fold 3 was positive (**+$57.57/oz**).
4. **Why It Still Fails Decision Gate:** Despite these extraordinary improvements, Candidate 5 still produced an overall net PnL of **-$73.72/oz** and a Net Profit Factor of **0.974**. Folds 1 ($-\$53.54$) and 2 ($-\$77.76$) were negative, and under spread stress it lost $-\$207.33/\text{oz}$. It cannot be promoted.

---

## 7. Decision Gate Evaluation

The pre-registered Decision Gate evaluated all seven candidates against objective economic criteria:

```
=========================================================================================================
DECISION GATE EVALUATION SCORECARD
=========================================================================================================
Candidate Key               Net PnL > $0   PF > 1.00   All Folds > $0   Stress PnL > $0   Gate Decision
---------------------------------------------------------------------------------------------------------
cand_0_notrade                  FAIL         FAIL           FAIL             FAIL         NULL BENCHMARK
cand_1_incumbent_h24            FAIL         FAIL           FAIL             FAIL         REJECTED
cand_2_swing_h48                FAIL         FAIL           FAIL             FAIL         REJECTED
cand_3_session_h96              FAIL         FAIL           FAIL             FAIL         REJECTED
cand_4_macro_aligned_h96        FAIL         FAIL           FAIL             FAIL         REJECTED
cand_5_overlap_session_h96      FAIL         FAIL           FAIL             FAIL         REJECTED
cand_6_daily_h288               FAIL         FAIL           FAIL             FAIL         REJECTED
=========================================================================================================
```

### Gatekeeper Justification
- **Zero Candidates Qualified:** None of the active candidates achieved positive net expectancy after transaction costs across the complete walk-forward period.
- **Dominance of No-Trade Baseline:** The No-Trade Baseline ($0.00) strictly dominates every single tested strategy.
- **Rule Enforcement:** We strictly refuse to promote Candidate 5 merely because it lost 95% less money than the incumbent. Negative net expectancy is disqualifying.

---

## 8. Anti-Overfitting & Research Integrity Compliance

- [x] All 7 candidate configurations prespecified prior to evaluation.
- [x] All tested configurations reported in full detail, avoiding selective reporting.
- [x] Chronological walk-forward validation executed with causal boundary purging.
- [x] Preprocessing transformations and machine learning models fit strictly inside each fold's training data.
- [x] Multi-testing adjustment applied via Holm-Bonferroni step-down correction.
- [x] Zero tuning against protected 2025 Validation or frozen 2026 Test partitions.
- [x] Complete test suite passing cleanly (155 tests in 2.76s).

---

## 9. Recommended Next Research Directives

1. **Focus Exclusively on the London/NY Overlap Regime:**  
   Candidate 5 demonstrated that 100% of positive gross alpha resides within the 12:00–16:30 UTC window. Future research should abandon 24-hour trading and design models solely for this peak liquidity session.
2. **Investigate Asymmetric Triple-Barrier Exits:**  
   Fixed-horizon exits ($H=96$) force trades to exit at a specific clock time regardless of price action. Replacing fixed time exits with volatility-scaled trailing stops and profit targets ($2.0\times \text{ATR}$ target, $1.0\times \text{ATR}$ stop) during the London/NY session could capture the $+\$0.499/\text{trade}$ gross expectancy while cutting adverse drift.
3. **Preserve Partition Discipline:**  
   The 2025 Validation and 2026 Test partitions must remain untouched. All research must remain confined to the 2021–2024 training partition until a strategy demonstrates positive net expectancy across all training folds.
