# Phase 30 Price & Horizon Statistics: Empirical Distributions on H4 & Daily

**Phase:** 30 — H4 and Daily Dataset Audit, Horizon Statistics & Execution Cost Analysis  
**Instrument:** XAUUSD (Spot Gold / US Dollar)  
**Dataset Under Audit:** 2021–2022 Development Partition ($N = 3,086$ H4 bars, $N = 516$ Daily bars)  
**Auditor:** Senior Quantitative Research Engineer & Market Data Auditor  
**Date:** October 2026  
**Status:** COMPLETE & INDEPENDENTLY AUDITED  

---

## Executive Summary

This report establishes the baseline price movement distributions, return characteristics, gap frequencies, and forward excursion profiles for XAUUSD on H4 and Daily timeframes across the permitted 2021–2022 development partition.

### Key Empirical Findings:
1. **Dramatic Excursion Expansion:**
   - **H4 Median Candle Range:** **$\$7.75/\text{oz}$** (Mean: $\$9.35/\text{oz}$, P95: $\$20.61/\text{oz}$).
   - **Daily Median Candle Range:** **$\$22.07/\text{oz}$** (Mean: $\$24.80/\text{oz}$, P95: $\$44.20/\text{oz}$).
   - In comparison to M5 (median range $\$1.02/\text{oz}$), the Daily timeframe expands price excursions by a factor of **$21.6\times$**.
2. **Multi-Day Excursion Profiles (MFE / MAE):**
   - Over a 3-day holding horizon, median Maximum Favorable Excursion (MFE) is **$\$17.25/\text{oz}$**.
   - Over a 5-day (1-week) horizon, median MFE expands to **$\$22.47/\text{oz}$**.
   - Over a 10-day (2-week) horizon, median MFE reaches **$\$31.16/\text{oz}$**.
3. **Symmetric Excursion Balance:** Across all multi-day horizons, median MFE and MAE are nearly identical (e.g. 5-day MFE $\$22.47$ vs MAE $\$22.16$). This confirms that untargeted buy-and-hold or random entry experiences symmetric two-sided volatility.
4. **Gap Distributions:**
   - Standard intraday H4 open gaps are negligible (median $\$0.02/\text{oz}$, P90 $\$0.31/\text{oz}$).
   - Weekend gaps ($N = 103$) are substantial: median weekend gap is **$\$0.97/\text{oz}$**, with P95 reaching **$\$4.89/\text{oz}$** and maximum historical gap reaching **$\$30.68/\text{oz}$**.
5. **Critical Epistemic Distinction:** Observed price excursion is **not** achievable trading PnL. An analyst cannot capture the high and low of a candle simultaneously. Capturing a portion of these excursions requires crossing bid-ask spreads, incurring slippage, and accumulating multi-day swap financing charges.

---

## 1. H4 Descriptive Price Statistics (2021–2022, $N = 3,086$)

```
+-------------------------------------------------------------------------------------------------------------------+
|                                      H4 DESCRIPTIVE PRICE DISTRIBUTIONS ($/oz)                                    |
+--------------------------+--------+--------+--------+--------+--------+--------+--------+--------+--------+---------+
| Metric                   | Mean   | StdDev | Min    | P10    | P25    | Median | P75    | P90    | P95    | Max     |
+--------------------------+--------+--------+--------+--------+--------+--------+--------+--------+--------+---------+
| Candle Range (H - L)     | $9.35  | $6.22  | $1.19  | $3.91  | $5.32  | $7.75  | $11.36 | $16.67 | $20.61 | $93.96  |
| Candle Body |C - O|      | $4.53  | $4.80  | $0.00  | $0.52  | $1.35  | $3.12  | $5.93  | $10.36 | $13.77 | $50.21  |
| Abs Close Change |C-C[-1]|| $4.54  | $4.82  | $0.00  | $0.53  | $1.36  | $3.11  | $5.93  | $10.28 | $13.83 | $50.21  |
| Open Gap |O - C[-1]|     | $0.14  | $0.74  | $0.00  | $0.00  | $0.00  | $0.02  | $0.06  | $0.31  | $0.68  | $30.68  |
| Weekend Gap (N = 103)    | $1.74  | $3.59  | $0.04  | $0.21  | $0.45  | $0.97  | $1.55  | $2.89  | $4.89  | $30.68  |
+--------------------------+--------+--------+--------+--------+--------+--------+--------+--------+--------+---------+
```

### Analytical Insights on H4:
- The median 4-hour range of **$\$7.75/\text{oz}$** provides substantial headroom above the $\$0.35–\$0.50/\text{oz}$ transaction cost wall. Fixed spread friction consumes only **$4.5\%$ to $6.5\%$** of the typical H4 range.
- 90% of all H4 candles move at least **$\$3.91/\text{oz}$**, while the top 5% of volatile sessions experience swings exceeding **$\$20.61/\text{oz}$**.

---

## 2. Daily Descriptive Price Statistics (2021–2022, $N = 516$ NY-Close Days)

```
+-------------------------------------------------------------------------------------------------------------------+
|                                     DAILY DESCRIPTIVE PRICE DISTRIBUTIONS ($/oz)                                  |
+--------------------------+--------+--------+--------+--------+--------+--------+--------+--------+--------+---------+
| Metric                   | Mean   | StdDev | Min    | P10    | P25    | Median | P75    | P90    | P95    | Max     |
+--------------------------+--------+--------+--------+--------+--------+--------+--------+--------+--------+---------+
| Candle Range (H - L)     | $24.80 | $11.82 | $7.89  | $13.51 | $16.94 | $22.07 | $29.75 | $38.81 | $44.20 | $96.46  |
| Candle Body |C - O|      | $11.95 | $10.70 | $0.13  | $1.73  | $4.29  | $8.62  | $16.34 | $27.58 | $33.11 | $65.32  |
| Abs Close Change |C-C[-1]|| $11.90 | $10.65 | $0.02  | $1.61  | $4.33  | $8.42  | $16.16 | $27.36 | $32.81 | $65.31  |
| Daily Open Gap |O-C[-1]| | $0.69  | $1.72  | $0.00  | $0.07  | $0.19  | $0.44  | $0.74  | $1.17  | $1.77  | $30.68  |
+--------------------------+--------+--------+--------+--------+--------+--------+--------+--------+--------+---------+
```

### Analytical Insights on Daily:
- The median daily price range is **$\$22.07/\text{oz}$**, with an average of **$\$24.80/\text{oz}$**.
- The median close-to-close change is **$\$8.42/\text{oz}$**.
- Fixed round-turn transaction friction of $\$0.42/\text{oz}$ represents only **$1.9\%$** of the median daily candle range and **$5.0\%$** of the median daily close-to-close change.

---

## 3. Forward Excursion Analysis (MFE & MAE Across Horizons)

To establish realistic profit targets and stop-loss boundaries for future swing hypothesis design, forward excursions were tracked from bar close across multiple forward horizons:

### A. H4 Forward Excursions (From Candle Close)

```
+-------------------------------------------------------------------------------------------------------------------+
|                                        H4 FORWARD EXCURSION DISTRIBUTIONS ($/oz)                                  |
+---------------------+-------------+-----------------------+-----------------------+-------------------------------+
| Horizon Identifier  | Duration    | Long MFE Median (Mean)| Long MAE Median (Mean)| MFE / MAE Dispersion Ratio    |
+---------------------+-------------+-----------------------+-----------------------+-------------------------------+
| h4_1_bars           | 4 hours     | $3.23 ($4.57)         | $3.26 ($4.77)         | 0.99 (Symmetric)              |
| h4_2_bars           | 8 hours     | $4.85 ($6.61)         | $4.81 ($6.98)         | 1.01 (Symmetric)              |
| h4_6_bars           | 24 hours    | $9.48 ($12.00)        | $9.50 ($12.82)        | 1.00 (Symmetric)              |
| h4_12_bars          | 48 hours    | $14.32 ($17.12)       | $13.72 ($18.34)       | 1.04 (Symmetric)              |
| h4_30_bars          | 120 hours   | $22.26 ($26.95)       | $22.62 ($29.57)       | 0.98 (Symmetric)              |
+---------------------+-------------+-----------------------+-----------------------+-------------------------------+
```

### B. Daily Forward Excursions (From Daily Close)

```
+-------------------------------------------------------------------------------------------------------------------+
|                                      DAILY FORWARD EXCURSION DISTRIBUTIONS ($/oz)                                 |
+---------------------+-------------+-----------------------+-----------------------+-------------------------------+
| Horizon Identifier  | Duration    | Long MFE Median (Mean)| Long MAE Median (Mean)| MFE / MAE Dispersion Ratio    |
+---------------------+-------------+-----------------------+-----------------------+-------------------------------+
| daily_1_days        | 1 Day       | $9.67 ($12.25)        | $8.61 ($12.52)        | 1.12 (Slight Long Updrift)    |
| daily_2_days        | 2 Days      | $14.49 ($17.38)       | $13.08 ($18.04)       | 1.11 (Slight Long Updrift)    |
| daily_3_days        | 3 Days      | $17.25 ($21.19)       | $16.42 ($22.24)       | 1.05 (Symmetric)              |
| daily_5_days        | 1 Week      | $22.47 ($27.12)       | $22.16 ($29.12)       | 1.01 (Symmetric)              |
| daily_10_days       | 2 Weeks     | $31.16 ($38.24)       | $32.26 ($42.15)       | 0.97 (Symmetric)              |
+---------------------+-------------+-----------------------+-----------------------+-------------------------------+
```

---

## 4. Methodological Distinction: Price Motion vs. Trade PnL

> [!CAUTION]
> **Definitive Auditor Declaration on Horizon Statistics:**  
> These price range and excursion metrics demonstrate **market volatility and statistical dispersion**, **NOT trading profitability**.  
> An unguided strategy entering at random will experience equal amounts of favorable ($+\$22.47$) and adverse ($-\$22.16$) excursion. In addition, real trading PnL suffers from:
> 1. Imperfect entry/exit timing (no trader enters at the exact low and exits at the exact high).
> 2. Premature stop-outs during adverse excursions prior to reaching favorable targets.
> 3. Execution slippage and bid-ask spreads.
> 4. Multi-day overnight swap financing drag.
> 
> Price excursion statistics prove that **the potential profit opportunity ($>\$20/oz$) is large enough to survive costs**, but they do **not** prove that a directional edge exists. Directional edge requires demonstrating out-of-sample predictive asymmetry.
