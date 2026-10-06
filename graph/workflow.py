from langgraph.graph import END, START, StateGraph

from agents.extractor import extract_claim_data
from agents.investigator import investigate_claim
from agents.reviewer import review_claim
from agents.validator import validate_documents
from graph.routing import route_supervisor
from state.budget import budget_exceeded
from state.schema import (
    MAX_INTERNAL_INVESTIGATIONS,
    ClaimState,
)
from state.store import save_snapshot


def add_trace(
    state: ClaimState,
    node: str,
) -> ClaimState:
    state.workflow_trace.append(
        {
            "step": len(state.workflow_trace) + 1,
            "node": node,
            "status": state.status,
            "current_agent": state.current_agent,
        }
    )

    return state


def supervisor(
    state: ClaimState,
) -> ClaimState:
    if budget_exceeded(state):
        state.status = "budget_exceeded"
        state.current_agent = "supervisor"
        return add_trace(state, "supervisor")

    if state.status == "waiting_for_documents":
        state.current_agent = "supervisor"
        return add_trace(state, "supervisor")

    if state.status == "human_approval":
        state.current_agent = "supervisor"
        return add_trace(state, "supervisor")

    if state.status == "complete":
        state.current_agent = "supervisor"
        return add_trace(state, "supervisor")

    if state.status == "terminated":
        state.current_agent = "supervisor"
        return add_trace(state, "supervisor")

    if state.document_validation is None:
        state.current_agent = "validator"
        state.status = "in_progress"
        return add_trace(state, "supervisor")

    if not state.document_validation.all_required_documents_present:
        state.status = "waiting_for_documents"
        state.current_agent = "supervisor"
        return add_trace(state, "supervisor")

    if state.extracted_data is None:
        state.current_agent = "extractor"
        state.status = "in_progress"
        return add_trace(state, "supervisor")

    if state.investigation is None:
        state.current_agent = "investigator"
        state.status = "in_progress"
        return add_trace(state, "supervisor")

    if state.review is None:
        state.current_agent = "reviewer"
        state.status = "in_progress"
        return add_trace(state, "supervisor")

    if state.review.status == "NEEDS_INVESTIGATION":
        state.pending_documents = state.review.required_documents

        if state.pending_documents:
            state.status = "waiting_for_documents"
            state.current_agent = "supervisor"
            return add_trace(state, "supervisor")

        state.pending_investigation_actions = (
            state.review.required_actions.copy()
        )

        if (
            state.internal_investigation_count
            < MAX_INTERNAL_INVESTIGATIONS
        ):
            state.internal_investigation_count += 1
            state.investigation = None
            state.review = None
            state.status = "in_progress"
            state.current_agent = "investigator"
            return add_trace(state, "supervisor")

        state.status = "human_approval"
        state.current_agent = "supervisor"
        return add_trace(state, "supervisor")

    if state.review.status == "APPROVED":
        state.pending_investigation_actions = []
        state.status = "human_approval"
        state.current_agent = "supervisor"
        return add_trace(state, "supervisor")

    if state.review.status == "REJECTED":
        state.pending_investigation_actions = []
        state.status = "complete"
        state.current_agent = "supervisor"
        return add_trace(state, "supervisor")

    raise ValueError(
        f"Unknown review status: {state.review.status}"
    )


def validator_node(
    state: ClaimState,
) -> ClaimState:
    state = validate_documents(state)
    return add_trace(state, "validator")


def extractor_node(
    state: ClaimState,
) -> ClaimState:
    state = extract_claim_data(state)
    return add_trace(state, "extractor")


def investigator_node(
    state: ClaimState,
) -> ClaimState:
    state = investigate_claim(state)
    return add_trace(state, "investigator")


def reviewer_node(
    state: ClaimState,
) -> ClaimState:
    state = review_claim(state)
    return add_trace(state, "reviewer")


def snapshot_node(
    state: ClaimState,
) -> ClaimState:
    add_trace(state, "snapshot")
    save_snapshot(state)
    return state


workflow = StateGraph(ClaimState)

workflow.add_node(
    "supervisor",
    supervisor,
)

workflow.add_node(
    "validator",
    validator_node,
)

workflow.add_node(
    "extractor",
    extractor_node,
)

workflow.add_node(
    "investigator",
    investigator_node,
)

workflow.add_node(
    "reviewer",
    reviewer_node,
)

workflow.add_node(
    "snapshot",
    snapshot_node,
)

workflow.add_edge(
    START,
    "supervisor",
)

workflow.add_conditional_edges(
    "supervisor",
    route_supervisor,
    {
        "validator": "validator",
        "extractor": "extractor",
        "investigator": "investigator",
        "reviewer": "reviewer",
        END: END,
    },
)

workflow.add_edge(
    "validator",
    "snapshot",
)

workflow.add_edge(
    "extractor",
    "snapshot",
)

workflow.add_edge(
    "investigator",
    "snapshot",
)

workflow.add_edge(
    "reviewer",
    "snapshot",
)

workflow.add_edge(
    "snapshot",
    "supervisor",
)

app = workflow.compile()