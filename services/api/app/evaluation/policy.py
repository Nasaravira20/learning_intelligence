from __future__ import annotations

from decimal import Decimal

from app.diagnostics.policy import evidence_supported
from app.diagnostics.schemas import ItemJudgment

CREDIT = {
    "correct": Decimal("1.000"),
    "partial": Decimal("0.500"),
    "incorrect": Decimal("0.000"),
    "unanswered": Decimal("0.000"),
}

RUBRIC = (
    "Score the answer separately from the reasoning.",
    "Partial credit applies when only part of the objective is shown.",
    "A correct answer with weak or missing reasoning is not mastery.",
    "Uncertain or thin evidence stays in review.",
    "Mastery requires a correct answer, sound reasoning, and solid understanding.",
)


def decide(judgment: ItemJudgment) -> tuple[str, Decimal]:
    credit = CREDIT[judgment.answer_verdict]
    uncertain = judgment.confidence == "low" or judgment.understanding == "uncertain" or judgment.reasoning_verdict == "uncertain"
    if uncertain:
        return "needs_review", credit
    weak_reason = judgment.reasoning_verdict in {"weak", "absent"}
    if judgment.answer_verdict == "correct" and weak_reason:
        return "further_assessment", credit
    if (
        judgment.answer_verdict == "correct"
        and judgment.reasoning_verdict == "sound"
        and judgment.understanding == "solid"
        and judgment.confidence in {"medium", "high"}
    ):
        return "mastered", Decimal("1.000")
    if judgment.answer_verdict == "partial" or judgment.understanding == "partial" or judgment.reasoning_verdict == "partial":
        return "remediation", min(credit, Decimal("0.500"))
    if judgment.answer_verdict in {"incorrect", "unanswered"} or judgment.understanding in {"none", "partial"}:
        return "remediation", Decimal("0.000")
    return "needs_review", credit


def feedback(objective_code: str, decision: str, judgment: ItemJudgment) -> str:
    if decision == "mastered":
        return f"The answer and the reasoning both show {objective_code}. That is observed evidence of this objective."
    if decision == "further_assessment":
        return (
            f"The answer for {objective_code} was counted correct, but the reasoning does not show why. "
            "A correct answer alone is not mastery. Another check is required."
        )
    if decision == "needs_review":
        return f"The evidence for {objective_code} is too thin to decide. This result stays in review and is not mastery."
    if judgment.answer_verdict == "partial" or judgment.understanding == "partial":
        return (
            f"The answer shows only part of {objective_code}. Partial credit is recorded. "
            "The missing part still has to be taught, so this is remediation rather than mastery."
        )
    return (
        f"The answer does not show {objective_code}. The missing understanding is the objective itself, "
        "so the next step is remediation rather than mastery."
    )


def accept_judgment(judgment: ItemJudgment, objective_code: str, answer: str, reasoning: str) -> None:
    if judgment.objective_code != objective_code:
        raise ValueError("The judgment does not match the objective.")
    hypothesis = judgment.misconception
    if hypothesis is None:
        return
    if not evidence_supported(hypothesis.evidence, answer, reasoning):
        raise ValueError("Misconception evidence must be copied from the learner response.")
    lowered = f"{hypothesis.description} {hypothesis.evidence}".casefold()
    if "doi" in lowered or "http://" in lowered or "https://" in lowered or '"' in hypothesis.description:
        raise ValueError("A misconception note cannot add a citation or a quotation.")
