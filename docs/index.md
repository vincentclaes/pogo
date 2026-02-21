# pogo

pogo is a dataset-agnostic generative BI app for biologists. Ask a question in plain English, get SQL, a table preview, and a chart suggestion, plus a sequential Jupyter notebook that captures the full reasoning trail.

## What You Can Do
- Load CSV, TSV, Excel, or Parquet datasets without schema setup.
- Ask intent-first questions and get explainable answers.
- Export everything to a runnable notebook and Markdown report.

## Quick Start
```bash
pogo --dataset <file-or-folder> --prompt "<question>" --out <output-dir>
```

## Key Docs
- Introduction (Human): product overview and usage.
- Introduction (Machine): constraints and system contract.
- Plan: architecture and MVP milestones.
- Testing: E2E expectations and the airway harness.
