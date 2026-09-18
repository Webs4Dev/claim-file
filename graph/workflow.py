from langgraph.graph import END, START, StateGraph

from agents.extractor import extract_claim_data
from agents.investigator import investigate_claim
from agents.reviewer import review_claim
from agents.supervisor import get_next_agent
from config import MAX_STEPS
from state.schema import ClaimState


def supervisor_node(state: ClaimState) -> ClaimState:
    state.current_agent = "supervisor"

    if state.step_count >= MAX_STEPS:
        state.status = "terminated"

    return state


def route_from_supervisor(state: ClaimState) -> str:
    return get_next_agent(state)


def build_workflow():
    workflow = StateGraph(ClaimState)

    workflow.add_node(
        "supervisor",
        supervisor_node,
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
        route_from_supervisor,
        {
            "extractor": "extractor",
            "investigator": "investigator",
            "reviewer": "reviewer",
            "human_approval": END,
            "complete": END,
            "terminated": END,
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