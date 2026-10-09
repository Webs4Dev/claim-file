from typing import Literal

from config import MAX_STEPS
from state.schema import ClaimState


SupervisorRoute = Literal[
    "extractor",
    "investigator",
    "reviewer",
    "waiting_for_documents",
    "needs_internal_review",
    "human_approval",
    "complete",
    "terminated",
]


def get_next_agent(
    state: ClaimState,
) -> SupervisorRoute:
    if state.status == "terminated":
        return "terminated"

    if state.status == "needs_internal_review":
        return "needs_internal_review"

    if state.step_count >= MAX_STEPS:
        state.status = "terminated"
        return "terminated"

    if state.extracted_data is None:
        if not state.documents:
            raise ValueError(
                "Claim must contain at least one document"
            )

        return "extractor"

    if state.investigation is None:
        return "investigator"

    if state.review is None:
        return "reviewer"

    review_status = state.review.status

    if review_status == "NEEDS_INVESTIGATION":
        state.pending_documents = state.review.required_documents

        if state.pending_documents:
            state.status = "waiting_for_documents"
            return "waiting_for_documents"

        state.pending_investigation_actions = (
            state.review.required_actions.copy()
        )
        state.status = "needs_internal_review"
        return "needs_internal_review"

    if review_status == "APPROVED":
        return "human_approval"

    if review_status == "REJECTED":
        state.status = "complete"
        return "complete"

    raise ValueError(
        f"Unknown review status: {review_status}"
    )


if __name__ == "__main__":
    print("Supervisor module loaded successfully.")
