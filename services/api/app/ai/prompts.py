GENERATION_PROBE = "Reply with the single word ready."

STRUCTURED_PROMPTS = {
    "diagnostic": (
        "Name one beginner gap for the chain rule and a confidence of low, medium, or high. "
        "Return only the requested JSON."
    ),
    "teaching": (
        "Give a one-sentence explanation of the chain rule and one check question. "
        "Return only the requested JSON."
    ),
    "evaluation": (
        "A learner says the derivative of sin(x^2) is cos(x^2). Mark the verdict met or not_met "
        "and give a short reason. Return only the requested JSON."
    ),
}
