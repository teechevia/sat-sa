"""
Tests for app/validator.py

Covers every check listed in the Stage 3 specification:
    - Valid data produces no issues
    - Duplicate IDs are detected
    - Invalid references (FK violations) are detected
    - Invalid timestamps are detected
    - Timestamp ordering violations are detected
    - Invalid enum values are detected
    - Missing required fields are detected
"""

from __future__ import annotations

import pandas as pd
import pytest

from app.validator import (
    validate_all,
    validate_organizations,
    validate_alerts,
    validate_investigations,
    validate_escalations,
    validate_cases,
)
from app.models import DataQualityIssue


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _issues(raw_data) -> list[DataQualityIssue]:
    report = validate_all(raw_data)
    return report.issues


def _issues_for(issue_list: list[DataQualityIssue], field: str | None = None,
                table: str | None = None) -> list[DataQualityIssue]:
    out = issue_list
    if field:
        out = [i for i in out if i.field == field]
    if table:
        out = [i for i in out if i.table == table]
    return out


# ---------------------------------------------------------------------------
# validate_organizations
# ---------------------------------------------------------------------------

class TestValidateOrganizations:

    def test_valid_organizations_produce_no_issues(self, raw_orgs):
        issues: list[DataQualityIssue] = []
        validate_organizations(raw_orgs, issues)
        assert issues == [], f"Expected no issues, got: {issues}"

    def test_duplicate_org_id_detected(self, raw_orgs):
        df = raw_orgs.copy()
        df.loc[1, "organization_id"] = "ORG-A"   # duplicate
        issues: list[DataQualityIssue] = []
        validate_organizations(df, issues)
        dup_issues = _issues_for(issues, field="organization_id")
        assert any("Duplicate" in i.issue for i in dup_issues)

    def test_invalid_size_detected(self, raw_orgs):
        df = raw_orgs.copy()
        df.loc[0, "size"] = "GIANT"
        issues: list[DataQualityIssue] = []
        validate_organizations(df, issues)
        assert any(i.field == "size" for i in issues)

    def test_peer_group_mismatch_detected(self, raw_orgs):
        df = raw_orgs.copy()
        df.loc[0, "peer_group"] = "large"   # size=small, peer_group=large
        issues: list[DataQualityIssue] = []
        validate_organizations(df, issues)
        assert any(i.field == "peer_group" for i in issues)

    def test_invalid_asset_count_detected(self, raw_orgs):
        df = raw_orgs.copy()
        df.loc[0, "active_asset_count"] = "abc"
        issues: list[DataQualityIssue] = []
        validate_organizations(df, issues)
        assert any(i.field == "active_asset_count" for i in issues)

    def test_zero_asset_count_detected(self, raw_orgs):
        df = raw_orgs.copy()
        df.loc[0, "active_asset_count"] = "0"
        issues: list[DataQualityIssue] = []
        validate_organizations(df, issues)
        assert any(i.field == "active_asset_count" for i in issues)

    def test_returns_valid_id_set(self, raw_orgs):
        issues: list[DataQualityIssue] = []
        valid_ids = validate_organizations(raw_orgs, issues)
        assert "ORG-A" in valid_ids
        assert "ORG-B" in valid_ids
        assert issues == []


# ---------------------------------------------------------------------------
# validate_alerts
# ---------------------------------------------------------------------------

class TestValidateAlerts:

    def _run(self, df: pd.DataFrame, raw_orgs, raw_cases) -> list[DataQualityIssue]:
        issues: list[DataQualityIssue] = []
        valid_orgs = set(raw_orgs["organization_id"])
        valid_cases = set(raw_cases["case_id"])
        validate_alerts(df, valid_orgs, valid_cases, issues)
        return issues

    def test_valid_alerts_produce_no_issues(self, raw_alerts, raw_orgs, raw_cases):
        issues = self._run(raw_alerts, raw_orgs, raw_cases)
        assert issues == [], f"Expected no issues, got: {issues}"

    def test_duplicate_alert_id_detected(self, raw_alerts, raw_orgs, raw_cases):
        df = raw_alerts.copy()
        df.loc[1, "alert_id"] = "A-001"   # duplicate
        issues = self._run(df, raw_orgs, raw_cases)
        assert any(i.field == "alert_id" and "Duplicate" in i.issue for i in issues)

    def test_unknown_org_id_detected(self, raw_alerts, raw_orgs, raw_cases):
        df = raw_alerts.copy()
        df.loc[0, "organization_id"] = "ORG-UNKNOWN"
        issues = self._run(df, raw_orgs, raw_cases)
        assert any(i.field == "organization_id" for i in issues)

    def test_invalid_severity_detected(self, raw_alerts, raw_orgs, raw_cases):
        df = raw_alerts.copy()
        df.loc[0, "severity"] = "EXTREME"
        issues = self._run(df, raw_orgs, raw_cases)
        assert any(i.field == "severity" for i in issues)

    def test_closed_before_created_detected(self, raw_alerts, raw_orgs, raw_cases):
        df = raw_alerts.copy()
        # closed_at is before created_at
        df.loc[0, "closed_at"] = "2024-12-31T00:00:00"
        issues = self._run(df, raw_orgs, raw_cases)
        assert any(i.field == "closed_at" and "earlier" in i.issue for i in issues)

    def test_invalid_created_at_detected(self, raw_alerts, raw_orgs, raw_cases):
        df = raw_alerts.copy()
        df.loc[0, "created_at"] = "NOT-A-DATE"
        issues = self._run(df, raw_orgs, raw_cases)
        assert any(i.field == "created_at" for i in issues)

    def test_missing_asset_id_detected(self, raw_alerts, raw_orgs, raw_cases):
        df = raw_alerts.copy()
        df.loc[0, "asset_id"] = ""
        issues = self._run(df, raw_orgs, raw_cases)
        assert any(i.field == "asset_id" for i in issues)

    def test_unknown_case_id_detected(self, raw_alerts, raw_orgs, raw_cases):
        df = raw_alerts.copy()
        df.loc[0, "case_id"] = "CASE-DOES-NOT-EXIST"
        issues = self._run(df, raw_orgs, raw_cases)
        assert any(i.field == "case_id" for i in issues)


# ---------------------------------------------------------------------------
# validate_investigations
# ---------------------------------------------------------------------------

class TestValidateInvestigations:

    def _run(self, df, raw_alerts, raw_orgs) -> list[DataQualityIssue]:
        issues: list[DataQualityIssue] = []
        valid_alerts = set(raw_alerts["alert_id"])
        valid_orgs   = set(raw_orgs["organization_id"])
        validate_investigations(df, valid_alerts, valid_orgs, issues)
        return issues

    def test_valid_investigations_produce_no_issues(
            self, raw_investigations, raw_alerts, raw_orgs):
        issues = self._run(raw_investigations, raw_alerts, raw_orgs)
        assert issues == []

    def test_duplicate_investigation_id_detected(
            self, raw_investigations, raw_alerts, raw_orgs):
        df = raw_investigations.copy()
        df.loc[1, "investigation_id"] = "INV-001"
        issues = self._run(df, raw_alerts, raw_orgs)
        assert any(i.field == "investigation_id" and "Duplicate" in i.issue
                   for i in issues)

    def test_unknown_alert_id_detected(
            self, raw_investigations, raw_alerts, raw_orgs):
        df = raw_investigations.copy()
        df.loc[0, "alert_id"] = "A-GHOST"
        issues = self._run(df, raw_alerts, raw_orgs)
        assert any(i.field == "alert_id" for i in issues)

    def test_completed_before_started_detected(
            self, raw_investigations, raw_alerts, raw_orgs):
        df = raw_investigations.copy()
        df.loc[0, "completed_at"] = "2024-12-01T00:00:00"
        issues = self._run(df, raw_alerts, raw_orgs)
        assert any(i.field == "completed_at" and "earlier" in i.issue for i in issues)

    def test_invalid_started_at_detected(
            self, raw_investigations, raw_alerts, raw_orgs):
        df = raw_investigations.copy()
        df.loc[0, "started_at"] = "NOTADATE"
        issues = self._run(df, raw_alerts, raw_orgs)
        assert any(i.field == "started_at" for i in issues)

    def test_negative_notes_length_detected(
            self, raw_investigations, raw_alerts, raw_orgs):
        df = raw_investigations.copy()
        df.loc[0, "notes_length"] = "-50"
        issues = self._run(df, raw_alerts, raw_orgs)
        assert any(i.field == "notes_length" for i in issues)


# ---------------------------------------------------------------------------
# validate_escalations
# ---------------------------------------------------------------------------

class TestValidateEscalations:

    def _run(self, df, raw_alerts, raw_orgs) -> list[DataQualityIssue]:
        issues: list[DataQualityIssue] = []
        validate_escalations(df, set(raw_alerts["alert_id"]),
                              set(raw_orgs["organization_id"]), issues)
        return issues

    def test_valid_escalation_produces_no_issues(
            self, raw_escalations, raw_alerts, raw_orgs):
        issues = self._run(raw_escalations, raw_alerts, raw_orgs)
        assert issues == []

    def test_duplicate_escalation_id_detected(
            self, raw_escalations, raw_alerts, raw_orgs):
        df = pd.concat([raw_escalations, raw_escalations], ignore_index=True)
        issues = self._run(df, raw_alerts, raw_orgs)
        assert any(i.field == "escalation_id" and "Duplicate" in i.issue
                   for i in issues)

    def test_unknown_alert_id_detected(
            self, raw_escalations, raw_alerts, raw_orgs):
        df = raw_escalations.copy()
        df.loc[0, "alert_id"] = "A-GHOST"
        issues = self._run(df, raw_alerts, raw_orgs)
        assert any(i.field == "alert_id" for i in issues)

    def test_invalid_escalation_level_detected(
            self, raw_escalations, raw_alerts, raw_orgs):
        df = raw_escalations.copy()
        df.loc[0, "escalation_level"] = "9"
        issues = self._run(df, raw_alerts, raw_orgs)
        assert any(i.field == "escalation_level" for i in issues)

    def test_invalid_escalated_at_detected(
            self, raw_escalations, raw_alerts, raw_orgs):
        df = raw_escalations.copy()
        df.loc[0, "escalated_at"] = ""
        issues = self._run(df, raw_alerts, raw_orgs)
        assert any(i.field == "escalated_at" for i in issues)


# ---------------------------------------------------------------------------
# validate_cases
# ---------------------------------------------------------------------------

class TestValidateCases:

    def _run(self, df, raw_orgs) -> list[DataQualityIssue]:
        issues: list[DataQualityIssue] = []
        validate_cases(df, set(raw_orgs["organization_id"]), issues)
        return issues

    def test_valid_cases_produce_no_issues(self, raw_cases, raw_orgs):
        issues = self._run(raw_cases, raw_orgs)
        assert issues == []

    def test_duplicate_case_id_detected(self, raw_cases, raw_orgs):
        df = raw_cases.copy()
        df.loc[1, "case_id"] = "CASE-001"
        issues = self._run(df, raw_orgs)
        assert any(i.field == "case_id" and "Duplicate" in i.issue for i in issues)

    def test_unknown_org_id_detected(self, raw_cases, raw_orgs):
        df = raw_cases.copy()
        df.loc[0, "organization_id"] = "ORG-GHOST"
        issues = self._run(df, raw_orgs)
        assert any(i.field == "organization_id" for i in issues)

    def test_closed_before_opened_detected(self, raw_cases, raw_orgs):
        df = raw_cases.copy()
        df.loc[0, "closed_at"] = "2024-01-01T00:00:00"
        issues = self._run(df, raw_orgs)
        assert any(i.field == "closed_at" and "earlier" in i.issue for i in issues)

    def test_invalid_remediation_evidence_detected(self, raw_cases, raw_orgs):
        df = raw_cases.copy()
        df.loc[0, "remediation_evidence"] = "yes"
        issues = self._run(df, raw_orgs)
        assert any(i.field == "remediation_evidence" for i in issues)


# ---------------------------------------------------------------------------
# validate_all (end-to-end)
# ---------------------------------------------------------------------------

class TestValidateAll:

    def test_clean_dataset_produces_no_issues(self, raw_data):
        report = validate_all(raw_data)
        assert report.issue_count == 0, (
            f"Expected 0 issues on clean fixture, got:\n"
            + "\n".join(f"  {i}" for i in report.issues)
        )

    def test_report_includes_all_tables(self, raw_data):
        report = validate_all(raw_data)
        assert set(report.tables_checked) == {
            "organizations", "alerts", "investigations", "escalations", "cases"
        }

    def test_total_records_counted(self, raw_data):
        report = validate_all(raw_data)
        expected = (
            len(raw_data.organizations) + len(raw_data.alerts)
            + len(raw_data.investigations) + len(raw_data.escalations)
            + len(raw_data.cases)
        )
        assert report.total_records_checked == expected

    def test_multiple_issues_all_reported(self, raw_data):
        """All issues across tables are accumulated — nothing silently dropped."""
        # Introduce one error in three different tables
        raw_data.alerts.loc[0, "severity"] = "INVALID"
        raw_data.organizations.loc[0, "size"] = "INVALID"
        raw_data.cases.loc[0, "remediation_evidence"] = "INVALID"
        report = validate_all(raw_data)
        assert report.issue_count >= 3
