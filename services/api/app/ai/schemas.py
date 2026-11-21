from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class DiagnosticProbe(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gap: str = Field(min_length=1, max_length=120)
    confidence: Literal["low", "medium", "high"]


class TeachingProbe(BaseModel):
    model_config = ConfigDict(extra="forbid")

    explanation: str = Field(min_length=1, max_length=200)
    check_question: str = Field(min_length=1, max_length=200)


class EvaluationProbe(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verdict: Literal["met", "not_met"]
    reason: str = Field(min_length=1, max_length=200)


STRUCTURED_TASKS: dict[str, type[BaseModel]] = {
    "diagnostic": DiagnosticProbe,
    "teaching": TeachingProbe,
    "evaluation": EvaluationProbe,
}


def parse_model_json(model: type[BaseModel], text: str) -> BaseModel:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = [line for line in cleaned.splitlines() if not line.strip().startswith("```")]
        cleaned = "\n".join(lines).strip()
    try:
        return model.model_validate_json(cleaned)
    except ValidationError as exc:
        raise ValueError("malformed_output") from exc
