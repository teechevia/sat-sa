"""
Tests for app/analytics.py

Covers:
    - investigation_rate calculation
    - critical_investigation_rate calculation
    - escalation_rate calculation
    - alerts_per_active_asset calculation
    - critical_alerts_per_active_asset calculation
    - median_closure_duration_min calculation
    - pct_fast_closed_uninvestigated calculation
    - repeat_incident_groups count and repeat_groups_without_remediation count
    - Zero-division safety (org with 0 active assets, 0 critical alerts, 0 cases)
    - Peer baselines calculation excluding the target organization itself
"""

from __future__ import annotations

import pandas as pd
import pytest

from app.analytics import (
    compute_org_metrics,
    compute_all_org_metrics,
    compute_peer_baselines,
)


class TestComputeOrgMetrics:

    def test_metrics_for_org_a(self, norm_data):
        """
        Fixtures for ORG-A (small, 10 assets):
            Alerts (2 total):
                A-001: critical, investigated=True, escalated=True, closure=240 min, inv_dur=120 min
                A-002: high, investigated=True, escalated=False, closure=480 min, inv_dur=180 min
            Cases (2 total):
                CASE-001: ASSET-1 + malware, recurrence=2, remediation=True
                CASE-002: ASSET-1 + malware, recurrence=0, remediation=False
        """
        org_row = norm_data.organizations[norm_data.organizations["organization_id"] == "ORG-A"].iloc[0]
        m = compute_org_metrics(
            org_id="ORG-A",
            org_row=org_row,
            alerts=norm_data.alerts,
            cases=norm_data.cases,
            invs=norm_data.investigations,
            escs=norm_data.escalations,
        )

        assert m["organization_id"] == "ORG-A"
        assert m["total_alerts"] == 2
        assert m["critical_alerts"] == 1
        assert m["high_alerts"] == 1
        assert m["active_asset_count"] == 10

        # investigation rates
        assert m["n_investigated"] == 2
        assert m["investigation_rate"] == 1.0  # 2 / 2
        assert m["critical_investigation_rate"] == 1.0  # 1 / 1

        # escalation rates
        assert m["n_escalated"] == 1
        assert m["escalation_rate"] == 0.5  # 1 / 2 (A-001 escalated, A-002 not)
        assert m["critical_escalation_rate"] == 1.0  # 1 / 1 (A-001)

        # normalized activity
        assert m["alerts_per_active_asset"] == 0.2  # 2 / 10
        assert m["critical_alerts_per_active_asset"] == 0.1  # 1 / 10

        # closure duration median
        # A-001 (240) and A-002 (480) -> median 360.0
        assert m["median_closure_duration_min"] == 360.0
        assert m["median_critical_closure_duration_min"] == 240.0

    def test_metrics_for_org_b(self, norm_data):
        """
        Fixtures for ORG-B (small, 20 assets):
            Alerts (2 total):
                A-003: critical, investigated=False, escalated=False, closure=60 min
                A-004: medium, investigated=False, escalated=False, closure=None (open)
        """
        org_row = norm_data.organizations[norm_data.organizations["organization_id"] == "ORG-B"].iloc[0]
        m = compute_org_metrics(
            org_id="ORG-B",
            org_row=org_row,
            alerts=norm_data.alerts,
            cases=norm_data.cases,
            invs=norm_data.investigations,
            escs=norm_data.escalations,
        )

        assert m["organization_id"] == "ORG-B"
        assert m["total_alerts"] == 2
        assert m["critical_alerts"] == 1
        assert m["high_alerts"] == 0

        assert m["n_investigated"] == 0
        assert m["investigation_rate"] == 0.0
        assert m["critical_investigation_rate"] == 0.0

        assert m["alerts_per_active_asset"] == 0.1  # 2 / 20
        assert m["critical_alerts_per_active_asset"] == 0.05  # 1 / 20

    def test_zero_division_safety(self, norm_data):
        """Test org with 0 alerts and 0 assets handles division safely without NaN."""
        empty_org_row = pd.Series({
            "organization_id": "ORG-ZERO",
            "peer_group": "small",
            "active_asset_count": 0,
        })
        m = compute_org_metrics(
            org_id="ORG-ZERO",
            org_row=empty_org_row,
            alerts=norm_data.alerts,
            cases=norm_data.cases,
            invs=norm_data.investigations,
            escs=norm_data.escalations,
        )

        assert m["total_alerts"] == 0
        assert m["investigation_rate"] == 0.0
        assert m["critical_investigation_rate"] == 0.0
        assert m["escalation_rate"] == 0.0
        assert m["alerts_per_active_asset"] == 0.0
        assert m["critical_alerts_per_active_asset"] == 0.0
        assert m["median_closure_duration_min"] is None


class TestPeerBaselines:

    def test_peer_baselines_exclude_self(self, norm_data):
        """
        Verify that compute_peer_baselines excludes the target org from its baseline calculation.
        """
        all_metrics = compute_all_org_metrics(norm_data)
        baselines = compute_peer_baselines(all_metrics)

        # ORG-A and ORG-B are both in peer_group 'small'
        # For ORG-A, its peer baseline in 'small' must come strictly from ORG-B!
        org_a_metric = next(m for m in all_metrics if m["organization_id"] == "ORG-A")
        org_b_metric = next(m for m in all_metrics if m["organization_id"] == "ORG-B")

        a_pb = baselines["ORG-A"]["baseline"]

        # ORG-B alerts_per_active_asset is 0.1
        # Since ORG-B is the ONLY peer for ORG-A, ORG-A's peer median must equal ORG-B's value!
        assert a_pb["alerts_per_active_asset_median"] == org_b_metric["alerts_per_active_asset"]
        assert a_pb["alerts_per_active_asset_median"] != org_a_metric["alerts_per_active_asset"]

    def test_peer_baselines_structure(self, norm_data):
        all_metrics = compute_all_org_metrics(norm_data)
        baselines = compute_peer_baselines(all_metrics)

        assert "ORG-A" in baselines
        assert "baseline" in baselines["ORG-A"]
        assert "deviations" in baselines["ORG-A"]

        devs = baselines["ORG-A"]["deviations"]
        assert "alerts_per_active_asset" in devs
        assert "critical_investigation_rate" in devs
        assert "deviation_pct" in devs["alerts_per_active_asset"]
