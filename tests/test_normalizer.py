"""
Tests for app/normalizer.py

The most important property tested here:
    Alert.investigated is DERIVED from investigations.csv — never self-reported.
    Alert.escalated is DERIVED from escalations.csv — never self-reported.

Also tests:
    - closure_duration_min is correct
    - investigation_dur_min is correct
    - investigation_lag_min is correct
    - has_case is correct
    - NaT is returned for open/incomplete records
    - escalation_count per alert is correct
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.normalizer import (
    normalize_all,
    enrich_alerts,
    normalize_investigations,
    normalize_escalations,
    normalize_cases,
)


# ---------------------------------------------------------------------------
# Derivation of 'investigated'
# ---------------------------------------------------------------------------

class TestInvestigatedDerivation:

    def test_alert_with_investigation_record_is_investigated(self, norm_data):
        """A-001 has INV-001 → investigated=True."""
        a001 = norm_data.alerts[norm_data.alerts["alert_id"] == "A-001"].iloc[0]
        assert a001["investigated"] is True or a001["investigated"] == True

    def test_alert_without_investigation_record_is_not_investigated(self, norm_data):
        """A-003 has NO investigation record → investigated=False."""
        a003 = norm_data.alerts[norm_data.alerts["alert_id"] == "A-003"].iloc[0]
        assert a003["investigated"] is False or a003["investigated"] == False

    def test_investigation_status_not_self_reported(self, raw_data):
        """
        Even if we manually mark an alert as 'investigated' in a hypothetical
        self-reported column, the derived 'investigated' field only reflects
        the presence of an actual investigation record.

        This test verifies the derivation is purely evidence-based by checking
        that the investigations DataFrame controls the outcome.
        """
        # Remove the investigation for A-001
        raw_no_inv = raw_data.__class__(
            organizations=raw_data.organizations,
            alerts=raw_data.alerts,
            investigations=raw_data.investigations[
                raw_data.investigations["alert_id"] != "A-001"
            ],
            escalations=raw_data.escalations,
            cases=raw_data.cases,
        )
        norm = normalize_all(raw_no_inv)
        a001 = norm.alerts[norm.alerts["alert_id"] == "A-001"].iloc[0]
        # A-001 no longer has an investigation record → investigated=False
        assert a001["investigated"] == False

    def test_all_four_alerts_have_investigated_field(self, norm_data):
        assert "investigated" in norm_data.alerts.columns
        assert len(norm_data.alerts) == 4


# ---------------------------------------------------------------------------
# Derivation of 'escalated'
# ---------------------------------------------------------------------------

class TestEscalatedDerivation:

    def test_alert_with_escalation_record_is_escalated(self, norm_data):
        """A-001 has ESC-001 → escalated=True."""
        a001 = norm_data.alerts[norm_data.alerts["alert_id"] == "A-001"].iloc[0]
        assert a001["escalated"] == True

    def test_alert_without_escalation_record_is_not_escalated(self, norm_data):
        """A-002 has NO escalation record → escalated=False."""
        a002 = norm_data.alerts[norm_data.alerts["alert_id"] == "A-002"].iloc[0]
        assert a002["escalated"] == False

    def test_escalation_status_is_evidence_derived(self, raw_data):
        """
        Removing all escalation records → all alerts have escalated=False.
        The derived value must reflect the absence of evidence.
        """
        raw_no_esc = raw_data.__class__(
            organizations=raw_data.organizations,
            alerts=raw_data.alerts,
            investigations=raw_data.investigations,
            escalations=pd.DataFrame(columns=raw_data.escalations.columns),
            cases=raw_data.cases,
        )
        norm = normalize_all(raw_no_esc)
        assert norm.alerts["escalated"].sum() == 0

    def test_escalation_count_correct(self, norm_data):
        """A-001 has 1 escalation record → escalation_count=1."""
        a001 = norm_data.alerts[norm_data.alerts["alert_id"] == "A-001"].iloc[0]
        assert int(a001["escalation_count"]) == 1

    def test_escalation_count_zero_for_non_escalated(self, norm_data):
        a002 = norm_data.alerts[norm_data.alerts["alert_id"] == "A-002"].iloc[0]
        assert int(a002["escalation_count"]) == 0


# ---------------------------------------------------------------------------
# Closure duration
# ---------------------------------------------------------------------------

class TestClosureDuration:

    def test_closure_duration_calculated_correctly(self, norm_data):
        """
        A-001: created=2025-01-01T10:00:00, closed=2025-01-01T14:00:00
               duration = 4 hours = 240 minutes
        """
        a001 = norm_data.alerts[norm_data.alerts["alert_id"] == "A-001"].iloc[0]
        assert abs(float(a001["closure_duration_min"]) - 240.0) < 0.01

    def test_closure_duration_null_for_open_alert(self, norm_data):
        """A-004 has no closed_at → closure_duration_min is NaN."""
        a004 = norm_data.alerts[norm_data.alerts["alert_id"] == "A-004"].iloc[0]
        assert pd.isna(a004["closure_duration_min"])

    def test_another_closure_duration(self, norm_data):
        """
        A-002: created=2025-01-02T10:00:00, closed=2025-01-02T18:00:00
               duration = 8 hours = 480 minutes
        """
        a002 = norm_data.alerts[norm_data.alerts["alert_id"] == "A-002"].iloc[0]
        assert abs(float(a002["closure_duration_min"]) - 480.0) < 0.01


# ---------------------------------------------------------------------------
# Investigation duration
# ---------------------------------------------------------------------------

class TestInvestigationDuration:

    def test_investigation_duration_calculated_correctly(self, norm_data):
        """
        INV-001: started=2025-01-01T10:30:00, completed=2025-01-01T12:30:00
                 duration = 120 minutes
        """
        a001 = norm_data.alerts[norm_data.alerts["alert_id"] == "A-001"].iloc[0]
        assert abs(float(a001["investigation_dur_min"]) - 120.0) < 0.01

    def test_investigation_duration_null_for_uninvestigated(self, norm_data):
        """A-003 has no investigation → investigation_dur_min is NaN."""
        a003 = norm_data.alerts[norm_data.alerts["alert_id"] == "A-003"].iloc[0]
        assert pd.isna(a003["investigation_dur_min"])

    def test_investigation_lag_calculated(self, norm_data):
        """
        A-001: alert_created=2025-01-01T10:00:00, inv_started=2025-01-01T10:30:00
               lag = 30 minutes
        """
        a001 = norm_data.alerts[norm_data.alerts["alert_id"] == "A-001"].iloc[0]
        assert abs(float(a001["investigation_lag_min"]) - 30.0) < 0.01


# ---------------------------------------------------------------------------
# has_case
# ---------------------------------------------------------------------------

class TestHasCase:

    def test_has_case_true_when_case_id_present(self, norm_data):
        """A-001 has case_id=CASE-001 → has_case=True."""
        a001 = norm_data.alerts[norm_data.alerts["alert_id"] == "A-001"].iloc[0]
        assert a001["has_case"] == True

    def test_has_case_false_when_no_case_id(self, norm_data):
        """A-002 has empty case_id → has_case=False."""
        a002 = norm_data.alerts[norm_data.alerts["alert_id"] == "A-002"].iloc[0]
        assert a002["has_case"] == False

    def test_has_case_true_when_org_b_has_case(self, norm_data):
        """A-004 has case_id=CASE-003 → has_case=True."""
        a004 = norm_data.alerts[norm_data.alerts["alert_id"] == "A-004"].iloc[0]
        assert a004["has_case"] == True


# ---------------------------------------------------------------------------
# Case normalization
# ---------------------------------------------------------------------------

class TestCaseNormalization:

    def test_remediation_evidence_parsed_to_bool(self, norm_data):
        """'True' string → Python True, 'False' string → Python False."""
        cases = norm_data.cases
        true_val  = cases[cases["case_id"] == "CASE-001"]["remediation_evidence"].iloc[0]
        false_val = cases[cases["case_id"] == "CASE-002"]["remediation_evidence"].iloc[0]
        assert true_val  is True  or true_val  == True
        assert false_val is False or false_val == False

    def test_open_case_has_nat_closed_at(self, norm_data):
        """CASE-002 has no closed_at → NaT."""
        case002 = norm_data.cases[norm_data.cases["case_id"] == "CASE-002"].iloc[0]
        assert pd.isna(case002["closed_at"])
