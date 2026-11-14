import { useEffect } from "react";
import { VITALS_HISTORY, VITALS_READING_LABELS } from "../Constants.ts";
import { useBloodPressureStore } from "../store/useBloodPressureStore.ts";
import { useBloodSugarStore } from "../store/useBloodSugarStore.ts";
import { useBodyTemperatureStore } from "../store/useBodyTemperatureStore.ts";
import { useDailySleepHoursStore } from "../store/useDailySleepHoursStore.ts";
import { useHeartRateStore } from "../store/useHeartRateStore.ts";
import { useVitalsHistoryStore } from "../store/useVitalsHistoryStore.ts";

export const useVitalsDashboardInit = () => {
  const loadHeartRate = useHeartRateStore((state) => state.loadHeartRate);
  const loadBloodPressure = useBloodPressureStore((state) => state.loadBloodPressure);
  const loadBloodSugar = useBloodSugarStore((state) => state.loadBloodSugar);
  const loadBodyTemperature = useBodyTemperatureStore((state) => state.loadBodyTemperature);
  const loadDailySleepHours = useDailySleepHoursStore((state) => state.loadDailySleepHours);
  const loadVitalsHistory = useVitalsHistoryStore((state) => state.loadVitalsHistory);
  const hasHeartRateError = useHeartRateStore((state) => state.hasHeartRateError);
  const hasBloodPressureError = useBloodPressureStore((state) => state.hasBloodPressureError);
  const hasBloodSugarError = useBloodSugarStore((state) => state.hasBloodSugarError);
  const hasBodyTemperatureError = useBodyTemperatureStore((state) => state.hasBodyTemperatureError);
  const hasDailySleepHoursError = useDailySleepHoursStore((state) => state.hasDailySleepHoursError);
  const hasVitalsHistoryError = useVitalsHistoryStore((state) => state.hasVitalsHistoryError);

  const failedReadings = [
    hasHeartRateError && VITALS_READING_LABELS.HEART_RATE,
    hasBloodPressureError && VITALS_READING_LABELS.BLOOD_PRESSURE,
    hasBloodSugarError && VITALS_READING_LABELS.BLOOD_SUGAR,
    hasBodyTemperatureError && VITALS_READING_LABELS.BODY_TEMPERATURE,
    hasDailySleepHoursError && VITALS_READING_LABELS.DAILY_SLEEP_HOURS,
    hasVitalsHistoryError && VITALS_READING_LABELS.VITALS_HISTORY,
  ]
    .filter(Boolean)
    .join(", ");

  useEffect(() => {
    const historyEndTime = new Date();
    const historyStartTime = new Date(
      historyEndTime.getTime() - VITALS_HISTORY.DEFAULT_DURATION_MS,
    );

    void loadHeartRate();
    void loadBloodPressure();
    void loadBloodSugar();
    void loadBodyTemperature();
    void loadDailySleepHours();
    void loadVitalsHistory({
      from: historyStartTime.toISOString(),
      to: historyEndTime.toISOString(),
    });
  }, [
    loadHeartRate,
    loadBloodPressure,
    loadBloodSugar,
    loadBodyTemperature,
    loadDailySleepHours,
    loadVitalsHistory,
  ]);

  return { failedReadings };
};
