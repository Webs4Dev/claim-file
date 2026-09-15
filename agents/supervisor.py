from typing import Literal

from config import MAX_STEPS
from state.schema import ClaimState


SupervisorRoute = Literal[
    "extractor",
    "investigator",
    "reviewer",
    "human_approval",
    "complete",
    "terminated",
]


def get_next_agent(state: ClaimState) -> SupervisorRoute:
    if state.step_count >= MAX_STEPS:
        state.status = "terminated"
        return "terminated"

    if state.status == "terminated":
        return "terminated"

    if state.extracted_data is None:
        if not state.documents:
            raise ValueError("Claim must contain at least one document")

        return "extractor"

    if state.investigation is None:
        return "investigator"

    if not state.review:
        return "reviewer"

    review_status = state.review.status

    if review_status == "NEEDS_INVESTIGATION":
        state.investigation = None
        return "investigator"

    if review_status == "APPROVED":
        return "human_approval"

    if review_status == "REJECTED":
        state.status = "complete"
        return "complete"

    raise ValueError(
        f"Unknown review status: {review_status}"
    )