"""
SAT-SA Detection Rules Engine
=============================
Stage 4 implementation.

Deterministic rules that evaluate normalized operational evidence and produce
structured Finding objects.

Rules implemented:
    RULE-1: Potential Execution Gap
            Critical alerts lacking investigation evidence.
            Trigger: missing_investigation_rate >= THRESHOLD_EXECUTION_GAP (0.40)

    RULE-2: Suspicious Fast Closure
            Critical/High alerts closed rapidly (< 10 min) without investigation.
            Trigger: fast_uninvestigated_rate >= THRESHOLD_FAST_CLOSURE_RATE (0.20)

    RULE-3: Repeated Incidents Without Remediation Evidence
            (asset_id, incident_type) groups with >= 3 cases and NO remediation evidence.
            Trigger: len(flagged_groups) > 0

    RULE-4: Peer Activity Deviation (Negative Space Signal)
            Normalized alert volume per asset deviating >= 40% from peer median.
            Trigger: deviation >= THRESHOLD_PEER_DEVIATION (0.40) for normalized activity.

Language & supervisory principles:
    - Language is cautious, neutral, and supervisory ("Potential execution gap").
    - Never uses "SOC failed", "breach", "attack", "insecure".
    - Every finding includes affected_record_ids for 100% record traceability.
    - Operates purely on normalized data & analytics — no hard-coded org IDs or ML.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd

from app.config import (
    THRESHOLD_EXECUTION_GAP,
    THRESHOLD_FAST_CLOSURE_RATE,
    THRESHOLD_FAST_MINUTES,
    THRESHOLD_PEER_DEVIATION,
    THRESHOLD_REPEAT_COUNT,
)
from app.models import Finding, FindingType, Priority


# ---------------------------------------------------------------------------
# Helper — datetime formatting for findings
# ---------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# RULE 1 — Potential Execution Gap
# ---------------------------------------------------------------------------

def run_execution_gap_rule(
    org_id: str,
    org_alerts: pd.DataFrame,
    threshold: float = THRESHOLD_EXECUTION_GAP,
) -> Finding | None:
    """
    Evaluates critical alerts for missing investigation evidence.

    Missing rate = (critical alerts where investigated == False) / total critical alerts.
    Triggers if missing_rate >= threshold (default 0.40).
    """
    crit_alerts = org_alerts[org_alerts["severity"] == "critical"]
    total_crit = len(crit_alerts)

    if total_crit == 0:
        return None

    uninv_crit = crit_alerts[crit_alerts["investigated"] == False]
    missing_count = len(uninv_crit)
    investigated_count = total_crit - missing_count
    missing_rate = missing_count / total_crit
    investigation_rate = investigated_count / total_crit

    if missing_rate < threshold:
        return None

    affected_ids = uninv_crit["alert_id"].tolist()

    evidence = {
        "what_was_detected": "High proportion of critical alerts with no corresponding investigation record",
        "rule_id": "RULE-1",
        "threshold_missing_rate": threshold,
        "total_critical_alerts": total_crit,
        "investigated_count": investigated_count,
        "missing_investigation_count": missing_count,
        "observed_missing_rate": round(missing_rate, 4),
        "observed_investigation_rate": round(investigation_rate, 4),
        "sample_affected_alert_ids": affected_ids[:10],
    }

    assessor_guidance = (
        "Verify whether uninvestigated critical alerts represent logging/reporting gaps, "
        "analyst capacity constraints, or automated suppression rules. Review the affected "
        "critical alert records to confirm whether high-risk activity was left unexamined."
    )

    return Finding(
        finding_id="",  # Assigned by findings.py
        organization_id=org_id,
        finding_type=FindingType.EXECUTION_GAP,
        priority=Priority.HIGH,  # Refined by findings.py priority scorer
        title="Potential Execution Gap in Critical Alert Investigation",
        description=(
            f"Potential execution gap: {missing_rate:.1%} of critical alerts ({missing_count} of {total_crit}) "
            f"lack corresponding investigation evidence, exceeding the supervisory threshold of {threshold:.0%}."
        ),
        evidence=evidence,
        affected_record_ids=affected_ids,
        assessor_guidance=assessor_guidance,
        rule_id="RULE-1",
        priority_score=0,
        generated_at=_now(),
    )


# ---------------------------------------------------------------------------
# RULE 2 — Suspicious Fast Closure
# ---------------------------------------------------------------------------

def run_fast_closure_rule(
    org_id: str,
    org_alerts: pd.DataFrame,
    fast_minutes: int = THRESHOLD_FAST_MINUTES,
    threshold_rate: float = THRESHOLD_FAST_CLOSURE_RATE,
) -> Finding | None:
    """
    Evaluates critical & high severity alerts for rapid closure (< 10 min)
    without investigation evidence.
    """
    crithigh = org_alerts[org_alerts["severity"].isin(["critical", "high"])].copy()
    total_crithigh = len(crithigh)

    if total_crithigh == 0:
        return None

    # Filter for fast + uninvestigated + closed
    fast_uninv = crithigh[
        (crithigh["closure_duration_min"] < fast_minutes)
        & (crithigh["investigated"] == False)
        & crithigh["closure_duration_min"].notna()
    ]

    flagged_count = len(fast_uninv)
    flagged_rate = flagged_count / total_crithigh

    if flagged_rate < threshold_rate:
        return None

    affected_ids = fast_uninv["alert_id"].tolist()
    median_closure_min = float(fast_uninv["closure_duration_min"].median()) if flagged_count > 0 else 0.0

    crit_flagged = len(fast_uninv[fast_uninv["severity"] == "critical"])
    high_flagged = len(fast_uninv[fast_uninv["severity"] == "high"])

    evidence = {
        "what_was_detected": (
            f"High proportion of critical/high alerts closed in under {fast_minutes} "
            "minutes without investigation evidence"
        ),
        "rule_id": "RULE-2",
        "threshold_fast_minutes": fast_minutes,
        "threshold_flagged_rate": threshold_rate,
        "total_critical_high_alerts": total_crithigh,
        "flagged_count": flagged_count,
        "observed_flagged_rate": round(flagged_rate, 4),
        "median_closure_duration_minutes": round(median_closure_min, 2),
        "severity_breakdown": {
            "critical_flagged": crit_flagged,
            "high_flagged": high_flagged,
        },
        "sample_affected_alert_ids": affected_ids[:10],
    }

    assessor_guidance = (
        "Review auto-closure scripts, ticketing rules, or analyst triage workflows. "
        "Confirm whether alerts are being closed automatically or prematurely without proper "
        "triage, root cause analysis, or evidence documentation."
    )

    return Finding(
        finding_id="",
        organization_id=org_id,
        finding_type=FindingType.SUSPICIOUS_FAST_CLOSURE,
        priority=Priority.HIGH,
        title="Suspicious Fast Closure of Critical and High Severity Alerts",
        description=(
            f"Potential operational anomaly: {flagged_rate:.1%} of critical/high severity alerts "
            f"({flagged_count} of {total_crithigh}) were closed in under {fast_minutes} minutes without "
            f"investigation evidence (median closure duration: {median_closure_min:.1f} min)."
        ),
        evidence=evidence,
        affected_record_ids=affected_ids,
        assessor_guidance=assessor_guidance,
        rule_id="RULE-2",
        priority_score=0,
        generated_at=_now(),
    )


# ---------------------------------------------------------------------------
# RULE 3 — Repeated Incidents
# ---------------------------------------------------------------------------

def run_repeated_incidents_rule(
    org_id: str,
    org_cases: pd.DataFrame,
    min_repeat_count: int = THRESHOLD_REPEAT_COUNT,
) -> Finding | None:
    """
    Evaluates cases grouped by (asset_id, incident_type).
    Flags groups where count >= min_repeat_count AND remediation_evidence is False for all cases in group.
    """
    if org_cases.empty:
        return None

    # Group by asset_id and incident_type
    flagged_groups: list[dict[str, Any]] = []
    affected_case_ids: list[str] = []

    grouped = org_cases.groupby(["asset_id", "incident_type"])
    for (asset_id, incident_type), group in grouped:
        case_count = len(group)
        # Check if all cases in group have remediation_evidence == False
        rem_false_all = (group["remediation_evidence"] == False).all()

        if case_count >= min_repeat_count and rem_false_all:
            c_ids = group["case_id"].tolist()
            flagged_groups.append({
                "asset_id": asset_id,
                "incident_type": incident_type,
                "case_count": case_count,
                "remediation_evidence_status": "All False",
                "case_ids": c_ids,
            })
            affected_case_ids.extend(c_ids)

    if not flagged_groups:
        return None

    # Sort groups by count descending to identify worst group
    flagged_groups.sort(key=lambda g: g["case_count"], reverse=True)
    worst_group = flagged_groups[0]

    evidence = {
        "what_was_detected": "Multiple recurring incident cases on identical assets without recorded remediation evidence",
        "rule_id": "RULE-3",
        "threshold_min_repeat_count": min_repeat_count,
        "flagged_group_count": len(flagged_groups),
        "total_affected_cases": len(affected_case_ids),
        "worst_repeated_group": {
            "asset_id": worst_group["asset_id"],
            "incident_type": worst_group["incident_type"],
            "case_count": worst_group["case_count"],
            "remediation_evidence": False,
        },
        "flagged_groups_summary": [
            {
                "asset_id": g["asset_id"],
                "incident_type": g["incident_type"],
                "case_count": g["case_count"],
            }
            for g in flagged_groups
        ],
    }

    assessor_guidance = (
        "Examine root cause analysis and remediation tracking for recurring asset/incident combinations. "
        "Verify whether remediation actions were completed but unrecorded, or if security controls failed "
        "to mitigate recurring vulnerabilities."
    )

    return Finding(
        finding_id="",
        organization_id=org_id,
        finding_type=FindingType.REPEATED_INCIDENTS,
        priority=Priority.HIGH,
        title="Repeated Incidents Without Recorded Remediation Evidence",
        description=(
            f"Potential remediation weakness: {len(flagged_groups)} recurring incident patterns "
            f"({len(affected_case_ids)} cases total) were observed for identical assets and incident types "
            f"without recorded remediation evidence (worst: {worst_group['asset_id']} + {worst_group['incident_type']} "
            f"recurring {worst_group['case_count']} times)."
        ),
        evidence=evidence,
        affected_record_ids=affected_case_ids,
        assessor_guidance=assessor_guidance,
        rule_id="RULE-3",
        priority_score=0,
        generated_at=_now(),
    )


# ---------------------------------------------------------------------------
# RULE 4 — Peer Activity Deviation (Negative Space Signal)
# ---------------------------------------------------------------------------

def run_peer_deviation_rule(
    org_id: str,
    org_metric: dict[str, Any],
    peer_baseline: dict[str, Any],
    org_alerts: pd.DataFrame,
    threshold_deviation: float = THRESHOLD_PEER_DEVIATION,
) -> Finding | None:
    """
    Evaluates normalized alert activity (alerts_per_active_asset, critical_alerts_per_active_asset)
    against leave-one-out peer group median.

    Does NOT flag investigation_rate or escalation_rate alone to prevent duplicating Rule 1.
    """
    baseline = peer_baseline.get("baseline", {})
    deviations = peer_baseline.get("deviations", {})

    # Check primary activity metric: alerts_per_active_asset
    metric_key = "alerts_per_active_asset"
    dev_info = deviations.get(metric_key, {})

    dev_pct = dev_info.get("deviation_pct")
    org_val = dev_info.get("org_value")
    peer_med = dev_info.get("peer_median")
    direction = dev_info.get("direction")

    if dev_pct is None or peer_med is None or peer_med == 0:
        return None

    rel_deviation = abs(dev_pct) / 100.0

    if rel_deviation < threshold_deviation:
        return None

    # Contextual metrics for assessor review
    crit_inv_rate = org_metric.get("critical_investigation_rate", 0.0)
    esc_rate = org_metric.get("escalation_rate", 0.0)

    evidence = {
        "what_was_detected": "Normalized alert activity deviates significantly from comparable peer organizations",
        "rule_id": "RULE-4",
        "threshold_peer_deviation": threshold_deviation,
        "metric_name": metric_key,
        "observed_org_value": org_val,
        "peer_group": org_metric.get("peer_group", ""),
        "peer_median": peer_med,
        "peer_count": baseline.get("n_peers", 0),
        "deviation_pct": dev_pct,
        "direction": direction,
        "contextual_metrics": {
            "note": "Contextual metrics included for assessor review.",
            "critical_investigation_rate": crit_inv_rate,
            "escalation_rate": esc_rate,
        },
    }

    assessor_guidance = (
        "Verify whether telemetry log ingestion coverage is complete, whether the organization's "
        "operational environment legitimately produces lower activity, whether asset inventory counts "
        "are accurate, or whether the submitted reporting period evidence is complete."
    )

    direction_str = "substantially below" if direction == "below" else "substantially above"

    # Affected IDs for peer deviation can include sample alerts from the org
    affected_ids = org_alerts["alert_id"].tolist()[:20]

    return Finding(
        finding_id="",
        organization_id=org_id,
        finding_type=FindingType.PEER_DEVIATION,
        priority=Priority.HIGH,
        title="Significant Peer Deviation in Normalized Alert Activity",
        description=(
            f"Potential activity gap: normalized alert activity ({org_val:.2f} alerts/asset) is {direction_str} "
            f"comparable peer organizations (peer median: {peer_med:.2f} alerts/asset, deviation: {dev_pct:.1f}%)."
        ),
        evidence=evidence,
        affected_record_ids=affected_ids,
        assessor_guidance=assessor_guidance,
        rule_id="RULE-4",
        priority_score=0,
        generated_at=_now(),
    )


# ---------------------------------------------------------------------------
# Master rule runner
# ---------------------------------------------------------------------------

def run_all_rules(
    norm: Any,
    all_metrics: list[dict[str, Any]],
    peer_baselines: dict[str, dict[str, Any]],
) -> list[Finding]:
    """
    Runs all 4 detection rules across all organizations in normalized data.
    Returns list of unassigned raw Finding objects (IDs & priority assigned by findings.py).
    """
    raw_findings: list[Finding] = []
    metrics_by_id = {m["organization_id"]: m for m in all_metrics}

    for _, org_row in norm.organizations.iterrows():
        org_id = str(org_row["organization_id"]).strip()
        org_alerts = norm.alerts[norm.alerts["organization_id"] == org_id]
        org_cases = norm.cases[norm.cases["organization_id"] == org_id]
        org_m = metrics_by_id.get(org_id, {})
        pb = peer_baselines.get(org_id, {})

        # Rule 1: Execution Gap
        f1 = run_execution_gap_rule(org_id, org_alerts)
        if f1:
            raw_findings.append(f1)

        # Rule 2: Suspicious Fast Closure
        f2 = run_fast_closure_rule(org_id, org_alerts)
        if f2:
            raw_findings.append(f2)

        # Rule 3: Repeated Incidents
        f3 = run_repeated_incidents_rule(org_id, org_cases)
        if f3:
            raw_findings.append(f3)

        # Rule 4: Peer Deviation
        f4 = run_peer_deviation_rule(org_id, org_m, pb, org_alerts)
        if f4:
            raw_findings.append(f4)

    return raw_findings
