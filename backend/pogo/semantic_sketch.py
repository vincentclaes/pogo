from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Set

from .profiling import DATETIME_TYPES, NUMERIC_TYPES, TableProfile


@dataclass
class SemanticSketch:
    tables: Dict[str, Dict[str, dict]]
    category_columns: Set[str]
    numeric_columns: Set[str]
    datetime_columns: Set[str]
    id_columns: Set[str]
    column_to_tables: Dict[str, List[str]]


def _humanize(name: str) -> str:
    parts = re.split(r"[_\s]+", name.strip())
    parts = [p for p in parts if p]
    return " ".join(parts) if parts else name


def _describe_column(
    name: str,
    profile: TableProfile,
    col_profile,
    role: str,
) -> str:
    label = _humanize(name)
    base = f"Text field for {label}."
    if name.lower().endswith("_id") or (
        col_profile.non_null > 0 and col_profile.distinct == col_profile.non_null
    ):
        base = f"Unique identifier for {label}."
    elif role == "numeric":
        base = f"Numeric measure of {label}."
    elif role == "datetime":
        base = f"Date or time for {label}."
    elif role == "category":
        base = f"Categorical label for {label}."

    extras = []
    missing = max(0, profile.row_count - col_profile.non_null)
    if missing:
        extras.append(f"{missing} missing")
    if role in {"numeric", "datetime"} and col_profile.min is not None and col_profile.max is not None:
        extras.append(f"range {col_profile.min} to {col_profile.max}")
    if role in {"category", "text"} and col_profile.top_values:
        top = [str(v) for v in col_profile.top_values if v is not None][:3]
        if top:
            extras.append("common values: " + ", ".join(top))

    if extras:
        return base + " " + "; ".join(extras) + "."
    return base


def build_semantic_sketch(profiles: Dict[str, TableProfile]) -> SemanticSketch:
    tables: Dict[str, Dict[str, dict]] = {}
    category_columns: Set[str] = set()
    numeric_columns: Set[str] = set()
    datetime_columns: Set[str] = set()
    id_columns: Set[str] = set()
    column_to_tables: Dict[str, List[str]] = {}

    for table_name, profile in profiles.items():
        tables[table_name] = {}
        for col_name, col_profile in profile.columns.items():
            dtype = col_profile.dtype.upper()
            role = "text"
            if dtype in NUMERIC_TYPES:
                role = "numeric"
                numeric_columns.add(col_name)
            elif dtype in DATETIME_TYPES:
                role = "datetime"
                datetime_columns.add(col_name)
            else:
                # low cardinality => category
                if col_profile.non_null > 0 and col_profile.distinct <= max(10, int(col_profile.non_null * 0.1)):
                    role = "category"
                    category_columns.add(col_name)

            if col_name.lower().endswith("_id") or col_profile.distinct == col_profile.non_null:
                id_columns.add(col_name)

            description = _describe_column(col_name, profile, col_profile, role)
            tables[table_name][col_name] = {
                "dtype": col_profile.dtype,
                "role": role,
                "distinct": col_profile.distinct,
                "non_null": col_profile.non_null,
                "description": description,
            }
            column_to_tables.setdefault(col_name, []).append(table_name)

    return SemanticSketch(
        tables=tables,
        category_columns=category_columns,
        numeric_columns=numeric_columns,
        datetime_columns=datetime_columns,
        id_columns=id_columns,
        column_to_tables=column_to_tables,
    )
