import { FINDING_STATUS_LABELS } from "../Constants.ts";

export type FindingAlert = {
  status: "warning" | "critical";
  name: string;
  triggers: string[];
  action: string;
};

type ChatFindingMessageProps = {
  finding: FindingAlert;
};

const ChatFindingMessage = ({ finding }: ChatFindingMessageProps) => (
  <div
    className={`vitals-dashboard-chat-message is-assistant is-finding is-${finding.status}`}
    role={finding.status === "critical" ? "alert" : undefined}
  >
    <p className="vitals-dashboard-chat-finding-line">
      <strong className="vitals-dashboard-chat-finding-status">
        {FINDING_STATUS_LABELS[finding.status]}
      </strong>{" "}
      {finding.name}
    </p>
    {finding.triggers.length > 0 && (
      <p className="vitals-dashboard-chat-finding-triggers">{finding.triggers.join(", ")}</p>
    )}
    <p className="vitals-dashboard-chat-finding-line">{finding.action}</p>
  </div>
);

export default ChatFindingMessage;
