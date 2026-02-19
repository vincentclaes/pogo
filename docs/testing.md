# Testing Strategy

## Goals
- Provide a programmatic end-to-end check for the agent loop.
- Validate that the system produces at least 1 table and 2 plots.
- Ensure notebook export matches the session steps.

## E2E CLI Contract (Planned)
Command:
```
python -m pogo.cli run --dataset <path> --prompt <text> --out <dir>
```

Expected outputs (written to a new timestamped folder based on `<dir>`):
- `<dir>_<timestamp>/summary.json`
- `<dir>_<timestamp>/<title>.ipynb`
- `<dir>_<timestamp>/<title>.executed.ipynb`
- `<dir>_<timestamp>/<title>.md`
- `<dir>_<timestamp>/tables/table_1.csv`
- `<dir>_<timestamp>/plots/plot_1.png`
- `<dir>_<timestamp>/plots/plot_2.png`

If plotting libraries are unavailable, the CLI should log that plots are skipped and still write `summary.json` and `session.ipynb`.

## Summary Schema (Planned)
`summary.json` should include:
- `intent`: parsed intent and confidence
- `sql`: executed SQL
- `table_preview`: first 5–10 rows
- `plots`: list of plot files and types
- `notes`: generated insights

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
- `tests/test_e2e_airway.py` executes the CLI with the airway dataset.
- Assert output files exist and have non-empty content.
- Optionally validate that `session.ipynb` includes expected cell headings.

## Future Extensions
- Add regression tests with stored `summary.json` snapshots.
- Add schema-agnostic tests with synthetic datasets.
