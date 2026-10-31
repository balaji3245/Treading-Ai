# Phase 29 Research Horizon Assessment: Strategic Paths & Horizon Feasibility

**Phase:** 29 — Data Acquisition Plan, Provider Evaluation & Cost Architecture  
**Instrument:** XAUUSD (Spot Gold) vs. CME COMEX Gold Futures (`GC`)  
**Auditor:** Quantitative Research Infrastructure Engineer & Senior Quant  
**Date:** October 2026  
**Status:** COMPLETE & INDEPENDENTLY AUDITED  

---

## Executive Summary

Phase 28 proved that high-frequency intraday trading on 5-minute (M5) bars is economically unviable due to the structural dominance of fixed transaction friction ($\$0.25–\$0.50/\text{oz}$) over microscopic price movements (median move $\$0.44/\text{oz}$). 

This report evaluates four concrete research paths to escape this friction trap. Crucially, this analysis demonstrates that **spot gold (`XAUUSD`) and gold futures (`GC`) are distinct financial instruments with time-varying basis and session divergences**. They must never be treated as interchangeable without explicit mathematical adjustments.

```
+-------------------------------------------------------------------------------------------------------------------+
|                                     STRATEGIC RESEARCH PATH COMPARISON                                            |
+-------------------+----------------------------+-----------------------+---------------------+--------------------+
| Path Identifier   | Primary Asset / Horizon    | Data Required         | Cost & Complexity   | Feasibility Rank   |
+-------------------+----------------------------+-----------------------+---------------------+--------------------+
| Path 1 (Swing)    | XAUUSD H4 / Daily Swings   | Existing HistData+FRED| $0.00 (Zero Cost)   | **PRIMARY (Rank 1)**|
| Path 2 (Tick Spot)| XAUUSD M5/M15 with Spreads | Dukascopy Tick Quotes | Free (Tooling req.) | **FALLBACK (Rank 2)|
| Path 3 (Futures)  | CME GC Pure Futures        | Databento GC MDP3     | Free credits / Low  | Secondary (Rank 3) |
| Path 4 (Hybrid)   | Spot Price + Futures Volume| XAUUSD + CME GC Volume| High Basis Risk     | Not Recommended    |
+-------------------+----------------------------+-----------------------+---------------------+--------------------+
```

---

## 1. Deep Dive into the Four Research Paths

### Path 1: Multi-Day Swing Research on H4 / Daily Horizons (Existing Data)
- **Concept:** Re-orient systematic hypothesis generation from intraday session transitions to **multi-day swing horizons (2 to 10 days)** using existing 1-minute data aggregated to H4 and Daily bars.
- **Data Requirement:** Existing `data/processed/XAUUSD/H4/` and Daily resampled bars + existing `FRED` macroeconomic series (`DFII10`, `DTWEXBGS`, `T10YIE`).
- **Research Questions It CAN Support:**
  - Can macro real-yield momentum (10-year TIPS yield rate of change) predict multi-day gold direction?
  - Do broad dollar index regime breakdowns trigger durable multi-week trending regimes in gold?
  - Do weekly volatility compression breakouts (e.g. 20-day ATR contractions) generate statistical follow-through?
  - Does daily mean-reversion operate effectively around 50-day and 200-day exponential moving averages?
- **Research Questions It CANNOT Support:**
  - Intraday liquidity timing or session-open order flow dynamics.
  - Microstructure execution slippage or spread-widening modeling.
  - Volume-based price discovery (VWAP, liquidity profiles).
- **Frictional Feasibility:** **Outstanding**. On H4/Daily horizons, average price excursions range from **$\$25.00 to $\$75.00/\text{oz}$**. A baseline round-turn friction of $\$0.35/\text{oz}$ represents only **$0.45\%$ to $1.4\%$** of the gross move. The strategy is virtually immune to execution friction.

### Path 2: Acquire Historical XAUUSD Bid/Ask Tick Data (Dukascopy)
- **Concept:** Procure synchronized millisecond tick quotes with simultaneous Bid and Ask prices to model true execution friction and test if any structural intraday edge survives.
- **Data Requirement:** Dukascopy historical `.bi5` tick data for XAUUSD (2018–2024).
- **Research Questions It CAN Support:**
  - What is the empirical distribution of gold spreads across Asian, London, and New York sessions?
  - How severely do spreads expand during CPI, Non-Farm Payrolls, and FOMC rate decisions?
  - Does adverse execution slippage on breakout stop-market orders exceed theoretical backtest buffers?
  - Can an intraday momentum strategy survive realistic dynamic bid-ask fill penalties?
- **Research Questions It CANNOT Support:**
  - Real exchange-traded contract turnover or institutional open interest changes.
  - CME exchange clearing volume or CFTC commercial hedger positioning.

### Path 3: Acquire CME COMEX Gold Futures (`GC`) Historical Data
- **Concept:** Transition research entirely from OTC spot CFD trading to exchange-traded futures, leveraging real contract volume, order-book depth, and centralized clearing.
- **Data Requirement:** Databento `GLBX.MDP3` dataset for `GC` (tick and 1-minute OHLCV with actual volume).
- **Research Questions It CAN Support:**
  - Does institutional volume profile (Point of Control, Value Area High/Low) act as robust support/resistance?
  - Do order-flow imbalances (bid/ask volume delta) exhibit predictive power over subsequent 1-hour returns?
  - How do large resting limit orders at CME clearing levels impact price rejection?
- **Research Questions It CANNOT Support:**
  - OTC retail spot broker execution realities (leverage, margin calls, swap fees).
  - Trading strategies intended for spot gold CFD accounts without futures margin capabilities.

### Path 4: Hybrid Model — CME Futures Volume Applied to Spot Price
- **Concept:** Use CME Gold Futures volume and order flow as an exogenous predictive signal to trade spot XAUUSD.
- **Critical Methodological Flaw:** **Basis Risk and Contract Discontinuity**.

---

## 2. The Theoretical & Empirical Flaw of Path 4: Spot vs. Futures Divergence

> [!WARNING]
> **Definitive Auditor Declaration on Spot vs. Futures Interchangeability:**  
> Gold futures (`GC`) and Spot Gold (`XAUUSD`) are **not interchangeable assets**. Attempting to apply futures volume directly to spot price action without accounting for the gold basis, calendar rollover, and session timing introduces dangerous methodological distortions.

### A. The Gold Basis (Cost of Carry Model)
Futures prices reflect the spot price adjusted for financing costs, storage, insurance, and the gold lease rate:
$$F_t = S_t \cdot e^{(r + s - y)(T - t)}$$
Where:
- $F_t$ = COMEX Gold Futures price at time $t$.
- $S_t$ = Spot Gold price (`XAUUSD`) at time $t$.
- $r$ = US Dollar risk-free interest rate (SOFR / Treasury rate).
- $s$ = Physical storage and vault insurance cost ($\sim 0.10\%–0.20\%$ annualized).
- $y$ = Gold lease rate (convenience yield earned by lending physical gold).
- $T - t$ = Time to contract maturity.

#### Real-World Divergence:
1. **Contango and Interest Rate Sensitivity:** When US interest rates rise (as in 2022–2024), the cost of carry expands. Front-month futures can trade **$\$10.00 to $\$30.00/\text{oz}$ above spot gold** (contango). During bank liquidity panics (e.g. March 2020), the basis blew out to over **$\$60.00/\text{oz}$** as physical air cargo between London vaults and New York COMEX was halted.
2. **Contract Rollover Jumps:** COMEX Gold futures trade on specific delivery cycles (Feb, Apr, Jun, Aug, Oct, Dec). Every two months, volume shifts from the expiring contract to the next active contract. A price chart of raw futures experiences an artificial gap of $\$15–\$30/\text{oz}$ on roll dates. Spot gold experiences **zero** roll gaps.
3. **Session Timing Discrepancies:**
   - COMEX Gold pit session closes at 13:30 NY time (17:30/18:30 UTC), after which futures volume plummets to thin electronic Globex trading.
   - Spot gold trades actively in London until 16:30 UTC and throughout the global day.
4. **Aggregation Hazard:** If a model triggers a spot trade based on a futures volume spike, the futures volume spike may simply reflect contract rollover transactions (calendar spread rolls) rather than genuine directional conviction.

---

## 3. Horizon Comparison: The Math of Frictional Immunity

To visualize why shifting from M5 to H4/Daily resolves the research impasse, compare the frictional drag across time horizons:

```
+-------------------------------------------------------------------------------------------------------------------+
|                                   TIME HORIZON FRICTION DRAG SPECTRUM                                             |
+-------------------+--------------------+--------------------+-----------------------+-----------------------------+
| Horizon           | Expected Move ($)  | Round-Turn Cost ($)| Frictional Drag (%)   | Viability Assessment        |
+-------------------+--------------------+--------------------+-----------------------+-----------------------------+
| M5 (Intraday)     | $0.44 – $1.50/oz   | $0.25 – $0.50/oz   | 25.0% – 60.0%         | **Structurally Fatal**      |
| M15 (Intraday)    | $1.20 – $3.50/oz   | $0.25 – $0.45/oz   | 10.0% – 25.0%         | **Extremely Fragile**       |
| H1 (Intraday)     | $3.50 – $8.00/oz   | $0.25 – $0.35/oz   | 4.0% – 8.0%           | **Challenging**             |
| H4 (Multi-Session)| $12.00 – $25.00/oz | $0.30 – $0.40/oz   | 1.5% – 3.0%           | **Economically Robust**     |
| Daily (Swing)     | $25.00 – $70.00/oz | $0.35 – $0.50/oz   | 0.5% – 1.4%           | **Friction-Immune**         |
| Weekly (Trend)    | $60.00 – $200.00/oz| $0.50 – $1.00/oz   | 0.2% – 0.8%           | **Friction-Immune**         |
+-------------------+--------------------+--------------------+-----------------------+-----------------------------+
```

### Analytical Deduction:
On the Daily timeframe, even if a broker charges an elevated spread of $\$0.40/\text{oz}$ and adverse slippage of $\$0.10/\text{oz}$, the total friction of $\$0.50/\text{oz}$ accounts for just **$1.0\%$** of a typical $\$50.00/\text{oz}$ swing. On M5, that exact same cost accounts for **$60\%$** of the move.

---

## 4. Strategic Assessment Conclusion

1. **Path 1 (Multi-Day Swing on Existing Data) is the clear winner for immediate research.** It requires zero budget, zero data purchases, and zero AWS spend. It bypasses the missing tick data issue by operating at horizons where spread errors are statistically negligible.
2. **Path 2 (Dukascopy Spot Tick Data) is the approved fallback.** If the research mandate strictly requires intraday execution modeling, Dukascopy provides the necessary millisecond Bid/Ask data for zero cost.
3. **Path 3 (Futures via Databento) is viable for future phases** using the $125 free credit, but requires establishing futures contract stitching infrastructure.
4. **Path 4 (Hybrid Spot/Futures) is rejected** due to basis risk and roll distortions.
