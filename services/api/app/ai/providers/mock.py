from app.ai.errors import ProviderError
from app.ai.types import GenerationRequest, GenerationResult, ModelInfo


class MockProvider:
    def __init__(
        self,
        models: list[ModelInfo] | None = None,
        script: list[GenerationResult | ProviderError] | None = None,
    ) -> None:
        self.models = models or []
        self.script = script or []
        self.calls: list[GenerationRequest] = []

    def list_models(self) -> list[ModelInfo]:
        return list(self.models)

    def generate(self, request: GenerationRequest) -> GenerationResult:
        self.calls.append(request)
        if not self.script:
            raise ProviderError("unknown", False)
        item = self.script.pop(0)
        if isinstance(item, ProviderError):
            raise item
        return item
