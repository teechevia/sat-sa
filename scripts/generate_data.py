#!/usr/bin/env python3
"""
SAT-SA Synthetic Data Generator
================================
Generates reproducible synthetic SOC evidence for 12 organizations.
Uses a fixed random seed for full reproducibility.

Usage:
    python scripts/generate_data.py

Output (written to data/):
    organizations.csv   — 12 organizations across 3 peer groups
    alerts.csv          — ~9,830 alerts
    investigations.csv  — investigation evidence records
    escalations.csv     — escalation records
    cases.csv           — case / incident records

Ground-truth weaknesses intentionally injected:
    ORG-002  Potential Execution Gap
             ~65% of critical alerts have no investigation record.
             Rule 1 should detect this.

    ORG-003  Suspicious Fast Closure
             Critical + high alerts closed in 2–8 minutes.
             ~75% of those have no investigation record.
             Rule 2 should detect this.

    ORG-004  Repeated Incidents Without Remediation Evidence
             8 distinct (asset_id, incident_type) patterns each recur
             5–8 times in separate case records. None have
             remediation_evidence. Rule 3 should detect this.

    ORG-012  Peer Deviation (Normalized Activity)
             Only ~120 alerts for 270 active assets (~0.44/asset).
             Large-org peers average ~3.2 alerts/asset.
             Rule 4 should detect this on normalized metric deviation.

All other organizations (ORG-001, ORG-005–ORG-011) behave normally
and should produce few or no high-priority findings.
"""

import csv
import random
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

# =============================================================================
# Reproducibility — change SEED to generate a different dataset
# =============================================================================
SEED = 42
random.seed(SEED)

# =============================================================================
# File paths
# =============================================================================
ROOT     = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
(DATA_DIR / "generated").mkdir(exist_ok=True)

# =============================================================================
# Time window: Jan–Jun 2025  (6-month reporting period)
# =============================================================================
START = datetime(2025, 1, 1, 0, 0, 0)
END   = datetime(2025, 6, 30, 23, 59, 59)


def rand_dt(earliest: datetime = START, latest: datetime = END) -> datetime:
    """Return a uniformly random datetime between earliest and latest."""
    span = int((latest - earliest).total_seconds())
    return earliest + timedelta(seconds=random.randint(0, span))


def rand_dt_after(base: datetime, min_min: int, max_min: int) -> datetime:
    """Return a random datetime between min_min and max_min minutes after base."""
    secs = random.randint(min_min * 60, max_min * 60)
    return base + timedelta(seconds=secs)


def fmt(dt: datetime | None) -> str:
    """Format datetime to ISO-8601 string, or empty string if None."""
    return dt.strftime("%Y-%m-%dT%H:%M:%S") if dt else ""


def write_csv(path: Path, rows: list[dict]) -> None:
    """Write a list of row dicts to a CSV file with a header row."""
    if not rows:
        print(f"  [WARN] No rows generated for {path.name}")
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"  Wrote {len(rows):>7,} rows  ->  {path.name}")


# =============================================================================
# Organization definitions
# Tuple layout:
#   (org_id, name, size, sector, peer_group, active_asset_count, behavior)
#
# 'behavior' is internal only — it is NOT written to organizations.csv.
# It tells the generator what pattern to inject for each org.
# =============================================================================
ORG_DEFS = [
    # ── Small organizations ────────────────────────────────────────────────
    ("ORG-001", "Aegis Financial",  "small",  "finance",   "small",  45,  "healthy"),
    ("ORG-002", "Bastion Energy",   "small",  "energy",    "small",  40,  "execution_gap"),
    ("ORG-003", "Citadel Health",   "small",  "health",    "small",  38,  "fast_closure"),
    ("ORG-004", "Dagger Transport", "small",  "transport", "small",  42,  "repeated_incidents"),
    # ── Medium organizations ───────────────────────────────────────────────
    ("ORG-005", "Eagle Telecom",    "medium", "telecom",   "medium", 120, "healthy"),
    ("ORG-006", "Falcon Finance",   "medium", "finance",   "medium", 110, "healthy"),
    ("ORG-007", "Garuda Energy",    "medium", "energy",    "medium", 105, "healthy"),
    ("ORG-008", "Hawk Health",      "medium", "health",    "medium", 115, "healthy"),
    # ── Large organizations ────────────────────────────────────────────────
    ("ORG-009", "Ironclad Telecom", "large",  "telecom",   "large",  280, "healthy"),
    ("ORG-010", "Javelin Finance",  "large",  "finance",   "large",  265, "healthy"),
    ("ORG-011", "Kestrel Energy",   "large",  "energy",    "large",  290, "healthy"),
    ("ORG-012", "Lynx Transport",   "large",  "transport", "large",  270, "peer_deviation"),
]

# Alert budgets per organization.
# Small:  ~750 each   → 4 × 750 ≈ 3,010
# Medium: ~1,000 each → 4 × 1,000 = 4,000
# Large:  ~900 each   → 3 × 900 = 2,700; ORG-012 = 120  (peer deviation)
# Total:  ≈ 9,830
ALERT_BUDGETS = {
    "ORG-001": 750,  "ORG-002": 760,  "ORG-003": 750,  "ORG-004": 750,
    "ORG-005": 1000, "ORG-006": 990,  "ORG-007": 1010, "ORG-008": 1000,
    "ORG-009": 900,  "ORG-010": 910,  "ORG-011": 890,  "ORG-012": 120,
}

INCIDENT_TYPES = [
    "malware", "phishing", "brute_force", "data_exfil",
    "recon", "lateral_movement", "privilege_escalation",
]
SEVERITIES  = ["critical", "high", "medium", "low"]
SEV_WEIGHTS = [0.20, 0.30, 0.32, 0.18]  # probability weights for each severity


# =============================================================================
# Behavior parameters
# These control how each "behavior profile" generates records.
# Changing a number here changes the detection difficulty — keep that in mind.
# =============================================================================

# Probability of generating an investigation record, per severity.
# This is where execution_gap and fast_closure weaknesses are injected.
INV_RATES: dict[str, dict[str, float]] = {
    "healthy":            {"critical": 0.91, "high": 0.86, "medium": 0.80, "low": 0.68},
    "execution_gap":      {"critical": 0.35, "high": 0.86, "medium": 0.82, "low": 0.70},
    #                                  ^^^^ only 35% of criticals investigated → 65% gap
    "fast_closure":       {"critical": 0.25, "high": 0.25, "medium": 0.82, "low": 0.70},
    #                                  ^^^^ most criticals/highs closed with no investigation
    "repeated_incidents": {"critical": 0.89, "high": 0.84, "medium": 0.80, "low": 0.68},
    "peer_deviation":     {"critical": 0.88, "high": 0.83, "medium": 0.78, "low": 0.65},
}

# Probability of generating an escalation record, applied to critical+high only.
ESC_RATES: dict[str, float] = {
    "healthy": 0.22,           # normal escalation behaviour
    "execution_gap": 0.18,     # slightly lower (alerts not being escalated either)
    "fast_closure": 0.05,      # very few escalations — alerts "close" before escalating
    "repeated_incidents": 0.18,
    "peer_deviation": 0.20,
}

# Alert closure time range in minutes, per severity, per behavior.
# fast_closure injects the key anomaly: critical+high closed in 2-8 minutes.
CLOSURE_MINS: dict[str, dict[str, tuple[int, int]]] = {
    "healthy": {
        "critical": (120, 480),   "high": (480, 1440),
        "medium":  (1440, 4320),  "low":  (2880, 8640),
    },
    "execution_gap": {
        "critical": (120, 480),   "high": (480, 1440),
        "medium":  (1440, 4320),  "low":  (2880, 8640),
    },
    "fast_closure": {
        "critical": (2, 8),       "high": (2, 8),    # ← INJECTED: 2–8 minutes
        "medium":  (1440, 4320),  "low":  (2880, 8640),
    },
    "repeated_incidents": {
        "critical": (120, 480),   "high": (480, 1440),
        "medium":  (1440, 4320),  "low":  (2880, 8640),
    },
    "peer_deviation": {
        "critical": (120, 480),   "high": (480, 1440),
        "medium":  (1440, 4320),  "low":  (2880, 8640),
    },
}

# Investigation notes_length range (in characters) per severity, per behavior.
# fast_closure: critical/high notes are very short — another corroborating signal.
NOTES_LEN: dict[str, dict[str, tuple[int, int]]] = {
    "healthy":            {"critical": (250, 900), "high": (180, 750), "medium": (100, 500), "low": (50, 300)},
    "execution_gap":      {"critical": (120, 600), "high": (180, 700), "medium": (100, 500), "low": (50, 300)},
    "fast_closure":       {"critical": (20,  80),  "high": (20,  80),  "medium": (100, 500), "low": (50, 300)},
    #                                  ^^^^^^^^^^  very short notes for fast-closed alerts
    "repeated_incidents": {"critical": (200, 800), "high": (150, 700), "medium": (100, 500), "low": (50, 300)},
    "peer_deviation":     {"critical": (200, 850), "high": (160, 720), "medium": (100, 500), "low": (50, 300)},
}

INV_OUTCOMES        = ["resolved", "escalated", "false_positive", "open"]
INV_OUTCOME_WEIGHTS = [0.60,       0.20,         0.15,             0.05]


# =============================================================================
# Core record constructors
# =============================================================================

def make_alert(
    org_id: str,
    behavior: str,
    assets: list[str],
    alert_counter: list[int],
    case_id: str | None = None,
    forced_incident_type: str | None = None,
    forced_asset_id: str | None = None,
) -> dict:
    """
    Build one alert record dict.

    'investigated' and 'escalated' are intentionally NOT included as columns.
    Those will be DERIVED by normalizer.py from the investigations and
    escalations tables — never from a self-reported field.
    """
    aid      = f"A-{alert_counter[0]:05d}"
    alert_counter[0] += 1

    sev      = random.choices(SEVERITIES, weights=SEV_WEIGHTS)[0]
    inc_type = forced_incident_type or random.choice(INCIDENT_TYPES)
    asset_id = forced_asset_id      or random.choice(assets)
    created  = rand_dt()

    cl_min, cl_max = CLOSURE_MINS[behavior][sev]
    closed = rand_dt_after(created, cl_min, cl_max)
    if closed > END:
        closed = None  # alert still open at end of reporting period

    return {
        "alert_id":        aid,
        "organization_id": org_id,
        "severity":        sev,
        "incident_type":   inc_type,
        "asset_id":        asset_id,
        "case_id":         case_id or "",
        "created_at":      fmt(created),
        "closed_at":       fmt(closed),
    }


def maybe_investigation(
    alert: dict,
    behavior: str,
    inv_counter: list[int],
) -> dict | None:
    """
    Decide whether to generate an investigation record for this alert.
    Returns an investigation dict, or None if no investigation occurred.

    The probability is controlled by INV_RATES[behavior][severity].
    This is where the EXECUTION_GAP and FAST_CLOSURE weaknesses are injected —
    the investigation rate for critical alerts in those behaviors is very low.
    """
    sev = alert["severity"]
    if random.random() >= INV_RATES[behavior][sev]:
        return None  # no investigation evidence for this alert

    created = datetime.fromisoformat(alert["created_at"])

    if behavior == "fast_closure" and sev in ("critical", "high"):
        # For fast-closure org: investigations (when they happen) are also
        # very quick — another corroborating signal.
        started   = rand_dt_after(created, 0, 2)   # starts 0–2 min after alert
        completed = rand_dt_after(started, 2, 6)    # finishes 2–6 min later
    else:
        started   = rand_dt_after(created, 10, 240)  # 10 min – 4 hours
        completed = rand_dt_after(started, 30, 480)  # 30 min – 8 hours

    if completed > END:
        completed = None

    nl_min, nl_max = NOTES_LEN[behavior][sev]

    iid = f"INV-{inv_counter[0]:05d}"
    inv_counter[0] += 1

    return {
        "investigation_id": iid,
        "alert_id":         alert["alert_id"],
        "organization_id":  alert["organization_id"],
        "analyst_id":       f"ANALYST-{random.randint(1, 20):02d}",
        "started_at":       fmt(started),
        "completed_at":     fmt(completed),
        "notes_length":     random.randint(nl_min, nl_max),
        "outcome":          random.choices(INV_OUTCOMES, weights=INV_OUTCOME_WEIGHTS)[0],
    }


def maybe_escalation(
    alert: dict,
    behavior: str,
    esc_counter: list[int],
) -> dict | None:
    """
    Decide whether to generate an escalation record for this alert.
    Only critical and high severity alerts can be escalated.
    Returns an escalation dict, or None.
    """
    if alert["severity"] not in ("critical", "high"):
        return None
    if random.random() >= ESC_RATES[behavior]:
        return None

    created  = datetime.fromisoformat(alert["created_at"])
    esc_time = rand_dt_after(created, 30, 180)

    eid = f"ESC-{esc_counter[0]:05d}"
    esc_counter[0] += 1

    return {
        "escalation_id":    eid,
        "alert_id":         alert["alert_id"],
        "organization_id":  alert["organization_id"],
        "escalated_at":     fmt(esc_time),
        "escalation_level": random.randint(1, 3),
    }


def make_case(
    org_id: str,
    asset_id: str,
    incident_type: str,
    case_counter: list[int],
    remediation_evidence: bool | None = None,
) -> dict:
    """
    Build one case record dict.
    remediation_evidence: if None, randomly assigned (75% chance True).
    """
    cid    = f"CASE-{case_counter[0]:05d}"
    case_counter[0] += 1
    opened = rand_dt()
    closed = rand_dt_after(opened, 480, 10080)  # 8 hours – 7 days
    if closed > END:
        closed = None

    if remediation_evidence is None:
        remediation_evidence = random.random() < 0.75

    return {
        "case_id":             cid,
        "organization_id":     org_id,
        "asset_id":            asset_id,
        "incident_type":       incident_type,
        "opened_at":           fmt(opened),
        "closed_at":           fmt(closed),
        "recurrence_count":    0,                 # incremented as alerts link to this case
        "remediation_evidence": remediation_evidence,
    }


# =============================================================================
# Standard organization generator
# Used for: healthy, execution_gap, fast_closure, peer_deviation behaviors
# =============================================================================

def gen_standard_org(
    org_id: str,
    behavior: str,
    assets: list[str],
    n_alerts: int,
    alert_counter: list[int],
    inv_counter: list[int],
    esc_counter: list[int],
    case_counter: list[int],
    reserved_pairs: set[tuple[str, str]] | None = None,
) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    """
    Generate all records for an organization with standard behavior.

    About 25% of alerts are linked to a randomly chosen case.
    Cases are pre-generated, then alerts are randomly assigned to them.

    reserved_pairs: optional set of (asset_id, incident_type) tuples that
        this function must NOT use when creating the normal case pool.
        Used by gen_repeated_incidents_org to prevent the normal generator
        from contaminating the 8 intentionally injected patterns.

    Returns: (alerts, investigations, escalations, cases)
    """
    alerts, investigations, escalations, cases = [], [], [], []

    # Pre-generate a case pool -- 25% of alerts will link to one of these.
    # If reserved_pairs is set, retry until we find a non-reserved combination.
    # With only 8 reserved pairs out of hundreds of possible combinations,
    # a retry loop of 20 attempts will virtually never exhaust without success.
    n_cases   = max(1, int(n_alerts * 0.25))
    case_pool: list[dict] = []
    for _ in range(n_cases):
        for _attempt in range(20):
            candidate_asset = random.choice(assets)
            candidate_type  = random.choice(INCIDENT_TYPES)
            if reserved_pairs is None or (candidate_asset, candidate_type) not in reserved_pairs:
                break
        c = make_case(org_id, candidate_asset, candidate_type, case_counter)
        case_pool.append(c)
    cases.extend(case_pool)

    case_ids   = [c["case_id"] for c in case_pool]
    case_by_id = {c["case_id"]: c for c in case_pool}

    for _ in range(n_alerts):
        # 25% of alerts are linked to a case
        linked_cid = random.choice(case_ids) if random.random() < 0.25 else None

        alert = make_alert(org_id, behavior, assets, alert_counter, case_id=linked_cid)
        alerts.append(alert)

        if linked_cid:
            case_by_id[linked_cid]["recurrence_count"] += 1

        inv = maybe_investigation(alert, behavior, inv_counter)
        if inv:
            investigations.append(inv)

        esc = maybe_escalation(alert, behavior, esc_counter)
        if esc:
            escalations.append(esc)

    return alerts, investigations, escalations, cases


# =============================================================================
# Repeated-incidents organization generator  (ORG-004 only)
# =============================================================================

def gen_repeated_incidents_org(
    org_id: str,
    behavior: str,
    assets: list[str],
    n_alerts: int,
    alert_counter: list[int],
    inv_counter: list[int],
    esc_counter: list[int],
    case_counter: list[int],
) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    """
    Generate data for ORG-004.

    INJECTED WEAKNESS:
        8 distinct (asset_id, incident_type) patterns, each recurring
        5–8 times in separate case records.  All flagged cases have
        remediation_evidence = False.

        This is detectable by Rule 3 (Repeated Incidents).
        The investigation rate is otherwise normal — the problem is the
        cases, not the individual alert investigations.
    """
    alerts, investigations, escalations, cases = [], [], [], []

    # ── Phase 1: Inject repeated incident patterns ─────────────────────────
    PATTERN_COUNT      = 8
    REPEAT_MIN, REPEAT_MAX = 5, 8

    # Build 8 distinct (asset, incident_type) pairs from the first 15 assets
    pattern_assets     = assets[:15]
    pattern_inc_types  = INCIDENT_TYPES[:5]  # first 5 incident types
    patterns: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for a in pattern_assets:
        for t in pattern_inc_types:
            if (a, t) not in seen and len(patterns) < PATTERN_COUNT:
                patterns.append((a, t))
                seen.add((a, t))

    for pat_asset, pat_type in patterns:
        n_reps = random.randint(REPEAT_MIN, REPEAT_MAX)

        for _ in range(n_reps):
            # Each occurrence of the pattern gets its own case record.
            # remediation_evidence = False for all repeated patterns.
            case = make_case(
                org_id, pat_asset, pat_type, case_counter,
                remediation_evidence=False,  # ← INJECTED WEAKNESS
            )
            cases.append(case)

            # 1–3 alerts per case occurrence
            n_case_alerts = random.randint(1, 3)
            for _ in range(n_case_alerts):
                alert = make_alert(
                    org_id, behavior, assets, alert_counter,
                    case_id=case["case_id"],
                    forced_incident_type=pat_type,
                    forced_asset_id=pat_asset,
                )
                alerts.append(alert)
                case["recurrence_count"] += 1

                inv = maybe_investigation(alert, behavior, inv_counter)
                if inv:
                    investigations.append(inv)

                esc = maybe_escalation(alert, behavior, esc_counter)
                if esc:
                    escalations.append(esc)

    # ── Phase 2: Fill remaining alert budget with normal alerts ────────────
    # IMPORTANT: pass the reserved_pairs so the normal case generator cannot
    # accidentally create a case with remediation_evidence=True for any of the
    # 8 intentionally injected (asset_id, incident_type) patterns.
    reserved_pairs: set[tuple[str, str]] = set(patterns)

    remaining = n_alerts - len(alerts)
    if remaining > 0:
        std_a, std_i, std_e, std_c = gen_standard_org(
            org_id, behavior, assets, remaining,
            alert_counter, inv_counter, esc_counter, case_counter,
            reserved_pairs=reserved_pairs,
        )
        alerts.extend(std_a)
        investigations.extend(std_i)
        escalations.extend(std_e)
        cases.extend(std_c)

    return alerts, investigations, escalations, cases


# =============================================================================
# Main entry point
# =============================================================================

def generate_all() -> None:
    """Generate all synthetic data files and write them to data/."""
    print("\n" + "=" * 65)
    print("SAT-SA Synthetic Data Generator")
    print(f"Seed:   {SEED}")
    print(f"Output: {DATA_DIR}")
    print("=" * 65)

    all_orgs:           list[dict] = []
    all_alerts:         list[dict] = []
    all_investigations: list[dict] = []
    all_escalations:    list[dict] = []
    all_cases:          list[dict] = []

    # Shared mutable counters.
    # Using a single-element list lets us pass them into functions and
    # mutate them in place (Python int is immutable; list is mutable).
    alert_counter = [1]
    inv_counter   = [1]
    esc_counter   = [1]
    case_counter  = [1]

    for org_tuple in ORG_DEFS:
        org_id, name, size, sector, peer_group, active_asset_count, behavior = org_tuple

        # Build the org record (behavior is internal only, not in the CSV)
        all_orgs.append({
            "organization_id":    org_id,
            "name":               name,
            "size":               size,
            "sector":             sector,
            "peer_group":         peer_group,
            "active_asset_count": active_asset_count,
        })

        # Asset pool: unique identifiers for each active asset in this org
        assets   = [f"ASSET-{org_id}-{i:03d}" for i in range(1, active_asset_count + 1)]
        n_alerts = ALERT_BUDGETS[org_id]

        print(f"\n  {org_id}  {name:<20}  {size:<7}  behavior={behavior}  "
              f"alerts={n_alerts}  assets={active_asset_count}")

        if behavior == "repeated_incidents":
            a, i, e, c = gen_repeated_incidents_org(
                org_id, behavior, assets, n_alerts,
                alert_counter, inv_counter, esc_counter, case_counter,
            )
        else:
            a, i, e, c = gen_standard_org(
                org_id, behavior, assets, n_alerts,
                alert_counter, inv_counter, esc_counter, case_counter,
            )

        all_alerts.extend(a)
        all_investigations.extend(i)
        all_escalations.extend(e)
        all_cases.extend(c)

    print("\n--- Writing CSV files ---")
    write_csv(DATA_DIR / "organizations.csv",  all_orgs)
    write_csv(DATA_DIR / "alerts.csv",         all_alerts)
    write_csv(DATA_DIR / "investigations.csv", all_investigations)
    write_csv(DATA_DIR / "escalations.csv",    all_escalations)
    write_csv(DATA_DIR / "cases.csv",          all_cases)

    print_stats(all_orgs, all_alerts, all_investigations, all_escalations, all_cases)


# =============================================================================
# Statistics reporter
# Verifies that the injected weaknesses are actually present in the data.
# =============================================================================

def print_stats(
    orgs:           list[dict],
    alerts:         list[dict],
    investigations: list[dict],
    escalations:    list[dict],
    cases:          list[dict],
) -> None:
    """Print a generation summary and verify all injected weaknesses."""

    inv_alert_ids = {inv["alert_id"] for inv in investigations}

    alert_by_org: dict[str, list[dict]] = defaultdict(list)
    for a in alerts:
        alert_by_org[a["organization_id"]].append(a)

    case_by_org: dict[str, list[dict]] = defaultdict(list)
    for c in cases:
        case_by_org[c["organization_id"]].append(c)

    # ── Overview table ─────────────────────────────────────────────────────
    print("\n" + "=" * 90)
    print("GENERATION OVERVIEW")
    print("=" * 90)
    print(f"  Total organizations:   {len(orgs)}")
    print(f"  Total alerts:          {len(alerts):,}")
    print(f"  Total investigations:  {len(investigations):,}")
    print(f"  Total escalations:     {len(escalations):,}")
    print(f"  Total cases:           {len(cases):,}")

    print()
    hdr = (f"{'Org':<10} {'Name':<20} {'Size':<7} {'Alerts':>7} "
           f"{'Assets':>7} {'A/Asset':>8} {'CritInvR':>9}  Behavior")
    print(hdr)
    print("-" * 90)

    org_behavior = {d[0]: d[6] for d in ORG_DEFS}

    for o in orgs:
        oid    = o["organization_id"]
        org_a  = alert_by_org[oid]
        crits  = [a for a in org_a if a["severity"] == "critical"]
        n_crit = len(crits)
        n_cinv = sum(1 for a in crits if a["alert_id"] in inv_alert_ids)
        c_rate = n_cinv / n_crit if n_crit else 0.0
        pa     = len(org_a) / o["active_asset_count"]
        bhv    = org_behavior[oid]
        marker = " << INJECTED" if bhv != "healthy" else ""

        print(
            f"  {oid:<10} {o['name']:<20} {o['size']:<7} "
            f"{len(org_a):>7,} {o['active_asset_count']:>7} "
            f"{pa:>8.2f} {c_rate:>8.1%}  {bhv}{marker}"
        )

    # ── Injected weakness verification ─────────────────────────────────────
    print("\n" + "=" * 90)
    print("INJECTED WEAKNESS VERIFICATION")
    print("=" * 90)

    all_pass = True

    # ── ORG-002: Execution Gap ─────────────────────────────────────────────
    o2_alerts = alert_by_org["ORG-002"]
    o2_crits  = [a for a in o2_alerts if a["severity"] == "critical"]
    o2_uninv  = [a for a in o2_crits  if a["alert_id"] not in inv_alert_ids]
    o2_rate   = len(o2_uninv) / max(1, len(o2_crits))
    o2_pass   = o2_rate > 0.50
    all_pass  = all_pass and o2_pass

    print(f"\n  [ORG-002] Potential Execution Gap")
    print(f"    Critical alerts total:      {len(o2_crits):,}")
    print(f"    Without investigation:      {len(o2_uninv):,}  ({o2_rate:.1%})")
    print(f"    Expected: >50% gap          {'PASS' if o2_pass else 'FAIL'}")

    # ── ORG-003: Suspicious Fast Closure ──────────────────────────────────
    o3_alerts    = alert_by_org["ORG-003"]
    o3_crit_high = [a for a in o3_alerts if a["severity"] in ("critical", "high")]
    o3_fast, o3_fast_uninv = [], []
    for a in o3_crit_high:
        if not a["closed_at"]:
            continue
        mins = ((datetime.fromisoformat(a["closed_at"]) -
                 datetime.fromisoformat(a["created_at"])).total_seconds() / 60)
        if mins < 10:
            o3_fast.append(a)
            if a["alert_id"] not in inv_alert_ids:
                o3_fast_uninv.append(a)
    o3_total     = max(1, len(o3_crit_high))
    o3_fast_rate = len(o3_fast_uninv) / o3_total
    o3_pass      = o3_fast_rate > 0.55
    all_pass     = all_pass and o3_pass

    print(f"\n  [ORG-003] Suspicious Fast Closure")
    print(f"    Critical+High alerts total: {len(o3_crit_high):,}")
    print(f"    Closed in <10 min:          {len(o3_fast):,}  ({len(o3_fast)/o3_total:.1%})")
    print(f"    Fast + uninvestigated:      {len(o3_fast_uninv):,}  ({o3_fast_rate:.1%})")
    print(f"    Expected: >55% fast+uninv   {'PASS' if o3_pass else 'FAIL'}")

    # ── ORG-004: Repeated Incidents ───────────────────────────────────────
    o4_cases = case_by_org["ORG-004"]

    def is_false_val(v) -> bool:
        """Handles bool False, string 'False', and string 'false'."""
        if isinstance(v, bool):
            return not v
        return str(v).strip().lower() == "false"

    repeat_groups: dict[tuple, list[dict]] = defaultdict(list)
    for c in o4_cases:
        repeat_groups[(c["asset_id"], c["incident_type"])].append(c)

    flagged = [
        (k, v) for k, v in repeat_groups.items()
        if len(v) >= 3 and all(is_false_val(c["remediation_evidence"]) for c in v)
    ]
    o4_pass  = len(flagged) >= 6
    all_pass = all_pass and o4_pass

    print(f"\n  [ORG-004] Repeated Incidents Without Remediation Evidence")
    print(f"    Total cases:                {len(o4_cases):,}")
    print(f"    Distinct (asset, type):     {len(repeat_groups)}")
    print(f"    Flaggable groups (>=3, no remediation): {len(flagged)}")
    print(f"    Expected: >=6 groups        {'PASS' if o4_pass else 'FAIL'}")

    # ── ORG-012: Peer Deviation ───────────────────────────────────────────
    large_orgs = [o for o in orgs if o["peer_group"] == "large"]
    per_assets: dict[str, float] = {}
    print("\n  [ORG-012] Peer Deviation - Normalized Activity (alerts/asset)")
    for o in large_orgs:
        oid = o["organization_id"]
        n   = len(alert_by_org[oid])
        pa  = n / o["active_asset_count"]
        per_assets[oid] = pa
        flag = "  << ANOMALY" if oid == "ORG-012" else ""
        print(f"    {oid}: {n:>4} alerts / {o['active_asset_count']:>3} assets "
              f"= {pa:.2f} alerts/asset{flag}")

    peers_excl_012 = sorted(v for k, v in per_assets.items() if k != "ORG-012")
    # Median of 3 values
    peer_median = peers_excl_012[len(peers_excl_012) // 2]
    o12_pa      = per_assets.get("ORG-012", 0.0)
    deviation   = abs(o12_pa - peer_median) / peer_median if peer_median > 0 else 0
    o12_pass    = deviation > 0.40
    all_pass    = all_pass and o12_pass

    print(f"    Peer median (leave-one-out, ORG-009/010/011): {peer_median:.2f}")
    print(f"    ORG-012 deviation from peer:  {deviation*100:.1f}%")
    print(f"    Expected: >40% deviation      {'PASS' if o12_pass else 'FAIL'}")

    # -- Summary -----------------------------------------------------------
    print("\n" + "=" * 90)
    print("  Overall ground-truth check: " + ("ALL PASS" if all_pass else "SOME CHECKS FAILED"))
    print("=" * 90)
    print("\nGeneration complete.  Next step: run the validator and analytics (Stage 4).\n")


# =============================================================================
# Entry point
# =============================================================================
if __name__ == "__main__":
    generate_all()
