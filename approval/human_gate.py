from datetime import datetime, timezone

from state.schema import ClaimState, HumanApproval, ReviewRequest

# A reviewer can settle any claim the automation handed to people: the
# normal approval step, and claims it could not finish (internal review,
# budget exceeded), which could otherwise only be rerun.
DECIDABLE_STATUSES = {
    "human_approval",
    "needs_internal_review",
    "budget_exceeded",
}


def approve_claim(
    state: ClaimState,
    decided_by: str,
    reason: str | None = None,
) -> ClaimState:
    if state.status not in DECIDABLE_STATUSES:
        raise ValueError(
            f"Claim is not awaiting a human decision. "
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
    if state.status not in DECIDABLE_STATUSES:
        raise ValueError(
            f"Claim is not awaiting a human decision. "
            f"Current status: {state.status}"
        )

    if not decided_by.strip():
        raise ValueError("decided_by cannot be empty.")

    # The claimant is shown this reason, so a rejection always has one.
    if not (reason or "").strip():
        raise ValueError("Add a reason before rejecting the claim.")

    state.human_approval = HumanApproval(
        decision="REJECTED",
        decided_by=decided_by.strip(),
        decided_at=datetime.now(timezone.utc),
        reason=reason.strip(),
    )

    state.status = "terminated"
    state.current_agent = "human_gate"

    return state


def request_review(
    state: ClaimState,
    note: str | None = None,
) -> ClaimState:
    """Send an automatic rejection back to a person, at the claimant's request.

    Only a verdict nobody has looked at yet can be sent back: once a
    reviewer has decided, human_approval is set and this is refused, so a
    claimant can ask once per claim.
    """
    automatically_rejected = (
        state.status == "complete"
        and state.human_approval is None
        and state.review is not None
        and state.review.status == "REJECTED"
    )
    if not automatically_rejected:
        raise ValueError(
            "Only a claim rejected by the automated checks can be sent for review."
        )

    state.review_request = ReviewRequest(
        requested_at=datetime.now(timezone.utc),
        note=(note or "").strip() or None,
    )
    state.status = "human_approval"
    state.current_agent = "human_gate"

    return state
