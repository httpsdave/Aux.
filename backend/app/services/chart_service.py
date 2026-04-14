from datetime import date, timedelta

from dateutil.relativedelta import relativedelta
from sqlalchemy import Select, delete, desc, select
from sqlalchemy.orm import Session

from app.db.models import ChartEntry
from app.schemas.chart import Period
from app.services.providers import SongRecord


def get_latest_chart_date(db: Session, source_chart: str) -> date | None:
    stmt = select(ChartEntry.chart_date).where(ChartEntry.source_chart == source_chart).order_by(desc(ChartEntry.chart_date)).limit(1)
    return db.execute(stmt).scalar_one_or_none()


def get_available_dates(db: Session, source_chart: str) -> list[date]:
    stmt = select(ChartEntry.chart_date).where(ChartEntry.source_chart == source_chart).distinct().order_by(desc(ChartEntry.chart_date))
    return list(db.execute(stmt).scalars().all())


def _get_nearest_chart_date(db: Session, source_chart: str, target: date) -> date | None:
    stmt = (
        select(ChartEntry.chart_date)
        .where(ChartEntry.source_chart == source_chart, ChartEntry.chart_date <= target)
        .order_by(desc(ChartEntry.chart_date))
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


def resolve_chart_date(db: Session, source_chart: str, requested_date: date, period: Period) -> date | None:
    if period == "week":
        target = requested_date
    elif period == "month":
        month_end = requested_date.replace(day=1) + relativedelta(months=1) - timedelta(days=1)
        target = month_end
    elif period == "year":
        target = requested_date.replace(month=12, day=31)
    else:
        target = requested_date - relativedelta(years=1)

    return _get_nearest_chart_date(db, source_chart, target)


def get_chart_entries(db: Session, source_chart: str, chart_date: date, chart_size: int) -> list[ChartEntry]:
    stmt: Select[tuple[ChartEntry]] = (
        select(ChartEntry)
        .where(ChartEntry.source_chart == source_chart, ChartEntry.chart_date == chart_date)
        .order_by(ChartEntry.rank.asc())
        .limit(chart_size)
    )
    return list(db.execute(stmt).scalars().all())


def upsert_chart_snapshot(db: Session, source_chart: str, rows: list[SongRecord]) -> None:
    if not rows:
        return

    snapshot_date = rows[0].chart_date
    db.execute(
        delete(ChartEntry).where(
            ChartEntry.source_chart == source_chart,
            ChartEntry.chart_date == snapshot_date,
        )
    )

    for row in rows:
        db.add(
            ChartEntry(
                source_chart=source_chart,
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
