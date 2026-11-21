from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.diagnostics.policy import ObjectiveNode
from app.planner.graph import learning_order

EVIDENCE_FLOOR = Decimal("0.400")
Evidence = tuple[str, str, str, Decimal] | None


@dataclass(frozen=True)
class StepDraft:
    code: str
    concept: str
    statement: str
    status: str
    evidence: str
    completion_criteria: str


def completion_criteria(statement: str) -> str:
    text = " ".join(statement.split())
    return f"Demonstrate: {text} Both the answer and the reasoning have to show it."


def is_satisfied(evidence: Evidence) -> bool:
    if evidence is None:
        return False
    understanding, answer, reasoning, confidence = evidence
    if confidence <= EVIDENCE_FLOOR:
        return False
    return understanding == "solid" and answer == "correct" and reasoning == "sound"


def plan_sequence(nodes: list[ObjectiveNode], evidence: dict[str, Evidence]) -> list[StepDraft]:
    ordered = learning_order(nodes)
    satisfied = [is_satisfied(evidence.get(node.code)) for node in ordered]
    gap = next((index for index, flag in enumerate(satisfied) if not flag), None)
    drafts: list[StepDraft] = []
    for index, node in enumerate(ordered):
        if satisfied[index]:
            status = "satisfied"
            kind = "observed"
        elif index == gap:
            status = "current"
            kind = "none"
        else:
            status = "upcoming"
            kind = "none"
        drafts.append(
            StepDraft(
                code=node.code,
                concept=node.concept.strip(),
                statement=node.statement.strip(),
                status=status,
                evidence=kind,
                completion_criteria=completion_criteria(node.statement),
            )
        )
    return drafts


def sequence_fingerprint(steps: list[StepDraft]) -> tuple[tuple[str, str, str], ...]:
    return tuple((step.code, step.status, step.evidence) for step in steps)


def plan_summary(steps: list[StepDraft]) -> str:
    current = next((step for step in steps if step.status == "current"), None)
    if current is None:
        return "Every objective already has observed evidence."
    later = sum(1 for step in steps if step.status == "upcoming")
    if later == 0:
        return f"Start at {current.code}."
    noun = "objective waits" if later == 1 else "objectives wait"
    return f"Start at {current.code}. {later} later {noun} on the prerequisite order."
