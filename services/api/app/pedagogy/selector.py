from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, Field

from app.pedagogy.registry import PedagogyRegistry, production_selectable_strategy_ids
from app.pedagogy.schemas import StrategyRecord

POLICY_VERSION = "2026.11.21"
CONTROLS_TEACHING = False

LearnerLevel = Literal["beginner", "partial", "proficient"]
SessionStage = Literal["initial_teaching", "practice", "revision", "assessment"]
PerformanceResult = Literal["correct", "incorrect", "partial", "forgotten"]
ReasoningQuality = Literal["sound", "weak", "missing"]
OutcomeResult = Literal["succeeded", "failed"]

_CANDIDATES: dict[str, tuple[str, ...]] = {
    "repeated_failure": (
        "formative_feedback",
        "small_step_instruction",
        "checks_for_understanding",
        "concrete_examples",
    ),
    "forgets_earlier_content": (
        "retrieval_practice",
        "spaced_practice",
        "checks_for_understanding",
    ),
    "strong_performance": (
        "checks_for_understanding",
        "mastery_learning",
        "retrieval_practice",
    ),
    "missing_prerequisites": (
        "small_step_instruction",
        "concrete_examples",
        "worked_examples",
        "guided_practice",
    ),
    "correct_answer_weak_reasoning": (
        "self_explanation",
        "elaborative_interrogation",
        "checks_for_understanding",
    ),
    "confuses_similar_concepts": (
        "concrete_examples",
        "self_explanation",
        "checks_for_understanding",
    ),
    "partial_understanding": (
        "self_explanation",
        "concrete_examples",
        "guided_practice",
    ),
    "ready_for_a_check": (
        "checks_for_understanding",
        "formative_feedback",
    ),
}
_SUPPORT_REDUCED = frozenset({"scaffolding", "worked_examples", "guided_practice"})
_FALLBACK_ORDER = (
    "checks_for_understanding",
    "small_step_instruction",
    "formative_feedback",
    "concrete_examples",
)


class PerformanceEvent(BaseModel):
    concept: str = Field(min_length=1)
    result: PerformanceResult
    reasoning: ReasoningQuality = "missing"


class StrategyOutcome(BaseModel):
    strategy_id: str = Field(min_length=1)
    result: OutcomeResult


class SelectorInput(BaseModel):
    topic: str = Field(min_length=1)
    learning_objective: str = Field(min_length=1)
    learner_level: LearnerLevel
    prior_knowledge: list[str] = Field(default_factory=list)
    knowledge_gaps: list[str] = Field(default_factory=list)
    misconceptions: list[str] = Field(default_factory=list)
    recent_performance: list[PerformanceEvent] = Field(default_factory=list)
    session_stage: SessionStage
    time_available_minutes: int = Field(ge=1, le=180)
    previous_strategy_outcomes: list[StrategyOutcome] = Field(default_factory=list)


class RejectedStrategy(BaseModel):
    strategy_id: str
    reason: str


class SelectionDecision(BaseModel):
    primary_strategy: str | None
    supporting_strategies: list[str]
    sequence: list[str]
    success_signals: list[str]
    fallback_strategy: str | None
    rationale: str
    registry_version: str
    policy_version: str
    situation: str
    controls_teaching: bool
    production_primary_strategy: str | None
    rejected: list[RejectedStrategy]
    input_fingerprint: str


def select(
    context: SelectorInput,
    registry: PedagogyRegistry,
    *,
    production: bool,
) -> SelectionDecision:
    """Choose registered strategies. This phase never starts teaching."""
    known = {item.strategy_id: item for item in registry.strategies}
    situation = detect_situation(context)
    active = active_conditions(context)
    failed = {item.strategy_id for item in context.previous_strategy_outcomes if item.result == "failed"}
    eligible: dict[str, str] = {}
    rejected: list[RejectedStrategy] = []
    for strategy_id, strategy in known.items():
        allowed, reason = _eligibility(strategy, active)
        if allowed:
            eligible[strategy_id] = reason
        else:
            rejected.append(RejectedStrategy(strategy_id=strategy_id, reason=reason))

    eligible_ids = set(eligible)
    ranked = _rank(situation, eligible, failed, known)
    for strategy_id in ranked:
        eligible.pop(strategy_id, None)
    for strategy_id in eligible:
        rejected.append(RejectedStrategy(strategy_id=strategy_id, reason="not_ranked_for_situation"))

    primary = ranked[0] if ranked else None
    supporting = ranked[1:4]
    fallback = _fallback(primary, ranked, eligible_ids)
    sequence = _sequence(primary, supporting, known)
    signals = list(known[primary].assessment_signals) if primary is not None else []
    production_allowed = set(production_selectable_strategy_ids(registry))
    production_primary = primary if production and primary in production_allowed else None
    if not production:
        production_primary = None
    rationale = _rationale(context, situation, primary, failed, production_primary)
    return SelectionDecision(
        primary_strategy=primary,
        supporting_strategies=supporting,
        sequence=sequence,
        success_signals=signals,
        fallback_strategy=fallback,
        rationale=rationale,
        registry_version=registry.manifest.registry_version,
        policy_version=POLICY_VERSION,
        situation=situation,
        controls_teaching=CONTROLS_TEACHING,
        production_primary_strategy=production_primary,
        rejected=sorted(rejected, key=lambda item: item.strategy_id),
        input_fingerprint=input_fingerprint(context),
    )


def detect_situation(context: SelectorInput) -> str:
    failure_count = sum(item.result == "incorrect" for item in context.recent_performance)
    failure_count += sum(item.result == "failed" for item in context.previous_strategy_outcomes)
    if failure_count >= 2:
        return "repeated_failure"
    forgot = any(item.result == "forgotten" for item in context.recent_performance)
    if forgot or (context.session_stage == "revision" and context.prior_knowledge and _gaps(context)):
        return "forgets_earlier_content"
    if _strong(context):
        return "strong_performance"
    if _gaps(context) and (context.learner_level == "beginner" or context.session_stage == "initial_teaching"):
        return "missing_prerequisites"
    if any(item.result == "correct" and item.reasoning != "sound" for item in context.recent_performance):
        return "correct_answer_weak_reasoning"
    if any(item.strip() for item in context.misconceptions):
        return "confuses_similar_concepts"
    if context.learner_level == "partial" or any(item.result == "partial" for item in context.recent_performance):
        return "partial_understanding"
    return "ready_for_a_check"


def active_conditions(context: SelectorInput) -> set[str]:
    target_taught = context.session_stage != "initial_teaching" or context.learning_objective in context.prior_knowledge
    active = {
        "the_objective_can_be_split_into_ordered_parts",
        "there_is_a_specific_idea_to_check",
        "the_objective_has_explicit_completion_criteria",
        "at_least_one_positive_case_and_one_contrasting_case_can_be_shown",
    }
    if target_taught:
        active.update(
            {
                "initial_instruction_has_been_provided",
                "the_concept_was_studied_earlier",
                "a_model_or_explanation_has_been_given",
                "the_learner_has_an_answer_or_example_to_explain",
            }
        )
    else:
        active.update(
            {
                "learner_has_never_been_taught_the_concept",
                "the_concept_has_not_been_taught",
                "the_learner_needs_a_model_before_independent_work",
                "the_learner_has_no_model_for_the_procedure",
                "the_learner_has_no_example_or_procedure_to_explain_yet",
                "support_is_still_required_for_the_learner_to_start",
            }
        )
    if context.prior_knowledge:
        active.add("the_learner_has_enough_prior_knowledge_to_attempt_a_reason")
    else:
        active.add("the_learner_has_no_prior_knowledge_to_connect")
    if context.recent_performance or any(item.result == "failed" for item in context.previous_strategy_outcomes):
        active.add("the_learner_has_made_an_attempt")
    if _strong(context):
        active.update(
            {
                "the_learner_already_solves_this_problem_type_with_sound_reasoning",
                "support_can_be_removed_without_changing_the_objective",
            }
        )
    weak_single = [
        item for item in context.recent_performance if item.result == "correct" and item.reasoning != "sound"
    ]
    if len(context.recent_performance) == 1 and len(weak_single) == 1:
        active.add("progress_would_depend_on_confidence_or_a_single_correct_answer")
    return active


def input_fingerprint(context: SelectorInput) -> str:
    payload = context.model_dump(mode="json")
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _gaps(context: SelectorInput) -> list[str]:
    return [gap.strip() for gap in context.knowledge_gaps if gap.strip()]


def _strong(context: SelectorInput) -> bool:
    if context.learner_level != "proficient" or _gaps(context) or any(item.strip() for item in context.misconceptions):
        return False
    if not context.recent_performance:
        return False
    return all(item.result == "correct" and item.reasoning == "sound" for item in context.recent_performance)


def _eligibility(strategy: StrategyRecord, active: set[str]) -> tuple[bool, str]:
    for condition in strategy.avoid_or_modify_conditions:
        if condition in active:
            return False, f"avoid:{condition}"
    for condition in strategy.learner_conditions:
        if condition not in active:
            return False, f"missing:{condition}"
    return True, "eligible"


def _rank(
    situation: str,
    eligible: dict[str, str],
    failed: set[str],
    known: dict[str, StrategyRecord],
) -> list[str]:
    candidates = list(_CANDIDATES[situation])
    if situation == "repeated_failure":
        candidates = [strategy_id for strategy_id in candidates if strategy_id not in failed]
    if situation == "strong_performance":
        candidates = [strategy_id for strategy_id in candidates if strategy_id not in _SUPPORT_REDUCED]
    ranked = [strategy_id for strategy_id in candidates if strategy_id in eligible and strategy_id in known]
    if situation == "repeated_failure" and not ranked:
        ranked = [
            strategy_id
            for strategy_id in known
            if strategy_id in eligible and strategy_id not in failed and strategy_id not in _SUPPORT_REDUCED
        ]
    if ranked and ranked[0] in failed:
        alternatives = [strategy_id for strategy_id in ranked if strategy_id not in failed]
        ranked = alternatives or ranked
    return ranked


def _fallback(primary: str | None, ranked: list[str], eligible_ids: set[str]) -> str | None:
    for strategy_id in _FALLBACK_ORDER:
        if strategy_id != primary and strategy_id in eligible_ids:
            return strategy_id
    for strategy_id in ranked:
        if strategy_id != primary:
            return strategy_id
    return None


def _sequence(primary: str | None, supporting: list[str], known: dict[str, StrategyRecord]) -> list[str]:
    if primary is None:
        return []
    steps = list(known[primary].implementation_steps)
    for strategy_id in supporting:
        extra = known[strategy_id].implementation_steps
        if extra:
            steps.append(extra[0])
    return steps[:8]


def _rationale(
    context: SelectorInput,
    situation: str,
    primary: str | None,
    failed: set[str],
    production_primary: str | None,
) -> str:
    gaps = ", ".join(_gaps(context)) or "none"
    misconceptions = ", ".join(item.strip() for item in context.misconceptions if item.strip()) or "none"
    results = ", ".join(f"{item.concept} {item.result}/{item.reasoning}" for item in context.recent_performance) or "none"
    skipped = ", ".join(sorted(failed)) or "none"
    chosen = primary or "none"
    production = production_primary or "none"
    return (
        f"Situation {situation} for {context.topic}, objective {context.learning_objective}, "
        f"level {context.learner_level}, stage {context.session_stage}. "
        f"Gaps: {gaps}. Misconceptions: {misconceptions}. Recent results: {results}. "
        f"Failed strategies skipped: {skipped}. "
        f"Benchmark primary {chosen} under policy {POLICY_VERSION}. "
        f"Production primary {production}. Teaching does not start."
    )
