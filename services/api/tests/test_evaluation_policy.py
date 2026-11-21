from decimal import Decimal

import pytest

from app.diagnostics.schemas import ItemJudgment
from app.evaluation.policy import accept_judgment, decide, feedback


def _item(**overrides) -> ItemJudgment:
    payload = {
        "objective_code": "chain-rule.apply",
        "answer_verdict": "correct",
        "reasoning_verdict": "sound",
        "understanding": "solid",
        "confidence": "high",
        "misconception": None,
    }
    payload.update(overrides)
    return ItemJudgment.model_validate(payload)


def test_correct_answer_with_weak_reasoning_is_not_mastery() -> None:
    decision, credit = decide(_item(reasoning_verdict="weak", understanding="partial"))
    assert decision == "further_assessment"
    assert credit == Decimal("1.000")
    note = feedback("chain-rule.apply", decision, _item(reasoning_verdict="weak", understanding="partial"))
    assert "not mastery" in note


def test_partial_credit_and_ambiguous_results_do_not_master() -> None:
    decision, credit = decide(_item(answer_verdict="partial", reasoning_verdict="partial", understanding="partial", confidence="medium"))
    assert decision == "remediation"
    assert credit == Decimal("0.500")
    note = feedback("chain-rule.apply", decision, _item(answer_verdict="partial", reasoning_verdict="partial", understanding="partial"))
    assert "Partial credit" in note
    assert "remediation" in note
    review, _credit = decide(_item(understanding="uncertain", confidence="low", reasoning_verdict="uncertain"))
    assert review == "needs_review"


def test_strong_evidence_is_mastery() -> None:
    decision, credit = decide(_item())
    assert decision == "mastered"
    assert credit == Decimal("1.000")


def test_misconception_evidence_must_come_from_the_learner() -> None:
    judgment = _item(
        misconception={
            "concept": "chain rule",
            "description": "The outer step was treated as the whole derivative.",
            "evidence": "I mixed the outer step only",
            "confidence": "medium",
        }
    )
    accept_judgment(judgment, "chain-rule.apply", "I mixed the outer step only", "The rest was missing.")
    with pytest.raises(ValueError):
        accept_judgment(judgment, "chain-rule.apply", "A different answer", "No overlap here.")
