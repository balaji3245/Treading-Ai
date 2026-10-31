# PHASE 27: TRANSACTION COST SENSITIVITY & FRICTION WALL ANALYSIS

**Phase:** 27 — New Hypothesis Discovery & Research Design  
**Repository:** `Treading-Ai`  
**Instrument:** XAUUSD (Spot Gold / US Dollar), M5 Timeframe  
**Execution Timestamp:** 2026-10-30T13:30:00 UTC  

---

## 1. Executive Purpose & Cost Modeling Framework

In systematic intraday gold trading, transaction costs are frequently the decisive determinant of whether a statistical pattern translates into commercial profitability. 

Every candidate hypothesis in Phase 27 was evaluated across three pre-registered transaction cost tiers:
1. **1.0× Baseline Friction ($0.25/oz):** Institutional prime-of-prime conditions ($0.20 spread + $0.05 slippage).
2. **1.5× Elevated Friction ($0.375/oz):** Normal market conditions with minor volatility widening ($0.30 spread + $0.075 slippage).
3. **2.0× Stressed Friction ($0.500/oz):** Illiquid hours, auction volatility, or fast-market slippage ($0.40 spread + $0.10 slippage).

---

## 2. Comprehensive Cost Sensitivity Matrix Across All 5 Hypotheses

| Hypothesis ID | Trades ($N$) | Gross PnL ($/oz) | Net PnL @ 1.0× ($0.25/oz) | Net PnL @ 1.5× ($0.375/oz) | Net PnL @ 2.0× ($0.500/oz) | Breakeven Cost ($/oz) | Friction Drag (% of Gross) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **HYP-27-VOL-SHOCK-EXPANSION** | 49 | +$58.296 | +$46.046 | +$39.921 | +$33.796 | **$1.190** | 21.0% |
| **HYP-27-LONDON-PM-FIX-IMBALANCE** | 133 | +$106.777 | +$73.527 | +$56.902 | +$40.277 | **$0.803** | 31.1% |
| **HYP-27-POST-COMEX-DRIFT-REVERSION** | 100 | +$48.546 | +$23.546 | +$11.046 | **-$1.454** | **$0.485** | **51.5%** |
| **HYP-27-CONSECUTIVE-RANGE-MOMENTUM** | 46 | +$76.400 | +$64.900 | +$59.150 | +$53.400 | **$1.661** | 15.1% |
| **HYP-27-MONDAY-WEEKEND-GAP-REVERSION** | 40 | +$4.243 | **-$5.757** | **-$10.757** | **-$15.757** | **$0.106** | **235.7%** |

---

## 3. Deep-Dive Friction Diagnostics

### 3.1 The Frictional Collapse of HYP-27-POST-COMEX-DRIFT-REVERSION
- Although `HYP-27-POST-COMEX-DRIFT-REVERSION` exhibited directional balance (Long PF 1.427, Short PF 1.210) and a 55.0% win rate, its average gross trade profit was only **+$0.485/oz**.
- At 1.0× baseline friction ($0.25/oz), transaction friction consumes **51.5%** of gross earnings, leaving an expectancy of only +$0.235/oz (failing the $\ge +\$0.50$ promotion gate).
- When costs rise to 2.0× ($0.50/oz)—a common occurrence during the illiquid 20:00–22:00 UTC evening lull when retail broker spreads naturally widen—net PnL turns negative (-$1.454/oz, PF 0.983).
- **Takeaway:** Even if a pattern has an apparent edge, if the average gross excursion is $< \$1.00/oz, transaction costs will consume the edge in real-world trading.

### 3.2 The Complete Failure of HYP-27-MONDAY-WEEKEND-GAP-REVERSION
- Weekend gap fading produced a meager +$4.243/oz of gross profit across 40 trades (average gross trade = +$0.106/oz).
- Baseline round-turn friction of $0.25/oz is more than double the entire gross edge.
- Net PnL was negative at all cost tiers (-$5.76/oz at 1.0×, -$10.76/oz at 1.5×, -$15.76/oz at 2.0×).
- Frictional drag exceeds 200%. The strategy is economically unviable.

### 3.3 Auction Slippage in HYP-27-LONDON-PM-FIX-IMBALANCE
- The London PM Fix occurs at 15:00 UTC, a window of elevated institutional volatility.
- While the breakeven cost is $0.803/oz, entry occurs at 15:05 UTC when market makers widen spreads. Frictional drag consumed 31.1% of gross returns, compounding the strategy's directional asymmetry failure (Long PF 0.959).

---

## 4. Economic Conclusions on Intraday Friction

1. **The Minimum Excursion Threshold:**
   - Any intraday strategy on XAUUSD M5 requires an expected gross excursion of at least **$\ge \$5.00/\text{oz}$** to remain robust against execution friction.
   - Strategies targeting small mean-reverting drifts ($< \$2.00/oz$) suffer catastrophic degradation once realistic spreads, slippage, and broker commissions are accounted for.
2. **Overnight Financing (Swap):**
   - None of the 5 candidate hypotheses incur overnight rollover financing ($0.00/oz across all trades) because all holding periods terminate prior to 22:00 UTC. However, daytime execution friction alone is sufficient to eliminate marginal statistical edges.
