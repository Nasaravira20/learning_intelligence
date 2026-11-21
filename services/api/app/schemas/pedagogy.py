from __future__ import annotations

from pydantic import BaseModel

from app.pedagogy.registry import PedagogyRegistry


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
