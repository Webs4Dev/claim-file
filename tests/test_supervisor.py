from agents.supervisor import get_next_agent
from state.schema import (
    ClaimExtraction,
    ClaimState,
    InvestigationResult,
    ReviewResult,
)


def main():
    print("\nSUPERVISOR TEST")
    print("=" * 50)

    state = ClaimState(
        claim_id="supervisor-test-001",
        documents=["data/sample_claims/claim_001.pdf"],
    )

    print(f"1. Initial: {get_next_agent(state)}")

    state.extracted_data = ClaimExtraction()
    print(f"2. After extraction: {get_next_agent(state)}")

    state.investigation = InvestigationResult(
        overall_status="INSUFFICIENT_EVIDENCE"
    )
    print(f"3. After investigation: {get_next_agent(state)}")

    state.review = ReviewResult(
        status="NEEDS_INVESTIGATION",
        summary="More investigation required.",
        concerns=["Missing vehicle information."],
        required_actions=["Obtain vehicle documentation."],
    )

    print(f"4. Needs investigation: {get_next_agent(state)}")
    print(f"   Investigation cleared: {state.investigation is None}")
    print(f"   Review cleared: {state.review is None}")

    state.investigation = InvestigationResult(
        overall_status="VALID"
    )

    state.review = ReviewResult(
        status="APPROVED",
        summary="Investigation is sufficiently supported.",
    )

    print(f"5. Approved: {get_next_agent(state)}")

    state.review = ReviewResult(
        status="REJECTED",
        summary="Investigation establishes a validity problem.",
    )

    print(f"6. Rejected: {get_next_agent(state)}")
    print(f"   Status: {state.status}")

    state.step_count = 10
    state.status = "pending"
    state.review = None

    print(f"7. Max steps reached: {get_next_agent(state)}")
    print(f"   Status: {state.status}")


if __name__ == "__main__":
    main()