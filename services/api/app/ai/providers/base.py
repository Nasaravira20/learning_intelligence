from typing import Protocol

from app.ai.types import GenerationRequest, GenerationResult, ModelInfo


class ModelProvider(Protocol):
    def list_models(self) -> list[ModelInfo]:
        """Return models the configured credential can see. This does not make them usable."""

    def generate(self, request: GenerationRequest) -> GenerationResult:
        """Run one generation. Raise ProviderError with an error class and no secret text."""
