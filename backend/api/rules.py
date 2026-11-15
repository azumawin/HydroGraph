"""The rule set in effect: built-in rules plus stored custom rules.

Built-in rules (``core.DEFAULT_RULES``) can be disabled but not edited or
deleted. Custom rules are Python source stored in :class:`FindingRule` and run
without a sandbox.
"""

import logging
from typing import TypedDict

from api.models import FindingRule
from core import DEFAULT_RULES, Rule, RuleError, compile_rule

logger = logging.getLogger(__name__)

BUILT_IN: dict[str, Rule] = {rule.id: rule for rule in DEFAULT_RULES}
_compiled: dict[str, Rule] = {}


class RuleEntry(TypedDict):
    rule: Rule
    default: bool
    enabled: bool


def compiled(source: str) -> Rule:
    """``compile_rule`` with a cache, since every reading re-evaluates rules.

    Raises:
        RuleError: The source is not a valid rule.
    """
    if source not in _compiled:
        _compiled[source] = compile_rule(source)
    return _compiled[source]


async def rule_entries() -> list[RuleEntry]:
    """Every rule, built-in ones first in plan order, then custom ones by age."""
    rows = {
        row.rule_id: row
        async for row in FindingRule.objects.order_by("created_at", "id")
    }
    entries: list[RuleEntry] = [
        {
            "rule": rule,
            "default": True,
            "enabled": rows[rule.id].enabled if rule.id in rows else True,
        }
        for rule in DEFAULT_RULES
    ]
    for row in rows.values():
        if row.rule_id in BUILT_IN:
            continue
        try:
            rule = compiled(row.source)
        except RuleError:
            logger.warning(
                "Stored rule %s no longer compiles", row.rule_id, exc_info=True
            )
            continue
        entries.append({"rule": rule, "default": False, "enabled": row.enabled})
    return entries


async def enabled_rules() -> list[Rule]:
    """The rules findings are evaluated with."""
    return [entry["rule"] for entry in await rule_entries() if entry["enabled"]]


def log_rule_error(rule: Rule, error: Exception) -> None:
    """Skip a rule that fails at run time instead of failing every finding."""
    logger.warning("Rule %s failed: %s", rule.id, error, exc_info=error)
