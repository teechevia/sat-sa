"""
SAT-SA Configuration
====================
All file paths and rule thresholds live here.

Why a dedicated config module?
    Tuning a detection threshold should never require editing rule logic.
    Change a number here → all rules respond.
    This is especially important for a student team: no hunting through
    analytics.py to find a magic number buried in a conditional.

Usage:
    from app.config import DATA_DIR, THRESHOLD_EXECUTION_GAP
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT     = Path(__file__).parent.parent          # sat-sa/
DATA_DIR = ROOT / "data"                          # sat-sa/data/

ALERTS_FILE        = DATA_DIR / "alerts.csv"
INVESTIGATIONS_FILE= DATA_DIR / "investigations.csv"
ESCALATIONS_FILE   = DATA_DIR / "escalations.csv"
CASES_FILE         = DATA_DIR / "cases.csv"
ORGANIZATIONS_FILE = DATA_DIR / "organizations.csv"

# ---------------------------------------------------------------------------
# Rule 1 — Potential Execution Gap
# ---------------------------------------------------------------------------
# If more than this fraction of critical alerts have no investigation record,
# emit an EXECUTION_GAP finding.
THRESHOLD_EXECUTION_GAP: float = 0.40  # 40%

# ---------------------------------------------------------------------------
# Rule 2 — Suspicious Fast Closure
# ---------------------------------------------------------------------------
# An alert closed in fewer than this many minutes is considered "fast".
THRESHOLD_FAST_MINUTES: int = 10

# If this fraction of critical+high alerts are both fast-closed AND have no
# investigation record, emit a SUSPICIOUS_FAST_CLOSURE finding.
THRESHOLD_FAST_CLOSURE_RATE: float = 0.20  # 20%

# ---------------------------------------------------------------------------
# Rule 3 — Repeated Incidents (Potential Remediation Weakness)
# ---------------------------------------------------------------------------
# An (asset_id, incident_type) pair that appears in at least this many
# separate case records is considered "repeated".
THRESHOLD_REPEAT_COUNT: int = 3

# ---------------------------------------------------------------------------
# Rule 4 — Peer Deviation
# ---------------------------------------------------------------------------
# A metric that deviates more than this fraction from the leave-one-out
# peer median is flagged. Default 40% = 0.40.
THRESHOLD_PEER_DEVIATION: float = 0.40

# Primary metrics used for peer comparison (normalized by active_asset_count)
PEER_COMPARISON_METRICS: list[str] = [
    "alerts_per_asset",
    "critical_alerts_per_asset",
    "critical_investigation_rate",
    "escalation_rate",
]

# ---------------------------------------------------------------------------
# Priority scoring (additive, transparent)
# ---------------------------------------------------------------------------
# These weights determine Finding.priority. See findings.py for scoring logic.
PRIORITY_THRESHOLDS = {
    "HIGH":   4,
    "MEDIUM": 2,
    "LOW":    1,
}
