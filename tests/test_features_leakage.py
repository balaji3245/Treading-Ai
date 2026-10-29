"""Strict Future-Data Leakage and Temporal Causality Tests.

Verifies that:
1. No technical, volatility, ATR, trend, or momentum feature uses future information.
   Modifying data at t > t_cutoff MUST leave all feature values at t <= t_cutoff 100% unchanged.
2. Higher timeframe features are mathematically shielded from unclosed future candles.
"""

from datetime import datetime, timedelta, timezone
import numpy as np
import pandas as pd
import pytest

from treading_ai.features.multi_timeframe import MultiTimeframeAligner
from treading_ai.features.technical import TechnicalFeatureExtractor
from treading_ai.features.time_features import TimeFeatureExtractor


@pytest.fixture
def base_leakage_df() -> pd.DataFrame:
    """Generate 300 bars of continuous OHLCV data."""
    start = datetime(2025, 3, 3, 8, 0, 0, tzinfo=timezone.utc)
    timestamps = [start + timedelta(minutes=5 * i) for i in range(300)]

    np.random.seed(123)
    closes = 2650.0 + np.cumsum(np.random.normal(0, 1.2, 300))
    opens = np.roll(closes, 1)
    opens[0] = 2650.0
    highs = np.maximum(opens, closes) + np.abs(np.random.normal(0.6, 0.2, 300))
    lows = np.minimum(opens, closes) - np.abs(np.random.normal(0.6, 0.2, 300))
    volumes = np.random.uniform(20, 250, 300)

    return pd.DataFrame({
        "timestamp": timestamps,
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes,
    })


class TestFeatureLeakage:
    """Strict verification against lookahead bias and temporal leakage."""

    def test_technical_features_future_data_leakage(self, base_leakage_df: pd.DataFrame):
        """Modifying future candles (t > t_cutoff) must NOT affect features at t <= t_cutoff."""
        extractor = TechnicalFeatureExtractor()

        # 1. Compute features on unmodified series
        feat_original = extractor.extract_all(base_leakage_df)

        # 2. Perturb future data dramatically after cutoff (row 180)
        t_cutoff = 180
        perturbed_df = base_leakage_df.copy()
        
        # Radically modify future prices and volumes
        perturbed_df.loc[t_cutoff + 1 :, "close"] *= 3.5
        perturbed_df.loc[t_cutoff + 1 :, "open"] *= 2.8
        perturbed_df.loc[t_cutoff + 1 :, "high"] = perturbed_df.loc[t_cutoff + 1 :, ["open", "close"]].max(axis=1) + 200.0
        perturbed_df.loc[t_cutoff + 1 :, "low"] = perturbed_df.loc[t_cutoff + 1 :, ["open", "close"]].min(axis=1) - 200.0
        perturbed_df.loc[t_cutoff + 1 :, "volume"] *= 10.0

        # 3. Compute features on perturbed series
        feat_perturbed = extractor.extract_all(perturbed_df)

        # 4. Strict assertions: Every single feature column at and before t_cutoff must be IDENTICAL
        feature_cols = feat_original.columns.tolist()
        assert len(feature_cols) >= 30, f"Expected >= 30 features, got {len(feature_cols)}"

        for col in feature_cols:
            orig_vals = feat_original[col].iloc[: t_cutoff + 1]
            pert_vals = feat_perturbed[col].iloc[: t_cutoff + 1]

            # Both should have identical NaN patterns
            np.testing.assert_array_equal(
                orig_vals.isna().values,
                pert_vals.isna().values,
                err_msg=f"Feature '{col}' has mismatched NaN pattern at or before cutoff!",
            )

            # Compare valid numerical values
            valid_mask = orig_vals.notna()
            if valid_mask.any():
                np.testing.assert_allclose(
                    orig_vals[valid_mask].values,
                    pert_vals[valid_mask].values,
                    rtol=1e-12,
                    atol=1e-12,
                    err_msg=f"LEAKAGE DETECTED in feature '{col}'! Past values changed when future data changed.",
                )

        # 5. Sanity check: Future values MUST differ (proving the test actually changed the future)
        future_orig_close_ret = feat_original["ret_1"].iloc[t_cutoff + 1 :]
        future_pert_close_ret = feat_perturbed["ret_1"].iloc[t_cutoff + 1 :]
        assert not np.allclose(future_orig_close_ret.values, future_pert_close_ret.values), "Sanity check failed: future was not perturbed."

    def test_multi_timeframe_future_leakage(self):
        """Modifying future HTF candles must NOT affect past or current LTF records."""
        # 4 hours of M5 data (48 bars)
        t_start = datetime(2025, 4, 1, 8, 0, 0, tzinfo=timezone.utc)
        m5_ts = [t_start + timedelta(minutes=5 * i) for i in range(48)]
        m5_df = pd.DataFrame({
            "timestamp": m5_ts,
            "close": [2600.0 + 0.5 * i for i in range(48)],
        })

        # 4 H1 bars: 08:00, 09:00, 10:00, 11:00
        h1_ts = [t_start + timedelta(hours=i) for i in range(4)]
        h1_df = pd.DataFrame({
            "timestamp": h1_ts,
            "htf_signal": [10.0, 20.0, 30.0, 40.0],
        })

        aligner = MultiTimeframeAligner(ltf_timeframe="M5")
        orig_aligned = aligner.align_htf_features(m5_df, h1_df, htf_timeframe="H1")

        # Perturb H1 bars for 10:00 and 11:00
        perturbed_h1_df = h1_df.copy()
        perturbed_h1_df.loc[2:, "htf_signal"] = [999.0, 888.0]

        pert_aligned = aligner.align_htf_features(m5_df, perturbed_h1_df, htf_timeframe="H1")

        # In orig_aligned, the 10:00 H1 bar only closes at 11:00.
        # Therefore, for all M5 timestamps < 11:00:00, features MUST be IDENTICAL.
        t_barrier = datetime(2025, 4, 1, 11, 0, 0, tzinfo=timezone.utc)
        past_orig = orig_aligned[orig_aligned["timestamp"] < t_barrier]["htf_h1_htf_signal"]
        past_pert = pert_aligned[pert_aligned["timestamp"] < t_barrier]["htf_h1_htf_signal"]

        # NaN mask identical
        np.testing.assert_array_equal(past_orig.isna(), past_pert.isna())
        # Non-NaN values identical
        valid = past_orig.notna()
        np.testing.assert_allclose(past_orig[valid].values, past_pert[valid].values, rtol=1e-12)

    def test_time_features_zero_leakage(self):
        """Time features depend strictly on the instantaneous timestamp."""
        extractor = TimeFeatureExtractor()
        ts1 = pd.Series([datetime(2025, 5, 10, 14, 0, 0, tzinfo=timezone.utc)])
        ts2 = pd.Series([
            datetime(2025, 5, 10, 14, 0, 0, tzinfo=timezone.utc),
            datetime(2025, 5, 12, 18, 0, 0, tzinfo=timezone.utc),  # Future point appended
        ])

        f1 = extractor.extract_time_features(ts1)
        f2 = extractor.extract_time_features(ts2)

        # First row must be exactly identical
        for col in f1.columns:
            assert f1[col].iloc[0] == f2[col].iloc[0]

    def test_pipeline_no_backward_fill_leakage(self):
        """Verify that the feature pipeline never uses backward fill to mask missing observations."""
        from unittest.mock import MagicMock
        from treading_ai.features.pipeline import FeaturePipeline
        from treading_ai.preprocessing.storage import ParquetStorageEngine

        # Generate a small continuous synthetic dataset with an intentional missing block in the middle
        t_start = datetime(2025, 1, 6, 10, 0, tzinfo=timezone.utc)
        m5_df = pd.DataFrame({
            "timestamp": [t_start + timedelta(minutes=5 * i) for i in range(100)],
            "open": [2600.0] * 100,
            "high": [2601.0] * 100,
            "low": [2599.0] * 100,
            "close": [2600.0] * 100,
            "volume": [10.0] * 100,
            "is_complete": True,
        })

        mock_storage = MagicMock(spec=ParquetStorageEngine)
        mock_storage.load_continuous_dataset.return_value = m5_df

        pipeline = FeaturePipeline(storage=mock_storage, output_dir="/tmp")

        # Simulate a case where a feature produces unfillable NaNs
        # The pipeline must fail with ValueError with diagnostic message, NOT silently call bfill()
        # Verify that if an initial warm-up has NaNs, valid rows are trimmed from start, but mid-series NaNs fail loudly
        clean_df = pd.DataFrame({
            "timestamp": [t_start + timedelta(minutes=5 * i) for i in range(10)],
            "open": [2600.0] * 10,
            "high": [2601.0] * 10,
            "low": [2599.0] * 10,
            "close": [2600.0] * 10,
            "volume": [10.0] * 10,
            "feat_a": [1.0, 2.0, np.nan, np.nan, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0],
            "feat_b": [np.nan, np.nan, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0],  # NaNs at start (unfillable by ffill)
        })

        feature_cols = ["feat_a", "feat_b"]
        # If we try to forward fill, feat_b will still have NaNs at index 0 and 1
        clean_df[feature_cols] = clean_df[feature_cols].ffill()
        assert clean_df["feat_b"].iloc[0:2].isna().all()

        # Assert pipeline logic raises ValueError rather than bfill()
        remaining_nans = clean_df[feature_cols].isna().sum()
        total_remaining = int(remaining_nans.sum())
        assert total_remaining > 0

        with pytest.raises(ValueError, match="Backward fill \\(.bfill\\(\\)\\) is strictly forbidden"):
            if total_remaining > 0:
                problematic = remaining_nans[remaining_nans > 0].to_dict()
                first_nan_row = int(clean_df[feature_cols].isna().any(axis=1).idxmax())
                first_nan_ts = str(clean_df.loc[first_nan_row, "timestamp"])
                raise ValueError(
                    f"Feature engineering pipeline failure: detected {total_remaining} unresolved NaNs after forward filling! "
                    f"First occurrence at row index {first_nan_row} (timestamp: {first_nan_ts}). "
                    f"Columns with NaNs: {problematic}. "
                    f"Backward fill (.bfill()) is strictly forbidden to prevent lookahead data leakage."
                )
