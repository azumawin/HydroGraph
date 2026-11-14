import { Activity, Droplet, HeartPulse, Moon, Thermometer } from "lucide-react";
import { VITALS_METRICS } from "../Constants.ts";
import { useBloodPressureStore } from "../store/useBloodPressureStore.ts";
import { useBloodSugarStore } from "../store/useBloodSugarStore.ts";
import { useBodyTemperatureStore } from "../store/useBodyTemperatureStore.ts";
import { useDailySleepHoursStore } from "../store/useDailySleepHoursStore.ts";
import { useHeartRateStore } from "../store/useHeartRateStore.ts";
import VitalReadingRow from "./VitalReadingRow.tsx";
import "../assets/css/VitalsPanel.css";

const VitalsPanel = () => {
  const heartRate = useHeartRateStore((state) => state.heartRate);
  const isLoadingHeartRate = useHeartRateStore((state) => state.isLoadingHeartRate);
  const hasHeartRateError = useHeartRateStore((state) => state.hasHeartRateError);
  const bloodPressure = useBloodPressureStore((state) => state.bloodPressure);
  const isLoadingBloodPressure = useBloodPressureStore((state) => state.isLoadingBloodPressure);
  const hasBloodPressureError = useBloodPressureStore((state) => state.hasBloodPressureError);
  const bloodSugar = useBloodSugarStore((state) => state.bloodSugar);
  const isLoadingBloodSugar = useBloodSugarStore((state) => state.isLoadingBloodSugar);
  const hasBloodSugarError = useBloodSugarStore((state) => state.hasBloodSugarError);
  const bodyTemperature = useBodyTemperatureStore((state) => state.bodyTemperature);
  const isLoadingBodyTemperature = useBodyTemperatureStore(
    (state) => state.isLoadingBodyTemperature,
  );
  const hasBodyTemperatureError = useBodyTemperatureStore((state) => state.hasBodyTemperatureError);
  const dailySleepHours = useDailySleepHoursStore((state) => state.dailySleepHours);
  const isLoadingDailySleepHours = useDailySleepHoursStore(
    (state) => state.isLoadingDailySleepHours,
  );
  const hasDailySleepHoursError = useDailySleepHoursStore((state) => state.hasDailySleepHoursError);

  return (
    <section className="vitals-dashboard-panel vitals-dashboard-vitals row-span-2">
      <header className="vitals-dashboard-panel-header">
        <Activity className="vitals-dashboard-icon" />
        <h2 className="vitals-dashboard-panel-title m-0">Vitals</h2>
      </header>
      <div className="vitals-dashboard-readings">
        <VitalReadingRow
          metric={VITALS_METRICS.HEART_RATE}
          icon={HeartPulse}
          readings={heartRate}
          isLoadingReading={isLoadingHeartRate}
          hasReadingError={hasHeartRateError}
        />
        <VitalReadingRow
          metric={VITALS_METRICS.BLOOD_PRESSURE}
          icon={Activity}
          readings={bloodPressure}
          isLoadingReading={isLoadingBloodPressure}
          hasReadingError={hasBloodPressureError}
        />
        <VitalReadingRow
          metric={VITALS_METRICS.BLOOD_SUGAR}
          icon={Droplet}
          readings={bloodSugar}
          isLoadingReading={isLoadingBloodSugar}
          hasReadingError={hasBloodSugarError}
        />
        <VitalReadingRow
          metric={VITALS_METRICS.BODY_TEMPERATURE}
          icon={Thermometer}
          readings={bodyTemperature}
          isLoadingReading={isLoadingBodyTemperature}
          hasReadingError={hasBodyTemperatureError}
        />
        <VitalReadingRow
          metric={VITALS_METRICS.DAILY_SLEEP}
          icon={Moon}
          readings={dailySleepHours}
          isLoadingReading={isLoadingDailySleepHours}
          hasReadingError={hasDailySleepHoursError}
        />
      </div>
    </section>
  );
};

export default VitalsPanel;
