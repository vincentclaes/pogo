# pogo

**Human page:** This README is the human-facing overview and usage guide.

A dataset‑agnostic generative BI app for bioinformatics. Ask a question in plain English, get a clean narrative with tables, charts, and a reproducible notebook.

**Command:**

```bash
pogo --model eu.anthropic.claude-opus-4-6-v1 \
  --dataset tests/fixtures/airway \
  --prompt "What are the top upregulated genes after dex treatment?" \
  --out output
```

**Output:**

![pogo demo](assets/pogo-demo.gif)

**What pogo does**
- Learns your dataset at runtime (no schema setup)
- Turns intent into SQL and visuals
- Writes a story‑driven notebook with explanations
- Exports both `.ipynb` and `.md`

**Why it feels different**
- It doesn’t just answer — it **walks you through what it’s doing**
- The notebook is **the product**: readable, shareable, reproducible

## Setup (Required)
```bash
ci/setup.sh
pre-commit install
```

## LLM Credentials (Required for Runs)
Anthropic API:
```bash
export ANTHROPIC_API_KEY="..."
```

Bedrock (if using a `eu.anthropic.*` or `us.anthropic.*` model):
- Configure AWS credentials (env vars or `~/.aws/credentials`).
- Set a region:
```bash
export AWS_REGION="us-east-1"
```

## Local CI (Before Commit)
```bash
ci/local_ci.sh
```

## How It Works
```
User Prompt
   |
   v
LLM Agent
   |  (asks only if needed)
   v
Runtime Profiling + Semantic Sketch
   |
   v
SQL Generation + Execution (DuckDB)
   |
   v
Tables + Charts + Story
   |
   v
Notebook + Markdown Export
```


## CLI Guide
Basic usage:
```bash
pogo --dataset <file-or-folder> --prompt "<question>" --out <output-dir>
```

Specify a model (Bedrock or Anthropic):
```bash
pogo --model eu.anthropic.claude-opus-4-6-v1 --dataset <file-or-folder> --prompt "<question>" --out <output-dir>
```

Interactive usage (asks for intent if no prompt provided):
```bash
pogo --dataset <file-or-folder> --out <output-dir>
```

Resume a prior session (continue the notebook and session log):
```bash
pogo --dataset <file-or-folder> --prompt "<question>" --resume <output-dir>
```

Machine-readable output (JSONL events):
```bash
pogo --dataset <file-or-folder> --prompt "<question>" --out <output-dir> --json
```

Quiet mode (suppress non-error output):
```bash
pogo --dataset <file-or-folder> --prompt "<question>" --out <output-dir> --quiet
```

Multiple prompts (run sequentially):
```bash
pogo \
  --dataset tests/fixtures/airway \
  --prompt "What are the top upregulated genes after dex treatment?" \
  --prompt "Compare average expression between treated and control samples." \
  --prompt "How many samples are treated vs control?" \
  --prompt "Show counts for gene GENE_0001 across samples." \
  --prompt "Give me an overview of the data." \
  --out output
```

Outputs written to a timestamped run directory based on `--out`:
- Run outputs are written to a timestamped run directory:
  - If `--out output`, then `output/session_<timestamp>/...`
  - Otherwise `<out>_<timestamp>/...`
- `session_<timestamp>.ipynb` (sequential notebook)
- `session_<timestamp>.executed.ipynb` (papermill‑executed notebook)
- `session_<timestamp>.md` (markdown export with images)
- `session.json` (dataset profile + semantic sketch + run history)
- `summary.json`
- `tables/table_*.csv`
- `plots/plot_*.png`
- `_md_images/` (only when markdown embeds images)

Note: each run creates a new timestamped output folder based on `--out` unless `--resume` is used.
The notebook embeds plots directly (no need to re‑run cells to see images).
