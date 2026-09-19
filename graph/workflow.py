from langgraph.graph import END, START, StateGraph

from agents.extractor import extract_claim_data
from agents.investigator import investigate_claim
from agents.reviewer import review_claim
from state.budget import budget_exceeded
from graph.routing import route_supervisor
from state.schema import ClaimState


def supervisor(state: ClaimState) -> ClaimState:
    if budget_exceeded(state):
        state.status = "budget_exceeded"
        return state

    if state.extracted_data is None:
        state.current_agent = "extractor"
        return state

    if state.investigation is None:
        state.current_agent = "investigator"
        return state

    if state.review is None:
        state.current_agent = "reviewer"
        return state

    if state.review.status == "NEEDS_INVESTIGATION":
        state.current_agent = "investigator"
        return state

    state.status = state.review.status.lower()
    state.current_agent = "completed"

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
        "supervisor",
    )

    workflow.add_edge(
        "investigator",
        "supervisor",
    )

    workflow.add_edge(
        "reviewer",
        "supervisor",
    )

    return workflow.compile()


app = build_workflow()