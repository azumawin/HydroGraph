import { CircleAlert, Check, Minus } from "lucide-react";
import { VITALS_EVALUATION_LABELS, VITALS_FORMAT, formatReadingValue } from "../Constants.ts";
import type { VitalMetric } from "../Constants.ts";
import type { VitalReading } from "../store/useTelemetryStore.ts";
import type { TelemetryFinding } from "../api/Service.ts";
import { BODY_EVALUATION_PRIORITY } from "./model/ModelConstants.ts";
import VitalHistoryChart from "./VitalHistoryChart.tsx";

type VitalReadingRowProps = {
  metric: VitalMetric;
  readings: VitalReading[];
  finding?: TelemetryFinding;
  isLoadingReading: boolean;
  hasReadingError: boolean;
};

const VitalReadingRow = ({
  metric,
  readings,
  finding,
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
  const evaluation =
    hasCompleteReading && !hasReadingError && !isLoadingReading
      ? (finding?.status ?? evaluatedReading?.evaluation)
      : undefined;
  const sensorError = finding?.values.sensor_error;
  const isFlagged = evaluation === "warning" || evaluation === "critical";
  const StatusIcon = evaluation === undefined ? Minus : isFlagged ? CircleAlert : Check;
  const statusLabel = isLoadingReading
    ? "Loading"
    : hasReadingError
      ? "Unavailable"
      : evaluation === undefined
        ? "Not measured"
        : typeof sensorError === "string"
          ? "Sensor error"
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
          <StatusIcon className="vitals-dashboard-status-icon" />
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
                Measured {VITALS_FORMAT.MEASURED_AT.format(new Date(measuredAt))}
              </time>
            ))}
          </span>
        </div>
        {finding && (
          <div className="vitals-dashboard-reading-assessment">
            {typeof finding.values.map_mmhg === "number" && (
              <span>MAP {VITALS_FORMAT.VALUE.format(finding.values.map_mmhg)} mmHg</span>
            )}
            {typeof finding.values.shock_index === "number" && (
              <span>Shock index {finding.values.shock_index.toFixed(2)}</span>
            )}
            {isFlagged && <span>{finding.triggers.join(" · ")}</span>}
          </div>
        )}
      </div>
    </article>
  );
};

export default VitalReadingRow;
