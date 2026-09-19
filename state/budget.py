from config import MAX_COST, MAX_STEPS, MAX_TOKENS
from state.schema import ClaimState


def steps_remaining(state: ClaimState) -> int:
    return max(
        MAX_STEPS - state.step_count,
        0,
    )


def tokens_remaining(state: ClaimState) -> int:
    return max(
        MAX_TOKENS - state.token_usage,
        0,
    )


def cost_remaining(state: ClaimState) -> float:
    return max(
        MAX_COST - state.estimated_cost,
        0.0,
    )


def budget_exceeded(state: ClaimState) -> bool:
    return (
        state.step_count >= MAX_STEPS
        or state.token_usage >= MAX_TOKENS
        or state.estimated_cost >= MAX_COST
    )


def can_make_model_call(
    state: ClaimState,
) -> bool:
    return not budget_exceeded(state)


def add_usage(
    state: ClaimState,
    input_tokens: int,
    output_tokens: int,
    cost: float,
) -> None:
    state.token_usage += (
        input_tokens + output_tokens
    )

    state.estimated_cost += cost