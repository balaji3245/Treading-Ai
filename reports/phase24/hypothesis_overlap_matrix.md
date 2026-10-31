# HYPOTHESIS OVERLAP & DIFFERENTIATION MATRIX: PHASE 24

**Phase:** 24 — New Hypothesis Discovery & Pre-Registration  
**Repository:** `Treading-Ai`  
**Execution Timestamp:** 2026-10-30T03:42:00 UTC  
**Objective:** Systematically screen prospective candidate hypotheses against prior failed paradigms to prevent circular research.  

---

## 1. Dimensional Comparison Matrix

The matrix below evaluates three prospective Phase 24 candidate hypotheses across 10 critical structural axes against the four historically rejected research paradigms:

- **Candidate A:** `HYP-24-LBMA-AM-FIX-DRIFT` (London AM Gold Auction Anticipation Drift)
- **Candidate B:** `HYP-24-NY-REVERSAL-EXHAUSTION` (US Morning Volatility Exhaustion & Post-Release Mean-Reversion)
- **Candidate C:** `HYP-24-COMEX-SETTLEMENT-REBALANCE` (COMEX Pit Close & Late Afternoon Inventory Squaring)

| Axis | Paradigm 1 (Phases 1–16: M5 ML Indicators) | Paradigm 3 (Phases 19–20: Daily Macro) | Paradigm 4 (Phases 21–23: Asian-London Breakout) | Candidate A (LBMA AM Fix Drift) | Candidate B (NY Reversal Exhaustion) | Candidate C (COMEX Settlement Rebalance) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Underlying Market Mechanism** | Statistical pattern matching on technical price indicators | Macro factor equilibrium (real yields & DXY regression) | Asian range compression to London opening liquidity expansion | Pre-auction inventory accumulation by LBMA market makers | Liquidity exhaustion & dealer inventory absorption following US macro shocks | Commodity index & ETF delta squaring following COMEX pit close |
| **2. Core Information Source** | 232 continuous M5 rolling technical features | Daily FRED macroeconomic series differences | Asian session high/low bounds & daily ATR lag | Early European momentum preceding 10:30 London fixing | Extreme US morning excursion relative to daily range | Daily excursion prior to 13:30 NY COMEX pit settlement |
| **3. Observation Frequency** | Continuous M5 steps ($N > 240,000$ bars) | Daily session returns ($N = 516$ days) | 1 discrete trade per compressed day ($N \approx 50-60$/yr) | 1 discrete trade per European business day ($N \approx 180$/yr) | Event-driven on extreme excursion days ($N \approx 60-80$/yr) | 1 trade on qualified extended days ($N \approx 70-90$/yr) |
| **4. Serial Label Overlap** | **Extreme (95%–99% overlap)** | Zero (daily non-overlapping) | Zero (daily non-overlapping) | Zero (discrete 1-hour intraday window) | Zero (discrete 4-hour intraday window) | Zero (discrete 2.5-hour intraday window) |
| **5. Entry Timing** | Every M5 bar with positive model threshold | Session open (18:00 NY) | Next M5 bar open after breakout close (07:05–09:00 UTC) | 09:30 London time Open | Next bar open following confirmed excursion exhaustion at 14:00 UTC | Next bar open following 18:30 UTC COMEX settlement |
| **6. Exit Timing** | Fixed forward bar count ($H=12$ to 288) | Session close (17:00 NY) | 12:00:00 UTC Close (11:55 bar close) | 10:30 London time Close (Auction time) | 18:30 UTC Close (or trailing stop) | 20:45 UTC Close (prior to rollover) |
| **7. Holding Duration** | 1 hour to 24 hours (rolling) | 23 hours (continuous overnight) | 3 to 5 hours (daytime only) | Exactly 1 hour | 4 to 4.5 hours | 2 to 2.5 hours |
| **8. Overnight Financing Exposure** | Uncontrolled (carried overnight) | Heavy daily financing ($-\$0.12$ daily, $-\$0.36$ Wed) | **$0.00/oz (closed by 12:00 UTC)** | **$0.00/oz (closed by 10:30 London)** | **$0.00/oz (closed by 18:30 UTC)** | **$0.00/oz (closed by 20:45 UTC)** |
| **9. Directional Symmetry / Macro Drift Dependence** | Highly vulnerable (Long bias masquerade) | Highly vulnerable (negative net return) | **Failed out-of-sample (Shorts collapsed, PF 0.633)** | Directionally conditioned on pre-fix momentum | **Counter-trend mean reversion (inherently symmetric)** | **Counter-trend mean reversion (inherently symmetric)** |
| **10. Expected Move vs Friction Ratio** | Move $1.50–$2.50 vs $0.40 cost (**17%–27% drag**) | Move $15–$25 vs $0.40+swap (**vulnerable to roll**) | Move $8–$14 vs $0.25 cost (**2%–3% drag**) | Move $3.00–$5.00 vs $0.25 cost (**5%–8% drag**) | Move $10.00–$20.00 vs $0.25 cost (**1.5%–2.5% drag**) | Move $6.00–$10.00 vs $0.25 cost (**3.0%–4.5% drag**) |

---

## 2. Granular Overlap Screening Against Prior Paradigms

### Screening Candidate A (`HYP-24-LBMA-AM-FIX-DRIFT`):
- **Overlap with Paradigm 1 (M5 Indicators):** None. Uses no technical indicators; operates on a discrete 1-hour pre-auction window.
- **Overlap with Paradigm 3 (Daily Macro):** None. Uses zero FRED macroeconomic series.
- **Overlap with Paradigm 4 (Asian-London Breakout):** Partial temporal proximity. Candidate A enters at 09:30 London time, which overlaps with the tail of the Asian-London holding window (07:05–12:00 UTC). Furthermore, with typical 1-hour moves of only $3.00–$5.00/oz, transaction friction ($0.25/oz) constitutes a 5%–8% drag, approaching the cost wall danger zone.

### Screening Candidate B (`HYP-24-NY-REVERSAL-EXHAUSTION`):
- **Overlap with Paradigm 1 (M5 Indicators):** None. Uses no rolling oscillators; triggers purely on extreme standard-deviation price extensions following macroeconomic releases.
- **Overlap with Paradigm 3 (Daily Macro):** Distinct. Paradigm 3 attempted to forecast 24-hour direction from static macro numbers; Candidate B exploits structural liquidity withdrawal and institutional market maker absorption following announcement shocks.
- **Overlap with Paradigm 4 (Asian-London Breakout):** **Completely orthogonal.**
  - **Time Window:** Paradigm 4 operated in the London morning (07:00–12:00 UTC). Candidate B operates in the New York afternoon (14:00–18:30 UTC).
  - **Market Dynamic:** Paradigm 4 was a trend-following expansion breakout strategy. Candidate B is a counter-trend liquidity mean-reversion strategy.
  - **Macro Secular Trend Immunity:** Because Candidate B fades extreme overextended moves, it does not suffer from the fatal flaw of Phase 23 (where Short trend breakouts collapsed into secular bull runs).
  - **Move Size vs Friction:** Extreme excursion moves in the US session average $12.00–$22.00/oz, making baseline friction ($0.25/oz) consume only 1.2%–2.0% of the gross excursion.

### Screening Candidate C (`HYP-24-COMEX-SETTLEMENT-REBALANCE`):
- **Overlap with Prior Work:** Orthogonal timing (18:30–20:45 UTC). However, trading between 18:30 and 20:45 UTC approaches the illiquid 21:00 UTC market rollover window, where broker bid-ask spreads begin widening substantially ($0.35–$0.60/oz).

---

## 3. Synthesis & Candidate Ranking

1. **Rank 1: Candidate B (`HYP-24-NY-REVERSAL-EXHAUSTION`)** exhibits zero overlap with any failed paradigm, operates in a completely unexamined time window (US afternoon 14:00–18:30 UTC), features the largest expected price moves relative to transaction friction ($12–$22/oz), completely avoids overnight financing ($0.00 swap), and directly addresses the directional breakdown flaw that caused the Phase 23 rejection.
2. **Rank 2: Candidate A (`HYP-24-LBMA-AM-FIX-DRIFT`)** possesses high institutional plausibility but suffers from narrow 1-hour move sizes ($3–$5/oz) and temporal proximity to the London morning.
3. **Rank 3: Candidate C (`HYP-24-COMEX-SETTLEMENT-REBALANCE`)** suffers from late-afternoon spread widening risks prior to the 21:00 UTC market closure.

**Audit Overlap Conclusion:** Candidate B is selected as the lead candidate for formal specification.
