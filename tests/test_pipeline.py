from graph.workflow import app
from state.schema import (
    ClaimDocument,
    ClaimForm,
    ClaimState,
)
from state.store import save_claim


CLAIM_ID = "claim-test-001"

DOCUMENT_PATH = (
    "data/sample_claims/"
    "claim_001.pdf"
)


def build_test_claim() -> ClaimState:
    claim_form = ClaimForm(
        policy_number="3510203118P105423456",
        insured_name="Suresh Kumar Pillai",
        vehicle_registration_number=(
            "TN 39 BZ 4521"
        ),
        vehicle_make="Maruti",
        vehicle_model="Swift",
        accident_date="15/06/2018",
        accident_time="18:45",
        accident_location=(
            "Avinashi Road, Tirupur"
        ),
        accident_description=(
            "Vehicle accident resulting "
            "in damage."
        ),
        driver_name="Suresh Kumar Pillai",
        driver_license_number=(
            "TN38 20140012345"
        ),
        damage_description=(
            "Front bumper, bonnet, "
            "left headlight and radiator "
            "grill damaged."
        ),
        additional_information={
            "estimated_repair_cost": "45000"
        },
    )

    document = ClaimDocument(
        document_type="policy_document",
        file_path=DOCUMENT_PATH,
        uploaded=True,
        required=True,
    )

    return ClaimState(
        claim_id=CLAIM_ID,
        claim_form=claim_form,
        documents=[
            DOCUMENT_PATH
        ],
        claim_documents=[
            document
        ],
    )


def run_pipeline():
    state = build_test_claim()

    result = app.invoke(
        state
    )

    final_state = ClaimState.model_validate(
        result
    )

    save_claim(
        final_state
    )

    print(
        final_state.model_dump_json(
            indent=2
        )
    )


if __name__ == "__main__":
    run_pipeline()