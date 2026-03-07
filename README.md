# POGO

A dataset exploration tool that generates a notebook in a conversational way. Ask a question in plain English, get SQL, tables, charts, and a reproducible notebook.

**Command:**

```bash
# point to your dataset and start chatting
pogo --dataset tests/fixtures/airway
  > "What are the top upregulated genes after dex treatment?"
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

```text
$ pogo --help
usage: pogo [-h] --dataset DATASET [--prompt PROMPT] [--out OUT] [--resume RESUME] [--model MODEL] [--quiet] [--json]

pogo: dataset-agnostic data analysis agent

options:
  -h, --help         show this help message and exit
  --dataset DATASET  Path to dataset file or directory
  --prompt PROMPT    Prompt to run (repeatable)
  --out OUT          Output directory
  --resume RESUME    Resume from an existing output directory
  --model MODEL      LLM model name
  --quiet            Suppress non-error output
  --json             Emit JSONL events to stdout

Examples:
  pogo --dataset data.csv --prompt "Give me an overview" --out output
  pogo --dataset tests/fixtures/airway \
    --prompt "Compare treated vs control" \
    --prompt "Show counts for gene GENE_0001" \
    --out output

Provider defaults:
  default provider -> openai
  openai -> gpt-5.3-codex
  anthropic -> claude-3-5-sonnet-latest
  bedrock -> eu.anthropic.claude-opus-4-6-v1

Shortcuts:
  --model openai (same as --model openai:gpt-5.3-codex)
  --model anthropic (same as --model anthropic:claude-3-5-sonnet-latest)
  --model bedrock (same as --model bedrock:eu.anthropic.claude-opus-4-6-v1)

Outputs (written to a new timestamped folder based on --out):
  If --out output: output/session_<timestamp>/...
  Otherwise: <out>_<timestamp>/...
  session_<timestamp>.ipynb (sequential notebook)
  session_<timestamp>.executed.ipynb
  session_<timestamp>.md
  session.json
  summary.json
  tables/table_*.csv
  plots/plot_*.png (if matplotlib is available)

Automation:
  --json emits JSONL events to stdout
  --quiet suppresses non-error output
```

## Providers

<details>
<summary>OpenAI</summary>

Default model: `gpt-5.3-codex` (strong code + reasoning default for general analysis tasks).
This model uses the Responses API (it is not supported by chat completions).

Credentials:
```bash
export OPENAI_API_KEY="..."
```

Examples:
```bash
pogo --model openai --dataset <file-or-folder> --prompt "<question>" --out <output-dir>
```

```bash
pogo --model openai:gpt-5.3-codex --dataset <file-or-folder> --prompt "<question>" --out <output-dir>
```
</details>

<details>
<summary>Anthropic</summary>

Default model: `claude-3-5-sonnet-latest` (fast, strong general model for everyday analysis).

Credentials:
```bash
export ANTHROPIC_API_KEY="..."
```

Examples:
```bash
pogo --model anthropic --dataset <file-or-folder> --prompt "<question>" --out <output-dir>
```

```bash
pogo --model anthropic:claude-3-5-sonnet-latest --dataset <file-or-folder> --prompt "<question>" --out <output-dir>
```
</details>

<details>
<summary>AWS Bedrock</summary>

Default model: `eu.anthropic.claude-opus-4-6-v1` (highest-capacity Anthropic model available via Bedrock).

Credentials:
```bash
export AWS_PROFILE="vincent"
export AWS_REGION="us-east-1"
```

Examples:
```bash
pogo --model bedrock --dataset <file-or-folder> --prompt "<question>" --out <output-dir>
```

```bash
pogo --model bedrock:eu.anthropic.claude-opus-4-6-v1 --dataset <file-or-folder> --prompt "<question>" --out <output-dir>
```
</details>
