from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

import duckdb
import pandas as pd

SUPPORTED_EXTENSIONS = {".csv", ".tsv", ".xlsx", ".parquet"}


@dataclass
class TableInfo:
    name: str
    source: str
    columns: List[str]


def _sanitize_table_name(name: str) -> str:
    name = name.lower()
    name = re.sub(r"[^a-z0-9_]+", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return name or "data"


def _iter_files(path: Path) -> List[Path]:
    if path.is_file():
        return [path]
    if not path.exists():
        raise FileNotFoundError(str(path))
    files = [p for p in path.iterdir() if p.suffix.lower() in SUPPORTED_EXTENSIONS]
    return sorted(files)


def _load_file(con: duckdb.DuckDBPyConnection, file_path: Path, table_name: str) -> TableInfo:
    ext = file_path.suffix.lower()
    if ext in {".csv", ".tsv"}:
        delim = "\t" if ext == ".tsv" else ","
        con.execute(
            f"create or replace table {table_name} as select * from read_csv_auto(?, delim='{delim}')",
            [str(file_path)],
        )
    elif ext == ".parquet":
        con.execute(
            f"create or replace table {table_name} as select * from read_parquet(?)",
            [str(file_path)],
        )
    elif ext == ".xlsx":
        df = pd.read_excel(file_path)
        con.register(f"{table_name}_df", df)
        con.execute(
            f"create or replace table {table_name} as select * from {table_name}_df"
        )
    else:
        raise ValueError(f"Unsupported file type: {file_path}")

    cols = [
        row[1] for row in con.execute(f"pragma table_info('{table_name}')").fetchall()
    ]
    return TableInfo(name=table_name, source=str(file_path), columns=cols)


def load_dataset(path: Path) -> Tuple[duckdb.DuckDBPyConnection, List[TableInfo]]:
    con = duckdb.connect(database=":memory:")
    files = _iter_files(path)
    if not files:
        raise ValueError(f"No supported files found in {path}")

    tables: List[TableInfo] = []
    for idx, file_path in enumerate(files):
        base = _sanitize_table_name(file_path.stem)
        table_name = f"{base}_{idx}" if idx > 0 else base
        tables.append(_load_file(con, file_path, table_name))

    return con, tables
