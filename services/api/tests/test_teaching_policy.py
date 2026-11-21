import pytest

from app.teaching.draft import scripted_lesson
from app.teaching.policy import accept_lesson, fade_support, support_strategy
from app.teaching.prompts import lesson_prompt
from app.teaching.schemas import LessonDraft

HIDDEN = "Apply the inner change, then the outer change, for chain-rule.apply"


def _draft() -> LessonDraft:
    prompt = lesson_prompt(
        objective_code="chain-rule.apply",
        concept="chain rule",
        statement="Apply the chain rule.",
        primary_strategy_id="small_step_instruction",
        supporting_strategy_ids=["concrete_examples", "worked_examples"],
        fallback_strategy_id="checks_for_understanding",
    )
    return LessonDraft.model_validate(scripted_lesson(prompt))


def _accept(draft: LessonDraft) -> None:
    accept_lesson(
        draft,
        objective_code="chain-rule.apply",
        allowed_strategy_ids={
            "small_step_instruction",
            "concrete_examples",
            "worked_examples",
            "checks_for_understanding",
        },
        required_strategy_ids={"small_step_instruction", "concrete_examples", "worked_examples"},
    )


def test_scripted_lesson_executes_the_selected_strategies() -> None:
    draft = _draft()
    _accept(draft)
    kinds = [item.kind for item in draft.activities]
    assert kinds.index("check_for_understanding") < len(kinds) - 1
    explanation = next(item for item in draft.activities if item.kind == "explanation")
    assert explanation.example
    assert "chain-rule.apply" in explanation.prompt
    worked = next(item for item in draft.activities if item.kind == "worked_example")
    assert len(worked.worked_steps) >= 2
    for activity in draft.activities:
        if not activity.hints:
            continue
        assert activity.hints[0].reveals_answer is False
        assert HIDDEN.casefold() not in activity.hints[0].text.casefold()


def test_first_hint_cannot_reveal_the_answer() -> None:
    draft = _draft()
    check = next(item for item in draft.activities if item.kind == "check_for_understanding")
    check.hints[0].reveals_answer = True
    with pytest.raises(ValueError):
        _accept(draft)


def test_unselected_strategy_is_rejected() -> None:
    draft = _draft()
    draft.activities[0].strategy_id = "retrieval_practice"
    with pytest.raises(ValueError):
        _accept(draft)


def test_support_fades_one_step_and_struggle_stays_on_a_selected_strategy() -> None:
    assert fade_support("high") == "medium"
    assert fade_support("medium") == "low"
    assert fade_support("low") == "low"
    assert support_strategy(["concrete_examples", "small_step_instruction"]) == "concrete_examples"
    assert support_strategy(["checks_for_understanding", "small_step_instruction"]) == "small_step_instruction"
