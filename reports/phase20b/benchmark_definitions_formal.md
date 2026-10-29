# Phase 20B: Formal Benchmark Definitions & Separation

**Document:** Formal Benchmark Definitions & Governance Policy  
**Phase:** PHASE 20B — FORMAL CORRECTIONS & RESEARCH CLOSURE  
**Auditor / Author:** Quantitative Researcher & Independent Validation Auditor  

---

## 1. Overview & Rationale

In Phase 20, Benchmark F was titled "Passive Buy-and-Hold", but was implemented with daily session entry and exit turnover. This deducted $\$0.30/\text{oz}$ in round-turn spread and slippage every single day for 516 days ($\$154.80$ in total turnover friction) and omitted $\$7.55/\text{oz}$ in overnight rollover price movement.

To establish scientific rigor, Phase 20B formally partitions the benchmark suite into four mathematically distinct reference strategies:
1.  **Benchmark E:** No-Trade Baseline (Risk-Free Cash)
2.  **Benchmark F1:** Daily Long-Only Strategy (Daily Turnover)
3.  **Benchmark F2:** Continuous Buy-and-Hold Position (Passive Asset Holding)
4.  **Benchmark G:** Prior-Session Momentum Strategy

---

## 2. Formal Benchmark Specifications

### Benchmark E: No-Trade Baseline
*   **Mathematical Signal:** $\text{Position}_t = 0 \quad \forall t \in \{1, \dots, N\}$.
*   **Operational Execution:** No market orders placed. Zero exposure to spot gold price fluctuations.
*   **Frictions:** $\$0.00$ spread, $\$0.00$ slippage, $\$0.00$ financing.
*   **Performance (2023–2024):**
    *   Gross PnL: **$\$0.00/\text{oz}$**
    *   Total Costs: **$\$0.00/\text{oz}$**
    *   Net PnL: **$\$0.00/\text{oz}$**
    *   Trade Count: **0**
*   **Scientific Role:** Mandatory non-negative hurdle. Any candidate model producing negative net PnL is inferior to holding uninvested cash.

---

### Benchmark F1: Daily Long-Only Strategy (Daily Turnover)
*   **Mathematical Signal:** $\text{Position}_t = +1.0 \quad \forall t \in \{1, \dots, N\}$.
*   **Operational Execution:**
    *   **Entry:** Enters long 1 troy ounce at 18:00 NY open every institutional trading day. Incurs $\$0.10$ half-spread and $\$0.05$ entry slippage.
    *   **Exit:** Closes position at 17:00 NY close next day. Incurs $\$0.10$ half-spread and $\$0.05$ exit slippage.
    *   **Overnight Gap Exposure:** Position is flat during the 17:00–18:00 NY daily rollover maintenance window. Price gaps occurring between 17:00 and 18:00 NY are **not captured**.
    *   **Financing (Swap):** Incurs overnight financing every session held across the 17:00 NY roll ($-\$0.12/\text{oz}$ standard; $-\$0.36/\text{oz}$ on Wednesday roll settling Friday).
*   **Friction Multipliers:**
    *   Turnover Friction: $516 \times \$0.30 = \$154.80/\text{oz}$.
    *   Swap Financing (Corrected): 103 Wed rolls ($\$37.08$) + 413 non-Wed rolls ($\$49.56$) = $\$86.64/\text{oz}$.
    *   Total Baseline Costs: $\$154.80 + \$86.64 = \mathbf{\$241.44/\text{oz}}$.
*   **Performance (2023–2024):**
    *   Gross PnL: **+$789.61/\text{oz}$**
    *   Total Costs: **$241.44/\text{oz}$**
    *   Net PnL: **+$548.17/\text{oz}$**
    *   Net Profit Factor: **1.159**
    *   Win Rate: **53.68%**
    *   Max Drawdown: **$298.54/oz** (2.80%)
    *   Active Executions: **516**
*   **Scientific Role:** Controls for market beta in strategies that mandate daily discrete session rebalancing.

---

### Benchmark F2: Continuous Buy-and-Hold Position (Passive Asset Holding)
*   **Mathematical Signal:** Enters $\text{Position}_0 = +1.0$ at start of out-of-sample period; holds continuously until liquidation at period termination.
*   **Operational Execution:**
    *   **Entry:** Enters 1 troy ounce at Session 0 Open (2023-01-02 18:00 NY at $\$1,827.187/\text{oz}$).
    *   **Exit:** Liquidates at Session 515 Close (2024-12-31 17:00 NY at $\$2,624.355/\text{oz}$).
    *   **Overnight Gap Exposure:** Held continuously through all daily rollover maintenance windows (17:00–18:00 NY) and weekends. Captures full price trajectory, including $+\$7.554/\text{oz}$ in overnight roll gaps.
    *   **Financing (Swap):** Incurs daily holding financing across all 516 trading sessions.
*   **Friction Multipliers:**
    *   Turnover Friction: Single round-turn at entry/exit = $\mathbf{\$0.30/\text{oz}}$ total.
    *   Swap Financing: 103 Wed rolls ($\$37.08$) + 413 non-Wed rolls ($\$49.56$) = $\mathbf{\$86.64/\text{oz}}$.
    *   Total Costs: $\$0.30 + \$86.64 = \mathbf{\$86.94/\text{oz}}$.
*   **Performance (2023–2024):**
    *   Gross PnL: **+$797.17/\text{oz}$**
    *   Total Costs: **$86.94/\text{oz}$**
    *   Net PnL: **+$710.23/\text{oz}$**
    *   Trade Count: **1**
    *   Max Drawdown: **$285.34/oz** (2.68%)
*   **Scientific Role:** The authentic economic benchmark for passive asset allocation and opportunity cost. Demonstrates what a true buy-and-hold gold investor earned over the 2-year period.

---

### Benchmark G: Prior-Session Momentum Strategy
*   **Mathematical Signal:** $\text{Position}_t = \text{sign}(\text{Return}_{t-1}) = \text{sign}(\text{Close}_{t-1} - \text{Open}_{t-1})$.
*   **Operational Execution:** Enters long if prior session was positive; enters short if prior session was negative; stays flat if prior session was zero.
*   **Performance (2023–2024):**
    *   Active Trades: **516**
    *   Gross PnL: **-$230.91/\text{oz}$**
    *   Total Costs: **$241.44/\text{oz}$**
    *   Net PnL: **-$472.35/\text{oz}$**
    *   Net Profit Factor: **0.881**
    *   Win Rate: **43.60%**
    *   Max Drawdown: **$721.46/oz** (7.21%)
*   **Scientific Role:** Controls for simple 1-day price autocorrelation / trend-following in gold.

---

## 3. Comparative Benchmark Reconciliation Matrix

| Parameter / Dimension | Benchmark E (No-Trade) | Benchmark F1 (Daily Long-Only) | Benchmark F2 (Continuous B&H) | Benchmark G (Momentum) |
| :--- | :---: | :---: | :---: | :---: |
| **Execution Turnover Cycles** | 0 | 516 | 1 | 516 |
| **Turnover Costs ($/\text{oz}$)** | $0.00 | $154.80 | $0.30 | $154.80 |
| **Financing Costs ($/\text{oz}$)** | $0.00 | $86.64 | $86.64 | $86.64 |
| **Total Friction ($/\text{oz}$)** | $0.00 | $241.44 | $86.94 | $241.44 |
| **Gross Return ($/\text{oz}$)** | $0.00 | +$789.61 | +$797.17 | -$230.91 |
| **Net Return ($/\text{oz}$)** | **$0.00** | **+$548.17** | **+$710.23** | **-$472.35** |
| **Relative Underperformance of Best Macro Model (Model B)** | -$75.42/oz vs Cash | -$623.59/oz vs F1 | **-$785.65/oz vs F2** | +$396.93/oz vs G |

---

## 4. Governance Mandate

1.  In any subsequent Treading-Ai research, the label "Buy-and-Hold" must **never** be applied to a strategy that incurs daily entry/exit execution friction.
2.  If a benchmark involves daily discrete participation, it must be explicitly designated as **Daily Long-Only Strategy**.
3.  Both F1 and F2 must be reported alongside any future directional model to distinguish execution turnover drag from genuine alpha.
