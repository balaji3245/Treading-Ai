# Phase 32 Audit Report: Overnight Swap Financing & Financial Accounting Verification

**Auditor:** Senior Quantitative Software Engineer, Financial Data Engineer, and Trading Cost Model Auditor  
**Date:** 2026-11-01  
**Project:** Treading-Ai — XAUUSD Research-Only System  
**Audit Scope:** Track C — Overnight Swap Financing Engine & Round-Turn Cost Integration  
**Target Code:** `src/treading_ai/backtesting/cost_model.py:OvernightSwapEngine`, `ExecutionCostModel.calculate_round_turn_cost`  

---

## 1. Executive Summary & Audit Verdict

This audit independently reviewed the Phase 31 `OvernightSwapEngine` and its integration with the institutional transaction cost model.

### Verdict Summary:
- **Rollover Boundary Accounting:** **PASS (Strict Pre-Trade Causality)**. Boundary crossing logic follows `entry_ts < roll_ts <= exit_ts` at 17:00:00 New York Time (`America/New_York`). All boundary edge cases (entry at cut, exit at cut, intraday trades, Wednesday 3x, multi-day holds) passed independent unit verification.
- **Unit Conversions & Contract Sizing:** **PASS (Exact Mathematical Parity)**. Verified exact conversions across `usd_per_oz_day`, `points_per_day`, `usd_per_lot_day`, and `annual_percentage` based on the institutional spot gold standard of 100 troy ounces per lot.
- **Accounting & Cost Integration:** **PASS (Zero Double-Counting Verified)**. Long and Short round-turn executions symmetrically incur exactly 1 spread charge, 2 slippage charges, 2 commission charges, and exactly 1 holding period financing drag.
- **Calibration Governance:** **PASS (Strict Assumption Preservation)**. The engine strictly outputs `is_calibrated=False` on all output records. Default rates (-$0.12/oz Long, -$0.04/oz Short) remain explicitly identified as illustrative assumptions.
- **Broker-Specific Limitations Identified:** The engine assumes a static weekly schedule (`triple_swap_day=2`). It does not dynamically model bank-holiday calendar roll shifts (e.g., Easter/Christmas shifting triple swap to Monday/Tuesday), nor does it support non-standard weekend CFD interest accruals.

---

## 2. Track C1: Rollover Boundary & Schedule Verification

### 2.1 Rollover Boundary Condition
Financing charges are incurred only when a holding period spans the 17:00:00 New York Time settlement cut:
$$\text{Boundary Crossing Condition:} \quad \text{entry\_ts} < \text{rollover\_ts} \le \text{exit\_ts}$$

In `OvernightSwapEngine.get_rollover_crossings`:
```python
roll_ny = datetime.combine(cur_date, time(self.rollover_hour_ny, self.rollover_minute_ny), tzinfo=TZ_NEW_YORK)
roll_utc = roll_ny.astimezone(timezone.utc)
if t_entry < roll_utc <= t_exit:
    mult = 3.0 if cur_date.weekday() == self.triple_swap_day else 1.0
    crossings.append({"timestamp_utc": roll_utc, "multiplier": mult})
```

### 2.2 Independent Edge-Case Testing

| Scenario | Entry Timestamp (UTC) | Exit Timestamp (UTC) | Rollovers Counted | Weighted Days | Audit Verification Finding |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Intraday Trade** | 2021-06-15 13:00 (09:00 NY) | 2021-06-15 19:00 (15:00 NY) | **0** | **0.0** | **PASS:** Closed before 17:00 NY cut; $0.00 swap charged. |
| **Both Before Cut** | 2021-06-15 20:50 (16:50 NY) | 2021-06-15 20:59 (16:59 NY) | **0** | **0.0** | **PASS:** Exited prior to settlement cut. |
| **Entry Exactly At Cut**| 2021-06-15 21:00 (17:00 NY) | 2021-06-15 22:00 (18:00 NY) | **0** | **0.0** | **PASS:** Filled for new session; does not pay prior roll. |
| **Exit Exactly At Cut** | 2021-06-15 20:00 (16:00 NY) | 2021-06-15 21:00 (17:00 NY) | **1** | **1.0** | **PASS:** Held into the cut; incurs Tuesday financing. |
| **Tuesday Overnight** | 2021-06-15 20:50 (16:50 NY) | 2021-06-15 22:10 (18:10 NY) | **1** | **1.0** | **PASS:** Exactly 1 rollover; multiplier = 1.0. |
| **Wednesday Triple Roll**| 2021-06-16 20:50 (16:50 NY) | 2021-06-16 22:10 (18:10 NY) | **1** | **3.0** | **PASS:** Crossed Wednesday cut; multiplier = 3.0. |
| **4-Day Swing (Mon–Fri)**| 2021-06-14 14:00 (10:00 NY) | 2021-06-18 14:00 (10:00 NY) | **4** | **6.0** | **PASS:** Mon(1) + Tue(1) + Wed(3) + Thu(1) = 6.0 days. |
| **7-Day Swing (Mon–Mon)**| 2021-06-14 14:00 (10:00 NY) | 2021-06-21 14:00 (10:00 NY) | **5** | **7.0** | **PASS:** Mon(1) + Tue(1) + Wed(3) + Thu(1) + Fri(1) = 7.0 days. |
| **Friday–Monday Hold** | 2021-06-18 20:50 (16:50 NY) | 2021-06-21 14:00 (10:00 NY) | **1** | **1.0** | **PASS:** Crossed Friday cut (settles Tuesday $\to$ Wednesday = 1 day). |

### 2.3 Identification of Unsupported Broker-Specific Conventions
1. **Bank Holiday Triple Swap Rescheduling:**
   - In interbank spot FX, if Friday is a bank holiday (e.g. Good Friday), Wednesday's roll settles Thursday $\to$ Monday, and Tuesday becomes a 2-day roll.
   - The current engine uses a static `triple_swap_day` parameter without a dynamic interbank holiday calendar.
2. **Friday 3x Convention (Retail CFDs):**
   - Certain retail brokers charge triple swap on Friday rather than Wednesday. This is supported via configuration (`triple_swap_day=4`), but must be set manually per broker profile.
3. **Daily Calendar Accruals:**
   - Some cryptocurrency or unregulated CFD brokers charge financing 7 days a week (including Saturday and Sunday) rather than using the $T+2$ Wednesday triple swap convention. The engine does not support 7-day accruals.

---

## 3. Track C2: Unit Conversion & Numerical Precision

We tested mathematical parity across the four supported quoting conventions for a $1,800.00/oz spot gold price:

### 3.1 Unit Parity Proofs

$$\begin{aligned}
\text{Rate Unit} & \quad \text{Quoted Rate} & \quad \text{Conversion Formula} & \quad \text{Resulting Rate (\$/oz/day)} \\
\hline
\text{USD per Oz Day} & -0.12000 & \text{Rate} & -\$0.12000 / \text{oz} \\
\text{Broker Points} & -12.00000\text{ pts} & \text{Rate} \times \$0.01 & -\$0.12000 / \text{oz} \\
\text{USD per Lot Day} & -\$12.00000 & \text{Rate} / 100.0\text{ oz} & -\$0.12000 / \text{oz} \\
\text{Annual Percentage} & -2.40000\%\text{ p.a.} & \frac{\$1,800 \times (-0.024)}{360} & -\$0.12000 / \text{oz}
\end{aligned}$$

### 3.2 Error Handling & Input Validation
- **Invalid Rate Unit:** Raises `ValueError: Invalid rate_unit '...'`.
- **Missing Spot Price for Annual %:** Raises `ValueError: spot_price must be a positive float when rate_unit='annual_percentage'`.
- **Zero / Negative Spot Price:** Correctly rejected with `ValueError`.
- **Invalid Direction:** Raises `ValueError: Invalid direction '...'`.
- **Reversed Timestamps (`exit_ts <= entry_ts`):** Returns safe empty record with `rollover_count = 0` and `total_swap_drag_usd = 0.0`.
- **Credit Sign Convention:** Tested with `swap_rate_long = +0.05 $/oz/day`. Result: `swap_pnl_per_oz = +0.05`, `total_swap_pnl_usd = +$5.00` (for 100 oz), and `swap_drag_per_oz = 0.0` (positive drag correctly capped at zero).

---

## 4. Track C3: Cost Integration & Zero Double-Counting

We audited the round-turn cost calculation in `ExecutionCostModel.calculate_round_turn_cost`:

### 4.1 Structural Long vs Short Execution Accounting

```
Long Round-Turn (Buy Entry @ Ask, Sell Exit @ Bid):
  Entry:  Bid + Spread ($0.20) + Slippage ($0.05) + Commission ($0.05) = Friction $0.30/oz
  Exit:   Bid - Slippage ($0.05) + Commission ($0.05)                  = Friction $0.10/oz
  Swap:   4 rollovers (Mon, Tue, Wed 3x, Thu) = 6.0 weighted days @ $0.12/oz = Drag $0.72/oz
  Total Round-Turn Friction: $0.30 + $0.10 + $0.72 = $1.12000 / oz ($112.00 per 100 oz lot)

Short Round-Turn (Sell Entry @ Bid, Buy Exit @ Ask):
  Entry:  Bid - Slippage ($0.05) + Commission ($0.05)                  = Friction $0.10/oz
  Exit:   Bid + Spread ($0.20) + Slippage ($0.05) + Commission ($0.05) = Friction $0.30/oz
  Swap:   4 rollovers = 6.0 weighted days @ $0.04/oz                          = Drag $0.24/oz
  Total Round-Turn Friction: $0.10 + $0.30 + $0.24 = $0.64000 / oz ($64.00 per 100 oz lot)
```

**Verification:** 
- Exactly 1 spread charge paid per round turn (on the Buy leg).
- Exactly 2 slippage charges paid per round turn (entry and exit).
- Exactly 2 commission charges paid per round turn ($0.05/oz per leg = $0.10/oz total).
- Exactly 1 swap financing drag accrued across the elapsed holding window.
- Zero double-counting detected.

---

## 5. Track C4: Calibration Status & Sensitivity Matrix

### 5.1 Verification of Uncalibrated Status
The engine strictly preserves the truthfulness invariant:
- Every `SwapFinancingRecord` object has `is_calibrated = False`.
- In all documentation and code comments, the default rates are explicitly labeled as **illustrative assumptions**.

### 5.2 Scenario Matrix Evaluation
The Phase 31 report proposed three sensitivity tiers. We independently confirmed that these tiers represent plausible market scenarios rather than observed broker quotes:

| Horizon | Tier 1: Prime ECN (-$0.08/oz/day) | Tier 2: Base Assumption (-$0.12/oz/day) | Tier 3: Stressed Retail (-$0.18/oz/day) | Hurdle Rate Drag on 100 oz Lot |
| :--- | :--- | :--- | :--- | :--- |
| **Intraday** | $0.00 / oz | $0.00 / oz | $0.00 / oz | $0.00 |
| **1-Day Overnight** | $0.08 / oz | $0.12 / oz | $0.18 / oz | $8.00 – $18.00 |
| **3-Day Wed Hold** | $0.24 / oz | $0.36 / oz | $0.54 / oz | $24.00 – $54.00 |
| **5-Day Full Week** | $0.56 / oz | $0.84 / oz | $1.26 / oz | $56.00 – $126.00 |
| **10-Day Swing** | $1.12 / oz | $1.68 / oz | $2.52 / oz | $112.00 – $252.00 |

**Advisory Rule:** Any future swing strategy backtest must pass profitability hurdles under **Tier 3 (Stressed Retail)** before being considered viable for production feasibility.

---

## 6. Audit Findings & Corrective Action Matrix

| Finding ID | Severity | File / Function | Description | Impact | Recommended Corrective Action |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **C-01** | Medium | `cost_model.py:OvernightSwapEngine` | Does not dynamically reschedule Wednesday triple swap for public holidays (e.g. Good Friday, Christmas). | Minor variance in swap accrual during holiday weeks ($\pm 1$ day timing shift). | Document as an unmodeled institutional holiday feature; implement holiday calendar roll table in Phase 33+. |
| **C-02** | Low | `tests/test_phase31_infrastructure.py` | `test_calculate_round_turn_cost_integration` tested only Long trades; Short round-turn was unasserted in test suite. | No test coverage regression for Short round turns in CI. | Add explicit Short round-turn test to unit test suite. |

**Track C Final Decision:** **PASS** (Rollover crossing logic, unit conversions, and cost integration are mathematically sound; advisory limitations documented).
