from agents.extractor import extract_claim_data
from agents.investigator import investigate_claim
from state.schema import ClaimState


def test_investigate_claim():
    state = ClaimState(
        claim_id="CLM-001",
        documents=["data/sample_claims/claim_001.pdf"]
    )

    state = extract_claim_data(state)

    print("\n" + "=" * 60)
    print("EXTRACTION OUTPUT")
    print("=" * 60)
    print(state.extracted_data.model_dump_json(indent=2))

    state = investigate_claim(state)

    assert state.investigation is not None
    assert state.investigation.overall_status
    assert len(state.investigation.findings) > 0

    print("\n" + "=" * 60)
    print("INVESTIGATION OUTPUT")
    print("=" * 60)
    print(state.investigation.model_dump_json(indent=2))

    print("\n" + "=" * 60)
    print(f"STEP COUNT: {state.step_count}")
    print("=" * 60)
    print("BUDGET USAGE")
    print("=" * 60)
    print(f"Tokens used: {state.token_usage}")
    print(f"Estimated cost: ${state.estimated_cost:.6f}")


if __name__ == "__main__":
    test_investigate_claim()