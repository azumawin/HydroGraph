import { VITALS_EVALUATION_LABELS, VITALS_FORMAT, formatReadingValue } from "../Constants.ts";
import type { VitalMetric } from "../Constants.ts";
import type { VitalReading } from "../store/useTelemetryStore.ts";
import { BODY_EVALUATION_PRIORITY } from "./model/ModelConstants.ts";
import VitalHistoryChart from "./VitalHistoryChart.tsx";

type VitalReadingRowProps = {
  metric: VitalMetric;
  readings: VitalReading[];
  isLoadingReading: boolean;
  hasReadingError: boolean;
};

const VitalReadingRow = ({
  metric,
  readings,
  isLoadingReading,
  hasReadingError,
}: VitalReadingRowProps) => {
  const orderedReadings = metric.SERIES.map((series) =>
    readings.find((reading) => reading.channel === series.CHANNEL),
  );
  const hasCompleteReading = orderedReadings.every((reading) => reading !== undefined);
  const evaluatedReading =
    hasCompleteReading && !hasReadingError && !isLoadingReading
      ? readings.toSorted(
          (first, second) =>
            BODY_EVALUATION_PRIORITY[second.evaluation] -
            BODY_EVALUATION_PRIORITY[first.evaluation],
        )[0]
      : undefined;
  const Icon = metric.ICON;
  const evaluation = evaluatedReading?.evaluation;
  const statusLabel = isLoadingReading
    ? "Loading"
    : hasReadingError
      ? "Unavailable"
      : evaluation === undefined
        ? "Not measured"
        : VITALS_EVALUATION_LABELS[evaluation];
  const measurementValue =
    isLoadingReading || hasReadingError
      ? "—"
      : orderedReadings
          .map((reading) => (reading === undefined ? "—" : formatReadingValue(reading.value)))
          .join("/");
  const measurementTimes = [
    ...new Set(
      orderedReadings.flatMap((reading) => (reading === undefined ? [] : [reading.measured_at])),
    ),
  ];

  return (
    <article className="vitals-dashboard-reading">
      <div className="vitals-dashboard-reading-summary">
        <div className="vitals-dashboard-reading-heading">
          <Icon className="vitals-dashboard-reading-icon" />
          <h3 className="vitals-dashboard-reading-label">{metric.LABEL}</h3>
        </div>
        <div className="vitals-dashboard-reading-measurement">
          <span className="vitals-dashboard-reading-value">{measurementValue}</span>
          <span className="vitals-dashboard-reading-unit">{orderedReadings[0]?.unit}</span>
        </div>
        <div className={`vitals-dashboard-reading-status is-${evaluation ?? "unmeasured"}`}>
          {statusLabel}
        </div>
      </div>
      <div className="vitals-dashboard-reading-history">
        <VitalHistoryChart metric={metric} />
        <div className="vitals-dashboard-reading-details">
          <div className="vitals-dashboard-reading-series">
            {metric.SERIES.map((series) => (
              <span className="vitals-dashboard-reading-series-item" key={series.CHANNEL}>
                <svg className="vitals-dashboard-series-swatch" viewBox="0 0 16 4">
                  <path d="M0 2H16" stroke={series.COLOR} strokeWidth="2" />
                </svg>
                {series.LABEL}
              </span>
            ))}
          </div>
          <span className="vitals-dashboard-reading-timestamp">
            {measurementTimes.map((measuredAt) => (
              <time key={measuredAt} dateTime={measuredAt}>
                {VITALS_FORMAT.MEASURED_AT.format(new Date(measuredAt))}
              </time>
            ))}
          </span>
        </div>
      </div>
    </article>
  );
};

export default VitalReadingRow;
