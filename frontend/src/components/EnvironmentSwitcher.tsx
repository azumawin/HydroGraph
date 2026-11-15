import { Globe } from "lucide-react";
import type { ChangeEvent } from "react";
import { ENVIRONMENT_LABELS } from "../Constants.ts";
import { environmentFacts } from "../environments.ts";
import { useTelemetryStore } from "../store/useTelemetryStore.ts";

const EnvironmentSwitcher = () => {
  const environments = useTelemetryStore((state) => state.dictionary?.environments);
  const environmentId = useTelemetryStore((state) => state.environmentId);
  const isSelectingEnvironment = useTelemetryStore((state) => state.isSelectingEnvironment);
  const selectEnvironment = useTelemetryStore((state) => state.selectEnvironment);

  const selectedEnvironment = environmentId === null ? undefined : environments?.[environmentId];

  // The same four numbers the picker's cards show, formatted the same way.
  const facts =
    selectedEnvironment === undefined
      ? []
      : environmentFacts(selectedEnvironment, ENVIRONMENT_LABELS);

  const handleEnvironmentChange = (event: ChangeEvent<HTMLSelectElement>) => {
    void selectEnvironment(event.target.value);
  };

  if (environments === undefined || environmentId === null || selectedEnvironment === undefined)
    return null;

  return (
    <div className="vitals-dashboard-environment">
      <label className="vitals-dashboard-environment-select-label">
        <Globe className="vitals-dashboard-icon" />
        <span className="vitals-dashboard-environment-select-caption">
          {ENVIRONMENT_LABELS.SELECT}
        </span>
        <select
          className="vitals-dashboard-environment-select"
          value={environmentId}
          disabled={isSelectingEnvironment}
          onChange={handleEnvironmentChange}
        >
          {Object.entries(environments).map(([id, environment]) => (
            <option key={id} value={id}>
              {environment.name}
            </option>
          ))}
        </select>
      </label>
      <dl className="vitals-dashboard-environment-facts">
        {facts.map((fact) => (
          <div className="vitals-dashboard-environment-fact" key={fact.label}>
            <dt className="vitals-dashboard-environment-fact-label">{fact.label}</dt>
            <dd className="vitals-dashboard-environment-fact-value">{fact.value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
};

export default EnvironmentSwitcher;
