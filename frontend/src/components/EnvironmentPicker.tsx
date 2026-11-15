import { ArrowRight, Globe } from "lucide-react";
import issLeo from "../assets/images/env-iss-leo.svg";
import lunarSurface from "../assets/images/env-lunar-surface.svg";
import marsSurface from "../assets/images/env-mars-surface.svg";
import marsTransit from "../assets/images/env-mars-transit.svg";
import { ENVIRONMENT_LABELS, ENVIRONMENT_PICKER } from "../Constants.ts";
import { environmentEffect, environmentFacts } from "../environments.ts";
import { useTelemetryStore } from "../store/useTelemetryStore.ts";
import "../assets/css/EnvironmentPicker.css";

// One illustration per environment in the catalog. An environment the backend
// adds later simply shows no scene rather than a broken image.
const SCENES: Record<string, string> = {
  iss_leo: issLeo,
  lunar_surface: lunarSurface,
  mars_transit: marsTransit,
  mars_surface: marsSurface,
};

type EnvironmentPickerProps = {
  // Called once the backend has accepted the choice.
  onChosen: () => void;
};

// The front door: the demo runs in one mission environment, and which one
// changes the gravity, the delay before a result arrives, the light-dark cycle
// and the dose rate a spike is graded against. Chosen per page load, so a
// reload asks again instead of resuming in a setting nobody picked.
const EnvironmentPicker = ({ onChosen }: EnvironmentPickerProps) => {
  const environments = useTelemetryStore((state) => state.dictionary?.environments);
  const environmentId = useTelemetryStore((state) => state.environmentId);
  const isSelectingEnvironment = useTelemetryStore((state) => state.isSelectingEnvironment);
  const selectEnvironment = useTelemetryStore((state) => state.selectEnvironment);

  const choose = async (id: string) => {
    if (isSelectingEnvironment) return;
    await selectEnvironment(id);
    // A failed switch leaves the picker up; the error banner says what failed.
    if (useTelemetryStore.getState().hasEnvironmentSelectError) return;
    onChosen();
  };

  return (
    <section className="vitals-dashboard-panel vitals-dashboard-environment-picker">
      <header className="vitals-dashboard-panel-header">
        <Globe className="vitals-dashboard-icon" />
        <h2 className="vitals-dashboard-panel-title m-0">{ENVIRONMENT_PICKER.TITLE}</h2>
      </header>
      <div className="vitals-dashboard-environment-picker-content">
        <p className="vitals-dashboard-environment-picker-lead">{ENVIRONMENT_PICKER.LEAD}</p>
        {environments === undefined ? (
          <p className="vitals-dashboard-chart-message" role="status">
            {ENVIRONMENT_PICKER.LOADING}
          </p>
        ) : (
          <div className="vitals-dashboard-environment-cards">
            {Object.entries(environments).map(([id, environment]) => {
              const scene = SCENES[id];

              return (
                <button
                  key={id}
                  type="button"
                  className={`vitals-dashboard-environment-card is-environment-${id}`}
                  data-environment={id}
                  disabled={isSelectingEnvironment}
                  onClick={() => void choose(id)}
                >
                  <span className="vitals-dashboard-environment-card-scene">
                    {scene !== undefined && <img src={scene} alt="" />}
                  </span>
                  <span className="vitals-dashboard-environment-card-heading">
                    <span className="vitals-dashboard-environment-card-name">
                      {environment.name}
                    </span>
                    {id === environmentId && (
                      <span className="vitals-dashboard-environment-card-badge">
                        {ENVIRONMENT_PICKER.IN_EFFECT}
                      </span>
                    )}
                  </span>
                  <span className="vitals-dashboard-environment-card-facts">
                    {environmentFacts(environment, ENVIRONMENT_LABELS).map((fact) => (
                      <span className="vitals-dashboard-environment-card-fact" key={fact.label}>
                        <span className="vitals-dashboard-environment-card-fact-label">
                          {fact.label}
                        </span>
                        <span className="vitals-dashboard-environment-card-fact-value">
                          {fact.value}
                        </span>
                      </span>
                    ))}
                  </span>
                  <span className="vitals-dashboard-environment-card-effect">
                    {environmentEffect(environment)}
                  </span>
                  <span className="vitals-dashboard-environment-card-action">
                    {ENVIRONMENT_PICKER.CHOOSE}
                    <ArrowRight className="vitals-dashboard-environment-card-action-icon" />
                  </span>
                </button>
              );
            })}
          </div>
        )}
      </div>
    </section>
  );
};

export default EnvironmentPicker;
