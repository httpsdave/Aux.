from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import date
from pathlib import Path
import re

from sqlalchemy.exc import OperationalError

BASE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BASE_DIR.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.db.database import SessionLocal, engine
from app.db.models import Base
from app.services.providers import SongRecord, fetch_global_top_songs, fetch_philippines_top_songs
from app.services.chart_service import get_chart_entries, get_latest_chart_date


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export chart snapshots for static frontend hosting")
    parser.add_argument(
        "--output-dir",
        default=str(REPO_ROOT / "frontend" / "public" / "data"),
        help="Output directory for static JSON files",
    )
    parser.add_argument("--global-chart", default="hot-100", help="Global chart key")
    parser.add_argument("--ph-chart", default="philippines-songs", help="Philippines chart key")
    parser.add_argument("--limit", type=int, default=100, help="Rows per chart")
    parser.add_argument("--no-enrich-global", action="store_true", help="Disable metadata enrichment for global chart")
    parser.add_argument("--no-enrich-ph", action="store_true", help="Disable metadata enrichment for PH chart")
    parser.add_argument(
        "--global-enrich-timeout-seconds",
        type=float,
        default=10.0,
        help="Timeout per iTunes metadata request during global enrichment",
    )
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


def _load_snapshot_rows(snapshot_file: Path) -> list[SongRecord]:
    if not snapshot_file.exists():
        return []

    try:
        payload = json.loads(snapshot_file.read_text(encoding="utf-8"))
    except Exception:
        return []

    resolved_date = payload.get("resolved_chart_date") or payload.get("chart_date")
    try:
        chart_date = date.fromisoformat(str(resolved_date))
    except Exception:
        chart_date = date.today()

    rows: list[SongRecord] = []
    for item in payload.get("entries") or []:
        if not isinstance(item, dict):
            continue

        try:
            rank = int(item.get("rank"))
        except Exception:
            continue

        title = str(item.get("title") or "").strip()
        artist = str(item.get("artist") or "").strip()
        if not title or not artist:
            continue

        rows.append(
            SongRecord(
                chart_date=chart_date,
                rank=rank,
                title=title,
                artist=artist,
                album=item.get("album"),
                image_url=item.get("image_url"),
                preview_url=item.get("preview_url"),
                weeks_on_chart=item.get("weeks_on_chart"),
                peak_position=item.get("peak_position"),
                last_week_position=item.get("last_week_position"),
            )
        )

    return rows


def _row_identity(row: SongRecord) -> tuple[str, str]:
    return (_normalize_key(row.title), _normalize_key(row.artist))


def _pad_rows_from_sample(rows: list[SongRecord], sample_rows: list[SongRecord], limit: int) -> tuple[list[SongRecord], int]:
    if len(rows) >= limit:
        return rows, 0

    combined = list(rows)
    existing = {_row_identity(row) for row in combined}

    for sample_row in sample_rows:
        if len(combined) >= limit:
            break
        key = _row_identity(sample_row)
        if key in existing:
            continue
        combined.append(sample_row)
        existing.add(key)

    padded = max(0, len(combined) - len(rows))
    return combined, padded


def _load_from_db(chart: str, limit: int) -> list[SongRecord]:
    try:
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
    except OperationalError:
        # CI runners may not have a seeded DB yet; treat as empty fallback.
        return []


def _normalize_key(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", " ", (value or "").casefold())
    return " ".join(cleaned.split())


def _media_cache_key(title: str, artist: str) -> str:
    return f"{_normalize_key(title)}::{_normalize_key(artist)}"


def _build_media_cache_from_snapshot(snapshot_file: Path) -> dict[str, dict[str, str]]:
    if not snapshot_file.exists():
        return {}

    try:
        payload = json.loads(snapshot_file.read_text(encoding="utf-8"))
    except Exception:
        return {}

    entries = payload.get("entries") or []
    cache: dict[str, dict[str, str]] = {}

    if isinstance(entries, dict):
        for key, media in entries.items():
            if not isinstance(media, dict):
                continue
            normalized_media: dict[str, str] = {}
            for field in ("image_url", "preview_url", "album"):
                value = media.get(field)
                if isinstance(value, str) and value.strip():
                    normalized_media[field] = value.strip()
            if normalized_media:
                cache[str(key)] = normalized_media
        return cache

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        title = str(entry.get("title") or "")
        artist = str(entry.get("artist") or "")
        key = _media_cache_key(title, artist)
        if not key:
            continue

        media: dict[str, str] = {}
        image_url = entry.get("image_url")
        preview_url = entry.get("preview_url")
        album = entry.get("album")

        if isinstance(image_url, str) and image_url.strip():
            media["image_url"] = image_url.strip()
        if isinstance(preview_url, str) and preview_url.strip():
            media["preview_url"] = preview_url.strip()
        if isinstance(album, str) and album.strip():
            media["album"] = album.strip()

        if media:
            cache[key] = media

    return cache


def _merge_media_cache(base: dict[str, dict[str, str]], extra: dict[str, dict[str, str]]) -> dict[str, dict[str, str]]:
    merged = dict(base)
    for key, media in extra.items():
        existing = dict(merged.get(key, {}))
        for field in ("image_url", "preview_url", "album"):
            value = media.get(field)
            if value and field not in existing:
                existing[field] = value
        if existing:
            merged[key] = existing
    return merged


def _apply_media_cache(rows: list[SongRecord], media_cache: dict[str, dict[str, str]]) -> int:
    patched = 0
    for row in rows:
        key = _media_cache_key(row.title, row.artist)
        media = media_cache.get(key)
        if not media:
            continue

        changed = False
        if row.image_url is None and media.get("image_url"):
            row.image_url = media["image_url"]
            changed = True
        if row.preview_url is None and media.get("preview_url"):
            row.preview_url = media["preview_url"]
            changed = True
        if row.album is None and media.get("album"):
            row.album = media["album"]
            changed = True

        if changed:
            patched += 1

    return patched


def _build_media_cache_from_rows(rows: list[SongRecord]) -> dict[str, dict[str, str]]:
    cache: dict[str, dict[str, str]] = {}
    for row in rows:
        media: dict[str, str] = {}
        if isinstance(row.image_url, str) and row.image_url.strip():
            media["image_url"] = row.image_url.strip()
        if isinstance(row.preview_url, str) and row.preview_url.strip():
            media["preview_url"] = row.preview_url.strip()
        if isinstance(row.album, str) and row.album.strip():
            media["album"] = row.album.strip()
        if media:
            cache[_media_cache_key(row.title, row.artist)] = media
    return cache


def _write_media_cache(file_path: Path, media_cache: dict[str, dict[str, str]]) -> None:
    ordered = dict(sorted(media_cache.items(), key=lambda item: item[0]))
    write_json(file_path, {"entries": ordered})


def serialize_snapshot(chart_key: str, rows: list[SongRecord]) -> dict:
    if not rows:
        # Return a valid but empty snapshot instead of crashing.
        return {
            "source_chart": chart_key,
            "resolved_chart_date": date.today().isoformat(),
            "dates": [date.today().isoformat()],
            "entries": [],
        }

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


def preview_coverage(snapshot: dict) -> tuple[int, int, float]:
    entries = snapshot.get("entries") or []
    total = len(entries)
    with_preview = sum(1 for row in entries if row.get("preview_url"))
    ratio = (with_preview / total) if total else 0.0
    return with_preview, total, ratio


def _resolve_chart_rows(
    label: str,
    chart_key: str,
    fetch_fn,
    fetch_kwargs: dict,
    snapshot_file: Path,
    limit: int,
) -> list[SongRecord]:
    """3-tier fallback: live fetch → DB → existing on-disk snapshot.

    Never raises — returns an empty list as a last resort so the script
    always produces valid output.
    """
    # Tier 1: live fetch
    rows: list[SongRecord] = []
    try:
        rows = fetch_fn(**fetch_kwargs)
    except Exception as exc:
        print(f"[{label}] Live fetch raised: {exc}")

    if rows:
        return rows

    # Tier 2: database
    rows = _load_from_db(chart_key, limit)
    if rows:
        print(f"[{label}] Live fetch returned no rows, using DB fallback")
        return rows

    # Tier 3: reuse existing on-disk snapshot
    rows = _load_snapshot_rows(snapshot_file)
    if rows:
        print(f"[{label}] Live fetch + DB empty, reusing existing snapshot ({len(rows)} rows)")
        return rows

    print(f"WARNING: [{label}] All sources empty — no data available")
    return []


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)

    # Ensure DB schema exists before any fallback reads in clean CI environments.
    Base.metadata.create_all(bind=engine)

    chart_sources = {
        "sources": [
            {"key": args.global_chart, "label": "Top Songs Global"},
            {"key": args.ph_chart, "label": "Top Songs Philippines"},
        ]
    }

    global_snapshot_file = output_dir / f"chart_{args.global_chart}.json"
    ph_snapshot_file = output_dir / f"chart_{args.ph_chart}.json"
    media_cache_file = output_dir / "media_cache.json"

    media_cache: dict[str, dict[str, str]] = {}
    media_cache = _merge_media_cache(media_cache, _build_media_cache_from_snapshot(global_snapshot_file))
    media_cache = _merge_media_cache(media_cache, _build_media_cache_from_snapshot(ph_snapshot_file))
    media_cache = _merge_media_cache(media_cache, _build_media_cache_from_snapshot(media_cache_file))

    # Global chart — Apple RSS feed
    global_rows = _resolve_chart_rows(
        label="Global",
        chart_key=args.global_chart,
        fetch_fn=fetch_global_top_songs,
        fetch_kwargs=dict(
            limit=args.limit,
            enrich_metadata=not args.no_enrich_global,
            timeout_seconds=args.global_enrich_timeout_seconds,
        ),
        snapshot_file=global_snapshot_file,
        limit=args.limit,
    )

    global_patched = _apply_media_cache(global_rows, media_cache)
    if global_patched:
        print(f"Global rows patched from cache: {global_patched}")

    # Philippines chart — Apple RSS feed
    ph_rows = _resolve_chart_rows(
        label="Philippines",
        chart_key=args.ph_chart,
        fetch_fn=fetch_philippines_top_songs,
        fetch_kwargs=dict(limit=args.limit, enrich_metadata=not args.no_enrich_ph),
        snapshot_file=ph_snapshot_file,
        limit=args.limit,
    )

    ph_patched = _apply_media_cache(ph_rows, media_cache)
    if ph_patched:
        print(f"PH rows patched from cache: {ph_patched}")

    media_cache = _merge_media_cache(media_cache, _build_media_cache_from_rows(global_rows))
    media_cache = _merge_media_cache(media_cache, _build_media_cache_from_rows(ph_rows))

    global_snapshot = serialize_snapshot(args.global_chart, global_rows[: args.limit])
    ph_snapshot = serialize_snapshot(args.ph_chart, ph_rows[: args.limit])

    # Only write new files if we actually have data.  If both are empty,
    # leave the existing files intact (they may still be valid from a
    # previous successful run).
    has_global = len(global_snapshot.get("entries", [])) > 0
    has_ph = len(ph_snapshot.get("entries", [])) > 0

    write_json(output_dir / "chart_sources.json", chart_sources)

    if has_global:
        write_json(output_dir / f"chart_{args.global_chart}.json", global_snapshot)
    else:
        print(f"Skipping write for {args.global_chart} — no entries (existing file preserved)")

    if has_ph:
        write_json(output_dir / f"chart_{args.ph_chart}.json", ph_snapshot)
    else:
        print(f"Skipping write for {args.ph_chart} — no entries (existing file preserved)")

    _write_media_cache(media_cache_file, media_cache)

    global_preview_count, global_total, global_ratio = preview_coverage(global_snapshot)
    ph_preview_count, ph_total, ph_ratio = preview_coverage(ph_snapshot)

    print(f"Wrote static data to {output_dir}")
    print(f"{args.global_chart}: {global_snapshot['resolved_chart_date']} ({len(global_snapshot['entries'])} rows)")
    print(f"{args.ph_chart}: {ph_snapshot['resolved_chart_date']} ({len(ph_snapshot['entries'])} rows)")
    print(
        f"{args.global_chart} preview coverage: "
        f"{global_preview_count}/{global_total} ({global_ratio:.1%})"
    )
    print(
        f"{args.ph_chart} preview coverage: "
        f"{ph_preview_count}/{ph_total} ({ph_ratio:.1%})"
    )


if __name__ == "__main__":
    main()
