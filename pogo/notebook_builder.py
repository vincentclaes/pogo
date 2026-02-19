"""Utilities to build and append to a Jupyter notebook at runtime.

Design goals:
- Append sequential steps from an agent loop (intent -> SQL -> result -> viz).
- Keep output deterministic and runnable.
- Avoid hardcoding schema; only log what the agent observes and does.
"""
from __future__ import annotations

import base64
import json
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

NBFORMAT = 4
NBFORMAT_MINOR = 5
DEFAULT_KERNEL = {
    "display_name": "Python 3",
    "language": "python",
    "name": "python3",
}
DEFAULT_LANGUAGE = {
    "name": "python",
    "version": "3.12",
}


def _to_source(text: str) -> list[str]:
    if text is None:
        return ["\n"]
    lines = text.splitlines() or [""]
    return [line + "\n" for line in lines]


def _escape_md(value: Any) -> str:
    s = "" if value is None else str(value)
    return s.replace("|", "\\|")


def _markdown_table(rows: list[dict[str, Any]], max_rows: int = 10) -> str:
    if not rows:
        return "_(no rows)_"

    cols = list(rows[0].keys())
    for row in rows[1:]:
        for col in row.keys():
            if col not in cols:
                cols.append(col)

    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |"
    body_lines = []
    for row in rows[:max_rows]:
        body_lines.append(
            "| "
            + " | ".join(_escape_md(row.get(col, "")) for col in cols)
            + " |"
        )
    return "\n".join([header, sep] + body_lines)


@dataclass
class NotebookBuilder:
    title: str
    audience: Optional[str] = None
    prerequisites: Optional[list[str]] = None
    goals: Optional[list[str]] = None
    cells: list[dict[str, Any]] = field(default_factory=list)

    def add_markdown(self, text: str) -> None:
        self.cells.append(
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": _to_source(text),
                "id": uuid.uuid4().hex,
            }
        )

    def add_code(self, code: str, outputs: Optional[list[dict[str, Any]]] = None) -> None:
        self.cells.append(
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": outputs or [],
                "source": _to_source(code),
                "id": uuid.uuid4().hex,
            }
        )

    def add_title_block(self) -> None:
        self.add_markdown(f"# {self.title}")

    def set_title(self, title: str) -> None:
        if not self.cells:
            self.add_markdown(f"# {title}")
            return
        first = self.cells[0]
        if first.get("cell_type") == "markdown":
            first["source"] = _to_source(f"# {title}")
        else:
            self.cells.insert(
                0,
                {
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": _to_source(f"# {title}"),
                    "id": uuid.uuid4().hex,
                },
            )
        self.title = title

    def add_section(self, title: str, body: Optional[str] = None) -> None:
        self.add_markdown(f"## {title}")
        if body:
            self.add_markdown(body)

    def add_story(self, title: str, body: str) -> None:
        self.add_section(title)
        self.add_markdown(body)

    def add_header(
        self,
        tldr: str,
        summary: str,
        prompts: list[tuple[str, str]],
        steps: list[str],
        title: Optional[str] = None,
    ) -> None:
        if title:
            self.set_title(title)
        self._remove_existing_header()
        header_cells = []
        header_cells.append(
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": _to_source("## TL;DR\n\n" + tldr),
                "id": uuid.uuid4().hex,
            }
        )
        header_cells.append(
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": _to_source("## Summary\n\n" + summary),
                "id": uuid.uuid4().hex,
            }
        )
        prompts_lines = ["## Prompts Used"]
        for prompt, answer in prompts:
            prompts_lines.append(f"- {prompt} — {answer}")
        header_cells.append(
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": _to_source("\n".join(prompts_lines)),
                "id": uuid.uuid4().hex,
            }
        )
        steps_lines = ["## Steps to Run"]
        for idx, step in enumerate(steps, start=1):
            steps_lines.append(f"{idx}. {step}")
        header_cells.append(
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": _to_source("\n".join(steps_lines)),
                "id": uuid.uuid4().hex,
            }
        )

        insert_at = 1 if self.cells else 0
        self.cells[insert_at:insert_at] = header_cells

    def _remove_existing_header(self) -> None:
        start = None
        end = None
        for idx, cell in enumerate(self.cells):
            if cell.get("cell_type") != "markdown":
                continue
            text = "".join(cell.get("source", []))
            if text.startswith("## TL;DR"):
                start = idx
            if text.startswith("## Steps to Run") and start is not None:
                end = idx
                break
        if start is not None:
            if end is None:
                end = start
            del self.cells[start : end + 1]

    def add_setup(self, dataset_path: str) -> None:
        self.add_section("Setup")
        code = (
            "from pathlib import Path\n"
            "import duckdb\n"
            "from app.ingestion import load_dataset\n\n"
            f"DATASET_PATH = Path(r\"{dataset_path}\")\n"
            "con, tables = load_dataset(DATASET_PATH)\n"
        )
        self.add_code(code)

    def add_intent(self, user_text: str, parsed_intent: str, confidence: Optional[float] = None) -> None:
        return

    def add_clarification(self, question: str) -> None:
        self.add_section("Clarification")
        self.add_markdown(f"Question: {question}")

    def add_sql(
        self,
        sql: str,
        description: Optional[str] = None,
        result_limit: int = 5,
        title: Optional[str] = None,
    ) -> None:
        self.add_section(title or "Reasoning")
        if description:
            self.add_markdown(description)
        code = (
            "# Query used\n"
            "query = '''\n"
            + sql
            + "\n'''\n"
            + "result = con.execute(query).df()\n"
            + f"result.head({result_limit})"
        )
        self.add_code(code)

    def add_result_preview(self, rows: list[dict[str, Any]], title: str = "Result Preview") -> None:
        return

    def add_visualization(self, code: str, description: Optional[str] = None, title: Optional[str] = None) -> None:
        self.add_section(title or "Visualization")
        if description:
            self.add_markdown(description)
        self.add_code(code)

    def add_image(
        self,
        image_path: str,
        title: Optional[str] = None,
        caption: Optional[str] = None,
        embed: bool = True,
    ) -> None:
        self.add_section(title or "Visualization")
        if caption:
            self.add_markdown(caption)

        path = Path(image_path)
        if embed and path.exists():
            data = base64.b64encode(path.read_bytes()).decode("ascii")
            outputs = [
                {
                    "output_type": "display_data",
                    "data": {"image/png": data},
                    "metadata": {},
                }
            ]
            code = (
                "from IPython.display import Image, display\n"
                f"display(Image(r\"{path}\"))\n"
            )
            self.add_code(code, outputs=outputs)
            return

        code = (
            "from IPython.display import Image, display\n"
            f"display(Image(\"{image_path}\"))"
        )
        self.add_code(code)

    def add_note(self, text: str) -> None:
        self.add_section("Notes")
        self.add_markdown(text)

    def to_notebook(self) -> dict[str, Any]:
        for cell in self.cells:
            if "id" not in cell:
                cell["id"] = uuid.uuid4().hex
        return {
            "cells": self.cells,
            "metadata": {
                "kernelspec": DEFAULT_KERNEL,
                "language_info": DEFAULT_LANGUAGE,
            },
            "nbformat": NBFORMAT,
            "nbformat_minor": NBFORMAT_MINOR,
        }

    def write(self, path: Path) -> None:
        payload = self.to_notebook()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2))

    @classmethod
    def load(cls, path: Path) -> "NotebookBuilder":
        data = json.loads(path.read_text())
        title = "Notebook"
        builder = cls(title=title)
        builder.cells = data.get("cells", [])
        return builder


@dataclass
class NotebookRecorder:
    path: Path
    title: str
    dataset_path: Optional[str] = None
    builder: NotebookBuilder = field(init=False)

    def __post_init__(self) -> None:
        if self.path.exists():
            self.builder = NotebookBuilder.load(self.path)
        else:
            self.builder = NotebookBuilder(title=self.title)
            self.builder.add_title_block()
            if self.dataset_path:
                self.builder.add_setup(self.dataset_path)

    def append_intent(self, user_text: str, parsed_intent: str, confidence: Optional[float] = None) -> None:
        self.builder.add_intent(user_text, parsed_intent, confidence)
        self.builder.write(self.path)

    def append_clarification(self, question: str) -> None:
        self.builder.add_clarification(question)
        self.builder.write(self.path)

    def append_sql(
        self,
        sql: str,
        description: Optional[str] = None,
        result_limit: int = 5,
        title: Optional[str] = None,
    ) -> None:
        self.builder.add_sql(sql, description=description, result_limit=result_limit, title=title)
        self.builder.write(self.path)

    def append_result_preview(self, rows: list[dict[str, Any]], title: str = "Result Preview") -> None:
        return

    def append_visualization(self, code: str, description: Optional[str] = None, title: Optional[str] = None) -> None:
        self.builder.add_visualization(code, description=description, title=title)
        self.builder.write(self.path)

    def append_image(
        self,
        image_path: str,
        title: Optional[str] = None,
        caption: Optional[str] = None,
        embed: bool = True,
    ) -> None:
        self.builder.add_image(image_path, title=title, caption=caption, embed=embed)
        self.builder.write(self.path)

    def append_story(self, title: str, body: str) -> None:
        self.builder.add_story(title, body)
        self.builder.write(self.path)

    def append_header(
        self,
        tldr: str,
        summary: str,
        prompts: list[tuple[str, str]],
        steps: list[str],
        title: Optional[str] = None,
    ) -> None:
        self.builder.add_header(tldr, summary, prompts, steps, title=title)
        self.builder.write(self.path)

    def finalize_paths(self) -> Path:
        slug = _slugify(self.builder.title or self.title)
        if not slug:
            slug = "session"
        new_path = self.path.with_name(f"{slug}.ipynb")
        if new_path != self.path and self.path.exists():
            self.path.rename(new_path)
            self.path = new_path
        return self.path

    def append_note(self, text: str) -> None:
        self.builder.add_note(text)
        self.builder.write(self.path)


def _slugify(value: str) -> str:
    value = value.strip().lower()
    # Treat any non-alphanumeric as a separator to ensure hyphenated words.
    value = re.sub(r"[^a-z0-9]+", " ", value)
    words = [w for w in value.split() if w]
    words = words[:6]
    slug = "-".join(words)
    max_len = 48
    if len(slug) > max_len:
        slug = slug[:max_len].rstrip("-")
    return slug
