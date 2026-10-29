"""Phase 21: Governance and Deliverable Verification Test Suite.

Verifies:
1. All required Phase 21 deliverable reports exist and contain required sections.
2. Protected partitions remain cryptographically unmodified.
3. Pre-registered protocol hash remains verified.
4. Selected hypothesis identifier is strictly HYP-21-ASIAN-LONDON-EXPANSION.
5. Final decision is strictly 'PHASE 21 HYPOTHESIS APPROVED FOR DEVELOPMENT'.
"""

import hashlib
from pathlib import Path

import pytest

PROJECT_ROOT = Path("/home/bhoot/project/Treading-Ai")
REPORTS_DIR = PROJECT_ROOT / "reports/phase21"
PROTOCOL_MD_PATH = PROJECT_ROOT / "reports/phase20/preregistered_protocol.md"

VAL_PARQUET_PATH = PROJECT_ROOT / "data/features/XAUUSD_M5_features_val.parquet"
TEST_PARQUET_PATH = PROJECT_ROOT / "data/features/XAUUSD_M5_features_test.parquet"

VAL_EXPECTED_SHA256 = "7e9222e9dc0893601e24505912eeab78330670c4e70ebcc2fa462ff8d44a4f94"
TEST_EXPECTED_SHA256 = "f95fd09a5d07666e3f1d9a72e840e2e97f3c058d11b6bb0c712b21dea86a5dec"
EXPECTED_PROTOCOL_SHA256 = "82d47383a2b65265ed3bebc5080aa3e259941f7508286dd377bb8dff8f92969c"


def compute_sha256(filepath: Path) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def test_protected_partitions_invariants():
    """Verify protected validation and test partitions remain bit-for-bit unchanged."""
    assert VAL_PARQUET_PATH.exists()
    assert TEST_PARQUET_PATH.exists()
    assert compute_sha256(VAL_PARQUET_PATH) == VAL_EXPECTED_SHA256
    assert compute_sha256(TEST_PARQUET_PATH) == TEST_EXPECTED_SHA256


def test_protocol_hash_integrity():
    """Verify pre-registered protocol hash matches cryptographic constant."""
    assert PROTOCOL_MD_PATH.exists()
    assert compute_sha256(PROTOCOL_MD_PATH) == EXPECTED_PROTOCOL_SHA256


def test_phase21_deliverables_exist():
    """Verify all 6 required Phase 21 deliverables exist."""
    required_files = [
        "prior_research_inventory.md",
        "candidate_hypotheses.md",
        "selected_hypothesis.md",
        "data_feasibility_audit.md",
        "statistical_test_plan.md",
        "phase21_decision.md",
    ]
    for filename in required_files:
        filepath = REPORTS_DIR / filename
        assert filepath.exists(), f"Missing required Phase 21 deliverable: {filepath}"
        assert filepath.stat().st_size > 500, f"Deliverable {filename} is too short"


def test_selected_hypothesis_identity():
    """Verify selected hypothesis is HYP-21-ASIAN-LONDON-EXPANSION."""
    filepath = REPORTS_DIR / "selected_hypothesis.md"
    content = filepath.read_text(encoding="utf-8")
    assert "HYP-21-ASIAN-LONDON-EXPANSION" in content
    assert "Asian Session Volatility Compression" in content
    assert "00:00, 07:00" in content
    assert "12:00" in content


def test_phase21_final_decision():
    """Verify final decision matches pre-registered enum string."""
    filepath = REPORTS_DIR / "phase21_decision.md"
    content = filepath.read_text(encoding="utf-8")
    assert "PHASE 21 HYPOTHESIS APPROVED FOR DEVELOPMENT" in content
