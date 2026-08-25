"""
SAT-SA Router — Organizations
=============================
GET /api/organizations
GET /api/organizations/{organization_id}
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.data_access import get_analytics_data, get_findings_data
from app.schemas import (
    ErrorResponse,
    OrganizationDetailResponse,
    OrganizationResponse,
)

router = APIRouter(prefix="/api/organizations", tags=["Organizations"])


@router.get(
    "",
    response_model=list[OrganizationResponse],
    summary="List all organizations",
    description="Returns basic information for all 12 monitored organizations across peer groups.",
)
def list_organizations() -> list[OrganizationResponse]:
    analytics = get_analytics_data()
    org_list = analytics.get("organizations", [])

    return [
        OrganizationResponse(
            organization_id=org["organization_id"],
            name=org["name"],
            size=org["size"],
            peer_group=org["peer_group"],
            active_asset_count=org["active_asset_count"],
        )
        for org in org_list
    ]


@router.get(
    "/{organization_id}",
    response_model=OrganizationDetailResponse,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
    summary="Get organization details by ID",
    description="Returns detailed operational metrics, peer baselines, peer deviations, and finding summary for a specific organization.",
)
def get_organization_detail(organization_id: str) -> OrganizationDetailResponse:
    analytics = get_analytics_data()
    org_list = analytics.get("organizations", [])

    target_org = next((o for o in org_list if o["organization_id"] == organization_id), None)
    if not target_org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization with ID '{organization_id}' not found.",
        )

    # Compute findings summary for this org
    all_findings = get_findings_data()
    org_findings = [f for f in all_findings if f.organization_id == organization_id]

    high_count = sum(1 for f in org_findings if f.priority.value == "HIGH")
    med_count  = sum(1 for f in org_findings if f.priority.value == "MEDIUM")
    low_count  = sum(1 for f in org_findings if f.priority.value == "LOW")

    findings_summary = {
        "total_findings": len(org_findings),
        "high_priority_count": high_count,
        "medium_priority_count": med_count,
        "low_priority_count": low_count,
        "finding_ids": [f.finding_id for f in org_findings],
    }

    return OrganizationDetailResponse(
        organization_id=target_org["organization_id"],
        name=target_org["name"],
        size=target_org["size"],
        peer_group=target_org["peer_group"],
        active_asset_count=target_org["active_asset_count"],
        metrics=target_org.get("metrics", {}),
        peer_baseline=target_org.get("peer_baseline", {}),
        peer_deviations=target_org.get("peer_deviations", {}),
        findings_summary=findings_summary,
    )
