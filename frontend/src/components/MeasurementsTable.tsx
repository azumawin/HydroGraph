import { ArrowDownRight, ArrowRight, ArrowUpRight } from "lucide-react";
import {
  MEASUREMENTS,
  VITALS_EVALUATION_LABELS,
  VITALS_FORMAT,
  formatReadingValue,
  formatTimeAgo,
} from "../Constants.ts";
import { useNow } from "../hooks/useNow.ts";
import { useTelemetryStore } from "../store/useTelemetryStore.ts";
import type { VitalHistoryPoint } from "../store/useTelemetryStore.ts";

const describeChange = (points: VitalHistoryPoint[] | undefined) => {
  if (points === undefined || points.length < 2) return undefined;
  const first = points[0];
  const change =
    Math.round((points[points.length - 1].value - first.value) * MEASUREMENTS.CHANGE_PRECISION) /
    MEASUREMENTS.CHANGE_PRECISION;
  return {
    change,
    Icon: change > 0 ? ArrowUpRight : change < 0 ? ArrowDownRight : ArrowRight,
    since: VITALS_FORMAT.MEASURED_AT.format(first.timestamp),
  };
};

const MeasurementsTable = () => {
  const channels = useTelemetryStore((state) => state.dictionary?.channels);
  const readings = useTelemetryStore((state) => state.readings);
  const history = useTelemetryStore((state) => state.history);
  const now = useNow(MEASUREMENTS.NOW_REFRESH_MS);

  const channelGroups = Object.entries(MEASUREMENTS.SCOPE_LABELS).map(([scope, label]) => ({
    scope,
    label,
    channels: Object.entries(channels ?? {}).filter(([, channel]) => channel.scope === scope),
  }));

  if (channels === undefined) {
    return <p className="vitals-dashboard-tab-message">Loading measurements…</p>;
  }

  return (
    <div className="vitals-dashboard-measurements">
      {channelGroups.map((group) => (
        <table className="vitals-dashboard-measurements-table" key={group.scope}>
          <caption className="vitals-dashboard-measurements-caption">{group.label}</caption>
          <thead>
            <tr className="vitals-dashboard-measurements-head">
              {MEASUREMENTS.COLUMNS.map((column) => (
                <th className="vitals-dashboard-measurements-heading" scope="col" key={column}>
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {group.channels.map(([channelId, channel]) => {
              const reading = readings[channelId];
              const change = describeChange(history[channelId]);
              const ChangeIcon = change?.Icon;

              return (
                <tr className="vitals-dashboard-measurements-row" key={channelId}>
                  <th className="vitals-dashboard-measurements-name" scope="row">
                    <details className="vitals-dashboard-measurements-details">
                      <summary className="vitals-dashboard-measurements-summary">
                        {channel.name}
                      </summary>
                      <p className="vitals-dashboard-measurements-explanation">
                        {channel.explanation}
                      </p>
                    </details>
                  </th>
                  <td className="vitals-dashboard-measurements-value">
                    {reading === undefined ? (
                      MEASUREMENTS.NO_READING
                    ) : (
                      <>
                        {formatReadingValue(reading.value)}{" "}
                        <span className="vitals-dashboard-measurements-unit">{reading.unit}</span>
                      </>
                    )}
                  </td>
                  <td className="vitals-dashboard-measurements-cell">
                    {reading !== undefined && (
                      <span className={`vitals-dashboard-reading-status is-${reading.evaluation}`}>
                        {VITALS_EVALUATION_LABELS[reading.evaluation]}
                      </span>
                    )}
                  </td>
                  <td className="vitals-dashboard-measurements-cell">
                    {reading !== undefined && (
                      <time dateTime={reading.measured_at}>
                        {formatTimeAgo(Date.parse(reading.measured_at), now)}
                      </time>
                    )}
                  </td>
                  <td className="vitals-dashboard-measurements-cell">
                    {change !== undefined && ChangeIcon !== undefined && (
                      <span className="vitals-dashboard-measurements-change">
                        <ChangeIcon className="vitals-dashboard-status-icon" />
                        {MEASUREMENTS.CHANGE_FORMAT.format(change.change)} since {change.since}
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      ))}
    </div>
  );
};

export default MeasurementsTable;
