import { ChartDatesResponse, ChartResponse, ChartSize, ChartSourcesResponse, ChartSourceKey, Period } from "@/lib/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const DATA_MODE = process.env.NEXT_PUBLIC_DATA_MODE || "api";

function makeUrl(path: string, query?: Record<string, string>) {
  const url = new URL(path, API_BASE_URL);
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      url.searchParams.set(key, value);
    }
  }
  return url;
}

function useStaticData(): boolean {
  return DATA_MODE === "static";
}

async function fetchStaticChart(chart: ChartSourceKey): Promise<{
  source_chart: string;
  resolved_chart_date: string;
  dates: string[];
  entries: ChartResponse["entries"];
}> {
  const response = await fetch(`/data/chart_${chart}.json`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error("Unable to fetch static chart data");
  }

  return response.json();
}

export async function fetchChartSources(): Promise<ChartSourcesResponse> {
  if (useStaticData()) {
    const response = await fetch("/data/chart_sources.json", { cache: "no-store" });
    if (!response.ok) {
      throw new Error("Unable to fetch chart sources");
    }
    return response.json();
  }

  const response = await fetch(makeUrl("/api/charts/sources"), {
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error("Unable to fetch chart sources");
  }

  return response.json();
}

export async function fetchChartDates(chart: ChartSourceKey): Promise<ChartDatesResponse> {
  if (useStaticData()) {
    const snapshot = await fetchStaticChart(chart);
    return {
      source_chart: snapshot.source_chart,
      dates: snapshot.dates.length > 0 ? snapshot.dates : [snapshot.resolved_chart_date]
    };
  }

  const response = await fetch(makeUrl("/api/charts/dates", { chart }), {
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error("Unable to fetch chart dates");
  }

  return response.json();
}

export async function fetchChart(params: {
  chart: ChartSourceKey;
  chartSize: ChartSize;
  period: Period;
  date: string;
}): Promise<ChartResponse> {
  if (useStaticData()) {
    const snapshot = await fetchStaticChart(params.chart);
    const availableDates = snapshot.dates.length > 0 ? snapshot.dates : [snapshot.resolved_chart_date];
    const requestedDate = params.date || availableDates[0];
    const resolvedDate = availableDates.includes(requestedDate) ? requestedDate : availableDates[0];

    return {
      source_chart: snapshot.source_chart,
      period: params.period,
      requested_date: requestedDate,
      resolved_chart_date: resolvedDate,
      chart_size: params.chartSize,
      entries: snapshot.entries.slice(0, params.chartSize)
    };
  }

  const response = await fetch(
    makeUrl("/api/charts", {
      chart: params.chart,
      chart_size: String(params.chartSize),
      period: params.period,
      date: params.date
    }),
    { cache: "no-store" }
  );

  if (!response.ok) {
    throw new Error("Unable to fetch chart entries");
  }

  return response.json();
}
