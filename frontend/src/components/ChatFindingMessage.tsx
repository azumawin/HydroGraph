import { OctagonAlert, TriangleAlert } from "lucide-react";
import { FINDING_STATUS_LABELS, VITALS_FORMAT } from "../Constants.ts";

export type FindingAlert = {
  status: "warning" | "critical";
  name: string;
  triggers: string[];
  action: string;
  announcedAt: number;
};

type ChatFindingMessageProps = {
  finding: FindingAlert;
};

const ChatFindingMessage = ({ finding }: ChatFindingMessageProps) => {
  const StatusIcon = finding.status === "critical" ? OctagonAlert : TriangleAlert;

  return (
    <article
      className={`vitals-dashboard-chat-message is-assistant is-finding is-${finding.status}`}
      role={finding.status === "critical" ? "alert" : undefined}
    >
      <header className="vitals-dashboard-chat-finding-heading">
        <StatusIcon className="vitals-dashboard-chat-finding-icon" />
        <span className="vitals-dashboard-chat-finding-status">
          {FINDING_STATUS_LABELS[finding.status]}
        </span>
        <time
          className="vitals-dashboard-chat-finding-time"
          dateTime={new Date(finding.announcedAt).toISOString()}
        >
          {VITALS_FORMAT.TIME.format(finding.announcedAt)}
        </time>
      </header>
      <div className="vitals-dashboard-chat-finding-body">
        <h3 className="vitals-dashboard-chat-finding-name">{finding.name}</h3>
        {finding.triggers.length > 0 && (
          <p className="vitals-dashboard-chat-finding-triggers">{finding.triggers.join(" · ")}</p>
        )}
        <p className="vitals-dashboard-chat-finding-action">{finding.action}</p>
      </div>
    </article>
  );
};

export default ChatFindingMessage;
