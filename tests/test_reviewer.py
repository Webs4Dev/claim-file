from agents.extractor import extract_claim_data
from agents.investigator import investigate_claim
from agents.reviewer import review_claim
from state.schema import ClaimState

PDF_PATH = "data/sample_claims/claim_001.pdf"

def main():
    state = ClaimState(
        claim_id="test-review-001",
        documents=[PDF_PATH],
    )

    state = extract_claim_data(state)
    state = investigate_claim(state)
    state = review_claim(state)

    print("\nREVIEW RESULT")
    print("=" * 50)
    print(state.review.model_dump_json(indent=2))

    print("\nCLAIM STATE")
    print("=" * 50)
    print(f"Current agent: {state.current_agent}")
    print(f"Status: {state.status}")
    print(f"Steps: {state.step_count}")


if __name__ == "__main__":
    main()