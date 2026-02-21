from __future__ import annotations

import hashlib
import json
import platform
from dataclasses import asdict
from datetime import date, datetime, timezone
from importlib import metadata
from itertools import combinations
from pathlib import Path
from typing import Dict, List

import duckdb

from .ingestion import TableInfo
from .profiling import TableProfile
from .semantic_sketch import SemanticSketch


def _file_fingerprint(path: Path) -> dict:
    stat = path.stat()
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return {
        "path": str(path),
        "size": stat.st_size,
        "mtime": stat.st_mtime,
        "sha256": hasher.hexdigest(),
    }


def build_dataset_fingerprint(tables: List[TableInfo]) -> List[dict]:
    fingerprints = []
    for table in tables:
        source = Path(table.source)
        if source.exists():
            fingerprints.append(_file_fingerprint(source))
    return fingerprints


def fingerprints_match(stored: List[dict], current: List[dict]) -> bool:
    if not stored or not current:
        return False
    stored_map = {item.get("path"): item.get("sha256") for item in stored}
    current_map = {item.get("path"): item.get("sha256") for item in current}
    if stored_map.keys() == current_map.keys():
        return all(stored_map[path] == sha for path, sha in current_map.items())
    stored_shas = sorted([sha for sha in stored_map.values() if sha])
    current_shas = sorted([sha for sha in current_map.values() if sha])
    return stored_shas == current_shas


def _json_safe(value):
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            return value
    return value


def _serialize_profiles(
    profiles: Dict[str, TableProfile],
    sketch: SemanticSketch,
) -> dict:
    payload: dict = {}
    for table_name, profile in profiles.items():
        columns = {}
        for col_name, col_profile in profile.columns.items():
            description = sketch.tables.get(table_name, {}).get(col_name, {}).get("description")
            columns[col_name] = {
                "dtype": col_profile.dtype,
                "non_null": col_profile.non_null,
                "distinct": col_profile.distinct,
                "missing": max(0, profile.row_count - col_profile.non_null),
                "min": _json_safe(col_profile.min),
                "max": _json_safe(col_profile.max),
                "top_values": [_json_safe(v) for v in (col_profile.top_values or [])],
                "description": description,
            }
        payload[table_name] = {
            "row_count": profile.row_count,
            "columns": columns,
        }
    return payload


def _serialize_semantic_sketch(sketch: SemanticSketch) -> dict:
    return {
        "tables": sketch.tables,
        "category_columns": sorted(sketch.category_columns),
        "numeric_columns": sorted(sketch.numeric_columns),
        "datetime_columns": sorted(sketch.datetime_columns),
        "id_columns": sorted(sketch.id_columns),
        "column_to_tables": sketch.column_to_tables,
    }


def semantic_sketch_from_payload(payload: dict) -> SemanticSketch:
    data = payload.get("semantic_sketch", {})
    return SemanticSketch(
        tables=data.get("tables", {}),
        category_columns=set(data.get("category_columns", [])),
        numeric_columns=set(data.get("numeric_columns", [])),
        datetime_columns=set(data.get("datetime_columns", [])),
        id_columns=set(data.get("id_columns", [])),
        column_to_tables=data.get("column_to_tables", {}),
    )


def table_row_counts_from_payload(payload: dict) -> Dict[str, int]:
    profiles = payload.get("profiles", {})
    return {table: data.get("row_count", 0) for table, data in profiles.items()}


def _build_semantic_layer(
    profiles: Dict[str, TableProfile],
    sketch: SemanticSketch,
) -> dict:
    entities = []
    for table_name, profile in profiles.items():
        pk_candidates = []
        for col_name, col_profile in profile.columns.items():
            if col_name in sketch.id_columns or col_profile.distinct == profile.row_count:
                pk_candidates.append(col_name)
        entities.append(
            {
                "table": table_name,
                "primary_keys": pk_candidates,
            }
        )

    dimensions = [
        {"column": col, "tables": sketch.column_to_tables.get(col, [])}
        for col in sorted(sketch.category_columns)
    ]
    measures = [
        {"column": col, "tables": sketch.column_to_tables.get(col, []), "default_agg": "avg"}
        for col in sorted(sketch.numeric_columns)
    ]
    time_columns = [
        {"column": col, "tables": sketch.column_to_tables.get(col, [])}
        for col in sorted(sketch.datetime_columns)
    ]

    joins = []
    for col, tables in sketch.column_to_tables.items():
        if len(tables) < 2:
            continue
        reason = "shared_id_column" if col in sketch.id_columns else "shared_column"
        for left, right in combinations(sorted(tables), 2):
            joins.append(
                {
                    "left_table": left,
                    "right_table": right,
                    "column": col,
                    "reason": reason,
                }
            )

    return {
        "entities": entities,
        "dimensions": dimensions,
        "measures": measures,
        "time_columns": time_columns,
        "join_candidates": joins,
    }


def _pogo_version() -> str:
    try:
        return metadata.version("pogo")
    except metadata.PackageNotFoundError:
        return "unknown"


def build_session_payload(
    dataset_path: Path,
    tables: List[TableInfo],
    profiles: Dict[str, TableProfile],
    sketch: SemanticSketch,
    model: str,
) -> dict:
    dataset = {
        "path": str(dataset_path.resolve()),
        "files": build_dataset_fingerprint(tables),
        "tables": [asdict(table) for table in tables],
    }

    payload = {
        "metadata": {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "pogo_version": _pogo_version(),
            "python_version": platform.python_version(),
            "duckdb_version": duckdb.__version__,
            "model": model,
        },
        "dataset": dataset,
        "profiles": _serialize_profiles(profiles, sketch),
        "semantic_sketch": _serialize_semantic_sketch(sketch),
        "semantic_layer": _build_semantic_layer(profiles, sketch),
        "conversation": [],
        "runs": [],
        "artifacts": {},
    }
    return payload


def write_session_payload(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2))


def load_session_payload(path: Path) -> dict:
    return json.loads(path.read_text())
