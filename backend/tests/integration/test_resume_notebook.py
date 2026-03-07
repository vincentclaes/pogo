from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.integration
def test_resume_appends_notebook(tmp_path: Path) -> None:
    if not os.environ.get("POGO_INTEGRATION"):
        pytest.skip("Set POGO_INTEGRATION=1 to run the real-model integration test.")

    repo_root = Path(__file__).resolve().parents[2]
    env_file = repo_root / ".env"
    dataset = repo_root / "tests" / "fixtures" / "airway"
    out_base = tmp_path / "session"
    model = os.environ.get("POGO_MODEL", "eu.anthropic.claude-opus-4-6-v1")
    prompt1 = "How many samples are treated vs control?"
    prompt2 = "Give me an overview of the data."

    env = os.environ.copy()
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            env.setdefault(key.strip(), value.strip())
    env["PYTHONPATH"] = str(repo_root)

    cmd = [
        sys.executable,
        "-m",
        "pogo",
        "--model",
        model,
        "--dataset",
        str(dataset),
        "--prompt",
        prompt1,
        "--out",
        str(out_base),
    ]
    result = subprocess.run(cmd, cwd=repo_root, env=env, text=True, capture_output=True)
    assert result.returncode == 0, f"CLI failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"

    sessions = sorted(tmp_path.glob("session_*"))
    assert sessions, "No session folder created."
    session_dir = sessions[-1]

    notebooks = sorted(
        [p for p in session_dir.glob("*.ipynb") if not p.name.endswith(".executed.ipynb")]
    )
    assert notebooks, "No notebook created on first run."
    base_notebook = notebooks[-1]
    base_cells = json.loads(base_notebook.read_text()).get("cells", [])
    base_count = len(base_cells)

    cmd = [
        sys.executable,
        "-m",
        "pogo",
        "--model",
        model,
        "--dataset",
        str(dataset),
        "--prompt",
        prompt2,
        "--resume",
        str(session_dir),
    ]
    result = subprocess.run(cmd, cwd=repo_root, env=env, text=True, capture_output=True)
    assert result.returncode == 0, f"CLI failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"

    notebooks_after = sorted(
        [p for p in session_dir.glob("*.ipynb") if not p.name.endswith(".executed.ipynb")]
    )
    assert len(notebooks_after) >= len(notebooks) + 1, "Resume did not create a new notebook."

    newest = max(notebooks_after, key=lambda p: p.stat().st_mtime)
    new_cells = json.loads(newest.read_text()).get("cells", [])
    assert len(new_cells) > base_count, "Resumed notebook did not append new cells."
