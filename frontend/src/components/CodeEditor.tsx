import { python } from "@codemirror/lang-python";
import { HighlightStyle, syntaxHighlighting } from "@codemirror/language";
import { EditorState } from "@codemirror/state";
import { EditorView } from "@codemirror/view";
import { tags } from "@lezer/highlight";
import { basicSetup, minimalSetup } from "codemirror";
import { useEffect, useEffectEvent, useRef } from "react";

type CodeEditorProps = {
  value: string;
  label: string;
  onChange?: (value: string) => void;
};

const CODE_HIGHLIGHT = HighlightStyle.define([
  { tag: [tags.keyword, tags.controlKeyword, tags.definitionKeyword], class: "is-keyword" },
  { tag: [tags.string, tags.special(tags.string)], class: "is-string" },
  { tag: [tags.number, tags.bool, tags.null], class: "is-literal" },
  { tag: [tags.comment, tags.docString], class: "is-comment" },
  {
    tag: [tags.function(tags.variableName), tags.definition(tags.variableName)],
    class: "is-function",
  },
  { tag: tags.constant(tags.variableName), class: "is-constant" },
]);

const CodeEditor = ({ value, label, onChange }: CodeEditorProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);

  const isReadOnly = onChange === undefined;
  const handleDocChange = useEffectEvent((doc: string) => onChange?.(doc));
  const readValue = useEffectEvent(() => value);

  useEffect(() => {
    const container = containerRef.current;
    if (container === null) return;

    const view = new EditorView({
      parent: container,
      state: EditorState.create({
        doc: readValue(),
        extensions: [
          isReadOnly ? minimalSetup : basicSetup,
          python(),
          syntaxHighlighting(CODE_HIGHLIGHT),
          EditorState.readOnly.of(isReadOnly),
          EditorView.editable.of(!isReadOnly),
          EditorView.contentAttributes.of({ "aria-label": label }),
          EditorView.updateListener.of((update) => {
            if (update.docChanged) handleDocChange(update.state.doc.toString());
          }),
        ],
      }),
    });
    viewRef.current = view;

    return () => {
      view.destroy();
      viewRef.current = null;
    };
  }, [isReadOnly, label]);

  useEffect(() => {
    const view = viewRef.current;
    if (view === null) return;
    const current = view.state.doc.toString();
    if (current !== value) {
      view.dispatch({ changes: { from: 0, to: current.length, insert: value } });
    }
  }, [value]);

  return (
    <div
      ref={containerRef}
      className={`vitals-dashboard-code-editor${isReadOnly ? " is-read-only" : ""}`}
    />
  );
};

export default CodeEditor;
