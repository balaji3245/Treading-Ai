# PHASE 25 DECISION RECORD: CONTROLLED DEVELOPMENT BACKTEST

**Hypothesis ID:** `HYP-24-NY-REVERSAL-EXHAUSTION`  
**Phase:** 25 — Controlled Development Backtest  
**Repository:** `Treading-Ai`  
**Baseline Git Commit:** `5038d33e4ff7e76d7f8d308da0b9b76132bfdc82`  
**Execution Timestamp:** 2026-10-30T03:55:00 UTC  

---

## Final Formal Verdict

```
PHASE 25 VERDICT: PASS
```

*Controlled development backtest gates satisfied; hypothesis is authorized for locked out-of-sample validation.*  
*(Passing development does NOT authorize live trading or establish commercial profitability).*

---

## 1. Pre-Registered Promotion Gate Evaluation Scorecard

All four promotion gates codified in `reports/phase24/frozen_evaluation_protocol.md` were evaluated on the 2021–2022 development partition without modification or relaxation:

| Gate | Criterion / Requirement | Evaluated Metric (2021–2022) | Status |
| :--- | :--- | :--- | :--- |
| **Gate 1: Economic Edge** | Net Expectancy $\ge +\$0.50/\text{oz}$ | **+$1.442/\text{oz}$** | **PASSED** |
| | Net Profit Factor $\ge 1.25$ | **1.586** | **PASSED** |
| | Directional Win Rate $\ge 52.5\%$ | **58.06%** (72W / 52L) | **PASSED** |
| | Positive Net PnL under 1.5× cost stress ($0.375/oz) | **+$163.331/\text{oz}$** (PF 1.523) | **PASSED** |
| **Gate 2: Directional Symmetry** | Long Net Profit Factor $\ge 1.10$ | **1.629** (Net PnL +$82.10) | **PASSED** |
| | Short Net Profit Factor $\ge 1.10$ | **1.554** (Net PnL +$96.73) | **PASSED** |
| | Directional Sample Balance | Exactly 62 Long / 62 Short | **PASSED** |
| **Gate 3: Statistical Significance** | Primary Metric 95% Bootstrap CI strictly $> \$0.00/\text{oz}$ | **[+$0.273, +$2.829] / \text{oz}$** | **PASSED** |
| | Outperformance over $0 no-trade baseline at $\alpha = 0.05$ | Established ($p < 0.01$) | **PASSED** |
| **Gate 4: Drawdown Boundary** | Maximum Peak-to-Trough Drawdown $\le \$45.00/\text{oz}$ | **$36.301/\text{oz}$** (0.36%) | **PASSED** |

---

## 2. Decision Rationale & Performance Verification

1. **Robust Quantitative Edge in Development:**
   - On the 2021–2022 development partition (141,614 M5 bars across 495 trading days), `HYP-24-NY-REVERSAL-EXHAUSTION` generated +$178.831/oz net of baseline friction across 124 executed trades.
   - The primary performance metric—mean net expectancy—is +$1.442/oz, nearly triple the minimum gate requirement of +$0.50/oz.
2. **Resolution of Directional Asymmetry:**
   - Unlike the rejected trend-following paradigm from Phase 23, the afternoon reversal mechanism is balanced:
     - Long trades: PF = 1.629, Win Rate = 59.68%, Net PnL = +$82.104/oz.
     - Short trades: PF = 1.554, Win Rate = 56.45%, Net PnL = +$96.727/oz.
   - Sub-cohort participation is symmetric (62 Long / 62 Short), confirming that the morning excursion exhaustion signal operates symmetrically on both upside and downside overextensions.
3. **Statistical Confidence Intervals:**
   - Moving-block bootstrap resampling ($B=2,000, b=5$) yields a 95% confidence interval of `[+$0.273, +$2.829]/oz` for mean net expectancy. Because the lower bound is strictly positive, the null hypothesis of zero economic edge is rejected at $\alpha = 0.05$.
4. **Friction Resilience:**
   - Even under 2.0× stressed execution costs ($0.50/oz round-turn), the strategy produces +$147.831/oz net PnL with a profit factor of 1.464, demonstrating substantial cushion against real-world slippage.
5. **Absolute Partition Governance:**
   - The 2023–2024 dataset remained uninspected during development and parameter freezing.
   - The 2025 validation and 2026 test partitions were cryptographically audited and confirmed 100% untouched.

---

## 3. Scope of Authorization

1. **What is Authorized:**
   - Formal closure of Phase 25 with a verdict of `PASS`.
   - Progression to **Phase 26: Locked Out-of-Sample Validation**, evaluating the frozen strategy on the 2023–2024 partition.
   - Permanent locking of strategy parameters:
     - Baseline anchor: 11:55 UTC bar close ($P_{\text{base}}$).
     - Excursion measurement: 13:55 UTC bar close ($P_{\text{14:00}}$).
     - Trailing ATR20: Lagged by 1 full day (`shift(1)`).
     - Frozen exhaustion threshold: $\theta_{\text{exhaustion}} = 0.320210$.
     - Entry timing: 14:05 UTC bar open.
     - Stop-loss: $0.75 \times |\Delta P_t|$ beyond entry price.
     - Scheduled flat exit: 18:25 UTC bar close (18:30 UTC pit close).
     - Baseline friction: $0.25/oz.
2. **What is NOT Authorized:**
   - Any re-tuning, optimization, or threshold adjustment prior to Phase 26.
   - Any access to the protected 2025 validation or 2026 test partitions.
   - Live trading, capital deployment, or claims of commercial profitability.

---

## 4. Required Phase 26 Evaluation Conditions

When executing Phase 26 on the 2023–2024 partition:
1. Load `data/processed/XAUUSD/M5/` for 2023 and 2024.
2. Maintain strict fail-closed boundary protections against 2025/2026 data.
3. Apply the frozen threshold $\theta_{\text{exhaustion}} = 0.320210$ without recalibration.
4. Transparently disclose that 2023–2024 was previously utilized in Phase 20 macro research (non-pristine status).
5. Evaluate against the identical promotion gates established in Phase 24.
