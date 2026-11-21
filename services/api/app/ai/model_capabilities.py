from app.ai.types import ModelInfo

NON_GENERATIVE = ("embedding", "imagen", "tts", "aqa", "veo", "robotics")
TEXT_EXCLUDED = NON_GENERATIVE + ("image", "audio", "live", "antigravity", "deep-research")


def bare_model_id(name: str) -> str:
    cleaned = name.strip()
    if cleaned.startswith("models/"):
        return cleaned.split("/", 1)[1]
    return cleaned


def is_generative(info: ModelInfo) -> bool:
    methods = [method.lower() for method in info.methods]
    if any("generate" in method or "interaction" in method for method in methods):
        return True
    if methods:
        return False
    lowered = info.model_id.lower()
    return not any(part in lowered for part in NON_GENERATIVE)


def is_text_candidate(info: ModelInfo) -> bool:
    if not is_generative(info):
        return False
    lowered = info.model_id.lower()
    return not any(part in lowered for part in TEXT_EXCLUDED)


def text_model_ids(listed: list[ModelInfo]) -> list[str]:
    return [info.model_id for info in listed if is_text_candidate(info)]


def select_candidates(
    listed: list[ModelInfo],
    configured: list[str],
    limit: int,
) -> tuple[list[str], list[str]]:
    """Return (candidates, configured ids that were not in the live list)."""
    listed_ids = [info.model_id for info in listed]
    listed_set = set(listed_ids)
    requested = [bare_model_id(item) for item in configured if item.strip()]
    if requested:
        present = [model_id for model_id in requested if model_id in listed_set]
        missing = [model_id for model_id in requested if model_id not in listed_set]
        return present, missing
    generative = [info.model_id for info in listed if is_generative(info)]
    return generative[: max(limit, 0)], []
