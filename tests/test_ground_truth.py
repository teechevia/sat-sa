"""
Ground-Truth and End-to-End Detection Verification Tests (Stage 4)
===================================================================
Verifies the complete detection engine against the actual synthetic dataset:
    - ORG-002 triggers Rule 1 (EXECUTION_GAP) with HIGH priority
    - ORG-003 triggers Rule 2 (SUSPICIOUS_FAST_CLOSURE) with HIGH priority
    - ORG-004 triggers Rule 3 (REPEATED_INCIDENTS) with HIGH priority
    - ORG-012 triggers Rule 4 (PEER_DEVIATION) with HIGH priority
    - Healthy organizations (ORG-001, ORG-005 to ORG-011) do NOT produce HIGH findings for injected rules
    - Every affected_record_id in every finding exists in the source dataset
    - Every finding contains non-empty evidence and assessor guidance
    - Priority scoring is deterministic
    - Running the detection pipeline twice on the same dataset produces identical findings
"""

from __future__ import annotations

import pytest

from app.rules import run_all_rules
from app.findings import build_findings, get_all_findings
from app.models import Priority, FindingType


@pytest.fixture(scope="module")
def stage4_findings(real_norm_data, real_metrics, real_peer_baselines):
    """Run Stage 4 detection pipeline once for test module."""
    raw_f = run_all_rules(real_norm_data, real_metrics, real_peer_baselines)
    return build_findings(raw_f)


class TestGroundTruthDetections:

    def test_org002_triggers_rule1_execution_gap(self, stage4_findings):
        """ORG-002 must trigger Rule 1 (EXECUTION_GAP) with HIGH priority."""
        f_list = [
            f for f in stage4_findings
            if f.organization_id == "ORG-002" and f.rule_id == "RULE-1"
        ]
        assert len(f_list) == 1, f"Expected 1 RULE-1 finding for ORG-002, got {len(f_list)}"

        f = f_list[0]
        assert f.finding_type == FindingType.EXECUTION_GAP
        assert f.priority == Priority.HIGH
        assert f.priority_score >= 4
        assert len(f.affected_record_ids) > 0
        assert f.evidence["observed_missing_rate"] > 0.50

    def test_org003_triggers_rule2_fast_closure(self, stage4_findings):
        """ORG-003 must trigger Rule 2 (SUSPICIOUS_FAST_CLOSURE) with HIGH priority."""
        f_list = [
            f for f in stage4_findings
            if f.organization_id == "ORG-003" and f.rule_id == "RULE-2"
        ]
        assert len(f_list) == 1, f"Expected 1 RULE-2 finding for ORG-003, got {len(f_list)}"

        f = f_list[0]
        assert f.finding_type == FindingType.SUSPICIOUS_FAST_CLOSURE
        assert f.priority == Priority.HIGH
        assert f.priority_score >= 4
        assert len(f.affected_record_ids) > 0
        assert f.evidence["observed_flagged_rate"] > 0.50

    def test_org004_triggers_rule3_repeated_incidents(self, stage4_findings):
        """ORG-004 must trigger Rule 3 (REPEATED_INCIDENTS) with HIGH priority."""
        f_list = [
            f for f in stage4_findings
            if f.organization_id == "ORG-004" and f.rule_id == "RULE-3"
        ]
        assert len(f_list) == 1, f"Expected 1 RULE-3 finding for ORG-004, got {len(f_list)}"

        f = f_list[0]
        assert f.finding_type == FindingType.REPEATED_INCIDENTS
        assert f.priority == Priority.HIGH
        assert f.evidence["flagged_group_count"] >= 6
        assert len(f.affected_record_ids) >= 18

    def test_org012_triggers_rule4_peer_deviation(self, stage4_findings):
        """ORG-012 must trigger Rule 4 (PEER_DEVIATION) with HIGH priority."""
        f_list = [
            f for f in stage4_findings
            if f.organization_id == "ORG-012" and f.rule_id == "RULE-4"
        ]
        assert len(f_list) == 1, f"Expected 1 RULE-4 finding for ORG-012, got {len(f_list)}"

        f = f_list[0]
        assert f.finding_type == FindingType.PEER_DEVIATION
        assert f.priority == Priority.HIGH
        assert abs(f.evidence["deviation_pct"]) > 60.0

    def test_healthy_orgs_do_not_produce_high_findings_from_injected_patterns(self, stage4_findings):
        """Healthy orgs (ORG-001, ORG-005..ORG-011) should have NO HIGH priority findings."""
        healthy_org_ids = {"ORG-001", "ORG-005", "ORG-006", "ORG-007", "ORG-008", "ORG-009", "ORG-010", "ORG-011"}
        for f in stage4_findings:
            if f.organization_id in healthy_org_ids:
                assert f.priority != Priority.HIGH, f"{f.organization_id} produced unexpected HIGH finding: {f.title}"

    def test_affected_record_ids_exist_in_source_dataset(self, stage4_findings, real_norm_data):
        """Verify that every affected_record_id in every finding exists in the source alerts/cases."""
        alert_id_set = set(real_norm_data.alerts["alert_id"])
        case_id_set = set(real_norm_data.cases["case_id"])
        valid_record_ids = alert_id_set | case_id_set

        for f in stage4_findings:
            for rec_id in f.affected_record_ids:
                assert rec_id in valid_record_ids, f"Finding {f.finding_id} references non-existent record ID '{rec_id}'"

    def test_findings_contain_required_evidence_and_guidance(self, stage4_findings):
        """Verify all findings contain non-empty evidence and assessor guidance."""
        for f in stage4_findings:
            assert f.evidence is not None and len(f.evidence) > 0
            assert f.assessor_guidance is not None and len(f.assessor_guidance.strip()) > 0
            assert f.rule_id in ("RULE-1", "RULE-2", "RULE-3", "RULE-4")
            assert f.priority_score > 0
            assert "priority_scoring_breakdown" in f.evidence

    def test_pipeline_is_deterministic(self, real_norm_data, real_metrics, real_peer_baselines):
        """Running the detection pipeline twice on the same dataset produces identical findings."""
        run1 = build_findings(run_all_rules(real_norm_data, real_metrics, real_peer_baselines))
        run2 = build_findings(run_all_rules(real_norm_data, real_metrics, real_peer_baselines))

        assert len(run1) == len(run2)
        for f1, f2 in zip(run1, run2):
            assert f1.finding_id == f2.finding_id
            assert f1.organization_id == f2.organization_id
            assert f1.finding_type == f2.finding_type
            assert f1.priority == f2.priority
            assert f1.priority_score == f2.priority_score
            assert f1.affected_record_ids == f2.affected_record_ids
