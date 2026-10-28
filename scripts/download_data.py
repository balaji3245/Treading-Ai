#!/usr/bin/env python3
"""CLI script to download historical XAUUSD data from HistData with provenance tracking."""

import argparse
import json
import logging
import sys
from pathlib import Path

# Add src to pythonpath
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from treading_ai.config import HISTDATA_DEFAULT_SYMBOL, RAW_DATA_DIR
from treading_ai.data_collection.downloader import HistDataDownloader

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("download_data")


def main():
    parser = argparse.ArgumentParser(description="Download historical XAUUSD spot data from HistData.com")
    parser.add_argument("--year", type=int, required=True, help="Year to download (e.g., 2024, 2026)")
    parser.add_argument("--month", type=int, default=None, help="Month to download (1-12, required for current year)")
    parser.add_argument("--symbol", type=str, default=HISTDATA_DEFAULT_SYMBOL, help="Symbol (default: XAUUSD)")
    parser.add_argument("--output-dir", type=Path, default=RAW_DATA_DIR, help="Destination directory for raw data")
    parser.add_argument("--force", action="store_true", help="Force re-download even if already cached")

    args = parser.parse_args()

    downloader = HistDataDownloader(output_dir=args.output_dir)
    try:
        logger.info("Starting historical data download for %s, year=%s, month=%s", args.symbol, args.year, args.month)
        metadata = downloader.download_xauusd_m1(
            year=args.year,
            month=args.month,
            symbol=args.symbol,
            force=args.force,
        )
        print("\nDownload Complete. Provenance Metadata:")
        print(json.dumps(metadata, indent=2))
    except Exception as e:
        logger.error("Download failed: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
