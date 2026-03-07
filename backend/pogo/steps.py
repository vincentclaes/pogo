from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional


def _json_safe(value: Any) -> Any:
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


def _sanitize_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [{key: _json_safe(value) for key, value in row.items()} for row in rows]


@dataclass
class Step:
    index: int
    title: Optional[str] = None
    reasoning: Optional[str] = None
    sql: Optional[str] = None
    preview_rows: List[Dict[str, Any]] = field(default_factory=list)
    row_count: Optional[int] = None
    table_path: Optional[str] = None
    plots: List[str] = field(default_factory=list)
    viz_title: Optional[str] = None
    viz_caption: Optional[str] = None
    status: str = "done"
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def to_payload(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["preview_rows"] = _sanitize_rows(payload.get("preview_rows", []))
        return payload
