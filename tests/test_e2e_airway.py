from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


def _matplotlib_available() -> bool:
    try:
        import matplotlib  # noqa: F401
        return True
    except Exception:
        return False


def test_airway_cli_end_to_end():
    repo_root = Path(__file__).resolve().parents[1]
    dataset_dir = repo_root / "tests" / "fixtures" / "airway"
    out_dir = repo_root / "tmp" / "airway_e2e"

    if out_dir.exists():
        shutil.rmtree(out_dir)

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
        str(out_dir),
    ]
    for prompt in prompts:
        cmd.extend(["--prompt", prompt])

    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr

    summary_path = out_dir / "summary.json"
    notebook_path = out_dir / "session.ipynb"
    assert summary_path.exists(), "summary.json was not created"
    assert notebook_path.exists(), "session.ipynb was not created"

    data = json.loads(summary_path.read_text())
    assert len(data.get("results", [])) == len(prompts)

    table_dir = out_dir / "tables"
    tables = list(table_dir.glob("table_*.csv"))
    assert len(tables) >= 1

    plot_dir = out_dir / "plots"
    plots = list(plot_dir.glob("plot_*.png"))
    if _matplotlib_available():
        assert len(plots) >= 2
