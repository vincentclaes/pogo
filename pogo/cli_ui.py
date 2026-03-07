from __future__ import annotations

import json
import os
import sys
from contextlib import nullcontext
from pathlib import Path
from typing import Iterable, Optional

from questionary import Style
from rich.console import Console
from rich.theme import Theme


def _use_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    return sys.stdout.isatty()


THEME = Theme(
    {
        "title": "bold magenta",
        "label": "bold cyan",
        "muted": "dim",
        "success": "bold green",
        "warn": "bold yellow",
        "error": "bold red",
    }
)

console = Console(
    theme=THEME,
    force_terminal=_use_color(),
    color_system="auto" if _use_color() else None,
    highlight=False,
    soft_wrap=True,
)

# Avoid prompt_toolkit cursor position warnings in limited terminals.
os.environ.setdefault("PROMPT_TOOLKIT_NO_CPR", "1")

_quiet = False
_json_mode = False


def configure_output(*, quiet: bool = False, json_mode: bool = False) -> None:
    global _quiet, _json_mode
    _quiet = quiet
    _json_mode = json_mode


def emit_event(event_type: str, **payload: object) -> None:
    if not _json_mode:
        return
    event = {"type": event_type, **payload}
    print(json.dumps(event, ensure_ascii=True), flush=True)


def status(message: str):
    if _quiet or _json_mode:
        return nullcontext()
    return console.status(message, spinner="dots")

QUESTIONARY_STYLE = Style(
    [
        ("qmark", "fg:#00b3b3 bold"),
        ("question", "bold"),
        ("answer", "fg:#00ff87"),
        ("pointer", "fg:#00b3b3 bold"),
        ("highlighted", "fg:#00b3b3 bold"),
        ("selected", "fg:#00b3b3"),
        ("separator", "fg:#666666"),
        ("instruction", "fg:#666666"),
        ("text", ""),
    ]
)


def banner() -> None:
    if _quiet or _json_mode:
        return
    console.print("pogo", style="title", markup=False)
    console.print(
        "Dataset-agnostic generative data analysis for non-technical users",
        style="muted",
        markup=False,
    )


def section(title: str) -> None:
    if _quiet or _json_mode:
        return
    console.print(f"\n[{title}]", style="label", markup=False)


def kv(label: str, value: str) -> None:
    if _quiet or _json_mode:
        return
    console.print(f"{label}: {value}", style="muted", markup=False)


def list_items(title: str, items: Iterable[str]) -> None:
    if _quiet or _json_mode:
        return
    console.print(f"{title}: {', '.join(items)}", style="muted", markup=False)


def question(index: int, prompt: str) -> None:
    if _quiet or _json_mode:
        return
    console.print(f"Question {index}: {prompt}", style="label", markup=False)


def clarify(prompt: str) -> None:
    if _quiet or _json_mode:
        return
    console.print(f"Clarify: {prompt}", style="warn", markup=False)


def answer(summary: Optional[str]) -> None:
    if summary:
        if _quiet or _json_mode:
            return
        console.print(f"Answer: {summary}", style="success", markup=False)


def result_summary(row_count: Optional[int], plot_count: int, table_path: Optional[str]) -> None:
    if _quiet or _json_mode:
        return
    parts = []
    if row_count is not None:
        parts.append(f"rows={row_count}")
    parts.append(f"plots={plot_count}")
    if table_path:
        parts.append(f"table={table_path}")
    console.print(f"Result: {', '.join(parts)}", style="muted", markup=False)


def warn(message: str) -> None:
    if _quiet or _json_mode:
        return
    console.print(message, style="warn", markup=False)


def output_paths(out_dir: Path, notebook: Path, executed: Path, markdown: Path, summary: Path) -> None:
    if _quiet or _json_mode:
        return
    console.print("\nOutputs", style="label", markup=False)
    console.print(f"Run dir: {out_dir}", style="muted", markup=False)
    console.print(f"Notebook: {notebook}", style="muted", markup=False)
    console.print(f"Executed: {executed}", style="muted", markup=False)
    console.print(f"Markdown: {markdown}", style="muted", markup=False)
    console.print(f"Summary: {summary}", style="muted", markup=False)
