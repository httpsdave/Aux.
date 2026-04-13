from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import httpx


@dataclass
class SongRecord:
    chart_date: date
    rank: int
    title: str
    artist: str
    album: str | None = None
    image_url: str | None = None
    preview_url: str | None = None
    weeks_on_chart: int | None = None
    peak_position: int | None = None
    last_week_position: int | None = None


def enrich_with_itunes(title: str, artist: str, timeout_seconds: float = 8.0) -> tuple[str | None, str | None, str | None]:
    params = {"term": f"{title} {artist}", "media": "music", "limit": 1}
    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            response = client.get("https://itunes.apple.com/search", params=params)
            response.raise_for_status()
            payload = response.json()
    except Exception:
        return None, None, None

    results = payload.get("results", [])
    if not results:
        return None, None, None

    item = results[0]
    image_url = item.get("artworkUrl100")
    preview_url = item.get("previewUrl")
    album = item.get("collectionName")
    if image_url and preview_url and album:
        return image_url, preview_url, album

    fallback_image_url, fallback_preview_url, fallback_album = enrich_with_deezer(title, artist, timeout_seconds)
    return (
        image_url or fallback_image_url,
        preview_url or fallback_preview_url,
        album or fallback_album,
    )


def enrich_with_deezer(title: str, artist: str, timeout_seconds: float = 8.0) -> tuple[str | None, str | None, str | None]:
    params = {"q": f'track:"{title}" artist:"{artist}"'}
    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            response = client.get("https://api.deezer.com/search", params=params)
            response.raise_for_status()
            payload = response.json()
    except Exception:
        return None, None, None

    results = payload.get("data", [])
    if not results:
        return None, None, None

    item = results[0]
    album_info = item.get("album") or {}
    image_url = album_info.get("cover_medium")
    preview_url = item.get("preview")
    album = album_info.get("title")
    return image_url, preview_url, album


def fetch_billboard_chart(chart_name: str, chart_date: str, enrich_metadata: bool = True) -> list[SongRecord]:
    import billboard

    chart = billboard.ChartData(chart_name, date=chart_date)
    normalized_date = date.fromisoformat(str(chart.date))
    rows: list[SongRecord] = []

    for idx, entry in enumerate(chart, start=1):
        title = getattr(entry, "title", "")
        artist = getattr(entry, "artist", "")
        if enrich_metadata:
            image_url, preview_url, album = enrich_with_itunes(title, artist)
        else:
            image_url, preview_url, album = None, None, None

        rows.append(
            SongRecord(
                chart_date=normalized_date,
                rank=idx,
                title=title,
                artist=artist,
                album=album,
                image_url=image_url,
                preview_url=preview_url,
                weeks_on_chart=getattr(entry, "weeks", None),
                peak_position=getattr(entry, "peakPos", None),
                last_week_position=getattr(entry, "lastPos", None),
            )
        )

    return rows
