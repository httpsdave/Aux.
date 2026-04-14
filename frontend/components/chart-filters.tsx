"use client";

import { ChartSize, Period } from "@/lib/types";

const chartSizes: ChartSize[] = [10, 25, 50, 100];
const periods: { label: string; value: Period }[] = [
  { label: "Week", value: "week" },
  { label: "Month", value: "month" },
  { label: "Year", value: "year" },
  { label: "Past Year", value: "past_year" }
];

interface ChartFiltersProps {
  chartSize: ChartSize;
  period: Period;
  selectedDate: string;
  dates: string[];
  onChartSizeChange: (value: ChartSize) => void;
  onPeriodChange: (value: Period) => void;
  onDateChange: (value: string) => void;
}

export default function ChartFilters({
  chartSize,
  period,
  selectedDate,
  dates,
  onChartSizeChange,
  onPeriodChange,
  onDateChange
}: ChartFiltersProps) {
  return (
    <section className="filters">
      <div className="filter-group">
        <label>Chart Size</label>
        <div className="select-wrapper">
          <select value={chartSize} onChange={(e) => onChartSizeChange(Number(e.target.value) as ChartSize)}>
            {chartSizes.map((size) => (
              <option key={size} value={size}>
                Top {size}
              </option>
            ))}
          </select>
          <span className="dropdown-arrow"></span>
        </div>
      </div>

      <div className="filter-group">
        <label>Period</label>
        <div className="select-wrapper">
          <select value={period} onChange={(e) => onPeriodChange(e.target.value as Period)}>
            {periods.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
          <span className="dropdown-arrow"></span>
        </div>
      </div>

      <div className="filter-group">
        <label>Chart Date</label>
        <div className="select-wrapper">
          <select value={selectedDate} onChange={(e) => onDateChange(e.target.value)}>
            {dates.map((dateValue) => (
              <option key={dateValue} value={dateValue}>
                {dateValue}
              </option>
            ))}
          </select>
          <span className="dropdown-arrow"></span>
        </div>
      </div>
    </section>
  );
}
