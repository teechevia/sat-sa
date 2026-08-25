"""
False-Positive and Edge-Case Tests (Stage 4)
============================================
Tests boundary conditions and edge cases to ensure rules fail safely without
crashing or generating false-positive findings.

Edge cases covered:
    - Zero critical alerts (Rule 1 does not trigger or crash)
    - Zero active assets (Analytics & Rule 4 handle zero-division safely)
    - No investigation records in table (handled safely)
    - No cases in table (Rule 3 returns None safely)
    - Peer baseline equal to zero (Rule 4 handles zero-division safely)
    - Fast closure WITH investigation present (Rule 2 does NOT trigger)
    - Fast closure WITHOUT investigation (Rule 2 triggers properly)
    - Repeated incidents where at least one case has remediation_evidence=True (Rule 3 does NOT trigger)
    - Organization with legitimate activity close to peer median (Rule 4 does NOT trigger)
"""

from __future__ import annotations

import pandas as pd
import pytest

from app.rules import (
    run_execution_gap_rule,
    run_fast_closure_rule,
    run_repeated_incidents_rule,
    run_peer_deviation_rule,
)


class TestEdgeCasesAndFalsePositives:

    def test_zero_critical_alerts(self):
        """Org with 0 critical alerts -> Rule 1 returns None without error."""
        df = pd.DataFrame([
            {"alert_id": "A-01", "organization_id": "ORG-1", "severity": "low", "investigated": False},
            {"alert_id": "A-02", "organization_id": "ORG-1", "severity": "medium", "investigated": False},
        ])
        finding = run_execution_gap_rule("ORG-1", df)
        assert finding is None

    def test_empty_alerts_dataframe(self):
        """Empty alerts DataFrame -> Rule 1 and Rule 2 return None safely."""
        df = pd.DataFrame(columns=["alert_id", "organization_id", "severity", "investigated", "closed_at", "created_at", "closure_duration_min"])
        assert run_execution_gap_rule("ORG-EMPTY", df) is None
        assert run_fast_closure_rule("ORG-EMPTY", df) is None

    def test_empty_cases_dataframe(self):
        """Empty cases DataFrame -> Rule 3 returns None safely."""
        df = pd.DataFrame(columns=["case_id", "organization_id", "asset_id", "incident_type", "remediation_evidence"])
        assert run_repeated_incidents_rule("ORG-EMPTY", df) is None

    def test_zero_peer_baseline(self):
        """Peer baseline median is 0.0 -> Rule 4 handles division safely and returns None."""
        org_metric = {"organization_id": "ORG-1", "peer_group": "small"}
        peer_baseline = {
            "baseline": {"n_peers": 2},
            "deviations": {
                "alerts_per_active_asset": {
                    "org_value": 0.0,
                    "peer_median": 0.0,
                    "deviation_pct": None,
                    "direction": None,
                }
            }
        }
        org_alerts = pd.DataFrame()
        assert run_peer_deviation_rule("ORG-1", org_metric, peer_baseline, org_alerts) is None

    def test_fast_closure_with_investigation_present_is_not_flagged(self):
        """Alerts closed in 3 min, but EVERY alert was investigated -> Rule 2 returns None."""
        alerts_data = []
        for i in range(1, 11):
            alerts_data.append({
                "alert_id": f"A-{i:03d}",
                "organization_id": "ORG-FAST-INV",
                "severity": "critical",
                "investigated": True,  # Properly investigated!
                "closure_duration_min": 3.0,
                "closed_at": "2025-01-01T10:03:00",
                "created_at": "2025-01-01T10:00:00",
            })
        df = pd.DataFrame(alerts_data)

        finding = run_fast_closure_rule("ORG-FAST-INV", df)
        assert finding is None

    def test_fast_closure_without_investigation_is_flagged(self):
        """Alerts closed in 3 min WITHOUT investigation -> Rule 2 triggers."""
        alerts_data = []
        for i in range(1, 11):
            alerts_data.append({
                "alert_id": f"A-{i:03d}",
                "organization_id": "ORG-FAST-NOINV",
                "severity": "critical",
                "investigated": False,  # Uninvestigated fast closure!
                "closure_duration_min": 3.0,
                "closed_at": "2025-01-01T10:03:00",
                "created_at": "2025-01-01T10:00:00",
            })
        df = pd.DataFrame(alerts_data)

        finding = run_fast_closure_rule("ORG-FAST-NOINV", df)
        assert finding is not None

    def test_repeated_incidents_with_remediation_true_not_flagged(self):
        """Asset with 5 repeat cases where 1 case has remediation_evidence=True -> Rule 3 returns None."""
        cases_data = [
            {"case_id": "C-01", "asset_id": "ASSET-X", "incident_type": "phishing", "remediation_evidence": False},
            {"case_id": "C-02", "asset_id": "ASSET-X", "incident_type": "phishing", "remediation_evidence": False},
            {"case_id": "C-03", "asset_id": "ASSET-X", "incident_type": "phishing", "remediation_evidence": False},
            {"case_id": "C-04", "asset_id": "ASSET-X", "incident_type": "phishing", "remediation_evidence": False},
            {"case_id": "C-05", "asset_id": "ASSET-X", "incident_type": "phishing", "remediation_evidence": True},  # Documented remediation
        ]
        df = pd.DataFrame(cases_data)

        finding = run_repeated_incidents_rule("ORG-SAFE", df)
        assert finding is None

    def test_legitimate_activity_close_to_peer_median_not_flagged(self):
        """Org activity 3.1 alerts/asset vs peer median 3.21 (3.4% deviation) -> Rule 4 returns None."""
        org_metric = {"organization_id": "ORG-HEALTHY", "peer_group": "large"}
        peer_baseline = {
            "baseline": {"n_peers": 3},
            "deviations": {
                "alerts_per_active_asset": {
                    "org_value": 3.1,
                    "peer_median": 3.21,
                    "deviation_pct": -3.4,
                    "direction": "below",
                }
            }
        }
        org_alerts = pd.DataFrame([{"alert_id": "A-001"}])

        finding = run_peer_deviation_rule("ORG-HEALTHY", org_metric, peer_baseline, org_alerts)
        assert finding is None
