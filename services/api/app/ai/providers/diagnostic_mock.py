import json

from app.ai.errors import ProviderError
from app.ai.types import GenerationRequest, GenerationResult
from app.teaching.draft import scripted_lesson


class DiagnosticMockProvider:
    """Development stand-in. It does not call Gemini and does not score real understanding."""

    def list_models(self) -> list:
        return []

    def generate(self, request: GenerationRequest) -> GenerationResult:
        if "Task: diagnostic_questions" in request.prompt:
            payload = {"questions": _questions(request.prompt)}
        elif "Task: diagnostic_judgment" in request.prompt:
            payload = {"judgments": _judgments(request.prompt)}
        elif "Task: teaching_lesson" in request.prompt:
            payload = scripted_lesson(request.prompt)
        elif "Task: evaluation_question" in request.prompt:
            payload = _evaluation_question(request.prompt)
        elif "Task: evaluation_judgment" in request.prompt:
            payload = _evaluation_judgment(request.prompt)
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


def _evaluation_question(prompt: str) -> dict[str, object]:
    objective = _labeled(prompt, "OBJECTIVE ")
    concept = _labeled(prompt, "CONCEPT ")
    return {
        "objective_code": objective,
        "prompt": f"Show {objective} for {concept}, and say why that result follows.",
    }


def _evaluation_judgment(prompt: str) -> dict[str, object]:
    objective = _labeled(prompt, "OBJECTIVE ")
    answer = _labeled(prompt, "ANSWER: ")
    reasoning = _labeled(prompt, "REASONING: ")
    blank = answer in {"", "(blank)"}
    unsure = "not sure" in f"{answer} {reasoning}".casefold()
    if blank:
        verdict, reason, understanding, confidence = "unanswered", "absent", "none", "low"
    elif unsure:
        verdict, reason, understanding, confidence = "unanswered", "uncertain", "uncertain", "low"
    elif "weak reason" in reasoning.casefold():
        verdict, reason, understanding, confidence = "correct", "weak", "partial", "medium"
    elif "partial" in answer.casefold():
        verdict, reason, understanding, confidence = "partial", "partial", "partial", "medium"
    else:
        verdict, reason, understanding, confidence = "partial", "weak", "partial", "medium"
    return {
        "objective_code": objective,
        "answer_verdict": verdict,
        "reasoning_verdict": reason,
        "understanding": understanding,
        "confidence": confidence,
        "misconception": None,
    }


def _labeled(prompt: str, prefix: str) -> str:
    for line in prompt.splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    raise ProviderError("unknown", False)
