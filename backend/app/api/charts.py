from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.schemas.chart import AvailableDatesResponse, ChartEntryOut, ChartResponse, ChartSourcesResponse, ChartSourceOut, Period
from app.services.chart_service import (
    get_available_dates,
    get_chart_entries,
    get_latest_chart_date,
    resolve_chart_date,
    upsert_chart_snapshot,
)
from app.services.providers import fetch_philippines_top_songs

router = APIRouter(prefix="/api/charts", tags=["charts"])

SUPPORTED_CHART_SOURCES: dict[str, str] = {
    "hot-100": "Top Songs Global",
    "philippines-songs": "Top Songs Philippines",
}


def resolve_chart_source(chart: str | None) -> str:
    candidate = chart or settings.chart_name
    if candidate not in SUPPORTED_CHART_SOURCES:
        allowed = ", ".join(sorted(SUPPORTED_CHART_SOURCES.keys()))
        raise HTTPException(status_code=422, detail=f"chart must be one of: {allowed}")
    return candidate


def bootstrap_source_if_missing(db: Session, source_chart: str) -> None:
    latest = get_latest_chart_date(db, source_chart)
    if latest is not None:
        return

    if source_chart == "philippines-songs":
        rows = fetch_philippines_top_songs(limit=100)
        upsert_chart_snapshot(db, source_chart, rows)


@router.get("/sources", response_model=ChartSourcesResponse)
def list_chart_sources() -> ChartSourcesResponse:
    sources = [ChartSourceOut(key=key, label=label) for key, label in SUPPORTED_CHART_SOURCES.items()]
    return ChartSourcesResponse(sources=sources)


@router.get("/dates", response_model=AvailableDatesResponse)
def list_chart_dates(
    chart: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> AvailableDatesResponse:
    source_chart = resolve_chart_source(chart)
    bootstrap_source_if_missing(db, source_chart)
    dates = get_available_dates(db, source_chart)
    return AvailableDatesResponse(source_chart=source_chart, dates=dates)


@router.get("", response_model=ChartResponse)
def read_chart(
    chart_size: int = Query(100),
    period: Period = Query("week"),
    date_value: date | None = Query(default=None, alias="date"),
    chart: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> ChartResponse:
    source_chart = resolve_chart_source(chart)
    bootstrap_source_if_missing(db, source_chart)
    allowed_sizes = {10, 25, 50, 100}
    if chart_size not in allowed_sizes:
        raise HTTPException(status_code=422, detail="chart_size must be one of 10, 25, 50, 100")

    requested_date = date_value or get_latest_chart_date(db, source_chart)
    if requested_date is None:
        raise HTTPException(status_code=404, detail="No chart data available yet")

    resolved_date = resolve_chart_date(db, source_chart, requested_date, period)
    if resolved_date is None:
        raise HTTPException(status_code=404, detail="No chart data found for selected period/date")

    rows = get_chart_entries(db, source_chart, resolved_date, chart_size)
    entries = [
        ChartEntryOut(
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

    return ChartResponse(
        source_chart=source_chart,
        period=period,
        requested_date=requested_date,
        resolved_chart_date=resolved_date,
        chart_size=chart_size,
        entries=entries,
    )
