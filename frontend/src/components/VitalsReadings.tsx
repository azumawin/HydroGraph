import { VITALS_METRICS } from "../Constants.ts";
import { useTelemetryStore } from "../store/useTelemetryStore.ts";
import VitalReadingRow from "./VitalReadingRow.tsx";

const VitalsReadings = () => {
  const readings = useTelemetryStore((state) => state.readings);
  const isLoadingTelemetry = useTelemetryStore((state) => state.dictionary === null);
  const hasTelemetryError = useTelemetryStore((state) => state.hasTelemetryError);

  const metricRows = Object.values(VITALS_METRICS).map((metric) => ({
    metric,
    readings: metric.SERIES.flatMap((series) => readings[series.CHANNEL] ?? []),
  }));

  return (
    <div className="vitals-dashboard-readings">
      {metricRows.map((row) => (
        <VitalReadingRow
          key={row.metric.LABEL}
          metric={row.metric}
          readings={row.readings}
          isLoadingReading={isLoadingTelemetry && !hasTelemetryError}
          hasReadingError={hasTelemetryError && row.readings.length === 0}
        />
      ))}
    </div>
  );
};

export default VitalsReadings;
