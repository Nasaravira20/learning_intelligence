from __future__ import annotations

from uuid import UUID

from sqlalchemy import select as sql_select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.core.time import utcnow
from app.models.diagnostics import LearningObjective
from app.models.entities import LearningSession
from app.models.pedagogy import PedagogySelection
from app.models.planning import LearningPlan, LearningPlanStep
from app.pedagogy.registry import RegistryValidationError, load_registry
from app.pedagogy.selector import POLICY_VERSION, SelectorInput, SelectionDecision
from app.pedagogy.selector import select as choose_strategies
from app.schemas.pedagogy import SelectionRead


def get_selection(db: Session, learning_session: LearningSession) -> SelectionRead:
    row = _active(db, learning_session.id)
    if row is None:
        raise NotFoundError("selection_not_found", "This session has no pedagogy selection.")
    return SelectionRead.from_row(row, learning_session.status)


def record_selection(
    db: Session,
    learning_session: LearningSession,
    context: SelectorInput | None,
) -> SelectionRead:
    if learning_session.status != "PLAN_READY":
        raise ConflictError(
            "selection_not_ready",
            "Choose strategies after the learning plan is ready.",
        )
    if context is None:
        context = context_from_plan(db, learning_session)
    try:
        registry = load_registry()
    except RegistryValidationError as exc:
        raise ConflictError("registry_invalid", "The pedagogy registry failed validation.") from exc
    decision = choose_strategies(context, registry, production=True)
    current = _active(db, learning_session.id)
    if (
        current is not None
        and current.input_fingerprint == decision.input_fingerprint
        and current.policy_version == decision.policy_version
        and current.registry_version == decision.registry_version
    ):
        return SelectionRead.from_row(current, learning_session.status)
    revision = 1
    if current is not None:
        current.status = "superseded"
        revision = current.revision + 1
    row = _write(db, learning_session, decision, revision)
    db.commit()
    db.refresh(row)
    return SelectionRead.from_row(row, learning_session.status)


def save_decision(db: Session, learning_session: LearningSession, decision: SelectionDecision) -> SelectionRead:
    current = _active(db, learning_session.id)
    revision = 1
    if current is not None:
        current.status = "superseded"
        revision = current.revision + 1
        db.flush()
    row = _write(db, learning_session, decision, revision)
    return SelectionRead.from_row(row, learning_session.status)


def context_from_plan(db: Session, learning_session: LearningSession) -> SelectorInput:
    plan = db.scalar(
        sql_select(LearningPlan).where(
            LearningPlan.session_id == learning_session.id,
            LearningPlan.status == "active",
        )
    )
    if plan is None:
        raise NotFoundError("plan_not_found", "This session has no learning plan.")
    steps = list(
        db.scalars(
            sql_select(LearningPlanStep).where(LearningPlanStep.plan_id == plan.id).order_by(LearningPlanStep.position)
        )
    )
    objectives = {
        item.id: item
        for item in db.scalars(sql_select(LearningObjective).where(LearningObjective.topic_id == learning_session.topic_id))
    }
    satisfied: list[str] = []
    gaps: list[str] = []
    current_code = ""
    for step in steps:
        objective = objectives.get(step.objective_id)
        if objective is None:
            continue
        if step.status == "satisfied":
            satisfied.append(objective.code)
        else:
            gaps.append(objective.code)
        if step.id == plan.current_step_id:
            current_code = objective.code
    if not current_code and gaps:
        current_code = gaps[0]
    if not current_code and satisfied:
        current_code = satisfied[-1]
    level = "proficient" if not gaps else "beginner" if not satisfied else "partial"
    stage = "initial_teaching" if not satisfied else "practice"
    topic = learning_session.topic.title if learning_session.topic is not None else "topic"
    return SelectorInput(
        topic=topic,
        learning_objective=current_code or topic,
        learner_level=level,  # type: ignore[arg-type]
        prior_knowledge=satisfied,
        knowledge_gaps=gaps,
        misconceptions=[],
        recent_performance=[],
        session_stage=stage,  # type: ignore[arg-type]
        time_available_minutes=20,
        previous_strategy_outcomes=[],
    )


def _active(db: Session, session_id: UUID) -> PedagogySelection | None:
    return db.scalar(
        sql_select(PedagogySelection).where(
            PedagogySelection.session_id == session_id,
            PedagogySelection.status == "active",
        )
    )


def _write(
    db: Session,
    learning_session: LearningSession,
    decision: SelectionDecision,
    revision: int,
) -> PedagogySelection:
    row = PedagogySelection(
        session_id=learning_session.id,
        learner_id=learning_session.learner_id,
        revision=revision,
        status="active",
        policy_version=decision.policy_version or POLICY_VERSION,
        registry_version=decision.registry_version,
        situation=decision.situation,
        primary_strategy_id=decision.primary_strategy,
        supporting_strategy_ids=decision.supporting_strategies,
        sequence=decision.sequence,
        success_signals=decision.success_signals,
        fallback_strategy_id=decision.fallback_strategy,
        rationale=decision.rationale,
        controls_teaching=False,
        production_primary_strategy_id=decision.production_primary_strategy,
        rejected=[item.model_dump() for item in decision.rejected],
        input_fingerprint=decision.input_fingerprint,
        created_at=utcnow(),
    )
    db.add(row)
    db.flush()
    return row
