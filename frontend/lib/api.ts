import { ChartDatesResponse, ChartResponse, ChartSize, ChartSourcesResponse, ChartSourceKey, Period } from "@/lib/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

function makeUrl(path: string, query?: Record<string, string>) {
  const url = new URL(path, API_BASE_URL);
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      url.searchParams.set(key, value);
    }
  }
  return url;
}

export async function fetchChartSources(): Promise<ChartSourcesResponse> {
  const response = await fetch(makeUrl("/api/charts/sources"), {
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error("Unable to fetch chart sources");
  }

  return response.json();
}

export async function fetchChartDates(chart: ChartSourceKey): Promise<ChartDatesResponse> {
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
