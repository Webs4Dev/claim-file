import json
import logging
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import (
    BackgroundTasks,
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
    Header,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from approval.human_gate import (
    approve_claim,
    reject_claim,
)
from graph.workflow import app as workflow_app
from state.schema import (
    ClaimDocument,
    ClaimForm,
    ClaimState,
)
from state.store import (
    list_claims,
    delete_claim,
    load_claim,
    load_submission_claim,
    save_claim,
    save_submission_claim,
)


logger = logging.getLogger(__name__)

UPLOAD_DIRECTORY = Path("data/uploads")
UPLOAD_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True,
)


api = FastAPI(
    title="ClaimFile",
    description="Motor insurance claim processing API",
    version="1.0.0",
)


api.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HumanDecisionRequest(BaseModel):
    decided_by: str = Field(min_length=1, max_length=100)
    reason: str | None = Field(default=None, max_length=2000)


def save_uploaded_file(
    claim_id: str,
    document_type: str,
    file: UploadFile,
) -> str:
    claim_directory = UPLOAD_DIRECTORY / claim_id
    claim_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    extension = Path(file.filename or "").suffix.lower()

    file_path = (
        claim_directory
        / f"{document_type}{extension}"
    )

    file_path.write_bytes(file.file.read())

    return str(file_path)


def parse_claim_form(claim_form: str) -> ClaimForm:
    try:
        data = json.loads(claim_form)
    except json.JSONDecodeError as error:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid claim_form JSON: {error}",
        ) from error

    try:
        return ClaimForm.model_validate(data)
    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid claim form: {error}",
        ) from error


def collect_initial_documents(
    policy_schedule: UploadFile | None,
    vehicle_registration: UploadFile | None,
    driving_license: UploadFile | None,
    damage_survey_report: UploadFile | None,
    repair_estimate: UploadFile | None,
) -> list[tuple[str, UploadFile]]:
    uploads = [
        ("policy_schedule", policy_schedule),
        ("vehicle_registration", vehicle_registration),
        ("driving_license", driving_license),
        ("damage_survey_report", damage_survey_report),
        ("repair_estimate", repair_estimate),
    ]

    return [
        (document_type, file)
        for document_type, file in uploads
        if file is not None and file.filename
    ]


def collect_additional_documents(
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
        ("policy_schedule", policy_schedule),
        ("policy_document", policy_document),
        ("vehicle_registration", vehicle_registration),
        ("driving_license", driving_license),
        ("damage_survey_report", damage_survey_report),
        ("repair_estimate", repair_estimate),
        ("repair_invoice", repair_invoice),
        ("police_report", police_report),
        ("fir_document", fir_document),
        ("accident_report", accident_report),
    ]

    return [
        (document_type, file)
        for document_type, file in uploads
        if file is not None and file.filename
    ]


def validate_requested_documents(
    claim: ClaimState,
    uploaded_documents: list[tuple[str, UploadFile]],
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
                    "was not requested for this claim."
                ),
            )


def remove_existing_document(
    claim: ClaimState,
    document_type: str,
) -> None:
    claim.claim_documents = [
        document
        for document in claim.claim_documents
        if document.document_type != document_type
    ]

    claim.documents = [
        path
        for path in claim.documents
        if Path(path).stem != document_type
    ]


def clear_uploaded_document_requests(
    claim: ClaimState,
    uploaded_types: list[str],
) -> None:
    uploaded_type_set = set(uploaded_types)

    claim.pending_documents = [
        document
        for document in claim.pending_documents
        if document.document_type not in uploaded_type_set
    ]


def build_public_response(state: ClaimState) -> dict:
    return {
        "claim_id": state.claim_id,
        "created_at": state.created_at.isoformat(),
        "claim_form": state.claim_form.model_dump(),
        "status": state.status,
        "documents": state.documents,
        "claim_documents": [
            document.model_dump()
            for document in state.claim_documents
        ],
        "pending_documents": [
            document.model_dump()
            for document in state.pending_documents
        ],
        "extracted_data": (
            state.extracted_data.model_dump()
            if state.extracted_data
            else None
        ),
        "document_validation": (
            state.document_validation.model_dump()
            if state.document_validation
            else None
        ),
        "investigation": (
            state.investigation.model_dump()
            if state.investigation
            else None
        ),
        "review": (
            state.review.model_dump()
            if state.review
            else None
        ),
        "human_approval": (
            state.human_approval.model_dump()
            if state.human_approval
            else None
        ),
    }


def validate_idempotency_key(key: str | None) -> str | None:
    if not key:
        return None
    try:
        return str(UUID(key))
    except (ValueError, TypeError) as error:
        raise HTTPException(
            status_code=400,
            detail="Idempotency-Key must be a UUID.",
        ) from error


def process_claim(claim_id: str) -> None:
    """Run a saved claim after the API has acknowledged its submission."""
    claim = load_claim(claim_id)
    if claim is None:
        return

    try:
        claim.status = "in_progress"
        save_claim(claim)
        result = workflow_app.invoke(claim)
        final_state = ClaimState.model_validate(result)
        save_claim(final_state)
    except Exception:
        # Keep the latest checkpoint recoverable without returning
        # implementation details or model traces to the client.
        logger.exception("Claim workflow failed for claim %s", claim_id)
        failed_state = load_claim(claim_id) or claim
        failed_state.status = "needs_internal_review"
        failed_state.current_agent = "supervisor"
        save_claim(failed_state)


@api.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "ClaimFile",
    }


@api.get("/claims")
def get_claims():
    claims = list_claims()

    return [
        build_public_response(claim)
        for claim in claims
    ]


@api.post("/claims")
def create_claim(
    background_tasks: BackgroundTasks,
    claim_form: str = Form(...),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    policy_schedule: UploadFile | None = File(None),
    vehicle_registration: UploadFile | None = File(None),
    driving_license: UploadFile | None = File(None),
    damage_survey_report: UploadFile | None = File(None),
    repair_estimate: UploadFile | None = File(None),
):
    form = parse_claim_form(claim_form)
    submission_key = validate_idempotency_key(idempotency_key)

    if submission_key:
        existing_id = load_submission_claim(submission_key)
        if existing_id:
            existing = load_claim(existing_id)
            if existing is not None:
                return build_public_response(existing)

    uploaded_documents = collect_initial_documents(
        policy_schedule,
        vehicle_registration,
        driving_license,
        damage_survey_report,
        repair_estimate,
    )

    if not uploaded_documents:
        raise HTTPException(
            status_code=400,
            detail="At least one document must be uploaded.",
        )

    claim_id = str(uuid4())
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
            ) from error

        document.file_path = save_uploaded_file(
            claim_id,
            document_type,
            file,
        )

        documents.append(document)

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

    save_claim(state)
    if submission_key and not save_submission_claim(submission_key, claim_id):
        existing_id = load_submission_claim(submission_key)
        delete_claim(claim_id)
        claim_directory = UPLOAD_DIRECTORY / claim_id
        for path in claim_directory.glob("*"):
            path.unlink(missing_ok=True)
        claim_directory.rmdir()
        existing = load_claim(existing_id) if existing_id else None
        if existing is not None:
            return build_public_response(existing)
        raise HTTPException(
            status_code=409,
            detail="This submission is still being received. Retry with the same request.",
        )

    background_tasks.add_task(process_claim, claim_id)
    return build_public_response(state)


@api.post("/claims/{claim_id}/retry")
def retry_claim(claim_id: str, background_tasks: BackgroundTasks):
    claim = load_claim(claim_id)

    if claim is None:
        raise HTTPException(
            status_code=404,
            detail="Claim not found.",
        )

    if claim.status not in {"needs_internal_review", "budget_exceeded"}:
        raise HTTPException(
            status_code=409,
            detail="Only claims under internal review can be rerun.",
        )

    # Start a fresh analysis using the same saved claim form and documents.
    claim.document_validation = None
    claim.extracted_data = None
    claim.investigation = None
    claim.review = None
    claim.human_approval = None
    claim.pending_documents = []
    claim.pending_investigation_actions = []
    claim.internal_investigation_count = 0
    claim.step_count = 0
    claim.token_usage = 0
    claim.estimated_cost = 0.0
    claim.workflow_trace = []
    claim.current_agent = "supervisor"
    claim.status = "in_progress"

    save_claim(claim)
    background_tasks.add_task(process_claim, claim_id)
    return build_public_response(claim)


@api.get("/claims/{claim_id}")
def get_claim(claim_id: str):
    claim = load_claim(claim_id)

    if claim is None:
        raise HTTPException(
            status_code=404,
            detail="Claim not found.",
        )

    return build_public_response(claim)


@api.post("/claims/{claim_id}/documents")
def upload_documents(
    claim_id: str,
    background_tasks: BackgroundTasks,
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
    claim = load_claim(claim_id)

    if claim is None:
        raise HTTPException(
            status_code=404,
            detail="Claim not found.",
        )

    if claim.status != "waiting_for_documents":
        raise HTTPException(
            status_code=400,
            detail="Claim is not waiting for additional documents.",
        )

    uploaded_documents = collect_additional_documents(
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

    if not uploaded_documents:
        raise HTTPException(
            status_code=400,
            detail="Upload at least one of the requested documents.",
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

        claim.documents.append(file_path)
        claim.claim_documents.append(document)
        uploaded_types.append(document_type)

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

    save_claim(claim)
    background_tasks.add_task(process_claim, claim_id)

    return build_public_response(claim)


@api.post("/claims/{claim_id}/approve")
def approve(
    claim_id: str,
    decision: HumanDecisionRequest,
):
    claim = load_claim(claim_id)

    if claim is None:
        raise HTTPException(
            status_code=404,
            detail="Claim not found.",
        )

    try:
        claim = approve_claim(
            claim,
            decision.decided_by,
            decision.reason,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    save_claim(claim)

    return build_public_response(claim)


@api.post("/claims/{claim_id}/reject")
def reject(
    claim_id: str,
    decision: HumanDecisionRequest,
):
    claim = load_claim(claim_id)

    if claim is None:
        raise HTTPException(
            status_code=404,
            detail="Claim not found.",
        )

    try:
        claim = reject_claim(
            claim,
            decision.decided_by,
            decision.reason,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    save_claim(claim)

    return build_public_response(claim)


app = api
