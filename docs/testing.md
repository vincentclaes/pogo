# Testing Strategy

## Goals
- Provide a programmatic end-to-end check for the agent loop.
- Validate that the system produces at least 1 table and 2 plots.
- Ensure notebook export matches the session steps.

## E2E CLI Contract (Current)
Command:
```
python -m pogo --dataset <path> --prompt "<text>" --out <dir>
```

Expected outputs (written to a new timestamped run directory based on `--out`):
- If `--out output`, then `output/session_<timestamp>/...`
- Otherwise `<dir>_<timestamp>/...`
- `summary.json`
- `session.json`
- `session_<timestamp>.ipynb`
- `session_<timestamp>.executed.ipynb`
- `session_<timestamp>.md`
- `tables/table_1.csv`
- `plots/plot_1.png`
- `plots/plot_2.png`

If plotting libraries are unavailable, the CLI should skip plot files and still write `summary.json` and the notebooks.

## Summary Schema (Current)
`summary.json` includes:
- `dataset`: dataset path
- `tables`: list of table names
- `results`: list of steps with prompt, optional SQL metadata, table path, plots, and notes

## Airway Test Harness
Prompts to run sequentially:
1. “What are the top upregulated genes after dex treatment?”
2. “Compare average expression between treated and control samples.”
3. “How many samples are treated vs control?”
4. “Show counts for gene X across samples.”
5. “Give me an overview of the data.”

Assertions:
- Each prompt produces a table preview.
- At least 2 plots are produced across the run.
- Notebook export contains all steps in order: intent, SQL, preview, chart.

## Suggested Test Implementation
- `tests/integration/test_llm_notebook.py` executes the CLI with the airway dataset.
- `tests/integration/test_resume_notebook.py` validates `--resume` appends a new notebook.
- Assert output files exist and have non-empty content.
- Validate that the executed notebook includes the expected markdown sections and SQL cells.

## Future Extensions
- Add regression tests with stored `summary.json` snapshots.
- Add schema-agnostic tests with synthetic datasets.
