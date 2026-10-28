#!/usr/bin/env python3
"""Script to generate multi-timeframe visualization plots for verification."""

import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # Headless backend for Linux terminal
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

# Add src to pythonpath
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from treading_ai.config import PROCESSED_DATA_DIR, REPORTS_DIR
from treading_ai.preprocessing.storage import ParquetStorageEngine


def main():
    parser = argparse.ArgumentParser(description="Plot sample multi-timeframe gold price data")
    parser.add_argument("--symbol", type=str, default="XAUUSD")
    parser.add_argument("--identifier", type=str, default="2026_01")
    parser.add_argument("--output", type=Path, default=REPORTS_DIR / "multi_timeframe_sample.png")

    args = parser.parse_args()
    storage = ParquetStorageEngine(base_dir=PROCESSED_DATA_DIR)

    # Load M1, M15, and H1 for a common window
    m1_path = storage.get_partition_path(args.symbol, "M1", args.identifier)
    m15_path = storage.get_partition_path(args.symbol, "M15", args.identifier)
    h1_path = storage.get_partition_path(args.symbol, "H1", args.identifier)

    if not m1_path.exists():
        print(f"Error: {m1_path} does not exist. Please run the pipeline first.")
        sys.exit(1)

    df_m1 = storage.read_candlesticks(m1_path)
    df_m15 = storage.read_candlesticks(m15_path)
    df_h1 = storage.read_candlesticks(h1_path)

    # Slice a representative 48-hour window
    start_ts = df_m1["timestamp"].iloc[100]
    end_ts = start_ts + pd.Timedelta(hours=48)

    sub_m1 = df_m1[(df_m1["timestamp"] >= start_ts) & (df_m1["timestamp"] <= end_ts)]
    sub_m15 = df_m15[(df_m15["timestamp"] >= start_ts) & (df_m15["timestamp"] <= end_ts)]
    sub_h1 = df_h1[(df_h1["timestamp"] >= start_ts) & (df_h1["timestamp"] <= end_ts)]

    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)
    fig.suptitle(f"{args.symbol} Spot Gold - Multi-Timeframe Alignment ({start_ts.strftime('%Y-%m-%d')} Window)", fontsize=14, fontweight="bold")

    # M1 plot
    axes[0].plot(sub_m1["timestamp"], sub_m1["close"], color="#2b5c8f", lw=0.9, label="M1 Close")
    axes[0].set_title(f"1-Minute (M1) Resolution - {len(sub_m1):,} bars", fontsize=11)
    axes[0].set_ylabel("Price (USD)")
    axes[0].grid(True, linestyle="--", alpha=0.5)
    axes[0].legend(loc="upper left")

    # M15 plot
    axes[1].plot(sub_m15["timestamp"], sub_m15["close"], color="#2e7d32", lw=1.2, label="M15 Close")
    axes[1].fill_between(sub_m15["timestamp"], sub_m15["low"], sub_m15["high"], color="#a5d6a7", alpha=0.4, label="M15 High-Low Range")
    axes[1].set_title(f"15-Minute (M15) Resolution - {len(sub_m15)} bars", fontsize=11)
    axes[1].set_ylabel("Price (USD)")
    axes[1].grid(True, linestyle="--", alpha=0.5)
    axes[1].legend(loc="upper left")

    # H1 plot
    axes[2].step(sub_h1["timestamp"], sub_h1["close"], where="post", color="#c62828", lw=1.5, label="H1 Close (Step)")
    axes[2].fill_between(sub_h1["timestamp"], sub_h1["low"], sub_h1["high"], step="post", color="#ef9a9a", alpha=0.4, label="H1 High-Low Range")
    axes[2].set_title(f"1-Hour (H1) Resolution - {len(sub_h1)} bars", fontsize=11)
    axes[2].set_ylabel("Price (USD)")
    axes[2].set_xlabel("Timestamp (UTC)")
    axes[2].grid(True, linestyle="--", alpha=0.5)
    axes[2].legend(loc="upper left")

    axes[2].xaxis.set_major_formatter(mdates.DateFormatter("%b %d %H:%M"))
    fig.autofmt_xdate()

    plt.tight_layout()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(args.output, dpi=150)
    plt.close()
    print(f"Sample multi-timeframe plot saved to: {args.output}")


if __name__ == "__main__":
    main()
