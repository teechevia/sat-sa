"""
SAT-SA Router — Findings
========================
GET /api/findings
GET /api/findings/{finding_id}
GET /api/findings/{finding_id}/evidence
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from app.data_access import get_findings_data, get_normalized_data
from app.models import FindingType, Priority
from app.schemas import (
    ErrorResponse,
    EvidenceRecord,
    EvidenceResponse,
    FindingListResponse,
    FindingResponse,
)

router = APIRouter(prefix="/api/findings", tags=["Findings"])


@router.get(
    "",
    response_model=FindingListResponse,
    summary="List supervisory findings with optional filters",
    description=(
        "Returns all generated findings. Allows optional filtering by organization_id, "
        "finding_type, and priority. Findings are deterministically sorted by priority, org ID, and finding ID."
    ),
)
def list_findings(
    organization_id: Optional[str] = Query(None, description="Filter by organization ID (e.g., ORG-002)"),
    finding_type: Optional[FindingType] = Query(None, description="Filter by finding type (EXECUTION_GAP, SUSPICIOUS_FAST_CLOSURE, REPEATED_INCIDENTS, PEER_DEVIATION)"),
    priority: Optional[Priority] = Query(None, description="Filter by priority level (HIGH, MEDIUM, LOW)"),
) -> FindingListResponse:
    all_findings = get_findings_data()

    filtered = all_findings
    if organization_id:
        filtered = [f for f in filtered if f.organization_id == organization_id]
    if finding_type:
        filtered = [f for f in filtered if f.finding_type == finding_type]
    if priority:
        filtered = [f for f in filtered if f.priority == priority]

    # Deterministic sorting: priority (HIGH -> MEDIUM -> LOW), organization_id, finding_id
    priority_order = {Priority.HIGH: 0, Priority.MEDIUM: 1, Priority.LOW: 2}
    sorted_findings = sorted(
        filtered,
        key=lambda f: (priority_order[f.priority], f.organization_id, f.finding_id),
    )

    return FindingListResponse(
        total=len(sorted_findings),
        findings=[FindingResponse.model_validate(f.model_dump()) for f in sorted_findings],
    )


@router.get(
    "/{finding_id}",
    response_model=FindingResponse,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
    summary="Get single finding details by ID",
    description="Returns complete details for a single finding including title, description, evidence thresholds, and assessor guidance.",
)
def get_finding_detail(finding_id: str) -> FindingResponse:
    all_findings = get_findings_data()
    finding = next((f for f in all_findings if f.finding_id == finding_id), None)

    if not finding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Finding with ID '{finding_id}' not found.",
        )

    return FindingResponse.model_validate(finding.model_dump())


@router.get(
    "/{finding_id}/evidence",
    response_model=EvidenceResponse,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
    summary="Get evidence record traceability for a finding",
    description="Returns exact alert or case records referenced in the finding's affected_record_ids for human verification.",
)
def get_finding_evidence(finding_id: str) -> EvidenceResponse:
    all_findings = get_findings_data()
    finding = next((f for f in all_findings if f.finding_id == finding_id), None)

    if not finding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Finding with ID '{finding_id}' not found.",
        )

    norm = get_normalized_data()
    affected_ids = set(finding.affected_record_ids)
    evidence_records: list[EvidenceRecord] = []

    # Look up affected IDs in alerts DataFrame
    alert_matches = norm.alerts[norm.alerts["alert_id"].isin(affected_ids)]
    for _, row in alert_matches.iterrows():
        rec_id = str(row["alert_id"])
        created = row["created_at"].isoformat() if pd_notna(row["created_at"]) else None
        closed  = row["closed_at"].isoformat()  if pd_notna(row["closed_at"])  else None

        details = {
            "alert_id": rec_id,
            "severity": str(row["severity"]),
            "incident_type": str(row["incident_type"]),
            "asset_id": str(row["asset_id"]),
            "case_id": str(row["case_id"]) if pd_notna(row["case_id"]) else None,
            "created_at": created,
            "closed_at": closed,
            "investigated": bool(row["investigated"]),
            "escalated": bool(row["escalated"]),
            "closure_duration_min": float(row["closure_duration_min"]) if pd_notna(row["closure_duration_min"]) else None,
        }

        evidence_records.append(
            EvidenceRecord(
                record_type="alert",
                record_id=rec_id,
                organization_id=str(row["organization_id"]),
                details=details,
            )
        )

    # Look up affected IDs in cases DataFrame
    case_matches = norm.cases[norm.cases["case_id"].isin(affected_ids)]
    for _, row in case_matches.iterrows():
        rec_id = str(row["case_id"])
        opened = row["opened_at"].isoformat() if pd_notna(row["opened_at"]) else None
        closed = row["closed_at"].isoformat() if pd_notna(row["closed_at"]) else None

        details = {
            "case_id": rec_id,
            "asset_id": str(row["asset_id"]),
            "incident_type": str(row["incident_type"]),
            "opened_at": opened,
            "closed_at": closed,
            "recurrence_count": int(row["recurrence_count"]) if pd_notna(row["recurrence_count"]) else 0,
            "remediation_evidence": bool(row["remediation_evidence"]) if pd_notna(row["remediation_evidence"]) else False,
        }

        evidence_records.append(
            EvidenceRecord(
                record_type="case",
                record_id=rec_id,
                organization_id=str(row["organization_id"]),
                details=details,
            )
        )

    return EvidenceResponse(
        finding_id=finding.finding_id,
        organization_id=finding.organization_id,
        finding_type=finding.finding_type,
        total_affected_records=len(finding.affected_record_ids),
        evidence_records=evidence_records,
    )


def pd_notna(val: Any) -> bool:
    """Helper to check if pandas value is not NA."""
    import pandas as pd
    return bool(pd.notna(val))
