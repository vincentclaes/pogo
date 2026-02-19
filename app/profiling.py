from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Any

import duckdb

NUMERIC_TYPES = {
    "TINYINT",
    "SMALLINT",
    "INTEGER",
    "BIGINT",
    "HUGEINT",
    "UTINYINT",
    "USMALLINT",
    "UINTEGER",
    "UBIGINT",
    "FLOAT",
    "DOUBLE",
    "REAL",
    "DECIMAL",
}

DATETIME_TYPES = {"DATE", "TIMESTAMP", "TIMESTAMPTZ", "TIME"}


@dataclass
class ColumnProfile:
    name: str
    dtype: str
    non_null: int
    distinct: int
    min: float | None = None
    max: float | None = None
    top_values: List[Any] | None = None


@dataclass
class TableProfile:
    name: str
    row_count: int
    columns: Dict[str, ColumnProfile]


def _quote(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _column_stats(con: duckdb.DuckDBPyConnection, table: str, col: str, dtype: str) -> ColumnProfile:
    qcol = _quote(col)
    row_count = con.execute(f"select count(*) from {table}").fetchone()[0]
    non_null = con.execute(f"select count({qcol}) from {table}").fetchone()[0]
    distinct = con.execute(f"select count(distinct {qcol}) from {table}").fetchone()[0]

    profile = ColumnProfile(name=col, dtype=dtype, non_null=non_null, distinct=distinct)

    upper = dtype.upper()
    if upper in NUMERIC_TYPES:
        row = con.execute(f"select min({qcol}), max({qcol}) from {table}").fetchone()
        profile.min = row[0]
        profile.max = row[1]
    elif upper in DATETIME_TYPES:
        row = con.execute(f"select min({qcol}), max({qcol}) from {table}").fetchone()
        profile.min = row[0]
        profile.max = row[1]
    else:
        top_rows = con.execute(
            f"select {qcol}, count(*) as n from {table} group by {qcol} order by n desc limit 5"
        ).fetchall()
        profile.top_values = [r[0] for r in top_rows]

    return profile


def profile_dataset(con: duckdb.DuckDBPyConnection, tables: List[str]) -> Dict[str, TableProfile]:
    profiles: Dict[str, TableProfile] = {}
    for table in tables:
        row_count = con.execute(f"select count(*) from {table}").fetchone()[0]
        columns_info = con.execute(f"pragma table_info('{table}')").fetchall()
        columns: Dict[str, ColumnProfile] = {}
        for _, name, dtype, *_ in columns_info:
            columns[name] = _column_stats(con, table, name, dtype)
        profiles[table] = TableProfile(name=table, row_count=row_count, columns=columns)
    return profiles
