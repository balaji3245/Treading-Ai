"""Tests for time and session feature extraction engine.

Verifies cyclical harmonic encodings (sine/cosine bounds, continuity) and
timezone-aware market session flag assignments (Asian, London, NY, Overlaps, Roll breaks)
across winter standard time, summer daylight saving time, and transition dates.
"""

from datetime import datetime, timezone
import numpy as np
import pandas as pd
import pytest

from treading_ai.features.time_features import TimeFeatureExtractor


class TestTimeFeatureExtractor:
    """Unit tests for TimeFeatureExtractor."""

    @pytest.fixture
    def extractor(self) -> TimeFeatureExtractor:
        return TimeFeatureExtractor()

    def test_cyclical_bounds_and_harmonics(self, extractor: TimeFeatureExtractor):
        # Create timestamps spanning a full 24 hours at 15-minute intervals
        base = datetime(2025, 6, 11, 0, 0, 0, tzinfo=timezone.utc)  # Wednesday (day_of_week=2, month=6)
        timestamps = pd.Series([base + pd.Timedelta(minutes=15 * i) for i in range(96)])

        features = extractor.extract_time_features(timestamps)

        # Check cyclical bounds [-1, 1]
        for col in ["sin_time_of_day", "cos_time_of_day", "sin_day_of_week", "cos_day_of_week", "sin_month", "cos_month"]:
            assert (features[col] >= -1.0 - 1e-6).all()
            assert (features[col] <= 1.0 + 1e-6).all()

        # Check Pythagorean identity sin^2 + cos^2 = 1.0
        time_circle = features["sin_time_of_day"] ** 2 + features["cos_time_of_day"] ** 2
        np.testing.assert_allclose(time_circle.values, 1.0, atol=1e-6)

        day_circle = features["sin_day_of_week"] ** 2 + features["cos_day_of_week"] ** 2
        np.testing.assert_allclose(day_circle.values, 1.0, atol=1e-6)

        month_circle = features["sin_month"] ** 2 + features["cos_month"] ** 2
        np.testing.assert_allclose(month_circle.values, 1.0, atol=1e-6)

    def test_winter_vs_summer_london_session(self, extractor: TimeFeatureExtractor):
        """Verify London session (08:00-16:30 local) adjusts seamlessly between GMT (winter) and BST (summer)."""
        # Winter: Wednesday 2025-01-15 (GMT = UTC+0)
        # London local hours: 08:00 to 16:30 GMT = 08:00 to 16:30 UTC
        ts_winter_before_open = pd.Series([datetime(2025, 1, 15, 7, 30, tzinfo=timezone.utc)])
        ts_winter_open = pd.Series([datetime(2025, 1, 15, 8, 30, tzinfo=timezone.utc)])
        ts_winter_active = pd.Series([datetime(2025, 1, 15, 16, 15, tzinfo=timezone.utc)])
        ts_winter_after_close = pd.Series([datetime(2025, 1, 15, 16, 45, tzinfo=timezone.utc)])

        assert extractor.extract_time_features(ts_winter_before_open).iloc[0]["session_london"] == 0
        assert extractor.extract_time_features(ts_winter_open).iloc[0]["session_london"] == 1
        assert extractor.extract_time_features(ts_winter_active).iloc[0]["session_london"] == 1
        assert extractor.extract_time_features(ts_winter_after_close).iloc[0]["session_london"] == 0

        # Summer: Wednesday 2025-07-16 (BST = UTC+1)
        # London local hours: 08:00 to 16:30 BST = 07:00 to 15:30 UTC
        ts_summer_before_open = pd.Series([datetime(2025, 7, 16, 6, 30, tzinfo=timezone.utc)])
        ts_summer_open = pd.Series([datetime(2025, 7, 16, 7, 30, tzinfo=timezone.utc)])
        ts_summer_active = pd.Series([datetime(2025, 7, 16, 15, 15, tzinfo=timezone.utc)])
        ts_summer_after_close = pd.Series([datetime(2025, 7, 16, 15, 45, tzinfo=timezone.utc)])

        assert extractor.extract_time_features(ts_summer_before_open).iloc[0]["session_london"] == 0
        assert extractor.extract_time_features(ts_summer_open).iloc[0]["session_london"] == 1
        assert extractor.extract_time_features(ts_summer_active).iloc[0]["session_london"] == 1
        assert extractor.extract_time_features(ts_summer_after_close).iloc[0]["session_london"] == 0

    def test_winter_vs_summer_ny_session(self, extractor: TimeFeatureExtractor):
        """Verify New York session (08:00-17:00 local) adjusts seamlessly between EST (winter) and EDT (summer)."""
        # Winter: Wednesday 2025-01-15 (EST = UTC-5)
        # NY local hours: 08:00 to 17:00 EST = 13:00 to 22:00 UTC
        ts_winter_before = pd.Series([datetime(2025, 1, 15, 12, 30, tzinfo=timezone.utc)])
        ts_winter_open = pd.Series([datetime(2025, 1, 15, 13, 30, tzinfo=timezone.utc)])
        ts_winter_late = pd.Series([datetime(2025, 1, 15, 21, 30, tzinfo=timezone.utc)])
        ts_winter_closed = pd.Series([datetime(2025, 1, 15, 22, 15, tzinfo=timezone.utc)])

        assert extractor.extract_time_features(ts_winter_before).iloc[0]["session_ny"] == 0
        assert extractor.extract_time_features(ts_winter_open).iloc[0]["session_ny"] == 1
        assert extractor.extract_time_features(ts_winter_late).iloc[0]["session_ny"] == 1
        assert extractor.extract_time_features(ts_winter_closed).iloc[0]["session_ny"] == 0

        # Summer: Wednesday 2025-07-16 (EDT = UTC-4)
        # NY local hours: 08:00 to 17:00 EDT = 12:00 to 21:00 UTC
        ts_summer_before = pd.Series([datetime(2025, 7, 16, 11, 30, tzinfo=timezone.utc)])
        ts_summer_open = pd.Series([datetime(2025, 7, 16, 12, 30, tzinfo=timezone.utc)])
        ts_summer_late = pd.Series([datetime(2025, 7, 16, 20, 30, tzinfo=timezone.utc)])
        ts_summer_closed = pd.Series([datetime(2025, 7, 16, 21, 15, tzinfo=timezone.utc)])

        assert extractor.extract_time_features(ts_summer_before).iloc[0]["session_ny"] == 0
        assert extractor.extract_time_features(ts_summer_open).iloc[0]["session_ny"] == 1
        assert extractor.extract_time_features(ts_summer_late).iloc[0]["session_ny"] == 1
        assert extractor.extract_time_features(ts_summer_closed).iloc[0]["session_ny"] == 0

    def test_london_ny_overlap_consistency(self, extractor: TimeFeatureExtractor):
        """Overlap must definitionally equal (session_london & session_ny) at all times."""
        # Test 100 hourly timestamps across spring mismatch, summer, autumn mismatch, and winter
        dates = [
            datetime(2024, 3, 15, h, 0, tzinfo=timezone.utc) for h in range(24)  # Spring mismatch
        ] + [
            datetime(2024, 7, 15, h, 0, tzinfo=timezone.utc) for h in range(24)  # Summer
        ] + [
            datetime(2024, 10, 30, h, 0, tzinfo=timezone.utc) for h in range(24) # Autumn mismatch
        ] + [
            datetime(2025, 1, 15, h, 0, tzinfo=timezone.utc) for h in range(24)  # Winter
        ]

        ts_series = pd.Series(dates)
        features = extractor.extract_time_features(ts_series)

        expected_overlap = features["session_london"] & features["session_ny"]
        np.testing.assert_array_equal(
            features["session_london_ny_overlap"].values,
            expected_overlap.values,
            err_msg="London-NY overlap is inconsistent with underlying session flags!",
        )

    def test_asian_session_tokyo(self, extractor: TimeFeatureExtractor):
        """Verify Asian session covers 09:00-18:00 JST (00:00 to 09:00 UTC)."""
        # 04:00 UTC Wednesday = 13:00 JST (Asian session active)
        ts_active = pd.Series([datetime(2025, 6, 11, 4, 0, tzinfo=timezone.utc)])
        assert extractor.extract_time_features(ts_active).iloc[0]["session_asian"] == 1

        # 12:00 UTC Wednesday = 21:00 JST (Asian session closed)
        ts_closed = pd.Series([datetime(2025, 6, 11, 12, 0, tzinfo=timezone.utc)])
        assert extractor.extract_time_features(ts_closed).iloc[0]["session_asian"] == 0

    def test_daily_roll_window_winter_vs_summer(self, extractor: TimeFeatureExtractor):
        """Daily roll break is 17:00-18:00 New York Time: 21:00-22:00 UTC in summer, 22:00-23:00 UTC in winter."""
        # Summer: Tuesday 2025-06-10 21:30 UTC = 17:30 EDT -> Active
        ts_summer = pd.Series([datetime(2025, 6, 10, 21, 30, tzinfo=timezone.utc)])
        assert extractor.extract_time_features(ts_summer).iloc[0]["is_daily_roll_window"] == 1

        # Winter: Tuesday 2025-01-14 22:30 UTC = 17:30 EST -> Active
        ts_winter = pd.Series([datetime(2025, 1, 14, 22, 30, tzinfo=timezone.utc)])
        assert extractor.extract_time_features(ts_winter).iloc[0]["is_daily_roll_window"] == 1

        # Non-roll hour: Tuesday 2025-06-10 18:00 UTC = 14:00 EDT -> Inactive
        ts_inactive = pd.Series([datetime(2025, 6, 10, 18, 0, tzinfo=timezone.utc)])
        assert extractor.extract_time_features(ts_inactive).iloc[0]["is_daily_roll_window"] == 0

    def test_friday_close_and_sunday_open(self, extractor: TimeFeatureExtractor):
        """Friday close approaching (14:00-17:00 NY) and Sunday open (>= 18:00 NY)."""
        # Friday 15:30 EDT (19:30 UTC) in Summer
        ts_fri = pd.Series([datetime(2025, 6, 13, 19, 30, tzinfo=timezone.utc)])
        f_fri = extractor.extract_time_features(ts_fri).iloc[0]
        assert f_fri["is_friday_close_approaching"] == 1
        assert f_fri["is_sunday_open"] == 0

        # Sunday 18:05 EDT (22:05 UTC) in Summer
        ts_sun = pd.Series([datetime(2025, 6, 15, 22, 5, tzinfo=timezone.utc)])
        f_sun = extractor.extract_time_features(ts_sun).iloc[0]
        assert f_sun["is_sunday_open"] == 1
        assert f_sun["is_friday_close_approaching"] == 0
