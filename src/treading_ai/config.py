"""Configuration module for Treading-AI data pipeline."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List
import os


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
FEATURES_DATA_DIR = DATA_DIR / "features"
REPORTS_DIR = PROJECT_ROOT / "reports"

# Ensure essential local runtime directories exist
for _dir in [DATA_DIR, RAW_DATA_DIR, PROCESSED_DATA_DIR, FEATURES_DATA_DIR, REPORTS_DIR]:
    _dir.mkdir(parents=True, exist_ok=True)

# Standardized column definitions
OHLC_COLUMNS: List[str] = ["timestamp", "open", "high", "low", "close", "volume"]

# Supported Timeframes and their Pandas Resampling Frequency Strings
TIMEFRAME_FREQ_MAP: Dict[str, str] = {
    "M1": "1min",
    "M5": "5min",
    "M15": "15min",
    "M30": "30min",
    "H1": "1h",
    "H4": "4h",
    "D1": "1D",
}

# Expected M1 constituent candle count per higher timeframe bar
TIMEFRAME_M1_COUNT: Dict[str, int] = {
    "M1": 1,
    "M5": 5,
    "M15": 15,
    "M30": 30,
    "H1": 60,
    "H4": 240,
    "D1": 1380,
}

# HistData Source Specifics
HISTDATA_DEFAULT_SYMBOL = "XAUUSD"
HISTDATA_BASE_URL = os.getenv("HISTDATA_BASE_URL", "https://www.histdata.com")
HISTDATA_DOWNLOAD_ENDPOINT = os.getenv("HISTDATA_DOWNLOAD_URL", "https://www.histdata.com/get.php")
# Timezone Provenance: HistData timestamps originate from an interbank feeder aligned to European DST
# (Europe/London local time - 5 hours: UTC-5 in European winter, UTC-4 in European summer).
HISTDATA_TIMEZONE = "Europe/London-5h"
HISTDATA_CSV_SEP = ";"
HISTDATA_CSV_COLUMNS = ["datetime_str", "open", "high", "low", "close", "volume"]
HISTDATA_DATETIME_FORMAT = "%Y%m%d %H%M%S"

# Market Schedule Constraints (in UTC):
# Spot gold market closes Friday at 17:00 New York Time:
# - Winter (EST): closes Friday ~22:00 UTC, opens Sunday ~23:00 UTC (Daily roll break ~22:00-23:00 UTC)
# - Summer (EDT): closes Friday ~21:00 UTC, opens Sunday ~22:00 UTC (Daily roll break ~21:00-22:00 UTC)
WEEKEND_CLOSE_DAY_UTC = 4  # Friday (Monday=0 ... Sunday=6)
WEEKEND_CLOSE_HOUR_UTC = 22
WEEKEND_OPEN_DAY_UTC = 6   # Sunday
WEEKEND_OPEN_HOUR_UTC = 23
DAILY_ROLL_START_HOUR_UTC = 22
DAILY_ROLL_END_HOUR_UTC = 23

# Performance / Hardware constraints (Dell Latitude 5410, 16GB RAM, CPU-only)
CHUNK_SIZE_ROWS = int(os.getenv("CHUNK_SIZE_ROWS", "100000"))
DEFAULT_PARQUET_COMPRESSION = "snappy"

# Quarantined raw datasets (excluded from production Parquet processing due to conflicting raw feeder records)
QUARANTINED_PERIODS: List[str] = ["2026_06", "2026_07", "2026_08", "2026_09", "2026_10"]

# Strict Temporal Split Boundaries for Machine Learning (Phase 2)
# Enforces chronological separation to eliminate future lookahead leakage
TRAIN_START_DATE: str = "2021-01-03 23:00:00+00:00"
TRAIN_END_DATE: str = "2024-12-31 21:57:00+00:00"
VAL_START_DATE: str = "2025-01-01 23:00:00+00:00"
VAL_END_DATE: str = "2025-12-31 21:57:00+00:00"
TEST_START_DATE: str = "2026-01-01 23:00:00+00:00"
TEST_END_DATE: str = "2026-05-31 23:59:00+00:00"
