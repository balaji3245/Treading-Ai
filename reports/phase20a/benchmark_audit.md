# Phase 20A: Buy-and-Hold Benchmark Audit

**Document:** Buy-and-Hold Benchmark Audit  
**Target Benchmark:** Benchmark F (`pos_F = 1.0`)  
**Auditor:** Quantitative Researcher & Independent Code Auditor  

---

## 1. Executive Benchmark Summary

Phase 20 reported Benchmark F under the title **`Benchmark_F_Buy_and_Hold`**, showing:
*   Gross PnL: **+$789.61/oz**
*   Total Costs: **$241.68/oz**
*   Net PnL: **+$547.93/oz**
*   Active Trades: **516**

The forensic audit reveals that **this calculation does not represent a Buy-and-Hold benchmark**. Instead, it represents a **Daily Long-Only Strategy with mandatory daily re-entry and exit turnover**.

---

## 2. Mathematical Diagnosis: Daily Turnover vs Continuous Holding

### A. Phase 20 Implementation (Daily Long-Only Strategy)
In [run_phase20_macro_test.py:164-166](file:///home/bhoot/project/Treading-Ai/scripts/run_phase20_macro_test.py#L164-L166), trading metrics were evaluated session-by-session:
$$\text{Gross PnL}_t = \text{pos}_t \times (\text{Close}_t - \text{Open}_t)$$
$$\text{Friction}_t = \text{Spread} + \text{Slippage} + \text{Swap}_t = \$0.20 + \$0.10 + \text{Swap}_t$$
Because `pos_F` was set to $1.0$ for all $516$ out-of-sample sessions, the simulation:
1.  **Entered a fresh position every session** at 18:00 NY, incurring $\$0.05$ entry slippage and $\$0.10$ half-spread.
2.  **Exited every session** at 17:00 NY next day, incurring $\$0.05$ exit slippage and $\$0.10$ half-spread.
3.  **Deducted $\$0.30/\text{oz}$ in turnover friction on all 516 sessions**, accumulating:
    $$\text{Total Turnover Friction} = 516 \times \$0.30 = \mathbf{\$154.80/\text{oz}}$$
4.  **Discarded the 1-hour rollover price movement** between 17:00 NY and 18:00 NY each day. Across the 515 overnight transitions, gold prices appreciated by:
    $$\Delta_{\text{rollover gaps}} = \sum_{t=1}^{515} (\text{Open}_{t+1} - \text{Close}_t) = \mathbf{+\$7.554/\text{oz}}$$

### B. True Continuous Buy-and-Hold Position
A genuine Buy-and-Hold benchmark establishes a long position once at the beginning of the evaluation period and liquidates it once at the end:
1.  **Entry:** Session 0 Open (2023-01-02 18:00 NY) at $\text{Price} = \$1,827.187/\text{oz}$.
    *   Turnover friction: Half-spread ($\$0.10$) + entry slippage ($\$0.05$) = $\$0.15/\text{oz}$.
2.  **Exit:** Session 515 Close (2024-12-31 17:00 NY) at $\text{Price} = \$2,624.355/\text{oz}$.
    *   Turnover friction: Half-spread ($\$0.10$) + exit slippage ($\$0.05$) = $\$0.15/\text{oz}$.
3.  **Continuous Gross PnL:**
    $$\text{Gross PnL}_{\text{cont}} = \$2,624.355 - \$1,827.187 = \mathbf{+\$797.168/\text{oz}}$$
    *(Note: This equals the daily session sum $\$789.614$ plus the captured overnight roll gaps $+\$7.554$).*
4.  **Overnight Financing (Swap):** The continuous holder maintains the position across all 516 trading sessions, paying daily swap financing:
    *   Under Phase 20's original Wednesday swap (104 Wed, 412 non-Wed): $\$86.88/\text{oz}$.
    *   Under corrected Wednesday swap (103 Wed, 413 non-Wed): $\$86.64/\text{oz}$.
5.  **Total Transaction Costs:**
    $$\text{Costs}_{\text{cont}} = \text{Entry/Exit Friction} + \text{Swap Financing} = \$0.30 + \$86.64 = \mathbf{\$86.94/\text{oz}}$$
6.  **Continuous Net PnL:**
    $$\text{Net PnL}_{\text{cont}} = \$797.168 - \$86.94 = \mathbf{+\$710.228/\text{oz}}$$

---

## 3. Side-by-Side Benchmark Reconciliation

| Benchmark Metric | Daily Long-Only Strategy (Phase 20 Code) | Continuous Buy-and-Hold Position (True B&H) | Discrepancy / Distortion |
| :--- | :---: | :---: | :---: |
| **Trade Count** | 516 executions | 1 continuous holding | 515 redundant trade cycles |
| **Entry Point** | 18:00 NY daily | 2023-01-02 18:00 NY | Continuous holding across period |
| **Exit Point** | 17:00 NY daily | 2024-12-31 17:00 NY | Continuous holding across period |
| **Gross PnL ($/\text{oz}$)** | +$789.61 | +$797.17 | +$7.55 overnight gaps omitted by daily turnover |
| **Spread & Slippage Costs** | $154.80 | $0.30 | **+$154.50 excess friction charged** |
| **Swap Financing Costs** | $86.64 | $86.64 | Identical holding duration |
| **Total Costs ($/\text{oz}$)** | $241.44 (Orig $241.68) | $86.94 | **+$154.50 overstated costs** |
| **Net PnL ($/\text{oz}$)** | +$548.17 (Orig +$547.93) | **+$710.23** | **+$162.06 understated net return** |
| **Profit Factor** | 1.159 | N/A (single continuous trade) | N/A |
| **Maximum Drawdown ($/\text{oz}$)** | $298.54 | $285.34 | -$13.20 shallower drawdown in continuous holding |

---

## 4. Benchmark Classification and Governance Policy

1.  **Label Correction:** Project documentation must cease labeling Phase 20's `pos_F` as "Passive Buy-and-Hold". It must be explicitly labeled as **`Benchmark_F_Daily_Long_Only`**.
2.  **Dual Reporting Requirement:** Any future comparison against gold performance must report both benchmarks:
    *   **Benchmark F1 (Daily Long-Only):** Useful for comparing strategies that have mandatory daily session turnover and must pay daily execution friction.
    *   **Benchmark F2 (Continuous Buy-and-Hold):** The authentic benchmark for passive asset allocation and opportunity cost evaluation.
3.  **Impact on Strategy Conclusions:**
    *   This benchmark distortion did not falsely promote any failing model. In fact, under true Buy-and-Hold ($+\$710.23/\text{oz}$), the underperformance of the macro models ($-\$294.54$ to $-\$75.42/\text{oz}$) is even more stark: the macro models underperformed passive gold by **over $\$785/\text{oz}$**.
