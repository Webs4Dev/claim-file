from openai import OpenAI

from config import OPENAI_API_KEY, OPENAI_MODEL
from state.budget import (
    add_usage,
    can_make_model_call,
)
from state.cost import calculate_cost
from state.schema import (
    ClaimDocument,
    ClaimState,
    DocumentValidationResult,
)
from tools.documents import (
    read_document,
    validate_document_file,
)


client = OpenAI(
    api_key=OPENAI_API_KEY
)


DOCUMENT_DESCRIPTIONS = {
    "policy_schedule": (
        "A motor insurance policy schedule containing "
        "policy number, insured details, vehicle details, "
        "policy period, or coverage information."
    ),
    "policy_document": (
        "A motor insurance policy document containing "
        "policy terms, conditions, coverage, exclusions, "
        "or other contractual information."
    ),
    "vehicle_registration": (
        "A vehicle registration document containing "
        "registration information, vehicle details, "
        "and registered owner information."
    ),
    "driving_license": (
        "A driving licence containing driver identity, "
        "licence number, validity or expiry information, "
        "and authorized vehicle classes."
    ),
    "damage_survey_report": (
        "A vehicle damage survey or inspection report "
        "describing observed accident damage and assessment."
    ),
    "repair_estimate": (
        "A repair estimate describing expected repair work "
        "and estimated repair costs."
    ),
    "repair_invoice": (
        "A repair invoice showing completed repair work "
        "and associated charges."
    ),
    "police_report": (
        "An official police report relating to the accident "
        "or incident."
    ),
    "fir_document": (
        "A First Information Report or FIR document "
        "relating to the reported accident."
    ),
    "accident_report": (
        "An accident report describing the accident, "
        "incident circumstances, date, location, "
        "or related details."
    ),
}


def build_validation_prompt(
    document: ClaimDocument,
    document_text: str,
) -> str:
    expected_description = DOCUMENT_DESCRIPTIONS[
        document.document_type
    ]

    return f"""
You are the document validation agent for a motor insurance
claim processing system.

Determine whether the submitted file appears to be the
document type that it claims to be.

Claimed document type:
{document.document_type}

Expected document:
{expected_description}

Document content:
----------------
{document_text}
----------------

Evaluate only the submitted document.

Check:

1. Whether the document actually appears to be the claimed
   document type.

2. Whether it contains information normally expected for
   that document type.

3. Whether there are obvious internal contradictions.

4. Whether the document appears incomplete, corrupted,
   unrelated, or unusable.

5. Whether the submitted file provides enough evidence to
   establish authenticity.

Return exactly one status:

VALID
The document clearly appears to be the claimed document type,
is sufficiently coherent and usable, and contains no clear
evidence that it is invalid.

INVALID
The document clearly does not represent the claimed document
type, or contains clear evidence that it is invalid,
contradictory, corrupted, or unusable.

UNVERIFIED
The document appears to be the claimed document type and may
be usable, but authenticity cannot be established from the
submitted file alone.

Important rules:

- Do not invent missing information.
- Do not assume that a document is genuine merely because
  it looks official.
- Do not reject a document only because an optional field
  is absent.
- Preserve uncertainty when authenticity cannot be established.
- Do not make a claim approval or rejection decision.
- Do not use general insurance knowledge to invent facts
  about the submitted document.
""".strip()


def validate_document(
    document: ClaimDocument,
) -> tuple[
    ClaimDocument,
    int,
    int,
    float,
]:
    if not document.file_path:
        document.validity = "INVALID"
        document.validation_reason = (
            "No file path was provided."
        )

        return (
            document,
            0,
            0,
            0.0,
        )

    file_is_valid, file_reason = (
        validate_document_file(
            document.file_path
        )
    )

    if not file_is_valid:
        document.validity = "INVALID"
        document.validation_reason = file_reason

        return (
            document,
            0,
            0,
            0.0,
        )

    document_text = read_document(
        document.file_path
    )

    prompt = build_validation_prompt(
        document=document,
        document_text=document_text,
    )

    response = client.responses.parse(
        model=OPENAI_MODEL,
        input=[
            {
                "role": "system",
                "content": (
                    "Validate insurance documents "
                    "conservatively and return only "
                    "the requested structured result."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        text_format=ClaimDocument,
        max_output_tokens=500,
    )

    usage = response.usage

    input_tokens = (
        usage.input_tokens
        if usage
        else 0
    )

    output_tokens = (
        usage.output_tokens
        if usage
        else 0
    )

    cost = calculate_cost(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )

    result = response.output_parsed

    if result is None:
        raise ValueError(
            "Validator model did not return "
            "structured output."
        )

    document.validity = result.validity
    document.validation_reason = (
        result.validation_reason
    )

    return (
        document,
        input_tokens,
        output_tokens,
        cost,
    )


def validate_documents(
    state: ClaimState,
) -> ClaimState:
    if not can_make_model_call(state):
        state.status = "budget_exceeded"
        state.current_agent = "supervisor"

        return state

    if not state.claim_documents:
        state.document_validation = (
            DocumentValidationResult(
                all_required_documents_present=False,
                documents=[],
                missing_documents=[],
                invalid_documents=[],
                unverified_documents=[],
            )
        )

        state.status = "waiting_for_documents"
        state.current_agent = "supervisor"
        state.step_count += 1

        return state

    validated_documents = []

    for document in state.claim_documents:
        if not document.uploaded:
            validated_documents.append(
                document
            )
            continue

        if not can_make_model_call(state):
            state.status = "budget_exceeded"
            state.current_agent = "supervisor"

            return state

        (
            validated_document,
            input_tokens,
            output_tokens,
            cost,
        ) = validate_document(
            document
        )

        add_usage(
            state,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
        )

        validated_documents.append(
            validated_document
        )

    missing_documents = [
        document.document_type
        for document in validated_documents
        if document.required
        and not document.uploaded
    ]

    invalid_documents = [
        document.document_type
        for document in validated_documents
        if document.required
        and document.validity == "INVALID"
    ]

    unverified_documents = [
        document.document_type
        for document in validated_documents
        if document.required
        and document.validity == "UNVERIFIED"
    ]

    all_required_documents_present = (
        len(missing_documents) == 0
        and len(invalid_documents) == 0
        and len(unverified_documents) == 0
    )

    state.document_validation = (
        DocumentValidationResult(
            all_required_documents_present=(
                all_required_documents_present
            ),
            documents=validated_documents,
            missing_documents=missing_documents,
            invalid_documents=invalid_documents,
            unverified_documents=unverified_documents,
        )
    )

    state.claim_documents = validated_documents

    state.current_agent = "supervisor"
    state.status = "in_progress"
    state.step_count += 1

    return state