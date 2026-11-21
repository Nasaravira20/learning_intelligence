from __future__ import annotations

import logging
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.errors import ProviderError
from app.ai.gateway import generate
from app.ai.providers.base import ModelProvider
from app.ai.schemas import parse_model_json
from app.ai.types import GenerationRequest
from app.core.config import get_settings
from app.core.errors import AppError, ConflictError, NotFoundError
from app.core.logging import log_event
from app.core.time import utcnow
from app.diagnostics.policy import CONFIDENCE, judgment_is_consistent
from app.diagnostics.schemas import ItemJudgment
from app.evaluation.policy import RUBRIC, accept_judgment, decide, feedback
from app.evaluation.prompts import judgment_prompt, question_prompt
from app.evaluation.schemas import QuestionDraft
from app.models.diagnostics import LearningObjective
from app.models.entities import LearningSession
from app.models.evaluation import EvaluationAttempt, MasteryRecord
from app.models.pedagogy import PedagogySelection
from app.models.teaching import TeachingLesson
from app.pedagogy.registry import RegistryValidationError, load_registry
from app.pedagogy.selector import PerformanceEvent, SelectorInput, StrategyOutcome
from app.pedagogy.selector import select as choose_strategies
from app.pedagogy.selection_service import save_decision
from app.schemas.evaluation import EvaluationRead, ResponseInput
from app.schemas.learner import AssessmentCreate, KnowledgeCreate, MisconceptionCreate
from app.services import learner_intelligence as intelligence
from app.services.sessions import enter_evaluation, resume_teaching, apply_evaluation_decision
from app.teaching.service import replace_lesson

logger = logging.getLogger(__name__)


def start_evaluation(db: Session, learning_session: LearningSession, provider: ModelProvider) -> EvaluationRead:
    open_attempt = _open_attempt(db, learning_session.id)
    if open_attempt is not None:
        return _read(db, open_attempt, learning_session.status)
    if learning_session.status == "MASTERED":
        raise ConflictError("evaluation_closed", "This objective is already marked mastered.")
    if learning_session.status not in {"TEACHING", "EVALUATING", "NEEDS_REVIEW"}:
        raise ConflictError("evaluation_not_ready", "Check understanding after a lesson has started.")
    lesson = _active_lesson(db, learning_session.id)
    if lesson is None:
        raise ConflictError("evaluation_not_ready", "Start a lesson before checking understanding.")
    objective = _objective(db, learning_session, lesson.objective_code)
    draft = _question(db, provider, objective, str(learning_session.id))
    if not isinstance(draft, QuestionDraft):
        raise AppError("malformed_output", "The model output did not match the required schema.", 422)
    if draft.objective_code != objective.code or objective.code not in draft.prompt:
        raise AppError("malformed_output", "The model output did not match the required schema.", 422)
    if '"' in draft.prompt or "doi" in draft.prompt.casefold() or "http" in draft.prompt.casefold():
        raise AppError("malformed_output", "The model output did not match the required schema.", 422)
    revision = _next_revision(db, learning_session.id)
    attempt = EvaluationAttempt(
        session_id=learning_session.id,
        learner_id=learning_session.learner_id,
        lesson_id=lesson.id,
        revision=revision,
        status="open",
        objective_code=objective.code,
        prompt=draft.prompt.strip(),
        rubric=list(RUBRIC),
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db.add(attempt)
    if learning_session.status != "EVALUATING":
        enter_evaluation(db, learning_session)
    db.flush()
    log_event(logger, logging.INFO, "evaluation_started", session_id=learning_session.id, revision=revision)
    return _read(db, attempt, learning_session.status)


def get_evaluation(db: Session, learning_session: LearningSession) -> EvaluationRead:
    attempt = _latest(db, learning_session.id)
    if attempt is None:
        raise NotFoundError("evaluation_not_found", "This session has no evaluation.")
    return _read(db, attempt, learning_session.status)


def submit_response(
    db: Session,
    learning_session: LearningSession,
    provider: ModelProvider,
    payload: ResponseInput,
) -> EvaluationRead:
    if learning_session.status != "EVALUATING":
        raise ConflictError("evaluation_not_ready", "This session is not waiting for an answer.")
    attempt = _open_attempt(db, learning_session.id)
    if attempt is None:
        raise ConflictError("evaluation_not_ready", "Start a check before submitting an answer.")
    objective = _objective(db, learning_session, attempt.objective_code)
    answer = payload.answer_text.strip()
    reasoning = payload.reasoning_text.strip()
    judgment = _judgment(db, provider, attempt, answer, reasoning)
    try:
        if not judgment_is_consistent(judgment):
            raise ValueError("The judgment contradicted itself.")
        accept_judgment(judgment, attempt.objective_code, answer, reasoning)
    except ValueError:
        log_event(logger, logging.WARNING, "evaluation_output_rejected", error_class="malformed_output")
        raise AppError("malformed_output", "The model output did not match the required schema.", 422) from None
    decision_name, credit = decide(judgment)
    note = feedback(attempt.objective_code, decision_name, judgment)
    strategy_id = None
    if decision_name == "remediation":
        strategy_id = _different_strategy(db, learning_session, objective, judgment)
    evidence_kind = "observed" if decision_name == "mastered" else "inferred"
    record = MasteryRecord(
        session_id=learning_session.id,
        learner_id=learning_session.learner_id,
        topic_id=learning_session.topic_id,
        objective_code=attempt.objective_code,
        decision=decision_name,
        credit=credit,
        evidence_kind=evidence_kind,
        feedback=note,
        answer_verdict=judgment.answer_verdict,
        reasoning_verdict=judgment.reasoning_verdict,
        understanding=judgment.understanding,
        remediation_strategy_id=strategy_id,
        misconception_evidence=judgment.misconception.evidence.strip() if judgment.misconception else None,
        created_at=utcnow(),
    )
    db.add(record)
    db.flush()
    attempt.status = "completed"
    attempt.answer_text = answer
    attempt.reasoning_text = reasoning
    attempt.mastery_record_id = record.id
    attempt.updated_at = utcnow()
    _record_learner_evidence(db, learning_session, objective, attempt, judgment, decision_name)
    apply_evaluation_decision(db, learning_session, decision_name)
    if decision_name == "mastered":
        from app.retention.schedule import schedule_after_mastery

        schedule_after_mastery(db, learning_session, attempt.objective_code)
    log_event(
        logger,
        logging.INFO,
        "evaluation_recorded",
        session_id=learning_session.id,
        decision=decision_name,
        credit=str(credit),
    )
    return _read(db, attempt, learning_session.status)


def start_remediation(db: Session, learning_session: LearningSession, provider: ModelProvider) -> EvaluationRead:
    if learning_session.status != "REMEDIATION":
        raise ConflictError("remediation_not_ready", "Remediation follows a partial or missed check.")
    attempt = _latest(db, learning_session.id)
    if attempt is None:
        raise ConflictError("remediation_not_ready", "Remediation follows a partial or missed check.")
    record = db.scalar(
        select(MasteryRecord)
        .where(MasteryRecord.session_id == learning_session.id)
        .order_by(MasteryRecord.created_at.desc(), MasteryRecord.id.desc())
    )
    if record is None or record.decision != "remediation" or not record.remediation_strategy_id:
        raise ConflictError("remediation_unavailable", "No different registered strategy is available.")
    objective = _objective(db, learning_session, attempt.objective_code)
    selection = _active_selection(db, learning_session.id)
    old_primary = selection.primary_strategy_id if selection is not None else None
    context = _remediation_input(learning_session, objective, old_primary, record)
    try:
        registry = load_registry()
    except RegistryValidationError as exc:
        raise ConflictError("registry_invalid", "The pedagogy registry failed validation.") from exc
    decision = choose_strategies(context, registry, production=True)
    if decision.primary_strategy is None or decision.primary_strategy == old_primary:
        raise ConflictError("remediation_unavailable", "No different registered strategy is available.")
    if decision.primary_strategy != record.remediation_strategy_id:
        record.remediation_strategy_id = decision.primary_strategy
    save_decision(db, learning_session, decision)
    resume_teaching(db, learning_session)
    replace_lesson(db, learning_session, provider)
    return _read(db, attempt, learning_session.status)


def _question(db: Session, provider: ModelProvider, objective: LearningObjective, action_id: str) -> QuestionDraft:
    prompt = question_prompt(objective_code=objective.code, concept=objective.concept, statement=objective.statement)
    return _complete(db, provider, "evaluation", prompt, QuestionDraft, action_id)


def _judgment(
    db: Session,
    provider: ModelProvider,
    attempt: EvaluationAttempt,
    answer: str,
    reasoning: str,
) -> ItemJudgment:
    prompt = judgment_prompt(
        objective_code=attempt.objective_code,
        prompt=attempt.prompt,
        answer=answer,
        reasoning=reasoning,
    )
    parsed = _complete(db, provider, "evaluation", prompt, ItemJudgment, f"{attempt.id}:judge")
    if not isinstance(parsed, ItemJudgment):
        raise AppError("malformed_output", "The model output did not match the required schema.", 422)
    return parsed


def _complete(db: Session, provider: ModelProvider, task: str, prompt: str, output_model: type, action_id: str):
    if len(prompt) > 4000:
        raise AppError("validation_error", "The model prompt is too long.", 422)
    settings = get_settings()
    if settings.ai_provider == "gemini":
        _result, parsed = generate(
            db,
            provider,
            task=task,
            category="development",
            prompt=prompt,
            output_model=output_model,
            action_id=action_id,
        )
        if parsed is None:
            raise AppError("malformed_output", "The model output did not match the required schema.", 422)
        return parsed
    request = GenerationRequest(
        model_id="mock",
        prompt=prompt,
        max_output_tokens=settings.gemini_max_output_tokens,
        schema=output_model.model_json_schema(),
    )
    try:
        result = provider.generate(request)
    except ProviderError as exc:
        raise AppError(exc.error_class, "The model request failed.", 503) from None
    try:
        return parse_model_json(output_model, result.text)
    except ValueError:
        log_event(logger, logging.WARNING, "evaluation_output_rejected", error_class="malformed_output", task=task)
        raise AppError("malformed_output", "The model output did not match the required schema.", 422) from None


def _different_strategy(db: Session, learning_session: LearningSession, objective: LearningObjective, judgment: ItemJudgment) -> str | None:
    selection = _active_selection(db, learning_session.id)
    old_primary = selection.primary_strategy_id if selection is not None else None
    record = MasteryRecord(
        session_id=learning_session.id,
        learner_id=learning_session.learner_id,
        topic_id=learning_session.topic_id,
        objective_code=objective.code,
        decision="remediation",
        credit=Decimal("0.000"),
        evidence_kind="inferred",
        feedback="placeholder",
        answer_verdict=judgment.answer_verdict,
        reasoning_verdict=judgment.reasoning_verdict,
        understanding=judgment.understanding,
    )
    context = _remediation_input(learning_session, objective, old_primary, record)
    try:
        registry = load_registry()
    except RegistryValidationError:
        return None
    decision = choose_strategies(context, registry, production=True)
    if decision.primary_strategy and decision.primary_strategy != old_primary:
        return decision.primary_strategy
    return None


def _remediation_input(
    learning_session: LearningSession,
    objective: LearningObjective,
    old_primary: str | None,
    record: MasteryRecord,
) -> SelectorInput:
    result = "partial" if record.answer_verdict == "partial" else "incorrect"
    reasoning = "weak" if record.reasoning_verdict in {"weak", "partial", "absent"} else "missing"
    topic = learning_session.topic.title if learning_session.topic is not None else "topic"
    outcomes = [StrategyOutcome(strategy_id=old_primary, result="failed")] if old_primary else []
    return SelectorInput(
        topic=topic,
        learning_objective=objective.code,
        learner_level="beginner",
        prior_knowledge=[],
        knowledge_gaps=[objective.code],
        misconceptions=[],
        recent_performance=[PerformanceEvent(concept=objective.concept, result=result, reasoning=reasoning)],
        session_stage="practice",
        time_available_minutes=20,
        previous_strategy_outcomes=outcomes,
    )


def _record_learner_evidence(
    db: Session,
    learning_session: LearningSession,
    objective: LearningObjective,
    attempt: EvaluationAttempt,
    judgment: ItemJudgment,
    decision_name: str,
) -> None:
    response_text = " ".join(part for part in (attempt.answer_text, attempt.reasoning_text) if part)
    intelligence.record_assessment(
        db,
        learning_session.learner_id,
        AssessmentCreate(
            topic_id=learning_session.topic_id,
            session_id=learning_session.id,
            prompt_summary=attempt.prompt[:500],
            response_summary=response_text[:2000] or "No answer was given.",
            outcome=judgment.answer_verdict,
        ),
    )
    if decision_name == "mastered":
        intelligence.record_knowledge(
            db,
            learning_session.learner_id,
            KnowledgeCreate(
                topic_id=learning_session.topic_id,
                concept=objective.concept,
                summary=f"Demonstrated: {objective.statement}"[:1000],
                evidence_kind="observed",
                provenance="assessment",
                confidence=CONFIDENCE[judgment.confidence],
            ),
        )
    elif decision_name == "remediation" and judgment.understanding == "partial":
        intelligence.record_knowledge(
            db,
            learning_session.learner_id,
            KnowledgeCreate(
                topic_id=learning_session.topic_id,
                concept=objective.concept,
                summary=f"Partial understanding of {objective.concept}.",
                evidence_kind="inferred",
                provenance="system_estimate",
                confidence=min(CONFIDENCE[judgment.confidence], Decimal("0.600")),
            ),
        )
    hypothesis = judgment.misconception
    if hypothesis is None:
        return
    confirmed = hypothesis.confidence == "high" and judgment.understanding != "uncertain" and judgment.confidence != "low"
    intelligence.record_misconception(
        db,
        learning_session.learner_id,
        MisconceptionCreate(
            topic_id=learning_session.topic_id,
            concept=objective.concept,
            description=hypothesis.description.strip(),
            supporting_note=hypothesis.evidence.strip(),
            evidence_kind="observed" if confirmed else "inferred",
            provenance="learner_response" if confirmed else "system_estimate",
            confidence=CONFIDENCE[hypothesis.confidence],
        ),
    )


def _read(db: Session, attempt: EvaluationAttempt, session_status: str) -> EvaluationRead:
    record = db.get(MasteryRecord, attempt.mastery_record_id) if attempt.mastery_record_id else None
    return EvaluationRead.from_parts(attempt, record, session_status)


def _open_attempt(db: Session, session_id) -> EvaluationAttempt | None:
    return db.scalar(
        select(EvaluationAttempt).where(
            EvaluationAttempt.session_id == session_id,
            EvaluationAttempt.status == "open",
        )
    )


def _latest(db: Session, session_id) -> EvaluationAttempt | None:
    return db.scalar(
        select(EvaluationAttempt)
        .where(EvaluationAttempt.session_id == session_id)
        .order_by(EvaluationAttempt.revision.desc())
    )


def _next_revision(db: Session, session_id) -> int:
    current = db.scalar(select(func.max(EvaluationAttempt.revision)).where(EvaluationAttempt.session_id == session_id))
    return int(current or 0) + 1


def _active_lesson(db: Session, session_id) -> TeachingLesson | None:
    active = db.scalar(
        select(TeachingLesson).where(TeachingLesson.session_id == session_id, TeachingLesson.status == "active")
    )
    if active is not None:
        return active
    return db.scalar(
        select(TeachingLesson)
        .where(TeachingLesson.session_id == session_id)
        .order_by(TeachingLesson.revision.desc())
    )


def _active_selection(db: Session, session_id) -> PedagogySelection | None:
    return db.scalar(
        select(PedagogySelection).where(
            PedagogySelection.session_id == session_id,
            PedagogySelection.status == "active",
        )
    )


def _objective(db: Session, learning_session: LearningSession, code: str) -> LearningObjective:
    objective = db.scalar(
        select(LearningObjective).where(
            LearningObjective.topic_id == learning_session.topic_id,
            LearningObjective.code == code,
        )
    )
    if objective is None:
        raise ConflictError("evaluation_not_ready", "The lesson objective is no longer on this topic.")
    return objective
