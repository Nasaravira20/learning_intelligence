from __future__ import annotations


def lesson_prompt(
    *,
    objective_code: str,
    concept: str,
    statement: str,
    primary_strategy_id: str,
    supporting_strategy_ids: list[str],
    fallback_strategy_id: str,
) -> str:
    supporting = ", ".join(supporting_strategy_ids) if supporting_strategy_ids else "none"
    short_statement = statement if len(statement) <= 180 else statement[:177] + "..."
    lines = [
        "Task: teaching_lesson",
        f"OBJECTIVE {objective_code}",
        f"CONCEPT {concept}",
        f"STATEMENT {short_statement}",
        f"PRIMARY {primary_strategy_id}",
        f"SUPPORTING {supporting}",
        f"FALLBACK {fallback_strategy_id}",
        "Use only the primary, supporting, and fallback strategy ids.",
        "Do not invent strategy ids, citations, DOIs, quotations, or effect sizes.",
        "Each activity is a structured object tied to the objective code.",
        "Explanations and examples include an example. A worked example includes steps.",
        "Put a check for understanding before the last activity.",
        "The first hint must not contain the complete answer.",
        "Return only JSON matching the schema.",
    ]
    return "\n".join(lines)
