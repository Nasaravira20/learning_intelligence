from app.ai.classify import provider_error_from_exception
from app.ai.model_capabilities import bare_model_id
from app.ai.types import GenerationRequest, GenerationResult, ModelInfo


def _methods(model: object) -> tuple[str, ...]:
    for attribute in ("supported_actions", "supported_generation_methods"):
        value = getattr(model, attribute, None)
        if isinstance(value, (list, tuple)):
            return tuple(str(item) for item in value)
    return ()


def _usage_value(usage: object, *names: str) -> int | None:
    if usage is None:
        return None
    for name in names:
        value = usage.get(name) if isinstance(usage, dict) else getattr(usage, name, None)
        if value is not None:
            return int(value)
    return None


class GeminiProvider:
    def __init__(self, api_key: str, timeout_seconds: float) -> None:
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._client = None

    def _sdk_client(self):
        if self._client is not None:
            return self._client
        from google import genai
        from google.genai import types

        timeout_ms = max(1, int(self._timeout_seconds * 1000))
        self._client = genai.Client(
            api_key=self._api_key,
            http_options=types.HttpOptions(timeout=timeout_ms),
        )
        return self._client

    def list_models(self) -> list[ModelInfo]:
        try:
            models = []
            for model in self._sdk_client().models.list():
                raw_name = str(getattr(model, "name", "") or "")
                if not raw_name:
                    continue
                models.append(ModelInfo(model_id=bare_model_id(raw_name), methods=_methods(model)))
            return models
        except Exception as exc:
            raise provider_error_from_exception(exc) from None

    def generate(self, request: GenerationRequest) -> GenerationResult:
        client = self._sdk_client()
        kwargs: dict[str, object] = {"model": request.model_id, "input": request.prompt}
        if request.schema is not None:
            kwargs["response_format"] = {
                "type": "text",
                "mime_type": "application/json",
                "schema": request.schema,
            }
        kwargs["generation_config"] = {
            "max_output_tokens": request.max_output_tokens,
            "temperature": 0,
        }
        kwargs["store"] = False
        try:
            interaction = client.interactions.create(
                timeout=self._timeout_seconds,
                automatic_continuation=False,
                **kwargs,
            )
        except Exception as exc:
            raise provider_error_from_exception(exc) from None
        usage = getattr(interaction, "usage", None)
        returned = bare_model_id(str(getattr(interaction, "model", "") or request.model_id))
        return GenerationResult(
            text=str(getattr(interaction, "output_text", "") or ""),
            model_id=returned,
            input_tokens=_usage_value(usage, "total_input_tokens", "input_tokens", "prompt_token_count"),
            output_tokens=_usage_value(usage, "total_output_tokens", "output_tokens", "candidates_token_count"),
        )
