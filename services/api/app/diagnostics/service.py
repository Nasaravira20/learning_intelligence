from __future__ import annotations

import logging
import re
from decimal import Decimal
from uuid import UUID

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
from app.diagnostics.policy import (
    CONFIDENCE,
    ObjectiveNode,
    align_judgments,
    align_questions,
    classify_starting_point,
    diagnosis_summary,
    item_is_uncertain,
    knowledge_decision,
    needs_review,
)
from app.diagnostics.prompts import judgment_prompt, question_prompt
from app.diagnostics.schemas import ItemJudgment, JudgmentSet, QuestionSet
from app.models import LearningSession
from app.models.diagnostics import (
    DiagnosticAttempt,
    DiagnosticQuestion,
    DiagnosticResponse,
    LearningObjective,
    ObjectivePrerequisite,
)
from app.models.learner_records import MisconceptionRecord
from app.schemas.diagnostics import (
    DiagnosisJudgmentRead,
    DiagnosisMisconceptionRead,
    DiagnosisQuestionRead,
    DiagnosisReport,
    ObjectiveCreate,
    ObjectiveRead,
    ResponseInput,
)
from app.schemas.learner import AssessmentCreate, KnowledgeCreate, MisconceptionCreate
from app.services import learner_intelligence as intelligence
from app.services.sessions import enter_diagnosis
from app.services.topics import get_topic

logger = logging.getLogger(__name__)

CODE_RE = re.compile(r"^[a-z0-9]+([.\-][a-z0-9]+)*$")
MAX_OBJECTIVES = 8


def _code(value: str) -> str:
    cleaned = value.strip()
    if CODE_RE.fullmatch(cleaned) is None:
        raise AppError("validation_error", "An objective code uses lowercase letters, numbers, dots, and hyphens.", 422)
    return cleaned


def _objectives(session: Session, topic_id: UUID) -> list[LearningObjective]:
    statement = (
        select(LearningObjective)
        .where(LearningObjective.topic_id == topic_id)
        .order_by(LearningObjective.position, LearningObjective.code)
    )
    return list(session.scalars(statement).all())


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


def _nodes(rows: list[LearningObjective], prerequisites: dict[UUID, list[str]]) -> list[ObjectiveNode]:
    return [
        ObjectiveNode(
            code=row.code,
            concept=row.concept,
            statement=row.statement,
            position=row.position,
            prerequisite_codes=tuple(prerequisites.get(row.id, [])),
        )
        for row in rows
    ]


def _observed_concepts(session: Session, learner_id: UUID, topic_id: UUID) -> list[str]:
    concepts = [
        row.concept.strip()
        for row in intelligence.list_knowledge(session, learner_id, topic_id=topic_id)
        if row.evidence_kind == "observed" and row.concept.strip()
    ]
    return sorted(set(concepts), key=str.lower)


def create_objective(session: Session, topic_id: UUID, payload: ObjectiveCreate) -> ObjectiveRead:
    get_topic(session, topic_id)
    code = _code(payload.code)
    existing = _objectives(session, topic_id)
    if any(item.code == code for item in existing):
        raise ConflictError("objective_exists", "That objective code is already on this topic.")
    by_code = {item.code: item for item in existing}
    missing = [item for item in payload.prerequisite_codes if _code(item) not in by_code]
    if missing:
        raise AppError("prerequisite_not_found", "A prerequisite objective must already exist on this topic.", 422)
    if code in {_code(item) for item in payload.prerequisite_codes}:
        raise AppError("validation_error", "An objective cannot be its own prerequisite.", 422)
    position = payload.position if payload.position is not None else len(existing)
    row = LearningObjective(
        topic_id=topic_id,
        code=code,
        statement=payload.statement.strip(),
        concept=payload.concept.strip(),
        position=position,
    )
    session.add(row)
    session.flush()
    for prerequisite_code in payload.prerequisite_codes:
        session.add(
            ObjectivePrerequisite(
                objective_id=row.id,
                prerequisite_id=by_code[_code(prerequisite_code)].id,
            )
        )
    session.flush()
    log_event(logger, logging.INFO, "objective_defined", topic_id=topic_id, objective_id=row.id, position=row.position)
    return _objective_read(row, [_code(item) for item in payload.prerequisite_codes])


def list_objective_reads(session: Session, topic_id: UUID) -> list[ObjectiveRead]:
    get_topic(session, topic_id)
    rows = _objectives(session, topic_id)
    prerequisites = _prerequisite_map(session, [row.id for row in rows])
    return [_objective_read(row, prerequisites.get(row.id, [])) for row in rows]


def _objective_read(row: LearningObjective, prerequisite_codes: list[str]) -> ObjectiveRead:
    return ObjectiveRead(
        id=row.id,
        topic_id=row.topic_id,
        code=row.code,
        statement=row.statement,
        concept=row.concept,
        position=row.position,
        prerequisite_codes=prerequisite_codes,
        created_at=row.created_at,
    )


def _attempt_for_session(session: Session, learning_session: LearningSession) -> DiagnosticAttempt | None:
    return session.scalar(select(DiagnosticAttempt).where(DiagnosticAttempt.session_id == learning_session.id))


def _complete_model(session: Session, provider: ModelProvider, task: str, prompt: str, output_model: type, action_id: str):
    if len(prompt) > 4000:
        raise AppError("validation_error", "The model prompt is too long.", 422)
    settings = get_settings()
    if settings.ai_provider == "gemini":
        _result, parsed = generate(
            session,
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
        log_event(logger, logging.WARNING, "diagnosis_output_rejected", error_class="malformed_output", task=task)
        raise AppError("malformed_output", "The model output did not match the required schema.", 422) from None


def start_diagnosis(session: Session, provider: ModelProvider, learning_session: LearningSession) -> DiagnosisReport:
    current = _attempt_for_session(session, learning_session)
    if current is not None:
        return report_for(session, learning_session, current)
    rows = _objectives(session, learning_session.topic_id)
    if not rows:
        raise AppError("objectives_required", "Define at least one learning objective before a diagnosis.", 422)
    if len(rows) > MAX_OBJECTIVES:
        raise AppError("too_many_objectives", "A diagnosis covers at most eight objectives.", 422)
    prerequisites = _prerequisite_map(session, [row.id for row in rows])
    nodes = _nodes(rows, prerequisites)
    observed = _observed_concepts(session, learning_session.learner_id, learning_session.topic_id)
    prompt = question_prompt(nodes, observed)
    parsed = _complete_model(
        session,
        provider,
        "diagnostic",
        prompt,
        QuestionSet,
        f"diagnosis-questions:{learning_session.id}",
    )
    assert isinstance(parsed, QuestionSet)
    align_questions(nodes, parsed.questions)
    enter_diagnosis(session, learning_session)
    attempt = DiagnosticAttempt(
        session_id=learning_session.id,
        learner_id=learning_session.learner_id,
        topic_id=learning_session.topic_id,
        status="in_progress",
    )
    session.add(attempt)
    session.flush()
    by_code = {row.code: row for row in rows}
    ordered = {item.objective_code: index for index, item in enumerate(parsed.questions)}
    for draft in parsed.questions:
        choices = None
        if draft.format == "multiple_choice":
            choices = [choice.strip() for choice in (draft.choices or [])]
        session.add(
            DiagnosticQuestion(
                attempt_id=attempt.id,
                objective_id=by_code[draft.objective_code].id,
                format=draft.format,
                prompt=draft.prompt.strip(),
                choices=choices,
                position=ordered[draft.objective_code],
            )
        )
    session.flush()
    log_event(
        logger,
        logging.INFO,
        "diagnosis_started",
        session_id=learning_session.id,
        attempt_id=attempt.id,
        objective_count=len(rows),
    )
    return report_for(session, learning_session, attempt)


def submit_responses(
    session: Session,
    provider: ModelProvider,
    learning_session: LearningSession,
    responses: list[ResponseInput],
) -> DiagnosisReport:
    attempt = _attempt_for_session(session, learning_session)
    if attempt is None:
        raise NotFoundError("diagnosis_not_found", "This session has no diagnosis.")
    if attempt.status != "in_progress":
        raise ConflictError("diagnosis_completed", "This diagnosis is already complete.")
    questions = _questions(session, attempt.id)
    expected = {question.id for question in questions}
    got = [item.question_id for item in responses]
    if len(got) != len(set(got)) or set(got) != expected:
        raise AppError("validation_error", "Answer every diagnostic question once.", 422)
    by_question = {item.question_id: item for item in responses}
    rows = _objectives(session, learning_session.topic_id)
    objectives_by_id = {row.id: row for row in rows}
    prerequisites = _prerequisite_map(session, [row.id for row in rows])
    nodes = _nodes(rows, prerequisites)
    answers: dict[str, tuple[str, str]] = {}
    prompt_items: list[tuple[str, str, str, str, str]] = []
    for question in questions:
        objective = objectives_by_id[question.objective_id]
        incoming = by_question[question.id]
        answers[objective.code] = (incoming.answer_text, incoming.reasoning_text)
        prompt_items.append((objective.code, question.format, question.prompt, incoming.answer_text, incoming.reasoning_text))
    parsed = _complete_model(
        session,
        provider,
        "diagnostic",
        judgment_prompt(prompt_items),
        JudgmentSet,
        f"diagnosis-evaluate:{attempt.id}",
    )
    assert isinstance(parsed, JudgmentSet)
    align_judgments(nodes, parsed.judgments, answers)
    by_code = {item.objective_code: item for item in parsed.judgments}
    observed = {item.lower() for item in _observed_concepts(session, learning_session.learner_id, learning_session.topic_id)}
    starting_point, first_code, overall = classify_starting_point(nodes, by_code, observed)
    uncertain_count = sum(1 for item in parsed.judgments if item_is_uncertain(item))
    hypothesis_ids: list[str] = []
    for question in questions:
        objective = objectives_by_id[question.objective_id]
        judgment = by_code[objective.code]
        incoming = by_question[question.id]
        _store_response(session, learning_session, attempt, question, objective, judgment, incoming, hypothesis_ids)
    attempt.status = "completed"
    attempt.starting_point = starting_point
    attempt.confidence = overall
    attempt.summary = diagnosis_summary(starting_point, first_code, uncertain_count)
    attempt.first_unmet_objective_id = next((row.id for row in rows if row.code == first_code), None)
    attempt.hypothesis_ids = hypothesis_ids
    attempt.completed_at = utcnow()
    learning_session.updated_at = attempt.completed_at
    session.flush()
    log_event(
        logger,
        logging.INFO,
        "diagnosis_completed",
        session_id=learning_session.id,
        attempt_id=attempt.id,
        starting_point=starting_point,
        uncertain_count=uncertain_count,
    )
    return report_for(session, learning_session, attempt)


def get_diagnosis(session: Session, learning_session: LearningSession) -> DiagnosisReport:
    attempt = _attempt_for_session(session, learning_session)
    if attempt is None:
        raise NotFoundError("diagnosis_not_found", "This session has no diagnosis.")
    return report_for(session, learning_session, attempt)


def _questions(session: Session, attempt_id: UUID) -> list[DiagnosticQuestion]:
    statement = (
        select(DiagnosticQuestion)
        .where(DiagnosticQuestion.attempt_id == attempt_id)
        .order_by(DiagnosticQuestion.position, DiagnosticQuestion.id)
    )
    return list(session.scalars(statement).all())


def _store_response(
    session: Session,
    learning_session: LearningSession,
    attempt: DiagnosticAttempt,
    question: DiagnosticQuestion,
    objective: LearningObjective,
    judgment: ItemJudgment,
    incoming: ResponseInput,
    hypothesis_ids: list[str],
) -> None:
    decision = knowledge_decision(judgment)
    session.add(
        DiagnosticResponse(
            question_id=question.id,
            answer_text=incoming.answer_text,
            reasoning_text=incoming.reasoning_text,
            answer_verdict=judgment.answer_verdict,
            reasoning_verdict=judgment.reasoning_verdict,
            understanding=judgment.understanding,
            confidence=CONFIDENCE[judgment.confidence],
            needs_review=needs_review(judgment),
        )
    )
    response_text = " ".join(part for part in (incoming.answer_text, incoming.reasoning_text) if part) or "No answer was given."
    intelligence.record_assessment(
        session,
        learning_session.learner_id,
        AssessmentCreate(
            topic_id=learning_session.topic_id,
            session_id=learning_session.id,
            prompt_summary=question.prompt[:500],
            response_summary=response_text[:2000],
            outcome=judgment.answer_verdict,
        ),
    )
    if decision == "observed":
        intelligence.record_knowledge(
            session,
            learning_session.learner_id,
            KnowledgeCreate(
                topic_id=learning_session.topic_id,
                concept=objective.concept,
                summary=f"Demonstrated: {objective.statement}"[:1000],
                evidence_kind="observed",
                provenance="learner_response",
                confidence=CONFIDENCE[judgment.confidence],
            ),
        )
    elif decision == "inferred":
        intelligence.record_knowledge(
            session,
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
    confirmed_hypothesis = hypothesis.confidence == "high" and not item_is_uncertain(judgment)
    row = intelligence.record_misconception(
        session,
        learning_session.learner_id,
        MisconceptionCreate(
            topic_id=learning_session.topic_id,
            concept=objective.concept,
            description=hypothesis.description.strip(),
            supporting_note=hypothesis.evidence.strip(),
            evidence_kind="observed" if confirmed_hypothesis else "inferred",
            provenance="learner_response" if confirmed_hypothesis else "system_estimate",
            confidence=CONFIDENCE[hypothesis.confidence],
        ),
    )
    hypothesis_ids.append(str(row.id))
    attempt.hypothesis_ids = hypothesis_ids


def report_for(session: Session, learning_session: LearningSession, attempt: DiagnosticAttempt) -> DiagnosisReport:
    questions = _questions(session, attempt.id)
    objective_ids = [question.objective_id for question in questions]
    objectives = {
        row.id: row
        for row in session.scalars(select(LearningObjective).where(LearningObjective.id.in_(objective_ids))).all()
    } if objective_ids else {}
    responses = {
        row.question_id: row
        for row in session.scalars(
            select(DiagnosticResponse).where(DiagnosticResponse.question_id.in_([question.id for question in questions]))
        ).all()
    } if questions else {}
    first_code = None
    if attempt.first_unmet_objective_id is not None:
        first = session.get(LearningObjective, attempt.first_unmet_objective_id)
        first_code = first.code if first is not None else None
    stored_ids = [UUID(item) for item in (attempt.hypothesis_ids or [])]
    misconceptions = []
    if stored_ids:
        rows = session.scalars(
            select(MisconceptionRecord).where(
                MisconceptionRecord.id.in_(stored_ids),
                MisconceptionRecord.learner_id == learning_session.learner_id,
            )
        ).all()
        order = {item: index for index, item in enumerate(stored_ids)}
        for row in sorted(rows, key=lambda item: order.get(item.id, 0)):
            misconceptions.append(
                DiagnosisMisconceptionRead(
                    id=row.id,
                    concept=row.concept,
                    description=row.description,
                    evidence=row.supporting_note,
                    confidence=float(row.confidence),
                    confirmed=row.evidence_kind == "observed",
                )
            )
    judgments: list[DiagnosisJudgmentRead] = []
    for question in questions:
        response = responses.get(question.id)
        if response is None:
            continue
        objective = objectives[question.objective_id]
        judgments.append(
            DiagnosisJudgmentRead(
                question_id=question.id,
                objective_code=objective.code,
                answer_text=response.answer_text,
                reasoning_text=response.reasoning_text,
                answer_verdict=response.answer_verdict,  # type: ignore[arg-type]
                reasoning_verdict=response.reasoning_verdict,  # type: ignore[arg-type]
                understanding=response.understanding,  # type: ignore[arg-type]
                confidence=float(response.confidence),
                needs_review=response.needs_review,
                confirmed=response.understanding == "solid"
                and response.answer_verdict == "correct"
                and response.reasoning_verdict == "sound"
                and float(response.confidence) > 0.4,
            )
        )
    return DiagnosisReport(
        id=attempt.id,
        session_id=learning_session.id,
        topic_id=learning_session.topic_id,
        status=attempt.status,  # type: ignore[arg-type]
        session_status=learning_session.status,
        starting_point=attempt.starting_point,  # type: ignore[arg-type]
        confidence=float(attempt.confidence) if attempt.confidence is not None else None,
        summary=attempt.summary,
        first_unmet_objective_code=first_code,
        questions=[
            DiagnosisQuestionRead(
                id=question.id,
                objective_code=objectives[question.objective_id].code,
                objective_statement=objectives[question.objective_id].statement,
                concept=objectives[question.objective_id].concept,
                format=question.format,  # type: ignore[arg-type]
                prompt=question.prompt,
                choices=question.choices,
                position=question.position,
            )
            for question in questions
        ],
        judgments=judgments,
        misconceptions=misconceptions,
    )

