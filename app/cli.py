from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List

from biosignal.notebook_builder import NotebookRecorder
from .agent import Agent
from .ingestion import load_dataset
from .profiling import profile_dataset
from .semantic_sketch import build_semantic_sketch


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the dataset-agnostic agent CLI")
    parser.add_argument("--dataset", required=True, help="Path to dataset file or directory")
    parser.add_argument("--prompt", action="append", help="Prompt to run (repeatable)")
    parser.add_argument("--out", default="output/session", help="Output directory")
    parser.add_argument("--allow-clarify", action="store_true", help="Allow clarification questions")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    dataset_path = Path(args.dataset)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    con, tables = load_dataset(dataset_path)
    table_names = [t.name for t in tables]

    profiles = profile_dataset(con, table_names)
    table_row_counts = {name: profile.row_count for name, profile in profiles.items()}
    sketch = build_semantic_sketch(profiles)

    recorder = NotebookRecorder(path=out_dir / "session.ipynb", title="Agent Session")

    prompts: List[str] = args.prompt or ["Give me an overview of the data."]

    agent = Agent(
        con=con,
        table_row_counts=table_row_counts,
        sketch=sketch,
        recorder=recorder,
        out_dir=out_dir,
        allow_clarify=args.allow_clarify,
    )

    results = []
    for idx, prompt in enumerate(prompts, start=1):
        result = agent.run(prompt, idx)
        results.append(
            {
                "prompt": result.prompt,
                "intent": result.intent.type,
                "confidence": result.intent.confidence,
                "sql": result.sql,
                "description": result.description,
                "table": str(result.table_path),
                "plots": [str(p) for p in result.plot_paths],
                "notes": result.notes,
                "clarification": result.clarification,
            }
        )

    summary = {
        "dataset": str(dataset_path),
        "tables": table_names,
        "results": results,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
