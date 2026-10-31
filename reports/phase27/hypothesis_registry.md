# PHASE 27: PRE-REGISTERED HYPOTHESIS REGISTRY

**Document Version:** 1.0.0 (FROZEN PRE-REGISTRATION)  
**Phase:** 27 — New Hypothesis Discovery & Research Design  
**Repository:** `Treading-Ai`  
**Instrument:** XAUUSD (Spot Gold / US Dollar), M5 Timeframe  
**Execution Timestamp:** 2026-10-30T13:10:00 UTC  
**Baseline Commit:** `5038d33e4ff7e76d7f8d308da0b9b76132bfdc82`  
**Development Scope:** 2021-01-01 to 2022-12-31 UTC Partition ($N = 141,614$ M5 bars)  

---

## 1. Governance & Anti-P-Hacking Mandate

In strict accordance with quantitative research protocol:
1. All five candidate hypotheses documented herein are **pre-registered prior to running formal performance experiments**.
2. Thresholds, feature calculations, holding durations, and promotion/rejection criteria are permanently frozen.
3. Once hashed, this document serves as the immutable benchmark for Phase 27 experimental evaluation.
4. Any post-hoc parameter adjustments, sliding-window re-optimizations, or cherry-picked rules will be treated as protocol violations.

---

## 2. Pre-Registered Candidate Hypotheses

```
====================================================================================================
HYPOTHESIS 1: HYP-27-VOL-SHOCK-EXPANSION
====================================================================================================
1. Hypothesis ID:
   HYP-27-VOL-SHOCK-EXPANSION
2. Proposed Market Mechanism:
   Physical bullion trading in Tokyo, Shanghai, and Hong Kong during the Asian session (00:00–07:00 UTC)
   is normally subdued. When the Asian session experiences extreme volatility expansion coupled with directional
   closing conviction, it reflects sovereign reserve reallocation or Eastern physical market flow rather than noise.
   By Mandelbrot-Engle volatility clustering, large price moves follow large price moves. When institutional
   European dealers enter at 08:00 UTC, order flow does not chop or revert; it clusters and continues the overnight
   directional expansion through the London morning.
3. Observable Features & Exact Calculations:
   - Asian True Range: Range_asia = max_{t in [00:00, 07:00)} High_t - min_{t in [00:00, 07:00)} Low_t
   - Asian Directional Vector: DeltaP_asia = Close_{06:55 bar} - Open_{00:00 bar}
   - Prior Volatility Benchmark: ATR20_prior = (1/20) * sum_{k=1}^{20} DailyTR_{d-k} (lagged by 1 full day)
   - Normalized Asian Range Ratio: NAR = Range_asia / ATR20_prior
   - Directional Conviction Ratio: Conviction = |DeltaP_asia| / Range_asia
4. Frozen Thresholds & Eligibility Rules:
   - Extreme Volatility Condition: NAR >= 0.50 (Top quartile of Asian volatility relative to daily ATR)
   - Directional Conviction Condition: Conviction >= 0.60 (Directional move accounts for >= 60% of total range)
   - Minimum Magnitude: |DeltaP_asia| >= $6.00/oz (Ensures price excursion clears transaction cost barrier)
5. Execution Timing & Mechanics:
   - Decision Timestamp: 07:00:00 UTC (Realized at 06:55 M5 bar close).
   - Execution Entry: 08:05:00 UTC bar open (European cash equity open, providing 1-hour latency/settlement buffer).
   - Fill Price: Open of 08:05:00 UTC bar.
   - Direction: Trend-following with Asian directional vector:
       Direction = +1 (LONG) if DeltaP_asia > 0; -1 (SHORT) if DeltaP_asia < 0.
6. Stop-Loss & Exit Rules:
   - Stop-Loss: Entry Price - (0.75 * |DeltaP_asia|) for Long; Entry Price + (0.75 * |DeltaP_asia|) for Short.
   - Intrabar Order of Operations: Stop checked before scheduled exit on every bar.
   - Adverse Open-Gap Slippage: Executed at Open if bar opens beyond stop.
   - Adverse Entry-Gap Abort: Aborted if 08:05 bar opens beyond initial stop price.
   - Scheduled Time Exit: Flat exit at 12:00:00 UTC Close (11:55 M5 bar close, 47 M5 bars held).
7. Expected Direction of Effect:
   Positive net expectancy in the direction of the overnight Asian momentum.
8. Minimum Sample Size Requirement:
   N >= 35 trades across the 2-year development partition.
9. Transaction Cost & Slippage Assumptions:
   1.0x Baseline: $0.25/oz round-turn ($0.20 spread + $0.05 slippage).
   1.5x Elevated: $0.375/oz; 2.0x Stressed: $0.50/oz. Overnight swap: $0.00/oz (liquidates 9 hours before rollover).
10. Confounders & Falsification Tests:
    - Confounder: London morning fakeout/whipsaws on minor central bank statements.
    - Falsification: Reverse direction test (counter-trend entry). If fading Asian shocks is superior, trend clustering is falsified.
11. Pre-Registered Rejection Criteria:
    Reject if Net Expectancy < +$0.50/oz, Net PF < 1.25, Win Rate < 50.0%, or either Long/Short sub-cohort PF < 1.05.

====================================================================================================
HYPOTHESIS 2: HYP-27-LONDON-PM-FIX-IMBALANCE
====================================================================================================
1. Hypothesis ID:
   HYP-27-LONDON-PM-FIX-IMBALANCE
2. Proposed Market Mechanism:
   The LBMA Gold Price PM Fix (15:00 UTC) is the preeminent global auction benchmark used by central banks,
   mining houses, and institutional ETFs for daily balance-sheet valuation. Strong directional displacement
   leading into the PM Fix (14:00–15:00 UTC) represents institutional order imbalances that dealers must
   warehouse and lay off into the physical London cash close (17:00 UTC). This institutional rebalancing creates
   directional post-auction momentum over the subsequent 2 hours.
3. Observable Features & Exact Calculations:
   - Pre-Fix Anchor: P_1400 = Close of 13:55 M5 bar (14:00:00 UTC).
   - Fix Settlement: P_1500 = Close of 14:55 M5 bar (15:00:00 UTC).
   - Pre-Fix Displacement: DeltaP_fix = P_1500 - P_1400
   - Fix Displacement Ratio: FDR = |DeltaP_fix| / ATR20_prior
4. Frozen Thresholds & Eligibility Rules:
   - Imbalance Condition: FDR >= 0.20 (Pre-fix displacement exceeds 20% of trailing daily ATR).
   - Minimum Absolute Displacement: |DeltaP_fix| >= $5.00/oz.
5. Execution Timing & Mechanics:
   - Decision Timestamp: 15:00:00 UTC (14:55 M5 bar close).
   - Execution Entry: 15:05:00 UTC bar open (First bar post-auction).
   - Fill Price: Open of 15:05:00 UTC bar.
   - Direction: Trend-following with auction displacement:
       Direction = +1 (LONG) if DeltaP_fix > 0; -1 (SHORT) if DeltaP_fix < 0.
6. Stop-Loss & Exit Rules:
   - Stop-Loss: Entry Price - (0.75 * |DeltaP_fix|) for Long; Entry Price + (0.75 * |DeltaP_fix|) for Short.
   - Stop Precedence: Stop evaluated before time exit on every bar.
   - Scheduled Time Exit: Flat exit at 17:00:00 UTC Close (16:55 M5 bar close, London cash market close, 23 bars held).
7. Expected Direction of Effect:
   Momentum continuation in the direction of the 14:00–15:00 UTC benchmark displacement.
8. Minimum Sample Size Requirement:
   N >= 60 trades across 2021–2022.
9. Transaction Cost & Slippage Assumptions:
   1.0x Baseline: $0.25/oz; 1.5x Elevated: $0.375/oz; 2.0x Stressed: $0.50/oz. Swap: $0.00/oz (liquidates 4 hours before rollover).
10. Confounders & Falsification Tests:
    - Confounder: Overlap with US 14:30–15:00 UTC macro data releases.
    - Falsification: Test days without significant macro releases vs days with releases. Test random time-shifted auction window (13:00 UTC).
11. Pre-Registered Rejection Criteria:
    Reject if Net Expectancy < +$0.50/oz, Net PF < 1.25, Win Rate < 50.0%, or either directional PF < 1.05.

====================================================================================================
HYPOTHESIS 3: HYP-27-POST-COMEX-DRIFT-REVERSION
====================================================================================================
1. Hypothesis ID:
   HYP-27-POST-COMEX-DRIFT-REVERSION
2. Proposed Market Mechanism:
   At 18:30 UTC, the COMEX gold futures trading pit closes and commercial pit market makers terminate operations.
   Between 18:30 and 20:00 UTC, market liquidity drops by >70% into the evening lull. Unsolicited retail or algorithmic
   price drift away from the official COMEX settlement price during this illiquid window lacks commercial institutional
   backing and systematically mean-reverts back toward the COMEX settlement price prior to the daily broker rollover (21:55 UTC).
3. Observable Features & Exact Calculations:
   - COMEX Settlement Anchor: P_settle = Close of 18:25 M5 bar (18:30:00 UTC).
   - Post-Pit Measurement: P_2000 = Close of 19:55 M5 bar (20:00:00 UTC).
   - Post-Pit Drift: DeltaP_drift = P_2000 - P_settle
   - Post-Pit Drift Ratio: PDR = |DeltaP_drift| / ATR20_prior
4. Frozen Thresholds & Eligibility Rules:
   - Drift Condition: PDR >= 0.12 (Drift exceeds 12% of daily ATR without institutional volume).
   - Absolute Minimum Drift: |DeltaP_drift| >= $3.00/oz.
5. Execution Timing & Mechanics:
   - Decision Timestamp: 20:00:00 UTC (19:55 M5 bar close).
   - Execution Entry: 20:05:00 UTC bar open.
   - Fill Price: Open of 20:05:00 UTC bar.
   - Direction: Counter-trend reversion toward COMEX settlement:
       Direction = -1 (SHORT) if DeltaP_drift > 0; +1 (LONG) if DeltaP_drift < 0.
6. Stop-Loss & Exit Rules:
   - Stop-Loss: Entry Price + (0.75 * |DeltaP_drift|) for Short; Entry Price - (0.75 * |DeltaP_drift|) for Long.
   - Intrabar Stop Precedence: Checked before time exit.
   - Scheduled Time Exit: Flat exit at 21:55:00 UTC Close (21:55 M5 bar close, 23 bars held).
   - Zero Rollover Risk: Must terminate strictly at 21:55:00 UTC, avoiding the 22:00 UTC broker rollover and swap fees.
7. Expected Direction of Effect:
   Mean-reversion back toward P_settle.
8. Minimum Sample Size Requirement:
   N >= 60 trades across 2021–2022.
9. Transaction Cost & Slippage Assumptions:
   1.0x Baseline: $0.25/oz; 1.5x Elevated: $0.375/oz; 2.0x Stressed: $0.50/oz. Swap: $0.00/oz verified.
10. Confounders & Falsification Tests:
    - Confounder: Widening spreads in the late evening session.
    - Falsification: Test trend-following entry. If trend-following outperforms reversion, drift reversion hypothesis is false.
11. Pre-Registered Rejection Criteria:
    Reject if Net Expectancy < +$0.50/oz, Net PF < 1.25, Win Rate < 52.0%, or either directional PF < 1.05.

====================================================================================================
HYPOTHESIS 4: HYP-27-CONSECUTIVE-RANGE-MOMENTUM
====================================================================================================
1. Hypothesis ID:
   HYP-27-CONSECUTIVE-RANGE-MOMENTUM
2. Proposed Market Mechanism:
   Volatility regimes cluster at the daily timeframe. When the prior trading day experienced expanding true range
   relative to trailing ATR (TR_{d-1} > ATR20_{d-1}), the gold market enters an active volatility expansion regime.
   Under this regime, the initial directional impulse established during the first two hours of London trading
   (07:00–09:00 UTC) indicates persistent institutional flow that continues throughout the European/US crossover session.
3. Observable Features & Exact Calculations:
   - Prior Daily Range Expansion: TR_{d-1} > ATR20_{d-1}^{prior}
   - London Opening Anchor: P_0700 = Close of 06:55 M5 bar (07:00:00 UTC).
   - London Morning Measurement: P_0900 = Close of 08:55 M5 bar (09:00:00 UTC).
   - London Impulse Vector: DeltaP_london = P_0900 - P_0700
   - London Impulse Ratio: LIR = |DeltaP_london| / ATR20_{d-1}^{prior}
4. Frozen Thresholds & Eligibility Rules:
   - Expansion Regime: TR_{d-1} > ATR20_{d-1}^{prior}
   - Impulse Magnitude: LIR >= 0.20 (London impulse exceeds 20% of trailing daily ATR).
   - Minimum Impulse: |DeltaP_london| >= $5.00/oz.
5. Execution Timing & Mechanics:
   - Decision Timestamp: 09:00:00 UTC (08:55 M5 bar close).
   - Execution Entry: 09:05:00 UTC bar open.
   - Fill Price: Open of 09:05:00 UTC bar.
   - Direction: Trend-following with London impulse:
       Direction = +1 (LONG) if DeltaP_london > 0; -1 (SHORT) if DeltaP_london < 0.
6. Stop-Loss & Exit Rules:
   - Stop-Loss: Entry Price - (0.75 * |DeltaP_london|) for Long; Entry Price + (0.75 * |DeltaP_london|) for Short.
   - Stop Precedence: Evaluated before time exit.
   - Scheduled Time Exit: Flat exit at 16:00:00 UTC Close (15:55 M5 bar close, 83 bars held).
7. Expected Direction of Effect:
   Trend continuation in the direction of the London morning impulse.
8. Minimum Sample Size Requirement:
   N >= 40 trades across 2021–2022.
9. Transaction Cost & Slippage Assumptions:
   1.0x Baseline: $0.25/oz; 1.5x Elevated: $0.375/oz; 2.0x Stressed: $0.50/oz. Swap: $0.00/oz (liquidates at 16:00 UTC).
10. Confounders & Falsification Tests:
    - Confounder: US morning announcement reversals (12:30–13:30 UTC).
    - Falsification: Test days where TR_{d-1} <= ATR20 (compression regime). If performance is identical, the regime conditioning is falsified.
11. Pre-Registered Rejection Criteria:
    Reject if Net Expectancy < +$0.50/oz, Net PF < 1.25, Win Rate < 50.0%, or either directional PF < 1.05.

====================================================================================================
HYPOTHESIS 5: HYP-27-MONDAY-WEEKEND-GAP-REVERSION
====================================================================================================
1. Hypothesis ID:
   HYP-27-MONDAY-WEEKEND-GAP-REVERSION
2. Proposed Market Mechanism:
   XAUUSD trading terminates Friday at 21:55 UTC and reopens Sunday at 23:00 UTC. Weekend headline news flow often
   causes emotional opening gaps. If an opening price gap persists into the early Asian session without expanding
   further by 02:00 UTC, the move represents an unbacked liquidity-vacuum displacement. As commercial Asian physical
   dealers enter the market between 02:00 and 07:00 UTC, price mean-reverts back toward Friday's official closing benchmark.
3. Observable Features & Exact Calculations:
   - Friday Benchmark Close: P_fri_close = Close of Friday 21:55 M5 bar.
   - Monday Asian Anchor: P_mon_0200 = Close of Monday 01:55 M5 bar (02:00:00 UTC).
   - Weekend Gap Vector: DeltaP_gap = P_mon_0200 - P_fri_close
   - Gap Ratio: GapRatio = |DeltaP_gap| / ATR20_{monday}^{prior}
4. Frozen Thresholds & Eligibility Rules:
   - Session Filter: Applied strictly on Mondays.
   - Gap Magnitude: GapRatio >= 0.15 (Weekend gap exceeds 15% of daily ATR).
   - Minimum Absolute Gap: |DeltaP_gap| >= $3.50/oz.
5. Execution Timing & Mechanics:
   - Decision Timestamp: Monday 02:00:00 UTC (01:55 M5 bar close).
   - Execution Entry: Monday 02:05:00 UTC bar open.
   - Fill Price: Open of Monday 02:05:00 UTC bar.
   - Direction: Counter-trend reversion toward Friday close:
       Direction = -1 (SHORT) if DeltaP_gap > 0; +1 (LONG) if DeltaP_gap < 0.
6. Stop-Loss & Exit Rules:
   - Stop-Loss: Entry Price + (0.75 * |DeltaP_gap|) for Short; Entry Price - (0.75 * |DeltaP_gap|) for Long.
   - Stop Precedence: Checked before time exit.
   - Scheduled Time Exit: Flat exit at Monday 07:00:00 UTC Close (06:55 M5 bar close, Asian session close, 59 bars held).
7. Expected Direction of Effect:
   Mean-reversion toward Friday closing price.
8. Minimum Sample Size Requirement:
   N >= 25 trades across 2021–2022 Mondays.
9. Transaction Cost & Slippage Assumptions:
   1.0x Baseline: $0.25/oz; 1.5x Elevated: $0.375/oz; 2.0x Stressed: $0.50/oz. Swap: $0.00/oz.
10. Confounders & Falsification Tests:
    - Confounder: War outbreaks or major Sunday geopolitical escalations creating permanent unfillable gaps.
    - Falsification: Test Monday trend continuation. If continuation is superior, gap-fill hypothesis is falsified.
11. Pre-Registered Rejection Criteria:
    Reject if Net Expectancy < +$0.50/oz, Net PF < 1.25, Win Rate < 50.0%, or either directional PF < 1.05.
```

---

## 3. Pre-Registered Promotion Gates (Phase 27 Decision Framework)

To qualify as a **CANDIDATE FOR FURTHER RESEARCH**, a hypothesis must satisfy all 6 development promotion gates on the authorized 2021–2022 development partition without post-hoc tuning:

1. **Gate 1: Minimum Economic Expectancy:**
   - Net Expectancy per trade $\ge +\$0.50/\text{oz}$ after 1.0× baseline friction ($0.25/oz).
2. **Gate 2: Net Profit Factor:**
   - Net Profit Factor $\ge 1.25$ under 1.0× baseline friction.
3. **Gate 3: Directional Hit Rate:**
   - Directional Win Rate $\ge 50.0\%$.
4. **Gate 4: Friction Stress Tolerance:**
   - Positive net PnL maintained under 1.5× elevated cost stress ($0.375/oz).
5. **Gate 5: Directional Symmetry:**
   - Both Long and Short directional sub-cohorts must achieve Net Profit Factor $\ge 1.05$. (Any severe directional collapse mandates rejection).
6. **Gate 6: Multiple Hypothesis Testing Control:**
   - Statistical significance evaluated under Holm–Bonferroni family-wise error rate control ($m = 5, \alpha = 0.05$).

---

## 4. Decision Classification Schema

Each pre-registered hypothesis will be assigned exactly one terminal classification:
- **REJECTED:** The empirical evidence contradicts the proposed economic edge, fails promotion gates, or collapses under friction stress.
- **INCONCLUSIVE:** Evidence or sample size is insufficient ($N < N_{\min}$), or statistical tests fail to achieve significance after multiple testing adjustment.
- **CANDIDATE FOR FURTHER RESEARCH:** Survives all pre-registered development checks on 2021–2022 without p-hacking. *(Note: Passing development does NOT authorize live trading or establish out-of-sample profitability).*
