from state.schema import ClaimState


def approve_claim(
    state: ClaimState,
) -> ClaimState:
    if state.status != "human_approval":
        raise ValueError(
            f"Claim is not awaiting human approval. "
            f"Current status: {state.status}"
        )

    state.status = "complete"
    state.current_agent = "human_gate"

    return state


def reject_claim(
    state: ClaimState,
) -> ClaimState:
    if state.status != "human_approval":
        raise ValueError(
            f"Claim is not awaiting human approval. "
            f"Current status: {state.status}"
        )

    state.status = "terminated"
    state.current_agent = "human_gate"

    return state