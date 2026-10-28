"""Unit tests for ParquetStorageEngine."""

from pathlib import Path

import pandas as pd
import pytest

from treading_ai.preprocessing.resampler import TimeframeResampler
from treading_ai.preprocessing.storage import ParquetStorageEngine


def test_parquet_round_trip(clean_synthetic_m1_df: pd.DataFrame, tmp_path: Path):
    storage = ParquetStorageEngine(base_dir=tmp_path)
    resampler = TimeframeResampler()
    multi_tf = resampler.resample_all_timeframes(clean_synthetic_m1_df)

    # Write M5 dataset
    m5_df = multi_tf["M5"]
    output_path = storage.write_candlesticks(
        df=m5_df,
        symbol="XAUUSD",
        timeframe="M5",
        identifier="2026_test",
        custom_metadata={"provenance_source": "synthetic_test", "author": "antigravity"},
    )

    assert output_path.exists()
    assert output_path.stat().st_size > 0

    # Read back full dataframe
    read_df = storage.read_candlesticks(output_path)
    assert len(read_df) == len(m5_df)
    assert list(read_df.columns) == list(m5_df.columns)
    assert pytest.approx(read_df["close"].iloc[0]) == m5_df["close"].iloc[0]
    assert read_df["is_complete"].all()


def test_column_projection(clean_synthetic_m1_df: pd.DataFrame, tmp_path: Path):
    storage = ParquetStorageEngine(base_dir=tmp_path)
    resampler = TimeframeResampler()
    df_m1 = resampler.resample_all_timeframes(clean_synthetic_m1_df)["M1"]

    path = storage.write_candlesticks(
        df=df_m1,
        symbol="XAUUSD",
        timeframe="M1",
        identifier="proj_test",
    )

    # Read only timestamp and close
    projected_df = storage.read_candlesticks(path, columns=["timestamp", "close"])
    assert list(projected_df.columns) == ["timestamp", "close"]
    assert len(projected_df) == 120


def test_chunked_streaming(clean_synthetic_m1_df: pd.DataFrame, tmp_path: Path):
    storage = ParquetStorageEngine(base_dir=tmp_path)
    resampler = TimeframeResampler()
    df_m1 = resampler.resample_all_timeframes(clean_synthetic_m1_df)["M1"]

    path = storage.write_candlesticks(
        df=df_m1,
        symbol="XAUUSD",
        timeframe="M1",
        identifier="stream_test",
    )

    chunks = list(storage.iter_candlestick_chunks(path, batch_size=30))
    # 120 rows with batch_size=30 should produce 4 chunks
    assert len(chunks) == 4
    total_rows = sum(len(c) for c in chunks)
    assert total_rows == 120


def test_filter_incomplete_candles(tmp_path: Path):
    storage = ParquetStorageEngine(base_dir=tmp_path)
    # Create dataset with 3 complete and 1 incomplete candle
    df = pd.DataFrame({
        "timestamp": pd.date_range("2026-01-01", periods=4, freq="5min", tz="UTC"),
        "open": [2000.0, 2001.0, 2002.0, 2003.0],
        "high": [2005.0, 2006.0, 2007.0, 2008.0],
        "low": [1995.0, 1996.0, 1997.0, 1998.0],
        "close": [2001.0, 2002.0, 2003.0, 2004.0],
        "volume": [10.0, 10.0, 10.0, 5.0],
        "bar_count": [5, 5, 5, 2],
        "is_complete": [True, True, True, False],
    })
    path = storage.write_candlesticks(df, "XAUUSD", "M5", "incomplete_test")

    # Unfiltered read keeps all 4
    df_all = storage.read_candlesticks(path, filter_incomplete=False)
    assert len(df_all) == 4

    # Filtered read strictly excludes the incomplete bar
    df_clean = storage.read_candlesticks(path, filter_incomplete=True)
    assert len(df_clean) == 3
    assert df_clean["is_complete"].all()


def test_quarantine_exclusion_in_continuous_dataset(tmp_path: Path):
    storage = ParquetStorageEngine(base_dir=tmp_path)
    
    # Write two partitions: 2026_01 (clean) and 2026_06 (quarantined)
    t1 = pd.date_range("2026-01-01", periods=10, freq="1h", tz="UTC")
    df1 = pd.DataFrame({
        "timestamp": t1,
        "open": [2000.0] * 10,
        "high": [2005.0] * 10,
        "low": [1995.0] * 10,
        "close": [2001.0] * 10,
        "volume": [10.0] * 10,
        "bar_count": [60] * 10,
        "is_complete": [True] * 10,
    })
    storage.write_candlesticks(df1, "XAUUSD", "H1", "2026_01")

    t6 = pd.date_range("2026-06-01", periods=10, freq="1h", tz="UTC")
    df6 = pd.DataFrame({
        "timestamp": t6,
        "open": [2050.0] * 10,
        "high": [2055.0] * 10,
        "low": [2045.0] * 10,
        "close": [2051.0] * 10,
        "volume": [10.0] * 10,
        "bar_count": [60] * 10,
        "is_complete": [True] * 10,
    })
    storage.write_candlesticks(df6, "XAUUSD", "H1", "2026_06")

    # list_available_partitions should automatically exclude 2026_06
    partitions = storage.list_available_partitions("XAUUSD", "H1")
    assert "2026_01" in partitions
    assert "2026_06" not in partitions

    # load_continuous_dataset should only contain 2026_01 data
    continuous = storage.load_continuous_dataset("XAUUSD", "H1")
    assert len(continuous) == 10
    assert continuous["timestamp"].max() < pd.Timestamp("2026-06-01", tz="UTC")

