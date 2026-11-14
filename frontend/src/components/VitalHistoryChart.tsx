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
import { useVitalsHistoryStore } from "../store/useVitalsHistoryStore.ts";

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
  const vitalsHistory = useVitalsHistoryStore((state) => state.vitalsHistory);
  const vitalsHistoryRange = useVitalsHistoryStore((state) => state.vitalsHistoryRange);
  const isLoadingVitalsHistory = useVitalsHistoryStore((state) => state.isLoadingVitalsHistory);
  const hasVitalsHistoryError = useVitalsHistoryStore((state) => state.hasVitalsHistoryError);

  const seriesChannels = metric.SERIES.map((series) => series.CHANNEL);
  const historyPoints = vitalsHistory.filter((point) => seriesChannels.includes(point.channel));
  const pointsByTimestamp = new Map<number, { timestamp: number; [channel: string]: number }>();

  for (const point of historyPoints) {
    const timestamp = Date.parse(point.timestamp);
    const chartPoint = pointsByTimestamp.get(timestamp) ?? { timestamp };
    chartPoint[point.channel] = point.value;
    pointsByTimestamp.set(timestamp, chartPoint);
  }

  const chartData = Array.from(pointsByTimestamp.values()).sort(
    (first, second) => first.timestamp - second.timestamp,
  );
  const chartDomain: [number, number] | undefined =
    vitalsHistoryRange === null
      ? undefined
      : [Date.parse(vitalsHistoryRange.from), Date.parse(vitalsHistoryRange.to)];
  const historyMessage = isLoadingVitalsHistory
    ? "Loading history…"
    : hasVitalsHistoryError
      ? "History unavailable. Reload the page to retry."
      : "No readings in this period.";

  if (isLoadingVitalsHistory || hasVitalsHistoryError || chartData.length === 0) {
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
            domain={chartDomain}
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
              unit={historyPoints.find((point) => point.channel === series.CHANNEL)?.unit}
              type="linear"
              stroke={series.COLOR}
              strokeWidth={VITALS_CHART.STROKE_WIDTH}
              fill={series.COLOR}
              fillOpacity={VITALS_CHART.FILL_OPACITY}
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
