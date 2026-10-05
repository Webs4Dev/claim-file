from agents.extractor import extract_claim_data
from state.schema import ClaimDocument, ClaimState


def test_extract_claim_data():
    documents = [
        ClaimDocument(
            document_type="policy_schedule",
            file_path="data/sample_claims/claim_001/policy_schedule.pdf",
            uploaded=True,
            validity="VALID",
            required=True,
        ),
        ClaimDocument(
            document_type="driving_license",
            file_path="data/sample_claims/claim_001/driving_licence.pdf",
            uploaded=True,
            validity="VALID",
            required=True,
        ),
        ClaimDocument(
            document_type="vehicle_registration",
            file_path="data/sample_claims/claim_001/vehicle_registration.pdf",
            uploaded=True,
            validity="VALID",
            required=True,
        ),
        ClaimDocument(
            document_type="damage_survey_report",
            file_path="data/sample_claims/claim_001/damage_survey_report.pdf",
            uploaded=True,
            validity="VALID",
            required=True,
        ),
        ClaimDocument(
            document_type="repair_estimate",
            file_path="data/sample_claims/claim_001/repair_estimate.pdf",
            uploaded=True,
            validity="VALID",
            required=True,
        ),
    ]

    state = ClaimState(
        claim_id="CLM-001",
        documents=[
            document.file_path
            for document in documents
            if document.file_path
        ],
        claim_documents=documents,
    )

    state = extract_claim_data(state)

    assert state.extracted_data is not None
    assert state.extracted_data.policy.policy_number is not None
    assert state.extracted_data.vehicle.registration_number is not None
    assert state.extracted_data.accident.date is not None
    assert state.extracted_data.driver.name is not None
    assert state.extracted_data.damage.description is not None
    assert state.step_count == 1

    print("\n" + "=" * 60)
    print("EXTRACTION OUTPUT")
    print("=" * 60)
    print(state.extracted_data.model_dump_json(indent=2))

    print("\n" + "=" * 60)
    print("BUDGET USAGE")
    print("=" * 60)
    print(f"Tokens used: {state.token_usage}")
    print(f"Estimated cost: ${state.estimated_cost:.6f}")


if __name__ == "__main__":
    test_extract_claim_data()