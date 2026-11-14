import nasaLogo from "../assets/images/nasa-logo.svg";
import { useVitalsDashboardInit } from "../hooks/useVitalsDashboardInit.ts";
import BodyScan from "./BodyScan.tsx";
import EnvironmentSwitcher from "./EnvironmentSwitcher.tsx";
import HealthAssistant from "./HealthAssistant.tsx";
import VitalsPanel from "./VitalsPanel.tsx";
import VitalsDashboardBackground from "./VitalsDashboardBackground.tsx";
import VitalsDashboardErrorToast from "./VitalsDashboardErrorToast.tsx";
import "../assets/css/VitalsDashboard.css";

const VitalsDashboard = () => {
  const { failedReadings, environmentId } = useVitalsDashboardInit();

  const environmentClassName = environmentId === null ? "" : ` is-environment-${environmentId}`;

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
          <h1 className="vitals-dashboard-title m-0">
            <span className="vitals-dashboard-title-prefix">Hydro</span>Graph
          </h1>
        </div>
        <EnvironmentSwitcher />
      </header>

      <main className="vitals-dashboard-layout grid min-h-0 grid-cols-[minmax(0,3fr)_minmax(0,2fr)] grid-rows-[minmax(0,0.9fr)_minmax(0,1.1fr)] gap-4">
        <VitalsPanel />
        <BodyScan />
        <HealthAssistant />
      </main>
    </div>
  );
};

export default VitalsDashboard;
