from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re

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


def _normalize_for_match(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", " ", (value or "").casefold())
    return " ".join(cleaned.split())


def _token_set(value: str) -> set[str]:
    normalized = _normalize_for_match(value)
    return {token for token in normalized.split(" ") if token}


def _dedupe_terms(terms: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for term in terms:
        normalized = " ".join(term.split())
        key = normalized.casefold()
        if not normalized or key in seen:
            continue
        seen.add(key)
        unique.append(normalized)
    return unique


def _base_artist_name(artist: str) -> str:
    primary = re.split(r"\s*(?:,|&|/| x | X | feat\.?|ft\.?)\s*", artist, maxsplit=1, flags=re.IGNORECASE)[0]
    return primary.strip() or artist


def _strip_title_noise(title: str) -> str:
    cleaned = re.sub(r"\s*\([^)]*(?:feat\.?|ft\.?|from|live|remix|version|edit)[^)]*\)", "", title, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*\[[^\]]*(?:feat\.?|ft\.?|from|live|remix|version|edit)[^\]]*\]", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*[-–:]\s*(?:feat\.?|ft\.?).*$", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip() or title


def _build_query_terms(title: str, artist: str) -> list[str]:
    title_clean = _strip_title_noise(title)
    artist_primary = _base_artist_name(artist)
    return _dedupe_terms(
        [
            f"{title} {artist}",
            f"{title} - {artist}",
            f"{title_clean} {artist_primary}",
            f"{title_clean} - {artist_primary}",
            f"{artist_primary} {title_clean}",
            title,
            title_clean,
        ]
    )


def _choose_best_match(
    title: str,
    artist: str,
    results: list[dict],
) -> list[dict]:
    """Sort API results by title/artist token overlap and keep best candidates first."""
    if not results:
        return []

    target_title_tokens = _token_set(_strip_title_noise(title))
    target_artist_tokens = _token_set(_base_artist_name(artist))

    def score(item: dict) -> tuple[float, int, int]:
        item_title = str(item.get("trackName") or "")
        item_artist = str(item.get("artistName") or "")
        item_title_tokens = _token_set(item_title)
        item_artist_tokens = _token_set(item_artist)

        title_overlap = len(target_title_tokens & item_title_tokens)
        artist_overlap = len(target_artist_tokens & item_artist_tokens)

        # Favor matches that include at least one title and artist token.
        if target_title_tokens:
            title_score = title_overlap / len(target_title_tokens)
        else:
            title_score = 0.0

        if target_artist_tokens:
            artist_score = artist_overlap / len(target_artist_tokens)
        else:
            artist_score = 0.0

        combined = (title_score * 0.7) + (artist_score * 0.3)
        return combined, title_overlap, artist_overlap

    scored = sorted(results, key=score, reverse=True)
    # Keep up to top 6 results to preserve fallback opportunities.
    return scored[:6]


def _extract_media_fields(item: dict) -> tuple[str | None, str | None, str | None]:
    image_url = item.get("artworkUrl100")
    if isinstance(image_url, str):
        image_url = image_url.replace("100x100bb", "600x600bb").replace("300x300bb", "600x600bb")

    preview_url = item.get("previewUrl")
    album = item.get("collectionName")
    return image_url, preview_url, album


def enrich_with_itunes_lookup(
    track_id: str,
    timeout_seconds: float = 8.0,
    country: str | None = None,
) -> tuple[str | None, str | None, str | None]:
    params: dict[str, str] = {"id": str(track_id), "entity": "song", "limit": "1"}
    if country:
        params["country"] = country

    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            response = client.get("https://itunes.apple.com/lookup", params=params)
            response.raise_for_status()
            payload = response.json()
    except Exception:
        return None, None, None

    results = payload.get("results") or []
    for item in results:
        wrapper_type = str(item.get("wrapperType") or "")
        kind = str(item.get("kind") or "")
        if wrapper_type == "track" or kind == "song":
            return _extract_media_fields(item)

    return None, None, None


def enrich_with_itunes(
    title: str,
    artist: str,
    timeout_seconds: float = 8.0,
    preferred_country: str | None = None,
) -> tuple[str | None, str | None, str | None]:
    query_terms = _build_query_terms(title, artist)

    country_candidates: list[str | None] = []
    if preferred_country:
        country_candidates.append(preferred_country)
    for country in ("US", "PH", "SG", "GB", "CA", "AU"):
        if country not in country_candidates:
            country_candidates.append(country)
    country_candidates.append(None)

    best_image_url = None
    best_preview_url = None
    best_album = None

    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            for country in country_candidates:
                for term in query_terms:
                    params = {"term": term, "media": "music", "entity": "song", "limit": 20}
                    if country is not None:
                        params["country"] = country

                    try:
                        response = client.get("https://itunes.apple.com/search", params=params)
                        response.raise_for_status()
                        payload = response.json()
                    except Exception:
                        # Keep trying alternate query terms/countries for transient API errors.
                        continue

                    results = _choose_best_match(title, artist, payload.get("results", []))
                    if not results:
                        continue

                    for item in results:
                        image_url, preview_url, album = _extract_media_fields(item)

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

    fallback_image_url, _, fallback_album = enrich_with_deezer(title, artist, timeout_seconds)
    return (
        best_image_url or fallback_image_url,
        best_preview_url,
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
                image_url = album_info.get("cover_xl") or album_info.get("cover_big") or album_info.get("cover_medium")
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
        track_id = str(item.get("id") or "")
        artwork_url = item.get("artworkUrl100")
        if isinstance(artwork_url, str):
            artwork_url = artwork_url.replace("100x100bb", "600x600bb").replace("300x300bb", "600x600bb")

        preview_url = None
        album = item.get("collectionName")
        if enrich_metadata:
            enriched_image_url, enriched_preview_url, enriched_album = (None, None, None)
            if track_id:
                enriched_image_url, enriched_preview_url, enriched_album = enrich_with_itunes_lookup(
                    track_id,
                    timeout_seconds=timeout_seconds,
                    country="PH",
                )

            if enriched_preview_url is None:
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
