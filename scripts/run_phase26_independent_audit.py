#!/usr/bin/env python3
"""Phase 26: Independent Forensic Audit & Clean-Room Trade Reconciliation.

Independent Audit Tasks:
1. Cryptographically verify protected partitions (val.parquet and test.parquet) and frozen protocol.
2. Read raw 2023-2024 M5 parquet datasets without importing backtest modules.
3. Independently recompute calendar daily bars, True Range, shifted ATR20, anchor/excursion prices, and NER.
4. Independently simulate all trade entries, stop-loss checks, gap handling, and scheduled exits.
5. Perform an exhaustive line-by-line reconciliation against evaluation_trades.csv.
6. Generate audit_reconciliation.json.
"""

import hashlib
import json
import logging
from datetime import datetime, time, timezone
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("Phase26IndependentAudit")

PROJECT_ROOT = Path("/home/bhoot/project/Treading-Ai")
M5_2023_PATH = PROJECT_ROOT / "data/processed/XAUUSD/M5/XAUUSD_M5_2023.parquet"
M5_2024_PATH = PROJECT_ROOT / "data/processed/XAUUSD/M5/XAUUSD_M5_2024.parquet"

VAL_PARQUET_PATH = PROJECT_ROOT / "data/features/XAUUSD_M5_features_val.parquet"
TEST_PARQUET_PATH = PROJECT_ROOT / "data/features/XAUUSD_M5_features_test.parquet"

VAL_EXPECTED_SHA256 = "7e9222e9dc0893601e24505912eeab78330670c4e70ebcc2fa462ff8d44a4f94"
TEST_EXPECTED_SHA256 = "f95fd09a5d07666e3f1d9a72e840e2e97f3c058d11b6bb0c712b21dea86a5dec"
PROTOCOL_PATH = PROJECT_ROOT / "reports/phase24/frozen_evaluation_protocol.md"
PROTOCOL_EXPECTED_SHA256 = "eac50d9fb79e8a3bfaa25a0be463c4dc778ea12f442e5cd6a2b88bfcd898cb18"

TRADES_CSV_PATH = PROJECT_ROOT / "reports/phase26/evaluation_trades.csv"
AUDIT_RECONCILIATION_PATH = PROJECT_ROOT / "reports/phase26/audit_reconciliation.json"

FROZEN_THRESHOLD = 0.320210
ROUND_TURN_FRICTION = 0.25


def compute_sha256(filepath: Path) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def run_clean_room_reconstruction() -> List[Dict[str, Any]]:
    logger.info("Executing clean-room reconstruction from raw parquet...")
    df23 = pd.read_parquet(M5_2023_PATH)
    df24 = pd.read_parquet(M5_2024_PATH)
    df = pd.concat([df23, df24], ignore_index=True)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.sort_values("timestamp").reset_index(drop=True)

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
    t_entry = time(14, 5, 0)
    t_exit = time(18, 25, 0)

    b_base = df[df["time_utc"] == t_base].groupby("date_utc").agg(p_base=("close", "last"))
    b_1400 = df[df["time_utc"] == t_1400].groupby("date_utc").agg(p_1400=("close", "last"))

    merged = b_base.join(b_1400, how="inner").dropna()
    merged = merged.join(daily_cal[["atr20_prior"]], how="inner").dropna()

    merged["delta_p"] = merged["p_1400"] - merged["p_base"]
    merged["ner"] = merged["delta_p"].abs() / merged["atr20_prior"]

    reconstructed_trades = []

    for date_val, row in merged.iterrows():
        if row["ner"] < FROZEN_THRESHOLD:
            continue

        day_df = df[df["date_utc"] == date_val].sort_values("timestamp").reset_index(drop=True)
        delta_p = float(row["delta_p"])
        if np.isclose(delta_p, 0.0):
            continue

        direction = -1 if delta_p > 0 else 1
        dir_str = "SHORT" if direction == -1 else "LONG"

        entry_bar = day_df[day_df["time_utc"] == t_entry]
        if entry_bar.empty:
            continue

        entry_idx = entry_bar.index[0]
        entry_price = float(entry_bar["open"].iloc[0])
        entry_ts = entry_bar["timestamp"].iloc[0]

        stop_dist = 0.75 * abs(delta_p)
        stop_price = entry_price + stop_dist if direction == -1 else entry_price - stop_dist

        holding_bars = day_df.loc[entry_idx:].copy()
        exit_price = None
        exit_ts = None
        exit_reason = None
        bars_held = 0

        for _, bar in holding_bars.iterrows():
            bars_held += 1
            b_open = float(bar["open"])
            b_high = float(bar["high"])
            b_low = float(bar["low"])
            b_close = float(bar["close"])
            b_time = bar["time_utc"]
            b_ts = bar["timestamp"]

            # Stop-first check
            if direction == -1:
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
            else:
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

            # Scheduled time exit
            if b_time == t_exit:
                exit_price = b_close
                exit_ts = b_ts
                exit_reason = "TIME_EXIT_1830"
                break
            elif b_time > t_exit:
                exit_price = b_open
                exit_ts = b_ts
                exit_reason = "TIME_EXIT_FAILSAFE"
                break

        if exit_price is None:
            last_b = holding_bars.iloc[-1]
            exit_price = float(last_b["close"])
            exit_ts = last_b["timestamp"]
            exit_reason = "SESSION_CLOSE_FALLBACK"

        gross_pnl = (exit_price - entry_price) * direction
        net_10 = gross_pnl - ROUND_TURN_FRICTION

        reconstructed_trades.append({
            "date": str(date_val),
            "direction": dir_str,
            "entry_ts": str(entry_ts),
            "entry_price": round(entry_price, 4),
            "stop_price": round(stop_price, 4),
            "exit_ts": str(exit_ts),
            "exit_price": round(exit_price, 4),
            "exit_reason": exit_reason,
            "gross_pnl_usd": round(gross_pnl, 4),
            "net_pnl_1_0x_usd": round(net_10, 4),
        })

    return reconstructed_trades


def reconcile_trades(reconstructed: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not TRADES_CSV_PATH.exists():
        raise FileNotFoundError(f"Evaluation trades CSV {TRADES_CSV_PATH} not found!")

    df_backtest = pd.read_csv(TRADES_CSV_PATH)
    n_expected = len(df_backtest)
    n_recon = len(reconstructed)

    discrepancies = []

    if n_expected != n_recon:
        discrepancies.append(f"Trade count mismatch: expected {n_expected}, reconstructed {n_recon}")

    for idx, r_trade in enumerate(reconstructed):
        if idx >= n_expected:
            discrepancies.append(f"Extra reconstructed trade at index {idx}: {r_trade}")
            continue

        b_row = df_backtest.iloc[idx]

        # Check key fields
        if r_trade["date"] != str(b_row["date"]):
            discrepancies.append(f"Trade {idx+1} date mismatch: {r_trade['date']} vs {b_row['date']}")
        if r_trade["direction"] != str(b_row["direction"]):
            discrepancies.append(f"Trade {idx+1} direction mismatch: {r_trade['direction']} vs {b_row['direction']}")
        if not np.isclose(r_trade["entry_price"], float(b_row["entry_price"]), atol=1e-4):
            discrepancies.append(f"Trade {idx+1} entry price mismatch: {r_trade['entry_price']} vs {b_row['entry_price']}")
        if not np.isclose(r_trade["exit_price"], float(b_row["exit_price"]), atol=1e-4):
            discrepancies.append(f"Trade {idx+1} exit price mismatch: {r_trade['exit_price']} vs {b_row['exit_price']}")
        if r_trade["exit_reason"] != str(b_row["exit_reason"]):
            discrepancies.append(f"Trade {idx+1} exit reason mismatch: {r_trade['exit_reason']} vs {b_row['exit_reason']}")
        if not np.isclose(r_trade["gross_pnl_usd"], float(b_row["gross_pnl_usd"]), atol=1e-4):
            discrepancies.append(f"Trade {idx+1} gross PnL mismatch: {r_trade['gross_pnl_usd']} vs {b_row['gross_pnl_usd']}")
        if not np.isclose(r_trade["net_pnl_1_0x_usd"], float(b_row["net_pnl_1_0x_usd"]), atol=1e-4):
            discrepancies.append(f"Trade {idx+1} net PnL mismatch: {r_trade['net_pnl_1_0x_usd']} vs {b_row['net_pnl_1_0x_usd']}")

    passed = len(discrepancies) == 0
    return {
        "reconciliation_passed": passed,
        "n_trades_checked": n_expected,
        "n_trades_reconstructed": n_recon,
        "discrepancies_count": len(discrepancies),
        "discrepancies": discrepancies,
    }


def main():
    logger.info("Starting Phase 26 Independent Forensic Audit...")

    val_hash = compute_sha256(VAL_PARQUET_PATH)
    test_hash = compute_sha256(TEST_PARQUET_PATH)
    proto_hash = compute_sha256(PROTOCOL_PATH)

    val_match = (val_hash == VAL_EXPECTED_SHA256)
    test_match = (test_hash == TEST_EXPECTED_SHA256)
    proto_match = (proto_hash == PROTOCOL_EXPECTED_SHA256)

    if not (val_match and test_match and proto_match):
        raise ValueError("CRITICAL: Partition or protocol checksum mismatch during independent audit!")

    reconstructed = run_clean_room_reconstruction()
    recon_results = reconcile_trades(reconstructed)

    audit_record = {
        "audit_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "protected_partitions": {
            "val": {"actual": val_hash, "expected": VAL_EXPECTED_SHA256, "match": val_match},
            "test": {"actual": test_hash, "expected": TEST_EXPECTED_SHA256, "match": test_match},
            "protocol": {"actual": proto_hash, "expected": PROTOCOL_EXPECTED_SHA256, "match": proto_match},
        },
        "reconciliation": recon_results,
    }

    with open(AUDIT_RECONCILIATION_PATH, "w") as f:
        json.dump(audit_record, f, indent=2)

    logger.info("Saved audit reconciliation to %s", AUDIT_RECONCILIATION_PATH)
    if recon_results["reconciliation_passed"]:
        logger.info("AUDIT PASSED: All %d trades matched perfectly with 0 discrepancies.", recon_results["n_trades_checked"])
    else:
        logger.error("AUDIT FAILED: %d discrepancies found!", recon_results["discrepancies_count"])


if __name__ == "__main__":
    main()
