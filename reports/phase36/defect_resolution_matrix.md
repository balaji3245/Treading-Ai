# Phase 36: Defect Traceability & Resolution Matrix

**Document Type:** Quantitative Research Audit & Defect Traceability Matrix  
**Author:** Senior Quantitative Research Auditor & Financial ML Governance Auditor  
**System:** Treading-Ai (XAUUSD Research-Only)  
**Date:** November 2026  
**Status:** COMPLETE — SPECIFICATION REMEDIATIONS DOCUMENTED  

---

## 1. Executive Summary & Auditing Directives

This matrix establishes end-to-end traceability between the open governance and specification defects cataloged in [`reports/phase35/open_defects_register.md`](file:///home/bhoot/project/Treading-Ai/reports/phase35/open_defects_register.md) and the versioned amendments enacted in [`reports/phase36/evaluation_protocol_v1.1.md`](file:///home/bhoot/project/Treading-Ai/reports/phase36/evaluation_protocol_v1.1.md).

### Non-Negotiable Auditing Standard:
**A documentation change alone must NOT be described as empirical validation.** Amending a protocol to specify asymmetric swap rates or gap execution policies resolves *specification ambiguities*, but it does not constitute *empirical validation*. Empirical closure requires physical data, verified broker statements, and deterministic simulation execution in future authorized phases.

---

## 2. Comprehensive Defect Resolution Matrix

```
+-----------+------------------------------------+------------------------------------+--------------------------+---------------------+
| Defect ID | Original Issue                     | Protocol v1.1 Remediation          | Resolution Status        | Remaining Open      |
|           |                                    |                                    |                          | Dependency          |
+-----------+------------------------------------+------------------------------------+--------------------------+---------------------+
| DEF-35-01 | Sample Size Gate vs Strategy       | Two-tier sample gate ($N<35$ fail, | PARTIALLY RESOLVED       | Acquisition of a    |
|           | Frequency Contradiction            | $35 \le N < 80$ underpowered,      | (Specification rectified;| multi-year dataset  |
|           |                                    | $N \ge 80$ full gate); power math. | awaits multi-year data). | (3–5 years).        |
+-----------+------------------------------------+------------------------------------+--------------------------+---------------------+
| DEF-35-02 | Unverified Session Calendar &      | 1,350 labeled unverified heuristic;| PARTIALLY RESOLVED       | Official feed       |
|           | 1,350-Minute Cutoff                | 3-way sensitivity matrix mandated  | (Heuristic documented;   | calendar or multi-  |
|           |                                    | across [1380, 1350, 1320].         | empirical testing open). | cutoff backtests.   |
+-----------+------------------------------------+------------------------------------+--------------------------+---------------------+
| DEF-35-03 | Uncalibrated Symmetric Long/Short  | Asymmetric carry matrix codified   | PARTIALLY RESOLVED       | Broker historical   |
|           | Swap Modeling                      | (Long -$0.22, Short -$0.05);       | (Model corrected;        | rate sheets or live |
|           |                                    | triple-swap rollover mandated.     | broker data unacquired). | statements.         |
+-----------+------------------------------------+------------------------------------+--------------------------+---------------------+
| DEF-35-04 | Unmodeled Weekend Opening Gap      | Execution at Sunday open price     | PARTIALLY RESOLVED       | Simulator engine    |
|           | Execution Slippage                 | mandated for breached stops;       | (Policy codified;        | code implementation |
|           |                                    | missing quote penalty added.       | engine unexecuted).      | in future phase.    |
+-----------+------------------------------------+------------------------------------+--------------------------+---------------------+
| DEF-35-05 | Conflation of Exploratory and      | 2023–2024 confirmatory status      | RESOLVED IN GOVERNANCE   | Acquisition of an   |
|           | Confirmatory Evidence              | revoked; Mode A/B separation       | SPECIFICATION            | independent Mode B  |
|           |                                    | enforced; independent data needed. | (Classification locked). | confirmatory set.   |
+-----------+------------------------------------+------------------------------------+--------------------------+---------------------+
```

---

## 3. Granular Defect Analysis & Evidentiary Traceability

### DEF-35-01: Sample Size Gate vs. Strategy Frequency Contradiction
- **Original Defect:** Protocol v1.0 enforced an arbitrary cutoff ($N < 60$ trades $\implies$ instant failure), guaranteeing rejection for selective swing hypotheses (`H-Swing-02` expected 40–70 trades; `H-Swing-03` expected 30–60 trades).
- **Protocol v1.1 Change:** Section 3 defines the statistical power formulation ($N \ge 196$ for $80\%$ power at $SR=0.50$). Establishes a two-tier decision gate:
  - $N < 35$: Operational failure $\implies$ Instant Rejection.
  - $35 \le N < 80$: Underpowered $\implies$ Inconclusive (requires extended multi-year partition).
  - $N \ge 80$: Full statistical gate $\implies$ Formal Sharpe/FDR evaluation.
- **Required Evidence for Full Closure:** A multi-year historical dataset (3–5 years) generating sufficient trade counts to achieve $\ge 80\%$ statistical power.
- **Current Status:** **PARTIALLY RESOLVED (Specification Complete; Empirical Validation Open).**
- **Remaining Dependency:** Data acquisition providing adequate sample depth.

---

### DEF-35-02: Unverified Session Calendar & 1,350-Minute Cutoff
- **Original Defect:** Phase 33 claimed 18 sessions with $< 1,350$ bars were official scheduled exchange closures, which Phase 34 proved to be unverified for the HistData OTC feed.
- **Protocol v1.1 Change:** Section 5 reclassifies the 1,350 cutoff as an *Unverified Empirical Heuristic* and mandates a 3-way sensitivity matrix across $[1380, 1350, 1320]$ bars. Strategy net expectancy must remain positive across all three tiers.
- **Required Evidence for Full Closure:** Feed-specific trading schedule documentation from the market data provider, or empirical sensitivity results showing strategy invariance to the cutoff.
- **Current Status:** **PARTIALLY RESOLVED (Heuristic Formally Documented; Empirical Testing Open).**
- **Remaining Dependency:** Ingestion of feed calendar metadata or sensitivity execution in a future evaluation phase.

---

### DEF-35-03: Uncalibrated Symmetric Long/Short Swap Modeling
- **Original Defect:** Overnight swaps were modeled symmetrically ($0.08, $0.12, $0.18/oz/day), severely understating real-world negative carry on long spot gold positions.
- **Protocol v1.1 Change:** Section 4 replaces symmetric swaps with an *Asymmetric Carry Matrix* ($-\$0.15$ to $-\$0.35$ Long, $-\$0.02$ to $-\$0.12$ Short), mandates Wednesday 3-day rollover accounting, and explicitly labels all values as unverified research assumptions.
- **Required Evidence for Full Closure:** Institutional broker daily financing statements or historical swap feeds calibrated to SOFR and physical bullion lending rates.
- **Current Status:** **PARTIALLY RESOLVED (Model Structure Rectified; Empirical Calibration Open).**
- **Remaining Dependency:** Real broker financing rate sheets.

---

### DEF-35-04: Unmodeled Weekend Opening Gap Execution Slippage
- **Original Defect:** Stop-loss orders held over weekends were assumed to fill at the stop price, ignoring gaps occurring between Friday 17:00 NY and Sunday 18:00 NY.
- **Protocol v1.1 Change:** Section 4.3 mandates that if Sunday opening price breaches a stop loss, the fill price must equal the Sunday market open price. Prohibits any simulator that assumes fills at the pre-gap stop price.
- **Required Evidence for Full Closure:** Verified backtesting simulator code implementing weekend gap detection, tick-level boundary checking, and fill price substitution.
- **Current Status:** **PARTIALLY RESOLVED (Policy Formally Codified; Code Implementation Open).**
- **Remaining Dependency:** Simulation engine verification in a future implementation phase.

---

### DEF-35-05: Conflation of Exploratory and Confirmatory Evidence
- **Original Defect:** Phase 33 described the previously evaluated 2023–2024 dataset as an "untouched confirmatory testbed."
- **Protocol v1.1 Change:** Section 2 formally revokes the confirmatory label, reclassifies 2023–2024 as *Exposed Historical Data*, mandates Mode A / Mode B governance separation, and enforces holdout quarantines.
- **Required Evidence for Full Closure:** Continued quarantine of 2025/2026 holdouts and acquisition of an authentic, unexposed Mode B confirmatory dataset.
- **Current Status:** **RESOLVED IN GOVERNANCE SPECIFICATION.**
- **Remaining Dependency:** Acquisition and custody verification of an independent confirmatory dataset.

---

## 4. Summary & Methodological Declaration

1. **Specification Closure:** All five defects have been addressed in the amended protocol specification (`evaluation_protocol_v1.1.md`). The protocol contains no contradictory sample-size gates, no false claims of data independence, and no unrealistic execution assumptions.
2. **Empirical Openness:** Physical validation (calibrated broker swap feeds, multi-year trade samples, and gap-aware simulator execution) remains dependent on future funded implementation phases.
3. **Evaluation Lock:** In accordance with institutional research integrity standards, no backtests or profitability checks were executed during Phase 36.
