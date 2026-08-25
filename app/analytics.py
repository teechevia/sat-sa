"""
SAT-SA Analytics Engine
========================
Computes per-organization operational metrics and leave-one-out peer baselines.

Design principles:
    - Every metric is deterministic, reproducible, traceable to source records.
    - No NaN / Inf values in the final output: safe_float() handles edge cases.
    - No risk score. No weights. No ML.
    - Denominators are always guarded (division by zero -> 0.0, not NaN).
    - Peer baselines use leave-one-out median/mean/std within the same peer_group.
      The target organization is EXCLUDED from its own peer baseline.

Metrics computed per organization:
    total_alerts, critical_alerts, high_alerts
    investigation_rate, critical_investigation_rate
    escalation_rate (critical+high), critical_escalation_rate
    closure_without_investigation_rate
    median_closure_duration_min, median_critical_closure_duration_min
    median_high_closure_duration_min
    median_investigation_duration_min
    pct_fast_closed_uninvestigated  (critical+high closed <10 min, uninvestigated)
    repeat_incident_groups          (asset+type pairs with >=3 cases)
    repeat_groups_without_remediation
    alerts_per_active_asset, critical_alerts_per_active_asset
    total_cases, total_investigations, total_escalations

Peer baseline metrics (leave-one-out):
    alerts_per_active_asset, critical_alerts_per_active_asset
    investigation_rate, critical_investigation_rate, escalation_rate

Usage:
    norm = normalize_all(raw)
    metrics = compute_all_org_metrics(norm)
    report  = build_analytics_report(norm, dq_report, metrics)
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from app.config import THRESHOLD_FAST_MINUTES, THRESHOLD_REPEAT_COUNT

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe(value: Any, default: float = 0.0) -> float:
    """
    Convert any numeric value to a JSON-safe float.
    NaN / Inf / None / NaT all become `default` (usually 0.0 or None).
    Returns None for intentionally missing values (e.g. no closed alerts).
    """
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return default
    try:
        v = float(value)
        if math.isnan(v) or math.isinf(v):
            return default
        return round(v, 4)
    except (TypeError, ValueError):
        return default


def _safe_rate(numerator: float, denominator: float) -> float:
    """Return numerator/denominator, or 0.0 if denominator is 0."""
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 4)


def _median_or_none(series: pd.Series) -> float | None:
    """Return median of non-NaN values, or None if the series is empty."""
    valid = series.dropna()
    if valid.empty:
        return None
    return round(float(valid.median()), 2)


def _mean_or_none(values: list[float]) -> float | None:
    if not values:
        return None
    return round(float(np.mean(values)), 4)


def _std_or_none(values: list[float]) -> float | None:
    """Sample std (ddof=1). None if fewer than 2 values."""
    if len(values) < 2:
        return None
    return round(float(np.std(values, ddof=1)), 4)


# ---------------------------------------------------------------------------
# Per-organization metrics
# ---------------------------------------------------------------------------

def compute_org_metrics(
    org_id:    str,
    org_row:   pd.Series,
    alerts:    pd.DataFrame,   # enriched alerts (full dataset)
    cases:     pd.DataFrame,   # typed cases (full dataset)
    invs:      pd.DataFrame,   # typed investigations (full dataset)
    escs:      pd.DataFrame,   # typed escalations (full dataset)
) -> dict[str, Any]:
    """
    Compute all operational metrics for one organization.

    All rate calculations use DERIVED investigated/escalated fields.
    Never reads self-reported status columns.

    Args:
        org_id:  The target organization ID.
        org_row: The organization record (from organizations DataFrame).
        alerts:  Enriched alerts DataFrame (all organizations — will be filtered).
        cases:   Typed cases DataFrame.
        invs:    Typed investigations DataFrame.
        escs:    Typed escalations DataFrame.

    Returns:
        dict with all metrics as JSON-safe floats/ints.
    """
    # ── Slice to this organization ────────────────────────────────────────
    a  = alerts[alerts["organization_id"] == org_id].copy()
    c  = cases[cases["organization_id"]   == org_id].copy()

    active_assets = int(org_row["active_asset_count"]) if pd.notna(org_row["active_asset_count"]) else 1

    n_total    = len(a)
    n_critical = int((a["severity"] == "critical").sum())
    n_high     = int((a["severity"] == "high").sum())
    n_crithigh = n_critical + n_high

    n_inv      = int(a["investigated"].sum())
    n_esc      = int(a["escalated"].sum())
    n_cases    = int(c.shape[0])
    n_invs_tot = int(invs[invs["organization_id"] == org_id].shape[0])
    n_escs_tot = int(escs[escs["organization_id"] == org_id].shape[0])

    # ── Investigation rates ────────────────────────────────────────────────
    investigation_rate = _safe_rate(n_inv, n_total)

    crit_a     = a[a["severity"] == "critical"]
    n_crit_inv = int(crit_a["investigated"].sum())
    critical_investigation_rate = _safe_rate(n_crit_inv, n_critical)

    # ── Escalation rates ──────────────────────────────────────────────────
    crithigh_a       = a[a["severity"].isin(["critical", "high"])]
    n_crithigh_esc   = int(crithigh_a["escalated"].sum())
    escalation_rate  = _safe_rate(n_crithigh_esc, n_crithigh)

    n_crit_esc       = int(crit_a["escalated"].sum())
    critical_escalation_rate = _safe_rate(n_crit_esc, n_critical)

    # ── Closure-without-investigation rate ────────────────────────────────
    # Fraction of CLOSED alerts that were never investigated.
    closed_a     = a[a["closed_at"].notna()]
    n_closed     = len(closed_a)
    n_closed_uninv = int((closed_a["investigated"] == False).sum())
    closure_without_investigation_rate = _safe_rate(n_closed_uninv, n_closed)

    # ── Closure duration (minutes) ────────────────────────────────────────
    median_closure_duration_min          = _median_or_none(a["closure_duration_min"])
    median_critical_closure_duration_min = _median_or_none(crit_a["closure_duration_min"])
    median_high_closure_duration_min     = _median_or_none(
        a[a["severity"] == "high"]["closure_duration_min"]
    )

    # ── Fast-closed and uninvestigated (key signal for ORG-003) ──────────
    # An alert is "fast-closed" if closure_duration_min < THRESHOLD_FAST_MINUTES.
    fast_uninv = crithigh_a[
        (crithigh_a["closure_duration_min"] < THRESHOLD_FAST_MINUTES)
        & (crithigh_a["investigated"] == False)
        & crithigh_a["closure_duration_min"].notna()
    ]
    pct_fast_closed_uninvestigated = _safe_rate(len(fast_uninv), n_crithigh)

    # ── Investigation duration (from investigation records) ───────────────
    inv_a = a[a["investigation_dur_min"].notna()]
    median_investigation_duration_min = _median_or_none(inv_a["investigation_dur_min"])

    # ── Normalized alert volume (key metric for peer comparison) ──────────
    alerts_per_active_asset           = _safe_rate(n_total, active_assets)
    critical_alerts_per_active_asset  = _safe_rate(n_critical, active_assets)

    # ── Repeated incident groups (key signal for ORG-004) ─────────────────
    # Count (asset_id, incident_type) pairs that appear in >= THRESHOLD_REPEAT_COUNT
    # separate case records for this organization.
    repeat_incident_groups = 0
    repeat_groups_without_remediation = 0

    if n_cases > 0:
        grouped = (
            c.groupby(["asset_id", "incident_type"])
             .agg(
                 count=("case_id", "count"),
                 all_no_rem=("remediation_evidence", lambda x: (x == False).all()),
             )
        )
        repeat_mask   = grouped["count"] >= THRESHOLD_REPEAT_COUNT
        repeat_incident_groups = int(repeat_mask.sum())
        repeat_groups_without_remediation = int(
            (repeat_mask & grouped["all_no_rem"]).sum()
        )

    return {
        # Identifiers
        "organization_id":    org_id,
        "peer_group":         str(org_row.get("peer_group", "")),
        "active_asset_count": active_assets,

        # Counts
        "total_alerts":       n_total,
        "critical_alerts":    n_critical,
        "high_alerts":        n_high,
        "total_cases":        n_cases,
        "total_investigations": n_invs_tot,
        "total_escalations":  n_escs_tot,

        # Investigation (evidence-derived, never self-reported)
        "n_investigated":            n_inv,
        "n_critical_investigated":   n_crit_inv,
        "investigation_rate":        investigation_rate,
        "critical_investigation_rate": critical_investigation_rate,

        # Escalation (evidence-derived)
        "n_escalated":               n_esc,
        "escalation_rate":           escalation_rate,
        "critical_escalation_rate":  critical_escalation_rate,

        # Closure quality
        "closure_without_investigation_rate": closure_without_investigation_rate,
        "pct_fast_closed_uninvestigated":     pct_fast_closed_uninvestigated,

        # Duration medians (None = not enough data)
        "median_closure_duration_min":          median_closure_duration_min,
        "median_critical_closure_duration_min": median_critical_closure_duration_min,
        "median_high_closure_duration_min":     median_high_closure_duration_min,
        "median_investigation_duration_min":    median_investigation_duration_min,

        # Normalized volume (primary peer comparison metric)
        "alerts_per_active_asset":          alerts_per_active_asset,
        "critical_alerts_per_active_asset": critical_alerts_per_active_asset,

        # Repeated incidents
        "repeat_incident_groups":             repeat_incident_groups,
        "repeat_groups_without_remediation":  repeat_groups_without_remediation,
    }


def compute_all_org_metrics(norm: "NormalizedData") -> list[dict[str, Any]]:  # type: ignore
    """
    Compute metrics for every organization and return a list of metric dicts.
    """
    all_metrics: list[dict[str, Any]] = []

    for _, org_row in norm.organizations.iterrows():
        org_id = str(org_row["organization_id"]).strip()
        m = compute_org_metrics(
            org_id=org_id,
            org_row=org_row,
            alerts=norm.alerts,
            cases=norm.cases,
            invs=norm.investigations,
            escs=norm.escalations,
        )
        all_metrics.append(m)

    return all_metrics


# ---------------------------------------------------------------------------
# Peer baseline computation (leave-one-out)
# ---------------------------------------------------------------------------

# Metrics used for peer comparison.
# Each entry: (metric_key, display_name)
PEER_METRICS: list[tuple[str, str]] = [
    ("alerts_per_active_asset",           "Alerts per active asset"),
    ("critical_alerts_per_active_asset",  "Critical alerts per active asset"),
    ("investigation_rate",                "Investigation rate"),
    ("critical_investigation_rate",       "Critical investigation rate"),
    ("escalation_rate",                   "Escalation rate"),
    ("median_closure_duration_min",       "Median closure duration (min)"),
    ("median_critical_closure_duration_min", "Median critical closure duration (min)"),
    ("pct_fast_closed_uninvestigated",    "Pct fast-closed uninvestigated"),
]


def compute_peer_baselines(
    all_metrics: list[dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    """
    For each organization, compute leave-one-out peer baselines.

    The target organization is EXCLUDED from its own peer baseline.
    Peers are all organizations in the same peer_group.

    Returns:
        dict keyed by organization_id, values are peer baseline dicts with
        {metric}_median, {metric}_mean, {metric}_std, and deviation info.

    Deviation from peer median:
        deviation_pct = (org_value - peer_median) / peer_median * 100
        direction = "above" | "below" | "at"
    """
    # Index metrics by org_id for fast lookup
    by_org: dict[str, dict] = {m["organization_id"]: m for m in all_metrics}

    baselines: dict[str, dict[str, Any]] = {}

    for m in all_metrics:
        org_id     = m["organization_id"]
        peer_group = m["peer_group"]

        # Peers = same peer_group, excluding self
        peer_metrics = [
            pm for pm in all_metrics
            if pm["peer_group"] == peer_group and pm["organization_id"] != org_id
        ]
        n_peers = len(peer_metrics)

        baseline: dict[str, Any] = {"n_peers": n_peers, "peer_group": peer_group}
        deviations: dict[str, Any] = {}

        for key, _label in PEER_METRICS:
            peer_values = [
                pm[key] for pm in peer_metrics
                if pm.get(key) is not None
            ]

            p_median = _safe(np.median(peer_values)) if peer_values else None
            p_mean   = _mean_or_none(peer_values)
            p_std    = _std_or_none(peer_values)

            baseline[f"{key}_median"] = p_median
            baseline[f"{key}_mean"]   = p_mean
            baseline[f"{key}_std"]    = p_std

            # Deviation of this org from peer median
            org_value = m.get(key)
            if org_value is not None and p_median is not None and p_median != 0:
                dev_pct  = round((org_value - p_median) / p_median * 100, 1)
                dev_abs  = round(org_value - p_median, 4)
                direction = "above" if dev_pct > 0 else ("below" if dev_pct < 0 else "at")
            else:
                dev_pct  = None
                dev_abs  = None
                direction = None

            deviations[key] = {
                "org_value":     org_value,
                "peer_median":   p_median,
                "deviation_pct": dev_pct,
                "deviation_abs": dev_abs,
                "direction":     direction,
            }

        baselines[org_id] = {"baseline": baseline, "deviations": deviations}

    return baselines


# ---------------------------------------------------------------------------
# Analytics report builder
# ---------------------------------------------------------------------------

def build_analytics_report(
    norm:        "NormalizedData",  # type: ignore
    dq_report:   "DataQualityReport",  # type: ignore
    all_metrics: list[dict[str, Any]],
    peer_baselines: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """
    Build a JSON-serializable analytics report.

    The report is the machine-readable output of Stage 3.
    It contains per-organization metrics, peer baselines, and
    data quality information.

    The structure is flat and transparent — no hidden scoring.
    """
    # Add org name and size to each metric record
    org_lookup = norm.organizations.set_index("organization_id").to_dict("index")

    org_records = []
    for m in all_metrics:
        org_id  = m["organization_id"]
        org_row = org_lookup.get(org_id, {})
        pb      = peer_baselines.get(org_id, {})

        org_records.append({
            "organization_id": org_id,
            "name":            org_row.get("name", ""),
            "size":            org_row.get("size", ""),
            "peer_group":      org_row.get("peer_group", ""),
            "metrics":         {k: v for k, v in m.items()
                                if k not in ("organization_id", "peer_group",
                                             "active_asset_count")},
            "active_asset_count": m.get("active_asset_count"),
            "peer_baseline":   pb.get("baseline", {}),
            "peer_deviations": pb.get("deviations", {}),
        })

    # Data quality summary
    dq_summary = {
        "total_records_checked": dq_report.total_records_checked,
        "issue_count":           dq_report.issue_count,
        "tables_checked":        dq_report.tables_checked,
        "issues": [
            {
                "table":     i.table,
                "record_id": i.record_id,
                "field":     i.field,
                "issue":     i.issue,
            }
            for i in dq_report.issues
        ],
    }

    return {
        "meta": {
            "generated_at": dq_report.generated_at.isoformat(),
            "total_orgs":   len(all_metrics),
            "total_alerts": int(norm.alerts.shape[0]),
            "total_investigations": int(norm.investigations.shape[0]),
            "total_escalations":    int(norm.escalations.shape[0]),
            "total_cases":          int(norm.cases.shape[0]),
        },
        "data_quality":    dq_summary,
        "organizations":   org_records,
    }
