"""Tests for FeaturePipeline end-to-end execution.

Verifies:
1. End-to-end feature extraction, HTF alignment, and chronological splitting.
2. Zero NaN policy after warm-up drop and continuous forward filling.
3. Strict non-overlapping chronological boundaries between train, val, and test.
4. Parquet output serialization and metadata tracking.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock
import numpy as np
import pandas as pd
import pytest

from treading_ai.features.pipeline import FeaturePipeline
from treading_ai.features.technical import TechnicalFeatureExtractor
from treading_ai.preprocessing.storage import ParquetStorageEngine


def _generate_synthetic_candles(start_dt: datetime, count: int, freq_minutes: int) -> pd.DataFrame:
    """Helper to generate continuous synthetic OHLCV candles."""
    np.random.seed(42)
    timestamps = [start_dt + timedelta(minutes=freq_minutes * i) for i in range(count)]
    closes = 2600.0 + np.cumsum(np.random.normal(0, 0.5, count))
    opens = np.roll(closes, 1)
    opens[0] = 2600.0
    highs = np.maximum(opens, closes) + np.abs(np.random.normal(0.4, 0.1, count))
    lows = np.minimum(opens, closes) - np.abs(np.random.normal(0.4, 0.1, count))
    volumes = np.random.uniform(50, 150, count)

    return pd.DataFrame({
        "timestamp": timestamps,
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes,
        "is_complete": True,
    })


class TestFeaturePipeline:
    """Unit and integration tests for FeaturePipeline."""

    def test_pipeline_synthetic_e2e(self, tmp_path: Path):
        """Test full pipeline workflow using mock storage engine returning continuous data."""
        # Span across Train (2024), Val (2025), Test (2026)
        # Create 1500 M5 bars starting late 2024 to early 2026
        # Let's create data:
        # 500 bars in Dec 2024 (Train)
        # 500 bars in Jan 2025 (Val)
        # 500 bars in Jan 2026 (Test)
        train_m5 = _generate_synthetic_candles(datetime(2024, 12, 20, 0, 0, 0, tzinfo=timezone.utc), 500, 5)
        val_m5 = _generate_synthetic_candles(datetime(2025, 1, 6, 0, 0, 0, tzinfo=timezone.utc), 500, 5)
        test_m5 = _generate_synthetic_candles(datetime(2026, 1, 5, 0, 0, 0, tzinfo=timezone.utc), 500, 5)
        full_m5 = pd.concat([train_m5, val_m5, test_m5], ignore_index=True)

        train_h1 = _generate_synthetic_candles(datetime(2024, 12, 19, 0, 0, 0, tzinfo=timezone.utc), 150, 60)
        val_h1 = _generate_synthetic_candles(datetime(2025, 1, 5, 0, 0, 0, tzinfo=timezone.utc), 150, 60)
        test_h1 = _generate_synthetic_candles(datetime(2026, 1, 4, 0, 0, 0, tzinfo=timezone.utc), 150, 60)
        full_h1 = pd.concat([train_h1, val_h1, test_h1], ignore_index=True)

        mock_storage = MagicMock(spec=ParquetStorageEngine)

        def mock_load(symbol, timeframe, filter_incomplete=True):
            if timeframe == "M5":
                return full_m5.copy()
            elif timeframe == "H1":
                return full_h1.copy()
            raise ValueError(f"Unknown timeframe: {timeframe}")

        mock_storage.load_continuous_dataset.side_effect = mock_load

        custom_tech = TechnicalFeatureExtractor(
            return_periods=[1, 5],
            volatility_windows=[5, 10],
            atr_windows=[7],
            ema_periods=[5, 10],
            bb_period=10,
        )

        pipeline = FeaturePipeline(
            storage=mock_storage,
            output_dir=tmp_path / "features",
            tech_extractor=custom_tech,
        )

        splits, metadata = pipeline.build_features(
            symbol="XAUUSD",
            base_timeframe="M5",
            htf_timeframes=["H1"],
            filter_incomplete=True,
            save_to_disk=True,
        )

        # 1. Verify metadata
        assert metadata.symbol == "XAUUSD"
        assert metadata.base_timeframe == "M5"
        assert metadata.htf_timeframes == ["H1"]
        assert metadata.total_features_count > 40
        assert metadata.warmup_dropped_rows > 0

        # 2. Verify all splits exist
        assert "train" in splits
        assert "val" in splits
        assert "test" in splits

        df_train = splits["train"]
        df_val = splits["val"]
        df_test = splits["test"]

        assert len(df_train) > 0
        assert len(df_val) > 0
        assert len(df_test) > 0

        # 3. Verify zero NaNs in all feature columns
        feat_cols = metadata.feature_names
        assert df_train[feat_cols].isna().sum().sum() == 0, "Train split contains NaNs!"
        assert df_val[feat_cols].isna().sum().sum() == 0, "Val split contains NaNs!"
        assert df_test[feat_cols].isna().sum().sum() == 0, "Test split contains NaNs!"

        # 4. Strict chronological ordering (no overlap)
        assert df_train["timestamp"].max() < df_val["timestamp"].min()
        assert df_val["timestamp"].max() < df_test["timestamp"].min()

        # 5. Verify Parquet files saved on disk
        for split_name in ["train", "val", "test"]:
            saved_file = tmp_path / "features" / f"XAUUSD_M5_features_{split_name}.parquet"
            assert saved_file.exists()
            assert saved_file.stat().st_size > 0

    def test_pipeline_with_market_structure(self, tmp_path: Path):
        """Test pipeline with include_market_structure=True."""
        train_m5 = _generate_synthetic_candles(datetime(2024, 12, 20, 0, 0, 0, tzinfo=timezone.utc), 300, 5)
        train_h1 = _generate_synthetic_candles(datetime(2024, 12, 19, 0, 0, 0, tzinfo=timezone.utc), 100, 60)

        mock_storage = MagicMock(spec=ParquetStorageEngine)
        mock_storage.load_continuous_dataset.side_effect = lambda symbol, timeframe, filter_incomplete=True: (
            train_m5.copy() if timeframe == "M5" else train_h1.copy()
        )

        custom_tech = TechnicalFeatureExtractor(
            return_periods=[1],
            volatility_windows=[5],
            atr_windows=[7],
            ema_periods=[5],
            bb_period=5,
        )

        pipeline = FeaturePipeline(
            storage=mock_storage,
            output_dir=tmp_path / "features",
            tech_extractor=custom_tech,
        )

        splits, metadata = pipeline.build_features(
            symbol="XAUUSD",
            base_timeframe="M5",
            htf_timeframes=["H1"],
            filter_incomplete=True,
            include_market_structure=True,
            save_to_disk=False,
        )

        df_train = splits["train"]
        assert "ms_swing_high" in df_train.columns
        assert "ms_bos_bullish" in df_train.columns
        assert "ms_active_fvg_bullish_count" in df_train.columns
        assert "ms_premium_discount_pct" in df_train.columns
