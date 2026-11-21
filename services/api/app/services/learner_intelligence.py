"""Deterministic learner-record persistence.

The model does not write these rows. Inferred evidence stays inferred when a learner corrects a record.
"""

from __future__ import annotations

import logging
from uuid import UUID, uuid4

from sqlalchemy import exists, select
from sqlalchemy.orm import Session, aliased

from app.core.errors import AppError, ConflictError, NotFoundError
from app.core.logging import log_event
from app.core.time import utcnow
from app.models import LearnerProfile
from app.models.learner_records import (
    AssessmentRecord,
    LearnerKnowledge,
    LearningActivity,
    LearningGoal,
    LearningPreference,
    MisconceptionRecord,
)
from app.schemas.learner import (
    ActivityCreate,
    ActivityRead,
    AssessmentCreate,
    AssessmentRead,
    GoalCreate,
    GoalRead,
    GoalUpdate,
    KnowledgeCorrection,
    KnowledgeCreate,
    KnowledgeRead,
    LearnerDashboard,
    MisconceptionCorrection,
    MisconceptionCreate,
    MisconceptionRead,
    PreferenceRead,
    PreferenceWrite,
    ProfileRead,
    ProfileUpdate,
    SessionHistoryRead,
)
from app.services.sessions import get_session as get_learning_session
from app.services.topics import get_topic

logger = logging.getLogger(__name__)


def update_profile(session: Session, profile: LearnerProfile, payload: ProfileUpdate) -> LearnerProfile:
    if "display_name" in payload.model_fields_set:
        profile.display_name = payload.display_name or profile.display_name
    if "background_note" in payload.model_fields_set:
        profile.background_note = payload.background_note
    profile.updated_at = utcnow()
    session.flush()
    log_event(logger, logging.INFO, "profile_updated", learner_id=profile.id)
    return profile


def get_preferences(session: Session, learner_id: UUID) -> LearningPreference | None:
    return session.scalar(select(LearningPreference).where(LearningPreference.learner_id == learner_id))


def save_preferences(session: Session, learner_id: UUID, payload: PreferenceWrite) -> LearningPreference:
    row = get_preferences(session, learner_id)
    now = utcnow()
    if row is None:
        row = LearningPreference(
            id=uuid4(),
            learner_id=learner_id,
            pace=payload.pace,
            explanation_detail=payload.explanation_detail,
            practice_first=payload.practice_first,
            notes=payload.notes,
            updated_at=now,
        )
        session.add(row)
    else:
        row.pace = payload.pace
        row.explanation_detail = payload.explanation_detail
        row.practice_first = payload.practice_first
        row.notes = payload.notes
        row.updated_at = now
    session.flush()
    log_event(logger, logging.INFO, "preferences_saved", learner_id=learner_id)
    return row


def _require_topic(session: Session, topic_id: UUID):
    return get_topic(session, topic_id)


def _require_owned_session(session: Session, learner_id: UUID, session_id: UUID):
    item = get_learning_session(session, session_id)
    if item.learner_id != learner_id:
        log_event(logger, logging.WARNING, "session_not_found", session_id=session_id)
        raise NotFoundError("session_not_found", "Learning session was not found.")
    return item


def list_goals(session: Session, learner_id: UUID) -> list[LearningGoal]:
    statement = (
        select(LearningGoal)
        .where(LearningGoal.learner_id == learner_id)
        .order_by(LearningGoal.created_at.asc(), LearningGoal.id.asc())
    )
    return list(session.scalars(statement).all())


def create_goal(session: Session, learner_id: UUID, payload: GoalCreate) -> LearningGoal:
    if payload.topic_id is not None:
        _require_topic(session, payload.topic_id)
    row = LearningGoal(
        id=uuid4(),
        learner_id=learner_id,
        topic_id=payload.topic_id,
        statement=payload.statement,
        status="active",
    )
    session.add(row)
    session.flush()
    log_event(logger, logging.INFO, "goal_created", learner_id=learner_id, goal_id=row.id, topic_id=row.topic_id)
    return row


def update_goal(session: Session, learner_id: UUID, goal_id: UUID, payload: GoalUpdate) -> LearningGoal:
    row = session.get(LearningGoal, goal_id)
    if row is None or row.learner_id != learner_id:
        log_event(logger, logging.WARNING, "goal_not_found", goal_id=goal_id)
        raise NotFoundError("goal_not_found", "Learning goal was not found.")
    if payload.statement is not None:
        row.statement = payload.statement
    if payload.status is not None:
        row.status = payload.status
    row.updated_at = utcnow()
    session.flush()
    log_event(logger, logging.INFO, "goal_updated", learner_id=learner_id, goal_id=row.id, status=row.status)
    return row


def _current_filter(model, id_column):
    replacement = aliased(model)
    return ~exists(select(replacement.id).where(replacement.replaces_id == id_column))


def list_knowledge(
    session: Session,
    learner_id: UUID,
    *,
    topic_id: UUID | None = None,
    history: bool = False,
) -> list[LearnerKnowledge]:
    statement = select(LearnerKnowledge).where(LearnerKnowledge.learner_id == learner_id)
    if topic_id is not None:
        statement = statement.where(LearnerKnowledge.topic_id == topic_id)
    if not history:
        statement = statement.where(_current_filter(LearnerKnowledge, LearnerKnowledge.id))
        statement = statement.order_by(LearnerKnowledge.created_at.desc(), LearnerKnowledge.id.desc())
    else:
        statement = statement.order_by(LearnerKnowledge.created_at.asc(), LearnerKnowledge.id.asc())
    return list(session.scalars(statement).all())


def record_knowledge(session: Session, learner_id: UUID, payload: KnowledgeCreate) -> LearnerKnowledge:
    _require_topic(session, payload.topic_id)
    row = LearnerKnowledge(
        id=uuid4(),
        learner_id=learner_id,
        topic_id=payload.topic_id,
        concept=payload.concept,
        summary=payload.summary,
        evidence_kind=payload.evidence_kind,
        confidence=payload.confidence,
        provenance=payload.provenance,
    )
    session.add(row)
    session.flush()
    log_event(
        logger,
        logging.INFO,
        "knowledge_recorded",
        learner_id=learner_id,
        knowledge_id=row.id,
        topic_id=row.topic_id,
        evidence_kind=row.evidence_kind,
    )
    return row


def correct_knowledge(
    session: Session,
    learner_id: UUID,
    knowledge_id: UUID,
    payload: KnowledgeCorrection,
) -> LearnerKnowledge:
    current = _replaceable(session, LearnerKnowledge, learner_id, knowledge_id, "knowledge_not_found", "Knowledge record was not found.")
    row = LearnerKnowledge(
        id=uuid4(),
        learner_id=current.learner_id,
        topic_id=current.topic_id,
        concept=payload.concept or current.concept,
        summary=payload.summary or current.summary,
        evidence_kind=current.evidence_kind,
        confidence=current.confidence if payload.confidence is None else payload.confidence,
        provenance=current.provenance,
        correction_note=payload.correction_note,
        corrected_at=utcnow(),
        replaces_id=current.id,
    )
    session.add(row)
    session.flush()
    log_event(
        logger,
        logging.INFO,
        "knowledge_corrected",
        learner_id=learner_id,
        knowledge_id=row.id,
        replaces_id=current.id,
        evidence_kind=row.evidence_kind,
    )
    return row


def list_misconceptions(
    session: Session,
    learner_id: UUID,
    *,
    topic_id: UUID | None = None,
    history: bool = False,
) -> list[MisconceptionRecord]:
    statement = select(MisconceptionRecord).where(MisconceptionRecord.learner_id == learner_id)
    if topic_id is not None:
        statement = statement.where(MisconceptionRecord.topic_id == topic_id)
    if not history:
        statement = statement.where(_current_filter(MisconceptionRecord, MisconceptionRecord.id))
        statement = statement.order_by(MisconceptionRecord.created_at.desc(), MisconceptionRecord.id.desc())
    else:
        statement = statement.order_by(MisconceptionRecord.created_at.asc(), MisconceptionRecord.id.asc())
    return list(session.scalars(statement).all())


def record_misconception(session: Session, learner_id: UUID, payload: MisconceptionCreate) -> MisconceptionRecord:
    _require_topic(session, payload.topic_id)
    row = MisconceptionRecord(
        id=uuid4(),
        learner_id=learner_id,
        topic_id=payload.topic_id,
        concept=payload.concept,
        description=payload.description,
        evidence_kind=payload.evidence_kind,
        confidence=payload.confidence,
        provenance=payload.provenance,
        supporting_note=payload.supporting_note,
        status="open",
    )
    session.add(row)
    session.flush()
    log_event(
        logger,
        logging.INFO,
        "misconception_recorded",
        learner_id=learner_id,
        misconception_id=row.id,
        topic_id=row.topic_id,
        evidence_kind=row.evidence_kind,
    )
    return row


def correct_misconception(
    session: Session,
    learner_id: UUID,
    misconception_id: UUID,
    payload: MisconceptionCorrection,
) -> MisconceptionRecord:
    current = _replaceable(
        session,
        MisconceptionRecord,
        learner_id,
        misconception_id,
        "misconception_not_found",
        "Misconception record was not found.",
    )
    row = MisconceptionRecord(
        id=uuid4(),
        learner_id=current.learner_id,
        topic_id=current.topic_id,
        concept=current.concept,
        description=payload.description or current.description,
        evidence_kind=current.evidence_kind,
        confidence=current.confidence,
        provenance=current.provenance,
        supporting_note=current.supporting_note,
        status=payload.status or current.status,
        correction_note=payload.correction_note,
        corrected_at=utcnow(),
        replaces_id=current.id,
    )
    session.add(row)
    session.flush()
    log_event(
        logger,
        logging.INFO,
        "misconception_corrected",
        learner_id=learner_id,
        misconception_id=row.id,
        replaces_id=current.id,
        evidence_kind=row.evidence_kind,
        status=row.status,
    )
    return row


def list_assessments(session: Session, learner_id: UUID, topic_id: UUID | None = None) -> list[AssessmentRecord]:
    statement = select(AssessmentRecord).where(AssessmentRecord.learner_id == learner_id)
    if topic_id is not None:
        statement = statement.where(AssessmentRecord.topic_id == topic_id)
    statement = statement.order_by(AssessmentRecord.created_at.asc(), AssessmentRecord.id.asc())
    return list(session.scalars(statement).all())


def record_assessment(session: Session, learner_id: UUID, payload: AssessmentCreate) -> AssessmentRecord:
    _require_topic(session, payload.topic_id)
    if payload.session_id is not None:
        learning_session = _require_owned_session(session, learner_id, payload.session_id)
        if learning_session.topic_id != payload.topic_id:
            raise AppError("session_topic_mismatch", "The session is for a different topic.", 422)
    row = AssessmentRecord(
        id=uuid4(),
        learner_id=learner_id,
        topic_id=payload.topic_id,
        session_id=payload.session_id,
        prompt_summary=payload.prompt_summary,
        response_summary=payload.response_summary,
        outcome=payload.outcome,
    )
    session.add(row)
    session.flush()
    log_event(
        logger,
        logging.INFO,
        "assessment_recorded",
        learner_id=learner_id,
        assessment_id=row.id,
        topic_id=row.topic_id,
        outcome=row.outcome,
    )
    return row


def list_activities(session: Session, learner_id: UUID) -> list[LearningActivity]:
    statement = (
        select(LearningActivity)
        .where(LearningActivity.learner_id == learner_id)
        .order_by(LearningActivity.occurred_at.asc(), LearningActivity.id.asc())
    )
    return list(session.scalars(statement).all())


def record_activity(session: Session, learner_id: UUID, payload: ActivityCreate) -> LearningActivity:
    if payload.topic_id is not None:
        _require_topic(session, payload.topic_id)
    if payload.session_id is not None:
        learning_session = _require_owned_session(session, learner_id, payload.session_id)
        if payload.topic_id is not None and learning_session.topic_id != payload.topic_id:
            raise AppError("session_topic_mismatch", "The session is for a different topic.", 422)
    row = LearningActivity(
        id=uuid4(),
        learner_id=learner_id,
        topic_id=payload.topic_id,
        session_id=payload.session_id,
        activity_kind=payload.activity_kind,
        summary=payload.summary,
        occurred_at=payload.occurred_at or utcnow(),
    )
    session.add(row)
    session.flush()
    log_event(
        logger,
        logging.INFO,
        "activity_recorded",
        learner_id=learner_id,
        activity_id=row.id,
        topic_id=row.topic_id,
        activity_kind=row.activity_kind,
    )
    return row


def dashboard(session: Session, profile: LearnerProfile) -> LearnerDashboard:
    preferences = get_preferences(session, profile.id)
    return LearnerDashboard(
        profile=ProfileRead.model_validate(profile),
        preferences=PreferenceRead.model_validate(preferences) if preferences is not None else None,
        goals=[GoalRead.model_validate(item) for item in list_goals(session, profile.id)],
        knowledge=[KnowledgeRead.model_validate(item) for item in list_knowledge(session, profile.id)],
        misconceptions=[
            MisconceptionRead.model_validate(item) for item in list_misconceptions(session, profile.id)
        ],
        assessments=[AssessmentRead.model_validate(item) for item in list_assessments(session, profile.id)],
        activities=[ActivityRead.model_validate(item) for item in list_activities(session, profile.id)],
    )


def history_for_session(session: Session, learning_session) -> SessionHistoryRead:
    learner_id = learning_session.learner_id
    topic_id = learning_session.topic_id
    profile = learning_session.learner
    preferences = get_preferences(session, learner_id)
    goals = [
        item
        for item in list_goals(session, learner_id)
        if item.topic_id is None or item.topic_id == topic_id
    ]
    knowledge = list_knowledge(session, learner_id, topic_id=topic_id, history=True)
    misconceptions = list_misconceptions(session, learner_id, topic_id=topic_id, history=True)
    assessments = list_assessments(session, learner_id, topic_id=topic_id)
    activities = [
        item
        for item in list_activities(session, learner_id)
        if item.topic_id == topic_id or item.session_id == learning_session.id
    ]
    return SessionHistoryRead(
        session_id=learning_session.id,
        learner_id=learner_id,
        topic_id=topic_id,
        topic_title=learning_session.topic.title,
        profile=ProfileRead.model_validate(profile),
        preferences=PreferenceRead.model_validate(preferences) if preferences is not None else None,
        goals=[GoalRead.model_validate(item) for item in goals],
        knowledge=[KnowledgeRead.model_validate(item) for item in knowledge],
        misconceptions=[MisconceptionRead.model_validate(item) for item in misconceptions],
        assessments=[AssessmentRead.model_validate(item) for item in assessments],
        activities=[ActivityRead.model_validate(item) for item in activities],
    )


def _replaceable(session: Session, model, learner_id: UUID, record_id: UUID, code: str, message: str):
    row = session.get(model, record_id)
    if row is None or row.learner_id != learner_id:
        log_event(logger, logging.WARNING, code, record_id=record_id)
        raise NotFoundError(code, message)
    replacement = session.scalar(select(model.id).where(model.replaces_id == record_id))
    if replacement is not None:
        raise ConflictError("record_already_corrected", "Correct the latest record.")
    return row
