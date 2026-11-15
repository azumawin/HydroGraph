import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { CircleAlert, Check, MessageSquare, SendHorizontal } from "lucide-react";
import { assistantErrorDetail, postAssistant } from "../api/Service.ts";
import type { ChatMessage } from "../api/Service.ts";
import { ASSISTANT, FINDING_STATUS_LABELS } from "../Constants.ts";
import { useTelemetryStore } from "../store/useTelemetryStore.ts";
import "../assets/css/HealthAssistant.css";

const HealthAssistant = () => {
  const findingInfo = useTelemetryStore((state) => state.dictionary?.findings);
  const findings = useTelemetryStore((state) => state.findings);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const transcript = useRef<HTMLDivElement>(null);

  const findingList = Object.values(findings);
  const hasFindings = findingList.length > 0;

  // Pin the newest message by scrolling this panel's own region, not by asking
  // the browser to bring an element into view: that walks every scrollable
  // ancestor, and on a viewport shorter than the dashboard's minimum height it
  // scrolls the page itself, taking the header with it. An empty transcript
  // leaves the findings list where it loaded, at the top.
  useEffect(() => {
    const region = transcript.current;
    if (region === null || (messages.length === 0 && !isSending && error === null)) return;
    region.scrollTop = region.scrollHeight;
  }, [messages, isSending, error]);

  const send = async (content: string) => {
    const text = content.trim();
    if (!text || isSending) return;

    const conversation: ChatMessage[] = [...messages, { role: "user", content: text }];
    setMessages(conversation);
    setDraft("");
    setError(null);
    setIsSending(true);

    try {
      const reply = await postAssistant(conversation);
      setMessages([...conversation, { role: "assistant", content: reply }]);
    } catch (caught) {
      setError(assistantErrorDetail(caught) ?? ASSISTANT.FALLBACK_ERROR);
    } finally {
      setIsSending(false);
    }
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void send(draft);
  };

  return (
    <section className="vitals-dashboard-panel vitals-dashboard-health-assistant">
      <header className="vitals-dashboard-panel-header">
        <MessageSquare className="vitals-dashboard-icon" />
        <h2 className="vitals-dashboard-panel-title m-0">Health assistant</h2>
      </header>
      <div
        className="vitals-dashboard-panel-content vitals-dashboard-health-assistant-content"
        ref={transcript}
      >
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
        <div className="vitals-dashboard-chat" aria-live="polite">
          {messages.length === 0 && !isSending && (
            <button
              type="button"
              className="vitals-dashboard-chat-starter"
              onClick={() => void send(ASSISTANT.STARTER)}
            >
              {ASSISTANT.STARTER_LABEL}
            </button>
          )}
          {messages.map((message, index) => (
            <p className={`vitals-dashboard-chat-message is-${message.role}`} key={index}>
              {message.content}
            </p>
          ))}
          {isSending && (
            <p className="vitals-dashboard-chat-message is-assistant is-pending">
              {ASSISTANT.THINKING}
            </p>
          )}
          {error && <p className="vitals-dashboard-chat-message is-error">{error}</p>}
        </div>
      </div>
      <form className="vitals-dashboard-chat-composer" onSubmit={handleSubmit}>
        <input
          className="vitals-dashboard-chat-input"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder={ASSISTANT.PLACEHOLDER}
          aria-label={ASSISTANT.PLACEHOLDER}
          maxLength={4000}
        />
        <button
          type="submit"
          className="vitals-dashboard-chat-send"
          disabled={isSending || !draft.trim()}
          aria-label={ASSISTANT.SEND_LABEL}
        >
          <SendHorizontal className="vitals-dashboard-chat-send-icon" />
        </button>
      </form>
    </section>
  );
};

export default HealthAssistant;
