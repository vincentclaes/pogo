# pogo

**Human page:** This README is the human-facing overview and usage guide.

A dataset‑agnostic generative BI app for bioinformatics. Ask a question in plain English, get a clean narrative with tables, charts, and a reproducible notebook.

**Command:** See Command Reference below.

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
See Command Reference.

## LLM Credentials (Required for Runs)
Anthropic API and Bedrock credentials are listed in Command Reference.

## Local CI (Before Commit)
See Command Reference.

## How It Works
1. User Prompt
2. LLM Agent (asks only if needed)
3. Runtime Profiling + Semantic Sketch
4. SQL Generation + Execution (DuckDB)
5. Tables + Charts + Story
6. Notebook + Markdown Export

## CLI Guide
Basic usage: see Command Reference.
Specify a model: see Command Reference.
Interactive usage: see Command Reference.
Resume a prior session: see Command Reference.
Machine-readable output: see Command Reference.
Quiet mode: see Command Reference.
Multiple prompts: see Command Reference.

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

## Command Reference
```
# Example command
pogo --model eu.anthropic.claude-opus-4-6-v1 \
  --dataset tests/fixtures/airway \
  --prompt "What are the top upregulated genes after dex treatment?" \
  --out output

# Setup
ci/setup.sh
pre-commit install

# LLM credentials
export ANTHROPIC_API_KEY="..."
export AWS_REGION="us-east-1"

# Local CI
ci/local_ci.sh

# Basic usage
pogo --dataset <file-or-folder> --prompt "<question>" --out <output-dir>

# Specify a model (Bedrock or Anthropic)
pogo --model eu.anthropic.claude-opus-4-6-v1 --dataset <file-or-folder> --prompt "<question>" --out <output-dir>

# Interactive usage (asks for intent if no prompt provided)
pogo --dataset <file-or-folder> --out <output-dir>

# Resume a prior session (continue the notebook and session log)
pogo --dataset <file-or-folder> --prompt "<question>" --resume <output-dir>

# Machine-readable output (JSONL events)
pogo --dataset <file-or-folder> --prompt "<question>" --out <output-dir> --json

# Quiet mode (suppress non-error output)
pogo --dataset <file-or-folder> --prompt "<question>" --out <output-dir> --quiet

# Multiple prompts (run sequentially)
pogo \
  --dataset tests/fixtures/airway \
  --prompt "What are the top upregulated genes after dex treatment?" \
  --prompt "Compare average expression between treated and control samples." \
  --prompt "How many samples are treated vs control?" \
  --prompt "Show counts for gene GENE_0001 across samples." \
  --prompt "Give me an overview of the data." \
  --out output
```
