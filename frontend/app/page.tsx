"use client";

import { useEffect, useMemo, useState } from "react";

import ChartFilters from "@/components/chart-filters";
import SongRow from "@/components/song-row";
import { fetchChart, fetchChartDates } from "@/lib/api";
import { ChartResponse, ChartSize, Period } from "@/lib/types";

export default function Home() {
  const pageSize = 10;
  const [dates, setDates] = useState<string[]>([]);
  const [selectedDate, setSelectedDate] = useState("");
  const [chartSize, setChartSize] = useState<ChartSize>(100);
  const [period, setPeriod] = useState<Period>("week");
  const [page, setPage] = useState(1);
  const [chartData, setChartData] = useState<ChartResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadDates() {
      try {
        const response = await fetchChartDates();
        setDates(response.dates);
        if (response.dates.length > 0) {
          setSelectedDate(response.dates[0]);
        }
      } catch {
        setError("Could not load available chart dates");
      }
    }

    void loadDates();
  }, []);

  useEffect(() => {
    if (!selectedDate) {
      return;
    }

    async function loadChart() {
      try {
        setLoading(true);
        setError(null);
        const response = await fetchChart({ chartSize, period, date: selectedDate });
        setChartData(response);
      } catch {
        setError("Could not load chart data");
      } finally {
        setLoading(false);
      }
    }

    void loadChart();
  }, [chartSize, period, selectedDate]);

  useEffect(() => {
    setPage(1);
  }, [chartSize, period, selectedDate, chartData?.resolved_chart_date]);

  const headlineDate = useMemo(() => {
    if (!chartData) {
      return "";
    }
    return new Date(chartData.resolved_chart_date).toLocaleDateString("en-US", {
      month: "long",
      day: "numeric",
      year: "numeric"
    });
  }, [chartData]);

  const entries = chartData?.entries ?? [];
  const totalPages = Math.max(1, Math.ceil(entries.length / pageSize));
  const safePage = Math.min(page, totalPages);
  const pageStart = (safePage - 1) * pageSize;
  const pagedEntries = entries.slice(pageStart, pageStart + pageSize);

  const startRank = pagedEntries.length > 0 ? pageStart + 1 : 0;
  const endRank = pageStart + pagedEntries.length;

  return (
    <main className="page-shell">
      <header className="hero">
        <p className="brand">Aux.</p>
        <h1>Top Songs</h1>
        <p className="sub">A chart-first music explorer with ranking context and audio previews.</p>
      </header>

      <ChartFilters
        chartSize={chartSize}
        period={period}
        selectedDate={selectedDate}
        dates={dates}
        onChartSizeChange={setChartSize}
        onPeriodChange={setPeriod}
        onDateChange={setSelectedDate}
      />

      <section className="chart-header">
        <h2>
          {chartSize === 100 ? "Top 100" : `Top ${chartSize}`} | {period.replace("_", " ")}
        </h2>
        {headlineDate ? <p>Week of {headlineDate}</p> : null}
      </section>

      {entries.length > 0 ? (
        <section className="pagination-bar">
          <p>
            Showing {startRank}-{endRank} of {entries.length}
          </p>
          <div className="pagination-actions">
            <button
              type="button"
              onClick={() => setPage((current) => Math.max(1, current - 1))}
              disabled={safePage === 1}
              aria-label="Previous Page"
            >
              &lt;
            </button>
            <div className="page-numbers">
              {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
                <button
                  key={p}
                  type="button"
                  className={p === safePage ? "active" : ""}
                  onClick={() => setPage(p)}
                >
                  {p}
                </button>
              ))}
            </div>
            <button
              type="button"
              onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
              disabled={safePage === totalPages}
              aria-label="Next Page"
            >
              &gt;
            </button>
          </div>
        </section>
      ) : null}

      {loading ? <p className="state">Loading chart...</p> : null}
      {error ? <p className="state error">{error}</p> : null}

      <section className="chart-list">
        {pagedEntries.map((song) => (
          <SongRow key={`${chartData.resolved_chart_date}-${song.rank}`} song={song} />
        ))}
      </section>

      {entries.length > 0 ? (
        <section className="pagination-bar" style={{ marginTop: "1rem" }}>
          <p>
            Showing {startRank}-{endRank} of {entries.length}
          </p>
          <div className="pagination-actions">
            <button
              type="button"
              onClick={() => setPage((current) => Math.max(1, current - 1))}
              disabled={safePage === 1}
              aria-label="Previous Page"
            >
              &lt;
            </button>
            <div className="page-numbers">
              {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
                <button
                  key={p}
                  type="button"
                  className={p === safePage ? "active" : ""}
                  onClick={() => setPage(p)}
                >
                  {p}
                </button>
              ))}
            </div>
            <button
              type="button"
              onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
              disabled={safePage === totalPages}
              aria-label="Next Page"
            >
              &gt;
            </button>
          </div>
        </section>
      ) : null}
    </main>
  );
}
