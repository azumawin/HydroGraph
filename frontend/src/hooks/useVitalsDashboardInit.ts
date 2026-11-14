import { useEffect } from "react";
import { TELEMETRY } from "../Constants.ts";
import { useTelemetryStore } from "../store/useTelemetryStore.ts";

export const useVitalsDashboardInit = () => {
  const connectTelemetry = useTelemetryStore((state) => state.connectTelemetry);
  const hasTelemetryError = useTelemetryStore((state) => state.hasTelemetryError);

  const failedReadings = hasTelemetryError ? TELEMETRY.CONNECTION_LABEL : "";

  useEffect(() => connectTelemetry(), [connectTelemetry]);

  return { failedReadings };
};
