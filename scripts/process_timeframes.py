#!/usr/bin/env python3
"""CLI script to process raw M1 CSV data into multi-timeframe Parquet datasets."""

import argparse
import logging
import sys
from pathlib import Path

# Add src to pythonpath
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from treading_ai.config import HISTDATA_DEFAULT_SYMBOL, PROCESSED_DATA_DIR
from treading_ai.preprocessing.resampler import TimeframeResampler
from treading_ai.preprocessing.storage import ParquetStorageEngine
from treading_ai.validation.validator import DataValidator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("process_timeframes")


def main():
    parser = argparse.ArgumentParser(description="Process raw M1 CSV into multi-timeframe Parquet datasets")
    parser.add_argument("raw_csv_path", type=Path, help="Path to raw HistData M1 CSV file")
    parser.add_argument("--symbol", type=str, default=HISTDATA_DEFAULT_SYMBOL, help="Symbol identifier (default: XAUUSD)")
    parser.add_argument("--identifier", type=str, required=True, help="Batch identifier (e.g. 2026_01)")
    parser.add_argument("--output-dir", type=Path, default=PROCESSED_DATA_DIR, help="Destination directory for processed Parquet")
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
        help="Deduplicate identical timestamps during resampling while preserving raw files intact",
    )

    args = parser.parse_args()
    if not args.raw_csv_path.exists():
        logger.error("Raw CSV file not found: %s", args.raw_csv_path)
        sys.exit(1)

    validator = DataValidator(expected_timeframe_minutes=1)
    logger.info("Loading and parsing raw CSV: %s", args.raw_csv_path)
    df_m1 = validator.load_raw_histdata_csv(args.raw_csv_path)

    logger.info("Loaded %d M1 raw records from %s to %s (UTC)", len(df_m1), df_m1['timestamp'].iloc[0], df_m1['timestamp'].iloc[-1])

    # Validate raw data before processing
    report = validator.validate(df_m1, dataset_name=f"{args.symbol}_M1_{args.identifier}")
    if report.duplicate_timestamps_count > 0:
        if report.conflicting_duplicates_count > 0:
            logger.error(
                "Raw data contains %d conflicting duplicate timestamps with differing OHLCV values! "
                "Conflicting rows cannot be silently removed. Manual investigation required. Aborting.",
                report.conflicting_duplicates_count,
            )
            sys.exit(1)

        if args.clean_duplicates:
            before_len = len(df_m1)
            df_m1 = df_m1.drop_duplicates(subset=["timestamp"], keep="first").sort_values("timestamp").reset_index(drop=True)
            logger.warning(
                "Deterministic deduplication applied: removed %d identical duplicate rows (%d unique timestamps). "
                "0 conflicting prices detected. Raw CSV preserved untouched.",
                before_len - len(df_m1),
                report.identical_duplicates_count,
            )
        else:
            logger.error(
                "Raw data contains %d duplicate timestamps (%d identical, 0 conflicting). "
                "Run with --clean-duplicates to apply deterministic deduplication for downstream processing.",
                report.duplicate_timestamps_count,
                report.identical_duplicates_count,
            )
            sys.exit(1)

    if report.non_positive_prices_count > 0 or report.high_low_violations_count > 0:
        logger.error("Raw data price integrity failed! Errors: %d. Aborting processing.", report.error_count)
        sys.exit(1)

    resampler = TimeframeResampler(h4_alignment=args.h4_alignment)
    logger.info("Resampling into timeframes: M1, M5, M15, M30, H1, H4 (H4 alignment: %s)...", args.h4_alignment)
    multi_tf = resampler.resample_all_timeframes(df_m1)

    storage = ParquetStorageEngine(base_dir=args.output_dir)

    print("\n--- Processed Timeframe Summary ---")
    print(f"{'Timeframe':<10} | {'Candles':<10} | {'Complete':<10} | {'Parquet Size':<15} | {'Path'}")
    print("-" * 80)

    for tf, df_tf in multi_tf.items():
        out_path = storage.write_candlesticks(
            df=df_tf,
            symbol=args.symbol,
            timeframe=tf,
            identifier=args.identifier,
            custom_metadata={
                "source": "HistData.com",
                "instrument": "XAU/USD",
                "base_timeframe": "M1",
                "target_timeframe": tf,
                "timezone": "UTC",
            },
        )
        size_kb = out_path.stat().st_size / 1024.0
        complete_count = int(df_tf["is_complete"].sum()) if "is_complete" in df_tf.columns else len(df_tf)
        print(f"{tf:<10} | {len(df_tf):<10,d} | {complete_count:<10,d} | {size_kb:<12.1f} KB | {out_path.name}")

    print("-" * 80)
    logger.info("All timeframes successfully exported to: %s", args.output_dir)


if __name__ == "__main__":
    main()
