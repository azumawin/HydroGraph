import { ADVICE, FINDING_STATUS_LABELS, formatCommDelay } from "../Constants.ts";
import type { TelemetryFinding } from "../api/Service.ts";
import { useTelemetryStore } from "../store/useTelemetryStore.ts";
import { BODY_EVALUATION_PRIORITY } from "./model/ModelConstants.ts";
import ScheduledChecks from "./ScheduledChecks.tsx";

type ActiveFinding = TelemetryFinding & { status: "warning" | "critical" };

const isActiveFinding = (finding: TelemetryFinding): finding is ActiveFinding =>
  finding.status !== "nominal";

const AdviceTab = () => {
  const findings = useTelemetryStore((state) => state.findings);
  const conditions = useTelemetryStore((state) => state.dictionary?.findings);
  const environmentId = useTelemetryStore((state) => state.environmentId);
  const environments = useTelemetryStore((state) => state.dictionary?.environments);

  const environment = environmentId === null ? undefined : environments?.[environmentId];
  const evaluatedFindings = Object.values(findings);
  const activeFindings = evaluatedFindings
    .filter(isActiveFinding)
    .toSorted(
      (first, second) =>
        BODY_EVALUATION_PRIORITY[second.status] - BODY_EVALUATION_PRIORITY[first.status],
    );

  if (environment === undefined) {
    return <p className="vitals-dashboard-tab-message">Loading advice…</p>;
  }

  const roundTrip = formatCommDelay(environment.comm_delay_rt_s);
  const isGroundAvailable = environment.comm_delay_rt_s <= ADVICE.REALTIME_GROUND_MAX_RT_S;
  const escalation = isGroundAvailable ? ADVICE.ESCALATION.ground : ADVICE.ESCALATION.autonomous;

  return (
    <div className="vitals-dashboard-advice">
      <div className="vitals-dashboard-advice-contact">
        <div>
          <h3 className="vitals-dashboard-advice-contact-title">
            {isGroundAvailable ? ADVICE.GROUND_AVAILABLE_TITLE : ADVICE.AUTONOMOUS_TITLE}
          </h3>
          <p className="vitals-dashboard-advice-contact-text">
            {isGroundAvailable
              ? `${roundTrip} round trip from ${environment.name}. Call the flight surgeon about anything below.`
              : `${roundTrip} round trip from ${environment.name}. Don't wait for a reply; act on the steps below.`}
          </p>
        </div>
      </div>
      {evaluatedFindings.length === 0 && (
        <p className="vitals-dashboard-tab-message">{ADVICE.NO_FINDINGS}</p>
      )}
      {evaluatedFindings.length > 0 && activeFindings.length === 0 && (
        <p className="vitals-dashboard-tab-message">{ADVICE.ALL_CLEAR}</p>
      )}
      <ol className="vitals-dashboard-advice-list">
        {activeFindings.map((finding) => (
          <li className={`vitals-dashboard-advice-card is-${finding.status}`} key={finding.id}>
            <div className="vitals-dashboard-advice-card-heading">
              <h3 className="vitals-dashboard-advice-card-title">
                {conditions?.[finding.id]?.name ?? finding.id}
              </h3>
              <span className={`vitals-dashboard-reading-status is-${finding.status}`}>
                {FINDING_STATUS_LABELS[finding.status]}
              </span>
            </div>
            {finding.triggers.length > 0 && (
              <p className="vitals-dashboard-advice-card-triggers">{finding.triggers.join(", ")}</p>
            )}
            <p className="vitals-dashboard-advice-card-action">{finding.action}</p>
            <p className="vitals-dashboard-advice-card-escalation">{escalation[finding.status]}</p>
          </li>
        ))}
      </ol>
      <ScheduledChecks />
    </div>
  );
};

export default AdviceTab;
