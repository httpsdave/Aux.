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


def enrich_with_itunes(
    title: str,
    artist: str,
    timeout_seconds: float = 8.0,
    preferred_country: str | None = None,
) -> tuple[str | None, str | None, str | None]:
    query_terms = [
        f"{title} {artist}",
        f"{title} - {artist}",
        title,
    ]

    country_candidates: list[str | None] = []
    if preferred_country:
        country_candidates.append(preferred_country)
    if "US" not in country_candidates:
        country_candidates.append("US")
    country_candidates.append(None)

    best_image_url = None
    best_preview_url = None
    best_album = None

    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            for country in country_candidates:
                for term in query_terms:
                    params = {"term": term, "media": "music", "entity": "song", "limit": 5}
                    if country is not None:
                        params["country"] = country

                    response = client.get("https://itunes.apple.com/search", params=params)
                    response.raise_for_status()
                    payload = response.json()

                    results = payload.get("results", [])
                    if not results:
                        continue

                    for item in results:
                        image_url = item.get("artworkUrl100")
                        preview_url = item.get("previewUrl")
                        album = item.get("collectionName")

                        if image_url and best_image_url is None:
                            best_image_url = image_url
                        if preview_url and best_preview_url is None:
                            best_preview_url = preview_url
                        if album and best_album is None:
                            best_album = album

                        if best_image_url and best_preview_url and best_album:
                            return best_image_url, best_preview_url, best_album
    except Exception:
        pass

    fallback_image_url, fallback_preview_url, fallback_album = enrich_with_deezer(title, artist, timeout_seconds)
    return (
        best_image_url or fallback_image_url,
        best_preview_url or fallback_preview_url,
        best_album or fallback_album,
    )


def enrich_with_deezer(title: str, artist: str, timeout_seconds: float = 8.0) -> tuple[str | None, str | None, str | None]:
    query_candidates = [
        f'track:"{title}" artist:"{artist}"',
        f"{title} {artist}",
        title,
    ]
    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            for query in query_candidates:
                response = client.get("https://api.deezer.com/search", params={"q": query})
                response.raise_for_status()
                payload = response.json()

                results = payload.get("data", [])
                if not results:
                    continue

                item = results[0]
                album_info = item.get("album") or {}
                image_url = album_info.get("cover_medium")
                preview_url = item.get("preview")
                album = album_info.get("title")
                return image_url, preview_url, album
    except Exception:
        return None, None, None

    return None, None, None


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


def fetch_philippines_top_songs(
    limit: int = 100,
    timeout_seconds: float = 10.0,
    enrich_metadata: bool = True,
) -> list[SongRecord]:
    url = f"https://rss.marketingtools.apple.com/api/v2/ph/music/most-played/{limit}/songs.json"
    with httpx.Client(timeout=timeout_seconds) as client:
        response = client.get(url)
        response.raise_for_status()
        payload = response.json()

    results = ((payload.get("feed") or {}).get("results") or [])[:limit]
    chart_date = date.today()
    rows: list[SongRecord] = []

    for index, item in enumerate(results, start=1):
        title = item.get("name") or ""
        artist = item.get("artistName") or ""
        artwork_url = item.get("artworkUrl100")
        if isinstance(artwork_url, str):
            artwork_url = artwork_url.replace("100x100bb", "300x300bb")

        preview_url = None
        album = item.get("collectionName")
        if enrich_metadata:
            enriched_image_url, enriched_preview_url, enriched_album = enrich_with_itunes(
                title,
                artist,
                timeout_seconds=timeout_seconds,
                preferred_country="PH",
            )
            preview_url = enriched_preview_url
            album = album or enriched_album
            artwork_url = artwork_url or enriched_image_url

        rows.append(
            SongRecord(
                chart_date=chart_date,
                rank=index,
                title=title,
                artist=artist,
                album=album,
                image_url=artwork_url,
                preview_url=preview_url,
                weeks_on_chart=None,
                peak_position=None,
                last_week_position=None,
            )
        )

    return rows
