from graph.workflow import app
from state.schema import ClaimState


PDF_PATH = "data/sample_claims/claim_001.pdf"


def main():
    workflow = app

    state = ClaimState(
        claim_id="test-workflow-001",
        documents=[PDF_PATH],
    )

    print("\nWORKFLOW START")
    print("=" * 50)

    for event in workflow.stream(state):
        for node, node_state in event.items():
            current_state = ClaimState.model_validate(
                node_state
            )

            print(
                f"\nIteration {current_state.step_count}"
            )
            print(f"Agent: {node}")
            print(f"Current agent: {current_state.current_agent}")
            print(f"Status: {current_state.status}")
            print(f"Tokens: {current_state.token_usage}")
            print(
                f"Cost: "
                f"${current_state.estimated_cost:.6f}"
            )

    result = current_state

    print("\nWORKFLOW RESULT")
    print("=" * 50)

    print(f"Claim ID: {result.claim_id}")
    print(f"Current agent: {result.current_agent}")
    print(f"Status: {result.status}")
    print(f"Steps: {result.step_count}")
    print(f"Tokens used: {result.token_usage}")
    print(f"Estimated cost: ${result.estimated_cost:.6f}")

    print("\nEXTRACTION")
    print("=" * 50)
    print(
        result.extracted_data.model_dump_json(indent=2)
        if result.extracted_data
        else "No extraction result."
    )

    print("\nINVESTIGATION")
    print("=" * 50)
    print(
        result.investigation.model_dump_json(indent=2)
        if result.investigation
        else "No investigation result."
    )

    print("\nREVIEW")
    print("=" * 50)
    print(
        result.review.model_dump_json(indent=2)
        if result.review
        else "No review result."
    )


if __name__ == "__main__":
    main()
