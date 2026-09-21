from langgraph.graph import END

from state.budget import budget_exceeded
from state.schema import ClaimState


def route_supervisor(
    state: ClaimState,
) -> str:
    if budget_exceeded(state):
        return END

    if state.status == "waiting_for_documents":
        return END

    if state.current_agent == "extractor":
        return "extractor"

    if state.current_agent == "investigator":
        return "investigator"

    if state.current_agent == "reviewer":
        return "reviewer"

    return END