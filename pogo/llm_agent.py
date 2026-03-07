from __future__ import annotations

import os
import threading
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, List, Optional, Protocol, Tuple, cast

import duckdb
import pandas as pd
from loguru import logger
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.bedrock import BedrockConverseModel
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.bedrock import BedrockProvider

from pogo.notebook_builder import NotebookRecorder

from .semantic_sketch import SemanticSketch
from .viz import generate_plots

DEFAULT_MODEL = "eu.anthropic.claude-opus-4-6-v1"
SUPPORTED_PROVIDERS = {"anthropic", "bedrock", "openai"}


@dataclass
class AgentDeps:
    con: duckdb.DuckDBPyConnection
    sketch: SemanticSketch
    table_row_counts: Dict[str, int]
    recorder: NotebookRecorder
    out_dir: Path
    con_lock: threading.Lock = field(default_factory=threading.Lock)
    plot_counter: int = 1
    table_counter: int = 1
    outputs: List[Dict[str, object]] = field(default_factory=list)
    story_written: bool = False
    header_written: bool = False


class AgentDecision(BaseModel):
    action: str  # ask | finish
    question: Optional[str] = None
    summary: Optional[str] = None


def split_model_name(model_name: str) -> tuple[str, str]:
    if ":" in model_name:
        provider, raw_name = model_name.split(":", 1)
        provider = provider.strip().lower()
        raw_name = raw_name.strip()
        if not provider or not raw_name:
            raise ValueError(f"Invalid model name '{model_name}'.")
        if provider not in SUPPORTED_PROVIDERS:
            raise ValueError(f"Unsupported model provider '{provider}'.")
        return provider, raw_name
    if model_name.startswith(("eu.anthropic.", "us.anthropic.")):
        return "bedrock", model_name
    return "anthropic", model_name


def _build_model(model_name: str) -> AnthropicModel | BedrockConverseModel | OpenAIModel:
    provider, resolved_name = split_model_name(model_name)
    if provider == "bedrock":
        region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")
        bedrock_provider = BedrockProvider(region_name=region)
        return BedrockConverseModel(resolved_name, provider=bedrock_provider)
    if provider == "openai":
        return OpenAIModel(resolved_name)
    return AnthropicModel(resolved_name)


def _df_preview(df: pd.DataFrame, limit: int = 10) -> List[dict]:
    return df.head(limit).to_dict(orient="records")


def _table_path(out_dir: Path, step_index: int) -> Path:
    table_dir = out_dir / "tables"
    table_dir.mkdir(parents=True, exist_ok=True)
    return table_dir / f"table_{step_index}.csv"


class _HasDeps(Protocol):
    deps: AgentDeps


def _record_sql_step(
    ctx: _HasDeps,
    sql: str,
    df: pd.DataFrame,
    reasoning_title: Optional[str] = None,
    reasoning: Optional[str] = None,
    include_plots: bool = True,
    viz_title: Optional[str] = None,
    viz_caption: Optional[str] = None,
) -> List[Path]:
    deps = ctx.deps
    deps.recorder.append_sql(sql, description=reasoning, title=reasoning_title)

    if not include_plots:
        return []

    plots = generate_plots(df, deps.out_dir / "plots", start_index=deps.plot_counter)
    deps.plot_counter += len(plots)
    default_title = "Result Visualization"
    default_caption = "This chart summarizes the query result so we can quickly spot patterns and differences."
    for plot in plots:
        caption = viz_caption or default_caption
        if viz_title:
            title = f"{viz_title} ({plot.chart_type})" if len(plots) > 1 else viz_title
        else:
            title = f"{default_title} ({plot.chart_type})" if len(plots) > 1 else default_title
        deps.recorder.append_image(
            image_path=str(plot.path),
            title=title,
            caption=caption,
        )

    return [p.path for p in plots]


def build_llm_agent(model_name: str = DEFAULT_MODEL) -> Agent[AgentDeps, AgentDecision]:
    system_prompt = (
        "You are a data analyst agent for pogo.\n"
        "Your job: answer the user's intent by exploring the dataset and producing\n"
        "useful tables and charts. Use tools to inspect schema and run SQL.\n"
        "Ask a clarifying question only if you cannot confidently map the request to columns.\n"
        "If the user's intent is vague, provide a concise overview and suggest 2-3 concrete next questions.\n"
        "When you have produced results, respond with action='finish' and a short summary.\n"
        "Use probe_sql for quick checks that should NOT appear in the notebook.\n"
        "Use run_sql for steps that SHOULD appear in the notebook.\n"
        "When calling run_sql, you must provide a short title and reasoning for the query.\n"
        "If a visualization is produced, provide a short title plus a brief 'what we see and why' caption.\n"
        "Before finishing, tell a brief story in the notebook using write_story: what you're doing, what we see, and what we learn.\n"
        "Before finishing, call write_header to set the notebook title, TL;DR, summary, prompts used (with short answers), and steps to run.\n"
    )

    model = _build_model(model_name)
    agent = Agent(model=model, deps_type=AgentDeps, output_type=AgentDecision, system_prompt=system_prompt)

    @agent.tool
    def list_tables(ctx: RunContext[AgentDeps]) -> Dict[str, int]:
        """Return available tables with row counts."""
        return ctx.deps.table_row_counts

    @agent.tool
    def get_semantic_sketch(ctx: RunContext[AgentDeps]) -> dict:
        """Return a compact semantic sketch of the dataset."""
        return {
            "tables": ctx.deps.sketch.tables,
            "category_columns": sorted(ctx.deps.sketch.category_columns),
            "numeric_columns": sorted(ctx.deps.sketch.numeric_columns),
            "datetime_columns": sorted(ctx.deps.sketch.datetime_columns),
            "id_columns": sorted(ctx.deps.sketch.id_columns),
        }

    @agent.tool
    def run_sql(
        ctx: RunContext[AgentDeps],
        sql: str,
        reasoning_title: str,
        reasoning: str,
        include_plots: bool = True,
        viz_title: Optional[str] = None,
        viz_caption: Optional[str] = None,
    ) -> Dict[str, object]:
        """Execute SQL and return a preview. Also writes notebook steps and plots."""
        logger.info("llm sql: {}", sql)
        with ctx.deps.con_lock:
            df = ctx.deps.con.execute(sql).df()
        table_path = _table_path(ctx.deps.out_dir, ctx.deps.table_counter)
        ctx.deps.table_counter += 1
        df.to_csv(table_path, index=False)
        plot_paths = _record_sql_step(
            ctx,
            sql,
            df,
            reasoning_title,
            reasoning,
            include_plots,
            viz_title,
            viz_caption,
        )
        payload = {
            "sql": sql,
            "reasoning_title": reasoning_title,
            "reasoning": reasoning,
            "viz_title": viz_title,
            "viz_caption": viz_caption,
            "rows": _df_preview(df),
            "row_count": len(df),
            "table_path": str(table_path),
            "plots": [str(p) for p in plot_paths],
        }
        ctx.deps.outputs.append(payload)
        return payload

    @agent.tool
    def probe_sql(ctx: RunContext[AgentDeps], sql: str, limit: int = 10) -> Dict[str, object]:
        """Run a quick exploratory SQL query without logging to the notebook."""
        logger.info("llm probe sql: {}", sql)
        with ctx.deps.con_lock:
            df = ctx.deps.con.execute(sql).df()
        return {
            "rows": _df_preview(df, limit=limit),
            "row_count": len(df),
        }

    @agent.tool
    def write_note(ctx: RunContext[AgentDeps], note: str) -> str:
        """Append an analyst note to the notebook."""
        ctx.deps.recorder.append_note(note)
        return "ok"

    @agent.tool
    def write_story(ctx: RunContext[AgentDeps], title: str, body: str) -> str:
        """Append a narrative section to the notebook."""
        ctx.deps.recorder.append_story(title, body)
        ctx.deps.story_written = True
        return "ok"

    @agent.tool
    def write_header(
        ctx: RunContext[AgentDeps],
        title: str,
        tldr: str,
        summary: str,
        prompts: List[Dict[str, str]],
        steps: List[str],
    ) -> str:
        """Write the notebook header (title, TL;DR, summary, prompts, steps)."""
        prompt_pairs = [(item.get("prompt", ""), item.get("answer", "")) for item in prompts]
        ctx.deps.recorder.append_header(
            tldr=tldr,
            summary=summary,
            prompts=prompt_pairs,
            steps=steps,
            title=title,
        )
        ctx.deps.header_written = True
        return "ok"

    return cast(Agent[AgentDeps, AgentDecision], agent)


def run_llm_loop(
    agent: Agent[AgentDeps, AgentDecision],
    deps: AgentDeps,
    initial_prompt: str,
    ask_user,
    history: Optional[List[str]] = None,
    max_steps: int = 6,
) -> Tuple[AgentDecision, List[str]]:
    conversation: List[str] = []
    clarifications: List[str] = []
    user_input = initial_prompt
    deps.recorder.append_intent(initial_prompt, "llm", None)

    for _ in range(max_steps):
        history_block = history or []
        prompt = "\n".join(history_block + conversation + [f"User: {user_input}"])
        result = agent.run_sync(prompt, deps=deps)
        decision = result.output

        if decision.action == "ask" and decision.question:
            conversation.append(f"Assistant: {decision.question}")
            clarifications.append(f"Assistant: {decision.question}")
            user_input = ask_user(decision.question)
            conversation.append(f"User: {user_input}")
            clarifications.append(f"User: {user_input}")
            continue

        if decision.action == "finish" and not deps.header_written:
            conversation.append("Assistant: Please provide the notebook header using write_header.")
            user_input = (
                "Please call write_header with a title, TL;DR, summary, prompts used with short answers, "
                "and steps to run."
            )
            continue

        if decision.action == "finish" and not deps.outputs:
            primary = max(deps.table_row_counts, key=lambda key: deps.table_row_counts[key])
            sql = f'SELECT * FROM "{primary}" LIMIT 20'
            df = deps.con.execute(sql).df()
            table_path = _table_path(deps.out_dir, deps.table_counter)
            deps.table_counter += 1
            df.to_csv(table_path, index=False)
            plot_paths = _record_sql_step(
                ctx=SimpleNamespace(deps=deps),
                sql=sql,
                df=df,
                reasoning_title="Dataset Overview",
                reasoning=(
                    "You asked for guidance, so I started with a quick preview of the primary table "
                    "to understand the columns and shape of the data."
                ),
                include_plots=True,
                viz_title="Quick Preview",
                viz_caption="A fast visual scan of the preview helps spot obvious patterns or outliers.",
            )
            deps.outputs.append(
                {
                    "sql": sql,
                    "reasoning_title": "Dataset Overview",
                    "reasoning": (
                        "You asked for guidance, so I started with a quick preview of the primary table "
                        "to understand the columns and shape of the data."
                    ),
                    "viz_title": "Quick Preview",
                    "viz_caption": "A fast visual scan of the preview helps spot obvious patterns or outliers.",
                    "rows": _df_preview(df),
                    "row_count": len(df),
                    "table_path": str(table_path),
                    "plots": [str(p) for p in plot_paths],
                }
            )
        return decision, clarifications

    if not deps.story_written:
        deps.recorder.append_story(
            "Summary",
            "We ran a focused query to answer the question, reviewed the result table, and generated a chart to highlight the main pattern. Review the outputs above for the key signal.",
        )
    if not deps.header_written:
        deps.recorder.append_header(
            title="pogo session",
            tldr="Summary not provided by the model.",
            summary="No header was generated by the model.",
            prompts=[("Prompt", "No short answer provided.")],
            steps=["Run pogo with your dataset and prompt."],
        )
    return AgentDecision(action="finish", summary="Reached max steps."), clarifications
