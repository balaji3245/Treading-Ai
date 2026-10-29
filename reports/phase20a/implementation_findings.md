# Phase 20A: Implementation Findings & Code Audit

**Document:** Implementation Findings & Code Audit  
**Target Code:** [run_phase20_macro_test.py](file:///home/bhoot/project/Treading-Ai/scripts/run_phase20_macro_test.py)  
**Protocol:** [preregistered_protocol.md](file:///home/bhoot/project/Treading-Ai/reports/phase20/preregistered_protocol.md)  
**Auditor:** Quantitative Researcher & Independent Code Auditor  

---

## 1. Finding FIND-20A-01: Benchmark F Mislabeling & Excessive Friction

### Code Reference
*   **File:** [run_phase20_macro_test.py:304](file:///home/bhoot/project/Treading-Ai/scripts/run_phase20_macro_test.py#L304)
    ```python
    df["pos_F"] = 1.0  # Buy-and-Hold
    ```
*   **Execution Loop:** [run_phase20_macro_test.py:164-166](file:///home/bhoot/project/Treading-Ai/scripts/run_phase20_macro_test.py#L164-L166)
    ```python
    gross_trade_pnls = pos * pnl
    trade_costs = np.where(active_mask, frictions, 0.0)
    net_trade_pnls = gross_trade_pnls - trade_costs
    ```
*   **Friction Definition:** [run_phase20_macro_test.py:313](file:///home/bhoot/project/Treading-Ai/scripts/run_phase20_macro_test.py#L313)
    ```python
    df["base_friction"] = 0.20 + 0.10 + swap_base
    ```

### Evidence & Mathematical Diagnosis
1.  **Turnover Multiplier Bug:** In `evaluate_trading_model`, `active_mask` is evaluated for each of the $N_{\text{oos}} = 516$ sessions. Because `pos_F == 1.0` is active every day, the code deducted $\$0.20$ spread and $\$0.10$ slippage **every single day**. Total turnover friction deducted was:
    $$\text{Turnover Friction} = 516 \times (\$0.20 + \$0.10) = \$154.80/\text{oz}$$
2.  **Definition Misalignment:** A continuous "Passive Buy-and-Hold" investor enters a single long position at the start of the out-of-sample period (2023-01-02 18:00 NY) and exits at the end (2024-12-31 17:00 NY). Such an investor incurs transaction friction **only twice** (half-turn at entry, half-turn at exit, totaling one round turn of $\$0.30/\text{oz}$).
3.  **Overnight Gap Return Omission:** Daily session returns sum only the intraday difference $\text{Close} - \text{Open}$ from 18:00 NY to 17:00 NY next day. They discard the price change between 17:00 NY and 18:00 NY (the daily rollover maintenance hour). Over 2023–2024, cumulative overnight gap return was:
    $$\Delta_{\text{gaps}} = \sum_{t=1}^{515} (\text{Open}_{t+1} - \text{Close}_t) = +\$7.554/\text{oz}$$
    Continuous Buy-and-Hold captures this move, yielding a gross return of $\$797.17/\text{oz}$, whereas Phase 20's daily sum was $\$789.61/\text{oz}$.
4.  **Net Impact:** True continuous Buy-and-Hold net PnL is:
    $$\text{Net PnL}_{\text{B\&H}} = \$797.17 - (\$0.30 + \$86.64) = \mathbf{+\$710.23/\text{oz}}$$
    Phase 20 reported **$+\$547.93/\text{oz}$**, understating the benchmark by **$\$162.30/\text{oz}$**.
5.  **Severity:** **CRITICAL (Reporting / Benchmark Integrity)**. The reported metric must be relabeled as **Daily Long-Only Strategy**.

---

## 2. Finding FIND-20A-02: Wednesday Rollover Timing Shift

### Code Reference
*   **File:** [run_phase20_macro_test.py:309-311](file:///home/bhoot/project/Treading-Ai/scripts/run_phase20_macro_test.py#L309-L311)
    ```python
    entry_day = pd.to_datetime(df["entry_ts_ny"].str[:10]).dt.day_of_week
    is_wednesday = (entry_day == 2)
    swap_base = np.where(is_wednesday, 0.36, 0.12)
    ```

### Evidence & Market Settlement Diagnosis
1.  **Spot Gold Settlement Convention:** Spot XAUUSD operates on $T+2$ business day settlement.
    *   Trades held across the **Wednesday 17:00 NY rollover** settle on Friday and roll to Monday (bridging Saturday and Sunday). Thus, positions held across Wednesday 17:00 NY incur **triple swap** ($3 \times \$0.12 = \$0.36/\text{oz}$).
2.  **Implementation Shift:**
    *   The session that closes and rolls across Wednesday 17:00 NY enters at **Tuesday 18:00 NY** (`settlement_date` is Wednesday, `settlement_dow == 2`, `entry_dow == 1`).
    *   The session entered at **Wednesday 18:00 NY** (`entry_dow == 2`, `settlement_dow == 3`) closes and rolls across Thursday 17:00 NY (rolling Monday to Tuesday settlement, which is a standard 1-day swap).
    *   Phase 20 evaluated `entry_day == 2`, debiting triple swap on Wednesday 18:00 NY entries instead of Tuesday 18:00 NY entries.
3.  **Out-of-Sample Impact:**
    *   In the 2023–2024 OOS dataset, `entry_dow == 2` has 104 sessions, while `settlement_dow == 2` has 103 sessions.
    *   For Model A: 2 triple swaps shifted onto inactive sessions, reducing corrected costs from $\$175.44$ to $\$172.80$ ($+\$2.64$ net PnL impact).
    *   For Model B: costs reduced from $\$191.04$ to $\$187.44$ ($+\$3.60$ net PnL impact).
    *   For Models C, D, F, G: costs reduced from $\$241.68$ to $\$241.44$ ($+\$0.24$ net PnL impact).
4.  **Severity:** **MODERATE (Accounting Precision)**. Does not alter the final conclusion, but represents a programmatic bug in financial accounting.

---

## 3. Finding FIND-20A-03: Short Position Swap Asymmetry

### Code Reference
*   **File:** [run_phase20_macro_test.py:165](file:///home/bhoot/project/Treading-Ai/scripts/run_phase20_macro_test.py#L165)
    ```python
    trade_costs = np.where(active_mask, frictions, 0.0)
    ```
*   **Friction Applied:** Applied identically to long positions (`pos > 0`) and short positions (`pos < 0`).

### Evidence & Institutional Analysis
1.  **Economic Reality:** Gold financing reflects the difference between USD borrowing rates (SOFR) and gold lease rates ($r_{\text{gold}} \approx 0.5\%$).
    *   Long gold: Borrow USD, buy gold $\implies$ pay SOFR, earn lease rate $\implies$ negative carry (debit).
    *   Short gold: Borrow gold, hold USD $\implies$ earn SOFR, pay lease rate $\implies$ positive or near-zero carry.
2.  **Proxy Status:** Retail CFD brokers frequently charge symmetrical financing debits due to retail financing markups. In institutional spot gold, charging a $-\$0.12/\text{oz}$ debit on shorts is an **unverified retail proxy**.
3.  **Sensitivity Analysis:** Setting short swap financing to $\$0.00/\text{oz}$:
    *   Model A Net PnL changes from $-\$294.54$ to $-\$259.38/\text{oz}$ ($\Delta = +\$35.16$).
    *   Model B Net PnL changes from $-\$75.42$ to $-\$42.06/\text{oz}$ ($\Delta = +\$33.36$).
    *   Model C Net PnL changes from $-\$81.92$ to $-\$50.12/\text{oz}$ ($\Delta = +\$31.80$).
    *   Model D Net PnL changes from $-\$258.48$ to $-\$226.44/\text{oz}$ ($\Delta = +\$32.04$).
4.  **Conclusion:** Even under zero short financing cost, all candidate models remain unprofitable.
5.  **Severity:** **LOW (Proxy Sensitivity)**.

---

## 4. Finding FIND-20A-04: Directional Accuracy Formula & Execution

### Code Reference
*   **File:** [run_phase20_macro_test.py:183-184](file:///home/bhoot/project/Treading-Ai/scripts/run_phase20_macro_test.py#L183-L184)
    ```python
    dir_matches = int((np.sign(active_pos) == np.sign(active_pnl)).sum())
    dir_acc = float(dir_matches / trades * 100.0) if trades > 0 else 0.0
    ```
*   **File:** [run_phase20_macro_test.py:340-343](file:///home/bhoot/project/Treading-Ai/scripts/run_phase20_macro_test.py#L340-L343)
    ```python
    active = (oos_data[pos_col] != 0)
    correct_dir = (np.sign(oos_data[pos_col]) == np.sign(oos_data["target_pnl_usd"]))[active]
    hit_rate = float(correct_dir.sum() / active.sum() * 100.0) if active.sum() > 0 else 0.0
    ```

### Audit Verification
1.  **Inactive Positions (`pos == 0`):** Inactive positions are strictly filtered out by boolean masking (`active`) prior to summation in both numerator and denominator.
2.  **Observation Consistency:** Numerator and denominator use the exact same subset of active observations ($N_{\text{active}} = 364$ for Model A, $396$ for Model B, $516$ for Models C & D).
3.  **Zero-Return Observations:** In the out-of-sample period, there are exactly **0 sessions** with `target_pnl_usd == 0`.
4.  **Reproduction:** Recomputed directional accuracies match Phase 20's reported figures to within floating point precision:
    *   Model A: $181 / 364 = 49.73\%$
    *   Model B: $201 / 396 = 50.76\%$
    *   Model C: $263 / 516 = 50.97\%$
    *   Model D: $265 / 516 = 51.36\%$
5.  **Severity:** **VERIFIED CORRECT**.

---

## 5. Finding FIND-20A-05: Statistical Testing Scope & Hypothesis Family

### Code Reference
*   **File:** [run_phase20_macro_test.py:411-430](file:///home/bhoot/project/Treading-Ai/scripts/run_phase20_macro_test.py#L411-L430)

### Audit Verification
1.  **Hypothesis Alignment:** The Holm-Bonferroni multiple testing adjustment was applied to the family of 4 candidate models ($M=4$) based on Pearson correlation $p$-values between continuous macro score and realized returns.
2.  **Trading Hypothesis Separation:** Phase 20 evaluated trading PnL metrics ($\text{PF} > 1.25$, $\text{Net PnL} > 0$) as deterministic gate hurdles rather than statistical null hypothesis rejections.
3.  **Correction Reproducibility:**
    *   Rank 1: Model B, $p = 0.5794 > 0.0125$ (Fail).
    *   Rank 2: Model D, $p = 0.6724 > 0.0167$ (Fail).
    *   Rank 3: Model C, $p = 0.6865 > 0.0250$ (Fail).
    *   Rank 4: Model A, $p = 0.8624 > 0.0500$ (Fail).
4.  **Severity:** **LOW (Methodological Clarity)**. Combining feature tests with trading tests was not attempted, preserving the family integrity at $M=4$.
