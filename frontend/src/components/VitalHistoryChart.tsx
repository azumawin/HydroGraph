import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { TooltipContentProps } from "recharts";
import { VITALS_CHART, VITALS_FORMAT } from "../Constants.ts";
import type { VitalMetric } from "../Constants.ts";
import { useTelemetryStore } from "../store/useTelemetryStore.ts";

type VitalHistoryChartProps = {
  metric: VitalMetric;
};

const VitalHistoryTooltip = ({ active, payload, label }: TooltipContentProps) => {
  if (!active || payload.length === 0 || typeof label !== "number") return null;

  return (
    <div className="vitals-dashboard-chart-tooltip">
      <p className="vitals-dashboard-chart-tooltip-time">
        {VITALS_FORMAT.MEASURED_AT.format(label)}
      </p>
      {payload.map((entry) => (
        <div className="vitals-dashboard-chart-tooltip-reading" key={entry.graphicalItemId}>
          <span>{entry.name}</span>
          <strong>
            {typeof entry.value === "number" ? VITALS_FORMAT.VALUE.format(entry.value) : "—"}{" "}
            {entry.unit}
          </strong>
        </div>
      ))}
    </div>
  );
};

const VitalHistoryChart = ({ metric }: VitalHistoryChartProps) => {
  const history = useTelemetryStore((state) => state.history);
  const channels = useTelemetryStore((state) => state.dictionary?.channels);
  const isLoadingTelemetry = useTelemetryStore((state) => state.dictionary === null);

  const pointsByTimestamp = new Map<number, { timestamp: number; [channel: string]: number }>();

  for (const series of metric.SERIES) {
    for (const point of history[series.CHANNEL] ?? []) {
      const chartPoint = pointsByTimestamp.get(point.timestamp) ?? { timestamp: point.timestamp };
      chartPoint[series.CHANNEL] = point.value;
      pointsByTimestamp.set(point.timestamp, chartPoint);
    }
  }

  const chartData = Array.from(pointsByTimestamp.values()).sort(
    (first, second) => first.timestamp - second.timestamp,
  );
  const historyMessage = isLoadingTelemetry ? "Loading history…" : "No readings yet.";

  if (chartData.length === 0) {
    return (
      <div className="vitals-dashboard-chart-message" role="status">
        {historyMessage}
      </div>
    );
  }

  return (
    <div
      className="vitals-dashboard-chart"
      role="img"
      aria-label={`${metric.LABEL} history. ${chartData.length} recorded timestamps.`}
    >
      <ResponsiveContainer width="100%" height="100%" minWidth={0}>
        <AreaChart data={chartData} margin={VITALS_CHART.MARGIN}>
          <CartesianGrid vertical={false} stroke="var(--color-chart-grid)" />
          <XAxis
            dataKey="timestamp"
            type="number"
            scale="time"
            domain={VITALS_CHART.TIME_DOMAIN}
            tickFormatter={VITALS_FORMAT.TIME.format.bind(VITALS_FORMAT.TIME)}
            tick={VITALS_CHART.TICK}
            axisLine={false}
            tickLine={false}
            height={VITALS_CHART.X_AXIS_HEIGHT}
            minTickGap={VITALS_CHART.MIN_TICK_GAP}
          />
          <YAxis
            domain={["auto", "auto"]}
            tickFormatter={VITALS_FORMAT.VALUE.format.bind(VITALS_FORMAT.VALUE)}
            tick={VITALS_CHART.TICK}
            tickCount={VITALS_CHART.TICK_COUNT}
            width={VITALS_CHART.Y_AXIS_WIDTH}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            content={VitalHistoryTooltip}
            isAnimationActive={false}
            cursor={{ stroke: "var(--color-divider)" }}
          />
          {metric.SERIES.map((series) => (
            <Area
              key={series.CHANNEL}
              dataKey={series.CHANNEL}
              name={series.LABEL}
              unit={channels?.[series.CHANNEL]?.display.unit}
              type="linear"
              stroke={series.COLOR}
              strokeWidth={VITALS_CHART.STROKE_WIDTH}
              fill={series.COLOR}
              fillOpacity={VITALS_CHART.FILL_OPACITY}
              connectNulls
              dot={
                chartData.length === 1 ? { r: VITALS_CHART.DOT_RADIUS, fill: series.COLOR } : false
              }
              isAnimationActive={false}
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};

export default VitalHistoryChart;
