"""Pytest fixtures for Treading-AI pipeline testing.

All fixtures are small, deterministic synthetic datasets that execute entirely offline
without requiring internet access.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict

import numpy as np
import pandas as pd
import pytest

from treading_ai.config import OHLC_COLUMNS


@pytest.fixture
def clean_synthetic_m1_df() -> pd.DataFrame:
    """Generate 120 minutes of valid continuous M1 synthetic candles on a Wednesday."""
    # Wednesday 2026-01-07 10:00:00 UTC to 11:59:00 UTC (120 bars)
    start_time = datetime(2026, 1, 7, 10, 0, 0, tzinfo=timezone.utc)
    timestamps = [start_time + timedelta(minutes=i) for i in range(120)]

    np.random.seed(42)
    base_price = 2650.0
    opens = []
    highs = []
    lows = []
    closes = []
    volumes = []

    current_price = base_price
    for _ in range(120):
        o = current_price
        c = round(o + np.random.uniform(-1.5, 1.5), 3)
        h = round(max(o, c) + abs(np.random.uniform(0.1, 1.0)), 3)
        l = round(min(o, c) - abs(np.random.uniform(0.1, 1.0)), 3)
        v = round(np.random.uniform(10.0, 100.0), 1)

        opens.append(o)
        highs.append(h)
        lows.append(l)
        closes.append(c)
        volumes.append(v)
        current_price = c

    df = pd.DataFrame({
        "timestamp": timestamps,
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes,
    })
    return df


@pytest.fixture
def synthetic_m1_with_anomalies(clean_synthetic_m1_df: pd.DataFrame) -> pd.DataFrame:
    """Generate M1 dataframe with deliberate anomalies for validator testing."""
    df = clean_synthetic_m1_df.copy()

    # 1. Row 5: Missing value
    df.loc[5, "close"] = np.nan

    # 2. Row 10: Non-positive price
    df.loc[10, "open"] = -10.0

    # 3. Row 15: High < max(Open, Close)
    df.loc[15, "high"] = df.loc[15, "open"] - 1.0

    # 4. Row 20: Low > min(Open, Close)
    df.loc[20, "low"] = df.loc[20, "close"] + 2.0

    # 5. Row 25: Duplicate timestamp of row 24
    df.loc[25, "timestamp"] = df.loc[24, "timestamp"]

    # 6. Row 30: Out of chronological order
    df.loc[30, "timestamp"] = df.loc[28, "timestamp"] - timedelta(minutes=5)

    return df


@pytest.fixture
def synthetic_gap_dataframe() -> pd.DataFrame:
    """Generate candles containing weekend closure, daily roll break, and an unexplained gap."""
    records = []

    # 1. Friday night before weekend close: 2026-01-09 21:58 and 21:59 UTC
    t1 = datetime(2026, 1, 9, 21, 58, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 1, 9, 21, 59, 0, tzinfo=timezone.utc)
    records.append({"timestamp": t1, "open": 2650.0, "high": 2651.0, "low": 2649.0, "close": 2650.5, "volume": 10.0})
    records.append({"timestamp": t2, "open": 2650.5, "high": 2652.0, "low": 2650.0, "close": 2651.0, "volume": 12.0})

    # Weekend gap -> Sunday reopening at 23:01 UTC (2026-01-11 23:01:00 UTC)
    t3 = datetime(2026, 1, 11, 23, 1, 0, tzinfo=timezone.utc)
    t4 = datetime(2026, 1, 11, 23, 2, 0, tzinfo=timezone.utc)
    records.append({"timestamp": t3, "open": 2652.0, "high": 2653.0, "low": 2651.5, "close": 2652.5, "volume": 15.0})
    records.append({"timestamp": t4, "open": 2652.5, "high": 2654.0, "low": 2652.0, "close": 2653.0, "volume": 14.0})

    # Daily roll break -> Monday 2026-01-12 21:59 UTC to 23:00 UTC (1 hour gap)
    t5 = datetime(2026, 1, 12, 21, 59, 0, tzinfo=timezone.utc)
    t6 = datetime(2026, 1, 12, 23, 0, 0, tzinfo=timezone.utc)
    records.append({"timestamp": t5, "open": 2653.0, "high": 2654.0, "low": 2652.5, "close": 2653.5, "volume": 20.0})
    records.append({"timestamp": t6, "open": 2653.5, "high": 2655.0, "low": 2653.0, "close": 2654.0, "volume": 18.0})

    # Unexplained gap during active hours -> Tuesday 2026-01-13 14:00 UTC to 14:45 UTC (45 min missing)
    t7 = datetime(2026, 1, 13, 14, 0, 0, tzinfo=timezone.utc)
    t8 = datetime(2026, 1, 13, 14, 45, 0, tzinfo=timezone.utc)
    records.append({"timestamp": t7, "open": 2654.0, "high": 2655.5, "low": 2653.5, "close": 2655.0, "volume": 30.0})
    records.append({"timestamp": t8, "open": 2655.0, "high": 2656.0, "low": 2654.5, "close": 2655.5, "volume": 25.0})

    return pd.DataFrame(records)
