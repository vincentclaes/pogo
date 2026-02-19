# MVP Plan: Dataset-Agnostic Generative BI App

## Goal
Build a lightweight generative BI app that:
- Learns dataset structure at runtime (no hardcoded schema)
- Uses an intent-first agent loop (asks only when needed)
- Generates SQL + visualizations
- Exports every step to a Jupyter notebook

## Implementation Plan (Detailed)
### Phase 1 - Core Architecture and Interfaces
1. **Define module boundaries and data contracts**
- `ingestion`: load files into DuckDB with schema inference.
- `profiling`: compute column stats and candidate semantic roles.
- `semantic_sketch`: compact, model-friendly summary of table structure.
- `intent`: infer user intent and map to columns.
- `sql_generator`: produce safe SQL for the intent.
- `viz_selector`: choose chart type based on result shape.
- `notebook_recorder`: log every step as notebook cells.

2. **Define core data models**
- `DatasetProfile`: column stats, table stats.
- `SemanticSketch`: candidate IDs, categories, numerics, datetimes.
- `Intent`: parsed intent type, entities, confidence.
- `QueryPlan`: SQL, description, expected output schema.
- `Insight`: summary text + metrics.

3. **Define interaction contract for the agent loop**
- Input: `user_text`, `semantic_sketch`, optional `context`.
- Output: one of `{clarify, plan}`.
  - `clarify`: single question only when confidence is low.
  - `plan`: SQL + visualization + notebook steps.

### Phase 2 - Ingestion + Profiling
1. **Ingestion**
- Support CSV/TSV (`read_csv_auto`), Excel (via pandas), Parquet.
- Normalize to DuckDB tables: `data_0`, `data_1`, etc.
- Track table metadata for later joins.

2. **Profiling**
- Per column:
  - dtype, missingness, distinct count
  - numeric ranges and quantiles
  - top categorical values
- Identify candidates:
  - ID columns (unique or name suffix `_id`)
  - category columns (low cardinality)
  - datetime columns (parseable timestamps)

3. **Semantic sketch**
- Compress profile to a prompt-friendly structure:
  - `{tables: {table: {col: dtype, role}}}`
  - `key_columns`, `category_columns`, `numeric_columns`, `datetime_columns`

### Phase 3 - Intent-First Agent Loop
1. **Intent inference**
- Ask: “What do you want to do with this data?”
- Parse user text into an `Intent` object with confidence.
- If low confidence: ask a single clarifying question.

2. **SQL generation**
- Generate SQL using the semantic sketch.
- Enforce safety: only `SELECT`, no `DROP/DELETE`.
- Ensure `LIMIT` on large results.

3. **Result handling**
- Execute SQL in DuckDB.
- Create a short preview (head).
- Trigger `viz_selector` for 1–2 default charts.

4. **Notebook logging**
- Log: intent, SQL, preview table, chart code, and notes.
- Always append sequentially so the notebook is runnable.

### Phase 4 - CLI + Test Harness
1. **CLI runner**
- `python -m pogo.cli run --dataset <path> --prompt <text> --out <dir>`
- Outputs:
  - `session.ipynb` (sequential notebook)
  - `summary.json` (intent, SQL, stats)
  - `plots/plot_1.png`, `plots/plot_2.png` (if available)

2. **E2E tests**
- Use airway dataset as a test harness.
- Run CLI with known prompts.
- Assert:
  - 1 table preview exists
  - 2 plots exist (if plotting libs available)
  - Notebook includes the same steps in order

### Phase 5 - Minimal FastAPI Scaffold
1. **Endpoints**
- `POST /upload` (CSV/TSV/Excel/Parquet)
- `POST /intent` (user text -> SQL + preview + viz)
- `GET /notebook` (download notebook)

2. **Local-first deployment**
- Simple `uvicorn` run, no VPC.

## Test Harness (Airway Dataset)
Use the airway dataset only to validate behavior. The app must remain dataset-agnostic.

Expected prompts:
- “What are the top upregulated genes after dex treatment?”
- “Compare average expression between treated and control samples.”
- “How many samples are treated vs control?”
- “Show counts for gene X across samples.”
- “Give me an overview of the data.”

Success criteria:
- No hardcoded schema.
- Minimal clarifications.
- SQL + chart generated for each prompt.
- Notebook export includes every step.

## Proposed File Layout (Planned)
- `app/ingestion.py`
- `app/profiling.py`
- `app/semantic_sketch.py`
- `app/intent.py`
- `app/sql_generator.py`
- `app/viz.py`
- `app/agent.py`
- `app/cli.py`
- `app/server.py`
- `tests/test_e2e_airway.py`
- `docs/testing.md`
