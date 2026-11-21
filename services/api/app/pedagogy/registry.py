from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import ValidationError

from app.pedagogy.schemas import (
    P0_STRATEGY_IDS,
    RegistryManifest,
    SourceRecord,
    StrategyRecord,
)


@dataclass(frozen=True)
class RegistryIssue:
    code: str
    message: str
    path: str


class RegistryValidationError(Exception):
    def __init__(self, issues: list[RegistryIssue]) -> None:
        self.issues = issues
        super().__init__(f"{len(issues)} registry validation issues")


@dataclass(frozen=True)
class PedagogyRegistry:
    root: Path
    manifest: RegistryManifest
    strategies: tuple[StrategyRecord, ...]
    sources: tuple[SourceRecord, ...]

    def source(self, source_id: str) -> SourceRecord | None:
        for item in self.sources:
            if item.source_id == source_id:
                return item
        return None


def registry_root() -> Path:
    override = os.environ.get("PEDAGOGY_REGISTRY_PATH")
    if override:
        return Path(override)
    app_root = Path(__file__).resolve().parents[2]
    packaged = app_root / "research"
    if (packaged / "registry.yaml").is_file():
        return packaged
    return Path(__file__).resolve().parents[4] / "research"


def load_registry(root: Path | None = None) -> PedagogyRegistry:
    registry_path = root or registry_root()
    issues: list[RegistryIssue] = []
    manifest = _load_manifest(registry_path, issues)
    strategies = _load_records(
        registry_path / "strategies",
        StrategyRecord,
        "strategy_id",
        "strategy",
        issues,
    )
    sources = _load_records(
        registry_path / "sources",
        SourceRecord,
        "source_id",
        "source",
        issues,
    )
    if manifest is not None:
        _check_versions(manifest, strategies, issues)
        _check_p0(strategies, issues)
    _check_source_links(strategies, sources, issues)
    _check_stored_files(registry_path, issues)
    if issues or manifest is None:
        raise RegistryValidationError(issues)
    return PedagogyRegistry(
        root=registry_path,
        manifest=manifest,
        strategies=tuple(strategies),
        sources=tuple(sources),
    )


def production_selectable_strategy_ids(registry: PedagogyRegistry) -> list[str]:
    """Return strategy IDs a production session may use.

    This is a review gate, not the Phase 6 selector. An entry is eligible only
    when a person has marked both the strategy and every linked source reviewed.
    """
    selected: list[str] = []
    for strategy in registry.strategies:
        if strategy.review_status != "reviewed":
            continue
        sources = [registry.source(source_id) for source_id in strategy.sources]
        if all(source is not None and source.review_status == "reviewed" for source in sources):
            selected.append(strategy.strategy_id)
    return selected


def _load_manifest(root: Path, issues: list[RegistryIssue]) -> RegistryManifest | None:
    path = root / "registry.yaml"
    payload = _read_yaml(path, "registry", issues)
    if payload is None:
        return None
    if not isinstance(payload, dict):
        issues.append(RegistryIssue("manifest_invalid", "Registry manifest must be a mapping.", "registry.yaml"))
        return None
    try:
        return RegistryManifest.model_validate(payload)
    except ValidationError as exc:
        _append_validation(issues, "registry.yaml", "manifest_invalid", exc)
        return None


def _load_records(
    directory: Path,
    model: type[StrategyRecord] | type[SourceRecord],
    id_field: str,
    kind: str,
    issues: list[RegistryIssue],
) -> list[StrategyRecord] | list[SourceRecord]:
    if not directory.is_dir():
        issues.append(RegistryIssue(f"missing_{kind}s", f"Missing {directory.name} directory.", directory.name))
        return []
    records = []
    seen: set[str] = set()
    paths = sorted(path for path in directory.iterdir() if path.is_file())
    if not paths:
        issues.append(RegistryIssue(f"missing_{kind}s", f"No {kind} files were found.", directory.name))
    for path in paths:
        if path.suffix != ".yaml":
            issues.append(RegistryIssue("unexpected_file", "Registry entries must be YAML files.", str(path)))
            continue
        payload = _read_yaml(path, kind, issues)
        if not isinstance(payload, dict):
            issues.append(RegistryIssue(f"{kind}_invalid", f"{kind} entry must be a mapping.", path.name))
            continue
        try:
            record = model.model_validate(payload)
        except ValidationError as exc:
            _append_validation(issues, path.name, f"{kind}_invalid", exc)
            continue
        record_id = getattr(record, id_field)
        if path.stem != record_id:
            issues.append(
                RegistryIssue(
                    "id_filename_mismatch",
                    f"{path.name} must be named {record_id}.yaml.",
                    path.name,
                )
            )
        if record_id in seen:
            issues.append(RegistryIssue("duplicate_id", f"Duplicate {kind} id {record_id}.", path.name))
        seen.add(record_id)
        records.append(record)
    return records


def _check_versions(
    manifest: RegistryManifest,
    strategies: list[StrategyRecord],
    issues: list[RegistryIssue],
) -> None:
    found = {item.strategy_id: item.version for item in strategies}
    for strategy_id, version in manifest.strategies.items():
        if strategy_id not in found:
            issues.append(
                RegistryIssue(
                    "missing_strategy",
                    f"Manifest lists {strategy_id}, but no strategy file exists.",
                    "registry.yaml",
                )
            )
            continue
        if found[strategy_id] != version:
            issues.append(
                RegistryIssue(
                    "version_mismatch",
                    f"{strategy_id} is {found[strategy_id]} in the file and {version} in the manifest.",
                    f"strategies/{strategy_id}.yaml",
                )
            )
    for strategy_id in found:
        if strategy_id not in manifest.strategies:
            issues.append(
                RegistryIssue(
                    "unversioned_strategy",
                    f"{strategy_id} is missing from the registry manifest.",
                    f"strategies/{strategy_id}.yaml",
                )
            )


def _check_p0(strategies: list[StrategyRecord], issues: list[RegistryIssue]) -> None:
    found = {item.strategy_id for item in strategies}
    expected = set(P0_STRATEGY_IDS)
    for strategy_id in sorted(expected - found):
        issues.append(RegistryIssue("missing_p0", f"P0 strategy {strategy_id} is missing.", "strategies"))
    for strategy_id in sorted(found - expected):
        issues.append(
            RegistryIssue(
                "unexpected_strategy",
                f"{strategy_id} is outside the P0 catalogue.",
                f"strategies/{strategy_id}.yaml",
            )
        )


def _check_source_links(
    strategies: list[StrategyRecord],
    sources: list[SourceRecord],
    issues: list[RegistryIssue],
) -> None:
    known = {item.source_id for item in sources}
    for strategy in strategies:
        for source_id in strategy.sources:
            if source_id not in known:
                issues.append(
                    RegistryIssue(
                        "missing_source",
                        f"{strategy.strategy_id} references unknown source {source_id}.",
                        f"strategies/{strategy.strategy_id}.yaml",
                    )
                )


def _check_stored_files(root: Path, issues: list[RegistryIssue]) -> None:
    if not root.exists():
        issues.append(RegistryIssue("missing_registry", "Registry directory does not exist.", str(root)))
        return
    for path in root.rglob("*"):
        if path.suffix.lower() in {".pdf", ".epub", ".html", ".txt"}:
            issues.append(
                RegistryIssue(
                    "copyrighted_file",
                    "Full papers, books, and page captures must not be stored.",
                    str(path.relative_to(root)),
                )
            )


def _read_yaml(path: Path, kind: str, issues: list[RegistryIssue]) -> object | None:
    if not path.is_file():
        issues.append(RegistryIssue("missing_file", f"Missing {path.name}.", path.name))
        return None
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        issues.append(RegistryIssue(f"{kind}_invalid", f"{path.name} is not valid YAML.", path.name))
        return None
    return payload


def _append_validation(
    issues: list[RegistryIssue],
    path: str,
    code: str,
    exc: ValidationError,
) -> None:
    for error in exc.errors():
        location = ".".join(str(part) for part in error["loc"]) or path
        issues.append(RegistryIssue(code, error["msg"], f"{path}:{location}"))
