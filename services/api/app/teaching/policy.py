from __future__ import annotations

from app.pedagogy.schemas import P0_STRATEGY_IDS
from app.teaching.schemas import ActivityDraft, LessonDraft

EXAMPLE_KINDS = {"explanation", "concrete_example", "worked_example"}
ANSWER_KINDS = {"check_for_understanding", "guided_practice", "independent_practice"}
SUPPORT_KINDS = {"explanation", "concrete_example", "worked_example"}
SUPPORT_ORDER = ("high", "medium", "low")

KIND_FOR_STRATEGY = {
    "retrieval_practice": "check_for_understanding",
    "spaced_practice": "check_for_understanding",
    "worked_examples": "worked_example",
    "guided_practice": "guided_practice",
    "scaffolding": "explanation",
    "small_step_instruction": "explanation",
    "checks_for_understanding": "check_for_understanding",
    "formative_feedback": "check_for_understanding",
    "self_explanation": "self_explanation",
    "concrete_examples": "concrete_example",
    "elaborative_interrogation": "self_explanation",
    "mastery_learning": "check_for_understanding",
}


def fade_support(level: str) -> str:
    index = SUPPORT_ORDER.index(level)
    return SUPPORT_ORDER[min(index + 1, len(SUPPORT_ORDER) - 1)]


def support_strategy(strategy_ids: list[str]) -> str:
    for strategy_id in strategy_ids:
        if KIND_FOR_STRATEGY[strategy_id] in SUPPORT_KINDS:
            return strategy_id
    return strategy_ids[0]


def accept_lesson(
    draft: LessonDraft,
    *,
    objective_code: str,
    allowed_strategy_ids: set[str],
    required_strategy_ids: set[str],
) -> None:
    if draft.objective_code != objective_code:
        raise ValueError("The lesson objective does not match the current plan step.")
    if not required_strategy_ids or not required_strategy_ids <= allowed_strategy_ids:
        raise ValueError("The lesson is missing the selected strategies.")
    seen: set[str] = set()
    check_before_end = False
    last_index = len(draft.activities) - 1
    for index, activity in enumerate(draft.activities):
        if activity.strategy_id not in P0_STRATEGY_IDS or activity.strategy_id not in allowed_strategy_ids:
            raise ValueError("An activity uses a strategy that was not selected.")
        seen.add(activity.strategy_id)
        if objective_code not in activity.prompt:
            raise ValueError("An activity is not tied to the learning objective.")
        _reject_invented_claims(activity.prompt, activity.title, activity.example, activity.expected_answer)
        for step in activity.worked_steps:
            _reject_invented_claims(step)
        if activity.kind in EXAMPLE_KINDS and not (activity.example and activity.example.strip()):
            raise ValueError("An explanation or example is missing its example.")
        if activity.kind == "worked_example" and len(activity.worked_steps) < 2:
            raise ValueError("A worked example needs its steps.")
        if activity.kind in ANSWER_KINDS:
            _require_hidden_answer(activity)
        elif activity.expected_answer:
            _require_hidden_answer(activity)
        if activity.kind == "check_for_understanding" and index < last_index:
            check_before_end = True
        if activity.kind == "independent_practice" and not check_before_end:
            raise ValueError("Independent practice follows a check.")
    if not check_before_end:
        raise ValueError("A check has to happen during the lesson.")
    if not required_strategy_ids <= seen:
        raise ValueError("A selected strategy was not executed.")


def _require_hidden_answer(activity: ActivityDraft) -> None:
    answer = (activity.expected_answer or "").strip()
    if len(answer) < 8:
        raise ValueError("A practice activity needs an answer that stays hidden.")
    if not activity.hints:
        raise ValueError("A practice activity needs a hint that is not the answer.")
    first = activity.hints[0]
    if first.reveals_answer or answer.casefold() in first.text.casefold():
        raise ValueError("The first hint reveals the answer.")


def _reject_invented_claims(*values: str | None) -> None:
    for value in values:
        if not value:
            continue
        lowered = value.casefold()
        if "doi" in lowered or "http://" in lowered or "https://" in lowered or '"' in value:
            raise ValueError("Teaching content cannot add a citation or a quotation.")
