from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import papermill as pm
import questionary

from pogo.notebook_builder import NotebookRecorder
from pogo.session import (
    build_dataset_fingerprint,
    build_session_payload,
    fingerprints_match,
    load_session_payload,
    semantic_sketch_from_payload,
    table_row_counts_from_payload,
    write_session_payload,
)

from .cli_ui import (
    QUESTIONARY_STYLE,
    answer,
    banner,
    clarify,
    configure_output,
    emit_event,
    kv,
    list_items,
    output_paths,
    question,
    result_summary,
    section,
    status,
    warn,
)
from .ingestion import load_dataset
from .llm_agent import DEFAULT_MODEL, AgentDeps, build_llm_agent, run_llm_loop
from .profiling import profile_dataset
from .semantic_sketch import build_semantic_sketch


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="pogo: dataset-agnostic BI agent",
        epilog=(
            "Examples:\n"
            "  pogo --dataset data.csv --prompt \"Give me an overview\" --out output\n"
            "  pogo --dataset tests/fixtures/airway \\\n"
            "    --prompt \"Compare treated vs control\" \\\n"
            "    --prompt \"Show counts for gene GENE_0001\" \\\n"
            "    --out output\n"
            "\n"
            "Outputs (written to a new timestamped folder based on --out):\n"
            "  If --out output: output/session_<timestamp>/...\n"
            "  Otherwise: <out>_<timestamp>/...\n"
            "  session_<timestamp>.ipynb (sequential notebook)\n"
            "  session_<timestamp>.executed.ipynb\n"
            "  session_<timestamp>.md\n"
            "  session.json\n"
            "  summary.json\n"
            "  tables/table_*.csv\n"
            "  plots/plot_*.png (if matplotlib is available)\n"
            "\n"
            "Automation:\n"
            "  --json emits JSONL events to stdout\n"
            "  --quiet suppresses non-error output\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--dataset", required=True, help="Path to dataset file or directory")
    parser.add_argument("--prompt", action="append", help="Prompt to run (repeatable)")
    parser.add_argument("--out", default="output", help="Output directory")
    parser.add_argument("--resume", help="Resume from an existing output directory")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="LLM model name")
    parser.add_argument("--quiet", action="store_true", help="Suppress non-error output")
    parser.add_argument("--json", action="store_true", help="Emit JSONL events to stdout")
    return parser.parse_args()


def _new_run_dir(base: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    if base.exists() and base.is_dir():
        run_dir = base / f"session_{stamp}"
    elif base.name == "output" and not base.suffix:
        run_dir = base / f"session_{stamp}"
    else:
        run_dir = base.with_name(f"{base.name}_{stamp}")
    run_dir.parent.mkdir(parents=True, exist_ok=True)
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def _run_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _next_index(out_dir: Path, prefix: str, suffix: str) -> int:
    if not out_dir.exists():
        return 1
    max_index = 0
    for candidate in out_dir.glob(f"{prefix}_*{suffix}"):
        stem = candidate.stem
        try:
            idx = int(stem.split("_")[-1])
        except ValueError:
            continue
        max_index = max(max_index, idx)
    return max_index + 1


def main() -> None:
    args = _parse_args()
    if args.quiet and args.json:
        raise RuntimeError("Choose either --quiet or --json (not both).")
    configure_output(quiet=args.quiet, json_mode=args.json)
    dataset_path = Path(args.dataset)
    base_out = Path(args.out)
    session_payload = None
    if args.resume:
        out_dir = Path(args.resume)
        if not out_dir.exists():
            raise FileNotFoundError(f"Resume directory not found: {out_dir}")
        session_path = out_dir / "session.json"
        if not session_path.exists():
            raise FileNotFoundError(f"session.json not found in {out_dir}")
        session_payload = load_session_payload(session_path)
    else:
        out_dir = _new_run_dir(base_out)
        session_path = out_dir / "session.json"

    banner()
    section("Run")
    kv("Dataset", str(dataset_path))
    kv("Output", str(out_dir.resolve()))
    emit_event(
        "run_start",
        dataset=str(dataset_path),
        output=str(out_dir.resolve()),
        model=args.model,
        resumed=bool(args.resume),
    )

    with status("Loading dataset…"):
        con, tables = load_dataset(dataset_path)
    table_names = [t.name for t in tables]
    list_items("Tables", table_names)
    emit_event("tables", tables=table_names)

    if session_payload:
        existing_runs = list(session_payload.get("runs", []))
        stored_files = session_payload.get("dataset", {}).get("files", [])
        current_files = build_dataset_fingerprint(tables)
        if stored_files and not fingerprints_match(stored_files, current_files):
            raise RuntimeError(
                "Resume requested but dataset fingerprint does not match the stored session."
            )
        table_row_counts = table_row_counts_from_payload(session_payload)
        sketch = semantic_sketch_from_payload(session_payload)
        if not table_row_counts or not sketch.tables:
            with status("Profiling dataset…"):
                profiles = profile_dataset(con, table_names)
            table_row_counts = {name: profile.row_count for name, profile in profiles.items()}
            sketch = build_semantic_sketch(profiles)
            session_payload = build_session_payload(dataset_path, tables, profiles, sketch, args.model)
            session_payload["runs"] = existing_runs
        else:
            session_payload["metadata"]["model"] = args.model
            session_payload["metadata"]["output_dir"] = str(out_dir.resolve())
            session_payload["dataset"]["path"] = str(dataset_path.resolve())
            session_payload["dataset"]["files"] = current_files
            session_payload["metadata"]["resumed_at"] = datetime.now(timezone.utc).isoformat()
            session_payload.setdefault("artifacts", {})
        write_session_payload(session_path, session_payload)
    else:
        with status("Profiling dataset…"):
            profiles = profile_dataset(con, table_names)
        table_row_counts = {name: profile.row_count for name, profile in profiles.items()}
        sketch = build_semantic_sketch(profiles)
        session_payload = build_session_payload(dataset_path, tables, profiles, sketch, args.model)
        session_payload["metadata"]["output_dir"] = str(out_dir.resolve())
        write_session_payload(session_path, session_payload)

    initial_title = "pogo session"
    notebook_path = session_payload.get("artifacts", {}).get("notebook") if session_payload else None
    notebook_file = out_dir / f"session_{_run_stamp()}.ipynb"
    if notebook_path:
        previous = Path(notebook_path)
        if not previous.is_absolute():
            previous = out_dir / previous
        if previous.exists():
            shutil.copy(previous, notebook_file)
    recorder = NotebookRecorder(
        path=notebook_file,
        title=initial_title,
        dataset_path=str(dataset_path.resolve()),
    )
    session_payload.setdefault("artifacts", {})
    session_payload["artifacts"].setdefault("notebooks", [])
    session_payload["artifacts"]["notebooks"].append(str(notebook_file))

    prompts: List[str] = args.prompt or []
    allow_chat = sys.stdin.isatty()
    if not prompts:
        if allow_chat:
            if args.json:
                raise RuntimeError("--json requires explicit --prompt arguments.")
            prompt = questionary.text(
                "What do you want to do with this data?",
                style=QUESTIONARY_STYLE,
            ).ask()
            if prompt:
                prompts = [prompt]
        if not prompts:
            prompts = ["Give me an overview of the data."]

    if args.model.startswith(("eu.anthropic.", "us.anthropic.")):
        if not (os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")):
            emit_event(
                "warning",
                message="AWS region not set; set AWS_REGION or AWS_DEFAULT_REGION for Bedrock.",
            )
            warn("AWS region not set; set AWS_REGION or AWS_DEFAULT_REGION for Bedrock.")
    else:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError("ANTHROPIC_API_KEY is required for Anthropic API usage.")

    llm_agent = build_llm_agent(args.model)

    results = list(session_payload.get("runs", [])) if session_payload else []
    session_payload.setdefault("steps", [])
    plot_counter = _next_index(out_dir / "plots", "plot", ".png")
    table_counter = _next_index(out_dir / "tables", "table", ".csv")
    step_counter = len(session_payload.get("steps", [])) + 1
    step_index = len(results) + 1

    def run_prompt_step(prompt: str, idx: int) -> None:
        nonlocal plot_counter, table_counter, step_counter, results, session_payload
        question(idx, prompt)
        emit_event("step_start", index=idx, prompt=prompt)
        deps = AgentDeps(
            con=con,
            sketch=sketch,
            table_row_counts=table_row_counts,
            recorder=recorder,
            out_dir=out_dir,
            plot_counter=plot_counter,
            table_counter=table_counter,
            step_counter=step_counter,
        )
        def _persist_step(event: dict) -> None:
            if event.get("type") != "step":
                return
            payload = event.get("step")
            if not isinstance(payload, dict):
                return
            session_payload.setdefault("steps", [])
            session_payload["steps"].append(payload)
            write_session_payload(session_path, session_payload)

        deps.emit_event = _persist_step

        prior_conversation = list(session_payload.get("conversation", []))

        def _ask_user(q: str) -> str:
            emit_event("clarify_question", index=idx, question=q)
            if args.json:
                raise RuntimeError("Clarification required but --json is non-interactive.")
            clarify(q)
            response = questionary.text(q, style=QUESTIONARY_STYLE).ask() or ""
            emit_event("clarify_response", index=idx, response=response)
            return response

        with status(f"Working on question {idx}…"):
            decision, clarifications = run_llm_loop(
                llm_agent,
                deps,
                prompt,
                ask_user=_ask_user,
                history=prior_conversation,
            )
        answer(decision.summary)
        emit_event("step_answer", index=idx, summary=decision.summary)
        if deps.outputs:
            last = deps.outputs[-1]
            row_count_raw = last.get("row_count")
            row_count = row_count_raw if isinstance(row_count_raw, int) else None
            plot_paths_raw = last.get("plots", [])
            plot_paths = plot_paths_raw if isinstance(plot_paths_raw, list) else []
            table_path_raw = last.get("table_path")
            table_path = table_path_raw if isinstance(table_path_raw, str) else None
            result_summary(row_count, len(plot_paths), table_path)
            emit_event(
                "step_result",
                index=idx,
                row_count=row_count,
                table_path=table_path,
                plots=plot_paths,
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
        session_payload.setdefault("conversation", [])
        session_payload["conversation"].append(f"User: {prompt}")
        session_payload["conversation"].extend(clarifications)
        if decision.summary:
            session_payload["conversation"].append(f"Assistant: {decision.summary}")
        plot_counter = deps.plot_counter
        table_counter = deps.table_counter
        step_counter = deps.step_counter
        session_payload["runs"] = results
        write_session_payload(session_path, session_payload)

    for prompt in prompts:
        run_prompt_step(prompt, step_index)
        step_index += 1

    if allow_chat and not args.json:
        while True:
            follow_up = questionary.text(
                "Anything else you'd like to explore? (blank to finish)",
                style=QUESTIONARY_STYLE,
            ).ask()
            if not follow_up:
                break
            run_prompt_step(follow_up, step_index)
            step_index += 1

    summary = {
        "dataset": str(dataset_path),
        "tables": table_names,
        "results": results,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    notebook_path = recorder.finalize_paths()

    session_payload["artifacts"]["summary"] = str(out_dir / "summary.json")
    session_payload["artifacts"]["notebook"] = str(notebook_path)
    notebooks = session_payload["artifacts"].get("notebooks", [])
    if notebooks:
        notebooks[-1] = str(notebook_path)
        session_payload["artifacts"]["notebooks"] = notebooks
    write_session_payload(session_path, session_payload)

    executed_path = notebook_path.with_name(f"{notebook_path.stem}.executed.ipynb")
    with status("Executing notebook with papermill…"):
        pm.execute_notebook(
            input_path=str(notebook_path),
            output_path=str(executed_path),
            kernel_name="python3",
        )
    session_payload["artifacts"]["executed_notebook"] = str(executed_path)
    write_session_payload(session_path, session_payload)

    markdown_path = notebook_path.with_name(f"{notebook_path.stem}.md")
    with status("Converting notebook to markdown…"):
        from .nbexport import export_markdown_with_images
        export_markdown_with_images(executed_path, markdown_path)
    output_paths(
        out_dir=out_dir.resolve(),
        notebook=notebook_path,
        executed=executed_path,
        markdown=markdown_path,
        summary=out_dir / "summary.json",
    )
    emit_event(
        "outputs",
        run_dir=str(out_dir.resolve()),
        notebook=str(notebook_path),
        executed=str(executed_path),
        markdown=str(markdown_path),
        summary=str(out_dir / "summary.json"),
    )
    session_payload["artifacts"]["markdown"] = str(markdown_path)
    write_session_payload(session_path, session_payload)

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
