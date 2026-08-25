"""
Integration Test Script for SAT-SA FastAPI Endpoints
======================================================
Verifies that all required Stage 5 REST API endpoints return valid, real
Stage 3 & 4 data.
"""

from __future__ import annotations

import json
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def verify_all():
    print("=" * 80)
    print("SAT-SA FASTAPI LIVE INTEGRATION TEST")
    print("=" * 80)

    # 1. Health
    r = client.get("/api/health")
    assert r.status_code == 200
    print("\n1. GET /api/health -> 200 OK")
    print("   Response:", json.dumps(r.json(), indent=2))

    # 2. List Organizations
    r = client.get("/api/organizations")
    assert r.status_code == 200
    orgs = r.json()
    assert len(orgs) == 12
    print(f"\n2. GET /api/organizations -> 200 OK ({len(orgs)} organizations returned)")

    # 3. Organization Detail (ORG-002)
    r = client.get("/api/organizations/ORG-002")
    assert r.status_code == 200
    org_detail = r.json()
    assert org_detail["organization_id"] == "ORG-002"
    print("\n3. GET /api/organizations/ORG-002 -> 200 OK")
    print("   Name:", org_detail["name"])
    print("   Critical Inv Rate:", org_detail["metrics"]["critical_investigation_rate"])
    print("   Findings Summary:", org_detail["findings_summary"])

    # 4. List Findings
    r = client.get("/api/findings")
    assert r.status_code == 200
    findings_resp = r.json()
    assert findings_resp["total"] == 5
    print(f"\n4. GET /api/findings -> 200 OK ({findings_resp['total']} findings returned)")

    # 5. Single Finding (F-001)
    r = client.get("/api/findings/F-001")
    assert r.status_code == 200
    f_detail = r.json()
    assert f_detail["finding_id"] == "F-001"
    print("\n5. GET /api/findings/F-001 -> 200 OK")
    print("   Title:", f_detail["title"])
    print("   Priority:", f_detail["priority"])
    print("   Rule:", f_detail["rule_id"])

    # 6. Finding Evidence Traceability (F-001)
    r = client.get("/api/findings/F-001/evidence")
    assert r.status_code == 200
    ev_detail = r.json()
    assert ev_detail["finding_id"] == "F-001"
    print(f"\n6. GET /api/findings/F-001/evidence -> 200 OK ({len(ev_detail['evidence_records'])} evidence records returned)")

    # 7. System Metrics
    r = client.get("/api/metrics")
    assert r.status_code == 200
    m_detail = r.json()
    assert m_detail["total_organizations"] == 12
    print("\n7. GET /api/metrics -> 200 OK")
    print("   Total Alerts:", m_detail["total_alerts"])
    print("   Total Findings:", m_detail["total_findings"])
    print("   By Priority:", m_detail["summary_by_priority"])

    # 8. OpenAPI JSON
    r = client.get("/openapi.json")
    assert r.status_code == 200
    print("\n8. GET /openapi.json -> 200 OK (Swagger OpenAPI Schema active)")

    print("\n" + "=" * 80)
    print("ALL API INTEGRATION ENDPOINT CHECKS PASSED ✓")
    print("=" * 80)

if __name__ == "__main__":
    verify_all()
