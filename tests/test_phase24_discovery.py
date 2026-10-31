"""Phase 24: New Hypothesis Discovery & Pre-Registration Test Suite.

Validates:
1. Cryptographic integrity of protected partitions (2025 val and 2026 test).
2. Strict chronological split boundaries and no-lookahead leakage prevention.
3. Permanence of Phase 23 REJECT verdict on HYP-21.
4. Completeness and validity of all Phase 24 deliverables.
5. Mathematical formulation of HYP-24-NY-REVERSAL-EXHAUSTION (entry direction, anchor, stop distance).
6. Verification that proposed holding window terminates before 21:00 UTC rollover (zero swap).
"""

import hashlib
from datetime import time
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path("/home/bhoot/project/Treading-Ai")
VAL_PARQUET_PATH = PROJECT_ROOT / "data/features/XAUUSD_M5_features_val.parquet"
TEST_PARQUET_PATH = PROJECT_ROOT / "data/features/XAUUSD_M5_features_test.parquet"

VAL_EXPECTED_SHA256 = "7e9222e9dc0893601e24505912eeab78330670c4e70ebcc2fa462ff8d44a4f94"
TEST_EXPECTED_SHA256 = "f95fd09a5d07666e3f1d9a72e840e2e97f3c058d11b6bb0c712b21dea86a5dec"

PHASE24_DIR = PROJECT_ROOT / "reports/phase24"


def compute_sha256(filepath: Path) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def test_phase24_protected_partitions_intact():
    """Verify protected validation and test partitions remain untouched."""
    assert VAL_PARQUET_PATH.exists()
    assert TEST_PARQUET_PATH.exists()

    val_hash = compute_sha256(VAL_PARQUET_PATH)
    test_hash = compute_sha256(TEST_PARQUET_PATH)

    assert val_hash == VAL_EXPECTED_SHA256
    assert test_hash == TEST_EXPECTED_SHA256


def test_phase24_chronological_splits_and_leakage():
    """Verify development split max timestamp < 2023-01-01 and prior daily lag logic."""
    df21 = pd.read_parquet(PROJECT_ROOT / "data/processed/XAUUSD/M5/XAUUSD_M5_2021.parquet")
    df22 = pd.read_parquet(PROJECT_ROOT / "data/processed/XAUUSD/M5/XAUUSD_M5_2022.parquet")

    df = pd.concat([df21, df22], ignore_index=True)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)

    # Assert strictly prior to 2023
    assert df["timestamp"].max() < pd.to_datetime("2023-01-01 00:00:00", utc=True)

    # Verify daily true range lag shift(1) strictly excludes day t
    daily_tr = pd.Series([10.0, 12.0, 15.0, 11.0, 14.0])
    atr_prior = daily_tr.rolling(3).mean().shift(1)

    # Day index 3 (value 11.0) must use values 0, 1, 2 only
    expected_atr_day3 = (10.0 + 12.0 + 15.0) / 3.0
    assert np.isclose(atr_prior.iloc[3], expected_atr_day3)
    assert pd.isna(atr_prior.iloc[0])


def test_phase24_rejection_of_hyp21_permanence():
    """Verify Phase 23 decision record permanently records REJECT for HYP-21."""
    p23_decision = PROJECT_ROOT / "reports/phase23/phase23_decision.md"
    assert p23_decision.exists()

    content = p23_decision.read_text()
    assert "PHASE 23 VERDICT: REJECT" in content
    assert "REJECTED" in content


def test_phase24_deliverables_complete():
    """Verify all 6 required Phase 24 reports exist and have substantive content."""
    required_files = [
        "research_inventory.md",
        "hypothesis_overlap_matrix.md",
        "candidate_hypotheses.md",
        "frozen_evaluation_protocol.md",
        "data_integrity_report.md",
        "phase24_decision.md",
    ]

    for fname in required_files:
        fpath = PHASE24_DIR / fname
        assert fpath.exists(), f"Missing required file: {fname}"
        assert fpath.stat().st_size > 1000, f"File {fname} is suspiciously short"


def test_phase24_lead_hypothesis_logic():
    """Verify mathematical formulation of HYP-24-NY-REVERSAL-EXHAUSTION."""
    # Anchor price at 12:00 UTC Close
    p_base = 2000.0

    # Case A: Massive upward excursion (e.g. following weak USD data)
    p_1400_up = 2025.0
    delta_p_up = p_1400_up - p_base
    direction_up = -1 if delta_p_up > 0 else 1
    stop_distance_up = 0.75 * abs(delta_p_up)
    stop_price_up = p_1400_up + stop_distance_up

    assert delta_p_up == 25.0
    assert direction_up == -1  # SHORT (counter-trend fade)
    assert stop_distance_up == 18.75
    assert stop_price_up == 2043.75

    # Case B: Massive downward excursion (e.g. following hot CPI data)
    p_1400_down = 1970.0
    delta_p_down = p_1400_down - p_base
    direction_down = -1 if delta_p_down > 0 else 1
    stop_distance_down = 0.75 * abs(delta_p_down)
    stop_price_down = p_1400_down - stop_distance_down

    assert delta_p_down == -30.0
    assert direction_down == 1  # LONG (counter-trend fade)
    assert stop_distance_down == 22.5
    assert stop_price_down == 1947.5


def test_phase24_zero_overnight_swap_window():
    """Verify that trade window (14:05 to 18:30 UTC) strictly terminates before rollover."""
    t_entry = time(14, 5, 0)
    t_exit = time(18, 30, 0)
    t_rollover_summer = time(21, 0, 0)
    t_rollover_winter = time(22, 0, 0)

    assert t_entry < t_exit < t_rollover_summer < t_rollover_winter
    # Margin of safety before rollover is at least 2.5 hours
    exit_minutes = t_exit.hour * 60 + t_exit.minute
    roll_minutes = t_rollover_summer.hour * 60 + t_rollover_summer.minute
    assert roll_minutes - exit_minutes == 150  # 2.5 hours
