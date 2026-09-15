from graph.workflow import build_workflow
from state.schema import ClaimState


PDF_PATH = "data/sample_claims/claim_001.pdf"


def main():
    workflow = build_workflow()

    state = ClaimState(
        claim_id="test-workflow-001",
        documents=[PDF_PATH],
    )

    result = workflow.invoke(state)
    result = ClaimState.model_validate(result)

    print("\nWORKFLOW RESULT")
    print("=" * 50)

    print(f"Current agent: {result.current_agent}")
    print(f"Status: {result.status}")
    print(f"Steps: {result.step_count}")

    print("\nEXTRACTION")
    print("=" * 50)
    print(result.extracted_data.model_dump_json(indent=2))

    print("\nINVESTIGATION")
    print("=" * 50)
    print(result.investigation.model_dump_json(indent=2))

    print("\nREVIEW")
    print("=" * 50)
    print(result.review.model_dump_json(indent=2))


if __name__ == "__main__":
    main()