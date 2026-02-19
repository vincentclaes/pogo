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

## LLM Mode (Claude Opus 4.6)
Set your Anthropic credentials and run with `--mode llm`:
```bash
export ANTHROPIC_API_KEY=...
biosignal --mode llm --model eu.anthropic.claude-opus-4-6-v1 \
  --dataset tests/fixtures/airway \
  --prompt "What are the top upregulated genes after dex treatment?" \
  --out output/session
```

If you use AWS Bedrock, ensure your AWS credentials are configured and keep the default model name.
Set `AWS_REGION` or `AWS_DEFAULT_REGION` as needed for Bedrock access.
## CLI Guide
Basic usage:
```bash
biosignal --dataset <file-or-folder> --prompt "<question>" --out <output-dir>
```

Interactive usage (asks for intent if no prompt provided):
```bash
biosignal --dataset <file-or-folder> --out <output-dir>
```

Multiple prompts (run sequentially):
```bash
biosignal \
  --dataset tests/fixtures/airway \
  --prompt "What are the top upregulated genes after dex treatment?" \
  --prompt "Compare average expression between treated and control samples." \
  --prompt "How many samples are treated vs control?" \
  --prompt "Show counts for gene GENE_0001 across samples." \
  --prompt "Give me an overview of the data." \
  --out output/session
```

Outputs written to `<output-dir>` (names derived from notebook title):
- `<title>.ipynb` (sequential notebook)
- `<title>.executed.ipynb` (papermill-executed notebook)
- `<title>.md` (nbconvert markdown export)
- `summary.json` (intent, SQL, notes)
- `tables/table_*.csv`
- `plots/plot_*.png` (if matplotlib is available)

Note: each run creates a new timestamped output folder based on `--out`.
The notebook embeds plots directly (no need to re-run cells to see images).

## Tests
```bash
pytest tests/test_e2e_airway.py
```
