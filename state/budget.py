from state.schema import ClaimState


def add_usage(
    state: ClaimState,
    input_tokens: int,
    output_tokens: int,
    cost: float,
) -> None:
    state.token_usage += input_tokens + output_tokens
    state.estimated_cost += cost


def budget_exceeded(state: ClaimState) -> bool:
    from config import MAX_COST, MAX_TOKENS

    return (
        state.token_usage >= MAX_TOKENS
        or state.estimated_cost >= MAX_COST
    )