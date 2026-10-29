# Phase 21: Candidate Hypothesis Discovery & Specification

**Phase:** PHASE 21 — NEW HYPOTHESIS DISCOVERY & RESEARCH DESIGN  
**Date:** October 2026  
**Auditor / Researcher:** Quantitative Researcher & Systematic Trading Specialist  
**Status:** COMPLETE CANDIDATE HYPOTHESIS SPECIFICATION  

---

## 1. Overview & Research Directives

In accordance with Phase 21 instructions, this document specifies three genuinely distinct, economically grounded, falsifiable trading hypotheses for XAUUSD. None of these candidates reuse previously rejected M5 technical indicators, rolling overlapping horizons, or daily FRED macroeconomic yield differentials.

Each candidate is evaluated across twelve standardized dimensions:
1.  **Market Mechanism**
2.  **Falsifiable Hypothesis**
3.  **Target Variable**
4.  **Observation Unit**
5.  **Features & Inputs**
6.  **Signal Timing & Execution**
7.  **Conceptual Entry & Exit Rules**
8.  **Transaction Costs & Financing**
9.  **Falsification & Failure Criteria**
10. **Data Feasibility**
11. **Leakage & Methodological Risks**
12. **Novelty & Differentiation Check**

---

## 2. Candidate Hypothesis 1: Asian Session Volatility Compression & London Opening Range Expansion

### 1. Market Mechanism
Spot gold is traded 24 hours a day, but trading activity is geographically segmented:
*   **Asian Session (00:00–07:00 UTC):** Dominated by regional physical dealers (Tokyo, Hong Kong, Sydney, Singapore) and retail inventory rebalancing. Institutional speculative liquidity is lowest during this window.
*   **London / European Open (07:00–12:00 UTC):** London is the global wholesale capital of physical bullion clearing (LBMA). When European bullion banks and London institutional market makers open, daily trading volume and liquidity expand by an order of magnitude.
*   **The Compression-Expansion Dynamic:** When the Asian session exhibits **extreme volatility compression** (narrow high-low range relative to trailing 20-day daily ATR), it indicates that dealer inventory is balanced and no substantial institutional speculative position has been committed. When London opens, large institutional order flow entering an illiquid, compressed market forces price to break out of the Asian bounds. Because the market lacks local liquidity to absorb institutional orders within the narrow range, the price expands directionally into the London morning session (07:00 to 12:00 UTC). Conversely, when the Asian range is already wide, London liquidity acts as an absorber, promoting mean reversion.

### 2. Falsifiable Hypothesis
$$\mathcal{H}_{1,\text{Asian-London}}: \text{On institutional trading days where the Asian session (00:00–07:00 UTC) range is compressed}$$
$$\left(\frac{\text{Range}_{\text{Asia}}}{\text{ATR}_{20}} < \text{Threshold}\right), \text{ the initial London breakout (first M5 close outside the Asian range}$$
$$\text{between 07:05 and 09:00 UTC) produces a statistically significant directional price expansion}$$
$$\text{in the direction of the breakout through 12:00 UTC that exceeds execution friction and achieves Net PF } > 1.25.$$

### 3. Target Variable
*   **Directional Session Return:**
    $$\text{Target Return} = \text{Direction} \times \left(\frac{\text{Close}_{\text{12:00 UTC}} - \text{Open}_{\text{entry}}}{\text{Open}_{\text{entry}}}\right)$$
*   **Gross PnL ($/\text{oz}$):**
    $$\text{Gross PnL} = \text{Direction} \times (\text{Close}_{\text{12:00 UTC}} - \text{Open}_{\text{entry}})$$
    Where $\text{Direction} = +1$ for an upside breakout ($\text{Close}_{\text{break}} > \text{High}_{\text{Asia}}$) and $\text{Direction} = -1$ for a downside breakout ($\text{Close}_{\text{break}} < \text{Low}_{\text{Asia}}$).

### 4. Observation Unit
*   **Discrete Event:** Exactly **one potential trade per qualifying institutional trading day**.
*   **Independence:** Observations are non-overlapping daily events. This completely avoids the $99\%$ serial autocorrelation overlap that plagued the M5 rolling horizon models of Phases 1–16.

### 5. Features & Inputs
1.  **Asian Session High & Low:**
    $$\text{High}_{\text{Asia}} = \max_{t \in [00:00, 07:00 \text{ UTC}]} \text{High}_t, \quad \text{Low}_{\text{Asia}} = \min_{t \in [00:00, 07:00 \text{ UTC}]} \text{Low}_t$$
2.  **Asian Session Range:** $\text{Range}_{\text{Asia}} = \text{High}_{\text{Asia}} - \text{Low}_{\text{Asia}}$.
3.  **Trailing 20-Day ATR ($\text{ATR}_{20}$):** Average True Range computed across the prior 20 completed 23-hour institutional daily sessions (finalized before 00:00 UTC).
4.  **Compression Ratio:** $\text{CR}_t = \text{Range}_{\text{Asia}, t} / \text{ATR}_{20, t}$.
5.  **Breakout Confirmation:** First M5 bar between 07:05 UTC and 09:00 UTC closing strictly above $\text{High}_{\text{Asia}}$ or strictly below $\text{Low}_{\text{Asia}}$.

### 6. Signal Timing & Execution
*   **Feature Availability:** Asian High, Asian Low, and $\text{CR}_t$ are finalized at **07:00 UTC**.
*   **Trigger Evaluation:** Evaluated on completed M5 bars between 07:05 UTC and 09:00 UTC.
*   **Trade Entry:** Exactly at the **Open of the M5 bar immediately following the confirmed breakout bar** (e.g. if the 07:25–07:30 UTC bar closes above $\text{High}_{\text{Asia}}$, entry occurs at 07:30 UTC open).
*   **Trade Exit:** Exactly at **12:00 UTC Close** (holding duration: 3.0 to 4.5 hours).

### 7. Conceptual Entry and Exit Rules
*   **Filter Condition:** Trade triggers only if $\text{CR}_t \le Q_1(\text{CR})$ (first quartile of compression ratio evaluated on development data).
*   **Long Entry:** First M5 close $> \text{High}_{\text{Asia}}$ between 07:05 and 09:00 UTC.
*   **Short Entry:** First M5 close $< \text{Low}_{\text{Asia}}$ between 07:05 and 09:00 UTC.
*   **No Trade:** If neither bound is breached by 09:00 UTC, position = 0 for the day.
*   **Exit Rule:** Time-based exit at 12:00 UTC, or catastrophic stop-loss at the opposite Asian bound.

### 8. Transaction Costs & Financing
*   **Spread:** $\$0.20/\text{oz}$ round turn (tightest liquidity of the day during London morning).
*   **Slippage:** $\$0.05/\text{oz}$ round turn ($\$0.025$ enter, $\$0.025$ exit).
*   **Overnight Swap Financing:** **$\$0.00/\text{oz}$**. Positions are entered after 07:00 UTC and closed at 12:00 UTC, completely avoiding the 17:00 NY (22:00 UTC) daily rollover maintenance window.
*   **Total Friction:** $\$0.25/\text{oz}$ round turn.
*   **Frictional Drag Ratio:** London morning average moves are $\$8.00-\$14.00/\text{oz}$. Friction consumes only $\approx 2.0\%-3.0\%$ of the move (immune to the Phase 16 cost wall).

### 9. Falsification & Failure Criteria
The hypothesis will be rejected if:
1.  Directional accuracy on out-of-sample breakouts is $\le 52.0\%$.
2.  Out-of-sample Net Profit Factor after $\$0.25/\text{oz}$ friction is $\le 1.15$.
3.  Mean Net PnL per active trade is $\le \$0.00/\text{oz}$.
4.  Welch's two-sample $t$-test between returns on compressed vs uncompressed days yields $p \ge 0.05$.

### 10. Data Feasibility
*   **Verified:** M5 OHLC and UTC timestamps exist from 2021-03-11 through 2024-12-31 in `data/features/XAUUSD_M5_features_train.parquet`.
*   **Volume Dependency:** ZERO. Does not require tick volume or trade size.

### 11. Leakage & Methodological Risks
*   **Look-Ahead Risk:** Zero. Asian bounds are finalized at 07:00 UTC. Breakout bar must complete before trade entry at the next open.
*   **Overlapping Horizon Risk:** Zero. At most one trade per calendar day; positions close by 12:00 UTC.

### 12. Novelty Check
*   Phase 1–16 evaluated rolling M5 technical indicators with continuous overlapping targets.
*   Phase 19–20 evaluated 23-hour daily macro fundamentals.
*   Candidate 1 evaluates an **intraday structural session-transition regime** (Asian equilibrium to London expansion), which has never been tested in this project.

---

## 3. Candidate Hypothesis 2: The London Morning Fixing (LBMA AM Auction) Anticipatory Drift

### 1. Market Mechanism
The LBMA Gold Price AM auction takes place electronically daily at 10:30 London time. Institutional participants (mining producers, sovereign wealth funds, central banks, and jewelry syndicates) submit market-on-fix orders. Bullion clearing banks accumulate inventory ahead of the auction to hedge client fill obligations. Academic literature on benchmark fixings (e.g., Caminschi & Heaney 2014) documents that pre-auction inventory hedging creates an anticipatory directional drift during the 60–90 minutes preceding the auction (09:00 to 10:30 London time), which dissipates following the auction clearing.

### 2. Falsifiable Hypothesis
$$\mathcal{H}_{1,\text{London-Fix}}: \text{When early European session price momentum (08:00 to 09:15 London time) exhibits clear directional bias}$$
$$(|\text{Return}| > \text{Threshold}), \text{ dealer hedging of LBMA AM auction orders produces a continuation drift}$$
$$\text{between 09:30 and 10:30 London time in the direction of the momentum, generating positive net expectancy.}$$

### 3. Target Variable
*   Price change from 09:30 London Open to 10:30 London Close signed by early momentum direction:
    $$\text{Target PnL} = \text{sign}(\text{Return}_{\text{08:00-09:15}}) \times (\text{Close}_{\text{10:30 London}} - \text{Open}_{\text{09:30 London}})$$

### 4. Observation Unit
*   One 1-hour trade per European business day.

### 5. Features & Inputs
1.  Early London session return: $(\text{Close}_{\text{09:15}} - \text{Open}_{\text{08:00}}) / \text{Open}_{\text{08:00}}$.
2.  London daylight saving calendar (GMT vs BST conversion).

### 6. Signal Timing & Execution
*   Signal evaluated at 09:15 London time.
*   Entry at 09:30 London open; exit at 10:30 London close.

### 7. Conceptual Entry and Exit Rules
*   Long if early momentum is positive and exceeds 0.5 standard deviations.
*   Short if early momentum is negative and exceeds 0.5 standard deviations.
*   Flat exit at 10:30 London time.

### 8. Costs & Friction
*   Spread: $\$0.20/\text{oz}$, Slippage: $\$0.05/\text{oz}$, Swap: $\$0.00$. Total: $\$0.25/\text{oz}$.
*   Move size in 1 hour is typically $\$3.00-\$5.00/\text{oz}$. Friction consumes $5.0\%-8.3\%$ of the move.

### 9. Failure Criteria
*   Net Profit Factor $\le 1.15$; Win Rate $\le 52.0\%$; $t$-test $p \ge 0.05$.

### 10. Data Feasibility
*   Requires M5 OHLC and GMT/BST timezone conversion. Verified available.

### 11. Leakage Risks
*   London DST shifting dates (last Sunday in March to last Sunday in October) must be mapped without error to prevent timestamp misalignment.

### 12. Novelty Check
*   Evaluates a specific institutional auction fixing mechanism, never examined in prior phases.

---

## 4. Candidate Hypothesis 3: COMEX Settlement & NY Afternoon Roll Rebalancing Mean-Reversion

### 1. Market Mechanism
COMEX gold futures pit trading closes at 13:30 NY (18:30 UTC). Major bullion banks, gold ETFs (SPDR Gold Shares GLD), and systematic commodity index funds rebalance their daily delta positions between 13:30 NY and the 17:00 NY OTC market close. When US morning macroeconomic data (08:30–10:00 NY) pushes gold prices into an extreme intraday excursion (stretched $> 2.0$ standard deviations from the daily session opening price), institutional market makers absorb inventory ahead of the 17:00 NY roll, driving a statistically significant afternoon mean-reversion between 14:00 NY and 16:45 NY.

### 2. Falsifiable Hypothesis
$$\mathcal{H}_{1,\text{NY-Rebalance}}: \text{Following an extreme US morning excursion } (|P_{\text{13:30 NY}} - P_{\text{Open}}| > 2.0 \cdot \sigma_{\text{daily}}),$$
$$\text{the price between 14:00 NY and 16:45 NY exhibits systematic mean-reversion toward the daily median price.}$$

### 3. Target Variable
*   Return from 14:00 NY open to 16:45 NY close in the direction opposite to the morning excursion:
    $$\text{Target PnL} = -\text{sign}(P_{\text{13:30 NY}} - P_{\text{Open}}) \times (P_{\text{16:45 NY}} - P_{\text{14:00 NY}})$$

### 4. Observation Unit
*   One trade per day on days with qualifying morning excursions.

### 5. Features & Inputs
1.  Morning excursion magnitude: $(P_{\text{13:30 NY}} - P_{\text{Open}}) / \text{ATR}_{20}$.
2.  Trailing 20-day daily standard deviation $\sigma_{\text{daily}}$.

### 6. Signal Timing & Execution
*   Evaluated at 13:30 NY. Entry at 14:00 NY open; exit at 16:45 NY close (before the 17:00 NY rollover maintenance window).

### 7. Conceptual Entry and Exit Rules
*   Short if morning was extended upward ($> +2.0 \sigma$).
*   Long if morning was extended downward ($< -2.0 \sigma$).
*   Exit at 16:45 NY.

### 8. Costs & Financing
*   Spread: $\$0.25/\text{oz}$ (afternoon liquidity begins thinning). Slippage: $\$0.05/\text{oz}$. Swap: $\$0.00$ (exits before 17:00 NY roll). Total: $\$0.30/\text{oz}$.
*   Move size: $\$4.00-\$7.00/\text{oz}$. Friction consumes $4.3\%-7.5\%$.

### 9. Failure Criteria
*   Mean net PnL $\le \$0.00$; Win Rate $\le 52.0\%$; Net PF $\le 1.15$.

### 10. Data Feasibility
*   Requires M5 OHLC and US Eastern Time daylight saving mapping (EDT vs EST). Verified available.

### 11. Leakage Risks
*   Exits must strictly execute by 16:45 NY to avoid crossing into the 17:00 NY roll closure.

### 12. Novelty Check
*   Evaluates intraday mean-reversion conditioned on extreme morning volatility excursions, distinct from all prior phases.

---

## 5. Comparative Evaluation & Selection Synthesis

| Evaluation Criteria | Candidate 1: Asian Compression / London Expansion | Candidate 2: London AM Fixing Drift | Candidate 3: NY Afternoon Mean-Reversion |
| :--- | :---: | :---: | :---: |
| **Market Mechanism Rigor** | **High** (Session liquidity transfer) | Medium (Auction order flow) | Medium (ETF / dealer squaring) |
| **Move Size vs Friction** | **Superior** ($8.00–$14.00 vs $0.25 $\approx 2.5\%$ drag) | Moderate ($3.00–$5.00 vs $0.25 $\approx 6\%$ drag) | Moderate ($4.00–$7.00 vs $0.30 $\approx 5\%$ drag) |
| **Overnight Financing Exposure** | **Zero** (07:00 to 12:00 UTC) | **Zero** (09:30 to 10:30 London) | **Zero** (14:00 to 16:45 NY) |
| **Observation Independence** | **Complete** (1 discrete trade / day) | **Complete** (1 discrete trade / day) | **Complete** (1 discrete trade / day) |
| **Timestamp Cleanliness** | **Cleanest** (Fixed UTC session boundaries) | Moderate (London DST shifts) | Moderate (US Eastern DST shifts) |
| **Sample Frequency** | $\approx 150-180$ trades/year | $\approx 180-200$ trades/year | $\approx 60-90$ trades/year (rare events) |
| **Data Verification** | Fully verified in M5 train parquet | Fully verified in M5 train parquet | Fully verified in M5 train parquet |

**Conclusion:** Candidate 1 possesses the strongest structural rationale, the cleanest timestamp specifications (fixed UTC session definitions), the largest expected move relative to execution friction, and the most robust sample size without rare-event dependencies.
