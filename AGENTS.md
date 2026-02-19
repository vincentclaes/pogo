# Agents Guide

## Purpose
Build **biosignal**, a dataset-agnostic generative BI app for non-technical biologists. The app must learn dataset structure at runtime, answer user intents with SQL + visualization, and export the full conversation as a sequential Jupyter notebook.

## Core Principles
- **Dataset-agnostic**: No hardcoded schema assumptions.
- **Intent-first**: Ask the user what they want to do, then only ask clarifying questions if confidence is low.
- **Runtime learning**: Profile data on load to infer columns, types, and likely group-bys.
- **Explainable**: Show the SQL, a table preview, and a chart suggestion.
- **Reproducible**: Every step is logged to a notebook (intent, SQL, results, notes, visuals).
- **LLM-driven content**: The LLM must provide titles and explanations for each query step and chart.

## Supported Input Formats (MVP)
- CSV
- TSV
- Excel (`.xlsx`)
- Parquet

## Runtime Profiling Requirements
After load, generate a compact profile:
- Column names and inferred types
- Distinct counts and missingness
- Numeric ranges and quantiles
- Top categorical values
- Candidate ID columns (e.g., suffix `_id`, unique values)
- Candidate datetime columns

This profile feeds the semantic sketch used for intent mapping.

## Intent-First Agent Loop
1. **Ask for intent**: "What do you want to do with this data?"
2. **Infer intent** from the user text and profile.
3. **Confidence check**:
   - If high: generate SQL + visualization directly.
   - If low: ask a single clarifying question (e.g., which column to group by).
4. **Execute query** in DuckDB.
5. **Summarize** results and provide a visualization.
6. **Confirm**: "Is this what you wanted?" If no, refine.

## LLM Responsibilities (Required)
- Provide a **short title** for each query step.
- Provide **reasoning/explanation** for why the query is run.
- Provide **"what we see and why"** captions for charts.
- Ask **at most one** clarification question when needed.

## Notebook Export
- Every agent step becomes a notebook cell:
  - Intent, SQL, result preview, visualization code, notes/insights.
- Notebook must be runnable and sequential.
 - CLI runs must write `session.ipynb` into the output directory.

## Test Dataset (Airway RNA-seq)
Use the airway dataset as the end-to-end test harness. This is not special-cased in the code; it is only used to validate correctness.

### Airway Use Cases (Expected Behaviors)
These are the checks to close the feedback loop and validate the agent:
1. **Differential expression summary**
   - Prompt: "What are the top upregulated genes after dex treatment?"
   - Expected: SQL over `de_results` (or proxy table) returning top genes by `log2fc`.
2. **Group comparison**
   - Prompt: "Compare average expression between treated and control samples."
   - Expected: SQL join between `counts` and `samples`, grouped by treatment.
3. **Sample overview**
   - Prompt: "How many samples are treated vs control?"
   - Expected: group-by count using the inferred categorical column.
4. **Gene lookup**
   - Prompt: "Show counts for gene X across samples."
   - Expected: filter on gene id, then show sample-level counts.
5. **Exploratory summary**
   - Prompt: "Give me an overview of the data."
   - Expected: row counts, missingness summary, category distributions.

### Success Criteria (Airway)
- The agent needs zero schema hints and still answers the above prompts.
- The agent only asks a clarifying question when intent cannot be resolved.
- Notebook export includes intent, SQL, results, and visualization for each step.

## Deployment Goal (MVP)
- Local-first, zero-ops (DuckDB + minimal backend), no VPC.

## Do / Don't
- Do not hardcode dataset-specific logic.
- Do not ask multiple questions in a row unless strictly necessary.
- Do provide explicit SQL and previewed results every time.
- Do log every step into the notebook recorder.
