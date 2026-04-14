"use client";

import { useEffect, useMemo, useState } from "react";

import ChartFilters from "@/components/chart-filters";
import SongRow from "@/components/song-row";
import { fetchChart, fetchChartDates, fetchChartSources } from "@/lib/api";
import { ChartResponse, ChartSize, ChartSource, ChartSourceKey, Period } from "@/lib/types";

export default function Home() {
  const pageSize = 10;
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [chartSources, setChartSources] = useState<ChartSource[]>([]);
  const [selectedChart, setSelectedChart] = useState<ChartSourceKey>("hot-100");
  const [dates, setDates] = useState<string[]>([]);
  const [selectedDate, setSelectedDate] = useState("");
  const [chartSize, setChartSize] = useState<ChartSize>(100);
  const [period, setPeriod] = useState<Period>("week");
  const [page, setPage] = useState(1);
  const [chartData, setChartData] = useState<ChartResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadChartSources() {
      try {
        const response = await fetchChartSources();
        setChartSources(response.sources);
      } catch {
        setError("Could not load chart sources");
      }
    }

    void loadChartSources();
  }, []);

  useEffect(() => {
    let isActive = true;

    setError(null);
    setDates([]);
    setSelectedDate("");
    setChartData(null);

    async function loadDates() {
      try {
        const response = await fetchChartDates(selectedChart);
        if (!isActive) {
          return;
        }

        setDates(response.dates);
        if (response.dates.length > 0) {
          setSelectedDate(response.dates[0]);
        } else {
          setSelectedDate("");
          setChartData(null);
        }
      } catch {
        if (isActive) {
          setError("Could not load available chart dates");
        }
      }
    }

    void loadDates();

    return () => {
      isActive = false;
    };
  }, [selectedChart]);

  useEffect(() => {
    if (!selectedDate) {
      return;
    }

    let isActive = true;

    async function loadChart() {
      try {
        setLoading(true);
        setError(null);
        const response = await fetchChart({ chart: selectedChart, chartSize, period, date: selectedDate });
        if (isActive) {
          setChartData(response);
        }
      } catch {
        if (isActive) {
          setError("Could not load chart data");
        }
      } finally {
        if (isActive) {
          setLoading(false);
        }
      }
    }

    void loadChart();

    return () => {
      isActive = false;
    };
  }, [selectedChart, chartSize, period, selectedDate]);

  useEffect(() => {
    setPage(1);
  }, [selectedChart, chartSize, period, selectedDate, chartData?.resolved_chart_date]);

  const currentChartLabel = useMemo(() => {
    const selected = chartSources.find((source) => source.key === selectedChart);
    return selected?.label ?? "Top Songs Global";
  }, [chartSources, selectedChart]);

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
    <>
      <header className="top-header">
        <div className="top-header-inner">
          <button
            type="button"
            className="hamburger-btn"
            aria-label="Open chart menu"
            onClick={() => setIsSidebarOpen(true)}
          >
            <span className="hamburger-line" aria-hidden="true" />
            <span className="hamburger-line" aria-hidden="true" />
            <span className="hamburger-line" aria-hidden="true" />
          </button>
        </div>
      </header>

      <main className="page-shell">
        {isSidebarOpen ? <button className="sidebar-backdrop" aria-label="Close chart menu" onClick={() => setIsSidebarOpen(false)} /> : null}

      <aside className={`sidebar ${isSidebarOpen ? "open" : ""}`}>
        <div className="sidebar-header">
          <h3>Charts</h3>
          <button type="button" className="close-sidebar" aria-label="Close" onClick={() => setIsSidebarOpen(false)}>
            x
          </button>
        </div>
        <nav className="sidebar-nav">
          {chartSources.map((source) => (
            <button
              key={source.key}
              type="button"
              className={`sidebar-link ${source.key === selectedChart ? "active" : ""}`}
              onClick={() => {
                setSelectedChart(source.key);
                setIsSidebarOpen(false);
              }}
            >
              {source.label}
            </button>
          ))}
        </nav>
      </aside>

      <header className="hero">
        <p className="brand">Aux.</p>
        <h1>Top Songs</h1>
        <p className="chart-context">{currentChartLabel}</p>
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
          <SongRow key={`${chartData?.resolved_chart_date ?? selectedDate ?? "snapshot"}-${song.rank}`} song={song} />
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
    </>
  );
}
