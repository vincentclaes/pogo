from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import duckdb
import pandas as pd

from notebook_builder import NotebookRecorder
from .intent import infer_intent, Intent
from .sql_generator import generate_sql, QueryPlan
from .viz import generate_plots


@dataclass
class StepResult:
    prompt: str
    intent: Intent
    sql: str
    description: str
    table_path: Path
    plot_paths: List[Path]
    notes: List[str]
    clarification: Optional[str] = None


def _df_preview(df: pd.DataFrame, limit: int = 10) -> List[dict]:
    return df.head(limit).to_dict(orient="records")


def _basic_insights(df: pd.DataFrame) -> List[str]:
    insights: List[str] = []
    if df.empty:
        return ["No rows returned."]

    numeric = df.select_dtypes(include="number")
    if not numeric.empty:
        desc = numeric.describe().to_dict()
        for col, stats in desc.items():
            if "mean" in stats:
                insights.append(f"{col} mean: {stats['mean']:.2f}")
    return insights


class Agent:
    def __init__(
        self,
        con: duckdb.DuckDBPyConnection,
        table_row_counts: Dict[str, int],
        sketch,
        recorder: NotebookRecorder,
        out_dir: Path,
        allow_clarify: bool = False,
    ) -> None:
        self.con = con
        self.table_row_counts = table_row_counts
        self.sketch = sketch
        self.recorder = recorder
        self.out_dir = out_dir
        self.allow_clarify = allow_clarify
        self.table_dir = out_dir / "tables"
        self.plot_dir = out_dir / "plots"
        self.table_dir.mkdir(parents=True, exist_ok=True)
        self.plot_dir.mkdir(parents=True, exist_ok=True)
        self.plot_counter = 1

    def run(self, prompt: str, step_index: int) -> StepResult:
        intent = infer_intent(prompt, self.sketch)
        clarification = None

        if intent.confidence < 0.7 and self.allow_clarify:
            clarification = "Which column should I group by or compare?"
            self.recorder.append_clarification(clarification)

        plan: QueryPlan = generate_sql(intent, self.sketch, self.table_row_counts)
        df = self.con.execute(plan.sql).df()

        table_path = self.table_dir / f"table_{step_index}.csv"
        df.to_csv(table_path, index=False)

        plots = generate_plots(df, self.plot_dir, start_index=self.plot_counter)
        self.plot_counter += len(plots)
        plot_paths = [p.path for p in plots]

        notes = _basic_insights(df)

        self.recorder.append_intent(prompt, intent.type, intent.confidence)
        if clarification:
            self.recorder.append_clarification(clarification)
        self.recorder.append_sql(plan.sql, description=plan.description)
        self.recorder.append_result_preview(_df_preview(df))
        if plot_paths:
            for plot in plots:
                self.recorder.append_visualization(
                    code=f"# Saved chart: {plot.path.name}",
                    description=f"Chart type: {plot.chart_type}",
                )
        if notes:
            self.recorder.append_note("\n".join(notes))

        return StepResult(
            prompt=prompt,
            intent=intent,
            sql=plan.sql,
            description=plan.description,
            table_path=table_path,
            plot_paths=plot_paths,
            notes=notes,
            clarification=clarification,
        )
