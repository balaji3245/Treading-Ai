#!/usr/bin/env python3
"""End-to-end pipeline runner for Treading-AI Phase 1.

Orchestrates historical download, raw validation, multi-timeframe resampling,
Parquet storage, and validation reporting.
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path

# Add src to pythonpath
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from treading_ai.config import (
    HISTDATA_DEFAULT_SYMBOL,
    PROCESSED_DATA_DIR,
    RAW_DATA_DIR,
    REPORTS_DIR,
)
from treading_ai.data_collection.downloader import HistDataDownloader
from treading_ai.preprocessing.resampler import TimeframeResampler
from treading_ai.preprocessing.storage import ParquetStorageEngine
from treading_ai.validation.validator import DataValidator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("pipeline_runner")


def main():
    parser = argparse.ArgumentParser(description="Run end-to-end Treading-AI historical data pipeline")
    parser.add_argument("--year", type=int, default=2026, help="Year to process (default: 2026)")
    parser.add_argument("--month", type=int, default=1, help="Month to process (default: 1 for Jan 2026)")
    parser.add_argument("--symbol", type=str, default=HISTDATA_DEFAULT_SYMBOL, help="Symbol (default: XAUUSD)")
    parser.add_argument("--force", action="store_true", help="Force re-download even if files exist")
    parser.add_argument(
        "--h4-alignment",
        type=str,
        choices=["session", "utc"],
        default="session",
        help="H4 candle alignment strategy: 'session' (NY 17:00 close / 22:00 UTC) or 'utc' (00:00 UTC)",
    )
    parser.add_argument(
        "--clean-duplicates",
        action="store_true",
        help="Deduplicate identical timestamps during downstream resampling while preserving raw files intact",
    )

    args = parser.parse_args()
    batch_id = f"{args.year}_{args.month:02d}" if args.month is not None else str(args.year)

    start_clock = time.time()
    print("=" * 80)
    print(f"  TREADING-AI: PHASE 1 HISTORICAL DATA PIPELINE RUNNER")
    print(f"  Instrument: {args.symbol} (Spot Gold) | Target Period: {batch_id} | H4 Alignment: {args.h4_alignment}")
    print("=" * 80)

    # Step 1: Download raw data
    logger.info("=== STEP 1: Ingesting Historical Data ===")
    downloader = HistDataDownloader(output_dir=RAW_DATA_DIR)
    metadata = downloader.download_xauusd_m1(
        year=args.year,
        month=args.month,
        symbol=args.symbol,
        force=args.force,
    )
    raw_csv_path = RAW_DATA_DIR / metadata["files"]["extracted_csv_name"]
    logger.info("Raw CSV located at: %s (Size: %.2f MB)", raw_csv_path, raw_csv_path.stat().st_size / (1024 * 1024))

    # Step 2: Validate raw data
    logger.info("=== STEP 2: Validating Raw Data Integrity ===")
    validator = DataValidator(expected_timeframe_minutes=1)
    df_m1 = validator.load_raw_histdata_csv(raw_csv_path)

    raw_report = validator.validate(df_m1, dataset_name=f"{args.symbol}_M1_{batch_id}")
    json_report_path = REPORTS_DIR / f"validation_report_{args.symbol}_M1_{batch_id}.json"
    md_report_path = REPORTS_DIR / f"validation_summary_{args.symbol}_M1_{batch_id}.md"

    raw_report.to_json(output_path=json_report_path)
    with open(md_report_path, "w", encoding="utf-8") as f:
        f.write(raw_report.to_summary_markdown())

    logger.info("Raw validation status: %s (Errors: %d, Warnings: %d)", raw_report.overall_status, raw_report.error_count, raw_report.warning_count)
    if raw_report.duplicate_timestamps_count > 0:
        if raw_report.conflicting_duplicates_count > 0:
            logger.error(
                "Raw data contains %d conflicting duplicate timestamps with differing OHLCV values! "
                "Conflicting rows cannot be silently removed. Manual investigation required. Aborting.",
                raw_report.conflicting_duplicates_count,
            )
            sys.exit(1)

        if args.clean_duplicates:
            before_len = len(df_m1)
            df_m1 = df_m1.drop_duplicates(subset=["timestamp"], keep="first").sort_values("timestamp").reset_index(drop=True)
            logger.warning(
                "Deterministic deduplication applied: removed %d identical duplicate rows (%d unique timestamps). "
                "0 conflicting prices detected. Raw CSV preserved untouched.",
                before_len - len(df_m1),
                raw_report.identical_duplicates_count,
            )
        else:
            logger.error(
                "Raw data contains %d duplicate timestamps (%d identical, 0 conflicting). "
                "Run with --clean-duplicates to apply deterministic deduplication for downstream processing.",
                raw_report.duplicate_timestamps_count,
                raw_report.identical_duplicates_count,
            )
            sys.exit(1)

    if raw_report.non_positive_prices_count > 0 or raw_report.high_low_violations_count > 0:
        logger.error("Data price integrity failure! Please check %s", json_report_path)
        sys.exit(1)

    # Step 3: Resample to target timeframes
    logger.info("=== STEP 3: Multi-Timeframe Resampling (M1, M5, M15, M30, H1, H4) [H4: %s] ===", args.h4_alignment)
    resampler = TimeframeResampler(h4_alignment=args.h4_alignment)
    multi_tf = resampler.resample_all_timeframes(df_m1)

    # Step 4: Write Parquet storage
    logger.info("=== STEP 4: Parquet Storage Export ===")
    storage = ParquetStorageEngine(base_dir=PROCESSED_DATA_DIR)

    parquet_paths = {}
    print("\n" + "-" * 80)
    print(f"{'Timeframe':<10} | {'Candles':<10} | {'Complete':<10} | {'Parquet Size':<15} | {'Filename'}")
    print("-" * 80)

    total_parquet_bytes = 0
    for tf, df_tf in multi_tf.items():
        out_path = storage.write_candlesticks(
            df=df_tf,
            symbol=args.symbol,
            timeframe=tf,
            identifier=batch_id,
            custom_metadata={
                "source": "HistData.com",
                "instrument": "XAU/USD",
                "base_timeframe": "M1",
                "target_timeframe": tf,
                "timezone": "UTC",
            },
        )
        parquet_paths[tf] = out_path
        fsize = out_path.stat().st_size
        total_parquet_bytes += fsize
        complete_count = int(df_tf["is_complete"].sum())
        print(f"{tf:<10} | {len(df_tf):<10,d} | {complete_count:<10,d} | {fsize / 1024.0:<12.1f} KB | {out_path.name}")

    print("-" * 80)

    # Measure disk usage
    elapsed = time.time() - start_clock
    raw_size_mb = raw_csv_path.stat().st_size / (1024 * 1024)
    proc_size_mb = total_parquet_bytes / (1024 * 1024)

    print("\n" + "=" * 80)
    print("  PIPELINE EXECUTION SUMMARY")
    print("=" * 80)
    print(f"Total M1 Candles Processed: {len(df_m1):,d}")
    print(f"Date Range (UTC):           {df_m1['timestamp'].iloc[0]} to {df_m1['timestamp'].iloc[-1]}")
    print(f"Raw CSV Disk Size:          {raw_size_mb:.2f} MB")
    print(f"Total Parquet Disk Size:    {proc_size_mb:.2f} MB (Compression ratio: {raw_size_mb / max(proc_size_mb, 0.001):.1f}x)")
    print(f"Elapsed Time:               {elapsed:.2f} seconds")
    print(f"Validation Report:          {md_report_path}")
    print("=" * 80)


if __name__ == "__main__":
    main()
