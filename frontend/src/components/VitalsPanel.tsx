import { Activity } from "lucide-react";
import { VITALS_METRICS } from "../Constants.ts";
import type { VitalMetric } from "../Constants.ts";
import { useTelemetryStore } from "../store/useTelemetryStore.ts";
import VitalReadingRow from "./VitalReadingRow.tsx";
import "../assets/css/VitalsPanel.css";

const VitalsPanel = () => {
  const readings = useTelemetryStore((state) => state.readings);
  const findings = useTelemetryStore((state) => state.findings);
  const isLoadingTelemetry = useTelemetryStore((state) => state.dictionary === null);
  const hasTelemetryError = useTelemetryStore((state) => state.hasTelemetryError);

  const metricRows = Object.values(VITALS_METRICS).map((metric: VitalMetric) => ({
    metric,
    readings: metric.SERIES.flatMap((series) => readings[series.CHANNEL] ?? []),
    finding: metric.FINDING_ID === undefined ? undefined : findings[metric.FINDING_ID],
  }));

  return (
    <section className="vitals-dashboard-panel vitals-dashboard-vitals row-span-2">
      <header className="vitals-dashboard-panel-header">
        <Activity className="vitals-dashboard-icon" />
        <h2 className="vitals-dashboard-panel-title m-0">Vitals</h2>
      </header>
      <div className="vitals-dashboard-readings">
        {metricRows.map((row) => (
          <VitalReadingRow
            key={row.metric.LABEL}
            metric={row.metric}
            readings={row.readings}
            finding={row.finding}
            isLoadingReading={isLoadingTelemetry && !hasTelemetryError}
            hasReadingError={hasTelemetryError && row.readings.length === 0}
          />
        ))}
      </div>
    </section>
  );
};

export default VitalsPanel;
