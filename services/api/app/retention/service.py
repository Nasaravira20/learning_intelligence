from __future__ import annotations

import logging
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.errors import ProviderError
from app.ai.providers.base import ModelProvider
from app.ai.schemas import parse_model_json
from app.ai.types import GenerationRequest
from app.core.config import get_settings
from app.core.errors import AppError, ConflictError
from app.core.logging import log_event
from app.core.time import utcnow
from app.diagnostics.policy import judgment_is_consistent
from app.diagnostics.schemas import ItemJudgment
from app.evaluation.policy import accept_judgment, decide, feedback
from app.evaluation.prompts import judgment_prompt
from app.evaluation.schemas import QuestionDraft
from app.evaluation.service import _different_strategy
from app.models.diagnostics import LearningObjective
from app.models.entities import LearningSession
from app.models.evaluation import MasteryRecord
from app.models.retention import RevisionReview
from app.retention.policy import RUBRIC, index_after, review_timing
from app.retention import policy as retention_policy
from app.retention.prompts import question_prompt
from app.retention.schedule import schedule_following
from app.schemas.retention import MasteryHistoryRead, ResponseInput, RetentionRead, ReviewRead
from app.services.sessions import apply_retention_outcome, enter_retention

logger = logging.getLogger(__name__)


def list_reviews(db: Session, learner_id: UUID) -> list[ReviewRead]:
    rows = list(
        db.scalars(
            select(RevisionReview)
            .where(RevisionReview.learner_id == learner_id)
            .order_by(RevisionReview.due_on.asc(), RevisionReview.created_at.asc())
        ).all()
    )
    moment = retention_policy.current_time()
    sessions = _session_status(db, {row.session_id for row in rows})
    return [ReviewRead.from_row(row, sessions.get(row.session_id, ""), moment) for row in rows]


def get_retention(db: Session, learning_session: LearningSession) -> RetentionRead:
    rows = list(
        db.scalars(
            select(RevisionReview)
            .where(RevisionReview.session_id == learning_session.id)
            .order_by(RevisionReview.created_at.asc())
        ).all()
    )
    mastery = list(
        db.scalars(
            select(MasteryRecord)
            .where(MasteryRecord.session_id == learning_session.id)
            .order_by(MasteryRecord.created_at.asc(), MasteryRecord.id.asc())
        ).all()
    )
    moment = retention_policy.current_time()
    return RetentionRead(
        session_status=learning_session.status,
        reviews=[ReviewRead.from_row(row, learning_session.status, moment) for row in rows],
        mastery=[
            MasteryHistoryRead(
                id=item.id,
                objective_code=item.objective_code,
                decision=item.decision,
                credit=f"{item.credit:.3f}",
                evidence_kind=item.evidence_kind,
                created_at=item.created_at,
            )
            for item in mastery
        ],
    )


def start_review(db: Session, learning_session: LearningSession, provider: ModelProvider) -> ReviewRead:
    if learning_session.status not in {"MASTERED", "MASTERY_UPDATED", "RETENTION_ASSESSMENT"}:
        raise ConflictError("retention_not_ready", "A review starts after the objective is mastered.")
    review = _open(db, learning_session.id)
    if review is None:
        raise ConflictError("retention_not_ready", "This session has no scheduled review.")
    if review.status == "in_progress":
        return ReviewRead.from_row(review, learning_session.status, retention_policy.current_time())
    timing = review_timing(review.due_on, retention_policy.current_time(), review.timezone)
    if timing == "scheduled":
        raise ConflictError("retention_not_due", "This review is not due yet.")
    objective = _objective(db, learning_session, review.objective_code)
    draft = _question(db, provider, objective, str(review.id))
    if not isinstance(draft, QuestionDraft):
        raise AppError("malformed_output", "The model output did not match the required schema.", 422)
    if draft.objective_code != objective.code or objective.code not in draft.prompt:
        raise AppError("malformed_output", "The model output did not match the required schema.", 422)
    if '"' in draft.prompt or "doi" in draft.prompt.casefold() or "http" in draft.prompt.casefold():
        raise AppError("malformed_output", "The model output did not match the required schema.", 422)
    review.prompt = draft.prompt.strip()
    review.rubric = list(RUBRIC)
    review.status = "in_progress"
    review.was_missed = timing == "missed"
    review.updated_at = utcnow()
    enter_retention(db, learning_session)
    db.flush()
    log_event(
        logger,
        logging.INFO,
        "retention_started",
        session_id=learning_session.id,
        objective_code=review.objective_code,
        missed=review.was_missed,
    )
    return ReviewRead.from_row(review, learning_session.status, retention_policy.current_time())


def submit_review(
    db: Session,
    learning_session: LearningSession,
    provider: ModelProvider,
    payload: ResponseInput,
) -> ReviewRead:
    if learning_session.status != "RETENTION_ASSESSMENT":
        raise ConflictError("retention_not_ready", "Start the review before submitting an answer.")
    review = _open(db, learning_session.id)
    if review is None or review.status != "in_progress":
        raise ConflictError("retention_not_ready", "Start the review before submitting an answer.")
    objective = _objective(db, learning_session, review.objective_code)
    answer = payload.answer_text.strip()
    reasoning = payload.reasoning_text.strip()
    judgment = _judgment(db, provider, review, answer, reasoning)
    try:
        if not judgment_is_consistent(judgment):
            raise ValueError("The judgment contradicted itself.")
        accept_judgment(judgment, review.objective_code, answer, reasoning)
    except ValueError:
        log_event(logger, logging.WARNING, "retention_output_rejected", error_class="malformed_output")
        raise AppError("malformed_output", "The model output did not match the required schema.", 422) from None
    decision_name, credit = decide(judgment)
    outcome = _outcome(decision_name)
    note = feedback(review.objective_code, decision_name, judgment)
    strategy_id = None
    if outcome == "failed":
        strategy_id = _different_strategy(db, learning_session, objective, judgment)
    evidence_kind = "observed" if outcome == "recalled" else "inferred"
    record = MasteryRecord(
        session_id=learning_session.id,
        learner_id=learning_session.learner_id,
        topic_id=learning_session.topic_id,
        objective_code=review.objective_code,
        decision=decision_name if outcome != "recalled" else "mastered",
        credit=Decimal("1.000") if outcome == "recalled" else credit,
        evidence_kind=evidence_kind,
        feedback=note,
        answer_verdict=judgment.answer_verdict,
        reasoning_verdict=judgment.reasoning_verdict,
        understanding=judgment.understanding,
        remediation_strategy_id=strategy_id,
        created_at=utcnow(),
    )
    db.add(record)
    db.flush()
    review.status = "completed"
    review.outcome = outcome
    review.answer_text = answer
    review.reasoning_text = reasoning
    review.mastery_record_id = record.id
    review.completed_at = utcnow()
    review.updated_at = review.completed_at
    db.flush()
    following = index_after(
        interval_index=review.interval_index,
        recalled=outcome == "recalled",
        missed=review.was_missed,
    )
    if outcome != "recalled":
        following = 0 if outcome == "failed" else review.interval_index
    schedule_following(db, learning_session, review.objective_code, following)
    apply_retention_outcome(db, learning_session, outcome)
    log_event(
        logger,
        logging.INFO,
        "retention_recorded",
        session_id=learning_session.id,
        outcome=outcome,
        missed=review.was_missed,
    )
    return ReviewRead.from_row(review, learning_session.status, retention_policy.current_time())


def _outcome(decision_name: str) -> str:
    if decision_name == "mastered":
        return "recalled"
    if decision_name == "remediation":
        return "failed"
    if decision_name == "further_assessment":
        return "further_assessment"
    return "needs_review"


def _question(db: Session, provider: ModelProvider, objective: LearningObjective, action_id: str):
    prompt = question_prompt(objective_code=objective.code, concept=objective.concept, statement=objective.statement)
    return _complete(db, provider, prompt, QuestionDraft, action_id)


def _judgment(db: Session, provider: ModelProvider, review: RevisionReview, answer: str, reasoning: str) -> ItemJudgment:
    prompt = judgment_prompt(
        objective_code=review.objective_code,
        prompt=review.prompt or "",
        answer=answer,
        reasoning=reasoning,
    )
    parsed = _complete(db, provider, prompt, ItemJudgment, f"{review.id}:judge")
    if not isinstance(parsed, ItemJudgment):
        raise AppError("malformed_output", "The model output did not match the required schema.", 422)
    return parsed


def _complete(db: Session, provider: ModelProvider, prompt: str, output_model: type, action_id: str):
    if len(prompt) > 4000:
        raise AppError("validation_error", "The model prompt is too long.", 422)
    settings = get_settings()
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
        log_event(logger, logging.WARNING, "retention_output_rejected", error_class="malformed_output")
        raise AppError("malformed_output", "The model output did not match the required schema.", 422) from None


def _open(db: Session, session_id) -> RevisionReview | None:
    return db.scalar(
        select(RevisionReview).where(
            RevisionReview.session_id == session_id,
            RevisionReview.status.in_(("scheduled", "in_progress")),
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
        raise ConflictError("retention_not_ready", "The reviewed objective is no longer on this topic.")
    return objective


def _session_status(db: Session, session_ids: set) -> dict:
    if not session_ids:
        return {}
    rows = db.scalars(select(LearningSession).where(LearningSession.id.in_(session_ids))).all()
    return {row.id: row.status for row in rows}
