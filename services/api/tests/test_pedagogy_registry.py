from pathlib import Path

import pytest
import yaml

from app.pedagogy.registry import (
    RegistryValidationError,
    load_registry,
    production_selectable_strategy_ids,
    registry_root,
)
from app.pedagogy.schemas import P0_STRATEGY_IDS, SourceRecord, StrategyRecord


def test_shipped_registry_validates_and_blocks_unreviewed_selection() -> None:
    registry = load_registry()
    ids = [item.strategy_id for item in registry.strategies]
    assert ids == sorted(ids)
    assert set(ids) == set(P0_STRATEGY_IDS)
    assert all(item.version == "1.0.0" for item in registry.strategies)
    assert registry.manifest.registry_version == "2026.11.21"
    assert set(registry.manifest.strategies) == set(ids)
    source_ids = {item.source_id for item in registry.sources}
    for strategy in registry.strategies:
        assert strategy.review_status == "pending_human_review"
        assert strategy.reviewed_by is None
        assert strategy.limitations
        assert strategy.implementation_steps
        for source_id in strategy.sources:
            assert source_id in source_ids
    for source in registry.sources:
        assert source.review_status == "pending_human_review"
        assert source.metadata_verification.checked_on.isoformat() == "2026-11-21"
        assert source.license
        assert source.url.startswith("https://")
    assert production_selectable_strategy_ids(registry) == []
    stored = {path.suffix.lower() for path in registry.root.rglob("*") if path.is_file()}
    assert ".pdf" not in stored
    assert ".html" not in stored


def test_registry_endpoint_reports_no_production_selection(client) -> None:
    response = client.get("/api/pedagogy/registry")
    assert response.status_code == 200
    body = response.json()
    assert body["registry_version"] == "2026.11.21"
    assert body["production_selectable_strategy_ids"] == []
    assert {item["strategy_id"] for item in body["strategies"]} == set(P0_STRATEGY_IDS)
    assert all(item["selectable_in_production"] is False for item in body["strategies"])
    assert "weinstein_2018" in {item["source_id"] for item in body["sources"]}


def test_invalid_entries_fail_validation(tmp_path: Path) -> None:
    _write_minimum(tmp_path)
    strategy = tmp_path / "strategies" / "retrieval_practice.yaml"
    payload = yaml.safe_load(strategy.read_text(encoding="utf-8"))
    payload.pop("version")
    strategy.write_text(yaml.safe_dump(payload), encoding="utf-8")
    with pytest.raises(RegistryValidationError) as missing_version:
        load_registry(tmp_path)
    assert "strategy_invalid" in {issue.code for issue in missing_version.value.issues}

    _write_minimum(tmp_path)
    duplicate = tmp_path / "strategies" / "other_name.yaml"
    duplicate.write_text((tmp_path / "strategies" / "retrieval_practice.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    with pytest.raises(RegistryValidationError) as duplicate_id:
        load_registry(tmp_path)
    codes = {issue.code for issue in duplicate_id.value.issues}
    assert "duplicate_id" in codes
    assert "id_filename_mismatch" in codes

    _write_minimum(tmp_path)
    broken = yaml.safe_load((tmp_path / "strategies" / "retrieval_practice.yaml").read_text(encoding="utf-8"))
    broken["sources"] = ["not_a_source"]
    (tmp_path / "strategies" / "retrieval_practice.yaml").write_text(yaml.safe_dump(broken), encoding="utf-8")
    with pytest.raises(RegistryValidationError) as missing_source:
        load_registry(tmp_path)
    assert "missing_source" in {issue.code for issue in missing_source.value.issues}

    _write_minimum(tmp_path)
    (tmp_path / "sources" / "paper.pdf").write_bytes(b"%PDF")
    with pytest.raises(RegistryValidationError) as copied_paper:
        load_registry(tmp_path)
    assert "copyrighted_file" in {issue.code for issue in copied_paper.value.issues}

    _write_minimum(tmp_path)
    reviewed = yaml.safe_load((tmp_path / "strategies" / "retrieval_practice.yaml").read_text(encoding="utf-8"))
    reviewed["review_status"] = "reviewed"
    (tmp_path / "strategies" / "retrieval_practice.yaml").write_text(yaml.safe_dump(reviewed), encoding="utf-8")
    with pytest.raises(RegistryValidationError) as missing_reviewer:
        load_registry(tmp_path)
    assert "strategy_invalid" in {issue.code for issue in missing_reviewer.value.issues}


def test_reviewed_strategy_is_selectable_only_when_sources_are_reviewed() -> None:
    strategy = _strategy()
    source = _source()
    registry = _registry((strategy,), (source,))
    assert production_selectable_strategy_ids(registry) == ["retrieval_practice"]

    pending_source = source.model_copy(update={"review_status": "pending_human_review", "reviewed_by": None})
    pending_registry = _registry((strategy,), (pending_source,))
    assert production_selectable_strategy_ids(pending_registry) == []

    pending_strategy = strategy.model_copy(update={"review_status": "pending_human_review", "reviewed_by": None})
    assert production_selectable_strategy_ids(_registry((pending_strategy,), (source,))) == []


def test_default_root_finds_the_repository_catalogue() -> None:
    root = registry_root()
    assert (root / "registry.yaml").is_file()
    assert (root / "strategies" / "mastery_learning.yaml").is_file()


def _registry(strategies: tuple[StrategyRecord, ...], sources: tuple[SourceRecord, ...]):
    from app.pedagogy.registry import PedagogyRegistry
    from app.pedagogy.schemas import RegistryManifest

    return PedagogyRegistry(
        root=Path("."),
        manifest=RegistryManifest(registry_version="2026.11.21", strategies={"retrieval_practice": "1.0.0"}),
        strategies=strategies,
        sources=sources,
    )


def _strategy() -> StrategyRecord:
    return StrategyRecord(
        strategy_id="retrieval_practice",
        name="Retrieval Practice",
        version="1.0.0",
        category="memory_and_retrieval",
        description="Ask the learner to recall something already taught before showing the answer.",
        learning_objectives=["recall"],
        suitable_contexts=["revision"],
        learner_conditions=["initial_instruction_has_been_provided"],
        avoid_or_modify_conditions=["learner_has_never_been_taught_the_concept"],
        implementation_steps=["Ask a focused question."],
        assessment_signals=["independent_recall"],
        limitations=["Not a substitute for initial instruction."],
        sources=["weinstein_2018"],
        review_status="reviewed",
        reviewed_by="Hassen",
    )


def _source() -> SourceRecord:
    return SourceRecord(
        source_id="weinstein_2018",
        title="Teaching the Science of Learning",
        authors=["Yana Weinstein"],
        year=2018,
        publication="Cognitive Research: Principles and Implications",
        doi="10.1186/s41235-017-0087-y",
        url="https://doi.org/10.1186/s41235-017-0087-y",
        access_type="open_access",
        license="CC BY 4.0",
        retrieved_date="2026-11-21",
        relevant_sections=["Retrieval practice"],
        evidence_notes="Original summary used only to test the review gate. The article is not stored.",
        limitations=["The article is not stored."],
        review_status="reviewed",
        reviewed_by="Hassen",
        metadata_verification={
            "checked_on": "2026-11-21",
            "method": "crossref",
            "identifier": "10.1186/s41235-017-0087-y",
        },
    )


def _write_minimum(root: Path) -> None:
    strategies = root / "strategies"
    sources = root / "sources"
    strategies.mkdir(parents=True, exist_ok=True)
    sources.mkdir(parents=True, exist_ok=True)
    for path in list(strategies.iterdir()) + list(sources.iterdir()):
        path.unlink()
    shipped = registry_root()
    for name in ("registry.yaml",):
        (root / name).write_text((shipped / name).read_text(encoding="utf-8"), encoding="utf-8")
    for path in (shipped / "strategies").glob("*.yaml"):
        (strategies / path.name).write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    for path in (shipped / "sources").glob("*.yaml"):
        (sources / path.name).write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
