from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.pedagogy import PedagogySelection
from app.pedagogy.registry import PedagogyRegistry
from app.pedagogy.selector import RejectedStrategy, SelectorInput


class StrategySummary(BaseModel):
    strategy_id: str
    name: str
    version: str
    review_status: str
    selectable_in_production: bool
    sources: list[str]


class SourceSummary(BaseModel):
    source_id: str
    title: str
    year: int
    access_type: str
    license: str
    review_status: str


class RegistryRead(BaseModel):
    registry_version: str
    production_selectable_strategy_ids: list[str]
    strategies: list[StrategySummary]
    sources: list[SourceSummary]

    @classmethod
    def from_registry(cls, registry: PedagogyRegistry, selectable: list[str]) -> RegistryRead:
        allowed = set(selectable)
        return cls(
            registry_version=registry.manifest.registry_version,
            production_selectable_strategy_ids=selectable,
            strategies=[
                StrategySummary(
                    strategy_id=item.strategy_id,
                    name=item.name,
                    version=item.version,
                    review_status=item.review_status,
                    selectable_in_production=item.strategy_id in allowed,
                    sources=list(item.sources),
                )
                for item in registry.strategies
            ],
            sources=[
                SourceSummary(
                    source_id=item.source_id,
                    title=item.title,
                    year=item.year,
                    access_type=item.access_type,
                    license=item.license,
                    review_status=item.review_status,
                )
                for item in registry.sources
            ],
        )


class SelectionRequest(BaseModel):
    context: SelectorInput | None = None


class SelectionRead(BaseModel):
    id: UUID
    session_id: UUID
    revision: int
    status: str
    session_status: str
    policy_version: str
    registry_version: str
    situation: str
    primary_strategy: str | None
    supporting_strategies: list[str]
    sequence: list[str]
    success_signals: list[str]
    fallback_strategy: str | None
    rationale: str
    controls_teaching: bool
    production_primary_strategy: str | None
    rejected: list[RejectedStrategy]
    input_fingerprint: str
    created_at: datetime

    @classmethod
    def from_row(cls, row: PedagogySelection, session_status: str) -> SelectionRead:
        return cls(
            id=row.id,
            session_id=row.session_id,
            revision=row.revision,
            status=row.status,
            session_status=session_status,
            policy_version=row.policy_version,
            registry_version=row.registry_version,
            situation=row.situation,
            primary_strategy=row.primary_strategy_id,
            supporting_strategies=list(row.supporting_strategy_ids),
            sequence=list(row.sequence),
            success_signals=list(row.success_signals),
            fallback_strategy=row.fallback_strategy_id,
            rationale=row.rationale,
            controls_teaching=row.controls_teaching,
            production_primary_strategy=row.production_primary_strategy_id,
            rejected=[RejectedStrategy.model_validate(item) for item in row.rejected],
            input_fingerprint=row.input_fingerprint,
            created_at=row.created_at,
        )
