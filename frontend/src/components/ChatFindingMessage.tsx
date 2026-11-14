import { OctagonAlert, TriangleAlert } from "lucide-react";
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

const ChatFindingMessage = ({ finding }: ChatFindingMessageProps) => {
  const StatusIcon = finding.status === "critical" ? OctagonAlert : TriangleAlert;

  return (
    <div
      className={`vitals-dashboard-chat-message is-assistant is-finding is-${finding.status}`}
      role={finding.status === "critical" ? "alert" : undefined}
    >
      <span className="vitals-dashboard-chat-finding-badge">
        <StatusIcon className="vitals-dashboard-chat-finding-badge-icon" />
      </span>
      <div className="vitals-dashboard-chat-finding-content">
        <p className="vitals-dashboard-chat-finding-title">
          <strong className="vitals-dashboard-chat-finding-name">{finding.name}</strong>
          <span className="vitals-dashboard-chat-finding-status">
            {FINDING_STATUS_LABELS[finding.status]}
          </span>
        </p>
        {finding.triggers.length > 0 && (
          <p className="vitals-dashboard-chat-finding-triggers">{finding.triggers.join(", ")}</p>
        )}
        <p className="vitals-dashboard-chat-finding-action">{finding.action}</p>
      </div>
    </div>
  );
};

export default ChatFindingMessage;
