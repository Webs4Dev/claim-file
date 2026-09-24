from pathlib import Path
from uuid import uuid4
import json

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from approval.human_gate import (
    approve_claim,
    reject_claim,
)
from state.schema import (
    ClaimDocument,
    ClaimForm,
    ClaimState,
)
from state.store import (
    load_claim,
    save_claim,
)
from graph.workflow import app


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
    ).suffix

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
        data = json.loads(claim_form)
    except json.JSONDecodeError as error:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid claim_form JSON: {error}",
        )

    try:
        return ClaimForm.model_validate(
            data
        )
    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid claim form: {error}",
        )


def parse_document_types(
    document_types: str,
) -> list[str]:
    try:
        values = json.loads(
            document_types
        )
    except json.JSONDecodeError as error:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid document_types JSON: "
                f"{error}"
            ),
        )

    if not isinstance(values, list):
        raise HTTPException(
            status_code=400,
            detail="document_types must be a JSON list.",
        )

    return values


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
    document_types: str = Form(...),
    files: list[UploadFile] = File(...),
):
    form = parse_claim_form(
        claim_form
    )

    types = parse_document_types(
        document_types
    )

    if len(types) != len(files):
        raise HTTPException(
            status_code=400,
            detail=(
                "The number of document_types "
                "must match the number of files."
            ),
        )

    claim_id = str(
        uuid4()
    )

    documents = []

    for document_type, file in zip(
        types,
        files,
    ):
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

        document.file_path = save_uploaded_file(
            claim_id,
            document_type,
            file,
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
    document_types: str = Form(...),
    files: list[UploadFile] = File(...),
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

    types = parse_document_types(
        document_types
    )

    if len(types) != len(files):
        raise HTTPException(
            status_code=400,
            detail=(
                "The number of document_types "
                "must match the number of files."
            ),
        )

    for document_type, file in zip(
        types,
        files,
    ):
        try:
            document = ClaimDocument(
                document_type=document_type,
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

        document.file_path = save_uploaded_file(
            claim_id,
            document_type,
            file,
        )

        claim.documents.append(
            document.file_path
        )

        claim.claim_documents.append(
            document
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