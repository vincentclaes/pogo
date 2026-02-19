from __future__ import annotations

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

            tables[table_name][col_name] = {
                "dtype": col_profile.dtype,
                "role": role,
                "distinct": col_profile.distinct,
                "non_null": col_profile.non_null,
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
