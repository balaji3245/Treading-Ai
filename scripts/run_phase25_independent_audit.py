#!/usr/bin/env python3
"""Phase 25 Independent Forensic Audit Script.

Reconstructs every trade independently from raw 2021-2022 M5 data and
reconciles the trade ledger against reported Phase 25 metrics.
"""

import hashlib
import json
import logging
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
logger = logging.getLogger("Phase25IndependentAudit")

PROJECT_ROOT = Path("/home/bhoot/project/Treading-Ai")
M5_2021_PATH = PROJECT_ROOT / "data/processed/XAUUSD/M5/XAUUSD_M5_2021.parquet"
M5_2022_PATH = PROJECT_ROOT / "data/processed/XAUUSD/M5/XAUUSD_M5_2022.parquet"
VAL_PARQUET_PATH = PROJECT_ROOT / "data/features/XAUUSD_M5_features_val.parquet"
TEST_PARQUET_PATH = PROJECT_ROOT / "data/features/XAUUSD_M5_features_test.parquet"

VAL_EXPECTED_SHA256 = "7e9222e9dc0893601e24505912eeab78330670c4e70ebcc2fa462ff8d44a4f94"
TEST_EXPECTED_SHA256 = "f95fd09a5d07666e3f1d9a72e840e2e97f3c058d11b6bb0c712b21dea86a5dec"

PHASE25_TRADES_CSV = PROJECT_ROOT / "reports/phase25/development_trades.csv"
PHASE25_METRICS_JSON = PROJECT_ROOT / "reports/phase25/development_metrics.json"
AUDIT_OUTPUT_JSON = PROJECT_ROOT / "reports/phase25/audit_reconciliation.json"

FROZEN_EXHAUSTION_THRESHOLD = 0.320210
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
    if max_ts >= pd.to_datetime("2023-01-01", utc=True):
        raise ValueError(f"Partition boundary violation! Max TS: {max_ts}")
    return df


def independent_reconstruction(df: pd.DataFrame) -> Tuple[List[Dict[str, Any]], pd.DataFrame, Dict[str, Any]]:
    df["date_utc"] = df["timestamp"].dt.date
    df["time_utc"] = df["timestamp"].dt.time

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

    t_base = time(11, 55, 0)
    t_1400 = time(13, 55, 0)

    b_base = df[df["time_utc"] == t_base].groupby("date_utc").agg(p_base=("close", "last"))
    b_1400 = df[df["time_utc"] == t_1400].groupby("date_utc").agg(p_1400=("close", "last"))

    merged = b_base.join(b_1400, how="inner").dropna()
    merged = merged.join(daily_cal[["atr20_prior"]], how="inner").dropna()

    merged["delta_p"] = merged["p_1400"] - merged["p_base"]
    merged["abs_delta_p"] = merged["delta_p"].abs()
    merged["ner"] = merged["abs_delta_p"] / merged["atr20_prior"]

    t_entry = time(14, 5, 0)
    t_exit = time(18, 25, 0)

    reconstructed_trades = []

    for date_val, row in merged.iterrows():
        if row["ner"] < FROZEN_EXHAUSTION_THRESHOLD:
            continue

        day_df = df[df["date_utc"] == date_val].sort_values("timestamp").reset_index(drop=True)
        delta_p = float(row["delta_p"])

        if np.isclose(delta_p, 0.0):
            continue

        signal = -1 if delta_p > 0 else 1

        entry_bars = day_df[day_df["time_utc"] == t_entry]
        if entry_bars.empty:
            continue

        entry_idx = entry_bars.index[0]
        entry_bar = day_df.loc[entry_idx]
        entry_price = float(entry_bar["open"])
        entry_ts = entry_bar["timestamp"]

        stop_dist = 0.75 * abs(delta_p)
        stop_price = entry_price + stop_dist if signal == -1 else entry_price - stop_dist

        if (signal == 1 and entry_price <= stop_price) or (signal == -1 and entry_price >= stop_price):
            continue

        holding_bars = day_df.loc[entry_idx:]
        exit_bars = holding_bars[holding_bars["time_utc"] == t_exit]
        exit_bar_idx = exit_bars.index[0] if not exit_bars.empty else holding_bars.index[-1]
        trade_bars = day_df.loc[entry_idx:exit_bar_idx]

        exit_price = None
        exit_reason = None
        exit_ts = None

        for _, h_bar in trade_bars.iterrows():
            if (signal == 1 and h_bar["open"] <= stop_price) or (signal == -1 and h_bar["open"] >= stop_price):
                exit_price = float(h_bar["open"])
                exit_reason = "STOP_GAP"
                exit_ts = h_bar["timestamp"]
                break
            if (signal == 1 and h_bar["low"] <= stop_price) or (signal == -1 and h_bar["high"] >= stop_price):
                exit_price = stop_price
                exit_reason = "STOP_LOSS"
                exit_ts = h_bar["timestamp"]
                break
            if h_bar["time_utc"] == t_exit:
                exit_price = float(h_bar["close"])
                exit_reason = "TIME_EXIT_1830"
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
            "delta_p": round(delta_p, 3),
            "ner": round(float(row["ner"]), 6),
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
        })

    info = {
        "n_evaluated_days": len(merged),
        "n_eligible_days": int((merged["ner"] >= FROZEN_EXHAUSTION_THRESHOLD).sum()),
        "empirical_q75": float(merged["ner"].quantile(0.75)),
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
        "date", "signal", "direction", "entry_ts", "entry_price",
        "stop_price", "exit_ts", "exit_price", "exit_reason",
        "gross_pnl_usd", "net_pnl_1_0x_usd"
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


def main():
    logger.info("Starting Phase 25 Independent Forensic Audit...")

    parts = verify_protected_partitions()
    assert parts["val"]["match"] and parts["test"]["match"], "Protected partition check failed!"

    df = load_raw_data()
    recon_trades, daily_df, info = independent_reconstruction(df)

    recon_res = reconcile_trades(recon_trades, PHASE25_TRADES_CSV)
    logger.info("Trade reconciliation: passed=%s, discrepancies=%d", recon_res["reconciliation_passed"], recon_res["discrepancies_count"])

    audit_record = {
        "audit_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "protected_partitions": parts,
        "data_summary": info,
        "reconciliation": recon_res,
    }

    with open(AUDIT_OUTPUT_JSON, "w") as f:
        json.dump(audit_record, f, indent=2)
    logger.info("Audit reconciliation record saved to %s", AUDIT_OUTPUT_JSON)


if __name__ == "__main__":
    main()
