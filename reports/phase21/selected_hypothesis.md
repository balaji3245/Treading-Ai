# Phase 21: Formal Specification of Selected Hypothesis

**Phase:** PHASE 21 — NEW HYPOTHESIS DISCOVERY & RESEARCH DESIGN  
**Date:** October 2026  
**Auditor / Researcher:** Quantitative Researcher & Systematic Trading Specialist  
**Selected Candidate:** **Candidate 1 — Asian Session Volatility Compression & London Opening Range Expansion**  
**Formal Hypothesis Identifier:** **`HYP-21-ASIAN-LONDON-EXPANSION`**  

---

## 1. Formal Economic Rationale

Spot gold (XAUUSD) is traded continuously across a sequence of global financial centers, each characterized by distinct participant profiles, order-flow dynamics, and liquidity depths:

1.  **The Asian Low-Liquidity Regime (00:00–07:00 UTC):**
    *   During Asian trading hours (Tokyo, Sydney, Hong Kong, Singapore), spot trading is driven predominantly by commercial bullion dealer inventory rebalancing, local physical retail flows, and minor hedge fund positioning.
    *   Institutional speculative liquidity is at its daily nadir.
    *   When the Asian session forms an unusually narrow, compressed price range, it indicates that dealer inventory is balanced and no major macroeconomic information shock has occurred.
2.  **The London Liquidity Influx & Range Expansion (07:00–12:00 UTC):**
    *   London is the historical and operational clearing center of the global wholesale gold market (LBMA), processing the vast majority of physical OTC bullion volume.
    *   Between 07:00 and 08:00 UTC, European bullion banks, institutional commodity trading advisors (CTAs), macro hedge funds, and sovereign participants commence trading.
    *   **The Invariant:** When an influx of large institutional order flow meets a market conditioned by Asian volatility compression, local dealer inventories cannot absorb the incoming volume within the narrow overnight range. Price discovery is forced outside the Asian bounds.
    *   Once a directional breakout outside the Asian range is established in early London trading, institutional dealers route orders with the prevailing momentum to seek counterparties, driving a sustained price expansion through the European morning session (07:00 to 12:00 UTC).
3.  **Why Prior Research Failed and Why This Differs:**
    *   *Prior M5 Research (Phases 1–16):* Evaluated continuous rolling indicators where spread ($0.40/oz) consumed 25%–38% of median price moves ($1.57), and rolling targets had 99% serial overlap.
    *   *Prior Macro Research (Phases 19–20B):* Evaluated daily macroeconomic changes that were already priced in by global bond markets.
    *   *HYP-21:* Focuses on an **intraday structural session-liquidity transition**. Expected London expansion moves are $\$8.00-\$14.00/\text{oz}$, against which liquid morning execution friction ($\$0.25/\text{oz}$) represents just $\approx 2.5\%$ of the move. Furthermore, the position exits at 12:00 UTC, incurring **zero overnight financing swap debits**.

---

## 2. Mathematical Formulation & Definitions

### A. Time Windows & Boundaries (Fixed UTC Standard)
*   **Asian Session Window:** $\mathcal{T}_{\text{Asia}} = [00:00, 07:00 \text{ UTC})$.
*   **London Breakout Evaluation Window:** $\mathcal{T}_{\text{London, Break}} = (07:00, 09:00 \text{ UTC}]$.
*   **Holding & Realization Window:** Trade entry timestamp to $\mathcal{T}_{\text{Exit}} = 12:00 \text{ UTC}$ Close.

### B. Feature & Range Definitions
1.  **Asian Session High and Low:**
    $$\text{High}_{\text{Asia}, d} = \max_{t \in \mathcal{T}_{\text{Asia}, d}} \text{High}_t$$
    $$\text{Low}_{\text{Asia}, d} = \min_{t \in \mathcal{T}_{\text{Asia}, d}} \text{Low}_t$$
2.  **Asian Session Range:**
    $$\text{Range}_{\text{Asia}, d} = \text{High}_{\text{Asia}, d} - \text{Low}_{\text{Asia}, d}$$
3.  **Trailing 20-Day Daily Average True Range ($\text{ATR}_{20, d}$):**
    Computed using the preceding 20 completed 23-hour daily sessions (18:00 NY to 17:00 NY):
    $$\text{ATR}_{20, d} = \frac{1}{20} \sum_{k=1}^{20} \text{TR}_{d-k}$$
    $$\text{TR}_{d-k} = \max\left(\text{High}_{d-k} - \text{Low}_{d-k}, |\text{High}_{d-k} - \text{Close}_{d-k-1}|, |\text{Low}_{d-k} - \text{Close}_{d-k-1}|\right)$$
4.  **Asian Compression Ratio ($\text{CR}_d$):**
    $$\text{CR}_d = \frac{\text{Range}_{\text{Asia}, d}}{\text{ATR}_{20, d}}$$

### C. Regime Conditioning Gate
A trading day $d$ is classified as a **Volatility Compressed Day** if and only if:
$$\text{CR}_d \le \tau_{\text{compression}}$$
Where $\tau_{\text{compression}}$ is the 25th percentile (first quartile $Q_1$) of $\text{CR}$ estimated strictly on the **Development Partition (2021–2022)** and frozen.

### D. Deterministic Signal & Breakout Rules
For any qualifying compressed day $d$, completed M5 bars $b_m \in \mathcal{T}_{\text{London, Break}}$ are monitored sequentially from 07:05 to 09:00 UTC:

*   **Long Breakout Event ($S_d = +1$):**
    Occurs on the *first* M5 bar $m^*$ where:
    $$\text{Close}_{m^*} > \text{High}_{\text{Asia}, d}$$
*   **Short Breakout Event ($S_d = -1$):**
    Occurs on the *first* M5 bar $m^*$ where:
    $$\text{Close}_{m^*} < \text{Low}_{\text{Asia}, d}$$
*   **No Breakout ($S_d = 0$):**
    If by 09:00 UTC no M5 bar has closed outside the Asian bounds $[\text{Low}_{\text{Asia}, d}, \text{High}_{\text{Asia}, d}]$, the day is marked as **No Trade** ($S_d = 0$).

### E. Execution & Liquidation Rules
*   **Entry Timestamp:** Exactly at the **Open of M5 bar $m^* + 1$** (the immediate bar following the confirmed breakout close).
*   **Entry Price:** $\text{Price}_{\text{entry}} = \text{Open}_{m^* + 1}$.
*   **Exit Timestamp:** Exactly at **12:00:00 UTC Close** (completed M5 bar ending 12:00 UTC).
*   **Exit Price:** $\text{Price}_{\text{exit}} = \text{Close}_{\text{12:00 UTC}}$.
*   **Catastrophic Stop-Loss:** If the market reverses during the holding window and crosses the opposite Asian bound (i.e. touches $\text{Low}_{\text{Asia}, d}$ for long trades or $\text{High}_{\text{Asia}, d}$ for short trades), the position is immediately liquidated at the stop level.

---

## 3. Economic & Transaction Cost Model

### A. Friction Parameters
1.  **Broker Bid-Ask Spread ($S$):** $\$0.20/\text{oz}$ round turn ($\$0.10$ entry, $\$0.10$ exit). In London morning hours (07:00–12:00 UTC), wholesale XAUUSD spreads are at their daily minimum ($0.12–$0.18 typical). $\$0.20/\text{oz}$ is a verified realistic proxy.
2.  **Slippage ($E$):** $\$0.05/\text{oz}$ round turn ($\$0.025$ entry, $\$0.025$ exit). In peak morning liquidity, market impact for standard retail/commercial lot sizes is negligible.
3.  **Overnight Financing (Swap):** **$\$0.00/\text{oz}$**. All trades are initiated between 07:05 and 09:00 UTC and closed at 12:00 UTC. No open position is maintained across the 17:00 NY (22:00 UTC) rollover.
4.  **Total Round-Turn Baseline Friction ($C_{\text{base}}$):**
    $$C_{\text{base}} = S + E = \$0.20 + \$0.05 = \mathbf{\$0.25/\text{oz}}$$

### B. Net PnL Calculation
For an active trade on day $d$:
$$\text{Gross PnL}_d = S_d \times (\text{Close}_{\text{12:00 UTC}, d} - \text{Open}_{\text{entry}, d})$$
$$\text{Net PnL}_d = \text{Gross PnL}_d - C_{\text{base}}$$

### C. Frictional Drag Comparison
*   *Phase 16 M5 Incumbent Model:* Median move = $\$2.26/\text{oz}$, Friction = $\$0.40/\text{oz} \implies$ **Friction consumed 17.7% of move**.
*   *HYP-21 London Expansion:* Expected move = $\$8.00-\$14.00/\text{oz}$, Friction = $\$0.25/\text{oz} \implies$ **Friction consumes only 1.8% to 3.1% of move**.

---

## 4. Formal Falsification & Failure Criteria

The hypothesis `HYP-21-ASIAN-LONDON-EXPANSION` will be deemed **falsified and permanently rejected** if any of the following pre-registered conditions are observed in the out-of-sample evaluation:

1.  **Economic Viability Failure:** The strategy fails to achieve an out-of-sample **Net Profit Factor $> 1.25$** after $\$0.25/\text{oz}$ baseline friction.
2.  **Negative Net Expectancy:** The mean Net PnL per active trade is $\le \$0.00/\text{oz}$ (inferior to Benchmark E).
3.  **Directional Randomness:** The directional win rate on breakout trades is $\le 52.0\%$ (failing a one-tailed binomial test against a 50% random walk at $\alpha = 0.05$).
4.  **No Regime Differentiation:** Breakout trades occurring on compressed days ($\text{CR} \le \tau$) do not produce a statistically significant higher mean return than breakout trades occurring on uncompressed days ($\text{CR} > \tau$) under a two-sample Welch's $t$-test ($p \ge 0.05$).
5.  **Cost Fragility:** The strategy produces negative net PnL under $1.5\times$ elevated costs ($C = \$0.375/\text{oz}$) or $2.0\times$ stressed costs ($C = \$0.50/\text{oz}$).
6.  **Benchmark Inferiority:** The strategy produces a lower cumulative net return than Benchmark E ($0.00).

---

## 5. Specification Governance

*   **Status:** Pre-registered conceptual specification only.
*   **Implementation Status:** NOT IMPLEMENTED. No code has been executed to generate signals or trade outcomes.
*   **Parameter Locking:** Thresholds and window definitions are conceptually fixed based on market operating hours; parameter curve-fitting is strictly forbidden.
