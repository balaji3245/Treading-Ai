"""Full feature engineering pipeline for historical market data.

Orchestrates technical indicators, time/session encodings, and multi-timeframe alignment
with strict chronological train/validation/test splitting, warm-up buffering, and NaN handling.
"""

from dataclasses import asdict, dataclass
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from treading_ai.config import (
    FEATURES_DATA_DIR,
    HISTDATA_DEFAULT_SYMBOL,
    TEST_END_DATE,
    TEST_START_DATE,
    TRAIN_END_DATE,
    TRAIN_START_DATE,
    VAL_END_DATE,
    VAL_START_DATE,
)
from treading_ai.features.market_structure import MarketStructureEngine
from treading_ai.features.multi_timeframe import MultiTimeframeAligner
from treading_ai.features.technical import TechnicalFeatureExtractor
from treading_ai.features.time_features import TimeFeatureExtractor
from treading_ai.preprocessing.storage import ParquetStorageEngine

logger = logging.getLogger(__name__)


@dataclass
class FeatureDatasetMetadata:
    symbol: str
    base_timeframe: str
    htf_timeframes: List[str]
    total_features_count: int
    feature_names: List[str]
    train_rows: int
    train_start: str
    train_end: str
    val_rows: int
    val_start: str
    val_end: str
    test_rows: int
    test_start: str
    test_end: str
    warmup_dropped_rows: int

    def to_dict(self) -> Dict:
        return asdict(self)


class FeaturePipeline:
    """End-to-end quantitative feature engineering pipeline."""

    def __init__(
        self,
        storage: Optional[ParquetStorageEngine] = None,
        output_dir: Path = FEATURES_DATA_DIR,
        tech_extractor: Optional[TechnicalFeatureExtractor] = None,
        time_extractor: Optional[TimeFeatureExtractor] = None,
        ms_extractor: Optional[MarketStructureEngine] = None,
    ):
        self.storage = storage or ParquetStorageEngine()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.tech_extractor = tech_extractor or TechnicalFeatureExtractor()
        self.time_extractor = time_extractor or TimeFeatureExtractor()
        self.ms_extractor = ms_extractor or MarketStructureEngine()

    def build_features(
        self,
        symbol: str = HISTDATA_DEFAULT_SYMBOL,
        base_timeframe: str = "M5",
        htf_timeframes: Optional[List[str]] = None,
        filter_incomplete: bool = True,
        include_market_structure: bool = False,
        save_to_disk: bool = True,
    ) -> Tuple[Dict[str, pd.DataFrame], FeatureDatasetMetadata]:
        """Extract all features, align higher timeframes, and partition into chronological splits.

        Parameters
        ----------
        symbol : str
            Instrument identifier (e.g., 'XAUUSD').
        base_timeframe : str
            Base trading timeframe (e.g., 'M5', 'M15', 'H1').
        htf_timeframes : Optional[List[str]]
            Higher timeframes to align (e.g. ['H1', 'H4']).
        filter_incomplete : bool
            Whether to exclude incomplete boundary candles. Default True.
        include_market_structure : bool
            Whether to extract causal market structure features. Default False.
        save_to_disk : bool
            Whether to serialize resulting splits to Parquet in data/features/.

        Returns
        -------
        Tuple[Dict[str, pd.DataFrame], FeatureDatasetMetadata]
            Dictionary containing 'train', 'val', 'test' DataFrames, and metadata summary.
        """
        htfs = htf_timeframes or ["H1", "H4"]
        logger.info("Starting feature engineering for %s on base timeframe %s (HTFs: %s)...", symbol, base_timeframe, htfs)

        # 1. Load verified continuous dataset for base timeframe
        # Automatically excludes QUARANTINED_PERIODS (2026_06 to 2026_10)
        df_base = self.storage.load_continuous_dataset(
            symbol=symbol,
            timeframe=base_timeframe,
            filter_incomplete=filter_incomplete,
        )
        logger.info("Loaded %d continuous %s base candles (%s to %s)", len(df_base), base_timeframe, df_base["timestamp"].iloc[0], df_base["timestamp"].iloc[-1])

        # 2. Extract technical and time features on base timeframe
        logger.info("Computing technical features on %s...", base_timeframe)
        tech_base = self.tech_extractor.extract_all(df_base)
        time_base = self.time_extractor.extract_time_features(df_base["timestamp"])

        combined_base = pd.concat([df_base[["timestamp", "open", "high", "low", "close", "volume"]], tech_base, time_base], axis=1)

        if include_market_structure:
            logger.info("Computing causal market structure features on %s...", base_timeframe)
            atr_for_ms = tech_base["atr_14"] if "atr_14" in tech_base.columns else None
            ms_base = self.ms_extractor.compute_features(df_base, atr_series=atr_for_ms)
            combined_base = pd.concat([combined_base, ms_base], axis=1)

        # 3. Extract HTF features and align with strict zero-lookahead causality
        aligner = MultiTimeframeAligner(ltf_timeframe=base_timeframe)
        for htf in htfs:
            logger.info("Processing and aligning higher timeframe %s...", htf)
            df_htf = self.storage.load_continuous_dataset(
                symbol=symbol,
                timeframe=htf,
                filter_incomplete=filter_incomplete,
            )
            # Compute technical features on HTF
            tech_htf = self.tech_extractor.extract_all(df_htf)
            htf_with_features = pd.concat([df_htf[["timestamp"]], tech_htf], axis=1)

            # Align onto base timeframe (backward as-of merge)
            combined_base = aligner.align_htf_features(
                ltf_df=combined_base,
                htf_df=htf_with_features,
                htf_timeframe=htf,
            )

        # 4. Handle warm-up periods and NaN policy
        # The rolling window indicators (e.g. 240 bars) introduce NaNs at the beginning of the continuous history (2021).
        # We determine the warm-up index where all feature columns become valid.
        feature_cols = [c for c in combined_base.columns if c not in ["timestamp", "open", "high", "low", "close", "volume"]]
        
        # Check first valid index across feature columns
        valid_mask = combined_base[feature_cols].notna().all(axis=1)
        first_valid_idx = valid_mask.idxmax() if valid_mask.any() else 0
        warmup_dropped = int(first_valid_idx)
        
        # Trim initial warm-up rows from the very start of 2021
        clean_df = combined_base.iloc[first_valid_idx:].reset_index(drop=True)
        logger.info("Trimmed %d initial warm-up bars from early 2021 (remaining clean rows: %d)", warmup_dropped, len(clean_df))

        # Strict NaN & Infinity Policy:
        # Backward fill (.bfill()) is strictly forbidden to prevent temporal leakage.
        # Forward fill is applied only where semantically justified across market transitions.
        nan_counts = clean_df[feature_cols].isna().sum().sum()
        if nan_counts > 0:
            logger.warning("Detected %d residual NaNs in feature set; forward filling across historical series", nan_counts)
            clean_df[feature_cols] = clean_df[feature_cols].ffill()

        # Explicitly verify NO remaining NaNs
        remaining_nans = clean_df[feature_cols].isna().sum()
        total_remaining_nans = int(remaining_nans.sum())
        if total_remaining_nans > 0:
            problematic = remaining_nans[remaining_nans > 0].to_dict()
            first_nan_row = int(clean_df[feature_cols].isna().any(axis=1).idxmax())
            first_nan_ts = str(clean_df.loc[first_nan_row, "timestamp"])
            raise ValueError(
                f"Feature engineering pipeline failure: detected {total_remaining_nans} unresolved NaNs after forward filling! "
                f"First occurrence at row index {first_nan_row} (timestamp: {first_nan_ts}). "
                f"Columns with NaNs: {problematic}. "
                f"Backward fill (.bfill()) is strictly forbidden to prevent lookahead data leakage."
            )

        # Explicitly verify NO infinite values
        inf_mask = np.isinf(clean_df[feature_cols].to_numpy())
        if inf_mask.any():
            inf_counts = {col: int(np.isinf(clean_df[col]).sum()) for col in feature_cols if np.isinf(clean_df[col]).any()}
            raise ValueError(
                f"Feature engineering pipeline failure: detected non-finite/infinite values in feature columns: {inf_counts}."
            )

        # 5. Partition into strict chronological splits
        t_train_start = pd.to_datetime(TRAIN_START_DATE, utc=True)
        t_train_end = pd.to_datetime(TRAIN_END_DATE, utc=True)
        t_val_start = pd.to_datetime(VAL_START_DATE, utc=True)
        t_val_end = pd.to_datetime(VAL_END_DATE, utc=True)
        t_test_start = pd.to_datetime(TEST_START_DATE, utc=True)
        t_test_end = pd.to_datetime(TEST_END_DATE, utc=True)

        df_train = clean_df[(clean_df["timestamp"] >= t_train_start) & (clean_df["timestamp"] <= t_train_end)].reset_index(drop=True)
        df_val = clean_df[(clean_df["timestamp"] >= t_val_start) & (clean_df["timestamp"] <= t_val_end)].reset_index(drop=True)
        df_test = clean_df[(clean_df["timestamp"] >= t_test_start) & (clean_df["timestamp"] <= t_test_end)].reset_index(drop=True)

        # Assert strict temporal separation (zero temporal overlap)
        if len(df_train) > 0 and len(df_val) > 0:
            assert df_train["timestamp"].max() < df_val["timestamp"].min(), "Train and Validation sets overlap temporally!"
        if len(df_val) > 0 and len(df_test) > 0:
            assert df_val["timestamp"].max() < df_test["timestamp"].min(), "Validation and Test sets overlap temporally!"

        tail_rows_count = len(clean_df[clean_df["timestamp"] > t_test_end])
        logger.info(
            "Row Ledger Accounting:\n"
            "  Loaded Base Candles:       %d\n"
            "  Warm-up Trimmed (2021):    %d\n"
            "  Clean Feature Rows:        %d\n"
            "  - Train Partition:         %d (%s to %s)\n"
            "  - Validation Partition:    %d (%s to %s)\n"
            "  - Test Partition:          %d (%s to %s)\n"
            "  - Post-Test Tail (June 1): %d (cleanly excluded by TEST_END_DATE)",
            len(df_base), warmup_dropped, len(clean_df),
            len(df_train), df_train["timestamp"].iloc[0] if len(df_train) else "empty", df_train["timestamp"].iloc[-1] if len(df_train) else "empty",
            len(df_val), df_val["timestamp"].iloc[0] if len(df_val) else "empty", df_val["timestamp"].iloc[-1] if len(df_val) else "empty",
            len(df_test), df_test["timestamp"].iloc[0] if len(df_test) else "empty", df_test["timestamp"].iloc[-1] if len(df_test) else "empty",
            tail_rows_count,
        )

        splits = {
            "train": df_train,
            "val": df_val,
            "test": df_test,
        }

        metadata = FeatureDatasetMetadata(
            symbol=symbol,
            base_timeframe=base_timeframe,
            htf_timeframes=htfs,
            total_features_count=len(feature_cols),
            feature_names=feature_cols,
            train_rows=len(df_train),
            train_start=str(df_train["timestamp"].iloc[0]) if len(df_train) else "",
            train_end=str(df_train["timestamp"].iloc[-1]) if len(df_train) else "",
            val_rows=len(df_val),
            val_start=str(df_val["timestamp"].iloc[0]) if len(df_val) else "",
            val_end=str(df_val["timestamp"].iloc[-1]) if len(df_val) else "",
            test_rows=len(df_test),
            test_start=str(df_test["timestamp"].iloc[0]) if len(df_test) else "",
            test_end=str(df_test["timestamp"].iloc[-1]) if len(df_test) else "",
            warmup_dropped_rows=warmup_dropped,
        )

        # 6. Save Parquet partitions to disk if requested
        if save_to_disk:
            for split_name, split_df in splits.items():
                fname = f"{symbol}_{base_timeframe}_features_{split_name}.parquet"
                fpath = self.output_dir / fname
                split_df.to_parquet(fpath, compression="snappy", index=False)
                logger.info("Saved %s split to %s (%d rows, %.2f MB)", split_name, fpath, len(split_df), fpath.stat().st_size / (1024 * 1024))

        return splits, metadata
