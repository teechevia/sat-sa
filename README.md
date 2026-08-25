# SAT-SA — Supervisory Assessment Tool for Security Operations

> MVP · Python 3.12 · FastAPI · Vanilla HTML/CSS/JS

SAT-SA is an **independent supervisory assessment system** that receives periodic structured evidence from organizations' SOC systems, normalizes and validates it, and surfaces prioritized **Findings** to a human assessor — each finding fully traceable to the underlying records.

SAT-SA does **not** replace SIEMs, ticketing systems, or SOC platforms. It is an oversight layer that asks:

> *"Does the available operational evidence suggest that security processes are functioning as expected?"*

---

## Quick Start

```bash
# 1. Clone / navigate to the project
cd sat-sa

# 2. Install dependencies
pip install -r requirements.txt

# 3. Generate synthetic data (run once, or whenever you want fresh data)
python scripts/generate_data.py

# 4. Start the API  (Stage 8 — after full backend is implemented)
uvicorn app.main:app --reload --port 8000

# 5. Open the dashboard
# Navigate browser to: http://localhost:8000/frontend/index.html
```

---

## Project Structure

```
sat-sa/
│
├── data/                        CSV evidence files (generated)
│   ├── organizations.csv        12 organizations across 3 peer groups
│   ├── alerts.csv               ~9,830 alert records
│   ├── investigations.csv       Investigation evidence per alert
│   ├── escalations.csv          Escalation records per alert
│   ├── cases.csv                Case/incident records
│   └── generated/               Re-run outputs (safe to delete)
│
├── app/
│   ├── main.py                  FastAPI application entry point
│   ├── config.py                All thresholds and paths (tune here)
│   ├── models.py                All Pydantic data models
│   ├── data_loader.py           Stage 4: reads CSV -> raw dicts
│   ├── validator.py             Stage 4: validates raw dicts
│   ├── normalizer.py            Stage 4: derives investigation/escalation status
│   ├── analytics.py             Stage 5: per-org operational metrics
│   ├── rules.py                 Stage 6: 4 detection rules
│   ├── findings.py              Stage 6: finding builder + store
│   └── routers/                 Stage 8: FastAPI route handlers
│
├── frontend/
│   ├── index.html               Dashboard (Stage 9)
│   ├── style.css                Dashboard styles (Stage 9)
│   └── app.js                   Dashboard logic (Stage 9)
│
├── scripts/
│   └── generate_data.py         Seeded synthetic data generator
│
├── tests/
│   ├── test_validator.py        Validation tests
│   ├── test_analytics.py        Metric calculation tests
│   ├── test_rules.py            Rule logic tests (controlled inputs)
│   ├── test_findings.py         Finding structure and priority tests
│   └── test_ground_truth.py    ** Most important: verifies injected weaknesses are detected
│
├── requirements.txt
└── README.md
```

---

## Architecture

```
CSV files (data/)
    |
    v
data_loader.py    -- reads CSV -> list[dict]  (no logic)
    |
    v
validator.py      -- checks schema, timestamps, refs -> DataQualityReport
    |
    v
normalizer.py     -- converts dicts -> typed Pydantic models
                  -- DERIVES: investigated (from investigations.csv)
                  -- DERIVES: escalated    (from escalations.csv)
    |
    v
analytics.py      -- computes per-org OrgMetrics
    |
    v
rules.py          -- runs 4 detection rules -> list[Finding]
    |
    v
findings.py       -- assigns IDs, priority scores, stores findings
    |
    v
FastAPI (main.py) -- serves JSON endpoints
    |
    v
Dashboard (frontend/) -- HTML/CSS/JS, renders findings + evidence panel
```

**Key design principle**: `investigated` and `escalated` are **never read from a self-reported field**. They are always **derived** by the normalizer from the actual investigation and escalation evidence records. This is how SAT-SA analyzes evidence rather than trusting reported status.

---

## Synthetic Dataset

| Table | Rows |
|---|---|
| organizations | 12 |
| alerts | 9,830 |
| investigations | ~7,700 |
| escalations | ~1,020 |
| cases | ~2,480 |

### Organizations

| Group | Orgs | Active Assets |
|---|---|---|
| small | ORG-001 to ORG-004 | 38–45 per org |
| medium | ORG-005 to ORG-008 | 105–120 per org |
| large | ORG-009 to ORG-012 | 265–290 per org |

### Injected Ground-Truth Weaknesses

| Org | Injected Pattern | Detected By |
|---|---|---|
| **ORG-002** Bastion Energy | ~64% of critical alerts have no investigation record | Rule 1: Execution Gap |
| **ORG-003** Citadel Health | Critical/high closed in 2–8 min; ~76% uninvestigated | Rule 2: Fast Closure |
| **ORG-004** Dagger Transport | 7 (asset, type) patterns repeat 5–8× without remediation | Rule 3: Repeated Incidents |
| **ORG-012** Lynx Transport | 0.44 alerts/asset vs peer median 3.21 (86% deviation) | Rule 4: Peer Deviation |

All other organizations (ORG-001, ORG-005–ORG-011) behave normally.

### Regenerating Data

```bash
# Regenerate with same seed (identical output)
python scripts/generate_data.py

# The generator prints a ground-truth verification report showing PASS/FAIL
# for each injected weakness.
```

---

## Detection Rules

| Rule | ID | What It Detects |
|---|---|---|
| Potential Execution Gap | RULE-1 | Critical alerts without investigation evidence |
| Suspicious Fast Closure | RULE-2 | Fast-closed critical/high alerts with multiple corroborating signals |
| Repeated Incidents | RULE-3 | Same (asset, incident_type) recurring without remediation evidence |
| Peer Deviation | RULE-4 | Normalized activity (alerts/asset) substantially below/above peer median |

All thresholds are in `app/config.py`.

---

## API Endpoints

```
GET  /api/health                         System status
GET  /api/organizations                  All 12 organizations
GET  /api/organizations/{org_id}         Single org + metrics summary
GET  /api/findings                       All findings, sorted HIGH -> MEDIUM -> LOW
GET  /api/findings/{finding_id}          Single finding
GET  /api/findings/{finding_id}/evidence Full evidence + affected record details
GET  /api/metrics/{org_id}              OrgMetrics for one organization
```

---

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run only ground-truth tests (most important)
pytest tests/test_ground_truth.py -v
```

---

## Important Terminology

| Use | Avoid |
|---|---|
| Potential execution gap | SOC failed |
| Potential operational anomaly | Organization is insecure |
| Peer deviation | Breach confirmed |
| Potential remediation weakness | Attack confirmed |
| Requires human review | Compromised |

SAT-SA surfaces supervisory signals for human review. It does not automatically declare that an organization has failed or been attacked.

---

## Development Stages

| Stage | Status | Description |
|---|---|---|
| 1 | Done | Architecture review |
| 2 | **Done** | Scaffold + data generator |
| 3 | — | (merged into Stage 2) |
| 4 | Pending | Data loader, validator, normalizer |
| 5 | Pending | Analytics engine |
| 6 | Pending | Detection rules + findings |
| 7 | Pending | Tests + ground-truth verification |
| 8 | Pending | FastAPI endpoints |
| 9 | Pending | Dashboard |
| 10 | Pending | End-to-end run + README finalization |

---

## Future Phases (Not in MVP)

- **Phase 2**: Stronger peer benchmarking, negative-space detection
- **Phase 3**: Process mining, anomaly detection
- **Phase 4**: Offline ML, analyst feedback loop
- **Phase 5**: PostgreSQL, authentication/RBAC, production hardening

---

## Requirements

- Python 3.12+
- No external API required
- No internet connection required after `pip install`
- No database required
