import { useState } from "react";
import nasaLogo from "../assets/images/nasa-logo.svg";
import { DASHBOARD_TABS, MEASUREMENTS } from "../Constants.ts";
import type { DashboardTabId } from "../Constants.ts";
import { useVitalsDashboardInit } from "../hooks/useVitalsDashboardInit.ts";
import BodyScan from "./BodyScan.tsx";
import ConditionsPanel from "./ConditionsPanel.tsx";
import EnvironmentPicker from "./EnvironmentPicker.tsx";
import EnvironmentSwitcher from "./EnvironmentSwitcher.tsx";
import HealthAssistant from "./HealthAssistant.tsx";
import MeasurementsPanel from "./MeasurementsPanel.tsx";
import VitalsPanel from "./VitalsPanel.tsx";
import VitalsDashboardBackground from "./VitalsDashboardBackground.tsx";
import VitalsDashboardErrorToast from "./VitalsDashboardErrorToast.tsx";
import "../assets/css/VitalsDashboard.css";

const VitalsDashboard = () => {
  const { failedReadings, environmentId } = useVitalsDashboardInit();
  const [tab, setTab] = useState<DashboardTabId>(DASHBOARD_TABS.VITALS.ID);
  // Deliberately not persisted: a reload returns to the picker rather than
  // resuming in whichever environment the backend happens to still hold.
  const [hasChosenEnvironment, setHasChosenEnvironment] = useState(false);

  const environmentClassName = environmentId === null ? "" : ` is-environment-${environmentId}`;
  const panelId = (id: DashboardTabId) => `vitals-dashboard-tabpanel-${id}`;
  const tabId = (id: DashboardTabId) => `vitals-dashboard-tab-${id}`;

  return (
    <div
      className={`vitals-dashboard${environmentClassName} grid h-screen min-h-[720px] min-w-[1000px] grid-rows-[auto_minmax(0,1fr)] gap-4 px-5 pb-5 text-(color:--color-text)`}
    >
      <VitalsDashboardBackground environmentId={environmentId} />
      {failedReadings && (
        <VitalsDashboardErrorToast key={failedReadings} failedReadings={failedReadings} />
      )}
      <header className="vitals-dashboard-header flex min-h-16 items-center gap-6 px-6">
        <div className="vitals-dashboard-brand flex items-center gap-3">
          <img
            src={nasaLogo}
            alt="NASA"
            className="vitals-dashboard-logo h-24 w-auto shrink-0 object-contain"
          />
          <h1 className="vitals-dashboard-title m-0">HydroGraph</h1>
        </div>
        {/* Until an environment is chosen there is nothing to navigate and
            nothing to switch: the picker owns the whole content row. */}
        {hasChosenEnvironment && (
          <>
            <nav
              className="vitals-dashboard-tabs"
              role="tablist"
              aria-label={MEASUREMENTS.TABS_LABEL}
            >
              {Object.values(DASHBOARD_TABS).map((option) => (
                <button
                  key={option.ID}
                  id={tabId(option.ID)}
                  className="vitals-dashboard-tab"
                  type="button"
                  role="tab"
                  aria-selected={tab === option.ID}
                  aria-controls={panelId(option.ID)}
                  onClick={() => setTab(option.ID)}
                >
                  {option.LABEL}
                </button>
              ))}
            </nav>
            <EnvironmentSwitcher />
          </>
        )}
      </header>

      {!hasChosenEnvironment && (
        <main className="vitals-dashboard-layout grid min-h-0 gap-4">
          <EnvironmentPicker onChosen={() => setHasChosenEnvironment(true)} />
        </main>
      )}

      {/* One view is mounted at a time: the store holds every reading and
          finding, so switching back costs nothing, and the body scan's 3D
          canvas is not kept alive behind the other tabs. */}
      {hasChosenEnvironment && tab === DASHBOARD_TABS.VITALS.ID && (
        <main
          id={panelId(DASHBOARD_TABS.VITALS.ID)}
          role="tabpanel"
          aria-labelledby={tabId(DASHBOARD_TABS.VITALS.ID)}
          className="vitals-dashboard-layout grid min-h-0 grid-cols-[minmax(0,3fr)_minmax(0,2fr)] grid-rows-[minmax(0,0.9fr)_minmax(0,1.1fr)] gap-4"
        >
          <VitalsPanel />
          <BodyScan />
          <HealthAssistant />
        </main>
      )}
      {hasChosenEnvironment && tab === DASHBOARD_TABS.CONDITIONS.ID && (
        <main
          id={panelId(DASHBOARD_TABS.CONDITIONS.ID)}
          role="tabpanel"
          aria-labelledby={tabId(DASHBOARD_TABS.CONDITIONS.ID)}
          className="vitals-dashboard-layout grid min-h-0 gap-4"
        >
          <ConditionsPanel />
        </main>
      )}
      {hasChosenEnvironment && tab === DASHBOARD_TABS.MEASUREMENTS.ID && (
        <main
          id={panelId(DASHBOARD_TABS.MEASUREMENTS.ID)}
          role="tabpanel"
          aria-labelledby={tabId(DASHBOARD_TABS.MEASUREMENTS.ID)}
          className="vitals-dashboard-layout grid min-h-0 gap-4"
        >
          <MeasurementsPanel />
        </main>
      )}
    </div>
  );
};

export default VitalsDashboard;
