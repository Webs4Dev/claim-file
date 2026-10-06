from datetime import datetime, timezone

from state.schema import ClaimState, HumanApproval


def approve_claim(
    state: ClaimState,
    decided_by: str,
    reason: str | None = None,
) -> ClaimState:
    if state.status != "human_approval":
        raise ValueError(
            f"Claim is not awaiting human approval. "
            f"Current status: {state.status}"
        )

    if not decided_by.strip():
        raise ValueError("decided_by cannot be empty.")

    state.human_approval = HumanApproval(
        decision="APPROVED",
        decided_by=decided_by.strip(),
        decided_at=datetime.now(timezone.utc),
        reason=reason,
    )

    state.status = "complete"
    state.current_agent = "human_gate"

    return state


def reject_claim(
    state: ClaimState,
    decided_by: str,
    reason: str | None = None,
) -> ClaimState:
    if state.status != "human_approval":
        raise ValueError(
            f"Claim is not awaiting human approval. "
            f"Current status: {state.status}"
        )

    if not decided_by.strip():
        raise ValueError("decided_by cannot be empty.")

    state.human_approval = HumanApproval(
        decision="REJECTED",
        decided_by=decided_by.strip(),
        decided_at=datetime.now(timezone.utc),
        reason=reason,
    )

    state.status = "terminated"
    state.current_agent = "human_gate"

    return state