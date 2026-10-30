# EXECUTION COST ASSUMPTIONS & SENSITIVITY MODELING: PHASE 22

**Phase:** 22 — Controlled Development  
**Hypothesis ID:** `HYP-21-ASIAN-LONDON-EXPANSION`  
**Instrument:** XAUUSD (Spot Gold / US Dollar)  
**Status:** Methodological Specification & Stress Framework  

---

## 1. Baseline Cost Model Architecture

The execution-cost model for `HYP-21-ASIAN-LONDON-EXPANSION` applies fixed round-turn friction to every completed trade. The registered baseline cost is **$0.25 per troy ounce** ($0.25/oz), broken down into:

1. **Round-Turn Bid-Ask Spread:** **$0.20/oz** ($0.10 entry + $0.10 exit).
2. **Round-Turn Adverse Execution Slippage:** **$0.05/oz** ($0.025 entry + $0.025 exit).
3. **Overnight Financing (Swap):** **$0.00/oz** (verified below).

$$\text{Gross PnL}_i = (\text{Exit Price}_i - \text{Entry Price}_i) \times \text{Direction}_i$$
$$\text{Net PnL}_i = \text{Gross PnL}_i - C_{\text{round-turn}}$$

Where $\text{Direction}_i = +1$ for Long trades and $-1$ for Short trades.

---

## 2. Overnight Financing & Rollover Verification

In retail and institutional spot gold trading, overnight financing (swap or rollover fee) is assessed if an open position is held past the daily settlement time (typically 21:00 UTC during US Daylight Saving Time or 22:00 UTC during standard time). On Wednesdays, a triple-swap charge is levied to cover weekend settlement.

### Verification of Zero Swap Financing:
- **Earliest Trade Entry Time:** `07:05:00 UTC` (Open of bar following first breakout confirmation).
- **Latest Trade Exit Time:** `12:00:00 UTC` (Close of the `11:55` M5 bar).
- **Maximum Trade Holding Duration:** 4 hours 55 minutes (59 bars).
- **Position State at Daily Rollover (21:00/22:00 UTC):** Flat (100% of days).
- **Weekend Position State:** Flat (100% of weekends).

Because all positions are strictly opened after 07:00 UTC and closed at or before 12:00 UTC on the same calendar day, **zero overnight swap fees are incurred ($0.00/oz)** across all trades.

---

## 3. Cost Sensitivity Tiers

To assess the robustness of the strategy against deteriorating liquidity, market impact, and broker markups, performance is evaluated under three standardized cost tiers:

| Cost Tier | Multiplier | Round-Turn Spread ($/oz) | Round-Turn Slippage ($/oz) | Total Friction ($/oz) | Total Cost for 101 Trades ($/oz) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Tier 1: Baseline** | 1.0× | $0.200 | $0.050 | **$0.250** | $25.25 |
| **Tier 2: Elevated** | 1.5× | $0.300 | $0.075 | **$0.375** | $37.875 |
| **Tier 3: Stressed** | 2.0× | $0.400 | $0.100 | **$0.500** | $50.50 |

---

## 4. Gross vs. Net Returns: Critical Differentiation

> [!WARNING]
> **Assumed Costs vs. Verified Broker Execution:**  
> The figures $0.20/oz spread and $0.05/oz slippage are **assumed modeling proxies**, derived from published institutional ECN averages during liquid London trading hours. They are **NOT verified live broker execution costs**.

### Key Real-World Execution Risks Not Fully Captured by Fixed Proxies:
1. **London Open Volatility Spikes:** Between 07:00 and 08:00 UTC, institutional market participants enter the London interbank market. While gold liquidity expands, bid-ask spreads frequently widen temporarily (e.g., from $0.15 to $0.40/oz) during the exact first few minutes of breakout momentum.
2. **Fast-Market Slippage on Breakouts:** When momentum breaks through the Asian session boundary, stop-loss triggering and algorithmic momentum orders can create localized liquidity voids. In live conditions, slippage on entry may exceed $0.05/oz.
3. **Execution Model Mitigations Already Implemented:**
   - **Next-Bar Open Execution:** The strategy never enters on the breakout candle itself; it enters on the open of the subsequent M5 bar, avoiding intra-candle chasing.
   - **Adverse Stop Gap Slippage:** If a market gaps beyond the stop-loss level, the model fills at the bar Open, realizing full adverse slippage rather than capping losses at the stop boundary.
   - **Adverse Entry Gap Abort:** If the market opens beyond the stop level, the entry is aborted, preventing catastrophic fills.

---

## 5. Summary of Friction Impact on 2021–2022 Development

| Metric | Gross (0.0×) | Baseline (1.0×) | Elevated (1.5×) | Stressed (2.0×) |
| :--- | :--- | :--- | :--- | :--- |
| **Total PnL ($/oz)** | **+$67.688** | **+$42.438** | **+$29.813** | **+$17.188** |
| **Avg Expectancy / Trade ($/oz)** | +$0.670 | +$0.420 | +$0.295 | +$0.170 |
| **Profit Factor** | 1.420 | 1.263 | 1.178 | 1.099 |
| **Win Rate** | 56.44% | 54.46% | 53.47% | 50.50% |
| **Friction Drag (% of Gross)** | 0.00% | 37.30% | 55.95% | 74.61% |

Even under extreme 2.0× cost stress ($0.50/oz total round-turn), the strategy maintains a positive net return on development data (+$17.19/oz, PF 1.099). However, because friction consumes up to 74.6% of gross PnL under stress, execution quality is the paramount operational risk factor.
