"""
SAT-SA API Response Schemas
===========================
Pydantic response models for the FastAPI REST API layer.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.models import FindingType, Priority


# ---------------------------------------------------------------------------
# Organization Schemas
# ---------------------------------------------------------------------------

class OrganizationResponse(BaseModel):
    organization_id:    str = Field(..., description="Unique organization identifier", example="ORG-002")
    name:               str = Field(..., description="Organization display name", example="Bastion Energy")
    size:               str = Field(..., description="Organization size category (small, medium, large)", example="small")
    peer_group:         str = Field(..., description="Peer group classification", example="small")
    active_asset_count: int = Field(..., description="Number of active infrastructure assets monitored", example=40)


class OrganizationDetailResponse(BaseModel):
    organization_id:    str = Field(..., description="Unique organization identifier")
    name:               str = Field(..., description="Organization display name")
    size:               str = Field(..., description="Organization size category")
    peer_group:         str = Field(..., description="Peer group classification")
    active_asset_count: int = Field(..., description="Number of active infrastructure assets monitored")
    metrics:            dict[str, Any] = Field(..., description="Calculated operational metrics")
    peer_baseline:      dict[str, Any] = Field(..., description="Leave-one-out peer baseline medians")
    peer_deviations:    dict[str, Any] = Field(..., description="Deviations from peer group baselines")
    findings_summary:   dict[str, Any] = Field(..., description="Summary of supervisory findings for this organization")


# ---------------------------------------------------------------------------
# Finding Schemas
# ---------------------------------------------------------------------------

class FindingResponse(BaseModel):
    finding_id:          str = Field(..., description="Unique sequential finding identifier", example="F-001")
    organization_id:     str = Field(..., description="Affected organization identifier", example="ORG-002")
    finding_type:        FindingType = Field(..., description="Supervisory finding category")
    priority:            Priority = Field(..., description="Assigned priority level (HIGH, MEDIUM, LOW)")
    title:               str = Field(..., description="Human-readable finding title")
    description:         str = Field(..., description="Cautious supervisory description")
    evidence:            dict[str, Any] = Field(..., description="Structured supporting evidence and thresholds")
    affected_record_ids: list[str] = Field(..., description="List of alert or case IDs supporting this finding")
    assessor_guidance:   str = Field(..., description="Recommended verification actions for the human assessor")
    rule_id:             str = Field(..., description="Rule ID that triggered this finding", example="RULE-1")
    priority_score:      int = Field(..., description="Additive priority score", example=5)
    generated_at:        datetime = Field(..., description="Timestamp when finding was generated")


class FindingListResponse(BaseModel):
    total:    int = Field(..., description="Total count of matching findings")
    findings: list[FindingResponse] = Field(..., description="List of matching findings")


# ---------------------------------------------------------------------------
# Evidence Traceability Schemas
# ---------------------------------------------------------------------------

class EvidenceRecord(BaseModel):
    record_type:     str = Field(..., description="Record category: 'alert' or 'case'", example="alert")
    record_id:       str = Field(..., description="Unique record identifier", example="A-00754")
    organization_id: str = Field(..., description="Organization identifier", example="ORG-002")
    details:         dict[str, Any] = Field(..., description="Raw record attributes and evidence flags")


class EvidenceResponse(BaseModel):
    finding_id:             str = Field(..., description="Finding identifier", example="F-001")
    organization_id:        str = Field(..., description="Organization identifier", example="ORG-002")
    finding_type:           FindingType = Field(..., description="Supervisory finding category")
    total_affected_records: int = Field(..., description="Count of affected record IDs")
    evidence_records:       list[EvidenceRecord] = Field(..., description="Detailed records supporting this finding")


# ---------------------------------------------------------------------------
# System Metrics Schemas
# ---------------------------------------------------------------------------

class MetricsResponse(BaseModel):
    meta:                 dict[str, Any] = Field(..., description="System metadata")
    data_quality:         dict[str, Any] = Field(..., description="Data quality validation summary")
    total_organizations:  int = Field(..., description="Total organizations analyzed")
    total_alerts:         int = Field(..., description="Total alert evidence records")
    total_investigations: int = Field(..., description="Total investigation records")
    total_escalations:    int = Field(..., description="Total escalation records")
    total_cases:          int = Field(..., description="Total case records")
    total_findings:       int = Field(..., description="Total supervisory findings generated")
    summary_by_priority:  dict[str, int] = Field(..., description="Finding count by priority (HIGH, MEDIUM, LOW)")
    summary_by_rule:      dict[str, int] = Field(..., description="Finding count by rule ID")
    organizations:        list[dict[str, Any]] = Field(..., description="Per-organization metrics and baselines")


# ---------------------------------------------------------------------------
# Error Schema
# ---------------------------------------------------------------------------

class ErrorResponse(BaseModel):
    detail: str = Field(..., description="Human-readable error description")
