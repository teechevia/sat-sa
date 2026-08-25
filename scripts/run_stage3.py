#!/usr/bin/env python3
"""
SAT-SA Stage 3 Pipeline Runner
==============================
Runs Stage 3 end-to-end:
    1. Load raw CSV evidence (data_loader.py)
    2. Validate raw data (validator.py)
    3. Normalize data & derive evidence status (normalizer.py)
    4. Compute organization & leave-one-out peer metrics (analytics.py)
    5. Output machine-readable analytics_report.json (data/analytics_report.json)
"""

from __future__ import annotations

import json
from pathlib import Path

from app.data_loader import load_all
from app.validator import validate_all
from app.normalizer import normalize_all
from app.analytics import compute_all_org_metrics, compute_peer_baselines, build_analytics_report

ROOT = Path(__file__).parent.parent
OUTPUT_JSON = ROOT / "data" / "analytics_report.json"


def run_stage3():
    print("=" * 80)
    print("SAT-SA STAGE 3 PIPELINE EXECUTION")
    print("=" * 80)

    # 1. Load
    print("\n--- Step 1: Loading Raw Data ---")
    raw = load_all(verbose=True)

    # 2. Validate
    print("\n--- Step 2: Validating Data ---")
    dq_report = validate_all(raw)
    print(f"Total records checked: {dq_report.total_records_checked:,}")
    print(f"Data quality issues found: {dq_report.issue_count}")
    if dq_report.has_issues:
        for issue in dq_report.issues:
            print(f"  [DQ ISSUE] Table: {issue.table}, Record: {issue.record_id}, Field: {issue.field} -> {issue.issue}")

    # 3. Normalize & Derive Evidence
    print("\n--- Step 3: Normalizing & Deriving Evidence Status ---")
    norm = normalize_all(raw)
    n_alerts = len(norm.alerts)
    n_inv = int(norm.alerts["investigated"].sum())
    n_esc = int(norm.alerts["escalated"].sum())
    n_cases_linked = int(norm.alerts["has_case"].sum())

    print(f"Total normalized alerts: {n_alerts:,}")
    print(f"  Evidence-derived investigated alerts: {n_inv:,} ({n_inv/n_alerts:.1%})")
    print(f"  Evidence-derived escalated alerts:    {n_esc:,} ({n_esc/n_alerts:.1%})")
    print(f"  Alerts linked to a case:              {n_cases_linked:,} ({n_cases_linked/n_alerts:.1%})")

    # 4. Metrics & Peer Baselines
    print("\n--- Step 4: Computing Metrics & Leave-One-Out Peer Baselines ---")
    all_metrics = compute_all_org_metrics(norm)
    peer_baselines = compute_peer_baselines(all_metrics)

    # Print summary per org
    hdr = f"{'Org':<10} {'Size':<7} {'Alerts':>7} {'Assets':>7} {'A/Asset':>8} {'CritInvR':>9} {'PeerCritInvR':>12} {'EscR':>7}"
    print("\n" + hdr)
    print("-" * 80)
    for m in all_metrics:
        oid = m["organization_id"]
        pb = peer_baselines[oid]["baseline"]
        p_cinv = pb.get("critical_investigation_rate_median", 0.0)
        print(f"  {oid:<10} {m['peer_group']:<7} {m['total_alerts']:>7,} {m['active_asset_count']:>7} "
              f"{m['alerts_per_active_asset']:>8.2f} {m['critical_investigation_rate']:>9.1%} "
              f"{p_cinv:>12.1%} {m['escalation_rate']:>7.1%}")

    # 5. Build Report & Save
    report = build_analytics_report(norm, dq_report, all_metrics, peer_baselines)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("\n" + "=" * 80)
    print(f"SUCCESS: Machine-readable analytics report written to: {OUTPUT_JSON}")
    print("=" * 80)

    return report


if __name__ == "__main__":
    run_stage3()
