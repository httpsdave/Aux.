from sqlalchemy import Date, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ChartEntry(Base):
    __tablename__ = "chart_entries"
    __table_args__ = (UniqueConstraint("chart_date", "source_chart", "rank", name="uq_chart_rank"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    source_chart: Mapped[str] = mapped_column(String(64), index=True, default="hot-100")
    chart_date: Mapped[Date] = mapped_column(Date, index=True)
    rank: Mapped[int] = mapped_column(Integer, index=True)
    title: Mapped[str] = mapped_column(String(256))
    artist: Mapped[str] = mapped_column(String(256))
    album: Mapped[str | None] = mapped_column(String(256), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    preview_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    weeks_on_chart: Mapped[int | None] = mapped_column(Integer, nullable=True)
    peak_position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_week_position: Mapped[int | None] = mapped_column(Integer, nullable=True)
