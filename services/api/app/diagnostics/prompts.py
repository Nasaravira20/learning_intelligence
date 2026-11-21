from __future__ import annotations

from app.diagnostics.policy import ObjectiveNode


def question_prompt(objectives: list[ObjectiveNode], observed_concepts: list[str]) -> str:
    lines = [
        "Task: diagnostic_questions",
        "Write one question for every objective code listed below.",
        "Use only those codes. Do not invent codes, citations, DOIs, quotations, or effect sizes.",
        "Formats are short_answer, multiple_choice, and reasoning.",
        "multiple_choice needs two to four choices. Other formats use null choices.",
        "Return only JSON matching the schema.",
    ]
    if observed_concepts:
        lines.append("Observed concepts, already demonstrated: " + ", ".join(observed_concepts))
    else:
        lines.append("The learner has no observed knowledge on this topic.")
    lines.append("Inferred knowledge is not confirmed and is omitted.")
    for item in objectives:
        statement = item.statement if len(item.statement) <= 180 else item.statement[:177] + "..."
        lines.append(f"OBJECTIVE {item.code} | concept: {item.concept} | statement: {statement}")
    return "\n".join(lines)


def judgment_prompt(items: list[tuple[str, str, str, str, str]]) -> str:
    lines = [
        "Task: diagnostic_judgment",
        "Judge the answer and the reasoning separately.",
        "If you are unsure, use confidence low and understanding uncertain.",
        "A misconception evidence field must be copied exactly from the learner answer or reasoning.",
        "Do not invent codes, citations, DOIs, quotations, or effect sizes.",
        "Return only JSON matching the schema.",
    ]
    for code, question_format, prompt, answer, reasoning in items:
        lines.append(f"ITEM {code}")
        lines.append(f"FORMAT {question_format}")
        lines.append("QUESTION: " + prompt[:180])
        lines.append("ANSWER: " + (answer.strip() or "(blank)"))
        lines.append("REASONING: " + (reasoning.strip() or "(blank)"))
    return "\n".join(lines)
