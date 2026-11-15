import { useState } from "react";
import { RULES } from "../Constants.ts";
import { useRules } from "../hooks/useRules.ts";

type RuleEditor = { mode: "new" } | { mode: "edit"; ruleId: string };

const RulesTab = () => {
  const {
    rulesState,
    pendingRuleId,
    actionError,
    changeRule,
    addRule,
    removeRule,
    clearActionError,
  } = useRules();
  const [editor, setEditor] = useState<RuleEditor | null>(null);
  const [draft, setDraft] = useState("");

  const isSaving = pendingRuleId !== null;

  const handleNewRuleClick = () => {
    clearActionError();
    setDraft(RULES.TEMPLATE);
    setEditor({ mode: "new" });
  };

  const handleEditClick = (ruleId: string, source: string) => {
    clearActionError();
    setDraft(source);
    setEditor({ mode: "edit", ruleId });
  };

  const handleEditorCancel = () => {
    clearActionError();
    setEditor(null);
  };

  const handleEditorSave = async () => {
    if (editor === null) return;
    const isSaved =
      editor.mode === "new"
        ? await addRule(draft)
        : await changeRule(editor.ruleId, { source: draft });
    if (isSaved) setEditor(null);
  };

  if (rulesState.status === "loading") {
    return <p className="vitals-dashboard-tab-message">Loading rules…</p>;
  }

  if (rulesState.status === "error") {
    return (
      <p className="vitals-dashboard-tab-message is-error" role="alert">
        {RULES.LOAD_ERROR}
      </p>
    );
  }

  return (
    <div className="vitals-dashboard-rules">
      <div className="vitals-dashboard-rules-toolbar">
        <p className="vitals-dashboard-rules-note">
          Each finding is a Python rule. Built-in rules can be turned off but not deleted.
        </p>
        <button
          type="button"
          className="vitals-dashboard-rules-button is-primary"
          onClick={handleNewRuleClick}
          disabled={editor !== null}
        >
          New rule
        </button>
      </div>
      {editor !== null && (
        <div className="vitals-dashboard-rules-editor">
          <textarea
            className="vitals-dashboard-rules-source"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            spellCheck={false}
            wrap="off"
            aria-label="Rule source"
          />
          {actionError && (
            <p className="vitals-dashboard-rules-error" role="alert">
              {actionError}
            </p>
          )}
          <div className="vitals-dashboard-rules-editor-actions">
            <button
              type="button"
              className="vitals-dashboard-rules-button"
              onClick={handleEditorCancel}
              disabled={isSaving}
            >
              Cancel
            </button>
            <button
              type="button"
              className="vitals-dashboard-rules-button is-primary"
              onClick={() => void handleEditorSave()}
              disabled={isSaving || !draft.trim()}
            >
              {editor.mode === "new" ? "Add rule" : "Save"}
            </button>
          </div>
        </div>
      )}
      {editor === null && actionError && (
        <p className="vitals-dashboard-rules-error" role="alert">
          {actionError}
        </p>
      )}
      <ul className="vitals-dashboard-rules-list">
        {rulesState.rules.map((rule) => (
          <li className="vitals-dashboard-rules-item" key={rule.id}>
            <div className="vitals-dashboard-rules-heading">
              <label className="vitals-dashboard-rules-toggle">
                <input
                  type="checkbox"
                  role="switch"
                  className="vitals-dashboard-rules-switch"
                  checked={rule.enabled}
                  disabled={pendingRuleId === rule.id}
                  onChange={(event) => void changeRule(rule.id, { enabled: event.target.checked })}
                />
                <span className="vitals-dashboard-rules-name">{rule.name}</span>
              </label>
              {rule.default ? (
                <span className="vitals-dashboard-rules-tag">Built-in</span>
              ) : (
                <span className="vitals-dashboard-rules-actions">
                  <button
                    type="button"
                    className="vitals-dashboard-rules-link"
                    onClick={() => handleEditClick(rule.id, rule.source)}
                    disabled={editor !== null}
                  >
                    Edit
                  </button>
                  <button
                    type="button"
                    className="vitals-dashboard-rules-link is-danger"
                    onClick={() => void removeRule(rule.id)}
                    disabled={pendingRuleId === rule.id}
                  >
                    Delete
                  </button>
                </span>
              )}
            </div>
            <p className="vitals-dashboard-rules-meta">
              {rule.id} ·{" "}
              {rule.channels.length === 0
                ? "not monitored"
                : `${rule.channels.length} input${rule.channels.length === 1 ? "" : "s"}`}
            </p>
            <details className="vitals-dashboard-rules-details">
              <summary className="vitals-dashboard-rules-summary">Source</summary>
              <pre className="vitals-dashboard-rules-code">{rule.source}</pre>
            </details>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default RulesTab;
