from agents.supervisor import get_next_agent
from state.schema import (
    ClaimExtraction,
    ClaimState,
    InvestigationResult,
    ReviewResult,
)

PDF_PATH = "data/sample_claims/claim_001.pdf"

def test_routes_to_extractor():
    state = ClaimState(
        claim_id="test-001",
        documents=[PDF_PATH],
    )

    assert get_next_agent(state) == "extractor"


def test_routes_to_investigator():
    state = ClaimState(
        claim_id="test-002",
        documents=[PDF_PATH],
        extracted_data=ClaimExtraction(),
    )

    assert get_next_agent(state) == "investigator"


def test_routes_to_reviewer():
    state = ClaimState(
        claim_id="test-003",
        documents=[PDF_PATH],
        extracted_data=ClaimExtraction(),
        investigation=InvestigationResult(
            overall_status="INSUFFICIENT_EVIDENCE"
        ),
    )

    assert get_next_agent(state) == "reviewer"


def test_routes_to_investigator_after_review():
    state = ClaimState(
        claim_id="test-004",
        documents=[PDF_PATH],
        extracted_data=ClaimExtraction(),
        investigation=InvestigationResult(
            overall_status="INSUFFICIENT_EVIDENCE"
        ),
        review=ReviewResult(
            status="NEEDS_INVESTIGATION",
            summary="More investigation is required.",
            concerns=["Vehicle class is missing."],
            required_actions=["Verify vehicle class."],
        ),
    )

    assert get_next_agent(state) == "investigator"
    assert state.investigation is None


def test_routes_to_human_approval():
    state = ClaimState(
        claim_id="test-005",
        documents=[PDF_PATH],
        extracted_data=ClaimExtraction(),
        investigation=InvestigationResult(
            overall_status="VALID"
        ),
        review=ReviewResult(
            status="APPROVED",
            summary="Investigation is sufficiently supported.",
        ),
    )

    assert get_next_agent(state) == "human_approval"


def test_routes_to_complete_after_rejection():
    state = ClaimState(
        claim_id="test-006",
        documents=[PDF_PATH],
        extracted_data=ClaimExtraction(),
        investigation=InvestigationResult(
            overall_status="INVALID"
        ),
        review=ReviewResult(
            status="REJECTED",
            summary="Investigation establishes a validity problem.",
        ),
    )

    assert get_next_agent(state) == "complete"
    assert state.status == "complete"


def test_routes_to_terminated():
    state = ClaimState(
        claim_id="test-007",
        status="terminated",
    )

    assert get_next_agent(state) == "terminated"


def test_missing_documents_raises_error():
    state = ClaimState(
        claim_id="test-008",
    )

    try:
        get_next_agent(state)
        assert False
    except ValueError as exc:
        assert str(exc) == "Claim must contain at least one document"

if __name__ == "__main__":
    test_routes_to_extractor()
    test_routes_to_investigator()
    test_routes_to_reviewer()
    test_routes_to_investigator_after_review()
    test_routes_to_human_approval()
    test_routes_to_complete_after_rejection()
    test_routes_to_terminated()
    test_missing_documents_raises_error()

    print("All supervisor tests passed.")