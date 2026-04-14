# Aux.

Aux. is a chart-style music website that tracks ranked songs (Top 10/25/50/100), lets users filter by time periods, and surfaces song metadata with cover art and audio previews.

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| 🎨 Frontend | Next.js + React + TypeScript | Interactive chart UI, filters, pagination, and song detail views |
| ⚙️ Backend API | FastAPI (Python) | Chart query API, period/date resolution, and data delivery |
| 🗃️ Database | SQLite + SQLAlchemy | Persistent chart storage and metadata records |
| 🕷️ Data Ingestion | Python scraping pipeline (`billboard.py`) | Collect weekly chart rankings and keep historical snapshots |
| 🎵 Metadata Enrichment | iTunes + Deezer lookup fallback | Resolve album art, audio previews, and album metadata |

## Vercel-Only Hosting (No Render)

You can deploy Aux as a static-data Next.js app on Vercel and refresh chart content daily with GitHub Actions.

### 1. Frontend Runtime Mode

Set this environment variable in Vercel:

- `NEXT_PUBLIC_DATA_MODE=static`

When set to `static`, the frontend reads chart JSON from `frontend/public/data` instead of calling a backend API.

### 2. Data Export Script

Use this script to generate static chart files:

- `backend/scripts/export_static_data.py`

It writes:

- `frontend/public/data/chart_sources.json`
- `frontend/public/data/chart_hot-100.json`
- `frontend/public/data/chart_philippines-songs.json`

### 3. Daily Automatic Updates

A workflow is included at:

- `.github/workflows/update-chart-data.yml`

It runs daily and also supports manual runs (`workflow_dispatch`).
On each run, it:

1. Installs backend dependencies
2. Regenerates static chart JSON
3. Commits and pushes only when chart data changed

This push triggers a fresh Vercel deployment so visitors see updated chart rankings and previews.
