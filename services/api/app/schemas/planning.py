from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

StepStatus = Literal["satisfied", "current", "upcoming"]
StepEvidence = Literal["observed", "none"]
PlanStatus = Literal["active", "superseded"]


class ConceptRead(BaseModel):
    id: UUID
    topic_id: UUID
    name: str
    position: int
    summary: str


class PlanStepRead(BaseModel):
    id: UUID
    position: int
    objective_id: UUID
    objective_code: str
    objective_statement: str
    concept_id: UUID
    concept: str
    status: StepStatus
    evidence: StepEvidence
    completion_criteria: str


class LearningPlanRead(BaseModel):
    id: UUID
    session_id: UUID
    topic_id: UUID
    revision: int
    status: PlanStatus
    session_status: str
    diagnostic_attempt_id: UUID
    starting_objective_code: str | None
    summary: str
    current_step_id: UUID | None
    concepts: list[ConceptRead]
    steps: list[PlanStepRead]
    created_at: datetime
    updated_at: datetime
