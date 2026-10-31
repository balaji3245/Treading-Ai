# PHASE 23 DECISION RECORD: LOCKED OUT-OF-SAMPLE EVALUATION

**Phase:** 23 — Locked Out-of-Sample Evaluation  
**Hypothesis ID:** `HYP-21-ASIAN-LONDON-EXPANSION`  
**Execution Timestamp:** 2026-10-30T03:32:00 UTC  
**Evaluation Partition:** 2023–2024 Out-of-Sample Partition  

---

## Final Formal Verdict

```
PHASE 23 VERDICT: REJECT
```

---

## 1. Executive Decision Summary

Hypothesis `HYP-21-ASIAN-LONDON-EXPANSION` is formally **REJECTED** following locked out-of-sample evaluation on the 2023–2024 partition. 

Although the implementation, data governance, and trade reconstruction were verified to be 100% bug-free and reproducible, the empirical market behavior over 2023–2024 fails the pre-registered requirements for economic viability, directional stability, and statistical significance.

---

## 2. Core Evidence Mandating Rejection

1. **Win Rate Degradation Below Random Null:**
   - In-sample win rate (2021–2022): **54.46%** (55 wins, 46 losses).
   - Out-of-sample win rate (2023–2024): **43.82%** (39 wins, 50 losses).
   - A two-sided exact binomial test against a 50% random coin-toss benchmark yields $p = 0.2891$, failing to establish any directional accuracy edge over random noise.
2. **Directional Collapse (Short Cohort Failure):**
   - Long trades: 52 trades, Net PnL = +$79.294/oz, Net PF = 1.850, Win rate = 55.77%.
   - Short trades: 37 trades, Net PnL = **-$41.933/oz**, Net PF = **0.633**, Win rate = **27.03%** (10 wins, 27 losses).
   - In 2021–2022, Long and Short trades were symmetrically profitable. In 2023–2024, the strategy's Short expansion breakouts failed catastrophically due to gold's macro secular uptrend. The strategy lacks an authentic directional expansion edge; its Long profits were merely a diluted passenger on secular macro trend drift.
3. **Statistical Uncertainty (Confidence Interval Spans Zero):**
   - Mean net expectancy per trade point estimate: +$0.420/oz.
   - Moving-block bootstrap 95% confidence interval ($B = 2,000$): **[-$0.855/oz, +$2.299/oz]**.
   - Because the lower bound is deeply negative, the hypothesis that true net expectancy is zero or negative ($\mathcal{H}_0: \mu \le 0$) **cannot be rejected**. The strategy fails to outperform the risk-free $0 no-trade baseline with statistical credibility.
4. **Drawdown Doubling:**
   - Development maximum drawdown: **$30.659/oz** (0.30%).
   - Out-of-sample maximum drawdown: **$61.558/oz** (0.61%).
5. **Execution Gap Distortion:**
   - On 4 trading days with missing 11:55 UTC bars, positions were held past the daily rollover into evening hours, generating +$62.96/oz gross.
   - When strictly capped at 12:00 UTC, out-of-sample net PnL collapses to **+$5.676/oz** at baseline friction ($0.25/oz) and becomes **negative -$5.45/oz** at 1.5× friction.

---

## 3. Compliance & Governance Directives

1. **No Live Promotion:** The strategy is rejected and will NOT be deployed or promoted to live trading.
2. **Protection of Reserved Datasets:** The protected 2025 validation (`val.parquet`) and 2026 test (`test.parquet`) partitions remain **100% locked, pristine, and untouched**. Under no circumstances should they be queried to salvage this hypothesis.
3. **No In-Flight Tweaking:** No parameter tuning (e.g. attempting to filter Short trades, slide compression thresholds, or optimize stops) is permitted on this hypothesis.
4. **Research Closure:** `HYP-21-ASIAN-LONDON-EXPANSION` is formally closed.
