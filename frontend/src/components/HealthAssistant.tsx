import { CircleAlert, Check, MessageSquare } from "lucide-react";
import { FINDING_STATUS_LABELS } from "../Constants.ts";
import { useTelemetryStore } from "../store/useTelemetryStore.ts";
import "../assets/css/HealthAssistant.css";

const HealthAssistant = () => {
  const findingInfo = useTelemetryStore((state) => state.dictionary?.findings);
  const findings = useTelemetryStore((state) => state.findings);

  const findingList = Object.values(findings);
  const hasFindings = findingList.length > 0;

  return (
    <section className="vitals-dashboard-panel vitals-dashboard-health-assistant">
      <header className="vitals-dashboard-panel-header">
        <MessageSquare className="vitals-dashboard-icon" />
        <h2 className="vitals-dashboard-panel-title m-0">Health assistant</h2>
      </header>
      <div className="vitals-dashboard-panel-content min-h-0 flex-1 overflow-y-auto p-6">
        {!hasFindings && <p className="vitals-dashboard-findings-empty">No findings yet.</p>}
        <ul className="vitals-dashboard-findings">
          {findingList.map((finding) => {
            const level = finding.status;
            const isFlagged = level === "warning" || level === "critical";
            const StatusIcon = isFlagged ? CircleAlert : Check;

            return (
              <li className="vitals-dashboard-finding" key={finding.id}>
                <div className="vitals-dashboard-finding-heading">
                  <h3 className="vitals-dashboard-finding-name">
                    {findingInfo?.[finding.id]?.name ?? finding.id}
                  </h3>
                  <span className={`vitals-dashboard-finding-status is-${level}`}>
                    <StatusIcon className="vitals-dashboard-status-icon" />
                    {FINDING_STATUS_LABELS[level]}
                  </span>
                </div>
                {isFlagged && (
                  <>
                    <p className="vitals-dashboard-finding-triggers">
                      {finding.triggers.join(" · ")}
                    </p>
                    <p className="vitals-dashboard-finding-action">{finding.action}</p>
                  </>
                )}
              </li>
            );
          })}
        </ul>
      </div>
    </section>
  );
};

export default HealthAssistant;
