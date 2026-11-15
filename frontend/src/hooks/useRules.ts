import { useEffect, useState } from "react";
import { createRule, deleteRule, fetchRules, ruleErrorDetail, updateRule } from "../api/Service.ts";
import type { FindingRule, FindingRuleChange } from "../api/Service.ts";
import { RULES } from "../Constants.ts";

type RulesState =
  | { status: "loading" }
  | { status: "error" }
  | { status: "ready"; rules: FindingRule[] };

export const useRules = () => {
  const [rulesState, setRulesState] = useState<RulesState>({ status: "loading" });
  const [pendingRuleId, setPendingRuleId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    let isCancelled = false;

    fetchRules()
      .then((rules) => {
        if (!isCancelled) setRulesState({ status: "ready", rules });
      })
      .catch(() => {
        if (!isCancelled) setRulesState({ status: "error" });
      });

    return () => {
      isCancelled = true;
    };
  }, []);

  const applyRules = (update: (rules: FindingRule[]) => FindingRule[]) => {
    setRulesState((current) =>
      current.status === "ready" ? { status: "ready", rules: update(current.rules) } : current,
    );
  };

  const runAction = async (ruleId: string, action: () => Promise<void>): Promise<boolean> => {
    setPendingRuleId(ruleId);
    setActionError(null);
    try {
      await action();
      return true;
    } catch (error) {
      setActionError(ruleErrorDetail(error) ?? RULES.FALLBACK_ERROR);
      return false;
    } finally {
      setPendingRuleId(null);
    }
  };

  const changeRule = (ruleId: string, change: FindingRuleChange) =>
    runAction(ruleId, async () => {
      const changed = await updateRule(ruleId, change);
      applyRules((rules) => rules.map((rule) => (rule.id === ruleId ? changed : rule)));
    });

  const addRule = (source: string) =>
    runAction("", async () => {
      const created = await createRule(source);
      applyRules((rules) => [...rules, created]);
    });

  const removeRule = (ruleId: string) =>
    runAction(ruleId, async () => {
      await deleteRule(ruleId);
      applyRules((rules) => rules.filter((rule) => rule.id !== ruleId));
    });

  const clearActionError = () => setActionError(null);

  return {
    rulesState,
    pendingRuleId,
    actionError,
    changeRule,
    addRule,
    removeRule,
    clearActionError,
  };
};
