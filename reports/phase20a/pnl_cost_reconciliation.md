# Phase 20A: PnL and Cost Accounting Reconciliation

**Document:** PnL and Cost Accounting Reconciliation  
**Target Study:** Phase 20 Out-of-Sample Performance (2023–2024, $N = 516$ Sessions)  
**Auditor:** Quantitative Researcher & Independent Code Auditor  

---

## 1. Classification of Cost & Execution Assumptions

All cost assumptions used in Phase 20 and Phase 20A are classified below into four strict categories: `verified`, `proxy`, `unverified`, or `not applicable`.

| Parameter | Value | Phase 20 Usage | Audit Classification | Empirical Justification & Limitations |
| :--- | :--- | :--- | :--- | :--- |
| **Broker Bid-Ask Spread** | $\$0.20/\text{oz}$ | Charged per active session | **Proxy** | Reflects typical tight institutional spread during liquid London/NY overlap. Widens significantly to $\$0.50-\$2.00$ during the 17:00–18:00 NY rollover maintenance window. |
| **Execution Slippage** | $\$0.10/\text{oz}$ | $\$0.05$ entry + $\$0.05$ exit | **Proxy** | Standard institutional execution proxy for normal liquid hours. Under-estimates market-reopen slippage at 18:00 NY. |
| **Long Overnight Swap** | $-\$0.12/\text{oz/day}$ | Charged on all long positions held overnight | **Proxy** | Corresponds to $\approx 2.2\%$ annual financing on $\$2,000$ gold ($2,000 \times 0.022 / 365 = \$0.1205$). Reasonable retail/prime broker rate. |
| **Short Overnight Swap** | $-\$0.12/\text{oz/day}$ | Charged on all short positions held overnight | **Unverified** | Assumes retail broker symmetric debit. In interbank/institutional spot markets, short gold positions earn USD SOFR interest minus gold lease rates ($\approx 0.5\%$), yielding a credit or near-zero financing. |
| **Wednesday Triple Swap** | $3\times$ daily swap ($-\$0.36/\text{oz}$) | Charged on rollover settling over weekend | **Verified Convention / Unverified Timing** | $T+2$ settlement rollover across Wednesday 17:00 NY is an established market convention. However, Phase 20's code misapplied it to Wednesday evening entry rather than Tuesday evening entry. |
| **Turnover Multiplier on Buy-and-Hold** | $\$0.30/\text{oz}$ daily | Charged every session on `pos_F = 1.0` | **Unverified / Mislabeled** | Passive buy-and-hold does not execute daily entries and exits. Applying daily spread and slippage is appropriate only for a Daily Long-Only turnover strategy. |
| **No-Trade Friction** | $\$0.00/\text{oz}$ | Zero friction when `pos == 0` | **Verified** | Standard risk-free cash holding baseline. |

---

## 2. Reconstructed Model Performance (1.0× Baseline Costs)

The table below reconciles Phase 20 original reported figures with Phase 20A independently reconstructed results:

| Strategy / Model | Active Trades | Gross PnL ($/\text{oz}$) | Original Costs ($/\text{oz}$) | Corrected Costs ($/\text{oz}$) | Original Net PnL ($/\text{oz}$) | Corrected Net PnL ($/\text{oz}$) | Net PnL Diff ($/\text{oz}$) | Corrected Net PF | Max Drawdown ($/\text{oz}$) | Max DD (%) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Model A (Yield Only)** | 364 | -$121.74 | $175.44 | $172.80 | -$297.18 | **-$294.54** | +$2.64 | 0.895 | $489.26 | 4.89% |
| **Model B (Dollar Only)** | 396 | +$112.02 | $191.04 | $187.44 | -$79.02 | **-$75.42** | +$3.60 | 0.975 | $401.78 | 4.02% |
| **Model C (Bivariate)** | 516 | +$159.52 | $241.68 | $241.44 | -$82.16 | **-$81.92** | +$0.24 | 0.978 | $458.50 | 4.59% |
| **Model D (Trivariate)** | 516 | -$17.04 | $241.68 | $241.44 | -$258.72 | **-$258.48** | +$0.24 | 0.933 | $454.12 | 4.54% |
| **Benchmark E (No-Trade)** | 0 | $0.00 | $0.00 | $0.00 | $0.00 | **$0.00** | $0.00 | N/A | $0.00 | 0.00% |
| **Benchmark F (Daily Long-Only)** | 516 | +$789.61 | $241.68 | $241.44 | +$547.93 | **+$548.17** | +$0.24 | 1.159 | $298.54 | 2.80% |
| **Benchmark F (Continuous B&H)** | 1 | +$797.17 | N/A | $86.94 | N/A | **+$710.23** | +$162.30 | N/A | $285.34 | 2.68% |
| **Benchmark G (Momentum)** | 516 | -$230.91 | $241.68 | $241.44 | -$472.59 | **-$472.35** | +$0.24 | 0.881 | $721.46 | 7.21% |

*Note:* Max Drawdown (%) is calculated on a hypothetical $\$10,000$ initial capital base holding 1 troy ounce.

---

## 3. Cost Sensitivity Tests (1.0×, 1.5×, 2.0× Multipliers)

The table below reconciles performance under stressed cost conditions:

| Model / Benchmark | 1.0× Baseline Net PnL | 1.5× Elevated Net PnL (Orig) | 1.5× Elevated Net PnL (Corr) | 2.0× Stressed Net PnL (Orig) | 2.0× Stressed Net PnL (Corr) | Robust under Stress? |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Model A (Yield Only)** | -$294.54 | -$384.90 | -$380.94 | -$472.62 | -$467.34 | **NO (Fails)** |
| **Model B (Dollar Only)** | -$75.42 | -$174.54 | -$169.14 | -$270.06 | -$262.86 | **NO (Fails)** |
| **Model C (Bivariate)** | -$81.92 | -$203.00 | -$202.64 | -$323.84 | -$323.36 | **NO (Fails)** |
| **Model D (Trivariate)** | -$258.48 | -$379.56 | -$379.20 | -$500.40 | -$499.92 | **NO (Fails)** |
| **Benchmark E (No-Trade)** | $0.00 | $0.00 | $0.00 | $0.00 | $0.00 | **YES (Neutral)** |
| **Benchmark F (Daily Long-Only)** | +$548.17 | +$427.09 | +$427.45 | +$306.25 | +$306.73 | **YES (Profitable)** |
| **Benchmark F (Continuous B&H)** | +$710.23 | N/A | +$666.76 | N/A | +$623.29 | **YES (Profitable)** |
| **Benchmark G (Momentum)** | -$472.35 | -$593.43 | -$593.07 | -$714.27 | -$713.79 | **NO (Fails)** |

---

## 4. Asymmetric Short Financing Sensitivity ($0.00 Short Swap)

To address the `unverified` assumption of symmetrical -$0.12/day short swap debits, we test an institutional scenario where long positions pay overnight swap ($0.12/day standard, $0.36 Wednesday), while short positions incur **zero swap financing** ($0.00):

| Model | Symmetric Net PnL (1.0×) | Zero Short Swap Net PnL (1.0×) | Short Swap Benefit ($/\text{oz}$) | Zero Short Swap Net PF | Resulting Expectancy |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Model A (Yield Only)** | -$294.54 | **-$259.38** | +$35.16 | 0.906 | Strictly Negative |
| **Model B (Dollar Only)** | -$75.42 | **-$42.06** | +$33.36 | 0.986 | Strictly Negative |
| **Model C (Bivariate)** | -$81.92 | **-$50.12** | +$31.80 | 0.987 | Strictly Negative |
| **Model D (Trivariate)** | -$258.48 | **-$226.44** | +$32.04 | 0.941 | Strictly Negative |

### Finding
Even under a completely cost-free short financing structure, **all four candidate models remain net negative**. The failure of the macro models is not an artifact of short financing costs; it is driven by their inability to forecast directional moves accurately enough to overcome basic bid-ask spread and slippage.
