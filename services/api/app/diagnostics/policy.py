from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.core.errors import AppError
from app.diagnostics.schemas import ItemJudgment, QuestionDraft

CONFIDENCE = {
    "low": Decimal("0.300"),
    "medium": Decimal("0.600"),
    "high": Decimal("0.850"),
}


@dataclass(frozen=True)
class ObjectiveNode:
    code: str
    concept: str
    statement: str
    position: int
    prerequisite_codes: tuple[str, ...] = ()


def reject_unsupported_text(value: str) -> None:
    lowered = value.lower()
    if "doi:" in lowered or "doi.org" in lowered or "http://" in lowered or "https://" in lowered or "effect size" in lowered:
        raise AppError("malformed_output", "The model output included an unsupported citation.", 422)


def align_questions(objectives: list[ObjectiveNode], questions: list[QuestionDraft]) -> None:
    expected = {item.code for item in objectives}
    got = [item.objective_code for item in questions]
    if len(got) != len(set(got)) or set(got) != expected:
        raise AppError("malformed_output", "Diagnostic questions must match the learning objectives.", 422)
    if len(objectives) >= 2 and len({item.format for item in questions}) < 2:
        raise AppError("malformed_output", "Diagnostic questions must use more than one format.", 422)
    for item in questions:
        reject_unsupported_text(item.prompt)
        if item.format == "multiple_choice":
            cleaned = [choice.strip() for choice in (item.choices or [])]
            if len(cleaned) < 2 or len(cleaned) > 4 or any(not choice for choice in cleaned) or len(set(cleaned)) != len(cleaned):
                raise AppError("malformed_output", "A multiple-choice question needs distinct choices.", 422)
            for choice in cleaned:
                if len(choice) > 80:
                    raise AppError("malformed_output", "A multiple-choice option is too long.", 422)
                reject_unsupported_text(choice)
        elif item.choices:
            raise AppError("malformed_output", "Only multiple-choice questions include choices.", 422)


def item_is_uncertain(item: ItemJudgment) -> bool:
    return item.confidence == "low" or item.understanding == "uncertain"


def item_is_met(item: ItemJudgment) -> bool:
    return (
        not item_is_uncertain(item)
        and item.understanding == "solid"
        and item.answer_verdict == "correct"
        and item.reasoning_verdict == "sound"
    )


def needs_review(item: ItemJudgment) -> bool:
    weak_reason = item.reasoning_verdict in {"weak", "absent", "uncertain"}
    if item.answer_verdict in {"correct", "partial"} and weak_reason:
        return True
    return item_is_uncertain(item)


def knowledge_decision(item: ItemJudgment) -> str:
    if item_is_met(item):
        return "observed"
    if item.understanding == "partial" and not item_is_uncertain(item):
        return "inferred"
    return "none"


def judgment_is_consistent(item: ItemJudgment) -> bool:
    if item.understanding == "solid" and (
        item.confidence == "low"
        or item.reasoning_verdict in {"weak", "absent", "uncertain"}
        or item.answer_verdict in {"incorrect", "unanswered"}
    ):
        return False
    if item.understanding == "uncertain" and item.confidence == "high":
        return False
    hypothesis = item.misconception
    if hypothesis is None:
        return True
    if item_is_uncertain(item) and hypothesis.confidence != "low":
        return False
    return True


def evidence_supported(evidence: str, answer: str, reasoning: str) -> bool:
    snippet = evidence.strip()
    if len(snippet) < 8:
        return False
    return snippet in f"{answer}\n{reasoning}"


def align_judgments(
    objectives: list[ObjectiveNode],
    judgments: list[ItemJudgment],
    answers: dict[str, tuple[str, str]],
) -> None:
    expected = {item.code for item in objectives}
    got = [item.objective_code for item in judgments]
    if len(got) != len(set(got)) or set(got) != expected:
        raise AppError("malformed_output", "Diagnostic judgments must match the learning objectives.", 422)
    concepts = {item.code: item.concept.strip().lower() for item in objectives}
    for item in judgments:
        if not judgment_is_consistent(item):
            raise AppError("malformed_output", "The diagnostic judgment contradicted itself.", 422)
        hypothesis = item.misconception
        if hypothesis is None:
            continue
        reject_unsupported_text(hypothesis.description)
        if hypothesis.concept.strip().lower() != concepts[item.objective_code]:
            raise AppError("malformed_output", "A misconception must name the objective concept.", 422)
        answer, reasoning = answers[item.objective_code]
        if not evidence_supported(hypothesis.evidence, answer, reasoning):
            raise AppError("malformed_output", "A misconception quote was not in the learner response.", 422)


def classify_starting_point(
    objectives: list[ObjectiveNode],
    judgments: dict[str, ItemJudgment],
    observed_concepts: set[str],
) -> tuple[str, str | None, Decimal]:
    ordered = sorted(objectives, key=lambda item: (item.position, item.code))
    met: set[str] = set()
    firm_unmet: list[ObjectiveNode] = []
    uncertain = 0
    confidences: list[Decimal] = []
    for node in ordered:
        judgment = judgments.get(node.code)
        if judgment is None:
            if node.concept.strip().lower() in observed_concepts:
                met.add(node.code)
            else:
                firm_unmet.append(node)
            continue
        confidences.append(CONFIDENCE[judgment.confidence])
        if item_is_uncertain(judgment):
            uncertain += 1
            continue
        if item_is_met(judgment):
            met.add(node.code)
        else:
            firm_unmet.append(node)
    overall = min(confidences) if confidences else Decimal("0.300")
    if uncertain:
        overall = min(overall, Decimal("0.400"))
    if not firm_unmet:
        if met:
            return "partial", None, overall
        return "uncertain", None, overall
    first = firm_unmet[0]
    earlier_met = any(node.code in met for node in ordered if node.position < first.position)
    prereq_met = any(code in met for code in first.prerequisite_codes)
    if earlier_met or prereq_met:
        return "partial", first.code, overall
    return "beginner", first.code, overall


def diagnosis_summary(starting_point: str, first_code: str | None, uncertain_count: int) -> str:
    if starting_point == "beginner" and first_code:
        text = f"Beginner. The first unmet objective is {first_code}."
    elif starting_point == "partial" and first_code:
        text = f"Partial knowledge. The first unmet objective is {first_code}."
    elif starting_point == "partial":
        text = "Partial knowledge. No firm gap in this diagnosis."
    else:
        text = "The diagnosis is uncertain."
    if uncertain_count:
        label = "conclusion stays uncertain." if uncertain_count == 1 else "conclusions stay uncertain."
        text = f"{text} {uncertain_count} {label}"
    return text
