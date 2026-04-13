from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from time import sleep

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.core.config import settings
from app.db.database import SessionLocal, engine
from app.db.models import Base, ChartEntry
from app.services.providers import SongRecord, fetch_billboard_chart


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch Billboard chart data and store it in SQLite")
    parser.add_argument("--date", required=False, help="Date in YYYY-MM-DD format. Defaults to today.")
    parser.add_argument("--start-date", required=False, help="Backfill start date in YYYY-MM-DD format")
    parser.add_argument("--end-date", required=False, help="Backfill end date in YYYY-MM-DD format")
    parser.add_argument("--step-days", type=int, default=7, help="Backfill step size in days. Default is 7")
    parser.add_argument("--chart", default=settings.chart_name, help="Chart name, e.g., hot-100")
    parser.add_argument(
        "--sample-file",
        default="data/sample_hot_100.json",
        help="Fallback sample JSON file used when Billboard fetch fails",
    )
    parser.add_argument("--replace", action="store_true", help="Replace records for the same chart date")
    parser.add_argument("--continue-on-error", action="store_true", help="Continue when one backfill date fails")
    parser.add_argument("--no-enrich", action="store_true", help="Disable iTunes metadata enrichment for faster imports")
    parser.add_argument("--retries", type=int, default=2, help="Retries per date fetch. Default is 2")
    parser.add_argument(
        "--retry-delay-seconds", type=float, default=2.0, help="Delay between retries in seconds. Default is 2"
    )
    parser.add_argument(
        "--fetch-timeout-seconds",
        type=float,
        default=45.0,
        help="Max seconds per date fetch before force timeout. Default is 45",
    )
    return parser.parse_args()


def parse_iso_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def iter_target_dates(args: argparse.Namespace) -> list[date]:
    if args.start_date and args.end_date:
        if args.step_days <= 0:
            raise ValueError("--step-days must be greater than 0")

        start = parse_iso_date(args.start_date)
        end = parse_iso_date(args.end_date)
        if start > end:
            raise ValueError("--start-date must be on or before --end-date")

        values: list[date] = []
        cursor = start
        while cursor <= end:
            values.append(cursor)
            cursor += timedelta(days=args.step_days)
        return values

    single = parse_iso_date(args.date) if args.date else date.today()
    return [single]


def load_sample(sample_file: Path) -> list[SongRecord]:
    payload = json.loads(sample_file.read_text(encoding="utf-8"))
    chart_date = date.fromisoformat(payload["chart_date"])
    songs: list[SongRecord] = []

    for item in payload["entries"]:
        songs.append(
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

    return songs


def upsert_rows(db: Session, chart_name: str, rows: list[SongRecord], replace: bool) -> None:
    if not rows:
        return

    chart_date = rows[0].chart_date
    existing_entries = db.execute(
        select(ChartEntry).where(ChartEntry.source_chart == chart_name, ChartEntry.chart_date == chart_date)
    ).scalars().all()
    existing_by_rank = {entry.rank: entry for entry in existing_entries}

    # Keep media metadata when the incoming rows have null media (for no-enrich backfills).
    for row in rows:
        previous = existing_by_rank.get(row.rank)
        if previous is None:
            continue
        if row.image_url is None:
            row.image_url = previous.image_url
        if row.preview_url is None:
            row.preview_url = previous.preview_url
        if row.album is None:
            row.album = previous.album

    if replace:
        db.execute(
            delete(ChartEntry).where(
                ChartEntry.source_chart == chart_name,
                ChartEntry.chart_date == chart_date,
            )
        )
    else:
        existing_count = len(existing_entries)
        if existing_count > 0:
            return

    for row in rows:
        db.add(
            ChartEntry(
                source_chart=chart_name,
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
        )

    db.commit()


def _fetch_worker(
    queue: mp.Queue,
    chart_name: str,
    chart_date: str,
    enrich_metadata: bool,
) -> None:
    try:
        rows = fetch_billboard_chart(chart_name, chart_date, enrich_metadata=enrich_metadata)
        queue.put(("ok", rows))
    except Exception as exc:
        queue.put(("error", str(exc)))


def fetch_with_timeout(
    chart_name: str,
    chart_date: date,
    enrich_metadata: bool,
    timeout_seconds: float,
) -> tuple[list[SongRecord] | None, str | None]:
    queue: mp.Queue = mp.Queue()
    process = mp.Process(
        target=_fetch_worker,
        args=(queue, chart_name, chart_date.isoformat(), enrich_metadata),
    )
    process.start()
    process.join(timeout_seconds)

    if process.is_alive():
        process.terminate()
        process.join()
        return None, f"fetch timeout after {timeout_seconds}s"

    if queue.empty():
        return None, "fetch failed without payload"

    status, payload = queue.get()
    if status == "ok":
        return payload, None

    return None, str(payload)


def fetch_with_retries(args: argparse.Namespace, target_date: date) -> tuple[list[SongRecord] | None, str | None]:
    attempts = max(0, args.retries) + 1
    last_error: str | None = None

    for attempt in range(1, attempts + 1):
        rows, error = fetch_with_timeout(
            args.chart,
            target_date,
            enrich_metadata=not args.no_enrich,
            timeout_seconds=args.fetch_timeout_seconds,
        )

        if rows is not None:
            return rows, None

        last_error = error or "unknown fetch error"
        if attempt < attempts:
            print(
                f"Retrying {target_date.isoformat()} ({attempt}/{attempts - 1} retries used): {last_error}",
            )
            sleep(max(0.0, args.retry_delay_seconds))

    return None, last_error


def main() -> None:
    args = parse_args()
    target_dates = iter_target_dates(args)

    Base.metadata.create_all(bind=engine)

    imported_rows = 0
    processed_dates = 0

    with SessionLocal() as db:
        for target_date in target_dates:
            rows, error = fetch_with_retries(args, target_date)
            source = "billboard"

            if rows is None:
                if len(target_dates) == 1:
                    rows = load_sample(Path(args.sample_file))
                    source = "sample"
                    print(f"Falling back to sample data due to fetch error: {error}")
                elif args.continue_on_error:
                    print(f"Skipped {target_date.isoformat()} after retries: {error}")
                    continue
                else:
                    raise RuntimeError(f"Failed to fetch {target_date.isoformat()}: {error}")

            # Never allow partial sample fallback to wipe a full chart snapshot.
            replace_for_write = args.replace and source != "sample"
            upsert_rows(db, args.chart, rows, replace=replace_for_write)
            imported_rows += len(rows)
            processed_dates += 1
            resolved_date = rows[0].chart_date if rows else target_date
            print(f"Imported {len(rows)} rows from {source} for {resolved_date}")

    print(f"Done: processed {processed_dates} dates, imported {imported_rows} rows")


if __name__ == "__main__":
    mp.freeze_support()
    main()
