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
