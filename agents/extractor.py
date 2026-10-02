from openai import OpenAI

from config import OPENAI_API_KEY, OPENAI_MODEL
from state.budget import (
    add_usage,
    can_make_model_call,
    max_output_tokens,
)
from state.cost import calculate_cost
from state.schema import ClaimExtraction, ClaimState
from tools.documents import read_document


client = OpenAI(
    api_key=OPENAI_API_KEY
)


def build_document_text(
    state: ClaimState,
) -> str:
    documents = []

    for document in state.claim_documents:
        if not document.file_path:
            continue

        if not document.uploaded:
            continue

        if document.validity == "INVALID":
            continue

        documents.append(
            (
                f"DOCUMENT TYPE: "
                f"{document.document_type}\n"
                f"FILE: "
                f"{document.file_path}\n"
                f"VALIDITY: "
                f"{document.validity}\n"
                f"CONTENT:\n"
                f"{read_document(document.file_path)}"
            )
        )

    if not documents:
        return (
            "No readable supporting documents "
            "are currently available."
        )

    return "\n\n".join(documents)


def build_extraction_prompt(
    state: ClaimState,
    document_text: str,
) -> str:
    claim_form = state.claim_form.model_dump_json(
        indent=2
    )

    return f"""
You are the document extraction agent for a car insurance
claim system.

Your task is strictly extraction.

Extract structured claim information from:

1. The online claim form.
2. The submitted supporting documents.

Return only information explicitly supported by those sources.


============================================================
ONLINE CLAIM FORM
============================================================

The following information was submitted directly by the claimant.

<claim_form>
{claim_form}
</claim_form>


============================================================
DOCUMENT SET
============================================================

The following documents are currently available.

A claim may contain documents from multiple submission rounds.

Always consider ALL available documents together.

A newly provided document supplements existing claim information.

It does not automatically replace information from the claim form
or earlier documents.

<documents>
{document_text}
</documents>


============================================================
CORE EXTRACTION PRINCIPLE
============================================================

Be conservative.

Never invent, assume, calculate, or infer information.

If a value is explicitly present in the online claim form and
corresponds to a ClaimExtraction field, extract that value.

The absence of that value from a supporting document does NOT
make the claim-form value null.

For example:

If the online claim form contains:

policy_number = "3510203118"

then:

ClaimExtraction.policy.policy_number

MUST contain:

"3510203118"

even if the submitted policy document does not contain a
readable policy number.

Similarly, directly submitted claim-form values should not be
discarded merely because a supporting document is missing,
incomplete, or does not repeat the same field.


============================================================
SOURCE PRIORITY
============================================================

For extraction purposes:

1. Explicit online claim-form values must be extracted into the
   corresponding ClaimExtraction fields.

2. Supporting documents may provide additional values that are
   absent from the claim form.

3. Supporting documents may provide more detailed values for a
   field.

4. If sources disagree, DO NOT decide which source is correct.

   Preserve the information that can be represented by the schema
   and do not hide the disagreement through interpretation.

The Investigator is responsible for investigating contradictions
and determining what the evidence means.


============================================================
EXTRACTION RULES
============================================================

1. POLICY INFORMATION

Extract policy information explicitly present in:

- the online claim form
- policy schedules
- policy documents
- other submitted claim documents

In particular, extract:

- policy number
- insurance period

If the claim form contains a policy number, extract it even when
the supporting policy document does not repeat it.

Do not require the policy document to confirm a claim-form policy
number before extracting it.

Do not determine whether the policy is active.

Do not determine whether coverage applies.

Those are Investigator responsibilities.


2. VEHICLE INFORMATION

Extract:

- registration number
- make
- model

If the source clearly identifies:

Make: Maruti
Model: Swift

extract:

make = "Maruti"
model = "Swift"

If a combined value such as:

Maruti Swift

is provided, separate make and model only when the source clearly
supports that separation.

Do not use external knowledge to identify a model.


3. ACCIDENT INFORMATION

Extract:

- date
- time
- location
- description

Preserve the source wording where possible.

Do not infer circumstances that are not explicitly stated.


4. DRIVER INFORMATION

Extract:

- driver name
- licence number
- licence expiry date
- authorized vehicle types

Extract claim-form values when present.

Use supporting documents to supplement missing information.

Do not determine whether the licence is valid for the vehicle.


5. DAMAGE INFORMATION

Extract:

- damage description
- estimated repair cost

Do not determine whether the damage is genuine.

Do not determine whether the repair amount is reasonable.


6. POLICE INFORMATION

Extract:

- FIR number
- FIR date
- police station

If the source explicitly states:

"No FIR filed"

preserve that information in the appropriate schema field when
possible.

Do not decide whether an FIR was legally required.


7. THIRD-PARTY INVOLVEMENT

Extract the explicitly submitted value.

Do not infer third-party involvement from the accident description.


8. NAME FIELDS

Name fields must contain only the person's name.

Do not include:

- address
- phone number
- ID number
- policy number
- other adjacent information

inside a name field.


9. EXPLICIT NEGATIVE VALUES

If a source explicitly contains:

- NA
- N/A
- NO
- NONE
- NOT APPLICABLE

preserve that value when the schema permits it.

Use null only when information is genuinely absent, blank,
unreadable, or cannot be found.


10. DOCUMENT VALIDITY

INVALID documents must not be used as supporting evidence.

Documents that pass validation may be used as supporting evidence.

Do not make an independent validity or authenticity determination
during extraction.

The Validator is responsible for document-level validation.


11. MULTIPLE DOCUMENTS

Consider all available documents together.

Do not automatically treat the newest document as correct.

Do not automatically treat one document as authoritative unless
the source explicitly establishes that.


12. CONTRADICTIONS

If the claim form and a supporting document provide different
values:

- do not choose one based on what seems more likely;
- do not use external knowledge to resolve the difference;
- preserve the information that can be represented by the schema;
- do not hide the contradiction.

The Investigator is responsible for investigating contradictions.


13. NO CROSS-CONTAMINATION

Do not combine information across different:

- people
- vehicles
- policies
- claims

unless the available evidence explicitly establishes that they
refer to the same claim.


14. NO INTERPRETATION

Do not perform:

- coverage decisions
- validity decisions
- liability decisions
- fraud decisions
- authenticity decisions
- policy interpretation

Only extract information.


15. SCHEMA CONFORMANCE

Return data that conforms exactly to ClaimExtraction.

Use the correct fields and types.

For list fields, preserve separately stated values as separate
items.


16. WHEN IN DOUBT

If a value is genuinely absent from both the online claim form
and all usable supporting documents, return null.

Do NOT return null merely because a value is absent from one
particular supporting document when the value is explicitly
present in the online claim form.

Return only the structured ClaimExtraction result.
""".strip()


def extract_claim_data(
    state: ClaimState,
) -> ClaimState:
    if not can_make_model_call(state):
        state.status = "budget_exceeded"
        state.current_agent = "supervisor"

        return state

    document_text = build_document_text(
        state
    )

    prompt = build_extraction_prompt(
        state=state,
        document_text=document_text,
    )

    allowed_output_tokens = max_output_tokens(
        state
    )

    if allowed_output_tokens <= 0:
        state.status = "budget_exceeded"
        state.current_agent = "supervisor"

        return state

    response = client.responses.parse(
        model=OPENAI_MODEL,
        input=[
            {
                "role": "system",
                "content": (
                    "You are a conservative claim "
                    "data extraction agent. "
                    "Every explicitly provided online "
                    "claim-form value that maps to the "
                    "ClaimExtraction schema must be "
                    "preserved in the structured output."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        text_format=ClaimExtraction,
        max_output_tokens=allowed_output_tokens,
    )

    extraction = response.output_parsed

    if extraction is None:
        raise ValueError(
            "No structured extraction was returned"
        )

    if response.usage:
        input_tokens = (
            response.usage.input_tokens or 0
        )

        output_tokens = (
            response.usage.output_tokens or 0
        )

        cost = calculate_cost(
            input_tokens,
            output_tokens,
        )

        add_usage(
            state,
            input_tokens,
            output_tokens,
            cost,
        )

    state.extracted_data = extraction
    state.current_agent = "supervisor"
    state.status = "in_progress"
    state.step_count += 1

    return state


if __name__ == "__main__":
    print(
        "Extractor module loaded successfully."
    )