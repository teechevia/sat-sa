"""
SAT-SA Data Validator
=====================
Validates raw DataFrames from data_loader.py.

Design principles:
    - Every issue is recorded; records are NEVER silently discarded.
    - Returns a DataQualityReport listing all issues.
    - Clearly separates "data quality issue" (e.g. missing timestamp)
      from "potential operational weakness" (e.g. uninvestigated alert).
      SAT-SA never conflates these two categories.

Validation coverage:
    Organizations:  IDs, size enum, peer_group consistency, asset count
    Alerts:         IDs, org FK, severity enum, timestamps, case FK, asset
    Investigations: IDs, alert FK, org FK, timestamps, notes_length
    Escalations:    IDs, alert FK, org FK, timestamp, level range
    Cases:          IDs, org FK, timestamps, remediation_evidence

Usage:
    from app.validator import validate_all
    report = validate_all(raw_data)
    if report.has_issues:
        for issue in report.issues:
            print(issue)
"""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from app.models import DataQualityIssue, DataQualityReport

# ---------------------------------------------------------------------------
# Controlled vocabularies
# ---------------------------------------------------------------------------
VALID_SEVERITIES  = {"critical", "high", "medium", "low"}
VALID_SIZES       = {"small", "medium", "large"}
VALID_OUTCOMES    = {"resolved", "escalated", "false_positive", "open"}
VALID_ESC_LEVELS  = {"1", "2", "3"}
VALID_REM_EVIDENT = {"True", "False"}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _is_valid_dt(val: str) -> bool:
    """Return True if val is a non-empty parseable datetime string."""
    if not val or val.strip() == "":
        return False
    try:
        pd.to_datetime(val)
        return True
    except Exception:
        return False


def _dt(val: str) -> pd.Timestamp:
    return pd.to_datetime(val)


def _check_unique_ids(df: pd.DataFrame, id_col: str, table: str,
                       issues: list[DataQualityIssue]) -> set[str]:
    """
    Report duplicate values in id_col. Return the set of valid (unique) IDs.
    """
    valid_ids: set[str] = set()
    seen: set[str] = set()
    for i, val in df[id_col].items():
        val = str(val).strip()
        if not val:
            issues.append(DataQualityIssue(
                table=table, record_id=f"row_{i}", field=id_col,
                issue=f"Missing {id_col}",
            ))
        elif val in seen:
            issues.append(DataQualityIssue(
                table=table, record_id=val, field=id_col,
                issue=f"Duplicate {id_col}: '{val}'",
            ))
        else:
            seen.add(val)
            valid_ids.add(val)
    return valid_ids


# ---------------------------------------------------------------------------
# Per-table validators
# ---------------------------------------------------------------------------

def validate_organizations(df: pd.DataFrame,
                            issues: list[DataQualityIssue]) -> set[str]:
    """
    Validate the organizations table.
    Returns the set of valid organization_ids for downstream FK checks.
    """
    valid_ids = _check_unique_ids(df, "organization_id", "organizations", issues)

    for _, row in df.iterrows():
        rid = str(row.get("organization_id", "")).strip()

        size = str(row.get("size", "")).strip()
        if size not in VALID_SIZES:
            issues.append(DataQualityIssue(
                table="organizations", record_id=rid, field="size",
                issue=f"Invalid size '{size}'. Expected one of: {sorted(VALID_SIZES)}",
            ))

        peer = str(row.get("peer_group", "")).strip()
        if peer != size:
            issues.append(DataQualityIssue(
                table="organizations", record_id=rid, field="peer_group",
                issue=f"peer_group '{peer}' does not match size '{size}'",
            ))

        aac = str(row.get("active_asset_count", "")).strip()
        try:
            v = int(aac)
            if v <= 0:
                raise ValueError("must be positive")
        except (ValueError, TypeError):
            issues.append(DataQualityIssue(
                table="organizations", record_id=rid, field="active_asset_count",
                issue=f"active_asset_count must be a positive integer, got '{aac}'",
            ))

    return valid_ids


def validate_alerts(df: pd.DataFrame,
                    valid_org_ids: set[str],
                    valid_case_ids: set[str],
                    issues: list[DataQualityIssue]) -> set[str]:
    """
    Validate the alerts table.
    Returns the set of valid alert_ids.
    """
    valid_ids = _check_unique_ids(df, "alert_id", "alerts", issues)

    for _, row in df.iterrows():
        aid = str(row.get("alert_id", "")).strip()
        if not aid:
            continue  # missing ID already recorded; skip row-level checks

        org = str(row.get("organization_id", "")).strip()
        if org not in valid_org_ids:
            issues.append(DataQualityIssue(
                table="alerts", record_id=aid, field="organization_id",
                issue=f"Unknown organization_id '{org}'",
            ))

        sev = str(row.get("severity", "")).strip()
        if sev not in VALID_SEVERITIES:
            issues.append(DataQualityIssue(
                table="alerts", record_id=aid, field="severity",
                issue=f"Invalid severity '{sev}'. "
                      f"Expected one of: {sorted(VALID_SEVERITIES)}",
            ))

        asset = str(row.get("asset_id", "")).strip()
        if not asset:
            issues.append(DataQualityIssue(
                table="alerts", record_id=aid, field="asset_id",
                issue="Missing asset_id",
            ))

        created = str(row.get("created_at", "")).strip()
        if not _is_valid_dt(created):
            issues.append(DataQualityIssue(
                table="alerts", record_id=aid, field="created_at",
                issue=f"Invalid or missing created_at '{created}'",
            ))
            continue  # Can't do time-ordering check without a valid created_at

        closed = str(row.get("closed_at", "")).strip()
        if closed:
            if not _is_valid_dt(closed):
                issues.append(DataQualityIssue(
                    table="alerts", record_id=aid, field="closed_at",
                    issue=f"Invalid closed_at '{closed}'",
                ))
            elif _dt(closed) < _dt(created):
                issues.append(DataQualityIssue(
                    table="alerts", record_id=aid, field="closed_at",
                    issue=f"closed_at ({closed}) is earlier than created_at ({created})",
                ))

        case = str(row.get("case_id", "")).strip()
        if case and case not in valid_case_ids:
            issues.append(DataQualityIssue(
                table="alerts", record_id=aid, field="case_id",
                issue=f"case_id '{case}' not found in cases table",
            ))

    return valid_ids


def validate_investigations(df: pd.DataFrame,
                             valid_alert_ids: set[str],
                             valid_org_ids: set[str],
                             issues: list[DataQualityIssue]) -> set[str]:
    """Validate the investigations table. Returns the set of valid investigation_ids."""
    valid_ids = _check_unique_ids(df, "investigation_id", "investigations", issues)

    for _, row in df.iterrows():
        iid = str(row.get("investigation_id", "")).strip()
        if not iid:
            continue

        alert = str(row.get("alert_id", "")).strip()
        if alert not in valid_alert_ids:
            issues.append(DataQualityIssue(
                table="investigations", record_id=iid, field="alert_id",
                issue=f"alert_id '{alert}' not found in alerts table",
            ))

        org = str(row.get("organization_id", "")).strip()
        if org not in valid_org_ids:
            issues.append(DataQualityIssue(
                table="investigations", record_id=iid, field="organization_id",
                issue=f"Unknown organization_id '{org}'",
            ))

        started = str(row.get("started_at", "")).strip()
        if not _is_valid_dt(started):
            issues.append(DataQualityIssue(
                table="investigations", record_id=iid, field="started_at",
                issue=f"Invalid or missing started_at '{started}'",
            ))
            continue

        completed = str(row.get("completed_at", "")).strip()
        if completed:
            if not _is_valid_dt(completed):
                issues.append(DataQualityIssue(
                    table="investigations", record_id=iid, field="completed_at",
                    issue=f"Invalid completed_at '{completed}'",
                ))
            elif _dt(completed) < _dt(started):
                issues.append(DataQualityIssue(
                    table="investigations", record_id=iid, field="completed_at",
                    issue=f"completed_at ({completed}) is earlier than "
                          f"started_at ({started})",
                ))

        nl = str(row.get("notes_length", "")).strip()
        try:
            v = int(nl)
            if v < 0:
                raise ValueError
        except (ValueError, TypeError):
            issues.append(DataQualityIssue(
                table="investigations", record_id=iid, field="notes_length",
                issue=f"notes_length must be a non-negative integer, got '{nl}'",
            ))

    return valid_ids


def validate_escalations(df: pd.DataFrame,
                          valid_alert_ids: set[str],
                          valid_org_ids: set[str],
                          issues: list[DataQualityIssue]) -> set[str]:
    """Validate the escalations table. Returns the set of valid escalation_ids."""
    valid_ids = _check_unique_ids(df, "escalation_id", "escalations", issues)

    for _, row in df.iterrows():
        eid = str(row.get("escalation_id", "")).strip()
        if not eid:
            continue

        alert = str(row.get("alert_id", "")).strip()
        if alert not in valid_alert_ids:
            issues.append(DataQualityIssue(
                table="escalations", record_id=eid, field="alert_id",
                issue=f"alert_id '{alert}' not found in alerts table",
            ))

        org = str(row.get("organization_id", "")).strip()
        if org not in valid_org_ids:
            issues.append(DataQualityIssue(
                table="escalations", record_id=eid, field="organization_id",
                issue=f"Unknown organization_id '{org}'",
            ))

        esc_at = str(row.get("escalated_at", "")).strip()
        if not _is_valid_dt(esc_at):
            issues.append(DataQualityIssue(
                table="escalations", record_id=eid, field="escalated_at",
                issue=f"Invalid or missing escalated_at '{esc_at}'",
            ))

        level = str(row.get("escalation_level", "")).strip()
        if level not in VALID_ESC_LEVELS:
            issues.append(DataQualityIssue(
                table="escalations", record_id=eid, field="escalation_level",
                issue=f"escalation_level must be 1, 2, or 3; got '{level}'",
            ))

    return valid_ids


def validate_cases(df: pd.DataFrame,
                   valid_org_ids: set[str],
                   issues: list[DataQualityIssue]) -> set[str]:
    """Validate the cases table. Returns the set of valid case_ids."""
    valid_ids = _check_unique_ids(df, "case_id", "cases", issues)

    for _, row in df.iterrows():
        cid = str(row.get("case_id", "")).strip()
        if not cid:
            continue

        org = str(row.get("organization_id", "")).strip()
        if org not in valid_org_ids:
            issues.append(DataQualityIssue(
                table="cases", record_id=cid, field="organization_id",
                issue=f"Unknown organization_id '{org}'",
            ))

        opened = str(row.get("opened_at", "")).strip()
        if not _is_valid_dt(opened):
            issues.append(DataQualityIssue(
                table="cases", record_id=cid, field="opened_at",
                issue=f"Invalid or missing opened_at '{opened}'",
            ))
            continue

        closed = str(row.get("closed_at", "")).strip()
        if closed:
            if not _is_valid_dt(closed):
                issues.append(DataQualityIssue(
                    table="cases", record_id=cid, field="closed_at",
                    issue=f"Invalid closed_at '{closed}'",
                ))
            elif _dt(closed) < _dt(opened):
                issues.append(DataQualityIssue(
                    table="cases", record_id=cid, field="closed_at",
                    issue=f"closed_at ({closed}) is earlier than opened_at ({opened})",
                ))

        rem = str(row.get("remediation_evidence", "")).strip()
        if rem not in VALID_REM_EVIDENT:
            issues.append(DataQualityIssue(
                table="cases", record_id=cid, field="remediation_evidence",
                issue=f"remediation_evidence must be 'True' or 'False'; got '{rem}'",
            ))

    return valid_ids


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def validate_all(raw: "RawData") -> DataQualityReport:  # type: ignore[name-defined]
    """
    Run all validation checks against the five tables.

    Records are NEVER silently dropped.
    Returns a DataQualityReport that lists every issue found.

    The report should be reviewed before analytics.
    Issues are informational — the pipeline continues regardless.
    """
    issues: list[DataQualityIssue] = []

    # Build reference ID sets (needed for FK checks)
    # Note: cases must be validated before alerts because alerts.case_id -> cases
    valid_case_ids  = set(raw.cases["case_id"].astype(str).str.strip()) - {"", "nan"}
    valid_org_ids   = validate_organizations(raw.organizations, issues)
    valid_case_ids  = validate_cases(raw.cases, valid_org_ids, issues)
    valid_alert_ids = validate_alerts(raw.alerts, valid_org_ids, valid_case_ids, issues)
    validate_investigations(raw.investigations, valid_alert_ids, valid_org_ids, issues)
    validate_escalations(raw.escalations, valid_alert_ids, valid_org_ids, issues)

    total_records = (
        len(raw.organizations)
        + len(raw.alerts)
        + len(raw.investigations)
        + len(raw.escalations)
        + len(raw.cases)
    )

    return DataQualityReport(
        total_records_checked=total_records,
        issues=issues,
        tables_checked=["organizations", "alerts", "investigations",
                        "escalations", "cases"],
        generated_at=datetime.now(timezone.utc),
    )
