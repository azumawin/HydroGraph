import { useEffect } from "react";
import { ENVIRONMENT_LABELS, TELEMETRY } from "../Constants.ts";
import { useTelemetryStore } from "../store/useTelemetryStore.ts";

export const useVitalsDashboardInit = () => {
  const connectTelemetry = useTelemetryStore((state) => state.connectTelemetry);
  const hasTelemetryError = useTelemetryStore((state) => state.hasTelemetryError);
  const hasEnvironmentSelectError = useTelemetryStore((state) => state.hasEnvironmentSelectError);
  const environmentId = useTelemetryStore((state) => state.environmentId);

  const failedReadings = [
    hasTelemetryError && TELEMETRY.CONNECTION_LABEL,
    hasEnvironmentSelectError && ENVIRONMENT_LABELS.SELECT_FAILED,
  ]
    .filter(Boolean)
    .join(", ");

  useEffect(() => connectTelemetry(), [connectTelemetry]);

  return { failedReadings, environmentId };
};
