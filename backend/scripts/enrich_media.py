from __future__ import annotations

import argparse
import sys
from datetime import date, datetime
from pathlib import Path
from time import sleep

from sqlalchemy import and_, select

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.db.database import SessionLocal
from app.db.models import ChartEntry
from app.services.providers import enrich_with_itunes


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Enrich chart rows with image, preview, and album metadata")
    parser.add_argument("--date", required=False, help="Single date in YYYY-MM-DD")
    parser.add_argument("--start-date", required=False, help="Start date in YYYY-MM-DD")
    parser.add_argument("--end-date", required=False, help="End date in YYYY-MM-DD")
    parser.add_argument("--chart", default="hot-100", help="Chart key, default: hot-100")
    parser.add_argument("--retries", type=int, default=2, help="Retries per row enrichment attempt")
    parser.add_argument("--retry-delay-seconds", type=float, default=1.5, help="Delay between retries")
    parser.add_argument("--timeout-seconds", type=float, default=8.0, help="HTTP timeout for iTunes request")
    parser.add_argument("--batch-size", type=int, default=50, help="Commit every N row updates")
    parser.add_argument("--limit", type=int, default=0, help="Max rows to inspect in one run. 0 means no limit")
    parser.add_argument("--progress-every", type=int, default=25, help="Print progress every N inspected rows")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing media metadata")
    parser.add_argument("--dry-run", action="store_true", help="Show planned updates without writing to DB")
    return parser.parse_args()


def parse_iso_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def build_date_filter(args: argparse.Namespace):
    if args.date:
        target = parse_iso_date(args.date)
        return ChartEntry.chart_date == target

    if args.start_date and args.end_date:
        start = parse_iso_date(args.start_date)
        end = parse_iso_date(args.end_date)
        if start > end:
            raise ValueError("--start-date must be on or before --end-date")
        return and_(ChartEntry.chart_date >= start, ChartEntry.chart_date <= end)

    return None


def resolve_enrichment(
    title: str,
    artist: str,
    timeout_seconds: float,
    retries: int,
    retry_delay_seconds: float,
    chart: str,
):
    attempts = max(0, retries) + 1
    for attempt in range(1, attempts + 1):
        preferred_country = "PH" if chart == "philippines-songs" else None
        image_url, preview_url, album = enrich_with_itunes(
            title,
            artist,
            timeout_seconds=timeout_seconds,
            preferred_country=preferred_country,
        )
        if image_url or preview_url or album:
            return image_url, preview_url, album

        if attempt < attempts:
            sleep(max(0.0, retry_delay_seconds))

    return None, None, None


def main() -> None:
    args = parse_args()
    date_filter = build_date_filter(args)

    updated = 0
    skipped = 0
    inspected = 0

    with SessionLocal() as db:
        stmt = select(ChartEntry).where(ChartEntry.source_chart == args.chart)
        if date_filter is not None:
            stmt = stmt.where(date_filter)
        if not args.overwrite:
            stmt = stmt.where(
                (ChartEntry.image_url.is_(None))
                | (ChartEntry.preview_url.is_(None))
                | (ChartEntry.album.is_(None))
            )
        stmt = stmt.order_by(ChartEntry.chart_date.desc(), ChartEntry.rank.asc())

        rows = db.execute(stmt).scalars().all()
        if args.limit > 0:
            rows = rows[: args.limit]

        # Cache repeated songs across weeks to reduce API calls and speed up enrichment.
        metadata_cache: dict[tuple[str, str], tuple[str | None, str | None, str | None]] = {}

        pending_writes = 0
        for row in rows:
            inspected += 1

            if args.progress_every > 0 and inspected % args.progress_every == 0:
                print(f"Progress: inspected={inspected}, updated={updated}, skipped={skipped}")

            has_complete_media = row.image_url is not None and row.preview_url is not None and row.album is not None
            if has_complete_media and not args.overwrite:
                skipped += 1
                continue

            cache_key = (row.title, row.artist)
            if cache_key in metadata_cache:
                image_url, preview_url, album = metadata_cache[cache_key]
            else:
                image_url, preview_url, album = resolve_enrichment(
                    row.title,
                    row.artist,
                    timeout_seconds=args.timeout_seconds,
                    retries=args.retries,
                    retry_delay_seconds=args.retry_delay_seconds,
                    chart=args.chart,
                )
                metadata_cache[cache_key] = (image_url, preview_url, album)

            if image_url is None and preview_url is None and album is None:
                skipped += 1
                continue

            if args.overwrite:
                row.image_url = image_url or row.image_url
                row.preview_url = preview_url or row.preview_url
                row.album = album or row.album
            else:
                if row.image_url is None:
                    row.image_url = image_url
                if row.preview_url is None:
                    row.preview_url = preview_url
                if row.album is None:
                    row.album = album

            updated += 1
            pending_writes += 1

            if pending_writes >= args.batch_size and not args.dry_run:
                db.commit()
                pending_writes = 0

        if not args.dry_run:
            db.commit()

    mode = "dry-run" if args.dry_run else "apply"
    print(f"Mode: {mode}")
    print(f"Inspected: {inspected}")
    print(f"Updated: {updated}")
    print(f"Skipped: {skipped}")


if __name__ == "__main__":
    main()
