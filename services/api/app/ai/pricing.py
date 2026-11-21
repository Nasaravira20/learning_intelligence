from decimal import Decimal

# Internal estimates used only for the budget guard. They are not a provider invoice.
INPUT_USD_PER_MILLION = Decimal("0.50")
OUTPUT_USD_PER_MILLION = Decimal("3.00")
MILLION = Decimal("1000000")
QUANTUM = Decimal("0.00000001")


def estimate_cost(input_tokens: int, output_tokens: int) -> Decimal:
    cost = (
        Decimal(max(input_tokens, 0)) * INPUT_USD_PER_MILLION
        + Decimal(max(output_tokens, 0)) * OUTPUT_USD_PER_MILLION
    ) / MILLION
    return cost.quantize(QUANTUM)


def worst_case_tokens(prompt: str, max_output_tokens: int) -> tuple[int, int]:
    input_tokens = max(1, (len(prompt) + 3) // 4)
    return input_tokens, max(max_output_tokens, 0)
