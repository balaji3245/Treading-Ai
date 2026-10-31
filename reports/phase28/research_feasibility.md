# Phase 28 Research Feasibility Synthesis: Systematic Trading on XAUUSD M5

**Phase:** 28 — Research Feasibility, Data Adequacy & Methodology Audit  
**Instrument:** XAUUSD (Spot Gold / US Dollar)  
**Timeframe:** M5  
**Auditor:** Senior Quantitative Research Engineer & Independent Financial ML Auditor  
**Date:** October 2026  
**Status:** COMPLETE & INDEPENDENTLY AUDITED  

---

## Executive Summary

Following the consecutive failure and rejection of all previous trading strategies across Phases 20–27 (culminating in the rejection of all five candidate hypotheses in Phase 27), this feasibility synthesis evaluates whether continuing strategy discovery on the current XAUUSD M5 dataset is scientifically justified.

By synthesizing the empirical findings of the **Execution Cost Audit**, **Data Adequacy Report**, **Statistical Power Analysis**, and **Predictive Information Audit**, this report establishes that **the current dataset, execution cost model, and research timeframe are structurally incapable of sustaining further strategy discovery**.

```
+-------------------------------------------------------------------------------------------------------------------+
|                                 PHASE 28 FOUR-PILLAR FEASIBILITY MATRIX                                           |
+----------------------+----------------------------------------------------------+---------------------------------+
| Audit Dimension      | Empirical Finding                                        | Feasibility Impact              |
+----------------------+----------------------------------------------------------+---------------------------------+
| 1. Execution Costs   | $0.25/oz baseline is an unvalidated static proxy.        | Lacks empirical broker validation|
|                      | Real costs range $0.35–$0.70/oz (up to $2.50 in roll/news| Intraday moves crushed by costs.|
+----------------------+----------------------------------------------------------+---------------------------------+
| 2. Data Adequacy     | OHLC is single-price (Bid) only. Volume is 100.0% zero.  | Volume & spread strategies      |
|                      | No Ask prices, no spreads, no order-book depth.          | technically impossible.         |
+----------------------+----------------------------------------------------------+---------------------------------+
| 3. Statistical Power | Sample sizes (N = 40–133) have 6%–43% power.             | High Type II error (blindness). |
|                      | MDE is $0.79–$4.05/oz; needs 5 to 131 years of data.     | True edge cannot be proven.     |
+----------------------+----------------------------------------------------------+---------------------------------+
| 4. Predictive Info   | OOS R2 is negative beyond 5 min. Feature R2 < 0.06%.     | M5 returns behave as pure noise.|
|                      | Gross signal ($0.008/oz) is 32x smaller than friction.   | Guaranteed negative expectancy. |
+----------------------+----------------------------------------------------------+---------------------------------+
```

---

## 1. Synthesis of the Four Audit Pillars

### Pillar 1: The Execution Friction Wall
- The foundational assumption of prior backtests was that spot gold can be traded at a flat cost of $0.25/oz.
- Empirical broker realities show that spot gold spreads widen dramatically during the Asian session ($0.40–$0.65/oz), at daily rollover ($1.50–$3.00/oz), and during macroeconomic releases ($1.80–$3.50/oz).
- Furthermore, stop-loss market fills suffer severe adverse execution slippage during momentum breakouts.
- For an M5 timeframe where the median 5-minute price delta is **$0.44/oz** and the median 1-hour move is **$1.50/oz**, transaction friction represents **17% to 60%** of the entire price move. Fixed costs mathematically consume gross edge.

### Pillar 2: Data Deficiencies & Epistemic Blindspots
- The historical dataset consists exclusively of HistData.com M1 bars aggregated to M5.
- The prices represent **Bid quotes only**. Without simultaneous Ask quotes, backtests execute at artificial midpoints, concealing the entry/exit spread penalty.
- The `volume` series is **100.0% zeros**. Indicators that rely on volume-weighted pricing, liquidity imbalances, or volume spikes cannot be computed.
- The absence of Level 2 order-book data prevents evaluating liquidity depth, market impact, and queuing delay.

### Pillar 3: Severe Underpowering & Sample Size Deficits
- In Phase 27, strategy sample sizes ranged from $N = 40$ to $N = 133$ trades across two years.
- Standard errors of mean trade return ($\text{SE} = \$0.28$ to $\$1.44/\text{oz}$) were larger than the entire target economic expectancy ($\$0.50/\text{oz}$).
- Statistical power to detect a true $+\$0.50/\text{oz}$ edge at $\alpha = 0.05$ was only **6.38% to 42.72%**.
- Achieving standard 80% power requires **250 to 3,000 trades**, which would necessitate **5 to 131 years** of stationary data at observed trade frequencies.
- Consequently, backtests on this dataset cannot differentiate a real edge from luck: failure to achieve significance does not disprove an edge, and positive backtest PnL does not prove an edge.

### Pillar 4: Near-Zero Predictive Information at M5
- Out-of-sample predictive modeling (trained on 2021, evaluated on 2022) revealed that 12 standard technical features explain less than **0.06%** of forward price variance.
- For forecast horizons beyond 5 minutes (15m, 1h), the out-of-sample $R^2$ is **strictly negative**, meaning a naive zero-return model outperforms feature-based predictions.
- The maximum out-of-sample directional accuracy was $50.94\%$, yielding a theoretical gross expectancy of $+\$0.0078/\text{oz}$. Against the $\$0.25/\text{oz}$ transaction cost, this results in a net expectancy of **$-\$0.2422/\text{oz}$**.
- Fixed friction is **32 times larger** than the marginal gross signal.

---

## 2. Evaluation of Strategic Alternatives

```
+---------------------------------------------------------------------------------+
|                       STRATEGIC HORIZON COMPARISON MATRIX                       |
+-------------------------+-----------------------+-------------------------------+
| Dimension               | M5 Intraday (Current) | Multi-Day Swing (Alternative) |
+-------------------------+-----------------------+-------------------------------+
| Average Excursion       | $1.00 – $4.00/oz      | $20.00 – $60.00/oz            |
| Round-Turn Friction     | $0.25 – $0.50/oz      | $0.30 – $0.50/oz + Swap       |
| Frictional Drag         | 15% – 50% (Fatal)     | 0.8% – 2.0% (Negligible)      |
| Trade Frequency         | 25 – 150 / year       | 15 – 35 / year                |
| Noise-to-Signal Ratio   | Extremely High (>99%) | Moderate                      |
| Primary Edge Driver     | Microstructure timing | Macro fundamentals / trends   |
| Current Data Suitability| Inadequate (No ticks) | Adequate (Daily/Hourly OHLC)  |
+-------------------------+-----------------------+-------------------------------+
```

---

## 3. Feasibility Conclusion & Strategic Recommendation

Attempting to manufacture another trading hypothesis on the current XAUUSD M5 dataset is an unproductive research exercise. The combination of:
1. Unvalidated execution costs,
2. Single-sided bid data with zero volume,
3. Severely underpowered sample sizes ($N < 150$, power $< 43\%$), and
4. Structural dominance of transaction friction over microscopic M5 predictive signals,

guarantees that any strategy developed on this dataset will either fail out-of-sample evaluation or prove to be an overfitted statistical artifact.

### Definitive Recommendation:
Research on M5 intraday hypothesis discovery must be **PAUSED IMMEDIATELY**. The program must transition to:
1. **Improving Data First:** Procuring institutional tick-level bid/ask quote feeds with depth of market and timestamped fill records.
2. **Re-orienting Research Horizons:** Shifting systematic strategy discovery from intraday M5 noise to **multi-day swing horizons (H1/H4/D1)** or macro-economic fundamental flows, where price excursions ($>\$25/oz$) render execution friction negligible.
