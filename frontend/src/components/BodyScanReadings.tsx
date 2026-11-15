import type { ChannelInfo } from "../api/Service.ts";
import {
  BODY_SCAN_FORMAT,
  formatReadingValue,
  VITALS_EVALUATION_LABELS,
  VITALS_FORMAT,
} from "../Constants.ts";
import type { VitalReading } from "../store/useTelemetryStore.ts";

type BodyScanReadingsProps = {
  channels: [string, ChannelInfo][];
  readings: Record<string, VitalReading>;
  isLoading: boolean;
  hasTelemetryError: boolean;
};

const BodyScanReadings = ({
  channels,
  readings,
  isLoading,
  hasTelemetryError,
}: BodyScanReadingsProps) => (
  <div className="vitals-dashboard-scan-readings">
    <p className="vitals-dashboard-scan-readings-description">
      Additional readings and context used by the body scan and health findings.
    </p>
    {hasTelemetryError && (
      <p className="vitals-dashboard-scan-readings-message" role="status">
        Telemetry unavailable. Saved readings may be out of date.
      </p>
    )}
    {isLoading ? (
      <p className="vitals-dashboard-scan-readings-message" role="status">
        Loading additional readings…
      </p>
    ) : channels.length === 0 ? (
      <p className="vitals-dashboard-scan-readings-message">No additional channels available.</p>
    ) : (
      <ul className="vitals-dashboard-scan-readings-list" aria-label="Additional readings">
        {channels.map(([channel, info]) => {
          const reading = readings[channel];
          const value =
            reading === undefined
              ? "—"
              : typeof reading.value === "number"
                ? BODY_SCAN_FORMAT.VALUE.format(reading.value)
                : typeof reading.value === "boolean"
                  ? reading.value
                    ? "Yes"
                    : "No"
                  : formatReadingValue(reading.value);
          const location =
            info.body_regions.length > 0
              ? info.body_regions.map(formatReadingValue).join(", ")
              : info.scope === "environment"
                ? "Environment"
                : "Crew context";

          return (
            <li className="vitals-dashboard-scan-reading" key={channel}>
              <div className="vitals-dashboard-scan-reading-heading">
                <span className="vitals-dashboard-scan-reading-name" title={info.explanation}>
                  {info.name}
                </span>
                <span className="vitals-dashboard-scan-reading-value">
                  {value}
                  {reading !== undefined && reading.unit && (
                    <span className="vitals-dashboard-scan-reading-unit"> {reading.unit}</span>
                  )}
                </span>
              </div>
              <div className="vitals-dashboard-scan-reading-details">
                <span className="vitals-dashboard-scan-reading-location">{location}</span>
                <span
                  className={`vitals-dashboard-body-region-status is-${reading?.evaluation ?? "unmeasured"}`}
                >
                  <span className="vitals-dashboard-body-region-dot" aria-hidden="true" />
                  {reading === undefined
                    ? "No reading"
                    : VITALS_EVALUATION_LABELS[reading.evaluation]}
                </span>
              </div>
              {reading !== undefined && (
                <time className="vitals-dashboard-scan-reading-time" dateTime={reading.measured_at}>
                  {VITALS_FORMAT.MEASURED_AT.format(new Date(reading.measured_at))}
                </time>
              )}
            </li>
          );
        })}
      </ul>
    )}
  </div>
);

export default BodyScanReadings;
