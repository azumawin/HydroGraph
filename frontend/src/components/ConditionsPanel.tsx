import { Check, CircleAlert, Stethoscope } from "lucide-react";
import { CONDITIONS, FINDING_STATUS_LABELS } from "../Constants.ts";
import { useTelemetryStore } from "../store/useTelemetryStore.ts";
import "../assets/css/ConditionsPanel.css";

const ConditionsPanel = () => {
  const findingInfo = useTelemetryStore((state) => state.dictionary?.findings);
  const findings = useTelemetryStore((state) => state.findings);

  const findingList = Object.values(findings);

  return (
    <section className="vitals-dashboard-panel vitals-dashboard-conditions">
      <header className="vitals-dashboard-panel-header">
        <Stethoscope className="vitals-dashboard-icon" />
        <h2 className="vitals-dashboard-panel-title m-0">{CONDITIONS.TITLE}</h2>
        {findingList.length > 0 && (
          <span className="vitals-dashboard-conditions-count">{findingList.length} detections</span>
        )}
      </header>
      <div className="vitals-dashboard-conditions-content">
        {findingList.length === 0 && (
          <p className="vitals-dashboard-findings-empty">{CONDITIONS.EMPTY}</p>
        )}
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
                    {typeof finding.values.qsofa_score === "number" && (
                      <p className="vitals-dashboard-finding-triggers">
                        NEWS2 {String(finding.values.news2_score)} / qSOFA{" "}
                        {finding.values.qsofa_score}
                        {typeof finding.values.il6_source_channel === "string" &&
                          ` · IL-6: ${finding.values.il6_source_channel}`}
                      </p>
                    )}
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

export default ConditionsPanel;
