export type Period = "week" | "month" | "year" | "past_year";

export type ChartSize = 10 | 25 | 50 | 100;

export interface SongEntry {
  rank: number;
  title: string;
  artist: string;
  album: string | null;
  image_url: string | null;
  preview_url: string | null;
  weeks_on_chart: number | null;
  peak_position: number | null;
  last_week_position: number | null;
}

export interface ChartResponse {
  source_chart: string;
  period: Period;
  requested_date: string;
  resolved_chart_date: string;
  chart_size: ChartSize;
  entries: SongEntry[];
}

export interface ChartDatesResponse {
  source_chart: string;
  dates: string[];
}
