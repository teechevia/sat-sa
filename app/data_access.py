"""
SAT-SA Data Access Layer for API
================================
Provides fast in-memory access to pre-computed Stage 3 analytics report,
Stage 4 findings report, and normalized evidence models.

Does NOT execute expensive data generation on every HTTP request.
Reads the already-generated Stage 3 & 4 JSON outputs.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.config import DATA_DIR
from app.data_loader import load_all
from app.normalizer import normalize_all, NormalizedData
from app.models import Finding, FindingType, Priority

log = logging.getLogger(__name__)

ANALYTICS_JSON_PATH = DATA_DIR / "analytics_report.json"
FINDINGS_JSON_PATH  = DATA_DIR / "findings.json"

# In-memory global data caches
_ANALYTICS_CACHE: dict[str, Any] | None = None
_FINDINGS_CACHE: list[Finding] | None = None
_NORMALIZED_CACHE: NormalizedData | None = None


def load_api_data(force_reload: bool = False) -> None:
    """
    Loads pre-computed JSON reports and normalized models into memory.
    Raises RuntimeError if required generated files are missing.
    """
    global _ANALYTICS_CACHE, _FINDINGS_CACHE, _NORMALIZED_CACHE

    if not force_reload and _ANALYTICS_CACHE is not None and _FINDINGS_CACHE is not None:
        return

    if not ANALYTICS_JSON_PATH.exists() or not FINDINGS_JSON_PATH.exists():
        raise RuntimeError(
            "Required SAT-SA data files missing. Please run Stage 3 & 4 scripts:\n"
            "  python scripts/generate_data.py\n"
            "  python -m scripts.run_stage3\n"
            "  python -m scripts.run_stage4"
        )

    # 1. Load analytics report
    with open(ANALYTICS_JSON_PATH, "r", encoding="utf-8") as f:
        _ANALYTICS_CACHE = json.load(f)

    # 2. Load findings report
    with open(FINDINGS_JSON_PATH, "r", encoding="utf-8") as f:
        raw_f_list = json.load(f)
        _FINDINGS_CACHE = [Finding.model_validate(f_dict) for f_dict in raw_f_list]

    # 3. Load normalized data for evidence traceability lookup
    raw = load_all(verbose=False)
    _NORMALIZED_CACHE = normalize_all(raw)

    log.info("API data cache initialized successfully (%d findings, %d orgs).",
             len(_FINDINGS_CACHE), len(_ANALYTICS_CACHE.get("organizations", [])))


def get_analytics_data() -> dict[str, Any]:
    load_api_data()
    assert _ANALYTICS_CACHE is not None
    return _ANALYTICS_CACHE


def get_findings_data() -> list[Finding]:
    load_api_data()
    assert _FINDINGS_CACHE is not None
    return _FINDINGS_CACHE


def get_normalized_data() -> NormalizedData:
    load_api_data()
    assert _NORMALIZED_CACHE is not None
    return _NORMALIZED_CACHE
