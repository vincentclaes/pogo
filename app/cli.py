from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import papermill as pm
import questionary
from loguru import logger

from biosignal.notebook_builder import NotebookRecorder

from .ingestion import load_dataset
from .llm_agent import DEFAULT_MODEL, AgentDeps, build_llm_agent, run_llm_loop
from .profiling import profile_dataset
from .semantic_sketch import build_semantic_sketch


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="biosignal: dataset-agnostic BI agent",
        epilog=(
            "Examples:\n"
            "  biosignal --dataset data.csv --prompt \"Give me an overview\" --out output/session\n"
            "  biosignal --dataset tests/fixtures/airway \\\n"
            "    --prompt \"Compare treated vs control\" \\\n"
            "    --prompt \"Show counts for gene GENE_0001\" \\\n"
            "    --out output/session\n"
            "\n"
            "Outputs (written to a new timestamped folder based on --out):\n"
            "  <out>/session.ipynb (sequential notebook)\n"
            "  <out>/summary.json (intent, SQL, notes)\n"
            "  <out>/tables/table_*.csv\n"
            "  <out>/plots/plot_*.png (if matplotlib is available)\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--dataset", required=True, help="Path to dataset file or directory")
    parser.add_argument("--prompt", action="append", help="Prompt to run (repeatable)")
    parser.add_argument("--out", default="output/session", help="Output directory")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="LLM model name")
    return parser.parse_args()


def _new_run_dir(base: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return base.with_name(f"{base.name}_{stamp}")


def main() -> None:
    args = _parse_args()
    logger.remove()
    logger.add(lambda msg: print(msg, end=""), level="INFO")
    dataset_path = Path(args.dataset)
    base_out = Path(args.out)
    out_dir = _new_run_dir(base_out)
    out_dir.mkdir(parents=True, exist_ok=True)

    logger.info("biosignal: starting run\n")
    logger.info("dataset: {}\n", dataset_path)
    logger.info("output: {}\n", out_dir)

    con, tables = load_dataset(dataset_path)
    table_names = [t.name for t in tables]
    logger.info("tables: {}\n", ", ".join(table_names))

    profiles = profile_dataset(con, table_names)
    table_row_counts = {name: profile.row_count for name, profile in profiles.items()}
    sketch = build_semantic_sketch(profiles)

    initial_title = "biosignal session"
    recorder = NotebookRecorder(
        path=out_dir / "session.ipynb",
        title=initial_title,
        dataset_path=str(dataset_path.resolve()),
    )

    prompts: List[str] = args.prompt or []
    if not prompts:
        prompt = questionary.text("What do you want to do with this data?").ask()
        if prompt:
            prompts = [prompt]
    if not prompts:
        prompts = ["Give me an overview of the data."]
    logger.info("prompts: {}\n", len(prompts))

    if args.model.startswith(("eu.anthropic.", "us.anthropic.")):
        if not (os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")):
            logger.warning("AWS region not set; set AWS_REGION or AWS_DEFAULT_REGION for Bedrock.\n")
    else:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError("ANTHROPIC_API_KEY is required for Anthropic API usage.")

    llm_agent = build_llm_agent(args.model)

    results = []
    for idx, prompt in enumerate(prompts, start=1):
        logger.info("step {}: {}\n", idx, prompt)
        deps = AgentDeps(
            con=con,
            sketch=sketch,
            table_row_counts=table_row_counts,
            recorder=recorder,
            out_dir=out_dir,
        )

        decision, _history = run_llm_loop(
            llm_agent,
            deps,
            prompt,
            ask_user=lambda q: questionary.text(q).ask() or "",
        )
        results.append(
            {
                "prompt": prompt,
                "intent": "llm",
                "confidence": None,
                "sql": None,
                "description": None,
                "table": deps.outputs[-1]["table_path"] if deps.outputs else None,
                "plots": deps.outputs[-1]["plots"] if deps.outputs else [],
                "notes": ([decision.summary] if decision.summary else []),
                "clarification": decision.question,
            }
        )

    summary = {
        "dataset": str(dataset_path),
        "tables": table_names,
        "results": results,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    notebook_path = recorder.finalize_paths()
    logger.info("summary: {}\n", out_dir / "summary.json")
    logger.info("notebook: {}\n", notebook_path)

    executed_path = notebook_path.with_name(f"{notebook_path.stem}.executed.ipynb")
    logger.info("executing notebook with papermill...\n")
    pm.execute_notebook(
        input_path=str(notebook_path),
        output_path=str(executed_path),
        kernel_name="python3",
    )
    logger.info("executed notebook: {}\n", executed_path)

    markdown_path = notebook_path.with_name(f"{notebook_path.stem}.md")
    logger.info("converting notebook to markdown...\n")
    from .nbexport import export_markdown_with_images
    export_markdown_with_images(executed_path, markdown_path)
    logger.info("markdown: {}\n", markdown_path)
    logger.info("biosignal: done\n")

    # Clean up any stray notebooks from earlier runs in the same output folder.
    for candidate in out_dir.glob("*.ipynb"):
        if candidate == notebook_path or candidate.name.endswith(".executed.ipynb"):
            continue
        stem = candidate.stem
        candidate.unlink(missing_ok=True)
        candidate.with_name(f"{stem}.executed.ipynb").unlink(missing_ok=True)
        candidate.with_name(f"{stem}.md").unlink(missing_ok=True)


if __name__ == "__main__":
    main()
