"""
Shared pytest fixtures for SAT-SA Stage 3 tests.

Small, controlled DataFrames that do NOT require the generated CSVs.
These are the foundation for all unit tests in test_validator,
test_normalizer, and test_analytics.

Integration tests (test_ground_truth.py) use session-scoped fixtures
that load the actual generated dataset.
"""

from __future__ import annotations

import pytest
import pandas as pd

from app.data_loader import RawData
from app.normalizer import normalize_all, NormalizedData


# ---------------------------------------------------------------------------
# Minimal raw DataFrames (all strings — same layout as CSV files)
# ---------------------------------------------------------------------------

@pytest.fixture
def raw_orgs() -> pd.DataFrame:
    return pd.DataFrame({
        "organization_id":    ["ORG-A", "ORG-B", "ORG-C", "ORG-D"],
        "name":               ["Alpha", "Beta", "Gamma", "Delta"],
        "size":               ["small", "small", "medium", "medium"],
        "sector":             ["finance", "energy", "health", "telecom"],
        "peer_group":         ["small", "small", "medium", "medium"],
        "active_asset_count": ["10", "20", "50", "60"],
    })


@pytest.fixture
def raw_cases() -> pd.DataFrame:
    return pd.DataFrame({
        "case_id":              ["CASE-001", "CASE-002", "CASE-003"],
        "organization_id":      ["ORG-A", "ORG-A", "ORG-B"],
        "asset_id":             ["ASSET-1", "ASSET-1", "ASSET-5"],
        "incident_type":        ["malware", "malware", "phishing"],
        "opened_at":            ["2025-01-01T09:00:00", "2025-01-10T09:00:00",
                                 "2025-02-01T09:00:00"],
        "closed_at":            ["2025-01-05T09:00:00", "", "2025-02-05T09:00:00"],
        "recurrence_count":     ["2", "0", "1"],
        "remediation_evidence": ["True", "False", "True"],
    })


@pytest.fixture
def raw_alerts() -> pd.DataFrame:
    """
    Four alerts:
        A-001: ORG-A, critical  — has investigation INV-001, escalation ESC-001
        A-002: ORG-A, high      — has investigation INV-002, no escalation
        A-003: ORG-B, critical  — NO investigation, NO escalation
        A-004: ORG-B, medium    — NO investigation, NO escalation
    """
    return pd.DataFrame({
        "alert_id":        ["A-001", "A-002", "A-003", "A-004"],
        "organization_id": ["ORG-A", "ORG-A", "ORG-B", "ORG-B"],
        "severity":        ["critical", "high", "critical", "medium"],
        "incident_type":   ["malware", "phishing", "malware", "recon"],
        "asset_id":        ["ASSET-1", "ASSET-2", "ASSET-5", "ASSET-6"],
        "case_id":         ["CASE-001", "", "", "CASE-003"],
        "created_at":      [
            "2025-01-01T10:00:00",
            "2025-01-02T10:00:00",
            "2025-01-03T10:00:00",
            "2025-01-04T10:00:00",
        ],
        "closed_at": [
            "2025-01-01T14:00:00",   # 240 min closure
            "2025-01-02T18:00:00",   # 480 min closure
            "2025-01-03T11:00:00",   # 60 min closure
            "",                       # still open
        ],
    })


@pytest.fixture
def raw_investigations() -> pd.DataFrame:
    """A-001 and A-002 have investigations. A-003 and A-004 do NOT."""
    return pd.DataFrame({
        "investigation_id": ["INV-001", "INV-002"],
        "alert_id":         ["A-001", "A-002"],
        "organization_id":  ["ORG-A", "ORG-A"],
        "analyst_id":       ["ANALYST-01", "ANALYST-02"],
        "started_at":       ["2025-01-01T10:30:00", "2025-01-02T11:00:00"],
        "completed_at":     ["2025-01-01T12:30:00", "2025-01-02T14:00:00"],
        "notes_length":     ["300", "450"],
        "outcome":          ["resolved", "escalated"],
    })
    # INV-001 duration: 120 min
    # INV-002 duration: 180 min


@pytest.fixture
def raw_escalations() -> pd.DataFrame:
    """Only A-001 has an escalation."""
    return pd.DataFrame({
        "escalation_id":    ["ESC-001"],
        "alert_id":         ["A-001"],
        "organization_id":  ["ORG-A"],
        "escalated_at":     ["2025-01-01T11:00:00"],
        "escalation_level": ["2"],
    })


@pytest.fixture
def raw_data(raw_orgs, raw_alerts, raw_investigations,
             raw_escalations, raw_cases) -> RawData:
    """Convenience fixture — wraps all five raw DataFrames in a RawData."""
    return RawData(
        organizations=raw_orgs,
        alerts=raw_alerts,
        investigations=raw_investigations,
        escalations=raw_escalations,
        cases=raw_cases,
    )


@pytest.fixture
def norm_data(raw_data) -> NormalizedData:
    """Pre-normalized version of raw_data for analytics/normalizer tests."""
    return normalize_all(raw_data)


# ---------------------------------------------------------------------------
# Session-scoped integration fixtures (load the actual generated dataset)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def real_raw_data():
    """Load the actual generated CSVs once per test session."""
    from app.data_loader import load_all
    return load_all(verbose=False)


@pytest.fixture(scope="session")
def real_norm_data(real_raw_data):
    """Normalize the actual dataset once per test session."""
    from app.normalizer import normalize_all
    return normalize_all(real_raw_data)


@pytest.fixture(scope="session")
def real_metrics(real_norm_data):
    """Compute all org metrics from the actual dataset once per session."""
    from app.analytics import compute_all_org_metrics
    return compute_all_org_metrics(real_norm_data)


@pytest.fixture(scope="session")
def real_peer_baselines(real_metrics):
    from app.analytics import compute_peer_baselines
    return compute_peer_baselines(real_metrics)
