import { useEffect, useLayoutEffect, useRef, useState } from "react";
import type { FormEvent, UIEvent } from "react";
import { ArrowDown, SendHorizontal } from "lucide-react";
import { assistantErrorDetail, postAssistant } from "../api/Service.ts";
import type { ChatMessage, TelemetryFinding } from "../api/Service.ts";
import { ASSISTANT, FINDING_STATUS_LABELS } from "../Constants.ts";
import { useTelemetryStore } from "../store/useTelemetryStore.ts";
import ChatFindingMessage from "./ChatFindingMessage.tsx";
import type { FindingAlert } from "./ChatFindingMessage.tsx";
import "../assets/css/HealthAssistant.css";

type TranscriptMessage = ChatMessage & { id: string; finding?: FindingAlert };

const formatFindingMessage = (finding: TelemetryFinding, name: string): string => {
  const lines = [`${FINDING_STATUS_LABELS[finding.status]}: ${name}`];
  if (finding.triggers.length > 0) lines.push(finding.triggers.join(" · "));
  if (finding.action.length > 0) lines.push(finding.action);
  return lines.join("\n");
};

const HealthAssistant = () => {
  const findingInfo = useTelemetryStore((state) => state.dictionary?.findings);
  const findings = useTelemetryStore((state) => state.findings);
  const [messages, setMessages] = useState<TranscriptMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [shouldFollowLatest, setShouldFollowLatest] = useState(true);
  const transcriptRef = useRef<HTMLDivElement>(null);
  const messageIdRef = useRef(0);
  const announcedFindingsRef = useRef<Record<string, string>>({});

  useEffect(() => {
    if (findingInfo === undefined) return;

    const pendingMessages: TranscriptMessage[] = [];
    for (const finding of Object.values(findings)) {
      if (finding.status === "nominal") {
        delete announcedFindingsRef.current[finding.id];
        continue;
      }

      const signature = [finding.status, ...finding.triggers, finding.action].join("\n");
      if (announcedFindingsRef.current[finding.id] === signature) continue;
      announcedFindingsRef.current[finding.id] = signature;

      const name = findingInfo[finding.id]?.name ?? finding.id;
      pendingMessages.push({
        id: `message-${messageIdRef.current++}`,
        role: "assistant",
        content: formatFindingMessage(finding, name),
        finding: {
          status: finding.status,
          name,
          triggers: finding.triggers,
          action: finding.action,
        },
      });
    }

    if (pendingMessages.length === 0) return;
    setMessages((current) => [...current, ...pendingMessages]);
  }, [findings, findingInfo]);

  useLayoutEffect(() => {
    const transcript = transcriptRef.current;
    if (transcript === null || !shouldFollowLatest) return;
    transcript.scrollTop = transcript.scrollHeight;
  }, [messages, isSending, error, shouldFollowLatest]);

  const send = async (content: string) => {
    const text = content.trim();
    if (!text || isSending) return;

    const userMessage: TranscriptMessage = {
      id: `message-${messageIdRef.current++}`,
      role: "user",
      content: text,
    };
    const conversation = [...messages, userMessage];
    setMessages((current) => [...current, userMessage]);
    setShouldFollowLatest(true);
    setDraft("");
    setError(null);
    setIsSending(true);

    try {
      const context = conversation
        .slice(-ASSISTANT.MAX_CONTEXT_MESSAGES)
        .map(({ role, content: messageContent }) => ({ role, content: messageContent }));
      const reply = await postAssistant(context);
      setMessages((current) => [
        ...current,
        { id: `message-${messageIdRef.current++}`, role: "assistant", content: reply },
      ]);
    } catch (caught) {
      setError(assistantErrorDetail(caught) ?? ASSISTANT.FALLBACK_ERROR);
    } finally {
      setIsSending(false);
    }
  };

  const handleTranscriptScroll = (event: UIEvent<HTMLDivElement>) => {
    const transcript = event.currentTarget;
    setShouldFollowLatest(
      transcript.scrollHeight - transcript.scrollTop - transcript.clientHeight <=
        ASSISTANT.SCROLL_THRESHOLD_PX,
    );
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void send(draft);
  };

  return (
    <section
      className="vitals-dashboard-panel vitals-dashboard-health-assistant"
      aria-label="Health assistant"
    >
      <div
        ref={transcriptRef}
        onScroll={handleTranscriptScroll}
        className="vitals-dashboard-panel-content min-h-0 flex-1 overflow-y-auto p-6"
      >
        <div className="vitals-dashboard-chat" aria-live="polite">
          {messages.map((message) =>
            message.finding === undefined ? (
              <p className={`vitals-dashboard-chat-message is-${message.role}`} key={message.id}>
                {message.content}
              </p>
            ) : (
              <ChatFindingMessage key={message.id} finding={message.finding} />
            ),
          )}
          {isSending && (
            <p className="vitals-dashboard-chat-message is-assistant is-pending">
              {ASSISTANT.THINKING}
            </p>
          )}
          {error && <p className="vitals-dashboard-chat-message is-error">{error}</p>}
        </div>
      </div>
      {!shouldFollowLatest && messages.length > 0 && (
        <button
          type="button"
          className="vitals-dashboard-chat-latest"
          onClick={() => setShouldFollowLatest(true)}
        >
          <ArrowDown className="vitals-dashboard-chat-latest-icon" aria-hidden="true" />
          {ASSISTANT.LATEST_LABEL}
        </button>
      )}
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
