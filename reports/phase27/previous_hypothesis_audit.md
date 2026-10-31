# PHASE 27: PREVIOUS HYPOTHESIS AUDIT & FAILURE MODE FORENSICS

**Phase:** 27 — New Hypothesis Discovery & Research Design  
**Repository:** `Treading-Ai`  
**Execution Timestamp:** 2026-10-30T13:05:00 UTC  

---

## 1. Executive Purpose & Scope

This forensic audit examines every previous hypothesis investigated in the `Treading-Ai` project across Phases 5, 20, 22, 23, 24, 25, and 26. 

For each historical hypothesis, this document audits:
1. The proposed economic market mechanism.
2. Formal entry, exit, stop, and holding rules.
3. The observed empirical results and primary failure modes.
4. Categorization of failure: **Rejected Mechanism** vs. **Inadequate Evidence** vs. **Implementation Problem**.
5. Explicit prohibition on ideas that must not be recycled as pseudo-new strategies.

---

## 2. Hypothesis-by-Hypothesis Forensic Audit

### 2.1 Phase 5: Selective Probabilistic Threshold Policy on M5 ML Indicators

- **Hypothesis Classification:** M5 Intraday Supervised Machine Learning with Abstention Policy.
- **Proposed Market Mechanism:**
  - Technical indicators (RSI, MACD, Bollinger Bands, ATR ratios) across multiple timeframes contain non-linear predictive information about forward return direction on M5 bars.
  - Applying an abstention threshold ($\tau > 0.50$) to probabilistic classifier outputs ($P(y = +1)$ vs $P(y = -1)$) filters out low-confidence market noise, allowing selective trading only when directional edge exceeds transaction friction.
- **Operational Entry & Exit Rules:**
  - Signal generated at bar $t$ close from 232 technical features.
  - Entry at bar $t+1$ Open if $\max(P(y=+1), P(y=-1)) \ge \tau$.
  - Fixed time exit at bar $t+1+H$ Open ($H \in \{12, 24, 48, 96, 288\}$ bars).
  - Fixed round-turn friction of $0.40/oz.
- **Observed Empirical Results:**
  - Out-of-fold directional accuracy collapsed to 42.1%–45.8% (sub-random).
  - Filtering by higher probability thresholds reduced trade count exponentially but did not improve net expectancy.
  - Frictions consumed between 18% and 38% of median price moves across short horizons ($H=12$ median move was $1.57/oz vs $0.40 cost).
- **Primary Failure Mode:**
  - **The Intraday Cost Wall & Lack of Signal:** M5 technical indicators do not possess predictive power for future price returns. The signal-to-noise ratio on M5 bars is near zero. High-churn trading against fixed bid-ask spread and slippage guarantees negative expectancy.
- **Root Cause Categorization:**
  - **REJECTED MECHANISM.** Technical indicators on high-frequency intraday bars lack statistical predictive edge.
- **Non-Recycling Prohibition:**
  - Do NOT train ML classifiers (GBDT, Random Forests, Neural Nets) on technical indicators (RSI, MACD, Moving Averages) to predict continuous forward bar returns.

---

### 2.2 Phase 20 (and 20A/20B): Daily Macroeconomic Directional Regression (Models A–D)

- **Hypothesis Classification:** Daily Macroeconomic Fundamental Forecasting.
- **Proposed Market Mechanism:**
  - Gold is an unyielding monetary asset whose price is fundamentally driven by daily changes in US real interest rates (10Y TIPS yield `DFII10`), the trade-weighted US Dollar Index (`DTWEXBGS`), and 10Y inflation breakevens (`T10YIE`).
  - Daily changes in these macro variables should forecast next-session directional returns on spot gold.
- **Operational Entry & Exit Rules:**
  - Model A (Linear OLS), Model B (Ridge Regression), Model C (Logistic Sign Classifier), Model D (Macro Regime Interaction).
  - Signal calculated daily at 18:00 NY time using completed FRED macro prints.
  - Entry at next-day Asian/London open; exit at 17:00 NY close (24-hour holding duration).
  - Subjected to round-turn spread ($0.25/oz) and daily swap financing costs ($0.15–$0.40/day).
- **Observed Empirical Results (2023–2024 Evaluation, N = 516 daily sessions):**
  - Linear correlation $|r| \le 0.0244, p \ge 0.5794$ (statistically indistinguishable from white noise).
  - Linear regression $R^2 \le 0.0006$.
  - Directional accuracy 49.73% to 51.36% (failed binomial test vs 50% coin toss, $p \ge 0.28$).
  - Net PnL ranged from -$294.54/oz to -$75.42/oz (Net PF 0.895 to 0.978).
- **Primary Failure Mode:**
  - **Macro Information Lag & High Efficient Market Absorption:** Macro news is discounted within milliseconds of release on COMEX and OTC markets. Daily FRED macro prints reflect stale settlement prices. Daily differences in interest rates and FX indices provide zero directional edge for next-session gold returns.
- **Root Cause Categorization:**
  - **REJECTED MECHANISM.** Daily macro regressions have zero next-session forecastability.
- **Non-Recycling Prohibition:**
  - Do NOT construct daily linear, ridge, or sign models on FRED yield, dollar, or inflation time-series to trade daily gold direction.

---

### 2.3 Phases 21–23: Asian Compression & London Morning Expansion (`HYP-21-ASIAN-LONDON-EXPANSION`)

- **Hypothesis Classification:** Intraday Range Breakout & Volatility Expansion.
- **Proposed Market Mechanism:**
  - Physical gold liquidity is quiet during the Asian session (00:00–07:00 UTC). When the Asian range contracts relative to trailing daily volatility ($\text{CR} \le 0.281865$, the 25th percentile of ATR20), institutional liquidity entering at the London market open (07:00–08:00 UTC) triggers directional breakout expansion.
- **Operational Entry & Exit Rules:**
  - Asian range defined across 84 M5 bars (`00:00` to `06:55` UTC).
  - Breakout monitoring window: `07:05` to `09:00` UTC (24 M5 bars).
  - Entry: Next-bar Open following confirmed M5 bar close outside Asian High/Low.
  - Stop-Loss: Placed at the opposite Asian range boundary.
  - Scheduled Exit: Flat exit at 12:00:00 UTC (`11:55` M5 bar close).
- **Observed Empirical Results:**
  - *Development (2021–2022, N = 101 trades):* Net PnL +$42.44/oz, Net PF 1.263, Win Rate 54.46%. Passed development gates.
  - *Out-of-Sample Evaluation (2023–2024, N = 89 trades):* Failed completely!
    - Win rate collapsed to 43.82% (39W / 50L).
    - Catastrophic directional breakdown: Short trades collapsed to a 27.03% win rate and a Net PF of 0.633 (-$41.93/oz loss).
    - 95% bootstrap CI spanned zero: [-$0.855, +$2.299]/oz. Maximum drawdown doubled to $61.56/oz.
    - True PnL strictly capped at 12:00 UTC was only +$5.68/oz at baseline and negative at 1.5x/2.0x costs.
- **Primary Failure Mode:**
  - **False Breakout Traps & Asymmetric London Order Flow:** Range compression in Asia does not guarantee clean directional expansion in London. In London open trading, false boundary breakouts ("stop runs") frequently whip back into the Asian range. Furthermore, secular macro gold buying created persistent upward drift, rendering short breakout trades systematically unprofitable.
- **Root Cause Categorization:**
  - **REJECTED MECHANISM & REGIME INSTABILITY.** Simple session range boundary breakouts suffer severe whipsaw losses during unbacked momentum traps.
- **Non-Recycling Prohibition:**
  - Do NOT test breakouts of Asian session high/low ranges, boundary expansions, or compression ratios during London open.

---

### 2.4 Phases 24–26: New York Morning Excursion Reversal (`HYP-24-NY-REVERSAL-EXHAUSTION`)

- **Hypothesis Classification:** Intraday Macro Announcement Mean Reversion / Exhaustion Fading.
- **Proposed Market Mechanism:**
  - US morning macroeconomic announcements (8:30 AM ET / 12:30–13:30 UTC) trigger sharp, emotional market overreactions. When the morning excursion from 12:00 to 14:00 UTC exceeds the 75th percentile of daily ATR ($\text{NER} \ge 0.320210$), liquidity exhausts, allowing institutional New York dealers to absorb flow and mean-revert price back toward the 12:00 baseline before the COMEX pit close (18:30 UTC).
- **Operational Entry & Exit Rules:**
  - Consensus anchor: `11:55` UTC bar close ($P_{\text{base}}$).
  - Excursion measurement: `13:55` UTC bar close ($P_{\text{14:00}}$).
  - $\Delta P = P_{\text{14:00}} - P_{\text{base}}$; $\text{NER} = |\Delta P| / \text{ATR}_{20}^{\text{prior}}$.
  - Counter-trend entry at `14:05:00 UTC` Open (Short if $\Delta P > 0$; Long if $\Delta P < 0$).
  - Stop-Loss: Entry $\pm (0.75 \times |\Delta P|)$ (stop checked before exit on every bar).
  - Scheduled Exit: Flat exit at `18:30:00 UTC` Close (`18:25` M5 bar close).
- **Observed Empirical Results:**
  - *Development (2021–2022, N = 124 trades):* Net PnL +$178.831/oz, Net PF 1.586, Win Rate 58.06%, perfectly balanced Long (PF 1.629) and Short (PF 1.554). Passed all development gates.
  - *Historical Evaluation (2023–2024, N = 77 trades):* Complete systemic failure!
    - Net PnL collapsed to **-$178.903/oz** (Net PF 0.551).
    - Net expectancy: **-$2.323/oz** (failing the $\ge +0.50$ gate by $2.82/oz).
    - Win rate dropped to 42.86%.
    - Stop-loss hit rate surged from 18.55% in development to **38.96%** in evaluation.
    - Long trades (fading downside morning drops) collapsed completely (Win Rate 32.43%, PF 0.367, -$150.65/oz).
    - Maximum drawdown surged to **$178.903/oz** (nearly 4x the $45 gate limit).
    - Bootstrap 95% CI was strictly negative: [-$4.156, +$0.149]/oz.
- **Primary Failure Mode:**
  - **Macro Regime Shift from Range Consolidation to Secular Trend Expansion:** In 2021–2022, gold traded in a sideways consolidation range ($1,680–$2,070/oz) where dealer mean-reversion was effective. In 2023–2024, gold entered a historic secular bull market driven by structural sovereign central bank de-dollarization, the March 2023 SVB banking crisis, and Middle East geopolitical shocks. In this momentum regime, morning excursions were NOT temporary liquidity overshoots; they represented genuine institutional trend initiation. Fading morning drops resulted in catastrophic counter-trend knife-catching.
- **Root Cause Categorization:**
  - **REJECTED MECHANISM & MACRO REGIME FRAGILITY.** Counter-trend fading of morning macro moves is fatally fragile to trend persistence regimes and lacks exogenous state conditioning.
- **Non-Recycling Prohibition:**
  - Do NOT modify, tweak, recalibrate, or revive counter-trend fading of US morning announcement excursions (12:00–14:00 UTC).

---

## 3. Systematic Summary Matrix of Historical Failures

| Paradigm / Hypothesis | Timeframe & Asset | Data Partitions Examined | Mechanism Claim | Ultimate Empirical Outcome | Core Reason for Rejection |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Phase 1–16: M5 ML Indicators** | M5 XAUUSD | 2021–2022 | Technical indicators predict continuous returns | Directional accuracy 42%–45%, heavy losses | Zero signal in indicators; fixed friction wall ($0.40/oz) |
| **Phase 17–18B: Diagnostics** | M5 XAUUSD | 2021–2022 | Autocorrelation & feature redundancy diagnostics | Confirmed high collinearity, serial correlation | Structural impossibility of indicator forecasting |
| **Phase 19–20B: Daily Macro** | Daily XAUUSD | 2023–2024 | Daily FRED yields/DXY predict gold excess returns | $R^2 \le 0.0006$, Net losses -$294 to -$75/oz | Macro prints lag instant market pricing; zero edge |
| **Phase 21–23: HYP-21 Breakout** | M5 XAUUSD | 2021–2024 | Asian compression breakout in London open | OOS PF collapsed to 0.633 on Shorts; 43.8% WR | False breakout traps; asymmetric upward gold drift |
| **Phase 24–26: HYP-24 Reversal** | M5 XAUUSD | 2021–2024 | US morning announcement exhaustion reversal | Evaluation PF collapsed to 0.551; -$178.90/oz | Secular trend regime turns fading into knife-catching |

---

## 4. Methodological Lessons & Requirements for Phase 27

1. **Beware of Regime-Conditional In-Sample Illusions:** Both `HYP-21` and `HYP-24` produced attractive in-sample / development metrics in 2021–2022 (PF 1.26 and 1.58), only to fail catastrophically in 2023–2024. This confirms that 2-year periods in gold are dominated by specific macro regimes (e.g. Fed hiking cycle vs. sovereign accumulation cycle).
2. **Economic Logic Must Survive Multiple Regimes:** Any new hypothesis must possess a structural microeconomic rationale (e.g. benchmark auction hedging, volatility clustering, illiquidity settlement drift) rather than an empirical statistical curve-fit.
3. **Execution Friction Is Uncompromising:** In intraday trading, fixed costs ($0.25–$0.50/oz) compound rapidly. Hypotheses targeting small excursions ($< \$5.00/oz) or high trade frequencies ($> 150$ trades/year) will inevitably fail net economic evaluation.
4. **Strict Independence of Hypotheses:** All candidate hypotheses in Phase 27 must be structurally orthogonal to the 5 rejected paradigms detailed above.
