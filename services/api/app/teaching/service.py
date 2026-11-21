from __future__ import annotations

import logging

from sqlalchemy import select
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
from app.models.diagnostics import LearningObjective
from app.models.entities import LearningSession
from app.models.pedagogy import PedagogySelection
from app.models.planning import LearningPlan, LearningPlanStep
from app.models.teaching import TeachingActivity, TeachingAttempt, TeachingHint, TeachingLesson
from app.schemas.teaching import AttemptInput, LessonRead
from app.services.sessions import enter_teaching
from app.teaching.draft import activity_for
from app.teaching.policy import accept_lesson, fade_support, support_strategy
from app.teaching.prompts import lesson_prompt
from app.teaching.schemas import LessonDraft

logger = logging.getLogger(__name__)


def start_lesson(db: Session, learning_session: LearningSession, provider: ModelProvider) -> LessonRead:
    existing = _lesson(db, learning_session.id)
    if existing is not None:
        return _read(db, existing, learning_session.status)
    if learning_session.status != "PLAN_READY":
        raise ConflictError("teaching_not_ready", "Start a lesson after the learning plan is ready.")
    selection = _selection(db, learning_session.id)
    if selection is None or not selection.primary_strategy_id:
        raise ConflictError("teaching_not_ready", "Choose strategies before starting a lesson.")
    objective = _current_objective(db, learning_session)
    fallback = selection.fallback_strategy_id or selection.primary_strategy_id
    supporting = [item for item in selection.supporting_strategy_ids if isinstance(item, str) and item.strip()]
    prompt = lesson_prompt(
        objective_code=objective.code,
        concept=objective.concept,
        statement=objective.statement,
        primary_strategy_id=selection.primary_strategy_id,
        supporting_strategy_ids=supporting,
        fallback_strategy_id=fallback,
    )
    draft = _draft(db, provider, prompt, str(learning_session.id))
    allowed = {selection.primary_strategy_id, fallback, *supporting}
    try:
        accept_lesson(
            draft,
            objective_code=objective.code,
            allowed_strategy_ids=allowed,
            required_strategy_ids={selection.primary_strategy_id, *supporting},
        )
    except ValueError:
        log_event(logger, logging.WARNING, "teaching_output_rejected", error_class="malformed_output")
        raise AppError("malformed_output", "The model output did not match the required schema.", 422) from None
    lesson = TeachingLesson(
        session_id=learning_session.id,
        learner_id=learning_session.learner_id,
        selection_id=selection.id,
        objective_code=objective.code,
        status="active",
        review_status="pending_human_review",
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db.add(lesson)
    db.flush()
    _store_activities(db, lesson, draft)
    enter_teaching(db, learning_session)
    log_event(
        logger,
        logging.INFO,
        "lesson_started",
        session_id=learning_session.id,
        lesson_id=lesson.id,
        objective_code=objective.code,
    )
    return _read(db, lesson, learning_session.status)


def get_lesson(db: Session, learning_session: LearningSession) -> LessonRead:
    lesson = _lesson(db, learning_session.id)
    if lesson is None:
        raise NotFoundError("lesson_not_found", "This session has no lesson.")
    return _read(db, lesson, learning_session.status)


def reveal_hint(db: Session, learning_session: LearningSession) -> LessonRead:
    lesson = _active_lesson(db, learning_session)
    activity = _current(db, lesson.id)
    hints = _hints(db, activity.id)
    if activity.hints_revealed >= len(hints):
        raise ConflictError("hints_exhausted", "This activity has no further hint.")
    activity.hints_revealed += 1
    lesson.updated_at = utcnow()
    db.flush()
    log_event(
        logger,
        logging.INFO,
        "teaching_hint_revealed",
        lesson_id=lesson.id,
        activity_id=activity.id,
        hints_revealed=activity.hints_revealed,
    )
    return _read(db, lesson, learning_session.status)


def record_attempt(db: Session, learning_session: LearningSession, payload: AttemptInput) -> LessonRead:
    lesson = _active_lesson(db, learning_session)
    activity = _current(db, lesson.id)
    db.add(
        TeachingAttempt(
            activity_id=activity.id,
            learner_id=learning_session.learner_id,
            outcome=payload.outcome,
            answer_text=payload.answer_text.strip(),
            created_at=utcnow(),
        )
    )
    if payload.outcome == "correct":
        _advance(db, lesson, activity)
    else:
        _insert_support(db, learning_session, lesson, activity)
    lesson.updated_at = utcnow()
    learning_session.updated_at = utcnow()
    db.flush()
    log_event(
        logger,
        logging.INFO,
        "teaching_attempt_recorded",
        lesson_id=lesson.id,
        activity_id=activity.id,
        outcome=payload.outcome,
        lesson_status=lesson.status,
    )
    return _read(db, lesson, learning_session.status)


def _draft(db: Session, provider: ModelProvider, prompt: str, action_id: str) -> LessonDraft:
    if len(prompt) > 4000:
        raise AppError("validation_error", "The model prompt is too long.", 422)
    settings = get_settings()
    if settings.ai_provider == "gemini":
        _result, parsed = generate(
            db,
            provider,
            task="teaching",
            category="development",
            prompt=prompt,
            output_model=LessonDraft,
            action_id=action_id,
        )
        if not isinstance(parsed, LessonDraft):
            raise AppError("malformed_output", "The model output did not match the required schema.", 422)
        return parsed
    request = GenerationRequest(
        model_id="mock",
        prompt=prompt,
        max_output_tokens=settings.gemini_max_output_tokens,
        schema=LessonDraft.model_json_schema(),
    )
    try:
        result = provider.generate(request)
    except ProviderError as exc:
        raise AppError(exc.error_class, "The model request failed.", 503) from None
    try:
        parsed = parse_model_json(LessonDraft, result.text)
    except ValueError:
        log_event(logger, logging.WARNING, "teaching_output_rejected", error_class="malformed_output")
        raise AppError("malformed_output", "The model output did not match the required schema.", 422) from None
    if not isinstance(parsed, LessonDraft):
        raise AppError("malformed_output", "The model output did not match the required schema.", 422)
    return parsed


def _store_activities(db: Session, lesson: TeachingLesson, draft: LessonDraft) -> None:
    for index, item in enumerate(draft.activities):
        activity = TeachingActivity(
            lesson_id=lesson.id,
            position=index,
            strategy_id=item.strategy_id,
            kind=item.kind,
            title=item.title.strip(),
            prompt=item.prompt.strip(),
            example=item.example.strip() if item.example else None,
            worked_steps=[step.strip() for step in item.worked_steps if step.strip()],
            expected_answer=item.expected_answer.strip() if item.expected_answer else None,
            support_level=item.support_level,
            status="current" if index == 0 else "upcoming",
            hints_revealed=0,
            inserted_for_struggle=False,
        )
        db.add(activity)
        db.flush()
        for hint_index, hint in enumerate(item.hints):
            db.add(
                TeachingHint(
                    activity_id=activity.id,
                    position=hint_index,
                    text=hint.text.strip(),
                    reveals_answer=hint.reveals_answer,
                )
            )
    db.flush()


def _advance(db: Session, lesson: TeachingLesson, activity: TeachingActivity) -> None:
    nxt = _following(db, lesson.id, activity.position)
    activity.status = "completed"
    db.flush()
    if nxt is None:
        lesson.status = "completed"
        return
    nxt.support_level = fade_support(nxt.support_level)
    nxt.status = "current"


def _insert_support(
    db: Session,
    learning_session: LearningSession,
    lesson: TeachingLesson,
    activity: TeachingActivity,
) -> None:
    selection = db.get(PedagogySelection, lesson.selection_id)
    objective = db.scalar(
        select(LearningObjective).where(
            LearningObjective.topic_id == learning_session.topic_id,
            LearningObjective.code == lesson.objective_code,
        )
    )
    if selection is None or not selection.primary_strategy_id or objective is None:
        raise ConflictError("teaching_not_ready", "The lesson is missing its plan or strategy choice.")
    supporting = [item for item in selection.supporting_strategy_ids if isinstance(item, str)]
    fallback = selection.fallback_strategy_id or selection.primary_strategy_id
    chosen = support_strategy([*supporting, selection.primary_strategy_id, fallback])
    draft = activity_for(
        chosen,
        objective.code,
        objective.concept,
        kind="concrete_example" if chosen == "concrete_examples" else None,
        support_level="high",
    )
    if draft["kind"] not in {"explanation", "concrete_example", "worked_example"}:
        draft = activity_for(chosen, objective.code, objective.concept, kind="explanation", support_level="high")
    later = list(
        db.scalars(
            select(TeachingActivity).where(
                TeachingActivity.lesson_id == lesson.id,
                TeachingActivity.position > activity.position,
            )
        )
    )
    for item in later:
        item.position += 100
    activity.status = "completed"
    db.flush()
    for item in later:
        item.position -= 99
    db.flush()
    inserted = TeachingActivity(
        lesson_id=lesson.id,
        position=activity.position + 1,
        strategy_id=str(draft["strategy_id"]),
        kind=str(draft["kind"]),
        title=str(draft["title"]),
        prompt=str(draft["prompt"]),
        example=str(draft["example"]) if draft["example"] else None,
        worked_steps=list(draft["worked_steps"]),
        expected_answer=None,
        support_level="high",
        status="current",
        hints_revealed=0,
        inserted_for_struggle=True,
    )
    db.add(inserted)
    db.flush()
    for hint_index, hint in enumerate(draft["hints"]):
        if not isinstance(hint, dict):
            continue
        db.add(
            TeachingHint(
                activity_id=inserted.id,
                position=hint_index,
                text=str(hint["text"]),
                reveals_answer=False,
            )
        )


def _active_lesson(db: Session, learning_session: LearningSession) -> TeachingLesson:
    lesson = _lesson(db, learning_session.id)
    if lesson is None:
        raise NotFoundError("lesson_not_found", "This session has no lesson.")
    if lesson.status != "active":
        raise ConflictError("lesson_complete", "This lesson has finished its activities.")
    if learning_session.status != "TEACHING":
        raise ConflictError("teaching_not_ready", "This session is not in teaching.")
    return lesson


def _current(db: Session, lesson_id) -> TeachingActivity:
    activity = db.scalar(
        select(TeachingActivity).where(
            TeachingActivity.lesson_id == lesson_id,
            TeachingActivity.status == "current",
        )
    )
    if activity is None:
        raise ConflictError("lesson_complete", "This lesson has no current activity.")
    return activity


def _following(db: Session, lesson_id, position: int) -> TeachingActivity | None:
    return db.scalar(
        select(TeachingActivity)
        .where(TeachingActivity.lesson_id == lesson_id, TeachingActivity.position > position)
        .order_by(TeachingActivity.position)
        .limit(1)
    )


def _lesson(db: Session, session_id) -> TeachingLesson | None:
    return db.scalar(select(TeachingLesson).where(TeachingLesson.session_id == session_id))


def _selection(db: Session, session_id) -> PedagogySelection | None:
    return db.scalar(
        select(PedagogySelection).where(
            PedagogySelection.session_id == session_id,
            PedagogySelection.status == "active",
        )
    )


def _current_objective(db: Session, learning_session: LearningSession) -> LearningObjective:
    plan = db.scalar(
        select(LearningPlan).where(
            LearningPlan.session_id == learning_session.id,
            LearningPlan.status == "active",
        )
    )
    if plan is None or plan.current_step_id is None:
        raise ConflictError("teaching_not_ready", "The learning plan has no current step.")
    step = db.get(LearningPlanStep, plan.current_step_id)
    if step is None:
        raise ConflictError("teaching_not_ready", "The learning plan has no current step.")
    objective = db.get(LearningObjective, step.objective_id)
    if objective is None:
        raise ConflictError("teaching_not_ready", "The current plan step has no objective.")
    return objective


def _hints(db: Session, activity_id) -> list[TeachingHint]:
    return list(
        db.scalars(
            select(TeachingHint).where(TeachingHint.activity_id == activity_id).order_by(TeachingHint.position)
        )
    )


def _read(db: Session, lesson: TeachingLesson, session_status: str) -> LessonRead:
    activities = list(
        db.scalars(
            select(TeachingActivity).where(TeachingActivity.lesson_id == lesson.id).order_by(TeachingActivity.position)
        )
    )
    parts = [(activity, _hints(db, activity.id)) for activity in activities]
    return LessonRead.from_parts(lesson, parts, session_status)
