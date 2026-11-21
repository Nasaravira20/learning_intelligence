from __future__ import annotations


def question_prompt(*, objective_code: str, concept: str, statement: str) -> str:
    short_statement = statement if len(statement) <= 180 else statement[:177] + "..."
    return "\n".join(
        [
            "Task: evaluation_question",
            f"OBJECTIVE {objective_code}",
            f"CONCEPT {concept}",
            f"STATEMENT {short_statement}",
            "Write one check for this objective code only.",
            "Ask for the answer and for the reason separately.",
            "Do not invent strategy ids, citations, DOIs, quotations, or effect sizes.",
            "Return only JSON matching the schema.",
        ]
    )


def judgment_prompt(*, objective_code: str, prompt: str, answer: str, reasoning: str) -> str:
    return "\n".join(
        [
            "Task: evaluation_judgment",
            f"OBJECTIVE {objective_code}",
            "QUESTION: " + prompt[:180],
            "ANSWER: " + (answer.strip() or "(blank)"),
            "REASONING: " + (reasoning.strip() or "(blank)"),
            "Judge the answer and the reasoning separately.",
            "If you are unsure, use confidence low and understanding uncertain.",
            "A misconception evidence field must be copied exactly from the answer or the reasoning.",
            "Do not invent strategy ids, citations, DOIs, quotations, or effect sizes.",
            "Return only JSON matching the schema.",
        ]
    )
