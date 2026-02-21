# Introduction (Machine)

## Purpose
Provide a dataset-agnostic, intent-first, and explainable BI agent for biology workflows that converts natural language intents into SQL + visualization + notebook output.

## Operating Constraints
- No hardcoded schema assumptions.
- Learn dataset structure at runtime via profiling.
- Ask at most one clarification question when intent confidence is low.
- Always show SQL, a table preview, and a chart suggestion.
- Log every step into a sequential notebook export.

## Supported Inputs (MVP)
- CSV
- TSV
- Excel (.xlsx)
- Parquet

## Runtime Profiling Output
For each table and column, generate a compact profile:
- Inferred type, missingness, distinct counts
- Numeric ranges + quantiles
- Top categorical values
- Candidate ID columns (e.g., unique or *_id)
- Candidate datetime columns

## Intent-First Loop
1. Ask: "What do you want to do with this data?"
2. Infer intent from user text + semantic sketch.
3. If confidence is low, ask one clarifying question.
4. Generate SQL and execute in DuckDB.
5. Return SQL, table preview, chart suggestion, and a short explanation.
6. Confirm with the user and refine on request.

## Required LLM Outputs (Per Step)
- Short title for the step.
- Reasoning for why the query is run.
- "What we see and why" caption for charts.

## Output Artifacts
Each run writes to a timestamped output directory based on `--out`:
- `<title>.ipynb` (sequential notebook)
- `<title>.executed.ipynb` (executed notebook)
- `<title>.md` (markdown export)
- `summary.json`
- `tables/table_*.csv`
- `plots/plot_*.png`

## CLI Contract (Current)
```
pogo --dataset <file-or-folder> --prompt "<question>" --out <output-dir>
```

## Success Criteria (Airway Test Harness)
- The agent answers without schema hints.
- Clarifications are only asked when intent is ambiguous.
- Notebook export includes intent, SQL, results, and visualization for each step.
