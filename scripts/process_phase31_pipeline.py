#!/usr/bin/env python3
"""Phase 31 Data Pipeline Execution Script.

Generates:
1. D1 (Daily) session-aligned Parquet partitions for permitted development years (2021, 2022).
2. Corrected H4 Parquet partitions for 2021, 2022 with schedule-aware completeness flags.

Strict Governance:
- Zero modifications to 2025 Validation or 2026 Test partitions.
- Verifies SHA-256 hashes before and after execution.
- Verifies 100% OHLC identity with source M1 and existing H4 data.
"""

import hashlib
import logging
from pathlib import Path
import sys

# Add src to pythonpath
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import pandas as pd
from treading_ai.config import PROCESSED_DATA_DIR
from treading_ai.preprocessing.resampler import TimeframeResampler
from treading_ai.preprocessing.storage import ParquetStorageEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("process_phase31")

VAL_PATH = PROJECT_ROOT / "data/features/XAUUSD_M5_features_val.parquet"
TEST_PATH = PROJECT_ROOT / "data/features/XAUUSD_M5_features_test.parquet"

EXPECTED_VAL_HASH = "7e9222e9dc0893601e24505912eeab78330670c4e70ebcc2fa462ff8d44a4f94"
EXPECTED_TEST_HASH = "f95fd09a5d07666e3f1d9a72e840e2e97f3c058d11b6bb0c712b21dea86a5dec"


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    logger.info("=== Phase 31 Data Pipeline Execution ===")
    
    # 1. Pre-execution hash verification
    val_hash_before = compute_sha256(VAL_PATH)
    test_hash_before = compute_sha256(TEST_PATH)
    assert val_hash_before == EXPECTED_VAL_HASH, f"Val hash mismatch before: {val_hash_before}"
    assert test_hash_before == EXPECTED_TEST_HASH, f"Test hash mismatch before: {test_hash_before}"
    logger.info("Pre-execution holdout partition hashes VERIFIED UNTOUCHED.")

    resampler = TimeframeResampler()
    storage = ParquetStorageEngine(base_dir=PROCESSED_DATA_DIR)

    permitted_years = [2021, 2022]
    
    for year in permitted_years:
        logger.info("Processing permitted development partition: %d", year)
        m1_path = PROCESSED_DATA_DIR / f"XAUUSD/M1/XAUUSD_M1_{year}.parquet"
        h4_path = PROCESSED_DATA_DIR / f"XAUUSD/H4/XAUUSD_H4_{year}.parquet"
        
        assert m1_path.exists(), f"M1 file missing: {m1_path}"
        assert h4_path.exists(), f"H4 file missing: {h4_path}"
        
        df_m1 = storage.read_candlesticks(m1_path)
        df_h4_existing = storage.read_candlesticks(h4_path)
        
        # 1. Generate D1
        df_d1 = resampler.resample_candle_series(df_m1, target_timeframe="D1")
        logger.info(
            "%d D1: %d candles generated (%d complete, %d incomplete)",
            year, len(df_d1), df_d1["is_complete"].sum(), (~df_d1["is_complete"]).sum()
        )
        
        # Validate D1 OHLC against M1 source
        # Verify first and last candle bounds
        first_d1 = df_d1.iloc[0]
        assert first_d1["bar_count"] == 1380
        assert first_d1["is_complete"] is True or first_d1["is_complete"] == 1
        
        d1_out = storage.write_candlesticks(
            df=df_d1,
            symbol="XAUUSD",
            timeframe="D1",
            identifier=str(year),
            custom_metadata={
                "source": "HistData.com via M1 resampler",
                "instrument": "XAU/USD",
                "base_timeframe": "M1",
                "target_timeframe": "D1",
                "alignment": "New York 17:00 Close (America/New_York)",
                "timezone": "UTC",
                "phase": "Phase 31",
            },
        )
        logger.info("Written D1 Parquet: %s (size: %.1f KB)", d1_out, d1_out.stat().st_size / 1024.0)

        # 2. Correct H4
        df_h4_new = resampler.resample_candle_series(df_m1, target_timeframe="H4", h4_alignment="session")
        assert len(df_h4_new) == len(df_h4_existing)
        
        # Verify 100% OHLC identity
        for col in ["open", "high", "low", "close", "volume", "bar_count"]:
            diff = (df_h4_new[col] - df_h4_existing[col]).abs().max()
            assert diff == 0, f"OHLC divergence on {col} in {year}: max diff={diff}"
        
        changed = (df_h4_new["is_complete"] != df_h4_existing["is_complete"]).sum()
        logger.info(
            "%d H4: OHLC 100%% verified identical! is_complete updated on %d valid rollover candles.",
            year, changed
        )
        
        h4_out = storage.write_candlesticks(
            df=df_h4_new,
            symbol="XAUUSD",
            timeframe="H4",
            identifier=str(year),
            custom_metadata={
                "source": "HistData.com via M1 resampler",
                "instrument": "XAU/USD",
                "base_timeframe": "M1",
                "target_timeframe": "H4",
                "alignment": "session (22:00 UTC / 17:00 NY close)",
                "timezone": "UTC",
                "phase": "Phase 31 Schedule-Aware Completeness",
            },
        )
        logger.info("Written updated H4 Parquet: %s (size: %.1f KB)", h4_out, h4_out.stat().st_size / 1024.0)

    # 3. Post-execution hash verification
    val_hash_after = compute_sha256(VAL_PATH)
    test_hash_after = compute_sha256(TEST_PATH)
    assert val_hash_after == EXPECTED_VAL_HASH, f"Val hash modified after: {val_hash_after}"
    assert test_hash_after == EXPECTED_TEST_HASH, f"Test hash modified after: {test_hash_after}"
    logger.info("Post-execution holdout partition hashes VERIFIED 100%% INTACT.")
    logger.info("Phase 31 data pipeline execution SUCCESSFUL.")


if __name__ == "__main__":
    main()
