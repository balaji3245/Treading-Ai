#!/usr/bin/env python3
"""Phase 27: New Hypothesis Discovery & Pre-Registered Development Experiments.

Evaluates the 5 pre-registered hypotheses on the 2021-2022 Development Partition:
1. HYP-27-VOL-SHOCK-EXPANSION
2. HYP-27-LONDON-PM-FIX-IMBALANCE
3. HYP-27-POST-COMEX-DRIFT-REVERSION
4. HYP-27-CONSECUTIVE-RANGE-MOMENTUM
5. HYP-27-MONDAY-WEEKEND-GAP-REVERSION

Strict Data Governance:
- Ingests strictly 2021-2022 development data from data/processed/XAUUSD/M5/.
- Fails closed if any timestamp >= 2023-01-01 00:00:00 UTC is present.
- Verifies cryptographic checksums of protected partitions (val.parquet and test.parquet).
- Verifies SHA-256 of frozen hypothesis_registry.md.
"""

import hashlib
import json
import logging
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from scipy import stats

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("Phase27Discovery")

PROJECT_ROOT = Path("/home/bhoot/project/Treading-Ai")
M5_2021_PATH = PROJECT_ROOT / "data/processed/XAUUSD/M5/XAUUSD_M5_2021.parquet"
M5_2022_PATH = PROJECT_ROOT / "data/processed/XAUUSD/M5/XAUUSD_M5_2022.parquet"

VAL_PARQUET_PATH = PROJECT_ROOT / "data/features/XAUUSD_M5_features_val.parquet"
TEST_PARQUET_PATH = PROJECT_ROOT / "data/features/XAUUSD_M5_features_test.parquet"

VAL_EXPECTED_SHA256 = "7e9222e9dc0893601e24505912eeab78330670c4e70ebcc2fa462ff8d44a4f94"
TEST_EXPECTED_SHA256 = "f95fd09a5d07666e3f1d9a72e840e2e97f3c058d11b6bb0c712b21dea86a5dec"

REGISTRY_PATH = PROJECT_ROOT / "reports/phase27/hypothesis_registry.md"
REGISTRY_EXPECTED_SHA256 = "e51dfffc1e42e7f8312adaeba71d31aaf4532100942d7fbc3c01ac4c6b044337"

OUTPUT_DIR = PROJECT_ROOT / "reports/phase27"
RESULTS_CSV_PATH = OUTPUT_DIR / "hypothesis_results.csv"
ALL_TRADES_CSV_PATH = OUTPUT_DIR / "all_trades.csv"
METRICS_JSON_PATH = OUTPUT_DIR / "experiment_metrics.json"

# Cost assumptions
COST_BASELINE = 0.25
COST_1_5X = 0.375
COST_2_0X = 0.50


class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        if isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (pd.Timestamp, pd.Timedelta)):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


def compute_sha256(filepath: Path) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def verify_governance() -> Dict[str, Any]:
    for name, p, exp in [("val", VAL_PARQUET_PATH, VAL_EXPECTED_SHA256), ("test", TEST_PARQUET_PATH, TEST_EXPECTED_SHA256)]:
        if not p.exists():
            raise FileNotFoundError(f"Protected partition {p} missing!")
        actual = compute_sha256(p)
        if actual != exp:
            raise ValueError(f"CRITICAL: Protected partition {name} modified! Got {actual}")

    if not REGISTRY_PATH.exists():
        raise FileNotFoundError(f"Registry {REGISTRY_PATH} missing!")
    actual_reg = compute_sha256(REGISTRY_PATH)
    if actual_reg != REGISTRY_EXPECTED_SHA256:
        raise ValueError(f"CRITICAL: Registry modified! Got {actual_reg}, expected {REGISTRY_EXPECTED_SHA256}")

    return {
        "val_sha256": VAL_EXPECTED_SHA256,
        "test_sha256": TEST_EXPECTED_SHA256,
        "registry_sha256": REGISTRY_EXPECTED_SHA256,
        "governance_verified": True,
    }


def block_bootstrap_confidence_interval(
    series: np.ndarray,
    stat_func,
    n_resamples: int = 2000,
    block_length: int = 5,
    ci_level: float = 0.95,
    seed: int = 42,
) -> Tuple[float, float, float, int]:
    n = len(series)
    if n == 0 or np.all(series == 0):
        return 0.0, 0.0, 0.0, 0

    rng = np.random.RandomState(seed)
    point_est = float(stat_func(series))
    boot_stats = []

    k = int(np.ceil(n / block_length))

    for _ in range(n_resamples):
        starts = rng.randint(0, max(1, n - block_length + 1), size=k)
        boot_idx = []
        for s in starts:
            boot_idx.extend(range(s, min(s + block_length, n)))
        boot_idx = boot_idx[:n]
        boot_sample = series[boot_idx]
        val = stat_func(boot_sample)
        if not np.isnan(val) and not np.isinf(val):
            boot_stats.append(val)

    if len(boot_stats) == 0:
        return point_est, float("nan"), float("nan"), 0

    alpha = (1.0 - ci_level) / 2.0
    lower = float(np.percentile(boot_stats, alpha * 100))
    upper = float(np.percentile(boot_stats, (1.0 - alpha) * 100))
    return point_est, lower, upper, len(boot_stats)


def load_development_data() -> Tuple[pd.DataFrame, pd.DataFrame]:
    logger.info("Loading 2021-2022 development data...")
    df21 = pd.read_parquet(M5_2021_PATH)
    df22 = pd.read_parquet(M5_2022_PATH)

    df = pd.concat([df21, df22], ignore_index=True)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.sort_values("timestamp").reset_index(drop=True)

    max_ts = df["timestamp"].max()
    prohibited_boundary = pd.to_datetime("2023-01-01 00:00:00", utc=True)
    if max_ts >= prohibited_boundary:
        raise ValueError(f"CRITICAL: Development data contains prohibited data >= 2023! Max TS: {max_ts}")

    df["date_utc"] = df["timestamp"].dt.date
    df["time_utc"] = df["timestamp"].dt.time
    df["day_of_week"] = df["timestamp"].dt.day_of_week

    # Daily calendar calculation
    daily_cal = df.groupby("date_utc").agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        n_bars=("open", "count"),
    )
    daily_cal = daily_cal[daily_cal["n_bars"] >= 100].copy()
    daily_cal["tr0"] = daily_cal["high"] - daily_cal["low"]
    daily_cal["tr1"] = (daily_cal["high"] - daily_cal["close"].shift(1)).abs()
    daily_cal["tr2"] = (daily_cal["low"] - daily_cal["close"].shift(1)).abs()
    daily_cal["tr"] = daily_cal[["tr0", "tr1", "tr2"]].max(axis=1)
    daily_cal["atr20_prior"] = daily_cal["tr"].rolling(20).mean().shift(1)

    logger.info("Loaded %d bars across %d regular daily sessions", len(df), len(daily_cal))
    return df, daily_cal


def run_strategy_backtest(
    hyp_id: str,
    df: pd.DataFrame,
    signals_df: pd.DataFrame,
    entry_time: time,
    exit_time: time,
    stop_mult: float = 0.75,
) -> List[Dict[str, Any]]:
    trades = []
    for date_val, row in signals_df.iterrows():
        direction = int(row["signal"])
        ref_delta = float(row["ref_delta"])

        day_df = df[df["date_utc"] == date_val].sort_values("timestamp").reset_index(drop=True)
        entry_bar = day_df[day_df["time_utc"] == entry_time]
        if entry_bar.empty:
            continue

        entry_idx = entry_bar.index[0]
        entry_price = float(entry_bar["open"].iloc[0])
        entry_ts = entry_bar["timestamp"].iloc[0]

        stop_dist = stop_mult * abs(ref_delta)
        stop_price = entry_price - stop_dist if direction == 1 else entry_price + stop_dist

        # Adverse entry gap abort
        if direction == 1 and entry_price <= stop_price:
            continue
        if direction == -1 and entry_price >= stop_price:
            continue

        holding = day_df.loc[entry_idx:].copy()
        exit_price = None
        exit_ts = None
        exit_reason = None
        bars_held = 0

        for _, bar in holding.iterrows():
            bars_held += 1
            b_open = float(bar["open"])
            b_high = float(bar["high"])
            b_low = float(bar["low"])
            b_close = float(bar["close"])
            b_time = bar["time_utc"]
            b_ts = bar["timestamp"]

            # Stop check
            if direction == 1:
                if b_open <= stop_price:
                    exit_price = b_open
                    exit_ts = b_ts
                    exit_reason = "STOP_GAP"
                    break
                elif b_low <= stop_price:
                    exit_price = stop_price
                    exit_ts = b_ts
                    exit_reason = "STOP_LOSS"
                    break
            else:
                if b_open >= stop_price:
                    exit_price = b_open
                    exit_ts = b_ts
                    exit_reason = "STOP_GAP"
                    break
                elif b_high >= stop_price:
                    exit_price = stop_price
                    exit_ts = b_ts
                    exit_reason = "STOP_LOSS"
                    break

            # Exit check
            if b_time == exit_time:
                exit_price = b_close
                exit_ts = b_ts
                exit_reason = "TIME_EXIT"
                break
            elif b_time > exit_time:
                exit_price = b_open
                exit_ts = b_ts
                exit_reason = "TIME_FAILSAFE"
                break

        if exit_price is None:
            last_b = holding.iloc[-1]
            exit_price = float(last_b["close"])
            exit_ts = last_b["timestamp"]
            exit_reason = "SESSION_FALLBACK"

        gross_pnl = (exit_price - entry_price) * direction
        net_10 = gross_pnl - COST_BASELINE
        net_15 = gross_pnl - COST_1_5X
        net_20 = gross_pnl - COST_2_0X

        trades.append({
            "hypothesis_id": hyp_id,
            "trade_id": len(trades) + 1,
            "date": str(date_val),
            "direction": "LONG" if direction == 1 else "SHORT",
            "ref_delta": round(ref_delta, 4),
            "entry_ts": str(entry_ts),
            "entry_price": round(entry_price, 4),
            "stop_price": round(stop_price, 4),
            "exit_ts": str(exit_ts),
            "exit_price": round(exit_price, 4),
            "exit_reason": exit_reason,
            "bars_held": bars_held,
            "gross_pnl_usd": round(gross_pnl, 4),
            "net_pnl_1_0x_usd": round(net_10, 4),
            "net_pnl_1_5x_usd": round(net_15, 4),
            "net_pnl_2_0x_usd": round(net_20, 4),
            "is_win_1_0x": bool(net_10 > 0.0),
        })

    return trades


def evaluate_hypothesis_trades(hyp_id: str, trades: List[Dict[str, Any]], min_n: int) -> Dict[str, Any]:
    if not trades:
        return {
            "hypothesis_id": hyp_id,
            "trade_count": 0,
            "decision": "REJECTED",
            "rationale": "Zero trades generated.",
        }

    df_t = pd.DataFrame(trades)
    n = len(df_t)
    net_10 = df_t["net_pnl_1_0x_usd"].to_numpy()
    gross = df_t["gross_pnl_usd"].to_numpy()

    net_sum = float(np.sum(net_10))
    avg_net = float(np.mean(net_10))
    wins = int(np.sum(net_10 > 0.0))
    losses = int(np.sum(net_10 < 0.0))
    win_rate = float(wins / n * 100.0) if n > 0 else 0.0

    gains = float(np.sum(net_10[net_10 > 0.0]))
    loss_sum = float(np.abs(np.sum(net_10[net_10 < 0.0])))
    pf = float(gains / loss_sum) if loss_sum > 0 else float("inf")

    # 1.5x and 2.0x
    net_15 = df_t["net_pnl_1_5x_usd"].to_numpy()
    net_15_sum = float(np.sum(net_15))
    gains_15 = float(np.sum(net_15[net_15 > 0.0]))
    loss_15 = float(np.abs(np.sum(net_15[net_15 < 0.0])))
    pf_15 = float(gains_15 / loss_15) if loss_15 > 0 else float("inf")

    net_20 = df_t["net_pnl_2_0x_usd"].to_numpy()
    net_20_sum = float(np.sum(net_20))
    gains_20 = float(np.sum(net_20[net_20 > 0.0]))
    loss_20 = float(np.abs(np.sum(net_20[net_20 < 0.0])))
    pf_20 = float(gains_20 / loss_20) if loss_20 > 0 else float("inf")

    # Drawdown
    cum_net = np.cumsum(net_10)
    peak = np.maximum.accumulate(np.insert(cum_net, 0, 0.0))
    dd = peak[1:] - cum_net
    max_dd = float(np.max(dd)) if len(dd) > 0 else 0.0

    # Directional sub-cohorts
    long_sub = df_t[df_t["direction"] == "LONG"]
    short_sub = df_t[df_t["direction"] == "SHORT"]
    n_long = len(long_sub)
    n_short = len(short_sub)

    def sub_pf(sub):
        if len(sub) == 0:
            return 0.0
        s_net = sub["net_pnl_1_0x_usd"].to_numpy()
        g = np.sum(s_net[s_net > 0.0])
        l = np.abs(np.sum(s_net[s_net < 0.0]))
        return float(g / l) if l > 0 else float("inf")

    long_pf = sub_pf(long_sub)
    short_pf = sub_pf(short_sub)
    long_net = float(long_sub["net_pnl_1_0x_usd"].sum()) if n_long > 0 else 0.0
    short_net = float(short_sub["net_pnl_1_0x_usd"].sum()) if n_short > 0 else 0.0

    # Bootstrap
    exp_point, exp_low, exp_high, _ = block_bootstrap_confidence_interval(
        net_10, np.mean, n_resamples=2000, block_length=5
    )

    def pf_stat(s):
        g = np.sum(s[s > 0])
        l = np.abs(np.sum(s[s < 0]))
        return g / l if l > 0 else np.nan

    pf_point, pf_low, pf_high, _ = block_bootstrap_confidence_interval(
        net_10, pf_stat, n_resamples=2000, block_length=5
    )

    # Binomial test
    binom = stats.binomtest(wins, n, p=0.5, alternative="greater")
    p_val_binom = float(binom.pvalue)

    # Promotion Gates Check
    g1_exp = bool(avg_net >= 0.50)
    g2_pf = bool(pf >= 1.25)
    g3_wr = bool(win_rate >= 50.0)
    g4_cost15 = bool(net_15_sum > 0.0)
    g5_symm = bool(long_pf >= 1.05 and short_pf >= 1.05)
    g6_sample = bool(n >= min_n)

    # Terminal Decision Logic
    if not g6_sample:
        decision = "INCONCLUSIVE"
        rationale = f"Insufficient sample size (N={n} < min_N={min_n})."
    elif not (g1_exp and g2_pf and g4_cost15 and g5_symm):
        decision = "REJECTED"
        reasons = []
        if not g1_exp:
            reasons.append(f"Expectancy ${avg_net:.3f} < $0.50")
        if not g2_pf:
            reasons.append(f"PF {pf:.3f} < 1.25")
        if not g4_cost15:
            reasons.append(f"Negative net PnL at 1.5x (${net_15_sum:.2f})")
        if not g5_symm:
            reasons.append(f"Directional asymmetry (Long PF {long_pf:.3f}, Short PF {short_pf:.3f} < 1.05)")
        rationale = "Failed development gates: " + "; ".join(reasons)
    else:
        decision = "CANDIDATE FOR FURTHER RESEARCH"
        rationale = "Satisfied all pre-registered development promotion gates."

    return {
        "hypothesis_id": hyp_id,
        "sample_size": n,
        "min_required_sample": min_n,
        "gross_pnl_usd": round(float(np.sum(gross)), 3),
        "net_pnl_1_0x_usd": round(net_sum, 3),
        "avg_net_trade_1_0x_usd": round(avg_net, 3),
        "net_profit_factor_1_0x": round(pf, 3),
        "win_rate_pct": round(win_rate, 2),
        "wins_count": wins,
        "losses_count": losses,
        "max_drawdown_usd": round(max_dd, 3),
        "net_pnl_1_5x_usd": round(net_15_sum, 3),
        "net_profit_factor_1_5x": round(pf_15, 3),
        "net_pnl_2_0x_usd": round(net_20_sum, 3),
        "net_profit_factor_2_0x": round(pf_20, 3),
        "long_trades_count": n_long,
        "short_trades_count": n_short,
        "long_net_pnl_usd": round(long_net, 3),
        "short_net_pnl_usd": round(short_net, 3),
        "long_profit_factor": round(long_pf, 3),
        "short_profit_factor": round(short_pf, 3),
        "bootstrap_exp_point": round(exp_point, 3),
        "bootstrap_exp_95_ci_lower": round(exp_low, 3),
        "bootstrap_exp_95_ci_upper": round(exp_high, 3),
        "bootstrap_pf_point": round(pf_point, 3),
        "bootstrap_pf_95_ci_lower": round(pf_low, 3),
        "bootstrap_pf_95_ci_upper": round(pf_high, 3),
        "binomial_p_val": round(p_val_binom, 4),
        "gates": {
            "gate_1_expectancy_ge_0_50": g1_exp,
            "gate_2_pf_ge_1_25": g2_pf,
            "gate_3_win_rate_ge_50": g3_wr,
            "gate_4_net_pnl_1_5x_gt_0": g4_cost15,
            "gate_5_directional_symmetry_pf_ge_1_05": g5_symm,
            "gate_6_sample_size_ge_min": g6_sample,
        },
        "decision": decision,
        "rationale": rationale,
    }


def main():
    logger.info("Executing Phase 27 Discovery Experiments...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    gov = verify_governance()
    logger.info("Governance verified: %s", gov)

    df, daily_cal = load_development_data()

    all_trades = []
    hypothesis_results = []

    # =========================================================================
    # Hypothesis 1: HYP-27-VOL-SHOCK-EXPANSION
    # =========================================================================
    logger.info("Evaluating HYP-27-VOL-SHOCK-EXPANSION...")
    asia_df = df[(df["time_utc"] >= time(0, 0, 0)) & (df["time_utc"] < time(7, 0, 0))]
    a_stats = asia_df.groupby("date_utc").agg(
        a_high=("high", "max"),
        a_low=("low", "min"),
        a_open=("open", "first"),
        a_close=("close", "last"),
    )
    a_stats["range"] = a_stats["a_high"] - a_stats["a_low"]
    a_stats["delta"] = a_stats["a_close"] - a_stats["a_open"]
    m1 = a_stats.join(daily_cal[["atr20_prior"]], how="inner").dropna()
    m1["nar"] = m1["range"] / m1["atr20_prior"]
    m1["conviction"] = m1["delta"].abs() / m1["range"]

    sig1 = m1[(m1["nar"] >= 0.50) & (m1["conviction"] >= 0.60) & (m1["delta"].abs() >= 6.0)].copy()
    sig1["signal"] = np.where(sig1["delta"] > 0, 1, -1)
    sig1["ref_delta"] = sig1["delta"]

    trades1 = run_strategy_backtest(
        "HYP-27-VOL-SHOCK-EXPANSION", df, sig1, time(8, 5, 0), time(11, 55, 0), stop_mult=0.75
    )
    res1 = evaluate_hypothesis_trades("HYP-27-VOL-SHOCK-EXPANSION", trades1, min_n=35)
    all_trades.extend(trades1)
    hypothesis_results.append(res1)

    # =========================================================================
    # Hypothesis 2: HYP-27-LONDON-PM-FIX-IMBALANCE
    # =========================================================================
    logger.info("Evaluating HYP-27-LONDON-PM-FIX-IMBALANCE...")
    p14 = df[df["time_utc"] == time(13, 55, 0)].groupby("date_utc").agg(p14=("close", "last"))
    p15 = df[df["time_utc"] == time(14, 55, 0)].groupby("date_utc").agg(p15=("close", "last"))
    m2 = p14.join(p15, how="inner").dropna().join(daily_cal[["atr20_prior"]], how="inner").dropna()
    m2["delta"] = m2["p15"] - m2["p14"]
    m2["fdr"] = m2["delta"].abs() / m2["atr20_prior"]

    sig2 = m2[(m2["fdr"] >= 0.20) & (m2["delta"].abs() >= 5.0)].copy()
    sig2["signal"] = np.where(sig2["delta"] > 0, 1, -1)
    sig2["ref_delta"] = sig2["delta"]

    trades2 = run_strategy_backtest(
        "HYP-27-LONDON-PM-FIX-IMBALANCE", df, sig2, time(15, 5, 0), time(16, 55, 0), stop_mult=0.75
    )
    res2 = evaluate_hypothesis_trades("HYP-27-LONDON-PM-FIX-IMBALANCE", trades2, min_n=60)
    all_trades.extend(trades2)
    hypothesis_results.append(res2)

    # =========================================================================
    # Hypothesis 3: HYP-27-POST-COMEX-DRIFT-REVERSION
    # =========================================================================
    logger.info("Evaluating HYP-27-POST-COMEX-DRIFT-REVERSION...")
    p_settle = df[df["time_utc"] == time(18, 25, 0)].groupby("date_utc").agg(p_settle=("close", "last"))
    p_late = df[df["time_utc"] == time(19, 55, 0)].groupby("date_utc").agg(p_late=("close", "last"))
    m3 = p_settle.join(p_late, how="inner").dropna().join(daily_cal[["atr20_prior"]], how="inner").dropna()
    m3["delta"] = m3["p_late"] - m3["p_settle"]
    m3["pdr"] = m3["delta"].abs() / m3["atr20_prior"]

    sig3 = m3[(m3["pdr"] >= 0.12) & (m3["delta"].abs() >= 3.0)].copy()
    sig3["signal"] = np.where(sig3["delta"] > 0, -1, 1)  # Counter-trend
    sig3["ref_delta"] = sig3["delta"]

    trades3 = run_strategy_backtest(
        "HYP-27-POST-COMEX-DRIFT-REVERSION", df, sig3, time(20, 5, 0), time(21, 55, 0), stop_mult=0.75
    )
    res3 = evaluate_hypothesis_trades("HYP-27-POST-COMEX-DRIFT-REVERSION", trades3, min_n=60)
    all_trades.extend(trades3)
    hypothesis_results.append(res3)

    # =========================================================================
    # Hypothesis 4: HYP-27-CONSECUTIVE-RANGE-MOMENTUM
    # =========================================================================
    logger.info("Evaluating HYP-27-CONSECUTIVE-RANGE-MOMENTUM...")
    daily_cal["tr_prior"] = daily_cal["tr"].shift(1)
    p07 = df[df["time_utc"] == time(6, 55, 0)].groupby("date_utc").agg(p07=("close", "last"))
    p09 = df[df["time_utc"] == time(8, 55, 0)].groupby("date_utc").agg(p09=("close", "last"))
    m4 = p07.join(p09, how="inner").dropna().join(daily_cal[["tr_prior", "atr20_prior"]], how="inner").dropna()
    m4["delta"] = m4["p09"] - m4["p07"]
    m4["lir"] = m4["delta"].abs() / m4["atr20_prior"]

    sig4 = m4[(m4["tr_prior"] > m4["atr20_prior"]) & (m4["lir"] >= 0.20) & (m4["delta"].abs() >= 5.0)].copy()
    sig4["signal"] = np.where(sig4["delta"] > 0, 1, -1)
    sig4["ref_delta"] = sig4["delta"]

    trades4 = run_strategy_backtest(
        "HYP-27-CONSECUTIVE-RANGE-MOMENTUM", df, sig4, time(9, 5, 0), time(15, 55, 0), stop_mult=0.75
    )
    res4 = evaluate_hypothesis_trades("HYP-27-CONSECUTIVE-RANGE-MOMENTUM", trades4, min_n=40)
    all_trades.extend(trades4)
    hypothesis_results.append(res4)

    # =========================================================================
    # Hypothesis 5: HYP-27-MONDAY-WEEKEND-GAP-REVERSION
    # =========================================================================
    logger.info("Evaluating HYP-27-MONDAY-WEEKEND-GAP-REVERSION...")
    fri_df = df[df["day_of_week"] == 4]
    fri_dates = sorted(fri_df["date_utc"].unique())

    sig5_records = []
    for f_d in fri_dates:
        m_d = f_d + timedelta(days=3)
        f_rows = fri_df[fri_df["date_utc"] == f_d]
        if f_rows.empty:
            continue
        f_close = float(f_rows.iloc[-1]["close"])

        m_rows = df[df["date_utc"] == m_d]
        if m_rows.empty:
            continue

        b_0200 = m_rows[m_rows["time_utc"] == time(1, 55, 0)]
        if b_0200.empty:
            continue
        p_0200 = float(b_0200["close"].iloc[0])

        if m_d not in daily_cal.index or pd.isna(daily_cal.loc[m_d, "atr20_prior"]):
            continue
        atr = float(daily_cal.loc[m_d, "atr20_prior"])
        gap = p_0200 - f_close
        gap_ratio = abs(gap) / atr

        if gap_ratio >= 0.15 and abs(gap) >= 3.50:
            sig5_records.append({
                "date_utc": m_d,
                "signal": -1 if gap > 0 else 1,
                "ref_delta": gap,
            })

    if sig5_records:
        sig5 = pd.DataFrame(sig5_records).set_index("date_utc")
        trades5 = run_strategy_backtest(
            "HYP-27-MONDAY-WEEKEND-GAP-REVERSION", df, sig5, time(2, 5, 0), time(6, 55, 0), stop_mult=0.75
        )
    else:
        trades5 = []

    res5 = evaluate_hypothesis_trades("HYP-27-MONDAY-WEEKEND-GAP-REVERSION", trades5, min_n=25)
    all_trades.extend(trades5)
    hypothesis_results.append(res5)

    # =========================================================================
    # Multiple Hypothesis Testing Adjustment (Holm-Bonferroni across m=5)
    # =========================================================================
    logger.info("Applying Holm-Bonferroni correction across m=5 hypotheses...")
    p_vals = [r.get("binomial_p_val", 1.0) for r in hypothesis_results]
    sorted_indices = np.argsort(p_vals)
    m = len(hypothesis_results)
    alpha = 0.05

    for rank, idx in enumerate(sorted_indices):
        hb_threshold = alpha / (m - rank)
        p = p_vals[idx]
        sig_hb = bool(p <= hb_threshold)
        hypothesis_results[idx]["holm_bonferroni"] = {
            "rank": rank + 1,
            "raw_p_value": p,
            "hb_threshold": round(hb_threshold, 5),
            "is_significant_after_hb": sig_hb,
        }

    # Save all trades CSV
    df_all_trades = pd.DataFrame(all_trades)
    df_all_trades.to_csv(ALL_TRADES_CSV_PATH, index=False)
    logger.info("Saved %d total trades across 5 hypotheses to %s", len(df_all_trades), ALL_TRADES_CSV_PATH)

    # Save summary results CSV
    summary_rows = []
    for r in hypothesis_results:
        summary_rows.append({
            "hypothesis_id": r["hypothesis_id"],
            "sample_size": r.get("sample_size", 0),
            "net_pnl_1_0x_usd": r.get("net_pnl_1_0x_usd", 0.0),
            "avg_net_trade_usd": r.get("avg_net_trade_1_0x_usd", 0.0),
            "net_profit_factor": r.get("net_profit_factor_1_0x", 0.0),
            "win_rate_pct": r.get("win_rate_pct", 0.0),
            "max_drawdown_usd": r.get("max_drawdown_usd", 0.0),
            "net_pnl_1_5x_usd": r.get("net_pnl_1_5x_usd", 0.0),
            "long_pf": r.get("long_profit_factor", 0.0),
            "short_pf": r.get("short_profit_factor", 0.0),
            "binomial_p_val": r.get("binomial_p_val", 1.0),
            "hb_significant": r.get("holm_bonferroni", {}).get("is_significant_after_hb", False),
            "decision": r["decision"],
            "rationale": r["rationale"],
        })
    df_summary = pd.DataFrame(summary_rows)
    df_summary.to_csv(RESULTS_CSV_PATH, index=False)
    logger.info("Saved hypothesis results summary to %s", RESULTS_CSV_PATH)

    # Save metrics JSON
    with open(METRICS_JSON_PATH, "w") as f:
        json.dump({
            "phase": "PHASE 27: NEW HYPOTHESIS DISCOVERY & PRE-REGISTERED EXPERIMENTS",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "governance": gov,
            "hypothesis_results": hypothesis_results,
        }, f, indent=2, cls=NpEncoder)
    logger.info("Saved complete metrics JSON to %s", METRICS_JSON_PATH)


if __name__ == "__main__":
    main()
