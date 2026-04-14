from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BASE_DIR.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.db.database import SessionLocal
from app.services.providers import SongRecord, fetch_billboard_chart, fetch_philippines_top_songs
from app.services.chart_service import get_chart_entries, get_latest_chart_date


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export chart snapshots for static frontend hosting")
    parser.add_argument(
        "--output-dir",
        default=str(REPO_ROOT / "frontend" / "public" / "data"),
        help="Output directory for static JSON files",
    )
    parser.add_argument("--global-date", default=date.today().isoformat(), help="Date for hot-100 fetch (YYYY-MM-DD)")
    parser.add_argument("--global-chart", default="hot-100", help="Global chart key")
    parser.add_argument("--ph-chart", default="philippines-songs", help="Philippines chart key")
    parser.add_argument("--limit", type=int, default=100, help="Rows per chart")
    parser.add_argument("--no-enrich-global", action="store_true", help="Disable metadata enrichment for global chart")
    parser.add_argument("--no-enrich-ph", action="store_true", help="Disable metadata enrichment for PH chart")
    return parser.parse_args()


def _load_sample(sample_file: Path) -> list[SongRecord]:
    payload = json.loads(sample_file.read_text(encoding="utf-8"))
    chart_date = date.fromisoformat(payload["chart_date"])
    rows: list[SongRecord] = []
    for item in payload["entries"]:
        rows.append(
            SongRecord(
                chart_date=chart_date,
                rank=item["rank"],
                title=item["title"],
                artist=item["artist"],
                album=item.get("album"),
                image_url=item.get("image_url"),
                preview_url=item.get("preview_url"),
                weeks_on_chart=item.get("weeks_on_chart"),
                peak_position=item.get("peak_position"),
                last_week_position=item.get("last_week_position"),
            )
        )
    return rows


def _load_from_db(chart: str, limit: int) -> list[SongRecord]:
    with SessionLocal() as db:
        latest_date = get_latest_chart_date(db, chart)
        if latest_date is None:
            return []

        rows = get_chart_entries(db, chart, latest_date, limit)
        return [
            SongRecord(
                chart_date=row.chart_date,
                rank=row.rank,
                title=row.title,
                artist=row.artist,
                album=row.album,
                image_url=row.image_url,
                preview_url=row.preview_url,
                weeks_on_chart=row.weeks_on_chart,
                peak_position=row.peak_position,
                last_week_position=row.last_week_position,
            )
            for row in rows
        ]


def serialize_snapshot(chart_key: str, rows: list[SongRecord]) -> dict:
    if not rows:
        raise ValueError(f"No rows available for chart: {chart_key}")

    snapshot_date = rows[0].chart_date.isoformat()
    entries = [asdict(row) for row in rows]
    for entry in entries:
        entry["chart_date"] = entry["chart_date"].isoformat()

    return {
        "source_chart": chart_key,
        "resolved_chart_date": snapshot_date,
        "dates": [snapshot_date],
        "entries": entries,
    }


def write_json(file_path: Path, payload: dict) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)

    chart_sources = {
        "sources": [
            {"key": args.global_chart, "label": "Top Songs Global"},
            {"key": args.ph_chart, "label": "Top Songs Philippines"},
        ]
    }

    sample_file = BASE_DIR / "data" / "sample_hot_100.json"

    try:
        global_rows = fetch_billboard_chart(
            chart_name=args.global_chart,
            chart_date=args.global_date,
            enrich_metadata=not args.no_enrich_global,
        )
        if not global_rows:
            global_rows = _load_from_db(args.global_chart, args.limit)
            if global_rows:
                print("Global fetch returned no rows, using DB fallback")
            else:
                global_rows = _load_sample(sample_file)
                print("Global fetch returned no rows, using sample fallback")
    except Exception as exc:
        global_rows = _load_from_db(args.global_chart, args.limit)
        if global_rows:
            print(f"Global fetch failed, using DB fallback: {exc}")
        else:
            global_rows = _load_sample(sample_file)
            print(f"Global fetch failed, using sample fallback: {exc}")

    try:
        ph_rows = fetch_philippines_top_songs(limit=args.limit, enrich_metadata=not args.no_enrich_ph)
        if not ph_rows:
            ph_rows = _load_from_db(args.ph_chart, args.limit)
            if ph_rows:
                print("Philippines fetch returned no rows, using DB fallback")
    except Exception as exc:
        ph_rows = _load_from_db(args.ph_chart, args.limit)
        if ph_rows:
            print(f"Philippines fetch failed, using DB fallback: {exc}")
        else:
            raise

    global_snapshot = serialize_snapshot(args.global_chart, global_rows[: args.limit])
    ph_snapshot = serialize_snapshot(args.ph_chart, ph_rows[: args.limit])

    write_json(output_dir / "chart_sources.json", chart_sources)
    write_json(output_dir / f"chart_{args.global_chart}.json", global_snapshot)
    write_json(output_dir / f"chart_{args.ph_chart}.json", ph_snapshot)

    print(f"Wrote static data to {output_dir}")
    print(f"{args.global_chart}: {global_snapshot['resolved_chart_date']} ({len(global_snapshot['entries'])} rows)")
    print(f"{args.ph_chart}: {ph_snapshot['resolved_chart_date']} ({len(ph_snapshot['entries'])} rows)")


if __name__ == "__main__":
    main()
