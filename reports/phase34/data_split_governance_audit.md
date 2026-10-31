# Phase 34: Data Split Governance & Contamination Audit

**Document Type:** Quantitative Research Audit & Data-Governance Review  
**Auditor:** Senior Quantitative Research Auditor & Financial ML Validation Specialist  
**System:** Treading-Ai (XAUUSD Research-Only)  
**Date:** November 2026  
**Status:** COMPLETE — CRITICAL DEFECT EXPOSED & RECTIFIED  

---

## 1. Executive Summary

This audit evaluates the integrity, exposure history, and independence classification of all historical data partitions across the Treading-Ai project lifecycle. 

### Critical Audit Finding:
In Phase 33, [`reports/phase33/evaluation_protocol.md`](file:///home/bhoot/project/Treading-Ai/reports/phase33/evaluation_protocol.md) and [`reports/phase33/phase33_decision.md`](file:///home/bhoot/project/Treading-Ai/reports/phase33/phase33_decision.md) designated the 2023–2024 dataset as:
> *"Confirmatory Evaluation Partition: 2023-01-01 to 2024-12-31 (untouched during hypothesis pre-registration; primary testbed for candidate evaluation)"* and *"Primary out-of-sample evaluation partition... completely uninspected and unread."*

**This designation is materially false and represents a severe data-governance failure.** 

A historical review of repository records reveals that the 2023–2024 partition was previously utilized as an out-of-sample evaluation testbed in **Phase 23** (for `HYP-21-ASIAN-LONDON-EXPANSION`) and in **Phase 26** (for `HYP-24-NY-REVERSAL-EXHAUSTION`). Both phases produced extensive documentation regarding gold's macroeconomic regime during 2023–2024—specifically detailing the persistent secular bull market, the March 2023 Silicon Valley Bank failure, runaway momentum expansion, and the complete collapse of short swing/intraday strategies.

Pre-registering new hypotheses in Phase 33 **does not and cannot reset historical exposure or confer statistical independence** upon a dataset whose empirical regime characteristics have already been inspected and published.

---

## 2. Chronological Data Partition Classifications

Each historical period available in the Treading-Ai project is formally reclassified according to institutional algorithmic trading risk standards:

| Period | Time Horizon | Available Files | Prior Exposure & Usage History | Formal Governance Classification |
| :--- | :--- | :--- | :--- | :--- |
| **2021–2022** | 2021-01-01 to 2022-12-31 | `DAT_ASCII_XAUUSD_M1_2021.csv`<br>`DAT_ASCII_XAUUSD_M1_2022.csv`<br>`XAUUSD_H4_2021/2022.parquet`<br>`XAUUSD_D1_2021/2022.parquet` | Iteratively used across Phases 3–15, Phase 22, Phase 25 for labeling, baseline model training, threshold tuning, and feature engineering. | **Exploratory / Development Data**<br>*(Heavily contaminated; cannot validate edge)* |
| **2023–2024** | 2023-01-01 to 2024-12-31 | `DAT_ASCII_XAUUSD_M1_2023.csv`<br>`DAT_ASCII_XAUUSD_M1_2024.csv`<br>`XAUUSD_H4_2023/2024.parquet`<br>`XAUUSD_M5/M15/M30_2023/2024.parquet` | Evaluated in Phase 23 (`HYP-21`, rejected) and Phase 26 (`HYP-24`, rejected). Macro regime, volatility surges, and short-side failure modes are fully documented in repository reports. | **Previously Evaluated / Exposed Data**<br>*(Non-independent; cannot serve as confirmatory testbed)* |
| **2025** | 2025-01-01 to 2025-12-31 | `XAUUSD_M5_features_val.parquet`<br>`DAT_ASCII_XAUUSD_M1_2025.csv` | Designated as frozen validation holdout in Phase 2. Quarantined. | **Protected Holdout Validation Data**<br>*(Strictly quarantined; inaccessible)* |
| **2026** | 2026-01-01 to 2026-10-31 | `XAUUSD_M5_features_test.parquet`<br>`DAT_ASCII_XAUUSD_M1_202601-10.csv` | Designated as frozen test holdout in Phase 2. Quarantined. | **Protected Holdout Test Data**<br>*(Strictly quarantined; inaccessible)* |

---

## 3. Prior Evaluation History of the 2023–2024 Dataset

### 3.1 Phase 23 Locked Evaluation Record
- **Report Reference:** [`reports/phase23/phase23_decision.md`](file:///home/bhoot/project/Treading-Ai/reports/phase23/phase23_decision.md)
- **Strategy Audited:** `HYP-21-ASIAN-LONDON-EXPANSION`
- **Evaluation Partition:** 2023–2024 Out-of-Sample Partition
- **Findings Recorded in Repository:**
  - Win rate collapsed from $54.46\%$ (2021–2022) to $43.82\%$ (2023–2024).
  - Short trades suffered catastrophic failure: 37 trades, Net PnL = -$41.933/oz, Profit Factor = 0.633, Win rate = 27.03%.
  - Drawdown doubled from $30.659/oz to $61.558/oz.
  - Documented cause: Spot gold's macro secular uptrend over 2023–2024 transformed intraday downward expansions into severe whipsaws.

### 3.2 Phase 26 Locked Evaluation Record
- **Report Reference:** [`reports/phase26/phase26_decision.md`](file:///home/bhoot/project/Treading-Ai/reports/phase26/phase26_decision.md)
- **Strategy Audited:** `HYP-24-NY-REVERSAL-EXHAUSTION`
- **Evaluation Partition:** 2023–2024 Historical Evaluation Partition
- **Findings Recorded in Repository:**
  - Strategy failed all 7 pre-registered promotion gates on 2023–2024 (Net Expectancy -$2.323/oz, PF 0.551).
  - Documented cause: *"When exposed to the persistent secular trend expansion of 2023–2024 (SVB banking crisis, geopolitical shocks, and sovereign central bank accumulation driving continuous new all-time highs), the counter-trend fading mechanism broke down completely."*

### 3.3 Implications for Pre-Registered Hypotheses
Because researchers have already observed that 2023–2024 was characterized by strong trend momentum and failing counter-trend/short setups:
- Designing a trend-pullback hypothesis (`H-Swing-01`) or a breakout hypothesis (`H-Swing-02`) after having observed trend persistence on 2023–2024 creates an inherent, subconscious selection bias.
- Even if the researchers consciously attempted to formulate economic priors independently, the **methodological claim of data independence is permanently invalidated**.

---

## 4. Required Corrective Actions on Phase 33 Documentation

The following explicit corrections are mandated across the project records:

1. **Revocation of "Untouched" Status:**
   All statements in [`reports/phase33/evaluation_protocol.md`](file:///home/bhoot/project/Treading-Ai/reports/phase33/evaluation_protocol.md) and [`reports/phase33/phase33_decision.md`](file:///home/bhoot/project/Treading-Ai/reports/phase33/phase33_decision.md) claiming that 2023–2024 is "untouched," "uninspected," or "confirmatory" are hereby declared **VOID**.
2. **Re-labeling of 2023–2024:**
   In any future research activity, the 2023–2024 partition must be designated exclusively as:
   `"Previously Evaluated Historical Partition (High Risk of Selection Bias)"`.
3. **Prohibition of Confirmatory Authority:**
   No positive outcome on the 2023–2024 dataset may be cited as proof of strategy robustness or used to authorize capital allocation.

---

## 5. Separation of Evidentiary Categories

### Verified Evidence:
- Phase 23 decision record (`reports/phase23/phase23_decision.md`) and Phase 26 decision record (`reports/phase26/phase26_decision.md`) explicitly document locked backtest executions and strategy evaluations on the 2023–2024 partition.
- `reports/phase33/evaluation_protocol.md` erroneously asserted that 2023–2024 was "completely uninspected and unread."

### Unverified Claims:
- Phase 33's claim that pre-registration insulated the 2023–2024 dataset from historical data-mining bias.

### Required Corrective Action:
- Classify 2023–2024 as previously exposed historical data. Prohibit its use as an independent confirmatory testbed.
