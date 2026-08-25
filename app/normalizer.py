"""
SAT-SA Normalizer
=================
Converts raw string DataFrames from data_loader.py into typed DataFrames
with proper dtypes and DERIVED fields.

CRITICAL derivation rules (never trust self-reported status):
    alert.investigated:
        True IFF a valid record exists in investigations.csv for this alert_id.
        Never read from any column on the alert row itself.

    alert.escalated:
        True IFF at least one record exists in escalations.csv for this alert_id.
        Never read from any column on the alert row itself.

Derived fields added to alerts:
    investigated            (bool)    — from investigations table
    escalated               (bool)    — from escalations table
    escalation_count        (int)     — number of escalation records
    has_case                (bool)    — case_id is non-empty
    closure_duration_min    (float?)  — (closed_at - created_at) / 60
    investigation_id        (str?)    — from investigations join
    investigation_started   (datetime?) — from investigations join
    investigation_completed (datetime?) — from investigations join
    investigation_notes_len (int?)    — from investigations join
    investigation_outcome   (str?)    — from investigations join
    investigation_dur_min   (float?)  — (completed - started) / 60
    investigation_lag_min   (float?)  — (inv_started - alert_created) / 60

Output:
    NormalizedData.alerts is the central DataFrame for all analytics.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class NormalizedData:
    """
    Container of typed, enriched DataFrames ready for analytics.py.

    All datetime columns are proper pandas Timestamps (NaT for missing).
    Numeric columns are float64 / int64 (not strings).
    Boolean derived columns ('investigated', 'escalated', 'has_case')
    are always present on the alerts DataFrame.
    """
    organizations:   pd.DataFrame   # org_id, name, size, peer_group, active_asset_count (int)
    alerts:          pd.DataFrame   # enriched alerts with derived columns
    investigations:  pd.DataFrame   # typed: datetimes, notes_length as int
    escalations:     pd.DataFrame   # typed: datetime, escalation_level as int
    cases:           pd.DataFrame   # typed: remediation_evidence as bool


# ---------------------------------------------------------------------------
# Per-table normalizers
# ---------------------------------------------------------------------------

def normalize_organizations(df: pd.DataFrame) -> pd.DataFrame:
    """Cast organization fields to proper types."""
    out = df.copy()
    out["active_asset_count"] = pd.to_numeric(
        out["active_asset_count"], errors="coerce"
    ).astype("Int64")          # nullable integer
    return out


def normalize_investigations(df: pd.DataFrame) -> pd.DataFrame:
    """Cast investigation fields. All datetimes use errors='coerce' -> NaT."""
    out = df.copy()
    out["started_at"]    = pd.to_datetime(out["started_at"],    errors="coerce")
    out["completed_at"]  = pd.to_datetime(
        out["completed_at"].replace("", np.nan), errors="coerce"
    )
    out["notes_length"]  = pd.to_numeric(out["notes_length"], errors="coerce").astype("Int64")

    # investigation_duration_minutes: only meaningful when completed_at is not NaT
    out["investigation_dur_min"] = (
        (out["completed_at"] - out["started_at"]).dt.total_seconds() / 60
    )
    return out


def normalize_escalations(df: pd.DataFrame) -> pd.DataFrame:
    """Cast escalation fields."""
    out = df.copy()
    out["escalated_at"]     = pd.to_datetime(out["escalated_at"], errors="coerce")
    out["escalation_level"] = pd.to_numeric(
        out["escalation_level"], errors="coerce"
    ).astype("Int64")
    return out


def normalize_cases(df: pd.DataFrame) -> pd.DataFrame:
    """Cast case fields. remediation_evidence: 'True'/'False' -> bool."""
    out = df.copy()
    out["opened_at"]  = pd.to_datetime(out["opened_at"],  errors="coerce")
    out["closed_at"]  = pd.to_datetime(
        out["closed_at"].replace("", np.nan), errors="coerce"
    )
    out["recurrence_count"] = pd.to_numeric(
        out["recurrence_count"], errors="coerce"
    ).astype("Int64")
    # Map string 'True'/'False' -> bool. Unknown values -> NaN.
    out["remediation_evidence"] = out["remediation_evidence"].map(
        {"True": True, "False": False}
    )
    return out


def enrich_alerts(
    raw_alerts: pd.DataFrame,
    typed_invs:  pd.DataFrame,    # already passed through normalize_investigations()
    raw_escs:    pd.DataFrame,    # already passed through normalize_escalations()
) -> pd.DataFrame:
    """
    Build the central enriched alerts DataFrame.

    DERIVATION:
        investigated  <- alert_id in typed_invs.alert_id
        escalated     <- alert_id in raw_escs.alert_id

    These are NEVER read from any self-reported column.
    """
    df = raw_alerts.copy()

    # ── Cast base alert fields ───────────────────────────────────────────
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
    df["closed_at"]  = pd.to_datetime(
        df["closed_at"].replace("", np.nan), errors="coerce"
    )
    df["case_id"]    = df["case_id"].replace("", pd.NA)

    # ── DERIVE: investigated ─────────────────────────────────────────────
    # True IFF a valid investigation record exists for this alert.
    inv_alert_ids       = set(typed_invs["alert_id"].dropna().astype(str))
    df["investigated"]  = df["alert_id"].isin(inv_alert_ids)

    # ── DERIVE: escalated / escalation_count ─────────────────────────────
    esc_alert_ids      = set(raw_escs["alert_id"].dropna().astype(str))
    df["escalated"]    = df["alert_id"].isin(esc_alert_ids)

    esc_counts         = (
        raw_escs.groupby("alert_id").size()
                .rename("escalation_count")
                .reset_index()
    )
    df = df.merge(esc_counts, on="alert_id", how="left")
    df["escalation_count"] = df["escalation_count"].fillna(0).astype(int)

    # ── DERIVE: has_case ─────────────────────────────────────────────────
    df["has_case"] = df["case_id"].notna()

    # ── DERIVE: closure_duration_min ─────────────────────────────────────
    # Minutes from alert creation to closure. NaN if alert is still open.
    df["closure_duration_min"] = (
        (df["closed_at"] - df["created_at"]).dt.total_seconds() / 60
    )

    # ── JOIN: investigation details ───────────────────────────────────────
    # Bring investigation fields onto the alert row for convenient analytics.
    # We use a left join; non-investigated alerts get NaT / NaN for inv cols.
    inv_detail = typed_invs[[
        "alert_id", "investigation_id",
        "started_at", "completed_at",
        "notes_length", "outcome",
        "investigation_dur_min",
    ]].rename(columns={
        "started_at":            "investigation_started",
        "completed_at":          "investigation_completed",
        "notes_length":          "investigation_notes_len",
        "outcome":               "investigation_outcome",
    })

    df = df.merge(inv_detail, on="alert_id", how="left")

    # ── DERIVE: investigation_lag_min ─────────────────────────────────────
    # Time from alert creation to investigation start.
    # Only meaningful for investigated alerts.
    df["investigation_lag_min"] = (
        (df["investigation_started"] - df["created_at"]).dt.total_seconds() / 60
    )

    return df


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def normalize_all(raw: "RawData") -> NormalizedData:  # type: ignore[name-defined]
    """
    Normalize all five tables and return a NormalizedData container.

    The enriched alerts DataFrame is the central object.
    All downstream analytics use it directly.
    """
    typed_orgs  = normalize_organizations(raw.organizations)
    typed_invs  = normalize_investigations(raw.investigations)
    typed_escs  = normalize_escalations(raw.escalations)
    typed_cases = normalize_cases(raw.cases)
    enriched_alerts = enrich_alerts(raw.alerts, typed_invs, typed_escs)

    return NormalizedData(
        organizations=typed_orgs,
        alerts=enriched_alerts,
        investigations=typed_invs,
        escalations=typed_escs,
        cases=typed_cases,
    )
