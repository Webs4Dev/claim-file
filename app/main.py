from pathlib import Path
from uuid import uuid4

import json

from fastapi import (
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
)

from approval.human_gate import (
    approve_claim,
    reject_claim,
)
from graph.workflow import app
from state.schema import (
    ClaimDocument,
    ClaimForm,
    ClaimState,
)
from state.store import (
    load_claim,
    save_claim,
)


UPLOAD_DIRECTORY = Path(
    "data/uploads"
)

UPLOAD_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True,
)


api = FastAPI(
    title="ClaimFile",
    description="Motor insurance claim processing API",
    version="1.0.0",
)


SUPPORTED_DOCUMENT_FIELDS = {
    "policy_schedule": "policy_schedule",
    "policy_document": "policy_document",
    "vehicle_registration": "vehicle_registration",
    "driving_license": "driving_license",
    "damage_survey_report": "damage_survey_report",
    "repair_estimate": "repair_estimate",
    "repair_invoice": "repair_invoice",
    "police_report": "police_report",
    "fir_document": "fir_document",
    "accident_report": "accident_report",
}


def save_uploaded_file(
    claim_id: str,
    document_type: str,
    file: UploadFile,
) -> str:
    claim_directory = (
        UPLOAD_DIRECTORY / claim_id
    )

    claim_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    extension = Path(
        file.filename or ""
    ).suffix.lower()

    file_path = (
        claim_directory
        / f"{document_type}{extension}"
    )

    file_path.write_bytes(
        file.file.read()
    )

    return str(file_path)


def parse_claim_form(
    claim_form: str,
) -> ClaimForm:
    try:
        data = json.loads(
            claim_form
        )
    except json.JSONDecodeError as error:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid claim_form JSON: "
                f"{error}"
            ),
        )

    try:
        return ClaimForm.model_validate(
            data
        )
    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid claim form: "
                f"{error}"
            ),
        )


def collect_uploaded_documents(
    policy_schedule: UploadFile | None,
    policy_document: UploadFile | None,
    vehicle_registration: UploadFile | None,
    driving_license: UploadFile | None,
    damage_survey_report: UploadFile | None,
    repair_estimate: UploadFile | None,
    repair_invoice: UploadFile | None,
    police_report: UploadFile | None,
    fir_document: UploadFile | None,
    accident_report: UploadFile | None,
) -> list[tuple[str, UploadFile]]:
    uploads = [
        (
            "policy_schedule",
            policy_schedule,
        ),
        (
            "policy_document",
            policy_document,
        ),
        (
            "vehicle_registration",
            vehicle_registration,
        ),
        (
            "driving_license",
            driving_license,
        ),
        (
            "damage_survey_report",
            damage_survey_report,
        ),
        (
            "repair_estimate",
            repair_estimate,
        ),
        (
            "repair_invoice",
            repair_invoice,
        ),
        (
            "police_report",
            police_report,
        ),
        (
            "fir_document",
            fir_document,
        ),
        (
            "accident_report",
            accident_report,
        ),
    ]

    return [
        (
            document_type,
            file,
        )
        for document_type, file in uploads
        if file is not None
        and file.filename
    ]


def validate_requested_documents(
    claim: ClaimState,
    uploaded_documents: list[
        tuple[str, UploadFile]
    ],
) -> None:
    requested_types = {
        document.document_type
        for document in claim.pending_documents
    }

    for document_type, _ in uploaded_documents:
        if document_type not in requested_types:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Document type '{document_type}' "
                    f"was not requested for this claim."
                ),
            )


def remove_existing_document(
    claim: ClaimState,
    document_type: str,
) -> None:
    existing_documents = []

    for document in claim.claim_documents:
        if document.document_type != document_type:
            existing_documents.append(
                document
            )

    claim.claim_documents = existing_documents

    claim.documents = [
        path
        for path in claim.documents
        if not Path(path).stem.startswith(
            document_type
        )
    ]


def clear_uploaded_document_requests(
    claim: ClaimState,
    uploaded_types: list[str],
) -> None:
    uploaded_type_set = set(
        uploaded_types
    )

    claim.pending_documents = [
        document
        for document in claim.pending_documents
        if document.document_type
        not in uploaded_type_set
    ]


@api.get(
    "/health"
)
def health_check():
    return {
        "status": "ok"
    }


@api.post(
    "/claims"
)
def create_claim(
    claim_form: str = Form(...),

    policy_schedule: UploadFile | None = File(None),
    policy_document: UploadFile | None = File(None),
    vehicle_registration: UploadFile | None = File(None),
    driving_license: UploadFile | None = File(None),
    damage_survey_report: UploadFile | None = File(None),
    repair_estimate: UploadFile | None = File(None),
    repair_invoice: UploadFile | None = File(None),
    police_report: UploadFile | None = File(None),
    fir_document: UploadFile | None = File(None),
    accident_report: UploadFile | None = File(None),
):
    form = parse_claim_form(
        claim_form
    )

    uploaded_documents = (
        collect_uploaded_documents(
            policy_schedule,
            policy_document,
            vehicle_registration,
            driving_license,
            damage_survey_report,
            repair_estimate,
            repair_invoice,
            police_report,
            fir_document,
            accident_report,
        )
    )

    if not uploaded_documents:
        raise HTTPException(
            status_code=400,
            detail=(
                "At least one document must "
                "be uploaded."
            ),
        )

    claim_id = str(
        uuid4()
    )

    documents = []

    for document_type, file in uploaded_documents:
        try:
            document = ClaimDocument(
                document_type=document_type,
                file_path=None,
                uploaded=True,
                required=True,
            )
        except Exception as error:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Invalid document type "
                    f"{document_type}: {error}"
                ),
            )

        document.file_path = (
            save_uploaded_file(
                claim_id,
                document_type,
                file,
            )
        )

        documents.append(
            document
        )

    document_paths = [
        document.file_path
        for document in documents
        if document.file_path
    ]

    state = ClaimState(
        claim_id=claim_id,
        claim_form=form,
        documents=document_paths,
        claim_documents=documents,
    )

    result = app.invoke(
        state
    )

    final_state = ClaimState.model_validate(
        result
    )

    save_claim(
        final_state
    )

    return final_state.model_dump()


@api.get(
    "/claims/{claim_id}"
)
def get_claim(
    claim_id: str,
):
    claim = load_claim(
        claim_id
    )

    if claim is None:
        raise HTTPException(
            status_code=404,
            detail="Claim not found.",
        )

    return claim.model_dump()


@api.post(
    "/claims/{claim_id}/documents"
)
def upload_documents(
    claim_id: str,

    policy_schedule: UploadFile | None = File(None),
    policy_document: UploadFile | None = File(None),
    vehicle_registration: UploadFile | None = File(None),
    driving_license: UploadFile | None = File(None),
    damage_survey_report: UploadFile | None = File(None),
    repair_estimate: UploadFile | None = File(None),
    repair_invoice: UploadFile | None = File(None),
    police_report: UploadFile | None = File(None),
    fir_document: UploadFile | None = File(None),
    accident_report: UploadFile | None = File(None),
):
    claim = load_claim(
        claim_id
    )

    if claim is None:
        raise HTTPException(
            status_code=404,
            detail="Claim not found.",
        )

    if claim.status != "waiting_for_documents":
        raise HTTPException(
            status_code=400,
            detail=(
                "Claim is not waiting for "
                "additional documents."
            ),
        )

    uploaded_documents = (
        collect_uploaded_documents(
            policy_schedule,
            policy_document,
            vehicle_registration,
            driving_license,
            damage_survey_report,
            repair_estimate,
            repair_invoice,
            police_report,
            fir_document,
            accident_report,
        )
    )

    if not uploaded_documents:
        raise HTTPException(
            status_code=400,
            detail=(
                "Upload at least one of the "
                "requested documents."
            ),
        )

    validate_requested_documents(
        claim,
        uploaded_documents,
    )

    uploaded_types = []

    for document_type, file in uploaded_documents:
        remove_existing_document(
            claim,
            document_type,
        )

        file_path = save_uploaded_file(
            claim_id,
            document_type,
            file,
        )

        document = ClaimDocument(
            document_type=document_type,
            file_path=file_path,
            uploaded=True,
            required=True,
        )

        claim.documents.append(
            file_path
        )

        claim.claim_documents.append(
            document
        )

        uploaded_types.append(
            document_type
        )

    clear_uploaded_document_requests(
        claim,
        uploaded_types,
    )

    claim.document_validation = None
    claim.extracted_data = None
    claim.investigation = None
    claim.review = None

    claim.current_agent = "supervisor"
    claim.status = "in_progress"

    result = app.invoke(
        claim
    )

    final_state = ClaimState.model_validate(
        result
    )

    save_claim(
        final_state
    )

    return final_state.model_dump()


@api.post(
    "/claims/{claim_id}/approve"
)
def approve(
    claim_id: str,
):
    claim = load_claim(
        claim_id
    )

    if claim is None:
        raise HTTPException(
            status_code=404,
            detail="Claim not found.",
        )

    try:
        claim = approve_claim(
            claim
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    save_claim(
        claim
    )

    return claim.model_dump()


@api.post(
    "/claims/{claim_id}/reject"
)
def reject(
    claim_id: str,
):
    claim = load_claim(
        claim_id
    )

    if claim is None:
        raise HTTPException(
            status_code=404,
            detail="Claim not found.",
        )

    try:
        claim = reject_claim(
            claim
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    save_claim(
        claim
    )

    return claim.model_dump()


app = api