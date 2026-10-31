# Phase 30 Research Pre-Registration Checklist & Governance Protocol

**Phase:** 30 — H4 and Daily Dataset Audit, Horizon Statistics & Execution Cost Analysis  
**Scope:** Mandatory Pre-Registration Protocol for Future H4/Daily Quantitative Research  
**Auditor:** Senior Quantitative Research Engineer & Algorithmic Trading Risk Engineer  
**Date:** October 2026  
**Status:** COMPLETE & MANDATED  

---

## Executive Summary

To prevent repeating the methodological failures of Phase 27 (where underpowered hypotheses were subjected to uncorrected multiple testing against an unrealistic cost wall), this document establishes the mandatory **Pre-Registration Checklist** that must be executed and cryptographically locked prior to any backtesting or exploratory model development on H4 and Daily timeframes.

---

## 1. The Pre-Registration Protocol (Seven Mandatory Gates)

Before a single line of strategy backtesting code is executed, a written specification document must be created under `reports/phase{N}/pre_registration.md` and hashed via SHA-256:

```
+-------------------------------------------------------------------------------------------------------------------+
|                                 RESEARCH PRE-REGISTRATION CHECKLIST                                               |
+-------+-----------------------------+-----------------------------------------------------------------------------+
| Gate  | Research Domain             | Mandatory Requirement & Quantitative Specification                         |
+-------+-----------------------------+-----------------------------------------------------------------------------+
| 1     | Economic Mechanism          | Must identify a plausible macro-fundamental driver (real interest rates,    |
|       |                             | sovereign debt debasement, term premium shifts, or multi-day flow imbalances|
+-------+-----------------------------+-----------------------------------------------------------------------------+
| 2     | Minimum Horizon Floor       | Target holding duration must be >= 1 trading day (H4/Daily). Target price   |
|       |                             | excursion must be >= $15.00/oz. Intraday sub-hour setups are barred.        |
+-------+-----------------------------+-----------------------------------------------------------------------------+
| 3     | Sample Size & Power Nuance  | Must document expected annual trade frequency (20 to 50 trades/year).       |
|       |                             | Sample size power calculations must explain non-stationarity trade-offs.    |
+-------+-----------------------------+-----------------------------------------------------------------------------+
| 4     | Serial Dependence Correction| Must enforce non-overlapping trade logic or calculate Bartlett-corrected    |
|       |                             | effective sample size Neff = N * (1 - rho_1) / (1 + rho_1).                 |
+-------+-----------------------------+-----------------------------------------------------------------------------+
| 5     | Multiple-Testing Control    | If m candidate features are screened, p-values must be adjusted via the     |
|       |                             | Benjamini-Hochberg False Discovery Rate (FDR) or Holm-Bonferroni method.    |
+-------+-----------------------------+-----------------------------------------------------------------------------+
| 6     | Three-Tier Cost Stressing   | Must report net metrics under Tier 1 (Prime ECN), Tier 2 (Retail Raw),      |
|       |                             | and Tier 3 (Stressed), explicitly deducting cumulative daily swap financing.|
+-------+-----------------------------+-----------------------------------------------------------------------------+
| 7     | Pre-Defined Rejection Rule  | Must establish hard falsification gates before seeing development returns.  |
|       |                             | Zero post-hoc parameter adjustments or threshold retuning permitted.       |
+-------+-----------------------------+-----------------------------------------------------------------------------+
```

---

## 2. Statistical Power Nuance on Multi-Day Swing Horizons

> [!IMPORTANT]
> **Definitive Methodological Rule on Sample Sizes:**  
> In Phase 28, the audit proved that Phase 27 candidate strategies were underpowered to detect a tiny intraday edge ($\delta = \$0.50/\text{oz}$) because standard errors ($\text{SE} \sim \$0.60–\$1.40$) dwarfed the target effect.  
> However, an arbitrary universal requirement of $80\%$ statistical power ($N \ge 1,000$ trades) must **NOT** be imposed mechanically on low-frequency multi-day swing models.
> 
> ### Why 80% Power is Inappropriate for Macro Swings:
> 1. Multi-day swing models holding 2 to 10 days generate only **$25$ to $50$ trades per year**.
> 2. Demanding $N = 1,000$ trades would require **$20$ to $40$ years of continuous history**.
> 3. Over a 40-year window, the global monetary system experiences major structural breaks (e.g. 1970s stagflation, 1980s Volcker tightening, 1990s Great Moderation, 2008 ZIRP/QE, 2022 post-pandemic inflation). Financial time-series are **non-stationary**; pooling across structural breaks invalidates the statistical test.
> 
> ### The Defensible Statistical Alternative:
> Instead of demanding unachievable sample sizes, swing research must employ:
> 1. **Stationary Block Bootstrapping:** Generate 10,000 resamples (using Politis & Romano stationary block bootstrap) to construct empirical 95% confidence intervals for expectancy and Profit Factor without assuming normality.
> 2. **Economic Significance Hurdle:** Demand that the strategy generate an average net expectancy of at least **$\$3.00/\text{oz}$** (which is $> 5\times$ base transaction friction) and a Net Profit Factor $\ge 1.25$.
> 3. **Directional Symmetry:** Require that both Long and Short legs individually achieve Net Profit Factor $\ge 1.05$.

---

## 3. Mandatory Multi-Tier Cost Stress Testing

Every backtest evaluation must execute across all three standardized execution tiers:

```text
Tier 1: Prime Institutional ECN
  - Round-turn spread: $0.15/oz
  - Round-turn commission: $0.05/oz
  - Round-turn slippage: $0.05/oz
  - Daily Long swap financing: $0.08/oz / day
  - Minimum Survival Threshold: Net Profit Factor >= 1.30, Expectancy >= +$4.00/oz

Tier 2: Retail Raw Spread (Base Case)
  - Round-turn spread: $0.25/oz
  - Round-turn commission: $0.07/oz
  - Round-turn slippage: $0.10/oz
  - Daily Long swap financing: $0.12/oz / day (includes Wednesday triple swap)
  - Minimum Survival Threshold: Net Profit Factor >= 1.25, Expectancy >= +$3.00/oz

Tier 3: Retail Standard / Elevated Cost Stress
  - Round-turn spread: $0.45/oz
  - Round-turn commission: $0.00/oz
  - Round-turn slippage: $0.25/oz
  - Daily Long swap financing: $0.18/oz / day
  - Minimum Survival Threshold: Net PnL > $0.00 (Must remain net positive)
```

---

## 4. Partition Isolation and Falsification Rules

```
+---------------------------------------------------------------------------------+
|                        DATA PARTITION GOVERNANCE RULES                          |
+--------------------------+-----------------------+------------------------------+
| Partition                | Date Range            | Authorized Usage             |
+--------------------------+-----------------------+------------------------------+
| Development Partition    | 2021–2022 (516 days)  | Exploratory testing, feature |
|                          |                       | selection, parameter freezing|
+--------------------------+-----------------------+------------------------------+
| Historical Out-of-Sample | 2023–2024 (516 days)  | Locked evaluation checkpoint |
+--------------------------+-----------------------+------------------------------+
| Protected Validation     | 2025 (Full Year)      | SEALED (Zero access)         |
+--------------------------+-----------------------+------------------------------+
| Protected Test           | 2026 (Year-to-Date)   | SEALED (Zero access)         |
+--------------------------+-----------------------+------------------------------+
```

### Pre-Defined Rejection Criteria:
A candidate hypothesis is **INSTANTLY REJECTED** without tuning if it exhibits any of the following:
1. Net Profit Factor under Tier 2 Base Costs is $< 1.25$.
2. Directional asymmetry: either Long PF or Short PF is $< 1.05$.
3. Net expectancy under Tier 3 Stressed Costs is $\le \$0.00/\text{oz}$.
4. Maximum drawdown exceeds $2.5\times$ total net dollar profit.
5. In-sample win rate $< 45.0\%$ (for momentum) or $< 50.0\%$ (for mean reversion).
6. Bootstrap 95% confidence interval for mean expectancy spans zero.
