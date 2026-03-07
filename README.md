# pogo

Dataset-agnostic generative BI for biologists. This repo is split into a Python backend (FastAPI + CLI) and a Next.js frontend.

**Repo Layout**
- `backend/` Python codebase, CLI, notebook generation, FastAPI API
- `frontend/` Next.js TypeScript app (chat + story + notebook view)
- `ci/` helper scripts

**Quick Start**
1. Install dependencies

```bash
ci/install.sh
```

2. Run backend + frontend

```bash
ci/run_all.sh
```

Backend runs on `http://127.0.0.1:8000` and frontend on `http://localhost:3000` by default.

**Environment**
- Anthropic API: `export ANTHROPIC_API_KEY="..."`
- Bedrock: `export AWS_PROFILE=vincent` and `export AWS_REGION=us-east-1`

**Backend API**
- FastAPI app: `backend/pogo/api/app.py` (run via `uv run`)
- Artifacts served at `/artifacts/{workbook_id}/...`
- Steps persisted to `session.json` under each workbook

**Frontend**
- Story and Notebook tabs are in `frontend/src/app/workbooks/[id]/page.tsx`
- API client in `frontend/src/lib/api.ts`

**Notes**
- One dataset per workbook for now.
- Story steps map 1:1 to backend steps.
