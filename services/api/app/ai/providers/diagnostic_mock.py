import json

from app.ai.errors import ProviderError
from app.ai.types import GenerationRequest, GenerationResult


class DiagnosticMockProvider:
    """Development stand-in. It does not call Gemini and does not score real understanding."""

    def list_models(self) -> list:
        return []

    def generate(self, request: GenerationRequest) -> GenerationResult:
        if "Task: diagnostic_questions" in request.prompt:
            payload = {"questions": _questions(request.prompt)}
        elif "Task: diagnostic_judgment" in request.prompt:
            payload = {"judgments": _judgments(request.prompt)}
        else:
            raise ProviderError("unsupported_operation", False)
        return GenerationResult(
            text=json.dumps(payload),
            model_id="mock",
            input_tokens=1,
            output_tokens=1,
        )


def _questions(prompt: str) -> list[dict[str, object]]:
    codes = [line.split()[1] for line in prompt.splitlines() if line.startswith("OBJECTIVE ")]
    if not codes:
        raise ProviderError("unknown", False)
    formats = ("short_answer", "multiple_choice", "reasoning")
    questions: list[dict[str, object]] = []
    for index, code in enumerate(codes):
        question_format = formats[index % len(formats)]
        questions.append(
            {
                "objective_code": code,
                "format": question_format,
                "prompt": f"Show what you know about {code}.",
                "choices": ["A first option", "A second option"] if question_format == "multiple_choice" else None,
            }
        )
    return questions


def _judgments(prompt: str) -> list[dict[str, object]]:
    blocks = prompt.split("ITEM ")[1:]
    if not blocks:
        raise ProviderError("unknown", False)
    judgments: list[dict[str, object]] = []
    for block in blocks:
        code = block.splitlines()[0].strip()
        answer = _field(block, "ANSWER: ")
        blank = answer in {"", "(blank)"}
        judgments.append(
            {
                "objective_code": code,
                "answer_verdict": "unanswered" if blank else "partial",
                "reasoning_verdict": "absent" if blank else "weak",
                "understanding": "none" if blank else "partial",
                "confidence": "low" if blank else "medium",
                "misconception": None,
            }
        )
    return judgments


def _field(block: str, label: str) -> str:
    for line in block.splitlines():
        if line.startswith(label):
            return line[len(label) :].strip()
    return ""
