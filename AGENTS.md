# Agents Guide (Repo Root)

This repo contains both backend and frontend for **pogo**. Use this file as the top-level operating guide and refer to `backend/AGENTS.md` for full backend details.

## Purpose
Build **pogo**, a dataset-agnostic generative BI app for non-technical biologists. The app must learn dataset structure at runtime, answer user intents with SQL + visualization, and export the full conversation as a sequential Jupyter notebook.

## Repo Layout
- `backend/` Python backend, CLI, notebook export, FastAPI API.
- `frontend/` Next.js TypeScript UI.

## Core Principles
- Dataset-agnostic, no hardcoded schema assumptions.
- Intent-first, ask at most one clarifying question when needed.
- Runtime profiling feeds the semantic sketch.
- Explainable outputs: SQL, preview, and chart suggestion.
- Reproducible notebook for every step.

## Frontend Rules
- Use Next.js with TypeScript.
- No user authentication for now.
- Story tab is a 1:1 mapping to backend `Step` objects.
- Notebook tab shows the generated notebook status and download.

## Backend Rules
- Use FastAPI for the API surface.
- Every `step()` call in the LLM agent must append a structured Step to `session.json`.
- The notebook is a derivative artifact generated from steps.
- One dataset per workbook (session).

## If Something Is Missing
If the frontend needs behavior that the backend does not expose, implement it in the backend first and then wire the frontend to it.

## Full Backend Guidance
See `backend/AGENTS.md`.
