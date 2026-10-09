from langgraph.graph import END

from state.budget import budget_exceeded
from state.schema import ClaimState


def route_supervisor(
    state: ClaimState,
) -> str:
    if budget_exceeded(state):
        return END

    if state.status in {
        "waiting_for_documents",
        "needs_internal_review",
        "human_approval",
        "complete",
        "terminated",
    }:
        return END

    if state.current_agent == "validator":
        return "validator"

    if state.current_agent == "extractor":
        return "extractor"

    if state.current_agent == "investigator":
        return "investigator"

    if state.current_agent == "reviewer":
        return "reviewer"

    return END
