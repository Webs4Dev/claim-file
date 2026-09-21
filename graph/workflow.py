from langgraph.graph import END, START, StateGraph

from agents.extractor import extract_claim_data
from agents.investigator import investigate_claim
from agents.reviewer import review_claim
from graph.routing import route_supervisor
from state.budget import budget_exceeded
from state.schema import ClaimState
from state.store import save_snapshot


def supervisor(
    state: ClaimState,
) -> ClaimState:
    if budget_exceeded(state):
        state.status = "budget_exceeded"
        return state

    if state.status == "waiting_for_documents":
        return state

    if state.extracted_data is None:
        state.current_agent = "extractor"
        state.status = "in_progress"
        return state

    if state.investigation is None:
        state.current_agent = "investigator"
        state.status = "in_progress"
        return state

    if state.review is None:
        state.current_agent = "reviewer"
        state.status = "in_progress"
        return state

    if state.review.status == "NEEDS_INVESTIGATION":
        state.status = "waiting_for_documents"
        state.current_agent = "supervisor"
        return state

    if state.review.status == "APPROVED":
        state.status = "complete"
        state.current_agent = "supervisor"
        return state

    if state.review.status == "REJECTED":
        state.status = "complete"
        state.current_agent = "supervisor"
        return state

    raise ValueError(
        f"Unknown review status: {state.review.status}"
    )


def save_state_snapshot(
    state: ClaimState,
) -> ClaimState:
    save_snapshot(state)
    return state


def build_workflow():
    workflow = StateGraph(ClaimState)

    workflow.add_node(
        "supervisor",
        supervisor,
    )

    workflow.add_node(
        "extractor",
        extract_claim_data,
    )

    workflow.add_node(
        "investigator",
        investigate_claim,
    )

    workflow.add_node(
        "reviewer",
        review_claim,
    )

    workflow.add_node(
        "save_snapshot",
        save_state_snapshot,
    )

    workflow.add_edge(
        START,
        "supervisor",
    )

    workflow.add_conditional_edges(
        "supervisor",
        route_supervisor,
        {
            "extractor": "extractor",
            "investigator": "investigator",
            "reviewer": "reviewer",
            END: END,
        },
    )

    workflow.add_edge(
        "extractor",
        "save_snapshot",
    )

    workflow.add_edge(
        "investigator",
        "save_snapshot",
    )

    workflow.add_edge(
        "reviewer",
        "save_snapshot",
    )

    workflow.add_edge(
        "save_snapshot",
        "supervisor",
    )

    return workflow.compile()


app = build_workflow()