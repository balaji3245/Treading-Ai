# Phase 31 Technical Audit: Overnight Swap Financing Engine

**Author:** Senior Quantitative Software Engineer & Trading Cost Model Auditor  
**Date:** 2026-10-31  
**Project:** Treading-Ai — XAUUSD Research System  
**Status:** IMPLEMENTED, TESTED & UNCALIBRATED (Assumptions Documented)  

---

## 1. Executive Summary

In Phase 30, the quantitative cost model audit demonstrated that while the existing transaction cost engine accurately modeled intraday execution friction (dynamic bid-ask spread, volatility slippage, and ECN commission), it possessed **no financing engine for multi-day holding periods**.

For swing trading horizons (holding periods spanning 1 to 10 trading sessions), overnight swap financing accumulates to between **$0.48 and $2.10 per troy ounce**, dwarfing fixed execution commissions ($0.10/oz round-turn). Backtesting multi-day strategies without explicit financing creates an artificial profitability illusion.

In Phase 31, we designed, implemented, and deterministically tested the `OvernightSwapEngine` within `src/treading_ai/backtesting/cost_model.py`. 

### Governance & Truthfulness Invariant:
> **CRITICAL DISCLOSURE:** The swap engine is **NOT CALIBRATED against verified broker market data**. Actual swap rates fluctuate daily based on interbank repo rates, gold leasing rates (GOFO), and broker Tom-Next funding schedules. Default rates in this engine are **explicit illustrative assumptions**. The engine flags `is_calibrated=False` on every output record until live broker specification files are provided and audited.

---

## 2. Institutional Financing & Rollover Mechanics

### 2.1 The Daily Settlement Boundary
In institutional spot foreign exchange and bullion trading, physical settlement occurs on a $T+2$ business day basis. A position held across the daily settlement cut-off time incurs an overnight rollover charge (or credit):
- **Rollover Boundary:** Exactly **17:00:00 New York local time** (`America/New_York`).
- **Dynamic UTC Transition:**
  - Summer (EDT): 21:00:00 UTC
  - Winter (EST): 22:00:00 UTC
- **Causality & Boundary Crossing Invariant:**
  - An order opened and closed within the same trading session (without crossing 17:00:00 NY) incurs **0 rollovers and $0.00 financing cost**.
  - Financing is charged strictly when the position holding interval satisfies:
    $$\text{entry\_ts} < \text{rollover\_ts} \le \text{exit\_ts}$$

### 2.2 Wednesday Triple Swap Convention ($3\times$)
Because spot gold trades settle $T+2$, a position rolled over on Wednesday at 17:00 NY extends its settlement date from Friday to Monday. This bridges the two weekend days (Saturday and Sunday) when financial markets are closed:
- **Wednesday Rollover:** Incurs **3 days of interest** ($3.0\times$ daily swap rate).
- **Monday, Tuesday, Thursday, Friday Rollovers:** Incur **1 day of interest** ($1.0\times$ daily swap rate).
- **Seven-Day Calendar Hold:** A position opened Monday 10:00 NY and closed the following Monday 10:00 NY crosses 5 business-day rollovers:
  $$\text{Weighted Days} = 1.0 (\text{Mon}) + 1.0 (\text{Tue}) + 3.0 (\text{Wed}) + 1.0 (\text{Thu}) + 1.0 (\text{Fri}) = 7.0 \text{ calendar days}$$
  This matches the physical reality of financing a leveraged position across 7 elapsed calendar days.

---

## 3. Architecture & Multi-Unit Support

The `OvernightSwapEngine` supports four standard broker quoting conventions, automatically converting all quotes to the standardized project accounting unit: **USD per troy ounce per day ($\$/\text{oz}/\text{day}$)**.

### 3.1 Supported Unit Conversions

| Broker Unit Specification | `rate_unit` Identifier | Conversion Formula to USD/oz/day | Illustrative Long Rate Example | Converted Rate |
| :--- | :--- | :--- | :--- | :--- |
| **USD per Troy Ounce per Day** | `"usd_per_oz_day"` | $\text{Rate}$ | $-0.12$ | $-\$0.120/\text{oz}/\text{day}$ |
| **Broker Points per Day** | `"points_per_day"` | $\text{Rate} \times \text{PointValue}$ ($\$0.01/\text{pt}$) | $-12.0\text{ pts}$ | $-\$0.120/\text{oz}/\text{day}$ |
| **USD per Standard Lot per Day** | `"usd_per_lot_day"` | $\text{Rate} / \text{ContractSize}$ ($100\text{ oz}$) | $-\$12.00/\text{lot}$ | $-\$0.120/\text{oz}/\text{day}$ |
| **Annual Percentage Rate** | `"annual_percentage"` | $\frac{\text{SpotPrice} \times (\text{Rate} / 100)}{360}$ | $-2.50\%\text{ p.a.}$ (@ $\$1,800/\text{oz}$) | $-\$0.125/\text{oz}/\text{day}$ |

### 3.2 Accounting Sign Conventions & Friction Drag
To eliminate ambiguity in performance reporting:
1. **Swap PnL (`swap_pnl_per_oz`):**
   - Signed metric.
   - Negative value indicates a debit (cash outflow dragging PnL).
   - Positive value indicates a credit (interest received).
2. **Swap Drag (`swap_drag_per_oz`):**
   - Non-negative friction metric.
   - $\text{swap\_drag\_per\_oz} = \max(0.0, -\text{swap\_pnl\_per\_oz})$.
   - Represents the hurdle rate in $\$ /\text{oz}$ that the trade's gross price excursion must overcome before breaking even.
3. **Total Position USD:**
   $$\text{Total Swap USD} = \text{Swap Drag per oz} \times \text{Position Size in Troy Ounces}$$
   Where 1 standard lot = $100.0\text{ oz}$, 1 mini lot = $10.0\text{ oz}$, and 1 micro lot = $1.0\text{ oz}$.

---

## 4. End-to-End Accounting Integration

The swap engine was integrated into `ExecutionCostModel.calculate_round_turn_cost` to provide unified, itemized accounting with **zero double-counting**:

```python
rt = cost_model.calculate_round_turn_cost(entry_exec, exit_exec, position_size_oz=100.0)
```

### Itemized Round-Turn Accounting Breakdown
For a 1 standard lot (100 oz) Long trade entered Monday 14:00 UTC and exited Friday 14:00 UTC across 4 rollovers (Mon 1x, Tue 1x, Wed 3x, Thu 1x = 6.0 weighted days):

```
+-----------------------------------------------------------------------------------+
| Component                | Unit Rate / Oz       | 100 oz Lot USD Impact | Note    |
+--------------------------+----------------------+-----------------------+---------+
| Entry Effective Spread   | $0.200 / oz          | $20.00                | BUY leg |
| Entry Slippage           | $0.050 / oz          | $5.00                 | Base    |
| Entry Commission         | $0.050 / oz          | $5.00                 | $5/lot  |
| Exit Effective Spread    | $0.000 / oz          | $0.00                 | SELL leg|
| Exit Slippage            | $0.050 / oz          | $5.00                 | Base    |
| Exit Commission          | $0.050 / oz          | $5.00                 | $5/lot  |
| Overnight Swap Financing | $0.720 / oz          | $72.00                | 6 days  |
+--------------------------+----------------------+-----------------------+---------+
| Total Round-Turn Friction| $1.120 / oz          | $112.00               | Net Drag|
+--------------------------+----------------------+-----------------------+---------+
```

**Observation:** Swap financing ($0.72/oz) represents **64.3% of the total transaction friction** on a 4-day swing trade, while execution commission ($0.10/oz) accounts for only 8.9%. Modeling swap is mandatory for institutional swing trading validity.

---

## 5. Broker Financing Sensitivity Matrix

Because true broker rates are unverified, we evaluated multi-day holding friction across three representative institutional broker tiers:

| Holding Horizon | Rollovers Crossed | Weighted Days | Tier 1: Prime ECN (-$0.08/oz/day) | Tier 2: Base Assumption (-$0.12/oz/day) | Tier 3: Stressed Retail (-$0.18/oz/day) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Intraday (M5/H1)** | 0 | 0.0 | **$0.00 / oz** | **$0.00 / oz** | **$0.00 / oz** |
| **Overnight (1-Day Tue)** | 1 | 1.0 | **$0.08 / oz** | **$0.12 / oz** | **$0.18 / oz** |
| **Overnight (1-Day Wed 3x)** | 1 | 3.0 | **$0.24 / oz** | **$0.36 / oz** | **$0.54 / oz** |
| **2-Day Swing (Tue–Thu)** | 2 | 4.0 | **$0.32 / oz** | **$0.48 / oz** | **$0.72 / oz** |
| **4-Day Swing (Mon–Fri)** | 4 | 6.0 | **$0.48 / oz** | **$0.72 / oz** | **$1.08 / oz** |
| **7-Day Swing (Mon–Mon)** | 5 | 7.0 | **$0.56 / oz** | **$0.84 / oz** | **$1.26 / oz** |
| **14-Day Macro Swing** | 10 | 14.0 | **$1.12 / oz** | **$1.68 / oz** | **$2.52 / oz** |

---

## 6. Unit Test Verification & Audit Sign-Off

The swap financing engine was validated via 6 deterministic unit tests in `tests/test_phase31_infrastructure.py`:
1. `test_intraday_trade_zero_swap`: Verifies $0.00 swap on intraday holds.
2. `test_single_rollover_crossing`: Verifies 1.0 weighted days on Tuesday crossing.
3. `test_wednesday_triple_swap`: Verifies 3.0 weighted days on Wednesday crossing.
4. `test_multi_day_holding_period`: Verifies 6.0 weighted days on Monday-to-Friday hold.
5. `test_one_week_holding_period`: Verifies 7.0 weighted days on Monday-to-Monday hold.
6. `test_unit_conversions`: Verifies mathematical parity between points, lot USD, annual %, and $/oz.

**Remaining Blocker:** Real broker swap quote data files remain unacquired. Until broker specifications are obtained, all backtest experiments must explicitly state that swap rates are configured assumptions.
