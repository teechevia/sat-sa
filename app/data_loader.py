"""
SAT-SA Data Loader
==================
Reads raw CSV files into pandas DataFrames.
Responsibility: file I/O only. No validation, no transformation.

Why keep dtype=str?
    Letting pandas silently coerce "False" -> NaN or "2025-01-40" -> NaT
    hides data quality problems. We read everything as strings and let
    validator.py decide what is good or bad.

Data flow:
    CSV files -> load_all() -> RawData -> validator.py
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from app.config import (
    ALERTS_FILE,
    CASES_FILE,
    ESCALATIONS_FILE,
    INVESTIGATIONS_FILE,
    ORGANIZATIONS_FILE,
)

log = logging.getLogger(__name__)


@dataclass
class TableLoadResult:
    """Summary produced after loading one CSV table."""
    table: str
    row_count: int
    columns: list[str]
    missing_by_column: dict[str, int]   # column -> count of blank / NaN cells


@dataclass
class RawData:
    """
    Container holding all five raw DataFrames.
    All cell values are str — no type coercion has been applied yet.
    """
    organizations:   pd.DataFrame
    alerts:          pd.DataFrame
    investigations:  pd.DataFrame
    escalations:     pd.DataFrame
    cases:           pd.DataFrame
    load_summaries:  list[TableLoadResult] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_one(path: Path, table: str) -> tuple[pd.DataFrame, TableLoadResult]:
    """
    Load one CSV file. All columns kept as strings.
    keep_default_na=False prevents pandas from converting 'False' -> NaN.
    """
    if not path.exists():
        raise FileNotFoundError(
            f"Data file not found: {path}\n"
            "Run:  python scripts/generate_data.py"
        )

    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    log.info("Loaded %-22s %7d rows", table, len(df))

    # Count blanks: empty string OR actual NaN (shouldn't occur with dtype=str)
    missing: dict[str, int] = {}
    for col in df.columns:
        n = int((df[col].isna() | (df[col].str.strip() == "")).sum())
        if n:
            missing[col] = n

    summary = TableLoadResult(
        table=table,
        row_count=len(df),
        columns=list(df.columns),
        missing_by_column=missing,
    )
    return df, summary


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_all(verbose: bool = True) -> RawData:
    """
    Load all five CSV files and return a RawData container.

    Raises FileNotFoundError if any required file is missing.
    Never raises on data quality issues — those are reported by validator.py.

    Args:
        verbose: If True, print a loading summary table.
    """
    table_specs = [
        (ORGANIZATIONS_FILE,  "organizations"),
        (ALERTS_FILE,         "alerts"),
        (INVESTIGATIONS_FILE, "investigations"),
        (ESCALATIONS_FILE,    "escalations"),
        (CASES_FILE,          "cases"),
    ]

    frames:    dict[str, pd.DataFrame]  = {}
    summaries: list[TableLoadResult]    = []

    for path, name in table_specs:
        df, summary = _load_one(path, name)
        frames[name] = df
        summaries.append(summary)

    if verbose:
        _print_load_report(summaries)

    return RawData(
        organizations=frames["organizations"],
        alerts=frames["alerts"],
        investigations=frames["investigations"],
        escalations=frames["escalations"],
        cases=frames["cases"],
        load_summaries=summaries,
    )


def _print_load_report(summaries: list[TableLoadResult]) -> None:
    total = sum(s.row_count for s in summaries)
    print("\n" + "=" * 62)
    print("DATA LOADING REPORT")
    print("=" * 62)
    for s in summaries:
        print(f"  {s.table:<22} {s.row_count:>8,} rows  "
              f"({len(s.columns)} columns)")
        for col, n in s.missing_by_column.items():
            print(f"      [MISSING] {col}: {n} blank cells")
    print(f"  {'TOTAL':<22} {total:>8,} rows")
    print("=" * 62)
