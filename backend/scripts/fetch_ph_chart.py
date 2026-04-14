from __future__ import annotations

import argparse
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.db.database import SessionLocal, engine
from app.db.models import Base
from app.services.chart_service import upsert_chart_snapshot
from app.services.providers import fetch_philippines_top_songs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch Philippines songs chart and store it")
    parser.add_argument("--chart", default="philippines-songs", help="Chart key")
    parser.add_argument("--limit", type=int, default=100, help="Number of rows to fetch")
    parser.add_argument("--no-enrich", action="store_true", help="Disable metadata enrichment")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    Base.metadata.create_all(bind=engine)

    rows = fetch_philippines_top_songs(limit=args.limit, enrich_metadata=not args.no_enrich)
    with SessionLocal() as db:
        upsert_chart_snapshot(db, args.chart, rows)

    snapshot_date = rows[0].chart_date.isoformat() if rows else "n/a"
    print(f"Imported {len(rows)} rows for {args.chart} on {snapshot_date}")


if __name__ == "__main__":
    main()
