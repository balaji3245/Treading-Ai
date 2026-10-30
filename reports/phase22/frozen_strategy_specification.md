# FROZEN STRATEGY SPECIFICATION: HYP-21-ASIAN-LONDON-EXPANSION

**Document Version:** 1.0.0 (FROZEN)  
**Hypothesis ID:** `HYP-21-ASIAN-LONDON-EXPANSION`  
**Phase:** 22 — Controlled Development  
**Status:** FROZEN PRIOR TO BACKTEST EXECUTION  
**Development Partition:** 2021-01-01 to 2022-12-31 UTC  

---

## 1. Executive Summary & Philosophy

This document formally and unambiguously freezes the trading rules, timing definitions, order-of-operations, boundary mechanics, and execution parameters for hypothesis `HYP-21-ASIAN-LONDON-EXPANSION`. 

All parameters documented herein were locked prior to computing backtest performance on the 2021–2022 development partition. No post-hoc tuning, optimization loops, or parameter adjustments were permitted.

The economic intuition of the strategy is that during the Asian trading session (00:00 to 07:00 UTC), physical gold liquidity and macroeconomic volatility in London and New York are largely dormant. When the Asian trading range contracts relative to trailing daily volatility (volatility compression), institutional order flow entering at the London market open (07:00–08:00 UTC) precipitates directional expansion. The strategy enters on confirmed directional range expansion and exits systematically at 12:00 UTC, capturing the morning London expansion impulse while avoiding overnight financing and New York session reversals.

---

## 2. Session Definitions & Clock Specifications

All times are defined strictly in **Coordinated Universal Time (UTC)**, completely independent of local Daylight Saving Time (DST) shifts in London, New York, or Tokyo.

| Session Segment | UTC Time Window | M5 Bar Timestamps Included | Bar Count | Description |
| :--- | :--- | :--- | :--- | :--- |
| **Asian Session** | 00:00:00 to 07:00:00 UTC | `00:00`, `00:05`, ..., `06:55` | 84 bars | Session defining High and Low boundaries. |
| **Breakout Monitoring** | 07:05:00 to 09:00:00 UTC | `07:00`, `07:05`, ..., `08:55` | 24 bars | Completed M5 bars evaluated for boundary breakout. |
| **Scheduled Exit** | 12:00:00 UTC Close | `11:55` bar (closes at 12:00:00) | 1 bar | Time-based flat exit for all open positions. |

> [!NOTE]
> M5 bar timestamps represent the **bar open time**. For example, the `06:55` bar opens at `06:55:00` and closes at `07:00:00` UTC. The `11:55` bar opens at `11:55:00` and closes at `12:00:00` UTC.

---

## 3. Mathematical Formulae & Parameter Definitions

### 3.1 Asian Session Range
The Asian session range is defined strictly from completed M5 bars between 00:00:00 and 07:00:00 UTC:
$$\text{Asia High}_t = \max_{i \in \text{Asia}_t} (\text{High}_{t, i})$$
$$\text{Asia Low}_t = \min_{i \in \text{Asia}_t} (\text{Low}_{t, i})$$
$$\text{Asia Range}_t = \text{Asia High}_t - \text{Asia Low}_t$$

### 3.2 Prior Daily Volatility ($\text{ATR}_{20}$)
To avoid any look-ahead leakage from current-day price action, daily true range is computed on calendar daily bars ($N \ge 100$ M5 bars, filtering out short partial weekend sessions), and trailing 20-day ATR is shifted by 1 full day:
$$\text{TR}_d = \max\Big(\text{High}_d - \text{Low}_d, |\text{High}_d - \text{Close}_{d-1}|, |\text{Low}_d - \text{Close}_{d-1}|\Big)$$
$$\text{ATR}_{20, t}^{\text{prior}} = \frac{1}{20} \sum_{k=1}^{20} \text{TR}_{t-k}$$

### 3.3 Compression Ratio & Frozen Threshold
The compression ratio ($CR_t$) measures Asian session contraction relative to trailing daily volatility:
$$CR_t = \frac{\text{Asia Range}_t}{\text{ATR}_{20, t}^{\text{prior}}}$$

- **Calibration Source:** First quartile ($Q_1$) of $CR_t$ calculated across all valid development days in 2021–2022 ($N = 495$ calendar days).
- **Frozen Threshold Value:**
  $$\tau_{\text{compression}} = 0.281865$$
- **Eligibility Condition:** A calendar day is eligible for breakout monitoring if and only if:
  $$CR_t \le 0.281865$$

---

## 4. Execution Logic & Deterministic Order of Operations

### 4.1 Breakout Detection
On eligible compressed days, the engine monitors completed M5 bars whose close occurs strictly between 07:05:00 and 09:00:00 UTC (timestamps `07:00` through `08:55`):
- **Long Breakout Trigger:** $\text{Close}_{t, i} > \text{Asia High}_t$
- **Short Breakout Trigger:** $\text{Close}_{t, i} < \text{Asia Low}_t$

### 4.2 Anomaly & Tie-Breaking Rules
1. **Whipsaw Anomaly Candle:** If an M5 bar exhibits extreme spread/volatility such that $\text{Close}_{t, i} > \text{Asia High}_t$ and $\text{Close}_{t, i} < \text{Asia Low}_t$ (impossible under standard prices, but evaluated for data safety) or if High/Low breach both boundaries on the trigger bar, the trigger is deemed invalid.
2. **First-Come-First-Served Priority:** The first completed M5 bar in the monitoring window that satisfies the breakout condition triggers the signal. Any subsequent breakout in the opposite direction later in the window is discarded.
3. **One Trade Per Day:** A maximum of exactly 1 trade is permitted per calendar day. Once a trade is triggered, no further orders are accepted on that calendar day.
4. **No Breakout:** If all 24 M5 bars in the monitoring window complete without a close beyond the Asian boundary, no trade is executed on that day.

### 4.3 Trade Entry
- **Timing:** Open of the M5 bar immediately following the trigger bar:
  $$t_{\text{entry}} = t_{\text{trigger}} + 5\text{ minutes}$$
- **Execution Price:** $\text{Open}_{t_{\text{entry}}}$
- **Entry Adverse Gap Rule:** If market gaps adversely across the opposite boundary such that:
  - For Long: $\text{Open}_{t_{\text{entry}}} \le \text{Stop Price}$
  - For Short: $\text{Open}_{t_{\text{entry}}} \ge \text{Stop Price}$
  The trade is **aborted immediately with zero fill** (no trade entered).

---

## 5. Mandatory Stop-Loss & Exit Clarifications

### 5.1 Stop-Loss Placement
The initial stop-loss is placed strictly at the **opposite Asian boundary**:
- **Long Position:** $\text{Stop Price} = \text{Asia Low}_t$
- **Short Position:** $\text{Stop Price} = \text{Asia High}_t$

### 5.2 Intrabar Order of Operations
On every held M5 bar $j \in [t_{\text{entry}}, t_{\text{exit}}]$, evaluation occurs in the following deterministic sequence:

```mermaid
flowchart TD
    A[Start Bar Evaluation] --> B{Bar Open Gaps Past Stop?}
    B -- Yes --> C[Execute Stop at Bar Open (Adverse Slippage)]
    B -- No --> D{Intrabar High/Low Breaches Stop?}
    D -- Yes --> E[Execute Stop at Stop Price]
    D -- No --> F{Is Bar Timestamp 11:55 UTC?}
    F -- Yes --> G[Execute Scheduled Exit at Bar Close 12:00 UTC]
    F -- No --> H[Hold Position to Next Bar]
```

1. **Step 1 (Open Gap Check):** Check if bar opens beyond the stop level:
   - Long: $\text{Open}_j \le \text{Stop Price} \implies \text{Exit Price} = \text{Open}_j$ (full gap slippage realized).
   - Short: $\text{Open}_j \ge \text{Stop Price} \implies \text{Exit Price} = \text{Open}_j$ (full gap slippage realized).
2. **Step 2 (Intrabar Stop Penetration):** If Open did not breach stop, check if intrabar price reaches the stop:
   - Long: $\text{Low}_j \le \text{Stop Price} \implies \text{Exit Price} = \text{Stop Price}$.
   - Short: $\text{High}_j \ge \text{Stop Price} \implies \text{Exit Price} = \text{Stop Price}$.
3. **Step 3 (Time Exit):** If the stop was not hit during Steps 1 or 2, and the bar timestamp is `11:55` UTC, the position is closed at $\text{Close}_j$ (representing 12:00:00 UTC).

> [!IMPORTANT]
> **Same-Bar Conflict Resolution:** If both the stop-loss condition and the scheduled 12:00 UTC exit occur within the same bar, the stop-loss is evaluated **first**. The stop-loss takes absolute precedence over the time exit.

### 5.3 Missing Bars & Session Interruption
If data provider drops bars or the session ends abruptly prior to `11:55` UTC, the position is liquidated at the final available bar's `close` price, labeled as `LAST_AVAILABLE_BAR_EXIT`.

---

## 6. Execution Cost Model

Execution friction is deducted from gross PnL on every completed trade:
$$\text{Gross PnL} = (\text{Exit Price} - \text{Entry Price}) \times \text{Direction}$$
$$\text{Net PnL} = \text{Gross PnL} - \text{Friction}$$

| Cost Scenario | Round-Turn Spread ($/oz) | Round-Turn Slippage ($/oz) | Total Friction ($/oz) |
| :--- | :--- | :--- | :--- |
| **1.0× Baseline** | $0.20 | $0.05 | **$0.25** |
| **1.5× Elevated** | $0.30 | $0.075 | **$0.375** |
| **2.0× Stressed** | $0.40 | $0.10 | **$0.50** |

- **Overnight Financing (Swap):** **$0.00/oz** across all trades. Verified because maximum holding interval is 07:05 to 12:00 UTC, which falls completely outside the broker daily rollover window (21:00–22:00 UTC). No weekend positions are ever held.

---

## 7. Change Control & Governance

Any modification to session timestamps, compression quantile thresholds, entry criteria, stop rules, or holding horizons constitutes an explicit hypothesis alteration and is strictly prohibited in Phase 22 and subsequent validation phases.
