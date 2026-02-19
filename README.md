# pogo

A dataset‑agnostic generative BI app for bioinformatics. Ask a question in plain English, get a clean narrative with tables, charts, and a reproducible notebook.

**Command:**

```bash
pogo --model eu.anthropic.claude-opus-4-6-v1 \
  --dataset tests/fixtures/airway \
  --prompt "What are the top upregulated genes after dex treatment?" \
  --out output/session
```

**Output:**

<img src="assets/pogo-demo.gif" alt="pogo demo" width="100%" />

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

Multiple prompts (run sequentially):
```bash
pogo \
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
- `<title>.executed.ipynb` (papermill‑executed notebook)
- `<title>.md` (markdown export with images)
- `summary.json`
- `tables/table_*.csv`
- `plots/plot_*.png`

Note: each run creates a new timestamped output folder based on `--out`.
The notebook embeds plots directly (no need to re‑run cells to see images).
