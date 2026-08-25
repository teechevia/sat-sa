"""
SAT-SA Finding Builder and Store
=================================
Stage 4 implementation.

Responsibility:
    1. Assign sequential finding_id values (F-001, F-002, ...).
    2. Compute priority using transparent additive scoring.
    3. Store all findings in-memory for API / report lookup.

Transparent Additive Priority Scoring Model (Strict adherence to documented signals):
    Allowed signals:
    +2 if critical severity is involved
    +2 if affected rate > 50%
    +1 if affected rate is 30–50%
    +1 if no investigation evidence exists
    +1 if multiple signals combine
    +2 if peer deviation > 60%
    +1 if peer deviation is 40–60%

Priority thresholds:
    Total Score >= 4  →  HIGH
    Total Score 2–3   →  MEDIUM
    Total Score 1     →  LOW

The raw score and transparent breakdown are stored in Finding.priority_score and
Finding.evidence["priority_scoring_breakdown"] so assessors can see exactly why a finding
received its priority level.
"""

from __future__ import annotations

from typing import Any

from app.models import Finding, FindingType, Priority

# In-memory store for built findings
_FINDINGS_STORE: dict[str, Finding] = {}


# ---------------------------------------------------------------------------
# Priority scoring engine
# ---------------------------------------------------------------------------

def score_finding(f: Finding) -> tuple[int, Priority, list[str]]:
    """
    Computes an additive priority score using strictly documented signals.
    Returns (score, priority, breakdown_reasons).
    """
    score = 0
    reasons: list[str] = []
    ev = f.evidence

    # Signal 1: +2 if critical severity is involved
    if f.finding_type == FindingType.EXECUTION_GAP:
        score += 2
        reasons.append("+2: Critical severity is involved")
    elif f.finding_type == FindingType.SUSPICIOUS_FAST_CLOSURE:
        sev_breakdown = ev.get("severity_breakdown", {})
        if sev_breakdown.get("critical_flagged", 0) > 0:
            score += 2
            reasons.append("+2: Critical severity is involved")

    # Signal 2: +2 if affected rate > 50%, or +1 if affected rate is 30-50%
    if f.finding_type == FindingType.EXECUTION_GAP:
        missing_rate = ev.get("observed_missing_rate", 0.0)
        if missing_rate > 0.50:
            score += 2
            reasons.append("+2: Affected rate > 50%")
        elif missing_rate >= 0.30:
            score += 1
            reasons.append("+1: Affected rate is 30–50%")

    elif f.finding_type == FindingType.SUSPICIOUS_FAST_CLOSURE:
        flagged_rate = ev.get("observed_flagged_rate", 0.0)
        if flagged_rate > 0.50:
            score += 2
            reasons.append("+2: Affected rate > 50%")
        elif flagged_rate >= 0.30:
            score += 1
            reasons.append("+1: Affected rate is 30–50%")

    elif f.finding_type == FindingType.REPEATED_INCIDENTS:
        group_count = ev.get("flagged_group_count", 0)
        if group_count >= 5:
            score += 2
            reasons.append("+2: Affected rate > 50%")
        elif group_count >= 2:
            score += 1
            reasons.append("+1: Affected rate is 30–50%")

    # Signal 3: +1 if no investigation evidence exists
    if f.finding_type in (FindingType.EXECUTION_GAP, FindingType.SUSPICIOUS_FAST_CLOSURE, FindingType.REPEATED_INCIDENTS, FindingType.PEER_DEVIATION):
        score += 1
        reasons.append("+1: No investigation evidence exists")

    # Signal 4: +1 if multiple signals combine
    if f.finding_type in (FindingType.SUSPICIOUS_FAST_CLOSURE, FindingType.REPEATED_INCIDENTS, FindingType.PEER_DEVIATION):
        score += 1
        reasons.append("+1: Multiple signals combine")

    # Signal 5: +2 if peer deviation > 60%, or +1 if peer deviation is 40-60%
    if f.finding_type == FindingType.PEER_DEVIATION:
        dev_pct = abs(ev.get("deviation_pct", 0.0) or 0.0)
        if dev_pct > 60.0:
            score += 2
            reasons.append("+2: Peer deviation > 60%")
        elif dev_pct >= 40.0:
            score += 1
            reasons.append("+1: Peer deviation is 40–60%")

    # Priority assignment based strictly on score
    if score >= 4:
        priority = Priority.HIGH
    elif score >= 2:
        priority = Priority.MEDIUM
    else:
        priority = Priority.LOW

    return score, priority, reasons


# ---------------------------------------------------------------------------
# Finding builder & store
# ---------------------------------------------------------------------------

def build_findings(raw_findings: list[Finding]) -> list[Finding]:
    """
    Enriches raw findings with sequential finding_ids (F-001, F-002, ...),
    computes transparent priority scores, updates priority fields,
    and populates the in-memory store.

    Returns findings sorted by priority (HIGH -> MEDIUM -> LOW).
    """
    global _FINDINGS_STORE
    _FINDINGS_STORE.clear()

    built_findings: list[Finding] = []

    # Sort raw findings deterministically by org_id and rule_id first
    raw_findings_sorted = sorted(
        raw_findings, key=lambda f: (f.organization_id, f.rule_id)
    )

    for i, raw_f in enumerate(raw_findings_sorted, start=1):
        finding_id = f"F-{i:03d}"

        # Compute score and priority
        score, priority, breakdown = score_finding(raw_f)

        # Build evidence dictionary with priority breakdown
        ev_copy = dict(raw_f.evidence)
        ev_copy["priority_score"] = score
        ev_copy["priority_scoring_breakdown"] = breakdown

        built_f = Finding(
            finding_id=finding_id,
            organization_id=raw_f.organization_id,
            finding_type=raw_f.finding_type,
            priority=priority,
            title=raw_f.title,
            description=raw_f.description,
            evidence=ev_copy,
            affected_record_ids=raw_f.affected_record_ids,
            assessor_guidance=raw_f.assessor_guidance,
            rule_id=raw_f.rule_id,
            priority_score=score,
            generated_at=raw_f.generated_at,
        )

        built_findings.append(built_f)
        _FINDINGS_STORE[finding_id] = built_f

    # Sort by priority rank: HIGH -> MEDIUM -> LOW
    priority_order = {Priority.HIGH: 0, Priority.MEDIUM: 1, Priority.LOW: 2}
    built_findings.sort(key=lambda f: (priority_order[f.priority], -f.priority_score, f.finding_id))

    return built_findings


def get_all_findings() -> list[Finding]:
    """Return all findings stored in memory, sorted HIGH -> MEDIUM -> LOW."""
    priority_order = {Priority.HIGH: 0, Priority.MEDIUM: 1, Priority.LOW: 2}
    return sorted(
        _FINDINGS_STORE.values(),
        key=lambda f: (priority_order[f.priority], -f.priority_score, f.finding_id),
    )


def get_finding(finding_id: str) -> Finding | None:
    """Return single finding by ID, or None if not found."""
    return _FINDINGS_STORE.get(finding_id)


def get_evidence(finding_id: str) -> dict[str, Any] | None:
    """Return evidence dictionary for a finding, or None if not found."""
    f = get_finding(finding_id)
    return f.evidence if f else None
