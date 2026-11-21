from __future__ import annotations


def question_prompt(*, objective_code: str, concept: str, statement: str) -> str:
    short_statement = statement if len(statement) <= 180 else statement[:177] + "..."
    return "\n".join(
        [
            "Task: retention_question",
            f"OBJECTIVE {objective_code}",
            f"CONCEPT {concept}",
            f"STATEMENT {short_statement}",
            "Ask the learner to recall this previously learned objective.",
            "Do not include the answer.",
            "Do not invent strategy ids, citations, DOIs, quotations, or effect sizes.",
            "Return only JSON matching the schema.",
        ]
    )
