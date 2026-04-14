from datetime import date
from typing import Literal

from pydantic import BaseModel


Period = Literal["week", "month", "year", "past_year"]


class ChartEntryOut(BaseModel):
    rank: int
    title: str
    artist: str
    album: str | None
    image_url: str | None
    preview_url: str | None
    weeks_on_chart: int | None
    peak_position: int | None
    last_week_position: int | None


class ChartResponse(BaseModel):
    source_chart: str
    period: Period
    requested_date: date
    resolved_chart_date: date
    chart_size: int
    entries: list[ChartEntryOut]


class AvailableDatesResponse(BaseModel):
    source_chart: str
    dates: list[date]


class ChartSourceOut(BaseModel):
    key: str
    label: str


class ChartSourcesResponse(BaseModel):
    sources: list[ChartSourceOut]
