#!/usr/bin/env python3
"""CLI script to synchronize multi-period historical data and generate coverage reports."""

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional, Tuple

# Add src to pythonpath
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from treading_ai.config import HISTDATA_DEFAULT_SYMBOL, RAW_DATA_DIR, REPORTS_DIR
from treading_ai.data_collection.orchestrator import HistoricalDataOrchestrator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("sync_data")


def main():
    parser = argparse.ArgumentParser(description="Synchronize historical market data and compile coverage report")
    parser.add_argument("--symbol", type=str, default=HISTDATA_DEFAULT_SYMBOL, help="Symbol (default: XAUUSD)")
    parser.add_argument("--years", type=int, nargs="+", default=[2026], help="Years to sync (e.g. 2024 2025 2026)")
    parser.add_argument(
        "--months",
        type=int,
        nargs="+",
        default=None,
        help="Specific months (1-12). If omitted for 2026, defaults to months 1-12. For completed years, defaults to annual archive.",
    )
    parser.add_argument("--force", action="store_true", help="Force re-download even if cached and verified")
    parser.add_argument("--raw-dir", type=Path, default=RAW_DATA_DIR, help="Raw data directory")
    parser.add_argument("--reports-dir", type=Path, default=REPORTS_DIR, help="Reports directory")

    args = parser.parse_args()

    # Build target periods list
    periods: List[Tuple[int, Optional[int]]] = []
    for y in args.years:
        if y < 2026:
            # Completed year: download as full annual archive
            periods.append((y, None))
        else:
            # Current year: monthly archives
            months_to_run = args.months or list(range(1, 13))
            for m in months_to_run:
                periods.append((y, m))

    orchestrator = HistoricalDataOrchestrator(
        raw_dir=args.raw_dir,
        reports_dir=args.reports_dir,
    )

    logger.info("Starting synchronization of %d requested periods for %s...", len(periods), args.symbol)
    report = orchestrator.sync_coverage(periods=periods, symbol=args.symbol, force=args.force)

    print("\n" + report.to_markdown())
    print("=" * 80)
    print(f"Total Periods Requested: {report.total_requested}")
    print(f"Total Available:         {report.total_available}")
    print(f"Total Unavailable:       {report.total_unavailable}")
    print(f"Total Failed:            {report.total_failed}")
    print(f"Total M1 Candles:        {report.total_m1_rows:,}")
    print(f"Coverage Reports Saved:  {args.reports_dir / f'coverage_report_{args.symbol}.md'}")
    print("=" * 80)


if __name__ == "__main__":
    main()
