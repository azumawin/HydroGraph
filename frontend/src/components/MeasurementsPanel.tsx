import { Check, CircleAlert, Gauge, List, Minus, User } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import {
  MEASUREMENTS,
  VITALS_EVALUATION_LABELS,
  VITALS_FORMAT,
  VITALS_MIN_SPAN_BY_CHANNEL,
  formatReadingValue,
} from "../Constants.ts";
import type { VitalMetric } from "../Constants.ts";
import type { ChannelInfo } from "../api/Service.ts";
import { groupByScope, measurementMinSpan } from "../measurements.ts";
import { useTelemetryStore } from "../store/useTelemetryStore.ts";
import type { VitalReading } from "../store/useTelemetryStore.ts";
import VitalHistoryChart from "./VitalHistoryChart.tsx";
import "../assets/css/MeasurementsPanel.css";

const SCOPE_ICONS: Record<ChannelInfo["scope"], LucideIcon> = {
  crew: User,
  environment: Gauge,
};

type MeasurementRowProps = {
  id: string;
  info: ChannelInfo;
  reading: VitalReading | undefined;
};

const MeasurementRow = ({ id, info, reading }: MeasurementRowProps) => {
  const evaluation = reading?.evaluation;
  const isFlagged = evaluation === "warning" || evaluation === "critical";
  const StatusIcon = evaluation === undefined ? Minus : isFlagged ? CircleAlert : Check;
  const Icon = SCOPE_ICONS[info.scope];
  const metric: VitalMetric = {
    LABEL: info.name,
    ICON: Icon,
    MIN_SPAN: measurementMinSpan(
      VITALS_MIN_SPAN_BY_CHANNEL[id],
      typeof reading?.value === "number" ? reading.value : undefined,
      MEASUREMENTS.FALLBACK_SPAN_FRACTION,
      MEASUREMENTS.FALLBACK_SPAN_FLOOR,
    ),
    SERIES: [{ CHANNEL: id, LABEL: info.name, COLOR: MEASUREMENTS.CHART_COLOR }],
  };

  return (
    <article className="vitals-dashboard-measurement" data-channel={id}>
      <div className="vitals-dashboard-measurement-summary">
        <div className="vitals-dashboard-reading-heading">
          <Icon className="vitals-dashboard-reading-icon" />
          <h3 className="vitals-dashboard-measurement-name">{info.name}</h3>
        </div>
        <div className="vitals-dashboard-reading-measurement">
          <span className="vitals-dashboard-measurement-value">
            {reading === undefined ? MEASUREMENTS.NO_VALUE : formatReadingValue(reading.value)}
          </span>
          <span className="vitals-dashboard-reading-unit">{info.display.unit}</span>
        </div>
        <div className={`vitals-dashboard-reading-status is-${evaluation ?? "unmeasured"}`}>
          <StatusIcon className="vitals-dashboard-status-icon" />
          {evaluation === undefined
            ? MEASUREMENTS.NOT_MEASURED
            : VITALS_EVALUATION_LABELS[evaluation]}
        </div>
      </div>
      {info.value_type === "number" && (
        <div className="vitals-dashboard-measurement-history">
          <VitalHistoryChart metric={metric} />
        </div>
      )}
      <div className="vitals-dashboard-measurement-footer">
        <p className="vitals-dashboard-measurement-explanation">{info.explanation}</p>
        {reading !== undefined && (
          <time className="vitals-dashboard-measurement-time" dateTime={reading.measured_at}>
            Measured {VITALS_FORMAT.MEASURED_AT.format(new Date(reading.measured_at))}
          </time>
        )}
      </div>
    </article>
  );
};

const MeasurementsPanel = () => {
  const dictionary = useTelemetryStore((state) => state.dictionary);
  const readings = useTelemetryStore((state) => state.readings);

  const groups =
    dictionary === null
      ? []
      : groupByScope(
          dictionary.channels,
          MEASUREMENTS.SCOPES.map((scope) => scope.ID),
        );

  return (
    <section className="vitals-dashboard-panel vitals-dashboard-measurements">
      <header className="vitals-dashboard-panel-header">
        <List className="vitals-dashboard-icon" />
        <h2 className="vitals-dashboard-panel-title m-0">{MEASUREMENTS.TITLE}</h2>
        {dictionary !== null && (
          <span className="vitals-dashboard-measurements-count">
            {Object.keys(dictionary.channels).length} channels
          </span>
        )}
      </header>
      <div className="vitals-dashboard-measurements-content">
        {dictionary === null && (
          <p className="vitals-dashboard-chart-message" role="status">
            {MEASUREMENTS.LOADING}
          </p>
        )}
        {dictionary !== null &&
          groups.map((group) => (
            <section className="vitals-dashboard-measurement-group" key={group.scope}>
              <h3 className="vitals-dashboard-measurement-group-title">
                <span>{MEASUREMENTS.SCOPES.find((scope) => scope.ID === group.scope)?.LABEL}</span>
                <span className="vitals-dashboard-measurement-group-count">
                  {group.channels.length}
                </span>
              </h3>
              {group.channels.map((id) => {
                const info = dictionary.channels[id];
                return info === undefined ? null : (
                  <MeasurementRow key={id} id={id} info={info} reading={readings[id]} />
                );
              })}
            </section>
          ))}
      </div>
    </section>
  );
};

export default MeasurementsPanel;
