"""
SAT-SA Router — System Metrics & Analytics
==========================================
GET /api/metrics
GET /api/organizations/{organization_id}/metrics
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.data_access import get_analytics_data, get_findings_data
from app.schemas import ErrorResponse, MetricsResponse

router = APIRouter(tags=["Metrics"])


@router.get(
    "/api/metrics",
    response_model=MetricsResponse,
    summary="Get system-wide analytics overview",
    description="Returns aggregate dataset metrics, data quality validation summary, finding counts by priority/rule, and per-organization metrics.",
)
def get_system_metrics() -> MetricsResponse:
    analytics = get_analytics_data()
    all_findings = get_findings_data()

    meta = analytics.get("meta", {})
    dq_summary = analytics.get("data_quality", {})
    org_list = analytics.get("organizations", [])

    priority_counts = Counter(f.priority.value for f in all_findings)
    rule_counts = Counter(f.rule_id for f in all_findings)

    return MetricsResponse(
        meta=meta,
        data_quality=dq_summary,
        total_organizations=len(org_list),
        total_alerts=meta.get("total_alerts", 0),
        total_investigations=meta.get("total_investigations", 0),
        total_escalations=meta.get("total_escalations", 0),
        total_cases=meta.get("total_cases", 0),
        total_findings=len(all_findings),
        summary_by_priority={
            "HIGH": priority_counts.get("HIGH", 0),
            "MEDIUM": priority_counts.get("MEDIUM", 0),
            "LOW": priority_counts.get("LOW", 0),
        },
        summary_by_rule=dict(rule_counts),
        organizations=org_list,
    )


@router.get(
    "/api/organizations/{organization_id}/metrics",
    response_model=dict[str, Any],
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
    summary="Get detailed metrics and peer baseline for one organization",
    description="Returns pre-computed operational metrics, peer baselines, and peer deviations for a single organization.",
)
def get_org_metrics_detail(organization_id: str) -> dict[str, Any]:
    analytics = get_analytics_data()
    org_list = analytics.get("organizations", [])

    target_org = next((o for o in org_list if o["organization_id"] == organization_id), None)
    if not target_org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization with ID '{organization_id}' not found.",
        )

    return {
        "organization_id": target_org["organization_id"],
        "name": target_org["name"],
        "size": target_org["size"],
        "peer_group": target_org["peer_group"],
        "active_asset_count": target_org["active_asset_count"],
        "metrics": target_org.get("metrics", {}),
        "peer_baseline": target_org.get("peer_baseline", {}),
        "peer_deviations": target_org.get("peer_deviations", {}),
    }
