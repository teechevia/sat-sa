"""
Stage 5 API Tests
=================
Tests for all FastAPI REST API endpoints in app/main.py using TestClient.

Tests:
    - GET /api/health
    - GET /api/organizations
    - GET /api/organizations/{valid_id}
    - GET /api/organizations/{invalid_id} -> 404
    - GET /api/findings
    - GET /api/findings?priority=HIGH
    - GET /api/findings?organization_id=ORG-002
    - GET /api/findings?finding_type=EXECUTION_GAP
    - GET /api/findings?priority=INVALID -> 422
    - GET /api/findings/{valid_id}
    - GET /api/findings/{invalid_id} -> 404
    - GET /api/metrics
    - GET /api/organizations/{id}/metrics
    - GET /api/findings/{id}/evidence
    - Ground-truth evidence traceability checks
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestHealthEndpoint:

    def test_health_check_returns_200(self):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["service"] == "SAT-SA"
        assert data["version"] == "0.1.0"


class TestOrganizationEndpoints:

    def test_list_organizations_returns_all_12_orgs(self):
        resp = client.get("/api/organizations")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 12
        org_ids = {o["organization_id"] for o in data}
        assert "ORG-001" in org_ids
        assert "ORG-012" in org_ids

    def test_get_valid_organization_detail(self):
        resp = client.get("/api/organizations/ORG-002")
        assert resp.status_code == 200
        data = resp.json()
        assert data["organization_id"] == "ORG-002"
        assert data["name"] == "Bastion Energy"
        assert data["size"] == "small"
        assert "metrics" in data
        assert "peer_baseline" in data
        assert "peer_deviations" in data
        assert "findings_summary" in data
        assert data["findings_summary"]["total_findings"] >= 1

    def test_get_invalid_organization_returns_404(self):
        resp = client.get("/api/organizations/ORG-INVALID-999")
        assert resp.status_code == 404
        data = resp.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()


class TestFindingEndpoints:

    def test_list_findings_returns_all_findings(self):
        resp = client.get("/api/findings")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 5
        assert len(data["findings"]) == 5

    def test_filter_findings_by_priority(self):
        resp = client.get("/api/findings?priority=HIGH")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 5
        assert all(f["priority"] == "HIGH" for f in data["findings"])

    def test_filter_findings_by_organization_id(self):
        resp = client.get("/api/findings?organization_id=ORG-002")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["findings"][0]["organization_id"] == "ORG-002"
        assert data["findings"][0]["finding_type"] == "EXECUTION_GAP"

    def test_filter_findings_by_finding_type(self):
        resp = client.get("/api/findings?finding_type=EXECUTION_GAP")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert all(f["finding_type"] == "EXECUTION_GAP" for f in data["findings"])

    def test_invalid_filter_priority_returns_422(self):
        resp = client.get("/api/findings?priority=SUPER_HIGH")
        assert resp.status_code == 422

    def test_invalid_filter_finding_type_returns_422(self):
        resp = client.get("/api/findings?finding_type=INVALID_TYPE")
        assert resp.status_code == 422

    def test_get_valid_finding_detail(self):
        resp = client.get("/api/findings/F-001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["finding_id"] == "F-001"
        assert data["organization_id"] == "ORG-002"
        assert data["rule_id"] == "RULE-1"
        assert "evidence" in data
        assert "assessor_guidance" in data

    def test_get_invalid_finding_returns_404(self):
        resp = client.get("/api/findings/F-9999")
        assert resp.status_code == 404


class TestMetricsEndpoints:

    def test_get_system_metrics(self):
        resp = client.get("/api/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_organizations"] == 12
        assert data["total_alerts"] > 9000
        assert data["total_findings"] == 5
        assert "summary_by_priority" in data
        assert "summary_by_rule" in data

    def test_get_org_metrics_detail(self):
        resp = client.get("/api/organizations/ORG-012/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert data["organization_id"] == "ORG-012"
        assert "metrics" in data
        assert "peer_baseline" in data

    def test_get_invalid_org_metrics_returns_404(self):
        resp = client.get("/api/organizations/ORG-9999/metrics")
        assert resp.status_code == 404


class TestEvidenceTraceabilityEndpoint:

    def test_get_finding_evidence_traceability(self):
        resp = client.get("/api/findings/F-001/evidence")
        assert resp.status_code == 200
        data = resp.json()
        assert data["finding_id"] == "F-001"
        assert data["organization_id"] == "ORG-002"
        assert data["total_affected_records"] > 0
        assert len(data["evidence_records"]) > 0

        # Spot check evidence records structure
        rec = data["evidence_records"][0]
        assert rec["record_type"] in ("alert", "case")
        assert "record_id" in rec
        assert "details" in rec

    def test_get_finding_evidence_invalid_id_returns_404(self):
        resp = client.get("/api/findings/F-9999/evidence")
        assert resp.status_code == 404


class TestOpenAPIDocumentation:

    def test_openapi_schema_available(self):
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        data = resp.json()
        assert data["info"]["title"] == "SAT-SA Supervisory Assessment Tool"
        assert "/api/health" in data["paths"]
        assert "/api/organizations" in data["paths"]
        assert "/api/findings" in data["paths"]
        assert "/api/metrics" in data["paths"]
