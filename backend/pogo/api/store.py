from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


def _base_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    override = os.environ.get("POGO_OUTPUT_DIR")
    return Path(override) if override else root / "output"


def base_output_dir() -> Path:
    return _base_dir()


def _slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    words = [w for w in value.split() if w]
    return "-".join(words[:6]) or "workbook"


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _workbook_dir(workbook_id: str) -> Path:
    return _base_dir() / workbook_id


def _workbook_path(workbook_id: str) -> Path:
    return _workbook_dir(workbook_id) / "workbook.json"


def create_workbook(name: str) -> Dict[str, Any]:
    slug = _slugify(name)
    workbook_id = f"workbook_{_stamp()}_{slug}"
    workbook_dir = _workbook_dir(workbook_id)
    workbook_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "id": workbook_id,
        "name": name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset_attached": False,
    }
    _workbook_path(workbook_id).write_text(json.dumps(payload, indent=2))
    return payload


def update_workbook(workbook_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    payload = load_workbook(workbook_id)
    payload.update(updates)
    _workbook_path(workbook_id).write_text(json.dumps(payload, indent=2))
    return payload


def load_workbook(workbook_id: str) -> Dict[str, Any]:
    path = _workbook_path(workbook_id)
    if not path.exists():
        raise FileNotFoundError(f"Workbook not found: {workbook_id}")
    return json.loads(path.read_text())


def list_workbooks() -> List[Dict[str, Any]]:
    base = _base_dir()
    if not base.exists():
        return []
    workbooks: List[Dict[str, Any]] = []
    for entry in base.iterdir():
        if not entry.is_dir():
            continue
        path = entry / "workbook.json"
        if not path.exists():
            continue
        payload = json.loads(path.read_text())
        session_path = entry / "session.json"
        if session_path.exists():
            session = json.loads(session_path.read_text())
            payload["dataset_attached"] = True
            payload["step_count"] = len(session.get("steps", []))
            payload["notebook"] = session.get("artifacts", {}).get("notebook")
        workbooks.append(payload)
    workbooks.sort(key=lambda item: item.get("created_at", ""), reverse=True)
    return workbooks


def workbook_dir(workbook_id: str) -> Path:
    path = _workbook_dir(workbook_id)
    if not path.exists():
        raise FileNotFoundError(f"Workbook not found: {workbook_id}")
    return path
