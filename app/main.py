import json
import logging
import shutil
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    Header,
    Query,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError

from approval.human_gate import (
    approve_claim,
    reject_claim,
)
from auth.api import current_user, require_reviewer
from auth.api import router as auth_router
from auth.store import User
from config import ALLOWED_ORIGINS
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
from tools.documents import SUPPORTED_DOCUMENT_EXTENSIONS


logger = logging.getLogger(__name__)

UPLOAD_DIRECTORY = Path("data/uploads")

MAX_UPLOAD_BYTES = 10 * 1024 * 1024

MAX_PAGE_SIZE = 200

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
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
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api.include_router(auth_router)


@api.middleware("http")
async def reject_cross_site_writes(request: Request, call_next):
    """CSRF guard. SameSite=Lax still sends the cookie from other ports on
    the same host, so state-changing requests must come from an allowed
    origin. Browsers always send Origin on cross-site POSTs; requests
    without one (curl, scripts) cannot carry a victim's cookie."""
    origin = request.headers.get("origin")

    if (
        request.method in UNSAFE_METHODS
        and origin is not None
        and origin not in ALLOWED_ORIGINS
    ):
        return JSONResponse(
            status_code=403,
            content={"detail": "Cross-site request blocked."},
        )

    return await call_next(request)


class HumanDecisionRequest(BaseModel):
    # The decider is the signed-in reviewer, never a client-supplied name.
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

    if extension not in SUPPORTED_DOCUMENT_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"{document_type}: only "
                f"{', '.join(sorted(SUPPORTED_DOCUMENT_EXTENSIONS))} "
                "files are accepted."
            ),
        )

    file_path = (
        claim_directory
        / f"{document_type}{extension}"
    )

    # Read in chunks so an oversized upload is refused without holding it
    # in memory or filling the disk.
    written = 0
    with file_path.open("wb") as output:
        while chunk := file.file.read(1024 * 1024):
            written += len(chunk)
            if written > MAX_UPLOAD_BYTES:
                output.close()
                file_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=413,
                    detail=f"{document_type}: files must be 10 MB or smaller.",
                )
            output.write(chunk)

    return str(file_path)


def parse_claim_form(claim_form: str) -> ClaimForm:
    try:
        data = json.loads(claim_form)
    except json.JSONDecodeError as error:
        raise HTTPException(
            status_code=400,
            detail="claim_form is not valid JSON.",
        ) from error

    try:
        return ClaimForm.model_validate(data)
    except ValidationError as error:
        # Name the fields only; the full pydantic message echoes the input
        # and internal model details.
        fields = sorted({
            ".".join(str(part) for part in issue["loc"]) or "claim_form"
            for issue in error.errors()
        })
        raise HTTPException(
            status_code=400,
            detail=f"Check these claim form fields: {', '.join(fields)}.",
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
    # Server file paths (state.documents, each document's file_path) stay
    # internal; clients identify documents by document_type.
    return {
        "claim_id": state.claim_id,
        "owner_id": state.owner_id,
        "created_at": state.created_at.isoformat(),
        "claim_form": state.claim_form.model_dump(),
        "status": state.status,
        "claim_documents": [
            document.model_dump(exclude={"file_path"})
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
            state.document_validation.model_dump(
                exclude={"documents": {"__all__": {"file_path"}}}
            )
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


def load_accessible_claim(claim_id: str, user: User) -> ClaimState:
    claim = load_claim(claim_id)

    # 404 rather than 403, so claimants cannot probe which claim IDs exist.
    if claim is None or (
        user.role != "reviewer" and claim.owner_id != user.user_id
    ):
        raise HTTPException(
            status_code=404,
            detail="Claim not found.",
        )

    return claim


def ensure_not_own_claim(claim: ClaimState, reviewer: User) -> None:
    if claim.owner_id == reviewer.user_id:
        raise HTTPException(
            status_code=403,
            detail="Reviewers cannot decide claims they submitted.",
        )


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
def get_claims(
    status: str | None = Query(
        None,
        max_length=300,
        description="Comma-separated statuses to include; omit for all.",
    ),
    q: str = Query("", max_length=100),
    order: Literal["newest", "oldest"] = "newest",
    limit: int = Query(50, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
    user: User = Depends(current_user),
):
    statuses = {
        value.strip()
        for value in (status or "").split(",")
        if value.strip()
    }

    page = list_claims(
        # Claimants only ever see their own claims.
        owner_id=None if user.role == "reviewer" else user.user_id,
        statuses=statuses or None,
        query=q,
        oldest_first=order == "oldest",
        offset=offset,
        limit=limit,
    )

    return {
        "claims": [
            build_public_response(claim)
            for claim in page.claims
        ],
        "total": page.total,
        "status_counts": page.status_counts,
        "limit": limit,
        "offset": offset,
    }


def save_initial_documents(
    claim_id: str,
    uploaded_documents: list[tuple[str, UploadFile]],
) -> list[ClaimDocument]:
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
                detail=f"Invalid document type {document_type}.",
            ) from error

        document.file_path = save_uploaded_file(
            claim_id,
            document_type,
            file,
        )

        documents.append(document)

    return documents


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
    user: User = Depends(current_user),
):
    form = parse_claim_form(claim_form)
    submission_key = validate_idempotency_key(idempotency_key)

    # Scope keys per user so one account can never receive another
    # account's claim by reusing an idempotency key.
    if submission_key:
        submission_key = f"{user.user_id}:{submission_key}"

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

    try:
        documents = save_initial_documents(claim_id, uploaded_documents)
    except HTTPException:
        # Do not leave a half-written upload folder for a claim that was
        # never created.
        shutil.rmtree(UPLOAD_DIRECTORY / claim_id, ignore_errors=True)
        raise

    document_paths = [
        document.file_path
        for document in documents
        if document.file_path
    ]

    state = ClaimState(
        claim_id=claim_id,
        owner_id=user.user_id,
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
def retry_claim(
    claim_id: str,
    background_tasks: BackgroundTasks,
    reviewer: User = Depends(require_reviewer),
):
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
def get_claim(claim_id: str, user: User = Depends(current_user)):
    claim = load_accessible_claim(claim_id, user)

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
    user: User = Depends(current_user),
):
    claim = load_accessible_claim(claim_id, user)

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
    reviewer: User = Depends(require_reviewer),
):
    claim = load_claim(claim_id)

    if claim is None:
        raise HTTPException(
            status_code=404,
            detail="Claim not found.",
        )

    ensure_not_own_claim(claim, reviewer)

    try:
        claim = approve_claim(
            claim,
            f"{reviewer.name} ({reviewer.email})",
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
    reviewer: User = Depends(require_reviewer),
):
    claim = load_claim(claim_id)

    if claim is None:
        raise HTTPException(
            status_code=404,
            detail="Claim not found.",
        )

    ensure_not_own_claim(claim, reviewer)

    try:
        claim = reject_claim(
            claim,
            f"{reviewer.name} ({reviewer.email})",
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
