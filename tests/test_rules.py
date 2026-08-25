"""
Tests for app/rules.py

Covers:
    - Rule 1 (Execution Gap): threshold triggering, uninvestigated critical alert collection, cautious wording.
    - Rule 2 (Suspicious Fast Closure): fast closure + uninvestigated combination, threshold rate, severity breakdown.
    - Rule 3 (Repeated Incidents): grouping by (asset_id, incident_type), recurrence threshold, remediation evidence check.
    - Rule 4 (Peer Activity Deviation): normalized activity metric deviation from peer median, negative space wording.
"""

from __future__ import annotations

import pandas as pd
import pytest

from app.rules import (
    run_execution_gap_rule,
    run_fast_closure_rule,
    run_repeated_incidents_rule,
    run_peer_deviation_rule,
    run_all_rules,
)
from app.models import FindingType


class TestRule1ExecutionGap:

    def test_execution_gap_triggers_when_above_threshold(self):
        """10 critical alerts, 6 uninvestigated (60% missing rate) -> triggers Rule 1."""
        alerts_data = []
        for i in range(1, 11):
            alerts_data.append({
                "alert_id": f"A-{i:03d}",
                "organization_id": "ORG-TEST",
                "severity": "critical",
                "investigated": (i <= 4),  # 4 investigated, 6 missing -> 60% missing
                "closed_at": "2025-01-01T12:00:00",
                "created_at": "2025-01-01T10:00:00",
            })
        df = pd.DataFrame(alerts_data)

        finding = run_execution_gap_rule("ORG-TEST", df, threshold=0.40)

        assert finding is not None
        assert finding.finding_type == FindingType.EXECUTION_GAP
        assert finding.organization_id == "ORG-TEST"
        assert finding.rule_id == "RULE-1"
        assert len(finding.affected_record_ids) == 6
        assert "Potential execution gap" in finding.description
        assert finding.evidence["observed_missing_rate"] == 0.6

    def test_execution_gap_does_not_trigger_below_threshold(self):
        """10 critical alerts, 2 uninvestigated (20% missing rate) -> below 0.40 threshold -> None."""
        alerts_data = []
        for i in range(1, 11):
            alerts_data.append({
                "alert_id": f"A-{i:03d}",
                "organization_id": "ORG-TEST",
                "severity": "critical",
                "investigated": (i <= 8),  # 8 investigated, 2 missing -> 20% missing
                "closed_at": "2025-01-01T12:00:00",
                "created_at": "2025-01-01T10:00:00",
            })
        df = pd.DataFrame(alerts_data)

        finding = run_execution_gap_rule("ORG-TEST", df, threshold=0.40)
        assert finding is None


class TestRule2FastClosure:

    def test_fast_closure_triggers_when_uninvestigated_and_fast(self):
        """10 critical/high alerts, 3 closed in 5 min and uninvestigated (30% rate) -> triggers Rule 2."""
        alerts_data = []
        for i in range(1, 11):
            is_fast_uninv = (i <= 3)
            alerts_data.append({
                "alert_id": f"A-{i:03d}",
                "organization_id": "ORG-TEST",
                "severity": "critical" if i % 2 == 1 else "high",
                "investigated": not is_fast_uninv,
                "closure_duration_min": 5.0 if is_fast_uninv else 120.0,
                "closed_at": "2025-01-01T10:05:00" if is_fast_uninv else "2025-01-01T12:00:00",
                "created_at": "2025-01-01T10:00:00",
            })
        df = pd.DataFrame(alerts_data)

        finding = run_fast_closure_rule("ORG-TEST", df, fast_minutes=10, threshold_rate=0.20)

        assert finding is not None
        assert finding.finding_type == FindingType.SUSPICIOUS_FAST_CLOSURE
        assert len(finding.affected_record_ids) == 3
        assert finding.evidence["observed_flagged_rate"] == 0.3

    def test_fast_closure_does_not_trigger_if_investigated(self):
        """Alerts closed in 5 min BUT investigated -> not flagged."""
        alerts_data = []
        for i in range(1, 11):
            alerts_data.append({
                "alert_id": f"A-{i:03d}",
                "organization_id": "ORG-TEST",
                "severity": "critical",
                "investigated": True,  # All investigated even though fast closed
                "closure_duration_min": 5.0,
                "closed_at": "2025-01-01T10:05:00",
                "created_at": "2025-01-01T10:00:00",
            })
        df = pd.DataFrame(alerts_data)

        finding = run_fast_closure_rule("ORG-TEST", df, fast_minutes=10, threshold_rate=0.20)
        assert finding is None


class TestRule3RepeatedIncidents:

    def test_repeated_incidents_triggers_when_remediation_false(self):
        """Group of 4 cases for ASSET-1 + malware, all remediation_evidence=False -> triggers Rule 3."""
        cases_data = [
            {"case_id": "C-01", "asset_id": "ASSET-1", "incident_type": "malware", "remediation_evidence": False},
            {"case_id": "C-02", "asset_id": "ASSET-1", "incident_type": "malware", "remediation_evidence": False},
            {"case_id": "C-03", "asset_id": "ASSET-1", "incident_type": "malware", "remediation_evidence": False},
            {"case_id": "C-04", "asset_id": "ASSET-1", "incident_type": "malware", "remediation_evidence": False},
        ]
        df = pd.DataFrame(cases_data)

        finding = run_repeated_incidents_rule("ORG-TEST", df, min_repeat_count=3)

        assert finding is not None
        assert finding.finding_type == FindingType.REPEATED_INCIDENTS
        assert len(finding.affected_record_ids) == 4
        assert finding.evidence["flagged_group_count"] == 1
        assert finding.evidence["worst_repeated_group"]["case_count"] == 4

    def test_repeated_incidents_does_not_trigger_if_any_remediation_true(self):
        """Group of 4 cases where 1 has remediation_evidence=True -> not flagged."""
        cases_data = [
            {"case_id": "C-01", "asset_id": "ASSET-1", "incident_type": "malware", "remediation_evidence": False},
            {"case_id": "C-02", "asset_id": "ASSET-1", "incident_type": "malware", "remediation_evidence": False},
            {"case_id": "C-03", "asset_id": "ASSET-1", "incident_type": "malware", "remediation_evidence": False},
            {"case_id": "C-04", "asset_id": "ASSET-1", "incident_type": "malware", "remediation_evidence": True},  # Remediation documented!
        ]
        df = pd.DataFrame(cases_data)

        finding = run_repeated_incidents_rule("ORG-TEST", df, min_repeat_count=3)
        assert finding is None


class TestRule4PeerDeviation:

    def test_peer_deviation_triggers_on_activity_gap(self):
        """Org with 0.5 alerts/asset vs peer median of 3.0 (83% deviation) -> triggers Rule 4."""
        org_metric = {
            "organization_id": "ORG-TEST",
            "peer_group": "large",
            "critical_investigation_rate": 0.90,
            "escalation_rate": 0.20,
        }
        peer_baseline = {
            "baseline": {"n_peers": 3},
            "deviations": {
                "alerts_per_active_asset": {
                    "org_value": 0.5,
                    "peer_median": 3.0,
                    "deviation_pct": -83.3,
                    "direction": "below",
                }
            }
        }
        org_alerts = pd.DataFrame([{"alert_id": "A-001"}])

        finding = run_peer_deviation_rule("ORG-TEST", org_metric, peer_baseline, org_alerts, threshold_deviation=0.40)

        assert finding is not None
        assert finding.finding_type == FindingType.PEER_DEVIATION
        assert finding.evidence["deviation_pct"] == -83.3
        assert "Potential activity gap" in finding.description

    def test_peer_deviation_does_not_trigger_within_threshold(self):
        """Org with 2.8 alerts/asset vs peer median 3.0 (6.7% deviation) -> None."""
        org_metric = {"organization_id": "ORG-TEST", "peer_group": "large"}
        peer_baseline = {
            "baseline": {"n_peers": 3},
            "deviations": {
                "alerts_per_active_asset": {
                    "org_value": 2.8,
                    "peer_median": 3.0,
                    "deviation_pct": -6.7,
                    "direction": "below",
                }
            }
        }
        org_alerts = pd.DataFrame([{"alert_id": "A-001"}])

        finding = run_peer_deviation_rule("ORG-TEST", org_metric, peer_baseline, org_alerts, threshold_deviation=0.40)
        assert finding is None
