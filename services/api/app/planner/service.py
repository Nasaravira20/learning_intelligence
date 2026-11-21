from __future__ import annotations

import logging
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError, ConflictError, NotFoundError
from app.core.logging import log_event
from app.core.time import utcnow
from app.diagnostics.policy import ObjectiveNode
from app.models import LearningSession
from app.models.diagnostics import DiagnosticAttempt, DiagnosticQuestion, DiagnosticResponse, LearningObjective, ObjectivePrerequisite
from app.models.planning import LearningPlan, LearningPlanStep, TopicConcept
from app.planner.policy import StepDraft, plan_sequence, plan_summary, sequence_fingerprint
from app.schemas.learner import ActivityCreate
from app.schemas.planning import ConceptRead, LearningPlanRead, PlanStepRead
from app.services import learner_intelligence as intelligence
from app.services.sessions import enter_plan
from app.services.topics import get_topic

logger = logging.getLogger(__name__)


def list_concepts(session: Session, topic_id: UUID) -> list[ConceptRead]:
    get_topic(session, topic_id)
    rows = session.scalars(
        select(TopicConcept).where(TopicConcept.topic_id == topic_id).order_by(TopicConcept.position, TopicConcept.name_key)
    ).all()
    return [_concept_read(row) for row in rows]


def create_plan(session: Session, learning_session: LearningSession) -> LearningPlanRead:
    if _active_plan(session, learning_session.id) is not None:
        raise ConflictError("plan_exists", "This session already has a learning plan. Revise it when evidence changes.")
    attempt = _plan_attempt(session, learning_session)
    plan = _write_plan(session, learning_session, attempt, revision=1)
    if learning_session.status != "PLAN_READY":
        enter_plan(session, learning_session)
    return _read(session, learning_session, plan)


def get_plan(session: Session, learning_session: LearningSession) -> LearningPlanRead:
    plan = _active_plan(session, learning_session.id)
    if plan is None:
        raise NotFoundError("plan_not_found", "This session has no learning plan.")
    return _read(session, learning_session, plan)


def revise_plan(session: Session, learning_session: LearningSession) -> LearningPlanRead:
    if learning_session.status != "PLAN_READY":
        raise AppError("invalid_transition", "Revise a plan after the session has one.", 409)
    current = _active_plan(session, learning_session.id)
    if current is None:
        raise NotFoundError("plan_not_found", "This session has no learning plan.")
    attempt = _plan_attempt(session, learning_session)
    drafts = _drafts(session, learning_session, attempt)
    if sequence_fingerprint(drafts) == _stored_fingerprint(session, current):
        raise ConflictError("plan_unchanged", "The plan already matches the latest diagnostic evidence.")
    now = utcnow()
    current.status = "superseded"
    current.updated_at = now
    session.flush()
    plan = _write_plan(session, learning_session, attempt, revision=current.revision + 1)
    return _read(session, learning_session, plan)


def _plan_attempt(session: Session, learning_session: LearningSession) -> DiagnosticAttempt:
    open_attempt = _open_attempt(session, learning_session.id)
    attempt = _latest_completed(session, learning_session.id)
    if open_attempt is not None and attempt is None:
        raise ConflictError("diagnosis_incomplete", "Complete the diagnosis before building a learning plan.")
    if open_attempt is not None:
        raise ConflictError("diagnosis_open", "Finish the diagnostic follow-up before changing the plan.")
    if attempt is None:
        raise NotFoundError("diagnosis_not_found", "This session has no diagnosis.")
    if learning_session.status not in {"DIAGNOSING", "PLAN_READY"}:
        raise AppError("invalid_transition", "This session cannot open a learning plan.", 409)
    return attempt


def _write_plan(session: Session, learning_session: LearningSession, attempt: DiagnosticAttempt, revision: int) -> LearningPlan:
    drafts = _drafts(session, learning_session, attempt)
    concepts = _sync_concepts(session, learning_session.topic_id, drafts)
    objectives = {
        row.code: row
        for row in session.scalars(select(LearningObjective).where(LearningObjective.topic_id == learning_session.topic_id)).all()
    }
    now = utcnow()
    plan = LearningPlan(
        session_id=learning_session.id,
        learner_id=learning_session.learner_id,
        topic_id=learning_session.topic_id,
        diagnostic_attempt_id=attempt.id,
        revision=revision,
        status="active",
        summary=plan_summary(drafts),
        created_at=now,
        updated_at=now,
    )
    session.add(plan)
    session.flush()
    current_step: LearningPlanStep | None = None
    for position, draft in enumerate(drafts):
        step = LearningPlanStep(
            plan_id=plan.id,
            concept_id=concepts[draft.concept.strip().lower()].id,
            objective_id=objectives[draft.code].id,
            position=position,
            status=draft.status,
            evidence=draft.evidence,
            completion_criteria=draft.completion_criteria,
        )
        session.add(step)
        if draft.status == "current":
            current_step = step
    session.flush()
    if current_step is not None:
        plan.current_step_id = current_step.id
        session.flush()
    starting = next((draft.code for draft in drafts if draft.status == "current"), None)
    if starting is None:
        activity = f"Learning plan revision {revision} already has observed evidence for every objective."
    else:
        activity = f"Learning plan revision {revision} starts at {starting}."
    intelligence.record_activity(
        session,
        learning_session.learner_id,
        ActivityCreate(
            topic_id=learning_session.topic_id,
            session_id=learning_session.id,
            activity_kind="note",
            summary=activity[:500],
        ),
    )
    learning_session.updated_at = now
    session.flush()
    log_event(
        logger,
        logging.INFO,
        "plan_revised" if revision > 1 else "plan_created",
        session_id=learning_session.id,
        plan_id=plan.id,
        revision=revision,
        step_count=len(drafts),
    )
    return plan


def _drafts(session: Session, learning_session: LearningSession, attempt: DiagnosticAttempt) -> list[StepDraft]:
    rows = list(
        session.scalars(
            select(LearningObjective)
            .where(LearningObjective.topic_id == learning_session.topic_id)
            .order_by(LearningObjective.position, LearningObjective.code)
        ).all()
    )
    if not rows:
        raise AppError("objectives_required", "Define at least one learning objective before a learning plan.", 422)
    prerequisites = _prerequisite_map(session, [row.id for row in rows])
    nodes = [
        ObjectiveNode(
            code=row.code,
            concept=row.concept,
            statement=row.statement,
            position=row.position,
            prerequisite_codes=tuple(prerequisites.get(row.id, [])),
        )
        for row in rows
    ]
    return plan_sequence(nodes, _evidence(session, attempt))


def _evidence(session: Session, attempt: DiagnosticAttempt) -> dict[str, tuple[str, str, str, Decimal] | None]:
    questions = list(
        session.scalars(select(DiagnosticQuestion).where(DiagnosticQuestion.attempt_id == attempt.id)).all()
    )
    if not questions:
        return {}
    responses = {
        row.question_id: row
        for row in session.scalars(
            select(DiagnosticResponse).where(DiagnosticResponse.question_id.in_([question.id for question in questions]))
        ).all()
    }
    objectives = {
        row.id: row
        for row in session.scalars(
            select(LearningObjective).where(LearningObjective.id.in_([question.objective_id for question in questions]))
        ).all()
    }
    evidence: dict[str, tuple[str, str, str, Decimal] | None] = {}
    for question in questions:
        objective = objectives.get(question.objective_id)
        if objective is None:
            continue
        response = responses.get(question.id)
        if response is None:
            evidence[objective.code] = None
            continue
        evidence[objective.code] = (
            response.understanding,
            response.answer_verdict,
            response.reasoning_verdict,
            Decimal(response.confidence),
        )
    return evidence


def _sync_concepts(session: Session, topic_id: UUID, drafts: list[StepDraft]) -> dict[str, TopicConcept]:
    existing = {
        row.name_key: row
        for row in session.scalars(select(TopicConcept).where(TopicConcept.topic_id == topic_id)).all()
    }
    statements: dict[str, list[str]] = {}
    order: list[tuple[str, str]] = []
    for draft in drafts:
        key = draft.concept.strip().lower()
        statements.setdefault(key, [])
        if draft.statement not in statements[key]:
            statements[key].append(draft.statement)
        if key not in {item[0] for item in order}:
            order.append((key, draft.concept.strip()))
    concepts: dict[str, TopicConcept] = {}
    for position, (key, name) in enumerate(order):
        summary = _concept_summary(name, statements[key])
        row = existing.get(key)
        if row is None:
            row = TopicConcept(topic_id=topic_id, name=name, name_key=key, summary=summary, position=position)
            session.add(row)
        else:
            row.name = name
            row.summary = summary
            row.position = position
        concepts[key] = row
    session.flush()
    return concepts


def _concept_summary(name: str, statements: list[str]) -> str:
    text = f"{name}: " + "; ".join(statements)
    return text[:500]


def _active_plan(session: Session, session_id: UUID) -> LearningPlan | None:
    return session.scalar(
        select(LearningPlan).where(LearningPlan.session_id == session_id, LearningPlan.status == "active")
    )


def _open_attempt(session: Session, session_id: UUID) -> DiagnosticAttempt | None:
    return session.scalar(
        select(DiagnosticAttempt).where(
            DiagnosticAttempt.session_id == session_id,
            DiagnosticAttempt.status == "in_progress",
        )
    )


def _latest_completed(session: Session, session_id: UUID) -> DiagnosticAttempt | None:
    return session.scalar(
        select(DiagnosticAttempt)
        .where(DiagnosticAttempt.session_id == session_id, DiagnosticAttempt.status == "completed")
        .order_by(DiagnosticAttempt.completed_at.desc(), DiagnosticAttempt.id.desc())
        .limit(1)
    )


def _prerequisite_map(session: Session, objective_ids: list[UUID]) -> dict[UUID, list[str]]:
    if not objective_ids:
        return {}
    rows = session.execute(
        select(ObjectivePrerequisite.objective_id, LearningObjective.code)
        .join(LearningObjective, LearningObjective.id == ObjectivePrerequisite.prerequisite_id)
        .where(ObjectivePrerequisite.objective_id.in_(objective_ids))
        .order_by(LearningObjective.position, LearningObjective.code)
    ).all()
    grouped: dict[UUID, list[str]] = {item_id: [] for item_id in objective_ids}
    for objective_id, code in rows:
        grouped[objective_id].append(code)
    return grouped


def _stored_fingerprint(session: Session, plan: LearningPlan) -> tuple[tuple[str, str, str], ...]:
    steps = list(
        session.scalars(
            select(LearningPlanStep).where(LearningPlanStep.plan_id == plan.id).order_by(LearningPlanStep.position)
        ).all()
    )
    codes = {
        row.id: row.code
        for row in session.scalars(
            select(LearningObjective).where(LearningObjective.id.in_([step.objective_id for step in steps]))
        ).all()
    } if steps else {}
    return tuple((codes[step.objective_id], step.status, step.evidence) for step in steps)


def _read(session: Session, learning_session: LearningSession, plan: LearningPlan) -> LearningPlanRead:
    steps = list(
        session.scalars(
            select(LearningPlanStep).where(LearningPlanStep.plan_id == plan.id).order_by(LearningPlanStep.position)
        ).all()
    )
    objectives = {
        row.id: row
        for row in session.scalars(
            select(LearningObjective).where(LearningObjective.id.in_([step.objective_id for step in steps]))
        ).all()
    } if steps else {}
    concepts = {
        row.id: row
        for row in session.scalars(
            select(TopicConcept).where(TopicConcept.id.in_([step.concept_id for step in steps]))
        ).all()
    } if steps else {}
    ordered_concepts = sorted(concepts.values(), key=lambda row: (row.position, row.name_key))
    starting = None
    if plan.current_step_id is not None:
        current = next((step for step in steps if step.id == plan.current_step_id), None)
        if current is not None and current.objective_id in objectives:
            starting = objectives[current.objective_id].code
    return LearningPlanRead(
        id=plan.id,
        session_id=plan.session_id,
        topic_id=plan.topic_id,
        revision=plan.revision,
        status=plan.status,  # type: ignore[arg-type]
        session_status=learning_session.status,
        diagnostic_attempt_id=plan.diagnostic_attempt_id,
        starting_objective_code=starting,
        summary=plan.summary,
        current_step_id=plan.current_step_id,
        concepts=[_concept_read(row) for row in ordered_concepts],
        steps=[
            PlanStepRead(
                id=step.id,
                position=step.position,
                objective_id=step.objective_id,
                objective_code=objectives[step.objective_id].code,
                objective_statement=objectives[step.objective_id].statement,
                concept_id=step.concept_id,
                concept=concepts[step.concept_id].name,
                status=step.status,  # type: ignore[arg-type]
                evidence=step.evidence,  # type: ignore[arg-type]
                completion_criteria=step.completion_criteria,
            )
            for step in steps
        ],
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )


def _concept_read(row: TopicConcept) -> ConceptRead:
    return ConceptRead(id=row.id, topic_id=row.topic_id, name=row.name, position=row.position, summary=row.summary)
