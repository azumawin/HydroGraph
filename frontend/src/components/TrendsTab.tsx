import { useState } from "react";
import { TRENDS } from "../Constants.ts";
import { useTelemetryStore } from "../store/useTelemetryStore.ts";
import ConditionTrends from "./ConditionTrends.tsx";

const TrendsTab = () => {
  const [periodId, setPeriodId] = useState<string>(TRENDS.PERIODS[0].ID);
  const environmentId = useTelemetryStore((state) => state.environmentId);
  const environments = useTelemetryStore((state) => state.dictionary?.environments);

  const environment = environmentId === null ? undefined : environments?.[environmentId];

  if (environmentId === null || environment === undefined) {
    return <p className="vitals-dashboard-tab-message">Loading trends…</p>;
  }

  return (
    <ConditionTrends
      key={environmentId}
      environmentName={environment.name}
      periodId={periodId}
      onPeriodChange={setPeriodId}
    />
  );
};

export default TrendsTab;
