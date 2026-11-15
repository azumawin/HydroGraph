"""Tests for core.rule: custom rule source and the result contract."""

import pytest

from core.assessment import FINDINGS, evaluate_findings
from core.environments import ENVIRONMENTS
from core.rule import Rule, RuleError, compile_rule
from core.rules import DEFAULT_RULES

ISS = ENVIRONMENTS["iss_leo"]

TACHYCARDIA = """
ID = "resting_tachycardia"
NAME = "Resting tachycardia"
CHANNELS = ("heart_rate",)


def evaluate(inputs):
    bpm = inputs["latest"]["heart_rate"] * 60
    if bpm > 120:
        return {"status": "critical", "triggers": ["HR > 120 bpm"], "action": "Rest", "bpm": bpm}
    return {"status": "nominal", "triggers": [], "action": "No finding", "bpm": bpm}
"""


def test_built_in_rules_are_the_ten_findings_in_order() -> None:
    assert [rule.id for rule in DEFAULT_RULES] == list(FINDINGS)
    assert all(rule.source for rule in DEFAULT_RULES)


def test_custom_source_compiles_and_runs_alongside_the_built_ins() -> None:
    rule = compile_rule(TACHYCARDIA)
    assert (rule.id, rule.name, rule.channels) == (
        "resting_tachycardia",
        "Resting tachycardia",
        ("heart_rate",),
    )
    results = evaluate_findings({"heart_rate": 2.5}, None, None, ISS, [rule])
    assert results["resting_tachycardia"]["status"] == "critical"


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("ID = 'Bad Id'\nNAME = 'x'\nCHANNELS = ()\ndef evaluate(i): pass", "ID"),
        ("ID = 'x'\nNAME = ''\nCHANNELS = ()\ndef evaluate(i): pass", "NAME"),
        ("ID = 'x'\nNAME = 'x'\nCHANNELS = ('nope',)\ndef evaluate(i): pass", "nope"),
        (
            "ID = 'x'\nNAME = 'x'\nCHANNELS = ()\nREQUIRED = ('spo2',)\n"
            + "def evaluate(i): pass",
            "subset",
        ),
        ("ID = 'x'\nNAME = 'x'\nCHANNELS = ()", "evaluate"),
        ("def broken(:", "SyntaxError"),
        ("raise RuntimeError('boom')", "boom"),
    ],
)
def test_invalid_source_is_rejected_with_a_reason(source: str, message: str) -> None:
    with pytest.raises(RuleError, match=message):
        _ = compile_rule(source)


def test_a_result_that_breaks_the_contract_is_reported_not_returned() -> None:
    rule = compile_rule(
        "ID = 'x'\nNAME = 'x'\nCHANNELS = ()\n"
        + "def evaluate(i):\n    return {'status': 'bad', 'triggers': [], 'action': ''}"
    )
    with pytest.raises(RuleError, match="status"):
        _ = evaluate_findings({}, None, None, ISS, [rule])

    failures: list[tuple[Rule, Exception]] = []
    results = evaluate_findings(
        {},
        None,
        None,
        ISS,
        [rule],
        lambda failed, error: failures.append((failed, error)),
    )
    assert results == {}
    assert [failed.id for failed, _ in failures] == ["x"]
