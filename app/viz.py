from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

import pandas as pd


@dataclass
class PlotSpec:
    path: Path
    chart_type: str


def _try_import_matplotlib():
    try:
        import matplotlib  # type: ignore
        matplotlib.use("Agg", force=True)
        import matplotlib.pyplot as plt  # type: ignore
        return plt
    except Exception:
        return None


def _pick_columns(df: pd.DataFrame) -> tuple[list[str], list[str]]:
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    categorical_cols = [c for c in df.columns if c not in numeric_cols]
    return numeric_cols, categorical_cols


def generate_plots(
    df: pd.DataFrame,
    out_dir: Path,
    start_index: int = 1,
    max_plots: int = 2,
) -> List[PlotSpec]:
    plt = _try_import_matplotlib()
    if plt is None or df.empty:
        return []

    out_dir.mkdir(parents=True, exist_ok=True)

    numeric_cols, categorical_cols = _pick_columns(df)
    plots: List[PlotSpec] = []
    index = start_index

    if numeric_cols and categorical_cols and len(plots) < max_plots:
        x = categorical_cols[0]
        y = numeric_cols[0]
        fig = df.plot(kind="bar", x=x, y=y, legend=False).get_figure()
        path = out_dir / f"plot_{index}.png"
        fig.tight_layout()
        fig.savefig(path)
        plt.close(fig)
        plots.append(PlotSpec(path=path, chart_type="bar"))
        index += 1

    if len(numeric_cols) >= 2 and len(plots) < max_plots:
        x, y = numeric_cols[:2]
        fig = df.plot(kind="scatter", x=x, y=y).get_figure()
        path = out_dir / f"plot_{index}.png"
        fig.tight_layout()
        fig.savefig(path)
        plt.close(fig)
        plots.append(PlotSpec(path=path, chart_type="scatter"))
        index += 1

    if len(numeric_cols) == 1 and len(plots) < max_plots:
        y = numeric_cols[0]
        fig = df.plot(kind="hist", y=y).get_figure()
        path = out_dir / f"plot_{index}.png"
        fig.tight_layout()
        fig.savefig(path)
        plt.close(fig)
        plots.append(PlotSpec(path=path, chart_type="hist"))

    return plots
