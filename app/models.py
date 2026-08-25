"""
SAT-SA Pydantic Models
======================
All data models for the normalized internal representation.

Every layer of the pipeline works with these models — never with raw dicts.

Organization of this file:
    1. Enums            — controlled vocabularies
    2. Raw data models  — one per CSV table
    3. Normalized Alert — central model with DERIVED fields
    4. Analytics model  — per-org metrics
    5. Finding model    — output of the rule engine
    6. Data quality     — validation report

IMPORTANT — derived fields:
    Alert.investigated and Alert.escalated are NOT read from any CSV column.
    They are computed by normalizer.py from the investigations and escalations
    tables respectively.  This is how SAT-SA analyzes evidence rather than
    trusting self-reported status.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


# =============================================================================
# 1. Enums
# =============================================================================

class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH     = "high"
    MEDIUM   = "medium"
    LOW      = "low"


class OrgSize(str, Enum):
    SMALL  = "small"
    MEDIUM = "medium"
    LARGE  = "large"


class InvestigationOutcome(str, Enum):
    RESOLVED       = "resolved"
    ESCALATED      = "escalated"
    FALSE_POSITIVE = "false_positive"
    OPEN           = "open"


class FindingType(str, Enum):
    EXECUTION_GAP          = "EXECUTION_GAP"
    SUSPICIOUS_FAST_CLOSURE = "SUSPICIOUS_FAST_CLOSURE"
    REPEATED_INCIDENTS     = "REPEATED_INCIDENTS"
    PEER_DEVIATION         = "PEER_DEVIATION"


class Priority(str, Enum):
    HIGH   = "HIGH"
    MEDIUM = "MEDIUM"
    LOW    = "LOW"


# =============================================================================
# 2. Raw data models (one per CSV table, no derivation)
# =============================================================================

class Organization(BaseModel):
    """
    Represents one row from organizations.csv.
    active_asset_count is used to normalize alert volume for peer comparison.
    """
    organization_id:   str
    name:              str
    size:              OrgSize
    sector:            str
    peer_group:        str
    active_asset_count: int


class RawAlert(BaseModel):
    """
    One row from alerts.csv — exactly what is in the file, no derivation.
    Note: there is no 'investigated' or 'escalated' column in alerts.csv.
    Those are derived by normalizer.py from the evidence tables.
    """
    alert_id:        str
    organization_id: str
    severity:        Severity
    incident_type:   str
    asset_id:        str
    case_id:         Optional[str]
    created_at:      datetime
    closed_at:       Optional[datetime]


class Investigation(BaseModel):
    """One row from investigations.csv."""
    investigation_id: str
    alert_id:         str
    organization_id:  str
    analyst_id:       str
    started_at:       datetime
    completed_at:     Optional[datetime]
    notes_length:     int
    outcome:          InvestigationOutcome


class Escalation(BaseModel):
    """One row from escalations.csv."""
    escalation_id:    str
    alert_id:         str
    organization_id:  str
    escalated_at:     datetime
    escalation_level: int


class Case(BaseModel):
    """One row from cases.csv."""
    case_id:               str
    organization_id:       str
    asset_id:              str
    incident_type:         str
    opened_at:             datetime
    closed_at:             Optional[datetime]
    recurrence_count:      int
    remediation_evidence:  bool


# =============================================================================
# 3. Normalized Alert — central enriched model
# =============================================================================

class Alert(BaseModel):
    """
    Normalized alert — the central object used by analytics.py and rules.py.

    Raw fields come from alerts.csv.
    DERIVED fields are populated by normalizer.enrich_alerts() after joining
    with investigations.csv and escalations.csv.
    COMPUTED fields are calculated from raw timestamps.

    Never trust the 'investigated' or 'escalated' values from any external
    source — they must always be freshly derived by normalizer.py.
    """
    # ── Raw fields (from alerts.csv) ──────────────────────────────────────
    alert_id:        str
    organization_id: str
    severity:        Severity
    incident_type:   str
    asset_id:        str
    case_id:         Optional[str]
    created_at:      datetime
    closed_at:       Optional[datetime]

    # ── DERIVED from investigations.csv (set by normalizer.enrich_alerts) ─
    investigated:                   bool                        = False
    investigation_id:               Optional[str]               = None
    investigation_started_at:       Optional[datetime]          = None
    investigation_completed_at:     Optional[datetime]          = None
    investigation_notes_length:     Optional[int]               = None
    investigation_outcome:          Optional[InvestigationOutcome] = None

    # ── DERIVED from escalations.csv ─────────────────────────────────────
    escalated:         bool = False
    escalation_count:  int  = 0

    # ── COMPUTED from timestamps (set by normalizer.enrich_alerts) ────────
    closure_minutes:            Optional[float] = None
    investigation_lag_minutes:  Optional[float] = None  # started_at - created_at


# =============================================================================
# 4. Analytics model
# =============================================================================

class OrgMetrics(BaseModel):
    """
    Per-organization operational metrics computed by analytics.py.
    All rates are derived from evidence — never from self-reported fields.
    """
    organization_id: str
    peer_group:      str
    active_asset_count: int

    # Counts
    total_alerts:    int
    critical_alerts: int
    high_alerts:     int
    total_cases:     int

    # Normalized activity — PRIMARY metric for peer comparison (Rule 4)
    # Dividing by active_asset_count makes organizations of different sizes
    # fairly comparable. A large org with more assets will naturally see
    # more alerts; alerts_per_asset removes that confound.
    alerts_per_asset:          float
    critical_alerts_per_asset: float

    # Investigation metrics (derived — not self-reported)
    overall_investigation_rate:  float   # all investigated / all alerts
    critical_investigation_rate: float   # investigated criticals / total criticals
    escalation_rate:             float   # escalated crit+high / total crit+high

    # Closure metrics
    median_closure_minutes:          Optional[float]
    median_critical_closure_minutes: Optional[float]
    pct_fast_closed_uninvestigated:  float  # fast+uninvestigated / total crit+high

    # Repeated incident metrics (from cases.csv)
    repeat_incident_groups:            int   # (asset, type) pairs with >= threshold cases
    repeat_groups_without_remediation: int   # of above, no remediation evidence

    # Peer context — filled by rules.py Rule 4 (leave-one-out median)
    peer_alerts_per_asset:          Optional[float] = None
    peer_critical_alerts_per_asset: Optional[float] = None
    peer_critical_investigation_rate: Optional[float] = None
    peer_escalation_rate:           Optional[float] = None


# =============================================================================
# 5. Finding model
# =============================================================================

class Finding(BaseModel):
    """
    Structured supervisory finding produced by the rule engine.

    Every finding must answer:
        1. What was detected?          → title + description
        2. Why was it detected?        → evidence (metrics, thresholds)
        3. What supports the finding?  → evidence (baselines, deviation)
        4. Which records triggered it? → affected_record_ids
        5. What should the assessor do?→ assessor_guidance

    Language convention:
        Use cautious supervisory language.
        Do NOT use: "SOC failed", "breached", "attacked", "compromised".
        DO use: "potential execution gap", "requires human review",
                "peer deviation", "potential remediation weakness".
    """
    finding_id:          str
    organization_id:     str
    finding_type:        FindingType
    priority:            Priority
    title:               str
    description:         str
    evidence:            dict          # metric values, thresholds, baselines
    affected_record_ids: list[str]     # alert_ids or case_ids — always traceable
    assessor_guidance:   str
    rule_id:             str           # e.g. "RULE-1"
    priority_score:      int           # raw additive score (transparent)
    generated_at:        datetime


# =============================================================================
# 6. Data quality report
# =============================================================================

class DataQualityIssue(BaseModel):
    """One validation problem found in a CSV table."""
    table:     str   # e.g. "alerts"
    record_id: str   # the ID field value (or row index if ID is missing)
    field:     str   # the problematic field name
    issue:     str   # human-readable description


class DataQualityReport(BaseModel):
    """
    Summary of all validation issues found before analytics run.

    Design principle:
        Data quality issues (e.g. missing created_at) are fundamentally
        different from operational weaknesses (e.g. uninvestigated criticals).
        This report captures the former only.
        The rule engine captures the latter.
    """
    total_records_checked: int
    issues:                list[DataQualityIssue]
    tables_checked:        list[str]
    generated_at:          datetime

    @property
    def issue_count(self) -> int:
        return len(self.issues)

    @property
    def has_issues(self) -> bool:
        return bool(self.issues)
