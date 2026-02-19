from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def _matplotlib_available() -> bool:
    try:
        import matplotlib  # noqa: F401
        return True
    except Exception:
        return False


def test_airway_cli_end_to_end(tmp_path: Path):
    repo_root = Path(__file__).resolve().parents[1]
    dataset_dir = repo_root / "tests" / "fixtures" / "airway"
    base_out_dir = tmp_path / "airway_e2e"

    prompts = [
        "What are the top upregulated genes after dex treatment?",
        "Compare average expression between treated and control samples.",
        "How many samples are treated vs control?",
        "Show counts for gene GENE_0001 across samples.",
        "Give me an overview of the data.",
    ]

    cmd = [
        sys.executable,
        "-m",
        "app.cli",
        "--dataset",
        str(dataset_dir),
        "--out",
        str(base_out_dir),
    ]
    for prompt in prompts:
        cmd.extend(["--prompt", prompt])

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=repo_root,
        env={**os.environ, "PYTHONPATH": str(repo_root)},
    )
    assert result.returncode == 0, result.stderr

    run_dirs = sorted(
        [p for p in base_out_dir.parent.glob(f"{base_out_dir.name}_*") if p.is_dir()],
        key=lambda p: p.stat().st_mtime,
    )
    assert run_dirs, "No output directory created"
    out_dir = run_dirs[-1]

    summary_path = out_dir / "summary.json"
    ipynb_files = [p for p in out_dir.glob("*.ipynb") if not p.name.endswith(".executed.ipynb")]
    assert len(ipynb_files) == 1, "Expected a single base notebook"
    notebook_path = ipynb_files[0]
    executed_notebook = notebook_path.with_name(f"{notebook_path.stem}.executed.ipynb")
    markdown_path = notebook_path.with_name(f"{notebook_path.stem}.md")
    assert summary_path.exists(), "summary.json was not created"
    assert notebook_path.exists(), "session.ipynb was not created"
    assert executed_notebook.exists(), "session.executed.ipynb was not created"
    assert markdown_path.exists(), "session.md was not created"

    data = json.loads(summary_path.read_text())
    assert len(data.get("results", [])) == len(prompts)

    table_dir = out_dir / "tables"
    tables = list(table_dir.glob("table_*.csv"))
    assert len(tables) >= 1

    plot_dir = out_dir / "plots"
    plots = list(plot_dir.glob("plot_*.png"))
    if _matplotlib_available():
        assert len(plots) >= 2
