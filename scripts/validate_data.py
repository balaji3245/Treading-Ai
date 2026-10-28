#!/usr/bin/env python3
"""CLI script to validate raw CSV or processed Parquet market data files."""

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

# Add src to pythonpath
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from treading_ai.config import REPORTS_DIR
from treading_ai.preprocessing.storage import ParquetStorageEngine
from treading_ai.validation.validator import DataValidator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("validate_data")


def main():
    parser = argparse.ArgumentParser(description="Validate financial market OHLC dataset")
    parser.add_argument("file_path", type=Path, help="Path to CSV or Parquet file to validate")
    parser.add_argument("--timeframe-minutes", type=int, default=1, help="Expected candle duration in minutes (default: 1)")
    parser.add_argument("--dataset-name", type=str, default=None, help="Name of dataset for report")
    parser.add_argument("--reports-dir", type=Path, default=REPORTS_DIR, help="Output directory for reports")

    args = parser.parse_args()
    file_path = args.file_path
    if not file_path.exists():
        logger.error("File does not exist: %s", file_path)
        sys.exit(1)

    dataset_name = args.dataset_name or file_path.stem
    validator = DataValidator(expected_timeframe_minutes=args.timeframe_minutes)

    logger.info("Loading dataset: %s", file_path)
    if file_path.suffix.lower() == ".csv":
        df = validator.load_raw_histdata_csv(file_path)
    elif file_path.suffix.lower() == ".parquet":
        storage = ParquetStorageEngine()
        df = storage.read_candlesticks(file_path)
    else:
        logger.error("Unsupported file extension '%s'. Must be .csv or .parquet", file_path.suffix)
        sys.exit(1)

    logger.info("Running validation checks on %d rows...", len(df))
    report = validator.validate(df, dataset_name=dataset_name)

    # Save reports
    args.reports_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.reports_dir / f"validation_report_{dataset_name}.json"
    md_path = args.reports_dir / f"validation_summary_{dataset_name}.md"

    report.to_json(output_path=json_path)
    md_summary = report.to_summary_markdown()
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_summary)

    print("\n" + md_summary)
    logger.info("Machine-readable JSON report written to: %s", json_path)
    logger.info("Human-readable Markdown summary written to: %s", md_path)

    if report.overall_status == "FAILED":
        sys.exit(1)


if __name__ == "__main__":
    main()
