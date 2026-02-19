# biosignal

Dataset-agnostic generative BI app for bioinformatics.

## What It Does (Visual)
```
User Prompt
   |
   v
Intent-First Agent
   |  (asks only if needed)
   v
Runtime Data Profiling
   |
   v
Semantic Sketch (columns, roles)
   |
   v
SQL Generation + Execution (DuckDB)
   |
   v
Results: Table + Charts + Insights
   |
   v
Notebook Export (sequential steps)
```

## Example Flow (CLI)
```
Upload/point to dataset
  -> auto schema inference
  -> user asks: "compare treated vs control"
  -> SQL runs, table + 2 plots generated
  -> session.ipynb written
```

## Quickstart
```bash
uv sync --dev
biosignal --dataset tests/fixtures/airway --prompt "Give me an overview of the data." --out output/session
```

## Tests
```bash
pytest tests/test_e2e_airway.py
```
