# Phase 35: Open Governance & Specification Defects Register

**Document Type:** Algorithmic Trading Risk Register & Remediation Blueprint  
**Author:** Senior Quantitative Research Auditor & Financial Data Governance Engineer  
**System:** Treading-Ai (XAUUSD Research-Only)  
**Date:** November 2026  
**Status:** ACTIVE REGISTER — AWAITING PHASE-APPROVAL REMEDIATION  

---

## 1. Executive Summary & Remediation Governance

This document establishes the authoritative register of open governance, methodological, and specification defects identified during the Phase 33 and Phase 34 audits. 

### Mandatory Governance Rule for Amendments:
**Do not silently alter existing registered hypotheses or evaluation documents.** In accordance with institutional research integrity standards, no code or documentation in `reports/phase33/` may be quietly modified. Any future remediation must follow a strict, version-controlled process:
1. Proposed corrections must be formally authored as versioned amendments (e.g. `hypothesis_preregistration_v1.1.md` or `evaluation_protocol_v1.1.md`).
2. Amendments must be approved by an independent auditor **prior to loading confirmatory data or executing outcome backtests**.
3. All original Phase 33 documents remain archived as the baseline record of historical pre-registration.

---

## 2. Open Defects Register

```
+-----------+-------------------------------------------------------+----------+------------------------------------+
| Defect ID | Defect Title                                          | Severity | Remediation Status                 |
+-----------+-------------------------------------------------------+----------+------------------------------------+
| DEF-35-01 | Sample Size Gate vs Strategy Frequency Contradiction  | CRITICAL | Remediation Blueprint Documented   |
| DEF-35-02 | Unverified Session Calendar & 1,350-Minute Cutoff     | HIGH     | Remediation Blueprint Documented   |
| DEF-35-03 | Uncalibrated Symmetric Long/Short Swap Modeling       | HIGH     | Remediation Blueprint Documented   |
| DEF-35-04 | Unmodeled Weekend Opening Gap Execution Slippage      | MEDIUM   | Remediation Blueprint Documented   |
| DEF-35-05 | Conflation of Exploratory and Confirmatory Evidence   | CRITICAL | Remediation Blueprint Documented   |
+-----------+-------------------------------------------------------+----------+------------------------------------+
```

---

### Defect DEF-35-01: Sample Size Gate vs. Strategy Frequency Contradiction

- **Severity:** **CRITICAL** (Guaranteed failure trap for selective hypotheses).
- **Documented Discrepancy:**
  - In [`reports/phase33/hypothesis_preregistration.md`](file:///home/bhoot/project/Treading-Ai/reports/phase33/hypothesis_preregistration.md):
    - `H-Swing-02` Section 3.8 states expected trade frequency is **20 to 35 trades/year** (40 to 70 trades across a 2-year evaluation partition).
    - `H-Swing-03` Section 4.8 states expected trade frequency is **15 to 30 trades/year** (30 to 60 trades across a 2-year evaluation partition).
  - In [`reports/phase33/evaluation_protocol.md`](file:///home/bhoot/project/Treading-Ai/reports/phase33/evaluation_protocol.md) Section 3 and Section 9:
    - Condition 8 mandates an arbitrary hard cutoff: *"Sample Size Insufficiency: Total completed trades across the 2-year partition < 60 results in INSTANT REJECTION."*
- **Root Cause:** The evaluation protocol author applied a uniform sample-size threshold ($N \ge 60$) derived from high-frequency intraday protocols without reconciling it against the lower frequency of selective multi-day swing architectures.
- **Impact:** If `H-Swing-02` executes 50 trades in 2 years, or `H-Swing-03` executes 45 trades in 2 years, both hypotheses will be automatically rejected by the evaluation protocol despite functioning exactly as pre-registered.
- **Required Corrective Action:**
  1. Author an amended `evaluation_protocol_v1.1.md` that introduces a **tiered sample-size gate scaled to holding duration**:
     - Fast Swing (Holding 12–48h, e.g. `H-Swing-01`): Minimum $N \ge 60$ trades over 2 years.
     - Breakout / Mean Reversion (Holding 24–96h, e.g. `H-Swing-02`, `H-Swing-03`): Minimum $N \ge 40$ trades over 2 years, OR expand the evaluation partition window to 3–4 years to achieve $N \ge 60$.
  2. Implement statistical power calculations that tie the sample size requirement directly to the minimum detectable Sharpe ratio at $\alpha = 0.05$ and $1 - \beta = 0.80$.

---

### Defect DEF-35-02: Unverified Session Calendar & 1,350-Minute Cutoff

- **Severity:** **HIGH** (Unsubstantiated market microstructure assumption).
- **Documented Discrepancy:**
  - [`reports/phase33/temporal_integrity_report.md`](file:///home/bhoot/project/Treading-Ai/reports/phase33/temporal_integrity_report.md) claimed that 18 sessions with $< 1,350$ bars in 2021–2022 represent "scheduled US exchange market holidays with documented early closures."
  - Phase 34 audit ([`reports/phase34/session_calendar_audit.md`](file:///home/bhoot/project/Treading-Ai/reports/phase34/session_calendar_audit.md)) proved that HistData publishes no broker schedule or holiday calendar, spot gold is an international OTC instrument, and quote halt cutoffs varied by 90 minutes between 2021 and 2022 on the same holidays.
- **Root Cause:** Equating CME COMEX futures exchange holiday circulars with OTC spot quote feeds.
- **Impact:** The 1,350-minute threshold (`min_d1_bars_for_regular_session = 1350`) is an ad-hoc empirical heuristic tuned to the 2021–2022 dataset distribution.
- **Required Corrective Action:**
  1. Formally designate `min_d1_bars_for_regular_session = 1350` as an **unverified empirical heuristic**, not an exchange-mandated standard.
  2. In future evaluation protocols, mandate sensitivity testing across cutoffs $[1320, 1350, 1375]$ to confirm that strategy performance does not hinge on the exclusion of specific holiday-adjacent sessions.

---

### Defect DEF-35-03: Uncalibrated Symmetric Long/Short Swap Modeling

- **Severity:** **HIGH** (Underestimation of multi-day holding friction).
- **Documented Discrepancy:**
  - [`reports/phase33/hypothesis_preregistration.md`](file:///home/bhoot/project/Treading-Ai/reports/phase33/hypothesis_preregistration.md) and [`reports/phase33/evaluation_protocol.md`](file:///home/bhoot/project/Treading-Ai/reports/phase33/evaluation_protocol.md) model overnight swap financing symmetrically for both Long and Short positions across three tiers: $\$0.08, \$0.12, \$0.18 / \text{oz} / \text{day}$.
- **Root Cause:** Lack of broker-specific historical swap feeds in the open-source development data.
- **Impact:** In retail spot gold trading, retail brokers charge substantially larger financing rates on Long positions (reflecting the USD SOFR benchmark rate plus broker margin mark-ups, typically $-\$0.20$ to $-\$0.35/\text{oz}/\text{day}$ in 2023–2024), while short positions often receive zero credit or are also charged negative carry. Multi-day long swing positions held for 3–4 days will face severe unmodeled financing drag.
- **Required Corrective Action:**
  1. Replace the symmetric swap model with an **asymmetric carry matrix** in the evaluation engine:
     - Baseline Scenario: Long Swap $-\$0.22 / \text{oz} / \text{day}$, Short Swap $-\$0.05 / \text{oz} / \text{day}$.
     - Stressed Scenario: Long Swap $-\$0.35 / \text{oz} / \text{day}$, Short Swap $-\$0.12 / \text{oz} / \text{day}$.
  2. Implement explicit Wednesday 3-day rollover accounting (triple swap) to reflect retail settlement cycles.

---

### Defect DEF-35-04: Unmodeled Weekend Opening Gap Execution Slippage

- **Severity:** **MEDIUM** (Severe tail-risk execution vulnerability).
- **Documented Discrepancy:**
  - Neither [`reports/phase33/hypothesis_preregistration.md`](file:///home/bhoot/project/Treading-Ai/reports/phase33/hypothesis_preregistration.md) nor [`reports/phase33/evaluation_protocol.md`](file:///home/bhoot/project/Treading-Ai/reports/phase33/evaluation_protocol.md) specifies how stop-loss orders are filled when a Sunday market opening gap bypasses the stop price.
- **Root Cause:** Standard backtesters assume stop orders are filled at the exact stop level, ignoring market closure discontinuities.
- **Impact:** In swing trading with holding periods of 24–96 hours, positions held over weekends (Friday 17:00 NY close to Sunday 18:00 NY open) face major gap risk from weekend geopolitical announcements. Assuming fills at the stop price rather than the market opening price understates drawdown and tail risk.
- **Required Corrective Action:**
  1. Formally mandate that the backtest simulation engine check the Sunday open price:
     $$\text{Realized Exit} = \begin{cases} \text{Sunday Open} & \text{if Sunday Open breaches Stop Loss} \\ \text{Stop Loss} & \text{if breached during normal continuous trading} \end{cases}$$
  2. Exclude any simulation engine that does not support gap slippage from Confirmatory Research.

---

### Defect DEF-35-05: Conflation of Exploratory and Confirmatory Evidence

- **Severity:** **CRITICAL** (Methodological invalidation of out-of-sample claims).
- **Documented Discrepancy:**
  - Phase 33 characterized the 2023–2024 partition as an "untouched confirmatory testbed," ignoring the fact that Phase 23 and Phase 26 previously evaluated strategies on this exact partition.
- **Root Cause:** Cognitive bias and failure to consult repository decision archives before writing evaluation protocols.
- **Impact:** Any evaluation conducted on 2023–2024 under Phase 33's framing would have constituted a false claim of data independence.
- **Required Corrective Action:**
  1. Formally adopt the Research Modes framework defined in [`reports/phase35/research_modes_and_governance.md`](file:///home/bhoot/project/Treading-Ai/reports/phase35/research_modes_and_governance.md).
  2. Permanently disqualify 2023–2024 from serving as an independent confirmatory testbed.

---

## 3. Protocol for Amending Preregistered Documents

To preserve research integrity, the following four-step change management workflow is mandated for any future modification to pre-registered hypotheses:

```
[Defect Identified]
       │
       ▼
[Draft Versioned Amendment] ──> (e.g., hypothesis_preregistration_v1.1.md)
       │
       ▼
[Independent Audit Review]  ──> (Verify rationale, check for outcome snooping)
       │
       ▼
[Formal Gate Approval]      ──> (Recorded in project decision report)
       │
       ▼
[Evaluation Authorization]  ──> (Lock version, authorize execution on independent data)
```

1. **Immutable Baseline:** `reports/phase33/` files must remain unmodified as the historical v1.0 baseline.
2. **Explicit Changelog:** The amendment document must feature an explicit changelog detailing the exact section modified, the defect ID being resolved, and the economic justification.
3. **Zero Outcome Snooping:** An amendment cannot be proposed or approved after viewing backtest results from a confirmatory dataset.

---

## 4. Evidentiary Categorization

### Verified Evidence:
- DEF-35-01 through DEF-35-05 represent verified discrepancies between Phase 33 documents, Phase 34 audit findings, and real-world market microstructure.
- All Phase 33 documents remain unmodified in local storage.

### Assumptions:
- It is assumed that future backtest simulators can incorporate asymmetric swaps and Sunday opening gap slippage without performance degradation.

### Recommendations:
- Maintain all five defects as **OPEN** until a formal amendment phase is authorized by project stakeholders.
- Do not authorize backtests until DEF-35-01 (sample size) and DEF-35-03 (swap asymmetry) are formally amended.
