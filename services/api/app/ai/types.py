from dataclasses import dataclass


@dataclass(frozen=True)
class ModelInfo:
    model_id: str
    methods: tuple[str, ...] = ()


@dataclass(frozen=True)
class GenerationRequest:
    model_id: str
    prompt: str
    max_output_tokens: int
    schema: dict | None = None


@dataclass(frozen=True)
class GenerationResult:
    text: str
    model_id: str
    input_tokens: int | None
    output_tokens: int | None
