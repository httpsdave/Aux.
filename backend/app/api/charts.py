from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.schemas.chart import AvailableDatesResponse, ChartEntryOut, ChartResponse, Period
from app.services.chart_service import (
    get_available_dates,
    get_chart_entries,
    get_latest_chart_date,
    resolve_chart_date,
)

router = APIRouter(prefix="/api/charts", tags=["charts"])


@router.get("/dates", response_model=AvailableDatesResponse)
def list_chart_dates(db: Session = Depends(get_db)) -> AvailableDatesResponse:
    dates = get_available_dates(db, settings.chart_name)
    return AvailableDatesResponse(source_chart=settings.chart_name, dates=dates)


@router.get("", response_model=ChartResponse)
def read_chart(
    chart_size: int = Query(100),
    period: Period = Query("week"),
    date_value: date | None = Query(default=None, alias="date"),
    db: Session = Depends(get_db),
) -> ChartResponse:
    allowed_sizes = {10, 25, 50, 100}
    if chart_size not in allowed_sizes:
        raise HTTPException(status_code=422, detail="chart_size must be one of 10, 25, 50, 100")

    requested_date = date_value or get_latest_chart_date(db, settings.chart_name)
    if requested_date is None:
        raise HTTPException(status_code=404, detail="No chart data available yet")

    resolved_date = resolve_chart_date(db, settings.chart_name, requested_date, period)
    if resolved_date is None:
        raise HTTPException(status_code=404, detail="No chart data found for selected period/date")

    rows = get_chart_entries(db, settings.chart_name, resolved_date, chart_size)
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
        source_chart=settings.chart_name,
        period=period,
        requested_date=requested_date,
        resolved_chart_date=resolved_date,
        chart_size=chart_size,
        entries=entries,
    )
