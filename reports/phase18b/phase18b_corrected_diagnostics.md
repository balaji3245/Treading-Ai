# Phase 18B: Corrected Diagnostics & Forensic Audit Corrections

**Status:** Completed & Methodologically Verified  
**Date:** October 2026  
**Scope:** Forensic Audit Corrections of Phase 17 Findings & Methodological Revision  
**Data Partition Governance:** Strict zero-access enforced for 2025 Validation (`val.parquet`, SHA-256 `7e9222...`) and 2026 Test (`test.parquet`, SHA-256 `f95fd0...`). Only 2021–2024 training data evaluated.

---

## Executive Summary

Phase 18B resolves the methodological, statistical, and accounting findings identified during the Phase 18A forensic audit of Phase 17 diagnostics. Phase 17 provided valuable high-level insights regarding cost friction, but suffered from an off-by-one excursion boundary indexing error, an unverified assertion labeling a single Bartlett-kernel estimate as "the true" effective sample size, an unhandled zero-variance feature that distorted collinearity rankings, a static confusion between "spread" and "half-spread", and unsupported conceptual claims regarding random walks and statistical independence.

This document presents the mathematically corrected and empirically verified diagnostic foundations.

### Key Corrections Summary

| Audit Domain | Phase 17 Flaw / Finding | Phase 18B Methodological Correction | Quantitative Impact |
| :--- | :--- | :--- | :--- |
| **Excursion Indexing** | Sliced `[1 : max_idx+1]`, omitting entry candle $i+1$ and looking into exit candle $i+1+H$ post-exit. | Sliced `[:max_idx]`, strictly constraining price data to active trade candles $[i+1, i+H]$. | Excursions overstated by $\$0.013\text{--}\$0.054/\text{oz}$. Corrected Long MFE at $H=24$: $\$3.526/\text{oz}$, Long MAE: $\$3.544/\text{oz}$. |
| **Effective Sample Size** | Labeled Bartlett kernel with $2H$ truncation as "the true" effective sample size. Heuristic $N/H$ labeled wrong. | Evaluated sensitivity across 4 estimators: Heuristic $N/H$, Bartlett ($2H$), Bartlett (First-Neg), and Parzen ($2H$). | $N_{\text{eff}}$ at $H=24$ spans $10,666$ to $20,487$. No single number can be labeled "true"; discrete sign mapping dampens autocorrelation decay. |
| **Feature Collinearity** | Zero-variance feature `is_daily_roll_window` caused $0/0 = \text{NaN}$, poisoning correlation sort. | Filtered constant features prior to correlation and PCA. Isolated exact duplicates ($|r|=1.000$). | Clean feature count = 231. 41 exact duplicate pairs identified (e.g. `rsi_14` vs `rsi_14_norm`). 52 PCA components explain 90% variance. |
| **Cost Accounting** | Terminology confused $0.20 "half-spread" with $0.40 round-turn, and applied symmetric break-even. | Traced exact spread crossing (paid once per round turn). Computed empirical asymmetric break-even. | Dynamic realized friction is $\sim \$0.6039/\text{oz}$. Empirical asymmetric break-even is $50.56\%$ for Incumbent, $48.88\%$ for Candidate 5. |
| **Research Interpretation** | Claimed $\text{MFE} = \text{MAE}$ proves random walk; non-overlapping bars guarantee independence. | Refuted both: proved $\text{MFE}=\text{MAE}$ is an algebraic tautology; explained persistent serial return dependence. | Eliminates false equivalence and theoretical over-reach. |

---

## 1. Resolution of Phase 18A Audit Findings

### A. Excursion Indexing & Trade Boundary Definitions

#### 1. Explicit Lifecycle Timing Definitions

To guarantee zero future-data leakage and prevent off-by-one errors, every trade lifecycle is explicitly formalized as follows:

*   **Decision Time ($t_d$):** The close of candle $i$ (`timestamp_close[i]`). At this exact instant, all feature data and model inference for candle $i$ are finalized.
*   **Entry Time ($t_e$):** The open of candle $i+1$ (`timestamp_open[i+1]`). The market order executes at the very beginning of the next bar.
*   **Active Trade Interval:** The continuous duration spanning from the open of candle $i+1$ through the close of candle $i+H$. This corresponds strictly to the price activity of candles $i+1, i+2, \dots, i+H$ (exactly $H$ bars).
*   **Exit Time ($t_x$):** The open of candle $i+1+H$ (`timestamp_open[i+1+H]`). The position is liquidated at the open price of the exit bar.
*   **Strict Boundary Exclusion:** Under no circumstances may any price data (High, Low, or Close) from candle $i+1+H$ enter the excursion calculation. Because the trade is closed at the Open of candle $i+1+H$, any price movement occurring later during candle $i+1+H$ happens strictly *after* market exit.

#### 2. Hand-Checkable Synthetic Indexing Test

Consider a synthetic price series with horizon $H = 2$:

$$\text{Candles: } [c_0, c_1, c_2, c_3, c_4]$$
$$\text{Opens: } [100.0, 101.0, 104.0, 108.0, 112.0]$$
$$\text{Highs: } [102.0, 105.0, 110.0, 999.0, 115.0]$$
$$\text{Lows: } [99.0, 100.0, 102.0, 50.0, 100.0]$$

*   **Decision at $c_0$:**
    *   Entry executes at Open of $c_1 = 101.0$.
    *   Exit executes at Open of $c_3 = 108.0$.
    *   Active trade candles: $c_1$ and $c_2$.
    *   Active maximum High: $\max(\text{High}[c_1], \text{High}[c_2]) = \max(105.0, 110.0) = 110.0$.
    *   Active minimum Low: $\min(\text{Low}[c_1], \text{Low}[c_2]) = \min(100.0, 102.0) = 100.0$.
    *   **Correct MFE:** $110.0 - 101.0 = +9.0$.
    *   **Correct MAE:** $101.0 - 100.0 = +1.0$.

*   **Phase 17 Implementation Flaw:**
    Phase 17 computed rolling forward maximums using reverse rolling windows and then shifted by $-1$, slicing with `[1 : max_idx + 1]`.
    *   In Phase 17's code, element 0 took index 1 of the shifted series, spanning candles $c_2$ and $c_3$.
    *   $\max(\text{High}[c_2], \text{High}[c_3]) = \max(110.0, 999.0) = 999.0$.
    *   Phase 17 reported $\text{MFE} = 999.0 - 101.0 = +898.0$, completely leaking the post-exit $999.0$ spike from candle $c_3$ into the trade excursion!

*   **Corrected Implementation:**
    The corrected formula slices strictly with `[:max_idx]`:
    $$\text{fwd\_max} = \text{highs.iloc}[::-1].\text{rolling}(H, \text{min\_periods}=H).\max().\text{iloc}[::-1].\text{shift}(-1).\text{to\_numpy}[:\text{max\_idx}]$$
    This correctly selects candles $c_1$ and $c_2$, yielding $\max = 110.0$ and completely ignoring the post-exit spike.

#### 3. Empirical Recalculation Across All Research Horizons

The table below presents the corrected excursion metrics compared against the values reported in Phase 17:

| Horizon ($H$) | Sample $N$ | Median Move ($|\Delta P|$) | Phase 17 Reported Excursion | Corrected Long MFE | Corrected Long MAE | Indexing Overstatement | MFE/MAE Ratio (Long) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **12 (1h)** | 260,808 | $\$1.57/\text{oz}$ | $\$2.508/\text{oz}$ | $\$2.441/\text{oz}$ | $\$2.467/\text{oz}$ | $+\$0.054/\text{oz}$ | 0.989 |
| **24 (2h)** | 260,796 | $\$2.26/\text{oz}$ | $\$3.575/\text{oz}$ | $\$3.526/\text{oz}$ | $\$3.544/\text{oz}$ | $+\$0.040/\text{oz}$ | 0.995 |
| **48 (4h)** | 260,772 | $\$3.37/\text{oz}$ | $\$5.168/\text{oz}$ | $\$5.148/\text{oz}$ | $\$5.128/\text{oz}$ | $+\$0.030/\text{oz}$ | 1.004 |
| **72 (6h)** | 260,748 | $\$4.35/\text{oz}$ | $\$6.443/\text{oz}$ | $\$6.451/\text{oz}$ | $\$6.384/\text{oz}$ | $+\$0.025/\text{oz}$ | 1.010 |
| **96 (8h)** | 260,724 | $\$5.16/\text{oz}$ | $\$7.546/\text{oz}$ | $\$7.584/\text{oz}$ | $\$7.463/\text{oz}$ | $+\$0.023/\text{oz}$ | 1.016 |
| **120 (10h)** | 260,700 | $\$5.90/\text{oz}$ | $\$8.542/\text{oz}$ | $\$8.611/\text{oz}$ | $\$8.431/\text{oz}$ | $+\$0.021/\text{oz}$ | 1.021 |
| **288 (24h)** | 260,532 | $\$10.06/\text{oz}$ | $\$13.758/\text{oz}$ | $\$14.112/\text{oz}$ | $\$13.377/\text{oz}$ | $+\$0.013/\text{oz}$ | 1.055 |

*Finding:* Phase 17's indexing error caused a consistent upward bias in reported excursions across all horizons, ranging from $+\$0.013/\text{oz}$ at $H=288$ to $+\$0.054/\text{oz}$ at $H=12$. When corrected, Long MFE and Long MAE remain very close to balanced at short horizons, with a slight drift toward Long MFE > Long MAE at multi-hour and daily horizons ($1.016\times$ at $H=96$, $1.055\times$ at $H=288$), reflecting the structural gold bull market over 2021–2024.

---

### B. Effective Sample Size ($N_{\text{eff}}$) Sensitivity Analysis

#### 1. Critique of $N/H$ vs. Bartlett Kernel

In time-series labeling with rolling overlapping horizons of length $H$, consecutive labels share $H-1$ observations of underlying price changes. This mechanical overlap creates pronounced serial correlation in the target series.

*   **Heuristic $N/H$:** Assumes continuous returns whose autocorrelation decays linearly from $\rho_1 \approx (H-1)/H$ to $\rho_H = 0$, yielding a variance inflation factor $\text{VIF} \approx H$ and $N_{\text{eff}} \approx N/H$. This heuristic is conservative and treats all intra-horizon samples as entirely redundant.
*   **Bartlett Kernel Estimator:** Employs triangular weights $w_k = 1 - k/M$ up to truncation lag $M$:
    $$\text{VIF} = 1 + 2 \sum_{k=1}^{M-1} \left(1 - \frac{k}{M}\right) \hat{\rho}_k, \quad N_{\text{eff}} = \frac{N}{\text{VIF}}$$
*   **Key Discovery:** Why does Bartlett yield higher $N_{\text{eff}}$ than $N/H$?
    The directional label target is not continuous returns, but a **ternary sign classification** $y_t \in \{-1, 0, +1\}$ filtered by an ATR threshold $\theta = 0.5 \times \text{ATR}$.
    Converting continuous moves to discrete signs dampens autocorrelation: small fluctuating moves that would share covariance under continuous math are mapped to 0 or fixed signs. Consequently, empirical autocorrelation of directional labels decays faster than the theoretical linear triangle of continuous returns.

#### 2. Estimator Sensitivity Comparison

To eliminate the dogmatic assertion that any single estimator is "the true" sample size, four robust estimators were evaluated across all horizons:
1.  **Heuristic $N/H$:** Lower bound based on complete intra-window redundancy.
2.  **Bartlett ($M = 2H$):** Standard Newey-West triangular kernel truncated at twice the horizon.
3.  **Bartlett (First-Negative Truncation):** Truncated at the first lag where empirical autocorrelation turns non-positive ($k_{\text{neg}} \approx H-1$), eliminating contamination from negative rebound noise.
4.  **Parzen ($M = 2H$):** Smooth cubic spline kernel ensuring strict positive semi-definiteness without sharp triangular cutoffs.

| Horizon ($H$) | Raw $N$ | Lag-1 $\hat{\rho}_1$ | First Neg Lag | Heuristic $N/H$ | Bartlett ($2H$) | Bartlett (First-Neg) | Parzen ($2H$) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **12** | 258,408 | 0.792 | 11 | **21,534** | **32,951** | **40,023** | **33,040** |
| **24** | 255,996 | 0.857 | 23 | **10,666** | **16,833** | **20,487** | **16,879** |
| **48** | 251,172 | 0.902 | 47 | **5,233** | **8,254** | **10,116** | **8,298** |
| **72** | 246,348 | 0.923 | 68 | **3,422** | **5,592** | **6,890** | **5,589** |
| **96** | 241,524 | 0.935 | 91 | **2,516** | **4,227** | **5,185** | **4,220** |
| **120** | 236,700 | 0.941 | 115 | **1,972** | **3,356** | **4,102** | **3,351** |
| **288** | 202,896 | 0.963 | 287 | **704** | **1,231** | **1,485** | **1,231** |

#### 3. Separation of Overlapping Labels vs. Market Return Serial Dependence

A critical conceptual distinction must be enforced:
*   **Overlapping-Label Dependence:** An artifact of rolling window sampling. It inflates variance mechanically but does not imply market predictability.
*   **Market Return Serial Dependence:** True economic dependence in financial time series (volatility clustering, GARCH effects, session volume cycles, macroeconomic momentum).
*   **Methodological Rule:** Even if non-overlapping samples are extracted (e.g. taking 1 bar every $H$ periods), the resulting sample is **not statistically independent**. Residual market autocorrelation, conditional heteroskedasticity, and regime persistence remain present.

---

### C. Clean Feature Diagnostics, Exact Duplicates & PCA Spectrum

#### 1. Zero-Variance Exclusion & Clean Collinearity Matrix

In Phase 17, feature `is_daily_roll_window` had zero variance across the training dataset (it was constant 0 due to timestamp filtering). Computing Pearson correlation against a constant feature results in division by zero ($0/0 = \text{NaN}$), which sorted arbitrarily to the top of collinearity rankings.

*Correction:* Zero-variance columns were identified and excluded before computing correlation matrices and PCA:
*   Raw features: 232
*   Zero-variance features excluded: `is_daily_roll_window` (1)
*   Clean features analyzed: 231
*   Valid non-trivial pairwise correlations: 26,565

#### 2. Clean Collinearity Counts & Top Redundancies

| Correlation Threshold | Pair Count | Percentage of All Pairs |
| :--- | :---: | :---: |
| $|r| \ge 0.80$ | 783 | 2.95% |
| $|r| \ge 0.90$ | 277 | 1.04% |
| $|r| \ge 0.95$ | 100 | 0.38% |
| $|r| \ge 0.98$ | 54 | 0.20% |
| $|r| \ge 0.99$ | 48 | 0.18% |
| **$|r| = 1.000$ (Exact Duplicates)** | **41** | **0.15%** |

#### 3. Linear Redundancy vs. Feature Correlation

The audit identified **41 pairs of exact mathematical duplicates** ($|r| = 1.000000$):
*   `rsi_14` vs. `rsi_14_norm` ($r = 1.000000$): Min-max scaling does not alter linear correlation.
*   `dist_ema_200` vs. `ema_slope_200` ($r = 0.999999996$): Proximity to an EMA and its empirical slope are collinear transformations of the same price differential.
*   `candle_span` vs. `log_hl_ratio` ($r = 0.9999988$): High-Low span and log ratio are exact monotonic transforms.
*   Identical redundancies repeated across higher timeframes (`htf_h1_rsi_14` vs `htf_h1_rsi_14_norm`, `htf_h4_dist_ema_200` vs `htf_h4_ema_slope_200`).

*Methodological Rule:* Exact duplicates represent zero additional information and introduce singularity into linear covariance matrices. In contrast, merely correlated features ($0.80 \le |r| \le 0.95$) retain independent variance but cause multicollinearity and parameter instability in unregularized models.

#### 4. PCA Variance Spectrum

PCA was performed on the standardized 231 clean features:
*   **29 principal components** explain **80%** of total variance.
*   **52 principal components** explain **90%** of total variance.
*   **71 principal components** explain **95%** of total variance.
*   **106 principal components** explain **99%** of total variance.
*   **Redundant Dimensions:** At the 90% variance threshold, **179 of 231 features (77.5%) are redundant linear combinations**.

---

### D. Transaction Cost Accounting & Empirical Payoffs

#### 1. Spread, Slippage, and Commission Architecture

Phase 17 contained conflicting statements regarding whether $0.20 was a "half-spread" or "full spread", leading to ambiguity over whether round-turn costs were $0.30 or $0.50.

*   **Spot Gold Quotation Convention:** Spot gold is quoted as Bid and Ask. The spread $S = \text{Ask} - \text{Bid}$. For an institutional broker, a typical spread is $\$0.20/\text{oz}$.
*   **Round-Turn Mechanics:** A long position enters by buying at Ask and exits by selling at Bid. The trade crosses the spread **exactly once** across the entire lifecycle:
    $$\text{Gross PnL} = \text{Exit Bid} - \text{Entry Ask} = (\text{Exit Mid} - 0.5 S) - (\text{Entry Mid} + 0.5 S) = \Delta \text{Mid} - S$$
    Therefore, the broker spread of $\$0.20$ is the total spread friction per round turn, not $\$0.40$.
*   **Static vs. Realized Dynamic Friction:**
    *   *Static Formula:* $\text{Spread } (\$0.20) + \text{Entry Slippage } (\$0.05) + \text{Exit Slippage } (\$0.05) = \$0.30/\text{oz}$.
    *   *Realized Dynamic Backtest Cost:* The backtester's `ExecutionCostModel` incorporates session multipliers (e.g., $1.5\times$ spread and slippage outside peak London/NY hours) and ATR volatility expansion.
    *   *Empirical Result:* The actual realized average friction paid across historical trades is **$\sim \$0.6039/\text{oz}$** (approximately double static base costs).
*   **Overnight Financing (Swap):** Intraday trades ($H \le 96$, $< 8$ hours) never held positions past the daily 17:00 NY rollover and thus incurred $\$0.00$ swap debits. However, any multi-day macro strategy holding gold overnight **must model swap financing** (typically SOFR-based debits of $-0.015\%$ to $-0.03\%$ per day for long spot gold).

#### 2. Empirical Asymmetric Break-Even Analysis

Phase 17 applied a symmetric-payoff break-even formula:
$$w_{\text{BE}} = \frac{1}{2}\left(1 + \frac{C}{\text{Median Move}}\right)$$
This formula strictly assumes:
1. Average gross win equals average gross loss ($G = L$).
2. Payoffs are symmetrically distributed around zero.

These assumptions are violated in actual trading data. When winners and losers have unequal magnitudes, the true break-even win rate is given by the exact asymmetric expectation formula:
$$\mathbb{E}[\text{Net PnL}] = w \cdot \overline{G}_{\text{win}} - (1 - w) \cdot \overline{L}_{\text{loss}} - \overline{C} = 0$$
$$w_{\text{BE}} = \frac{\overline{L}_{\text{loss}} + \overline{C}}{\overline{G}_{\text{win}} + \overline{L}_{\text{loss}}}$$

Using the actual trade distributions from out-of-fold evaluations:

| Parameter | Incumbent Model ($H=24$, 2h) | Candidate 5 Swing ($H=96$, 8h) |
| :--- | :---: | :---: |
| **Total Trades** | 2,724 | 531 |
| **Actual Win Rate** | 45.41% | 48.21% |
| **Average Gross Win ($\overline{G}_{\text{win}}$)** | $\$5.44/\text{oz}$ | $\$11.22/\text{oz}$ |
| **Average Gross Loss ($\overline{L}_{\text{loss}}$)** | $\$4.34/\text{oz}$ | $\$9.48/\text{oz}$ |
| **Average Realized Friction ($\overline{C}$)** | $\$0.60/\text{oz}$ | $\$0.64/\text{oz}$ |
| **Average Net Win** | $\$4.84/\text{oz}$ | $\$10.64/\text{oz}$ |
| **Average Net Loss** | $\$4.95/\text{oz}$ | $\$10.17/\text{oz}$ |
| **Empirical Break-Even Win Rate ($w_{\text{BE}}$)** | **50.56%** | **48.88%** |
| **Actual vs. Break-Even Deficit** | **-5.14%** | **-0.67%** |

*Takeaway:*
*   For the Incumbent model, average gross wins ($\$5.44$) exceeded gross losses ($\$4.34$). Despite this asymmetric advantage, cost friction of $\$0.60/\text{oz}$ shifted the net payoff negative, requiring a $50.56\%$ win rate. Because actual win rate was only $45.41\%$, the model suffered substantial losses.
*   For Candidate 5, longer holding periods produced larger wins ($\$11.22$) relative to friction ($\$0.64$). The empirical break-even win rate dropped to $48.88\%$. While Candidate 5 achieved $48.21\%$, narrowing the deficit to $-0.67\%$, it remained sub-break-even.

---

## 2. Methodological Corrections to Research Interpretation

To prevent confirmation bias and unsupported extrapolations, the following five methodological rules are formally adopted:

### 1. $\text{MFE} = \text{MAE}$ Does Not Prove a Random Walk
*   **Mathematical Fact:** The equality of pooled forward MFE and pooled forward MAE is an algebraic identity that holds for **any price series whatsoever**.
    $$\text{Short MFE} \equiv \text{Long MAE} = \text{Open} - \min(\text{Low})$$
    $$\text{Short MAE} \equiv \text{Long MFE} = \max(\text{High}) - \text{Open}$$
    $$\text{Pooled MFE} = \frac{1}{2}(\text{Long MFE} + \text{Short MFE}) = \frac{1}{2}(\max(\text{High}) - \min(\text{Low})) \equiv \text{Pooled MAE}$$
*   **Correction:** Observing pooled $\text{MFE} = \text{MAE}$ provides zero evidence regarding the underlying data-generating process and cannot be cited as proof of Brownian motion or martingale dynamics.

### 2. Non-Overlapping Observations Do Not Guarantee Statistical Independence
*   **Statistical Fact:** Sampling observations at non-overlapping intervals (e.g. 1 observation every $H$ bars) eliminates the mechanical moving-average covariance induced by overlapping horizons. However, financial asset returns exhibit persistent volatility clustering (ARCH/GARCH), structural regime shifts, and autocorrelation in higher moments.
*   **Correction:** Non-overlapping samples mitigate moving-average label overlap, but do not satisfy i.i.d. assumptions. Standard errors must still account for heteroskedasticity and residual serial dependence.

### 3. Daily Bars Do Not Eliminate All Serial Correlation
*   **Empirical Fact:** Aggregating intraday M5 bars into daily bars removes high-frequency microstructure noise, bid-ask bounce, and intraday session seasonality. However, daily returns of macroeconomic assets like gold frequently exhibit multi-day momentum, macro regime persistence, and interest-rate trend correlation.
*   **Correction:** Daily aggregation alters the spectral frequency of the time series, but does not render daily price movements memoryless.

### 4. Lower Transaction-Cost Ratios Do Not Automatically Imply a Profitable Strategy
*   **Economic Fact:** At daily horizons ($H=288$), cost friction drops to $\sim 4\%\text{--}6\%$ of median price movement (compared to $26.6\%$ at $H=24$). While lower friction is a necessary condition for profitability, it is **not sufficient**.
*   **Correction:** A strategy with zero friction can still lose money if its directional accuracy is worse than random or if adverse selection impairs entry timing. Lower cost friction merely removes a mechanical headwind; it does not generate alpha.

### 5. Passing Statistical or Robustness Tests Does Not Prove Predictive Edge
*   **Scientific Fact:** Statistical tests (such as bootstrapping, permutation tests, or stationary bootstrap) can reject specific null hypotheses (e.g., rejecting that mean return is strictly zero). However, passing such tests in-sample or on historical development folds does not prove an enduring predictive edge.
*   **Correction:** Statistical significance establishes only that observed performance is unlikely under an idealized null model. It cannot guard against data snooping, regime change, structural breaks, or post-decision execution decay.

---

## 3. Verified Diagnostic Data Summary

All metrics reported herein have been generated deterministically by `scripts/run_phase18b_corrected_diagnostics.py` and validated by `tests/test_phase18b_diagnostics.py`. Full numerical artifacts are archived in `reports/phase18b/phase18b_results.json`.
