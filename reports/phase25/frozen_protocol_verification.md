# PHASE 25: FROZEN PROTOCOL VERIFICATION & SPECIFICATION FREEZE

**Hypothesis ID:** `HYP-24-NY-REVERSAL-EXHAUSTION`  
**Phase:** 25 — Controlled Development Backtest  
**Authoritative Protocol Document:** `reports/phase24/frozen_evaluation_protocol.md`  
**Protocol SHA-256 Hash:** `eac50d9fb79e8a3bfaa25a0be463c4dc778ea12f442e5cd6a2b88bfcd898cb18`  
**Baseline Git Commit:** `5038d33e4ff7e76d7f8d308da0b9b76132bfdc82`  
**Working Tree Status:** Clean tracked tree (untracked Phase 23–25 reports and test scripts present)  
**Verification Date:** 2026-10-30T03:40:00 UTC  

---

## 1. Protocol Authenticity & Decision Record Alignment

Before any backtest code was executed or parameters evaluated, the authoritative specification was verified against the Phase 24 decision record:

1. **Protocol Document Integrity:**
   - Source: `reports/phase24/frozen_evaluation_protocol.md`
   - Verified SHA-256: `eac50d9fb79e8a3bfaa25a0be463c4dc778ea12f442e5cd6a2b88bfcd898cb18`
   - Match: Cryptographically confirmed identical to the pre-registered Phase 24 protocol.
2. **Decision Record Alignment:**
   - Document: `reports/phase24/phase24_decision.md`
   - Pre-registered hypothesis: `HYP-24-NY-REVERSAL-EXHAUSTION`
   - Lead authorizer: Phase 24 formal verdict `PASS` authorizing controlled development only (not live trading or profitability).
3. **No Silent Rule Alteration:**
   - Entry timing, consensus anchor, excursion window, stop-loss multiplier, time exit, transaction cost schedule, and promotion gate criteria were locked without modification.

---

## 2. Written Protocol Amendment: Timestamp Convention & Execution Timing

To guarantee zero look-ahead bias and eliminate all ambiguity in high-frequency M5 bar indexing, the timestamping convention is formally codified in this written amendment prior to backtest evaluation:

### 2.1 M5 Parquet Timestamp Definition
- In the XAUUSD M5 historical dataset (`data/processed/XAUUSD/M5/`), each record's `timestamp` corresponds strictly to the **start time (bar open)** of the 5-minute interval in Coordinated Universal Time (UTC).
- Therefore:
  - The bar timestamped `11:55:00 UTC` spans `[11:55:00, 12:00:00) UTC`. Its `close` price is realized precisely at `12:00:00 UTC`.
  - The bar timestamped `13:55:00 UTC` spans `[13:55:00, 14:00:00) UTC`. Its `close` price is realized precisely at `14:00:00 UTC`.
  - The bar timestamped `14:00:00 UTC` spans `[14:00:00, 14:05:00) UTC`.
  - The bar timestamped `14:05:00 UTC` spans `[14:05:00, 14:10:00) UTC`.
  - The bar timestamped `18:25:00 UTC` spans `[18:25:00, 18:30:00) UTC`. Its `close` price is realized precisely at `18:30:00 UTC` (official COMEX gold pit settlement).

### 2.2 Operational Alignment with Frozen Protocol
1. **Consensus Baseline Anchor ($P_{\text{base}}$):**
   - Specified as the 12:00:00 UTC price level.
   - Evaluated as `bar[timestamp == 11:55:00 UTC].close`.
2. **Morning Excursion Measurement ($P_{\text{14:00}}$):**
   - Specified as the 14:00:00 UTC price level.
   - Evaluated as `bar[timestamp == 13:55:00 UTC].close`.
   - Excursion vector: $\Delta P_t = P_{\text{14:00}} - P_{\text{base}}$.
3. **Normalized Excursion Ratio ($\text{NER}_t$):**
   - $\text{NER}_t = \frac{|\Delta P_t|}{\text{ATR}_{20, t}^{\text{prior}}}$.
   - Trailing 20-day ATR is computed exclusively on completed calendar days shifted by 1 full day (`shift(1)`), eliminating any current-day look-ahead.
4. **Execution Timing Verification:**
   - The frozen protocol specifies: *"Entry at the specified 14:05 UTC bar open, subject to a verified timestamp convention."*
   - At `14:00:00 UTC`, the 13:55 bar completes and $\Delta P_t$ and $\text{NER}_t$ become known.
   - To account for institutional trade generation, signaling, and OMS transmission latency (5-minute buffer), order entry is submitted for execution at the **`14:05:00 UTC` bar open**.
   - Price fill: `bar[timestamp == 14:05:00 UTC].open`.
   - *Sensitivity check:* Even if immediate fill at `14:00:00 UTC` open were utilized, signal generation occurs strictly at the 13:55 close (`14:00:00 UTC`). The 14:05:00 entry provides conservative latency buffering.
5. **Trade Direction:**
   - Counter-trend exhaustion fading:
     - If $\Delta P_t > 0$ (Morning upside overshoot) $\implies$ **SHORT** trade.
     - If $\Delta P_t < 0$ (Morning downside overshoot) $\implies$ **LONG** trade.
     - If $\Delta P_t == 0 \implies$ No trade.
6. **Stop-Loss Mechanics:**
   - Stop distance: $D_{\text{stop}} = 0.75 \times |\Delta P_t|$.
   - For Short: $\text{Stop Price} = \text{Entry Price} + D_{\text{stop}}$.
   - For Long: $\text{Stop Price} = \text{Entry Price} - D_{\text{stop}}$.
7. **Order-of-Operations & Gap Rules:**
   - Stop-first intrabar precedence: on every bar $j \in [t_{\text{entry}}, t_{\text{exit}}]$, stop penetration is checked before scheduled time exit.
   - Adverse open-gap slippage: if a bar opens past the stop price, exit fills at the bar open price (full adverse slippage realized).
   - Adverse entry-gap abort: if the entry bar opens beyond the initial stop price, the trade is aborted immediately (0 fill, 0 loss).
8. **Scheduled Time Exit:**
   - Holding terminates at `18:30:00 UTC` Close (`bar[timestamp == 18:25:00 UTC].close`).
   - If not stopped out, the trade is closed at this price.
9. **Financing and Transaction Cost Assumptions:**
   - Round-turn baseline friction: **$0.25/oz** ($0.20 spread + $0.05 slippage).
   - Elevated friction tiers: 1.5× ($0.375/oz) and 2.0× ($0.50/oz).
   - Overnight financing (swap): **$0.00/oz** across all trades (trades terminate 2.5 hours prior to the 21:00 UTC rollover window).
10. **Trade Frequency:**
    - Maximum of **1 trade per eligible calendar day**.

---

## 3. Pre-Registered Promotion Gates (Phase 24 Frozen Scorecard)

The strategy must satisfy all 4 frozen gates on the 2021–2022 development partition without relaxation:

| Gate | Category | Threshold / Requirement |
| :--- | :--- | :--- |
| **Gate 1** | **Economic Edge** | Net Expectancy $\ge +\$0.50/\text{oz}$; Net Profit Factor $\ge 1.25$; Win Rate $\ge 52.5\%$; Net PnL $> 0$ at 1.5× cost stress ($0.375/oz). |
| **Gate 2** | **Directional Symmetry** | Long Net Profit Factor $\ge 1.10$ AND Short Net Profit Factor $\ge 1.10$. No directional collapse. |
| **Gate 3** | **Statistical Significance** | Moving-block bootstrap 95% CI ($B=2,000, b=5$) for mean net expectancy strictly $> \$0.00/\text{oz}$. Outperformance over $0 no-trade baseline at $\alpha = 0.05$. |
| **Gate 4** | **Risk / Drawdown** | Peak-to-trough equity drawdown $\le \$45.00/\text{oz}$ ($< 0.50\%$ of asset price). |

---

## 4. Verification Conclusion

The frozen evaluation protocol is verified intact, mathematically explicit, and operationally unambiguous. No post-hoc modifications or parameter adjustments are permitted. Controlled development backtesting on the 2021–2022 partition is fully authorized.
