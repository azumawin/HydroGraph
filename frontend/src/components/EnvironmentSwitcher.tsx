import { Globe } from "lucide-react";
import type { ChangeEvent } from "react";
import { ENVIRONMENT_FORMAT, ENVIRONMENT_LABELS } from "../Constants.ts";
import { useTelemetryStore } from "../store/useTelemetryStore.ts";

const formatCommDelay = (seconds: number) =>
  seconds < ENVIRONMENT_FORMAT.SECONDS_PER_MINUTE
    ? `${ENVIRONMENT_FORMAT.NUMBER.format(seconds)} s`
    : `${ENVIRONMENT_FORMAT.NUMBER.format(seconds / ENVIRONMENT_FORMAT.SECONDS_PER_MINUTE)} min`;

const formatDayLength = (hours: number) =>
  hours <= ENVIRONMENT_FORMAT.MAX_HOURS_SHOWN
    ? `${ENVIRONMENT_FORMAT.NUMBER.format(hours)} h`
    : `${ENVIRONMENT_FORMAT.NUMBER.format(hours / ENVIRONMENT_FORMAT.HOURS_PER_DAY)} days`;

const EnvironmentSwitcher = () => {
  const environments = useTelemetryStore((state) => state.dictionary?.environments);
  const environmentId = useTelemetryStore((state) => state.environmentId);
  const isSelectingEnvironment = useTelemetryStore((state) => state.isSelectingEnvironment);
  const selectEnvironment = useTelemetryStore((state) => state.selectEnvironment);

  const selectedEnvironment = environments?.find((environment) => environment.id === environmentId);

  const facts =
    selectedEnvironment === undefined
      ? []
      : [
          {
            LABEL: ENVIRONMENT_LABELS.GRAVITY,
            VALUE: `${ENVIRONMENT_FORMAT.NUMBER.format(selectedEnvironment.gravity_g)} g`,
          },
          {
            LABEL: ENVIRONMENT_LABELS.COMM_DELAY,
            VALUE: formatCommDelay(selectedEnvironment.comm_delay_rt_s),
          },
          {
            LABEL: ENVIRONMENT_LABELS.DAY_LENGTH,
            VALUE: formatDayLength(selectedEnvironment.day_length_h),
          },
          {
            LABEL: ENVIRONMENT_LABELS.RADIATION,
            VALUE: `${ENVIRONMENT_FORMAT.NUMBER.format(selectedEnvironment.baseline_dose_rate_usv_h)} µSv/h`,
          },
        ];

  const handleEnvironmentChange = (event: ChangeEvent<HTMLSelectElement>) => {
    void selectEnvironment(event.target.value);
  };

  if (environments === undefined || selectedEnvironment === undefined) return null;

  return (
    <div className="vitals-dashboard-environment">
      <label className="vitals-dashboard-environment-select-label">
        <Globe className="vitals-dashboard-icon" />
        <span className="vitals-dashboard-environment-select-caption">
          {ENVIRONMENT_LABELS.SELECT}
        </span>
        <select
          className="vitals-dashboard-environment-select"
          value={selectedEnvironment.id}
          disabled={isSelectingEnvironment}
          onChange={handleEnvironmentChange}
        >
          {environments.map((environment) => (
            <option key={environment.id} value={environment.id}>
              {environment.name}
            </option>
          ))}
        </select>
      </label>
      <dl className="vitals-dashboard-environment-facts">
        {facts.map((fact) => (
          <div className="vitals-dashboard-environment-fact" key={fact.LABEL}>
            <dt className="vitals-dashboard-environment-fact-label">{fact.LABEL}</dt>
            <dd className="vitals-dashboard-environment-fact-value">{fact.VALUE}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
};

export default EnvironmentSwitcher;
