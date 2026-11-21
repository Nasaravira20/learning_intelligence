from app.pedagogy.registry import load_registry
from app.pedagogy.schemas import P0_STRATEGY_IDS
from app.pedagogy.selector import SelectorInput, select


def _context(**overrides: object) -> SelectorInput:
    payload = {
        "topic": "Backpropagation",
        "learning_objective": "Understand the chain rule",
        "learner_level": "beginner",
        "prior_knowledge": ["basic_derivatives"],
        "knowledge_gaps": ["chain_rule"],
        "misconceptions": ["confuses_loss_and_gradient"],
        "recent_performance": [],
        "session_stage": "initial_teaching",
        "time_available_minutes": 20,
        "previous_strategy_outcomes": [],
    }
    payload.update(overrides)
    return SelectorInput.model_validate(payload)


def _decision(**overrides: object):
    return select(_context(**overrides), load_registry(), production=False)


def test_missing_prerequisites_choose_small_steps_and_examples() -> None:
    decision = _decision()
    assert decision.situation == "missing_prerequisites"
    assert decision.primary_strategy == "small_step_instruction"
    assert "concrete_examples" in decision.supporting_strategies
    assert "worked_examples" in decision.supporting_strategies
    assert "retrieval_practice" not in decision.supporting_strategies
    assert decision.fallback_strategy == "checks_for_understanding"
    assert "chain_rule" in decision.rationale
    assert decision.controls_teaching is False
    assert decision.production_primary_strategy is None
    rejected = {item.strategy_id: item.reason for item in decision.rejected}
    assert rejected["retrieval_practice"].startswith("avoid:")


def test_learner_context_changes_the_strategy() -> None:
    partial = _decision(
        learner_level="partial",
        knowledge_gaps=[],
        misconceptions=[],
        session_stage="practice",
        recent_performance=[{"concept": "chain_rule", "result": "partial", "reasoning": "weak"}],
    )
    assert partial.situation == "partial_understanding"
    assert partial.primary_strategy == "self_explanation"
    assert partial.primary_strategy != _decision().primary_strategy


def test_repeated_failure_skips_the_failed_strategy() -> None:
    decision = _decision(
        learner_level="partial",
        knowledge_gaps=[],
        misconceptions=[],
        session_stage="practice",
        recent_performance=[
            {"concept": "chain_rule", "result": "incorrect", "reasoning": "missing"},
            {"concept": "chain_rule", "result": "incorrect", "reasoning": "weak"},
        ],
        previous_strategy_outcomes=[{"strategy_id": "formative_feedback", "result": "failed"}],
    )
    assert decision.situation == "repeated_failure"
    assert decision.primary_strategy != "formative_feedback"
    assert decision.primary_strategy == "small_step_instruction"
    assert "formative_feedback" in decision.rationale


def test_strong_performance_reduces_support() -> None:
    decision = _decision(
        learner_level="proficient",
        knowledge_gaps=[],
        misconceptions=[],
        session_stage="practice",
        prior_knowledge=["chain_rule"],
        recent_performance=[{"concept": "chain_rule", "result": "correct", "reasoning": "sound"}],
    )
    assert decision.situation == "strong_performance"
    assert decision.primary_strategy == "checks_for_understanding"
    chosen = {decision.primary_strategy, *decision.supporting_strategies}
    assert "scaffolding" not in chosen
    assert "worked_examples" not in chosen
    assert "guided_practice" not in chosen


def test_only_registered_strategies_are_selected_and_repeat() -> None:
    registry = load_registry()
    known = {item.strategy_id for item in registry.strategies}
    assert known == set(P0_STRATEGY_IDS)
    first = _decision()
    second = _decision()
    assert first.model_dump() == second.model_dump()
    selected = [first.primary_strategy, first.fallback_strategy, *first.supporting_strategies]
    assert all(strategy_id in known for strategy_id in selected)
    assert "additional_prerequisite_instruction" not in selected


def test_forgetting_selects_retrieval_and_a_weak_answer_does_not_count_as_mastery() -> None:
    forgotten = _decision(
        learner_level="partial",
        knowledge_gaps=["chain_rule"],
        misconceptions=[],
        session_stage="revision",
        prior_knowledge=["chain_rule"],
        recent_performance=[{"concept": "chain_rule", "result": "forgotten", "reasoning": "missing"}],
    )
    assert forgotten.situation == "forgets_earlier_content"
    assert forgotten.primary_strategy == "retrieval_practice"
    assert "spaced_practice" in forgotten.supporting_strategies

    weak = _decision(
        learner_level="partial",
        knowledge_gaps=[],
        misconceptions=[],
        session_stage="assessment",
        prior_knowledge=["chain_rule"],
        recent_performance=[{"concept": "chain_rule", "result": "correct", "reasoning": "weak"}],
    )
    assert weak.situation == "correct_answer_weak_reasoning"
    assert weak.primary_strategy == "self_explanation"
    rejected = {item.strategy_id: item.reason for item in weak.rejected}
    assert rejected["mastery_learning"].startswith("avoid:")


def test_confusion_uses_contrastive_examples() -> None:
    decision = _decision(
        learner_level="partial",
        knowledge_gaps=[],
        session_stage="practice",
        prior_knowledge=["chain_rule"],
        misconceptions=["confuses_loss_and_gradient"],
    )
    assert decision.situation == "confuses_similar_concepts"
    assert decision.primary_strategy == "concrete_examples"


def test_reviewed_registry_still_does_not_start_teaching() -> None:
    registry = load_registry()
    strategies = tuple(
        item.model_copy(update={"review_status": "reviewed", "reviewed_by": "Hassen"}) for item in registry.strategies
    )
    sources = tuple(
        item.model_copy(update={"review_status": "reviewed", "reviewed_by": "Hassen"}) for item in registry.sources
    )
    reviewed = registry.__class__(
        root=registry.root,
        manifest=registry.manifest,
        strategies=strategies,
        sources=sources,
    )
    decision = select(_context(), reviewed, production=True)
    assert decision.primary_strategy == "small_step_instruction"
    assert decision.production_primary_strategy == "small_step_instruction"
    assert decision.controls_teaching is False
