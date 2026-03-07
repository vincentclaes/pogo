from __future__ import annotations

import json
import shutil
import threading
from datetime import datetime, timezone
from pathlib import Path
from queue import Queue
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from pogo.api.store import (
    base_output_dir,
    create_workbook,
    list_workbooks,
    load_workbook,
    update_workbook,
    workbook_dir,
)
from pogo.ingestion import SUPPORTED_EXTENSIONS, load_dataset
from pogo.llm_agent import DEFAULT_MODEL, AgentDeps, build_llm_agent, run_llm_loop
from pogo.notebook_builder import NotebookRecorder
from pogo.profiling import profile_dataset
from pogo.semantic_sketch import build_semantic_sketch
from pogo.session import (
    build_session_payload,
    load_session_payload,
    semantic_sketch_from_payload,
    table_row_counts_from_payload,
    write_session_payload,
)

app = FastAPI(title="pogo API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/artifacts", StaticFiles(directory=base_output_dir(), html=False), name="artifacts")


class WorkbookCreate(BaseModel):
    name: str


class PromptRequest(BaseModel):
    prompt: str
    model: Optional[str] = None


class ClarificationNeeded(Exception):
    def __init__(self, question: str) -> None:
        super().__init__(question)
        self.question = question


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


def _relative_path(out_dir: Path, path: Path) -> str:
    try:
        return str(path.relative_to(out_dir))
    except ValueError:
        return str(path)


def _save_uploads(target_dir: Path, files: List[UploadFile]) -> List[Path]:
    target_dir.mkdir(parents=True, exist_ok=True)
    saved: List[Path] = []
    for upload in files:
        if not upload.filename:
            continue
        safe_name = Path(upload.filename).name
        if Path(safe_name).suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {safe_name}",
            )
        dest = target_dir / safe_name
        with dest.open("wb") as handle:
            shutil.copyfileobj(upload.file, handle)
        saved.append(dest)
    if not saved:
        raise HTTPException(status_code=400, detail="No valid dataset files uploaded.")
    return saved


@app.post("/workbooks")
def create_workbook_route(payload: WorkbookCreate) -> Dict[str, Any]:
    return create_workbook(payload.name)


@app.get("/workbooks")
def list_workbooks_route() -> List[Dict[str, Any]]:
    return list_workbooks()


@app.get("/workbooks/{workbook_id}")
def get_workbook_route(workbook_id: str) -> Dict[str, Any]:
    workbook = load_workbook(workbook_id)
    session_path = workbook_dir(workbook_id) / "session.json"
    if session_path.exists():
        session = load_session_payload(session_path)
        workbook["session"] = {
            "dataset": session.get("dataset", {}),
            "step_count": len(session.get("steps", [])),
            "notebook": session.get("artifacts", {}).get("notebook"),
        }
    return workbook


@app.post("/workbooks/{workbook_id}/dataset")
def attach_dataset_route(
    workbook_id: str,
    files: List[UploadFile] = File(...),
    model: Optional[str] = None,
) -> Dict[str, Any]:
    out_dir = workbook_dir(workbook_id)
    dataset_dir = out_dir / "dataset"
    saved_files = _save_uploads(dataset_dir, files)

    con, tables = load_dataset(dataset_dir)
    profiles = profile_dataset(con, [t.name for t in tables])
    sketch = build_semantic_sketch(profiles)
    model_name = model or DEFAULT_MODEL

    session_payload = build_session_payload(dataset_dir, tables, profiles, sketch, model_name)
    session_payload["metadata"]["output_dir"] = str(out_dir.resolve())
    session_payload.setdefault("steps", [])

    notebook_file = out_dir / f"session_{_run_stamp()}.ipynb"
    recorder = NotebookRecorder(
        path=notebook_file,
        title="pogo session",
        dataset_path=str(dataset_dir.resolve()),
    )
    recorder.builder.write(recorder.path)

    notebook_rel = _relative_path(out_dir, notebook_file)
    session_payload.setdefault("artifacts", {})
    session_payload["artifacts"]["notebook"] = notebook_rel
    session_payload["artifacts"]["notebooks"] = [notebook_rel]

    write_session_payload(out_dir / "session.json", session_payload)
    update_workbook(
        workbook_id,
        {
            "dataset_attached": True,
            "dataset_files": [str(p.name) for p in saved_files],
        },
    )
    con.close()
    return {
        "id": workbook_id,
        "dataset_files": [p.name for p in saved_files],
        "notebook": notebook_rel,
    }


def _run_prompt(
    workbook_id: str,
    prompt: str,
    model: Optional[str] = None,
    event_queue: Optional[Queue] = None,
) -> Dict[str, Any]:
    out_dir = workbook_dir(workbook_id)
    session_path = out_dir / "session.json"
    if not session_path.exists():
        raise HTTPException(status_code=400, detail="Dataset not attached.")

    session_payload = load_session_payload(session_path)
    dataset_path = Path(session_payload.get("dataset", {}).get("path", ""))
    if not dataset_path.exists():
        raise HTTPException(status_code=400, detail="Dataset path not found on server.")

    con, _tables = load_dataset(dataset_path)
    sketch = semantic_sketch_from_payload(session_payload)
    table_row_counts = table_row_counts_from_payload(session_payload)

    prior_notebook = session_payload.get("artifacts", {}).get("notebook")
    prior_path = out_dir / prior_notebook if prior_notebook else None
    notebook_file = out_dir / f"session_{_run_stamp()}.ipynb"
    if prior_path and prior_path.exists():
        shutil.copy(prior_path, notebook_file)

    recorder = NotebookRecorder(
        path=notebook_file,
        title="pogo session",
        dataset_path=str(dataset_path.resolve()),
    )
    recorder.builder.write(recorder.path)

    notebook_rel = _relative_path(out_dir, notebook_file)
    session_payload.setdefault("artifacts", {})
    session_payload["artifacts"].setdefault("notebooks", [])
    session_payload["artifacts"]["notebooks"].append(notebook_rel)
    session_payload["artifacts"]["notebook"] = notebook_rel
    session_payload["metadata"]["model"] = model or session_payload.get("metadata", {}).get("model")

    plot_counter = _next_index(out_dir / "plots", "plot", ".png")
    table_counter = _next_index(out_dir / "tables", "table", ".csv")
    step_counter = len(session_payload.get("steps", [])) + 1

    new_steps: List[Dict[str, Any]] = []

    def _persist_step(event: Dict[str, Any]) -> None:
        if event.get("type") != "step":
            return
        payload = event.get("step")
        if not isinstance(payload, dict):
            return
        session_payload.setdefault("steps", [])
        session_payload["steps"].append(payload)
        new_steps.append(payload)
        write_session_payload(session_path, session_payload)
        if event_queue is not None:
            event_queue.put({"type": "step", "step": payload})

    llm_agent = build_llm_agent(model or DEFAULT_MODEL)
    deps = AgentDeps(
        con=con,
        sketch=sketch,
        table_row_counts=table_row_counts,
        recorder=recorder,
        out_dir=out_dir,
        plot_counter=plot_counter,
        table_counter=table_counter,
        step_counter=step_counter,
        emit_event=_persist_step,
    )

    def _ask_user(question: str) -> str:
        raise ClarificationNeeded(question)

    try:
        decision, clarifications = run_llm_loop(
            llm_agent,
            deps,
            prompt,
            ask_user=_ask_user,
            history=list(session_payload.get("conversation", [])),
        )
    except ClarificationNeeded as clarifying:
        session_payload.setdefault("conversation", [])
        session_payload["conversation"].append(f"User: {prompt}")
        session_payload["conversation"].append(f"Assistant: {clarifying.question}")
        write_session_payload(session_path, session_payload)
        if event_queue is not None:
            event_queue.put({"type": "clarify", "question": clarifying.question})
        return {"action": "clarify", "question": clarifying.question}
    except Exception as exc:
        if event_queue is not None:
            event_queue.put({"type": "error", "message": str(exc)})
        raise
    finally:
        con.close()

    session_payload.setdefault("conversation", [])
    session_payload["conversation"].append(f"User: {prompt}")
    session_payload["conversation"].extend(clarifications)
    if decision.summary:
        session_payload["conversation"].append(f"Assistant: {decision.summary}")

    finalized = recorder.finalize_paths()
    notebook_rel = _relative_path(out_dir, finalized)
    if session_payload.get("artifacts", {}).get("notebooks"):
        session_payload["artifacts"]["notebooks"][-1] = notebook_rel
    session_payload["artifacts"]["notebook"] = notebook_rel

    last_step = new_steps[-1] if new_steps else None
    session_payload.setdefault("runs", [])
    session_payload["runs"].append(
        {
            "prompt": prompt,
            "intent": "llm",
            "confidence": None,
            "sql": None,
            "description": None,
            "table": last_step.get("table_path") if last_step else None,
            "plots": last_step.get("plots") if last_step else [],
            "notes": [decision.summary] if decision.summary else [],
            "clarification": decision.question,
        }
    )
    write_session_payload(session_path, session_payload)

    response = {
        "action": "finish",
        "summary": decision.summary,
        "steps": new_steps,
        "notebook": notebook_rel,
    }
    if event_queue is not None:
        event_queue.put({"type": "done", **response})
    return response


@app.post("/workbooks/{workbook_id}/prompts")
def prompt_route(workbook_id: str, payload: PromptRequest) -> Dict[str, Any]:
    return _run_prompt(workbook_id, payload.prompt, payload.model)


@app.post("/workbooks/{workbook_id}/prompts/stream")
def prompt_stream_route(workbook_id: str, payload: PromptRequest):
    queue: Queue = Queue()

    def _run() -> None:
        queue.put({"type": "start"})
        try:
            _run_prompt(workbook_id, payload.prompt, payload.model, event_queue=queue)
        except Exception as exc:
            queue.put({"type": "error", "message": str(exc)})
        finally:
            queue.put(None)

    threading.Thread(target=_run, daemon=True).start()

    def _event_stream():
        while True:
            event = queue.get()
            if event is None:
                break
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(_event_stream(), media_type="text/event-stream")


@app.get("/workbooks/{workbook_id}/steps")
def steps_route(workbook_id: str) -> List[Dict[str, Any]]:
    session_path = workbook_dir(workbook_id) / "session.json"
    if not session_path.exists():
        raise HTTPException(status_code=404, detail="Session not found")
    session_payload = load_session_payload(session_path)
    steps = session_payload.get("steps", [])
    return sorted(steps, key=lambda item: item.get("index", 0))


@app.get("/workbooks/{workbook_id}/notebook")
def notebook_route(workbook_id: str):
    session_path = workbook_dir(workbook_id) / "session.json"
    if not session_path.exists():
        raise HTTPException(status_code=404, detail="Session not found")
    session_payload = load_session_payload(session_path)
    notebook_rel = session_payload.get("artifacts", {}).get("notebook")
    if not notebook_rel:
        raise HTTPException(status_code=404, detail="Notebook not found")
    notebook_path = workbook_dir(workbook_id) / notebook_rel
    if not notebook_path.exists():
        raise HTTPException(status_code=404, detail="Notebook file missing")
    return FileResponse(notebook_path)


@app.get("/workbooks/{workbook_id}/summary")
def summary_route(workbook_id: str) -> Dict[str, Any]:
    session_path = workbook_dir(workbook_id) / "session.json"
    if not session_path.exists():
        raise HTTPException(status_code=404, detail="Session not found")
    session_payload = load_session_payload(session_path)
    return {
        "steps": len(session_payload.get("steps", [])),
        "notebook": session_payload.get("artifacts", {}).get("notebook"),
    }


@app.get("/workbooks/{workbook_id}/session")
def session_route(workbook_id: str) -> Dict[str, Any]:
    session_path = workbook_dir(workbook_id) / "session.json"
    if not session_path.exists():
        raise HTTPException(status_code=404, detail="Session not found")
    return load_session_payload(session_path)


@app.get("/health")
def health_route() -> Dict[str, str]:
    return {"status": "ok"}
