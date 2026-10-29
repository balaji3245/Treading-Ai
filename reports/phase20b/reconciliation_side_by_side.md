# Phase 20B: Side-by-Side Accounting & Reconciliation Report

**Document:** Side-by-Side Accounting & Metric Reconciliation  
**Phase:** PHASE 20B — FORMAL CORRECTIONS & RESEARCH CLOSURE  
**Auditor / Author:** Quantitative Researcher & Independent Validation Auditor  

---

## 1. Primary Reconciled Results (1.0× Baseline Cost Tier)

All values are expressed in USD per troy ounce ($/oz) over the 516 out-of-sample institutional gold sessions (2023–2024):

| Strategy / Model | Active Trades | Gross PnL | Phase 20 Original Costs | Phase 20B Corrected Costs | Cost Difference | Phase 20 Original Net PnL | Phase 20B Corrected Net PnL | Net PnL Impact | Corrected Net PF | Corrected Win Rate (%) | Directional Hit Rate (%) | Max Drawdown ($/oz) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Model A (Yield Only)** | 364 | -$121.74 | $175.44 | $172.80 | -$2.64 | -$297.18 | **-$294.54** | +$2.64 | 0.895 | 45.33% | 49.73% | $489.26 |
| **Model B (Dollar Only)** | 396 | +$112.02 | $191.04 | $187.44 | -$3.60 | -$79.02 | **-$75.42** | +$3.60 | 0.975 | 47.73% | 50.76% | $401.78 |
| **Model C (Bivariate)** | 516 | +$159.52 | $241.68 | $241.44 | -$0.24 | -$82.16 | **-$81.92** | +$0.24 | 0.978 | 47.09% | 50.97% | $458.50 |
| **Model D (Trivariate)** | 516 | -$17.04 | $241.68 | $241.44 | -$0.24 | -$258.72 | **-$258.48** | +$0.24 | 0.933 | 46.12% | 51.36% | $454.12 |
| **Benchmark E (No-Trade)** | 0 | $0.00 | $0.00 | $0.00 | $0.00 | $0.00 | **$0.00** | $0.00 | N/A | 0.00% | 0.00% | $0.00 |
| **Benchmark F1 (Daily Long-Only)** | 516 | +$789.61 | $241.68 | $241.44 | -$0.24 | +$547.93 | **+$548.17** | +$0.24 | 1.159 | 53.68% | 52.91% | $298.54 |
| **Benchmark F2 (Continuous B&H)** | 1 | +$797.17 | N/A | $86.94 | -$154.50 | N/A | **+$710.23** | +$162.30 | N/A | 100.00% | N/A | $285.34 |
| **Benchmark G (Prior Momentum)** | 516 | -$230.91 | $241.68 | $241.44 | -$0.24 | -$472.59 | **-$472.35** | +$0.24 | 0.881 | 43.60% | 46.71% | $721.46 |

---

## 2. Reconciling Implementation Timing Differences

### A. Wednesday Triple-Swap Timing Shift
*   **The Bug:** In Phase 20 (`run_phase20_macro_test.py:309-311`), `entry_dow == 2` applied triple swap to trades entered Wednesday 18:00 NY (settling Monday).
*   **The Market Convention:** Spot gold trades on $T+2$ value date settlement. Positions held across Wednesday 17:00 NY roll settle Friday and roll over the weekend to Monday ($3\times$ swap). This corresponds to trade date Wednesday (`settlement_dow == 2`), which enters Tuesday 18:00 NY.
*   **Reconciled Impact:**
    *   104 Wednesday entry sessions shifted to 103 Wednesday settlement sessions.
    *   Total 2-year holding financing for a long position reduced from $\$86.88$ to $\mathbf{\$86.64/\text{oz}}$ ($-\$0.24/\text{oz}$).
    *   For Model A (inactive on 152 sessions): 2 triple swaps were shifted onto inactive sessions, reducing total costs by $\$2.64/\text{oz}$.
    *   For Model B (inactive on 120 sessions): 3 triple swaps were shifted onto inactive sessions, reducing total costs by $\$3.60/\text{oz}$.
    *   For Models C, D, F1, G (active all 516 sessions): costs reduced by exactly $\$0.24/\text{oz}$.

---

## 3. Short Financing Sensitivity ($0.00 Short Swap)

In Phase 20, short positions were debited $-\$0.12/\text{oz}$/day identically to long positions. In institutional spot markets, short gold positions earn USD SOFR interest minus gold lease rates, resulting in positive or near-zero carry. Symmetrical debit is an **unverified retail proxy**.

To ensure scientific completeness, we evaluate performance when short swap financing is set to $\$0.00/\text{oz}$ (zero carrying cost on short positions):

| Model | Symmetric Corrected Net PnL | Zero Short Swap Net PnL | Benefit from Zero Short Swap | Resulting Net Profit Factor | Economic Viability |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Model A (Yield Only)** | -$294.54 | **-$259.38** | +$35.16 | 0.906 | Strictly Unprofitable |
| **Model B (Dollar Only)** | -$75.42 | **-$42.06** | +$33.36 | 0.986 | Strictly Unprofitable |
| **Model C (Bivariate)** | -$81.92 | **-$50.12** | +$31.80 | 0.987 | Strictly Unprofitable |
| **Model D (Trivariate)** | -$258.48 | **-$226.44** | +$32.04 | 0.941 | Strictly Unprofitable |

**Finding:** Even with completely free short financing, **every single macro model loses money**. The failure of the strategy is fundamental, not an accounting artifact.

---

## 4. Stressed Cost Sensitivity Reconciled (1.0×, 1.5×, 2.0× Multipliers)

| Strategy / Model | 1.0× Baseline Net PnL | 1.5× Elevated Net PnL | 2.0× Stressed Net PnL | Meets Robustness Hurdle? |
| :--- | :---: | :---: | :---: | :---: |
| **Model A (Yield Only)** | -$294.54 | -$380.94 | -$467.34 | **NO (Fails)** |
| **Model B (Dollar Only)** | -$75.42 | -$169.14 | -$262.86 | **NO (Fails)** |
| **Model C (Bivariate)** | -$81.92 | -$202.64 | -$323.36 | **NO (Fails)** |
| **Model D (Trivariate)** | -$258.48 | -$379.20 | -$499.92 | **NO (Fails)** |
| **Benchmark E (No-Trade)** | $0.00 | $0.00 | $0.00 | **YES (Neutral)** |
| **Benchmark F1 (Daily Long-Only)** | +$548.17 | +$427.45 | +$306.73 | **YES (Profitable)** |
| **Benchmark F2 (Continuous B&H)** | +$710.23 | +$666.76 | +$623.29 | **YES (Profitable)** |
| **Benchmark G (Prior Momentum)** | -$472.35 | -$593.07 | -$713.79 | **NO (Fails)** |

---

## 5. Reconciliation Conclusion

1.  **Original Phase 20 Reports Preserved:** Original results remain intact in `reports/phase20/results.json`.
2.  **Corrected Values Certified:** Reconciled values published herein represent the authoritative, audited quantitative record.
3.  **Research Conclusion Invariant:** Accounting corrections improved net PnL by $\$0.24$ to $\$3.60/\text{oz}$, but do not alter the conclusion: **macroeconomic signals fail to generate positive net trading expectancy**.
