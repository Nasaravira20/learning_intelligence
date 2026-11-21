from __future__ import annotations

from app.ai.errors import ProviderError
from app.teaching.policy import KIND_FOR_STRATEGY


def scripted_lesson(prompt: str) -> dict[str, object]:
    if "Task: teaching_lesson" not in prompt:
        raise ProviderError("unsupported_operation", False)
    objective = _line(prompt, "OBJECTIVE ")
    concept = _line(prompt, "CONCEPT ")
    primary = _line(prompt, "PRIMARY ")
    supporting = [
        item.strip()
        for item in _line(prompt, "SUPPORTING ").split(",")
        if item.strip() and item.strip() != "none"
    ]
    fallback = _line(prompt, "FALLBACK ")
    activities: list[dict[str, object]] = [activity_for(primary, objective, concept)]
    seen = {primary}
    for strategy_id in supporting:
        if strategy_id in seen:
            continue
        seen.add(strategy_id)
        activities.append(activity_for(strategy_id, objective, concept))
    if not any(item["kind"] == "check_for_understanding" for item in activities):
        activities.append(
            activity_for(fallback, objective, concept, kind="check_for_understanding")
        )
    activities.append(activity_for(primary, objective, concept, kind="independent_practice", support_level="low"))
    for item in activities[:-1]:
        item["support_level"] = "high"
    return {"objective_code": objective, "activities": activities}


def activity_for(
    strategy_id: str,
    objective_code: str,
    concept: str,
    *,
    kind: str | None = None,
    support_level: str = "high",
) -> dict[str, object]:
    resolved = kind or KIND_FOR_STRATEGY[strategy_id]
    example = None
    steps: list[str] = []
    expected = None
    hints = [
        {
            "text": "Stay on the first part of this objective before adding the next part.",
            "reveals_answer": False,
        }
    ]
    if resolved in {"explanation", "concrete_example", "worked_example", "self_explanation"}:
        example = f"One case of {concept} for {objective_code} uses a short input and a short output."
    if resolved == "worked_example":
        steps = [
            f"Write the first part of {objective_code}.",
            f"Write the dependent part of {objective_code}.",
        ]
    if resolved in {"check_for_understanding", "guided_practice", "independent_practice"}:
        expected = f"Apply the inner change, then the outer change, for {objective_code}"
        hints = [
            {
                "text": "Name the first part of this objective before combining later parts.",
                "reveals_answer": False,
            },
            {
                "text": "Use the earlier part before the part that depends on it.",
                "reveals_answer": False,
            },
        ]
    title = f"{resolved.replace('_', ' ')} for {objective_code}"
    return {
        "strategy_id": strategy_id,
        "kind": resolved,
        "title": title[:120],
        "prompt": f"Objective {objective_code}: work on {concept} using {strategy_id}.",
        "example": example,
        "worked_steps": steps,
        "expected_answer": expected,
        "hints": hints,
        "support_level": support_level,
    }


def _line(prompt: str, prefix: str) -> str:
    for line in prompt.splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    raise ProviderError("unknown", False)
