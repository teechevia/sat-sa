#!/usr/bin/env python3
"""
SAT-SA Stage 4 Pipeline Runner — Detection Engine & Findings
============================================================
Runs Stage 4 end-to-end:
    1. Run Stage 3 data pipeline (load -> validate -> normalize -> analytics)
    2. Execute detection rules (rules.py)
    3. Build structured Findings with transparent priority scoring (findings.py)
    4. Save machine-readable output to data/findings.json
    5. Print comprehensive detection report & summary table
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

from app.data_loader import load_all
from app.validator import validate_all
from app.normalizer import normalize_all
from app.analytics import compute_all_org_metrics, compute_peer_baselines
from app.rules import run_all_rules
from app.findings import build_findings, get_all_findings

ROOT = Path(__file__).parent.parent
OUTPUT_FINDINGS_JSON = ROOT / "data" / "findings.json"


def run_stage4():
    print("=" * 90)
    print("SAT-SA STAGE 4 — DETECTION ENGINE & FINDINGS EXECUTION")
    print("=" * 90)

    # 1. Run Stage 3 Pipeline
    print("\n--- Step 1: Loading & Normalizing Operational Evidence ---")
    raw = load_all(verbose=False)
    dq_report = validate_all(raw)
    norm = normalize_all(raw)
    all_metrics = compute_all_org_metrics(norm)
    peer_baselines = compute_peer_baselines(all_metrics)
    print(f"Normalized {len(norm.alerts):,} alerts across {len(norm.organizations)} organizations.")

    # 2. Run Detection Rules
    print("\n--- Step 2: Running Detection Rules Engine ---")
    raw_findings = run_all_rules(norm, all_metrics, peer_baselines)
    print(f"Detection engine generated {len(raw_findings)} candidate rule triggers.")

    # 3. Build & Priority-Score Findings
    print("\n--- Step 3: Scoring & Building Structured Findings ---")
    findings = build_findings(raw_findings)
    print(f"Built {len(findings)} structured Finding objects with sequential IDs and priority scores.")

    # 4. Save to data/findings.json
    findings_data = [f.model_dump(mode="json") for f in findings]
    with open(OUTPUT_FINDINGS_JSON, "w", encoding="utf-8") as f:
        json.dump(findings_data, f, indent=2, default=str)
    print(f"Saved machine-readable findings to: {OUTPUT_FINDINGS_JSON}")

    # 5. Summary Statistics & Reporting
    priority_counts = Counter(f.priority.value for f in findings)
    rule_counts = Counter(f.rule_id for f in findings)
    type_counts = Counter(f.finding_type.value for f in findings)

    org_findings: dict[str, list] = defaultdict(list)
    for f in findings:
        org_findings[f.organization_id].append(f)

    print("\n" + "=" * 90)
    print("FINDINGS SUMMARY STATISTICS")
    print("=" * 90)
    print(f"  Total Findings Generated:  {len(findings)}")
    print(f"    HIGH Priority:           {priority_counts.get('HIGH', 0)}")
    print(f"    MEDIUM Priority:         {priority_counts.get('MEDIUM', 0)}")
    print(f"    LOW Priority:            {priority_counts.get('LOW', 0)}")

    print("\n  Findings by Rule:")
    for rule_id, count in sorted(rule_counts.items()):
        print(f"    {rule_id:<10}: {count} finding(s)")

    print("\n  Findings by Type:")
    for ftype, count in sorted(type_counts.items()):
        print(f"    {ftype:<25}: {count} finding(s)")

    print("\n" + "=" * 90)
    print("FINDINGS BY ORGANIZATION")
    print("=" * 90)
    hdr = f"{'Org ID':<10} {'Finding ID':<12} {'Rule ID':<10} {'Priority':<10} {'Score':<7} Title"
    print(hdr)
    print("-" * 90)

    for org_id in sorted(norm.organizations["organization_id"]):
        org_f_list = org_findings.get(org_id, [])
        if not org_f_list:
            print(f"  {org_id:<10}  (No findings detected -- Healthy operational profile)")
        else:
            for f in org_f_list:
                print(f"  {f.organization_id:<10} {f.finding_id:<12} {f.rule_id:<10} {f.priority.value:<10} {f.priority_score:<7} {f.title}")

    # Detailed ground-truth check verification
    print("\n" + "=" * 90)
    print("INJECTED SCENARIOS GROUND-TRUTH VERIFICATION")
    print("=" * 90)

    target_checks = [
        ("ORG-002", "EXECUTION_GAP", "RULE-1"),
        ("ORG-003", "SUSPICIOUS_FAST_CLOSURE", "RULE-2"),
        ("ORG-004", "REPEATED_INCIDENTS", "RULE-3"),
        ("ORG-012", "PEER_DEVIATION", "RULE-4"),
    ]

    all_injected_found = True
    for org_id, expected_type, expected_rule in target_checks:
        matches = [
            f for f in findings
            if f.organization_id == org_id and f.rule_id == expected_rule
        ]
        if matches:
            m = matches[0]
            print(f"  [PASS] {org_id} -> Detected {m.finding_id} ({m.rule_id} / {m.finding_type.value}) - Priority: {m.priority.value} (Score: {m.priority_score})")
        else:
            print(f"  [FAIL] {org_id} -> Expected {expected_rule} ({expected_type}) but none triggered!")
            all_injected_found = False

    print("\n" + "=" * 90)
    print(f"OVERALL STAGE 4 DETECTION STATUS: {'ALL INJECTED PATTERNS DETECTED ✓' if all_injected_found else 'SOME PATTERNS MISSING ✗'}")
    print("=" * 90)

    return findings


if __name__ == "__main__":
    run_stage4()
