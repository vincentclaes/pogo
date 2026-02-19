from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.integration
def test_llm_generates_notebook(tmp_path: Path) -> None:
    if not os.environ.get("BIOSIGNAL_INTEGRATION"):
        pytest.skip("Set BIOSIGNAL_INTEGRATION=1 to run the real-model integration test.")

    repo_root = Path(__file__).resolve().parents[2]
    env_file = repo_root / ".env"
    dataset = repo_root / "tests" / "fixtures" / "airway"
    out_base = tmp_path / "session"
    model = os.environ.get("BIOSIGNAL_MODEL", "eu.anthropic.claude-opus-4-6-v1")
    prompt = "What are the top upregulated genes after dex treatment?"

    cmd = [
        sys.executable,
        "-m",
        "biosignal",
        "--mode",
        "llm",
        "--model",
        model,
        "--dataset",
        str(dataset),
        "--prompt",
        prompt,
        "--out",
        str(out_base),
    ]
    env = os.environ.copy()
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            env.setdefault(key.strip(), value.strip())
    env["PYTHONPATH"] = str(repo_root)
    result = subprocess.run(cmd, cwd=repo_root, env=env, text=True, capture_output=True)
    assert result.returncode == 0, f"CLI failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"

    sessions = sorted(tmp_path.glob("session_*"))
    assert sessions, "No session folder created."
    session_dir = sessions[-1]

    summary_path = session_dir / "summary.json"
    assert summary_path.exists(), "summary.json missing."

    executed = list(session_dir.glob("*.executed.ipynb"))
    assert executed, "Executed notebook missing."
    executed_path = executed[0]

    markdown_files = [p for p in session_dir.glob("*.md")]
    assert markdown_files, "Markdown export missing."
    markdown_path = markdown_files[0]

    nb = json.loads(executed_path.read_text())
    cells = nb.get("cells", [])
    assert cells, "Notebook has no cells."

    markdown_cells = [c for c in cells if c.get("cell_type") == "markdown"]
    markdown_text = "\n".join("".join(c.get("source", [])) for c in markdown_cells)
    assert markdown_text.strip().startswith("# "), "Notebook title missing."
    for section in ("## TL;DR", "## Summary", "## Prompts Used", "## Steps to Run"):
        assert section in markdown_text, f"Missing notebook section: {section}"

    code_cells = [c for c in cells if c.get("cell_type") == "code"]
    assert code_cells, "Notebook has no code cells."
    assert any(c.get("outputs") for c in code_cells), "Executed notebook has no outputs."
    assert any("query = '''" in "".join(c.get("source", [])) for c in code_cells), "SQL cell missing."

    tables_dir = session_dir / "tables"
    assert tables_dir.exists() and any(tables_dir.glob("*.csv")), "Table CSVs missing."

    md_text = markdown_path.read_text()
    if "_md_images/" in md_text:
        images_dir = session_dir / "_md_images"
        assert images_dir.exists() and any(images_dir.iterdir()), "Markdown images referenced but missing."
