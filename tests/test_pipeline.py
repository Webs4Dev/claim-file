import json

from graph.workflow import app
from state.schema import (
    ClaimDocument,
    ClaimForm,
    ClaimState,
)


CLAIM_ID = "claim-test-001"


CLAIM_FORM = ClaimForm(
    policy_number="TEST-POL-3510203118",
    insured_name="Suresh Kumar Pillai",
    vehicle_registration_number="TN 39 BZ 4521",
    vehicle_make="Maruti",
    vehicle_model="Swift",
    accident_date="15/06/2026",
    accident_time="18:45",
    accident_location=(
        "Avinashi Road, Tirupur, Tamil Nadu"
    ),
    accident_description=(
        "Vehicle accident resulting in damage."
    ),
    driver_name="Suresh Kumar Pillai",
    driver_license_number=(
        "TEST-TN38-20140012345"
    ),
    damage_description=(
        "Front bumper, bonnet, left headlight "
        "and radiator grille damaged."
    ),
    third_party_involved=False,
    additional_information={
        "estimated_repair_cost": "45000"
    },
)


DOCUMENTS = [
    ClaimDocument(
        document_type="policy_schedule",
        file_path=(
            "data/sample_claims/"
            "claim_001/"
            "policy_schedule.pdf"
        ),
        uploaded=True,
        required=True,
    ),
    ClaimDocument(
        document_type="driving_license",
        file_path=(
            "data/sample_claims/"
            "claim_001/"
            "driving_licence.pdf"
        ),
        uploaded=True,
        required=True,
    ),
    ClaimDocument(
        document_type="vehicle_registration",
        file_path=(
            "data/sample_claims/"
            "claim_001/"
            "vehicle_registration.pdf"
        ),
        uploaded=True,
        required=True,
    ),
    ClaimDocument(
        document_type="damage_survey_report",
        file_path=(
            "data/sample_claims/"
            "claim_001/"
            "damage_survey_report.pdf"
        ),
        uploaded=True,
        required=True,
    ),
    ClaimDocument(
        document_type="repair_estimate",
        file_path=(
            "data/sample_claims/"
            "claim_001/"
            "repair_estimate.pdf"
        ),
        uploaded=True,
        required=True,
    ),
]


def run_test_pipeline() -> ClaimState:
    document_paths = [
        document.file_path
        for document in DOCUMENTS
        if document.file_path
    ]

    state = ClaimState(
        claim_id=CLAIM_ID,
        claim_form=CLAIM_FORM,
        documents=document_paths,
        claim_documents=DOCUMENTS,
    )

    result = app.invoke(state)

    return ClaimState.model_validate(result)


def print_workflow_trace(
    state: ClaimState,
) -> None:
    print()
    print("=" * 60)
    print("WORKFLOW TRACE")
    print("=" * 60)

    for item in state.workflow_trace:
        print(
            f"STEP {item['step']}: "
            f"{item['node']}"
        )
        print(
            f"  Status: {item['status']}"
        )
        print(
            f"  Current agent: "
            f"{item['current_agent']}"
        )
        print()


def validate_expected_result(
    state: ClaimState,
) -> None:
    print("=" * 60)
    print("FINAL RESULT")
    print("=" * 60)

    print("STATUS:", state.status)
    print("STEP COUNT:", state.step_count)
    print("TOKEN USAGE:", state.token_usage)
    print("ESTIMATED COST:", state.estimated_cost)

    if state.review:
        print(
            "REVIEW STATUS:",
            state.review.status,
        )

    print(
        "PENDING DOCUMENTS:",
        [
            document.document_type
            for document in state.pending_documents
        ],
    )

    print_workflow_trace(state)


if __name__ == "__main__":
    final_state = run_test_pipeline()

    validate_expected_result(
        final_state
    )

    print()
    print("=" * 60)
    print("FULL FINAL STATE")
    print("=" * 60)

    print(
        json.dumps(
            final_state.model_dump(),
            indent=2,
            ensure_ascii=False,
        )
    )