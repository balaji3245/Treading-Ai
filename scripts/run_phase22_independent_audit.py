#!/usr/bin/env python3
"""Phase 22 Independent Forensic Audit Script.

Reconstructs every trade independently from raw 2021-2022 M5 data and
recalculates every metric to verify the Phase 22 development backtest.
"""

import hashlib
import json
import logging
import sys
from datetime import datetime, time, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from scipy import stats

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("Phase22IndependentAudit")

PROJECT_ROOT = Path("/home/bhoot/project/Treading-Ai")
M5_2021_PATH = PROJECT_ROOT / "data/processed/XAUUSD/M5/XAUUSD_M5_2021.parquet"
M5_2022_PATH = PROJECT_ROOT / "data/processed/XAUUSD/M5/XAUUSD_M5_2022.parquet"
VAL_PARQUET_PATH = PROJECT_ROOT / "data/features/XAUUSD_M5_features_val.parquet"
TEST_PARQUET_PATH = PROJECT_ROOT / "data/features/XAUUSD_M5_features_test.parquet"

VAL_EXPECTED_SHA256 = "7e9222e9dc0893601e24505912eeab78330670c4e70ebcc2fa462ff8d44a4f94"
TEST_EXPECTED_SHA256 = "f95fd09a5d07666e3f1d9a72e840e2e97f3c058d11b6bb0c712b21dea86a5dec"

PHASE22_TRADES_CSV = PROJECT_ROOT / "reports/phase22/development_trades.csv"
PHASE22_METRICS_JSON = PROJECT_ROOT / "reports/phase22/development_metrics.json"
AUDIT_OUTPUT_JSON = PROJECT_ROOT / "reports/phase22/audit_reconciliation.json"

FROZEN_Q1_THRESHOLD = 0.281865
COST_1_0X = 0.25
COST_1_5X = 0.375
COST_2_0X = 0.50


def compute_sha256(filepath: Path) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def verify_protected_partitions() -> Dict[str, Any]:
    val_hash = compute_sha256(VAL_PARQUET_PATH)
    test_hash = compute_sha256(TEST_PARQUET_PATH)
    return {
        "val": {"actual": val_hash, "expected": VAL_EXPECTED_SHA256, "match": val_hash == VAL_EXPECTED_SHA256},
        "test": {"actual": test_hash, "expected": TEST_EXPECTED_SHA256, "match": test_hash == TEST_EXPECTED_SHA256},
    }


def load_raw_data() -> pd.DataFrame:
    df21 = pd.read_parquet(M5_2021_PATH)
    df22 = pd.read_parquet(M5_2022_PATH)
    df = pd.concat([df21, df22], ignore_index=True)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.sort_values("timestamp").reset_index(drop=True)

    max_ts = df["timestamp"].max()
    prohibited_boundary = pd.to_datetime("2023-01-01 00:00:00", utc=True)
    if max_ts >= prohibited_boundary:
        raise ValueError(f"Prohibited partition leakage! Max TS: {max_ts}")
    return df


def independent_reconstruction(df: pd.DataFrame) -> Tuple[List[Dict[str, Any]], pd.DataFrame, Dict[str, Any]]:
    df["date_utc"] = df["timestamp"].dt.date
    df["time_utc"] = df["timestamp"].dt.time

    # 1. Daily ATR20 shifted by 1
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

    # 2. Asian session (00:00:00 to 07:00:00 UTC exclusive of 07:00)
    t_asia_start = time(0, 0, 0)
    t_asia_end = time(7, 0, 0)

    asia_df = df[(df["time_utc"] >= t_asia_start) & (df["time_utc"] < t_asia_end)]
    asia_summary = asia_df.groupby("date_utc").agg(
        asia_high=("high", "max"),
        asia_low=("low", "min"),
        asia_bars=("open", "count"),
    )
    asia_summary["asia_range"] = asia_summary["asia_high"] - asia_summary["asia_low"]

    merged = asia_summary.join(daily_cal[["atr20_prior"]], how="inner").dropna()
    merged["compression_ratio"] = merged["asia_range"] / merged["atr20_prior"]

    # Quantile audit: check empirical Q1
    q1_empirical = float(merged["compression_ratio"].quantile(0.25))

    # 3. Trade reconstruction
    t_break_start = time(7, 0, 0)
    t_break_end = time(8, 55, 0)
    t_exit = time(11, 55, 0)

    reconstructed_trades = []

    for date_val, row in merged.iterrows():
        cr = float(row["compression_ratio"])
        if cr > FROZEN_Q1_THRESHOLD:
            continue

        day_df = df[df["date_utc"] == date_val].sort_values("timestamp").reset_index(drop=True)
        asia_h = float(row["asia_high"])
        asia_l = float(row["asia_low"])

        break_bars = day_df[(day_df["time_utc"] >= t_break_start) & (day_df["time_utc"] <= t_break_end)]

        signal = 0
        trigger_idx = None
        trigger_ts = None

        for idx, b in break_bars.iterrows():
            is_l = bool(b["close"] > asia_h)
            is_s = bool(b["close"] < asia_l)

            if is_l and is_s:
                signal = 0
                break
            elif is_l:
                signal = 1
                trigger_idx = idx
                trigger_ts = b["timestamp"]
                break
            elif is_s:
                signal = -1
                trigger_idx = idx
                trigger_ts = b["timestamp"]
                break

        if signal == 0 or trigger_idx is None:
            continue

        entry_idx = trigger_idx + 1
        if entry_idx >= len(day_df):
            continue

        entry_bar = day_df.loc[entry_idx]
        entry_price = float(entry_bar["open"])
        entry_ts = entry_bar["timestamp"]
        stop_price = asia_l if signal == 1 else asia_h

        # Adverse entry gap abort
        if signal == 1 and entry_price <= stop_price:
            continue
        if signal == -1 and entry_price >= stop_price:
            continue

        holding_bars = day_df.loc[entry_idx:]
        exit_bar_series = holding_bars[holding_bars["time_utc"] == t_exit]
        exit_bar_idx = exit_bar_series.index[0] if not exit_bar_series.empty else holding_bars.index[-1]

        trade_bars = day_df.loc[entry_idx:exit_bar_idx]

        exit_price = None
        exit_reason = None
        exit_ts = None

        for _, h_bar in trade_bars.iterrows():
            # 1. Bar open gap past stop
            if signal == 1 and h_bar["open"] <= stop_price:
                exit_price = float(h_bar["open"])
                exit_reason = "STOP_GAP"
                exit_ts = h_bar["timestamp"]
                break
            if signal == -1 and h_bar["open"] >= stop_price:
                exit_price = float(h_bar["open"])
                exit_reason = "STOP_GAP"
                exit_ts = h_bar["timestamp"]
                break

            # 2. Intrabar breach of stop
            if signal == 1 and h_bar["low"] <= stop_price:
                exit_price = stop_price
                exit_reason = "STOP_LOSS"
                exit_ts = h_bar["timestamp"]
                break
            if signal == -1 and h_bar["high"] >= stop_price:
                exit_price = stop_price
                exit_reason = "STOP_LOSS"
                exit_ts = h_bar["timestamp"]
                break

            # 3. Scheduled time exit
            if h_bar["time_utc"] == t_exit:
                exit_price = float(h_bar["close"])
                exit_reason = "TIME_EXIT_1200"
                exit_ts = h_bar["timestamp"]
                break

        if exit_price is None:
            exit_price = float(trade_bars.iloc[-1]["close"])
            exit_reason = "LAST_AVAILABLE_BAR_EXIT"
            exit_ts = trade_bars.iloc[-1]["timestamp"]

        gross_pnl = float((exit_price - entry_price) * signal)
        net_10 = gross_pnl - COST_1_0X
        net_15 = gross_pnl - COST_1_5X
        net_20 = gross_pnl - COST_2_0X

        reconstructed_trades.append({
            "trade_id": len(reconstructed_trades) + 1,
            "date": str(date_val),
            "signal": int(signal),
            "direction": "LONG" if signal == 1 else "SHORT",
            "trigger_ts": str(trigger_ts),
            "entry_ts": str(entry_ts),
            "entry_price": round(entry_price, 3),
            "stop_price": round(stop_price, 3),
            "exit_ts": str(exit_ts),
            "exit_price": round(exit_price, 3),
            "exit_reason": exit_reason,
            "bars_held": int(len(trade_bars)),
            "gross_pnl_usd": round(gross_pnl, 3),
            "net_pnl_1_0x_usd": round(net_10, 3),
            "net_pnl_1_5x_usd": round(net_15, 3),
            "net_pnl_2_0x_usd": round(net_20, 3),
            "is_win_1_0x": bool(net_10 > 0),
            "asia_high": round(asia_h, 3),
            "asia_low": round(asia_l, 3),
            "asia_range": round(asia_h - asia_l, 3),
            "atr20_prior": round(float(row["atr20_prior"]), 3),
            "compression_ratio": round(cr, 6),
        })

    info = {
        "n_evaluated_days": len(merged),
        "n_compressed_days": int((merged["compression_ratio"] <= FROZEN_Q1_THRESHOLD).sum()),
        "empirical_q1": q1_empirical,
    }
    return reconstructed_trades, merged, info


def reconcile_trades(recon_trades: List[Dict[str, Any]], orig_csv_path: Path) -> Dict[str, Any]:
    orig_df = pd.read_csv(orig_csv_path)
    recon_df = pd.DataFrame(recon_trades)

    if len(orig_df) != len(recon_df):
        return {
            "reconciliation_passed": False,
            "error": f"Row count mismatch: orig={len(orig_df)}, recon={len(recon_df)}",
        }

    discrepancies = []
    columns_to_check = [
        "date", "signal", "direction", "trigger_ts", "entry_ts",
        "entry_price", "stop_price", "exit_ts", "exit_price",
        "exit_reason", "gross_pnl_usd", "net_pnl_1_0x_usd"
    ]

    for idx in range(len(orig_df)):
        r_orig = orig_df.iloc[idx]
        r_recon = recon_df.iloc[idx]
        for col in columns_to_check:
            val_o = r_orig[col]
            val_r = r_recon[col]
            if isinstance(val_o, float) or isinstance(val_r, float):
                if not np.isclose(float(val_o), float(val_r), atol=1e-3):
                    discrepancies.append({"trade_id": idx + 1, "col": col, "orig": val_o, "recon": val_r})
            else:
                if str(val_o) != str(val_r):
                    discrepancies.append({"trade_id": idx + 1, "col": col, "orig": val_o, "recon": val_r})

    return {
        "reconciliation_passed": len(discrepancies) == 0,
        "n_trades_checked": len(orig_df),
        "discrepancies_count": len(discrepancies),
        "discrepancies": discrepancies,
    }


def recompute_all_metrics(recon_trades: List[Dict[str, Any]], n_eligible: int) -> Dict[str, Any]:
    tdf = pd.DataFrame(recon_trades)
    n = len(tdf)

    def stats_for_col(col: str, cost: float):
        pnl = tdf[col].to_numpy()
        gross = tdf["gross_pnl_usd"].to_numpy()
        w = pnl[pnl > 0]
        l = pnl[pnl < 0]
        pf = float(w.sum() / -l.sum()) if len(l) > 0 and l.sum() != 0 else None
        eq = np.cumsum(pnl)
        pk = np.maximum.accumulate(eq)
        dd = pk - eq
        return {
            "gross_pnl": round(float(gross.sum()), 3),
            "net_pnl": round(float(pnl.sum()), 3),
            "total_friction": round(float(cost * n), 3),
            "expectancy": round(float(pnl.mean()), 3),
            "wins": int((pnl > 0).sum()),
            "losses": int((pnl < 0).sum()),
            "win_rate_pct": round(float((pnl > 0).sum() / n * 100), 2),
            "profit_factor": round(pf, 3) if pf else None,
            "max_drawdown_usd": round(float(dd.max()), 3),
        }

    long_tdf = tdf[tdf["direction"] == "LONG"]
    short_tdf = tdf[tdf["direction"] == "SHORT"]

    long_pnl = long_tdf["net_pnl_1_0x_usd"].to_numpy()
    short_pnl = short_tdf["net_pnl_1_0x_usd"].to_numpy()

    long_pf = float(long_pnl[long_pnl > 0].sum() / -long_pnl[long_pnl < 0].sum()) if (long_pnl < 0).sum() > 0 else None
    short_pf = float(short_pnl[short_pnl > 0].sum() / -short_pnl[short_pnl < 0].sum()) if (short_pnl < 0).sum() > 0 else None

    # Bootstrap
    rng = np.random.RandomState(42)
    pnl_10 = tdf["net_pnl_1_0x_usd"].to_numpy()
    boot_means = []
    boot_pfs = []
    k = int(np.ceil(n / 5))
    for _ in range(2000):
        starts = rng.randint(0, max(1, n - 5 + 1), size=k)
        b_idx = []
        for s in starts:
            b_idx.extend(range(s, min(s + 5, n)))
        b_idx = b_idx[:n]
        sample = pnl_10[b_idx]
        boot_means.append(float(np.mean(sample)))
        sw = sample[sample > 0].sum()
        sl = -sample[sample < 0].sum()
        if sl > 0:
            boot_pfs.append(float(sw / sl))

    ci_mean = [round(float(np.percentile(boot_means, 2.5)), 3), round(float(np.percentile(boot_means, 97.5)), 3)]
    ci_pf = [round(float(np.percentile(boot_pfs, 2.5)), 3), round(float(np.percentile(boot_pfs, 97.5)), 3)]

    # Binomial test
    binom_p = float(stats.binomtest(int((pnl_10 > 0).sum()), n, 0.5, alternative="greater").pvalue)

    return {
        "executed_trades": n,
        "eligible_days": n_eligible,
        "participation_rate": round(n / n_eligible * 100, 2),
        "long_count": len(long_tdf),
        "short_count": len(short_tdf),
        "exit_reasons": {str(k): int(v) for k, v in tdf["exit_reason"].value_counts().items()},
        "baseline_1_0x": stats_for_col("net_pnl_1_0x_usd", COST_1_0X),
        "elevated_1_5x": stats_for_col("net_pnl_1_5x_usd", COST_1_5X),
        "stressed_2_0x": stats_for_col("net_pnl_2_0x_usd", COST_2_0X),
        "long_cohort": {
            "count": len(long_tdf),
            "net_pnl": round(float(long_pnl.sum()), 3),
            "win_rate_pct": round(float((long_pnl > 0).sum() / len(long_tdf) * 100), 2),
            "profit_factor": round(long_pf, 3),
        },
        "short_cohort": {
            "count": len(short_tdf),
            "net_pnl": round(float(short_pnl.sum()), 3),
            "win_rate_pct": round(float((short_pnl > 0).sum() / len(short_tdf) * 100), 2),
            "profit_factor": round(short_pf, 3),
        },
        "uncertainty": {
            "expectancy_bootstrap_95_ci": ci_mean,
            "profit_factor_bootstrap_95_ci": ci_pf,
            "valid_pf_resamples": len(boot_pfs),
            "binom_p_value": round(binom_p, 4),
        },
    }


def main():
    logger.info("Starting Phase 22 Independent Forensic Audit...")

    # 1. Protected partition check
    parts = verify_protected_partitions()
    logger.info("Protected partitions audit: %s", parts)
    assert parts["val"]["match"] and parts["test"]["match"], "Partition check failed!"

    # 2. Raw data load
    df = load_raw_data()
    logger.info("Loaded raw development data: %d rows", len(df))

    # 3. Independent reconstruction
    recon_trades, daily_df, info = independent_reconstruction(df)
    logger.info("Independent reconstruction complete: %d trades across %d days", len(recon_trades), info["n_evaluated_days"])

    # 4. Reconciliation against existing trade log
    recon_res = reconcile_trades(recon_trades, PHASE22_TRADES_CSV)
    logger.info("Trade reconciliation result: passed=%s, discrepancies=%d", recon_res["reconciliation_passed"], recon_res["discrepancies_count"])

    # 5. Recompute all metrics
    audit_metrics = recompute_all_metrics(recon_trades, info["n_compressed_days"])
    logger.info("Recomputed metrics: Net 1.0x PnL = $%.3f, Win Rate = %.2f%%, PF = %.3f, DD = $%.3f",
                audit_metrics["baseline_1_0x"]["net_pnl"],
                audit_metrics["baseline_1_0x"]["win_rate_pct"],
                audit_metrics["baseline_1_0x"]["profit_factor"],
                audit_metrics["baseline_1_0x"]["max_drawdown_usd"])

    # 6. Save audit reconciliation
    audit_record = {
        "audit_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "protected_partitions": parts,
        "data_summary": info,
        "reconciliation": recon_res,
        "recomputed_metrics": audit_metrics,
    }

    with open(AUDIT_OUTPUT_JSON, "w") as f:
        json.dump(audit_record, f, indent=2)
    logger.info("Audit reconciliation record saved to %s", AUDIT_OUTPUT_JSON)


if __name__ == "__main__":
    main()
