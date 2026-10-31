# Phase 34: Preregistration Integrity & Specification Audit

**Document Type:** Quantitative Research Audit & Model Governance Review  
**Auditor:** Senior Quantitative Research Auditor & Financial ML Validation Specialist  
**System:** Treading-Ai (XAUUSD Research-Only)  
**Date:** November 2026  
**Status:** COMPLETE — AMBIGUITIES & CONFLICTS CATALOGED  

---

## 1. Executive Summary

This audit inspects the mathematical rigor, causality, and internal consistency of Phase 33's pre-registered swing hypotheses ([`reports/phase33/hypothesis_preregistration.md`](file:///home/bhoot/project/Treading-Ai/reports/phase33/hypothesis_preregistration.md)), feature pipeline ([`reports/phase33/feature_dictionary.md`](file:///home/bhoot/project/Treading-Ai/reports/phase33/feature_dictionary.md)), and evaluation protocol ([`reports/phase33/evaluation_protocol.md`](file:///home/bhoot/project/Treading-Ai/reports/phase33/evaluation_protocol.md)).

### Overall Assessment:
1. **Mathematical & Causal Formulation:** The mathematical formulas, indicator equations, and temporal causality constraints ($d1\_available\_ts \le h4\_decision\_ts$) are sound and lookahead-free.
2. **Critical Specification Conflicts Detected:**
   - **Sample Size Contradiction:** The evaluation protocol mandates a hard cutoff of $N \ge 60$ trades for acceptance, but the pre-registered frequency expectations for `H-Swing-02` (40–70 trades over 2 years) and `H-Swing-03` (30–60 trades over 2 years) allow realized sample sizes below 60, creating an automatic failure trap.
   - **Data Partition Contamination:** The evaluation protocol is constructed around testing on 2023–2024 as an "untouched confirmatory testbed," which has been formally invalidated by Phase 23 and Phase 26 audit records.
   - **Unmodeled Swap Asymmetry & Weekend Gap Risk:** The cost model assumes symmetric long/short swaps and lacks an explicit gap-execution policy for weekend rollovers.

---

## 2. Hypothesis-by-Hypothesis Integrity Audit

### 2.1 Hypothesis 1 (`H-Swing-01`): D1 Trend Regime Filtered H4 Pullback Continuation

| Dimension | Specification Audit | Status | Notes / Findings |
| :--- | :--- | :---: | :--- |
| **Signal Definition** | $d1\_regime == \pm 1$, $d1\_slope > 0$, $-1.50 \le pb\_depth \le -0.25$, candle wick $\ge 0.25$. | **PASS** | Fixed, unambiguous mathematical conditions evaluated at `h4_decision_ts`. |
| **Causal Timing** | Merged D1 candle finalized at 17:00 NY ($d1 \le h4$). Entry at open of $t+1$. | **PASS** | Strict causality preserved; zero within-bar lookahead. |
| **Targets & Stops** | Stop: $1.50 \times ATR_{14}(H4)$. Target: $3.00 \times ATR_{14}(H4)$. Time Stop: 18 H4 bars. | **PASS** | Fixed 2:1 payoff geometry; unambiguous time stop. |
| **Sample Size Alignment** | Expected: 35–55 trades/year (70–110 in 2 years). Protocol requires $N \ge 60$. | **PASS** | Expected frequency is compatible with protocol threshold. |
| **Falsification Criteria** | Net Expectancy $\le \$0.00$, Win rate $< 35\%$, Drawdown $> 15\%$. | **PASS** | Quantitative and objectively falsifiable. |

---

### 2.2 Hypothesis 2 (`H-Swing-02`): H4 Volatility Breakout Conditioned on D1 Compression

| Dimension | Specification Audit | Status | Notes / Findings |
| :--- | :--- | :---: | :--- |
| **Signal Definition** | $d1\_compression < 0.85$, $h4\_tr\_expansion \ge 1.40$, Donchian 20 break, body $\ge 0.60$. | **PASS** | Shifted Donchian channel prevents current-bar contamination. |
| **Causal Timing** | Evaluated at close of breakout bar. Entry at open of $t+1$. | **PASS** | Lookahead-free execution. |
| **Trailing Stop Rule** | Move to breakeven after $+1.50 \times \text{Risk}$, trail behind EMA10 of H4. | **AMBIGUOUS** | Does the EMA10 trail update only at H4 bar closes or intra-bar? Must be clarified as updating at candle close. |
| **Sample Size Alignment** | Expected: 20–35 trades/year (40–70 in 2 years). Protocol requires $N \ge 60$. | **CONFLICT** | **Critical Conflict:** If realized trades fall between 40 and 59, the strategy will fail the protocol gate despite functioning exactly as anticipated. |
| **Falsification Criteria** | Net Expectancy $\le \$0.00$, Win rate $< 30\%$, PF $< 1.35$. | **PASS** | Objectively falsifiable. |

---

### 2.3 Hypothesis 3 (`H-Swing-03`): Multi-Day Mean Reversion to Dynamic D1 Value Zone

| Dimension | Specification Audit | Status | Notes / Findings |
| :--- | :--- | :---: | :--- |
| **Signal Definition** | $d1\_adx < 20.0$, $cross\_zscore \ge \pm 2.0$, $h4\_rsi \le 30$ or $\ge 70$. | **PASS** | Stationarity and multi-timeframe alignment verified. |
| **Causal Timing** | Daily value anchor derived from completed $D-1$ session. | **PASS** | Fully causal. |
| **Target & Exit** | Target: $EMA_{20}(D1)_D$. Stop: $1.75 \times ATR_{14}$. Invalidation: $ADX > 25.0$. | **PASS** | Clear value-reversion anchor and regime invalidation. |
| **Sample Size Alignment** | Expected: 15–30 trades/year (30–60 in 2 years). Protocol requires $N \ge 60$. | **CONFLICT** | **Critical Conflict:** The expected frequency range has a median of 45 trades, falling well short of the protocol's 60-trade minimum gate. |
| **Falsification Criteria** | Net Expectancy $\le \$0.00$, Win rate $< 45\%$, Drawdown $> 12\%$. | **PASS** | Objectively falsifiable. |

---

## 3. Cross-Document Inconsistencies & Unsupported Assumptions

### 3.1 Conflict on Sample Size Gates
- In [`reports/phase33/evaluation_protocol.md`](file:///home/bhoot/project/Treading-Ai/reports/phase33/evaluation_protocol.md) Section 9, condition 8 states:
  > *"Sample Size Insufficiency: Total completed trades across the 2-year partition < 60 results in INSTANT REJECTION."*
- However, `H-Swing-02` and `H-Swing-03` are highly selective swing architectures whose pre-registered distributions allow trade totals in the 30–50 range over 2 years.
- **Required Correction:** The evaluation protocol must scale the minimum sample threshold relative to strategy selectivity, or explicitly specify that low-frequency swing strategies require a longer evaluation window (e.g. 3–4 years) to reach statistical power.

### 3.2 Omission of Retail Swap Asymmetry
- All three swap tiers ($0.08, $0.12, $0.18/oz/day) are modeled as symmetric for both long and short positions.
- **Microstructure Reality:** In OTC spot gold, brokers charge negative financing carry on long positions (reflecting the USD SOFR benchmark rate plus broker margin) that is substantially larger than any short credit. Many brokers charge negative swaps on *both* sides.
- **Impact:** Long swing trades held for 3 to 4 days will face higher financing drag than assumed in Phase 33.

### 3.3 Weekend Gap Execution Policy
- Spot gold trading halts at 17:00 NY on Friday and reopens at 18:00 NY on Sunday. Geopolitical events over weekends frequently cause price gaps at market open.
- **Omission in Protocol:** The protocol does not state whether a stop-loss order breached by a Sunday opening gap is executed at the stop price (an unrealistic assumption) or at the worse market open price (realistic execution).
- **Mandatory Policy:** The evaluation protocol must mandate execution at Sunday open price (slipping through the stop) whenever an opening gap breaches the stop level.

---

## 4. Separation of Evidentiary Categories

### Verified Evidence:
- Mathematical equations for all three hypotheses and the feature extractor are fully causal and deterministic.
- The 60-trade cutoff in `evaluation_protocol.md` conflicts with the 30–60 trade frequency range in `hypothesis_preregistration.md`.
- Phase 33 swap tiers are symmetric and do not reflect asymmetric retail broker pricing.

### Unverified Assumptions:
- The assumption that stop losses can be filled without gap slippage across weekend market closures.
- The assumption that symmetric swap tiers represent actual retail carry costs.

### Required Corrective Actions:
1. Reconcile sample size thresholds with selective swing holding periods before any evaluation run.
2. Formally mandate worst-case weekend gap execution in the execution simulator.
3. Incorporate asymmetric swap stress-testing into future evaluation protocols.
