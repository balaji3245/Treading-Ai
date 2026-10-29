#!/usr/bin/env python3
"""CLI Script to run the Feature Engineering Pipeline for Treading-AI.

Extracts technical indicators, time/session encodings, and aligns higher-timeframe
features with strict zero-lookahead causality. Partitions output into strict
chronological train/val/test datasets in `data/features/`.
"""

import argparse
import logging
import sys
import time
from pathlib import Path

# Add src to sys.path if not present
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from treading_ai.config import FEATURES_DATA_DIR, HISTDATA_DEFAULT_SYMBOL
from treading_ai.features.pipeline import FeaturePipeline
from treading_ai.preprocessing.storage import ParquetStorageEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("build_features")


def parse_args():
    parser = argparse.ArgumentParser(description="Treading-AI Feature Engineering CLI")
    parser.add_argument(
        "--symbol",
        type=str,
        default=HISTDATA_DEFAULT_SYMBOL,
        help=f"Instrument symbol (default: {HISTDATA_DEFAULT_SYMBOL})",
    )
    parser.add_argument(
        "--base-timeframe",
        type=str,
        default="M5",
        help="Base timeframe for feature extraction (default: M5)",
    )
    parser.add_argument(
        "--htf-timeframes",
        nargs="+",
        default=["H1", "H4"],
        help="Higher timeframes to align onto base timeframe (default: H1 H4)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(FEATURES_DATA_DIR),
        help=f"Output directory for feature Parquet files (default: {FEATURES_DATA_DIR})",
    )
    parser.add_argument(
        "--include-incomplete",
        action="store_true",
        help="Include incomplete edge candles (default: False, filters incomplete)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    start_time = time.time()

    logger.info("=" * 70)
    logger.info("Treading-AI: Phase 2 Feature Engineering Execution")
    logger.info("=" * 70)
    logger.info("Symbol:             %s", args.symbol)
    logger.info("Base Timeframe:     %s", args.base_timeframe)
    logger.info("Higher Timeframes:  %s", args.htf_timeframes)
    logger.info("Filter Incomplete:  %s", not args.include_incomplete)
    logger.info("Output Directory:   %s", args.output_dir)
    logger.info("=" * 70)

    storage = ParquetStorageEngine()
    pipeline = FeaturePipeline(
        storage=storage,
        output_dir=Path(args.output_dir),
    )

    try:
        splits, metadata = pipeline.build_features(
            symbol=args.symbol,
            base_timeframe=args.base_timeframe,
            htf_timeframes=args.htf_timeframes,
            filter_incomplete=not args.include_incomplete,
            save_to_disk=True,
        )
    except Exception as e:
        logger.error("Feature engineering failed: %s", e, exc_info=True)
        sys.exit(1)

    elapsed = time.time() - start_time
    logger.info("=" * 70)
    logger.info("FEATURE ENGINEERING RUN COMPLETE (Elapsed: %.2f seconds)", elapsed)
    logger.info("=" * 70)
    logger.info("Total Engineered Features: %d", metadata.total_features_count)
    logger.info("Initial Warm-up Dropped:   %d rows", metadata.warmup_dropped_rows)
    logger.info("Split Row Counts:")
    logger.info("  - Train:      %d rows (%s to %s)", metadata.train_rows, metadata.train_start, metadata.train_end)
    logger.info("  - Validation: %d rows (%s to %s)", metadata.val_rows, metadata.val_start, metadata.val_end)
    logger.info("  - Test:       %d rows (%s to %s)", metadata.test_rows, metadata.test_start, metadata.test_end)
    
    # Audit zero NaNs and Infinities
    for split_name in ["train", "val", "test"]:
        df_split = splits[split_name]
        feat_cols = metadata.feature_names
        n_nans = df_split[feat_cols].isna().sum().sum()
        n_infs = (~df_split[feat_cols].apply(lambda s: s.between(-1e12, 1e12))).sum().sum()
        logger.info(
            "Split '%s' Quality Audit: NaNs=%d, Out-of-Bounds/Infs=%d (Status: %s)",
            split_name,
            n_nans,
            n_infs,
            "PASS" if n_nans == 0 and n_infs == 0 else "FAIL",
        )

    logger.info("=" * 70)


if __name__ == "__main__":
    main()
