INPUT_COST_PER_MILLION = 0.20
OUTPUT_COST_PER_MILLION = 1.20


def calculate_cost(
    input_tokens: int,
    output_tokens: int,
) -> float:
    input_cost = (
        input_tokens * INPUT_COST_PER_MILLION / 1_000_000
    )

    output_cost = (
        output_tokens * OUTPUT_COST_PER_MILLION / 1_000_000
    )

    return input_cost + output_cost