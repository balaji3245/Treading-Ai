# Phase 36: Governance Gate Decision & Protocol Amendment Sign-Off

**Phase:** Phase 36 — Evaluation Protocol v1.1 Amendment & Defect Traceability  
**System:** Treading-Ai (XAUUSD Research-Only)  
**Roles:** Senior Quantitative Research Engineer, Financial ML Governance Auditor  
**Date:** November 2026  

---

## 1. Formal Gate Decision

### **DECISION: PASS — PROTOCOL AMENDMENT DOCUMENTED**

### Decision Rationale:
Phase 36 has completed all planning, auditing, and specification objectives:
1. **Evaluation Protocol v1.1 Formally Codified:** [`reports/phase36/evaluation_protocol_v1.1.md`](file:///home/bhoot/project/Treading-Ai/reports/phase36/evaluation_protocol_v1.1.md) successfully amends the historical v1.0 baseline, resolving specification contradictions regarding sample size gates, asymmetric financing carry, Sunday opening gap execution, and session completeness heuristics.
2. **Defect Traceability Matrix Established:** [`reports/phase36/defect_resolution_matrix.md`](file:///home/bhoot/project/Treading-Ai/reports/phase36/defect_resolution_matrix.md) establishes end-to-end traceability for defects DEF-35-01 through DEF-35-05, explicitly separating documentation remediation from physical empirical validation.
3. **Data Integrity & Quarantines Preserved:** The protected 2025 Validation and 2026 Test partitions were neither read, loaded, queried, nor hashed. No external data was purchased or downloaded ($0.00 spend).
4. **Research Pre-Registration Preserved:** The Phase 33 pre-registered hypotheses remain completely intact; no rules, indicator parameters, or decision thresholds were altered.

---

## 2. Four Mandatory Governance Questions

In strict accordance with the Phase 36 mandate, the following four governance determinations are formally recorded:

### 1. Is the Protocol Amendment Complete?
**YES.**  
`evaluation_protocol_v1.1.md` is complete, internally consistent, and fully version-controlled. It replaces arbitrary uniform gates with objective statistical power formulations, mandates asymmetric carry modeling, codifies worst-case weekend gap execution, and establishes a 5-stage capital deployment gate.

### 2. Which Assumptions Remain Unverified?
The following market microstructure assumptions remain unverified research models and cannot be confirmed without real broker data:
- **Broker Financing Rates:** The asymmetric swap tiers ($-\$0.15$ to $-\$0.35$ Long, $-\$0.02$ to $-\$0.12$ Short) are uncalibrated research heuristics. They do not reflect verified rate sheets from a specific institutional bullion broker.
- **Source-Feed Trading Schedule:** The HistData OTC feed lacks an official broker/exchange trading calendar. The 1,350-minute completeness cutoff remains an empirical heuristic.
- **Weekend Opening Gap Execution:** Assumes orders execute at the Sunday market opening price without additional broker execution delays or requotes.

### 3. Does an Independent Confirmatory Dataset Exist in the Workspace?
**NO.**  
As established in Phase 34 and Phase 35, all historical data in local storage is either heavily explored (2021–2022), previously evaluated (2023–2024), or protected holdout data (2025–2026). No uninspected, independent historical dataset currently exists in the workspace.

### 4. Is Any Strategy Evaluation Authorized?
**NO.**  
Under no circumstances is strategy evaluation authorized by Phase 36. Backtests, equity curve evaluations, parameter tuning, and model training remain **STRICTLY PROHIBITED**. Strategy evaluation cannot occur until an independent confirmatory dataset is acquired and verified under a future authorized phase.

---

## 3. Summary of Completed Phase 36 Deliverables

All three required Phase 36 documents have been generated and archived under `reports/phase36/`:

1. [**`reports/phase36/evaluation_protocol_v1.1.md`**](file:///home/bhoot/project/Treading-Ai/reports/phase36/evaluation_protocol_v1.1.md):
   - Versioned protocol amendment containing change log, Mode B independence rules, two-tier sample-size power gate, asymmetric carry matrix, Sunday opening gap execution policy, completeness sensitivity matrix, and 5-stage deployment gate.
2. [**`reports/phase36/defect_resolution_matrix.md`**](file:///home/bhoot/project/Treading-Ai/reports/phase36/defect_resolution_matrix.md):
   - Comprehensive traceability matrix mapping defects DEF-35-01 through DEF-35-05 to specific protocol changes, evidentiary requirements, and remaining open dependencies.
3. [**`reports/phase36/phase36_decision.md`**](file:///home/bhoot/project/Treading-Ai/reports/phase36/phase36_decision.md):
   - Authoritative gate decision record, four governance determinations, evidentiary segregation, and execution halt confirmation.

---

## 4. Protected Partition Governance

In strict compliance with Phase 36 instructions, the protected 2025 Validation and 2026 Test partitions were **NOT read, loaded, queried, or hashed in this phase**.

The following reference values represent **previously recorded SHA-256 hashes** from prior phases, recorded here solely as historical documentation:
- **2025 Validation (`data/features/XAUUSD_M5_features_val.parquet`):**
  `7e9222e9dc0893601e24505912eeab78330670c4e70ebcc2fa462ff8d44a4f94`
- **2026 Test (`data/features/XAUUSD_M5_features_test.parquet`):**
  `f95fd09a5d07666e3f1d9a72e840e2e97f3c058d11b6bb0c712b21dea86a5dec`

Both partitions remain 100% quarantined, unaccessed, and intact.

---

## 5. Separation of Evidentiary Categories

### 5.1 Verified Evidence
- `evaluation_protocol_v1.1.md` resolves all textual, mathematical, and procedural contradictions present in v1.0.
- All code in `src/treading_ai/` and all historical data files in `data/` remain unmodified.
- Zero budget was expended ($0.00 spend).

### 5.2 Assumptions
- It is assumed that future backtest simulators can parse underlying M1 bars to execute Sunday opening gap fills accurately.
- It is assumed that institutional brokers charge financing rates within the $-\$0.15$ to $-\$0.35/\text{oz}/\text{day}$ band for long spot gold.

### 5.3 Unresolved Issues
- **No Independent Testbed:** The project still lacks an independent historical dataset outside the holdouts.
- **Empirical Calibration Pending:** Broker rate sheets and source-feed calendars remain unacquired.

### 5.4 Recommendations
1. Maintain the evaluation halt. Do not backtest hypotheses on 2021–2024 data.
2. In Phase 37, either formulate a concrete data acquisition plan to obtain independent tick/M1 data (Mode B) or conduct explicitly labeled exploratory feature diagnostics on 2021–2022 data (Mode A).

---

## 6. Stop Conditions Acknowledged & Execution Halted

In strict compliance with Phase 36 instructions:
- **Zero strategy backtests were executed.**
- **Zero strategy profitability calculations were performed.**
- **Zero machine learning models were trained.**
- **Protected partitions were neither queried nor hashed.**
- **No external downloads were initiated.**

**EXECUTION HALTED.** Strategy evaluation is NOT authorized. The research system halts and awaits explicit stakeholder approval before proceeding to Phase 37.
