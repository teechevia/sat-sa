"""
Tests for app/findings.py

Covers:
    - Additive priority scoring system
    - Priority rank assignment (HIGH, MEDIUM, LOW)
    - Sequential ID assignment (F-001, F-002, ...)
    - Transparent priority scoring breakdown in evidence
    - Sorting by priority rank and score
    - Finding lookups and store functionality
"""

from __future__ import annotations

from datetime import datetime, timezone
import pytest

from app.findings import build_findings, get_all_findings, get_finding, score_finding
from app.models import Finding, FindingType, Priority


def _make_raw_finding(finding_type: FindingType, org_id: str = "ORG-TEST", evidence: dict | None = None) -> Finding:
    return Finding(
        finding_id="",
        organization_id=org_id,
        finding_type=finding_type,
        priority=Priority.LOW,
        title="Test Finding Title",
        description="Test description for supervisory assessment",
        evidence=evidence or {},
        affected_record_ids=["A-001", "A-002"],
        assessor_guidance="Test assessor guidance string",
        rule_id="RULE-TEST",
        priority_score=0,
        generated_at=datetime.now(timezone.utc),
    )


class TestPriorityScoring:

    def test_execution_gap_high_missing_rate_scores_high(self):
        """Execution gap (critical severity = +2, missing rate 60% = +2, no inv evidence = +1 -> total 5 -> HIGH)."""
        f = _make_raw_finding(
            FindingType.EXECUTION_GAP,
            evidence={"observed_missing_rate": 0.60, "total_critical_alerts": 100}
        )
        score, priority, breakdown = score_finding(f)

        assert score >= 4
        assert priority == Priority.HIGH
        assert len(breakdown) >= 3
        assert any("Critical severity is involved" in b for b in breakdown)

    def test_suspicious_fast_closure_scoring(self):
        """Fast closure with critical alerts (+2), flagged rate 40% (+1), no inv (+1), combined signals (+1) -> total 5 -> HIGH."""
        f = _make_raw_finding(
            FindingType.SUSPICIOUS_FAST_CLOSURE,
            evidence={
                "observed_flagged_rate": 0.40,
                "severity_breakdown": {"critical_flagged": 5, "high_flagged": 10}
            }
        )
        score, priority, breakdown = score_finding(f)

        assert score >= 4
        assert priority == Priority.HIGH

    def test_peer_deviation_large_deviation_scores_high(self):
        """Peer deviation > 60% (+2), peer dev (+2), critical inv rate low (+1) -> total 5 -> HIGH."""
        f = _make_raw_finding(
            FindingType.PEER_DEVIATION,
            evidence={
                "metric_name": "alerts_per_active_asset",
                "deviation_pct": -86.3,
                "contextual_metrics": {"critical_investigation_rate": 0.85}
            }
        )
        score, priority, breakdown = score_finding(f)

        assert score >= 4
        assert priority == Priority.HIGH

    def test_medium_priority_scoring(self):
        """Repeated incidents with 1 group (+1 assets +1 absence +1 combined -> total 3 -> MEDIUM)."""
        f = _make_raw_finding(
            FindingType.REPEATED_INCIDENTS,
            evidence={"flagged_group_count": 1}
        )
        score, priority, breakdown = score_finding(f)

        assert score in (2, 3)
        assert priority == Priority.MEDIUM


class TestFindingBuilderAndStore:

    def test_build_findings_assigns_sequential_ids_and_sorts(self):
        """Verifies F-001, F-002 IDs, priority assignment, and sorting HIGH -> MEDIUM -> LOW."""
        f_high = _make_raw_finding(
            FindingType.EXECUTION_GAP,
            org_id="ORG-1",
            evidence={"observed_missing_rate": 0.65}
        )
        f_medium = _make_raw_finding(
            FindingType.REPEATED_INCIDENTS,
            org_id="ORG-2",
            evidence={"flagged_group_count": 1}
        )

        built = build_findings([f_medium, f_high])

        assert len(built) == 2
        # First finding should be HIGH priority
        assert built[0].priority == Priority.HIGH
        assert built[0].finding_id == "F-001"
        assert built[1].priority == Priority.MEDIUM
        assert built[1].finding_id == "F-002"

        # Evidence should contain priority_scoring_breakdown
        assert "priority_scoring_breakdown" in built[0].evidence
        assert built[0].priority_score > 0

    def test_get_finding_and_get_all_findings(self):
        f = _make_raw_finding(
            FindingType.EXECUTION_GAP,
            org_id="ORG-1",
            evidence={"observed_missing_rate": 0.65}
        )
        build_findings([f])

        all_f = get_all_findings()
        assert len(all_f) == 1
        assert all_f[0].finding_id == "F-001"

        single = get_finding("F-001")
        assert single is not None
        assert single.organization_id == "ORG-1"

        unknown = get_finding("F-999")
        assert unknown is None
