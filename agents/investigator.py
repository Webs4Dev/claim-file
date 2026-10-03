import json
import re
from datetime import datetime
from openai import OpenAI
from config import OPENAI_API_KEY, OPENAI_MODEL

from state.budget import (
    add_usage,
    budget_exceeded,
    can_make_model_call,
    max_output_tokens,
)
from state.cost import calculate_cost
from state.schema import (
    DRIVER_LICENCE,
    POLICY_VALIDITY,
    ClaimExtraction,
    ClaimState,
    InvestigationFinding,
    InvestigationResult,
    InvestigationStatus,
)
from tools.policy import (
    POLICY_SEARCH_TOOL,
    search_policy,
)


client = OpenAI(
    api_key=OPENAI_API_KEY
)

MAX_POLICY_SEARCHES = 2
FINAL_OUTPUT_TOKEN_LIMIT = 5000


def parse_date(
    value: str,
) -> datetime | None:

    for date_format in (
        "%d/%m/%Y",
        "%d.%m.%Y",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(
                value.strip(),
                date_format,
            )
        except ValueError:
            continue

    return None


def normalize_text(
    value: str | None,
) -> str:

    if not value:
        return ""

    return re.sub(
        r"[^a-z0-9]",
        "",
        value.lower(),
    )


def normalize_policy_number(
    value: str | None,
) -> str:

    return normalize_text(value)


def normalize_registration_number(
    value: str | None,
) -> str:

    return normalize_text(value)


def normalize_license_number(
    value: str | None,
) -> str:

    return normalize_text(value)


def normalize_name(
    value: str | None,
) -> str:

    return normalize_text(value)


def normalize_vehicle_value(
    value: str | None,
) -> str:

    return normalize_text(value)


def normalize_time(
    value: str | None,
) -> str:

    if not value:
        return ""

    value = value.strip().upper()

    for time_format in (
        "%H:%M",
        "%H:%M:%S",
        "%I:%M %p",
        "%I:%M:%S %p",
    ):
        try:
            parsed = datetime.strptime(
                value,
                time_format,
            )

            return parsed.strftime("%H:%M")

        except ValueError:
            continue

    return normalize_text(value)


def calculate_policy_validity(
    extraction: ClaimExtraction,
) -> InvestigationStatus:

    if not extraction.policy.insurance_period:
        return "INSUFFICIENT_EVIDENCE"

    if not extraction.accident.date:
        return "INSUFFICIENT_EVIDENCE"

    try:
        start, end = (
            extraction.policy.insurance_period.split(
                " to "
            )
        )

    except ValueError:
        return "INSUFFICIENT_EVIDENCE"

    start_date = parse_date(start)

    end_date = parse_date(end)

    accident_date = parse_date(
        extraction.accident.date
    )

    if (
        not start_date
        or not end_date
        or not accident_date
    ):
        return "INSUFFICIENT_EVIDENCE"

    if start_date <= accident_date <= end_date:
        return "VALID"

    return "INVALID"


def calculate_license_validity(
    extraction: ClaimExtraction,
) -> InvestigationStatus:

    if not extraction.driver.license_expiry_date:
        return "INSUFFICIENT_EVIDENCE"

    if not extraction.accident.date:
        return "INSUFFICIENT_EVIDENCE"

    expiry_date = parse_date(
        extraction.driver.license_expiry_date
    )

    accident_date = parse_date(
        extraction.accident.date
    )

    if not expiry_date or not accident_date:
        return "INSUFFICIENT_EVIDENCE"

    if accident_date <= expiry_date:
        return "VALID"

    return "INVALID"


def build_document_validation_context(
    state: ClaimState,
) -> str:

    if state.document_validation is None:
        return (
            "No document validation result is available."
        )

    return state.document_validation.model_dump_json(
        indent=2
    )


def build_investigation_prompt(
    state: ClaimState,
    policy_status: InvestigationStatus,
    license_status: InvestigationStatus,
) -> str:

    extraction = state.extracted_data

    if extraction is None:
        raise ValueError(
            "Extracted claim data is required for investigation."
        )

    if state.review is not None:

        investigation_context = """

This is a re-investigation.

A previous review identified an issue requiring further
investigation.

Use the previous review only to identify what should be
re-examined. Do not treat it as factual evidence.

Base all findings on the current evidence.

"""

    else:

        investigation_context = """

This is the initial investigation of the claim.

"""

    claim_form = state.claim_form.model_dump_json(
        indent=2
    )

    document_validation = (
        build_document_validation_context(
            state
        )
    )

    previous_review = ""

    if state.review is not None:

        previous_review = f"""

PREVIOUS REVIEW

{state.review.model_dump_json(indent=2)}

"""

    return f"""

You are the Investigator agent for a motor insurance claim.

Investigate using:

1. Extracted claim data.

2. Online claim form data.

3. Document validation results.

4. Policy evidence retrieved through the policy search tool.

Do not perform document extraction.

Do not verify document authenticity.

Do not invent facts.

Do not make a final payout or approval decision.

{investigation_context}

DOCUMENT VALIDATION

VALID documents may be used as supporting evidence.

INVALID documents must not be treated as reliable evidence.

Use the validated document information when evaluating the claim.

Do not request another document merely because an existing
document has been validated as VALID.

POLICY SEARCH

Use the policy search tool only when a specific policy wording
question requires verification.

Use product "private_car".

You may search the policy knowledge base at most twice.

Do not use general insurance knowledge when the answer depends
on policy wording.

When investigating accidental damage to the insured vehicle,
policy searches must specifically target Section I / Own Damage.

For vehicle-damage coverage questions, do not use broad queries
such as:

"Does the policy cover accidental damage?"

Instead, search specifically for the applicable Section I wording.

The first policy search should focus on:

- Section I / Own Damage
- accidental loss or damage to the insured vehicle
- collision with a fixed object
- the actual accident circumstances
- whether that type of accidental collision falls within the
  Section I cover

For the current claim, the accident description should be used
to make the search specific. In particular, if the evidence
describes collision with a concrete median divider or another
fixed object, include that circumstance in the policy query.

If a second policy search is required, it should focus on:

- Section I exclusions
- Section I conditions
- reasonable-care requirements
- accident reporting requirements
- applicable deductibles
- conditions affecting accidental collision damage

Do not use unrelated add-on sections as evidence for Section I
Own Damage coverage.

For example, evidence concerning personal belongings,
No Claim Bonus, electric vehicle battery coverage, or other
optional/add-on covers must not be treated as evidence that
Section I Own Damage covers the claimed vehicle damage unless
the policy wording explicitly connects that section to the claim.

Do not conclude that the claim is covered merely because the
policy contains general language about accidental damage.

The retrieved policy evidence must contain wording relevant to
the applicable Section I / Own Damage coverage, exclusion,
condition, or deductible before it is used to support the
investigation.

If the retrieved evidence does not establish the applicable
coverage, report the limitation as INSUFFICIENT_EVIDENCE or
CONCERN rather than assuming coverage.

DETERMINISTIC RESULTS

Policy Validity: {policy_status}

Driver and Licence Information: {license_status}

These two statuses are computed by the system and must not be
overridden.

The licence status only checks whether the licence was unexpired
on the accident date.

Do not infer vehicle-class compatibility from the vehicle make
or model.

DETERMINISTIC CONSISTENCY CHECKS

The system compares these fields between the online claim form
and extracted data:

- policy number
- vehicle registration number
- accident date
- accident time
- driver licence number
- driver name
- vehicle make
- vehicle model

If both values exist and differ after normalization, report a
contradiction.

If the claim form has a value but extracted data does not,
report missing information rather than a contradiction.

Do not invent contradictions.

INVESTIGATION CATEGORIES

Produce exactly one finding for each:

- Policy Validity
- Driver and Licence Information
- Vehicle Information
- Accident Information
- Damage Information
- Third-Party Involvement
- Police/FIR Information

Each finding must have:

- category
- status
- finding
- evidence

Allowed statuses:

- VALID
- INVALID
- CONCERN
- INSUFFICIENT_EVIDENCE

Keep finding and evidence concise.

Use only evidence supported by the supplied data.

Do not infer fraud.

Do not invent policy requirements.

POLICY VALIDITY

Use the deterministic Policy Validity status.

Consider:

- policy number
- insurance period
- accident date
- policy wording when relevant

DRIVER AND LICENCE INFORMATION

Use the deterministic Driver and Licence Information status.

Consider:

- driver identity
- licence number
- licence expiry date
- authorized vehicle types

Do not claim vehicle-class compatibility unless the evidence
explicitly supports it.

VEHICLE INFORMATION

Compare:

- registration number
- make
- model
- vehicle identity
- consistency between submitted sources

If the available sources agree, treat the information as
consistent.

ACCIDENT INFORMATION

Compare:

- accident date
- accident time
- accident location
- accident description

Use deterministic checks for date and time.

Use the available evidence for location and description.

Do not invent accident circumstances.

DAMAGE INFORMATION

Compare:

- claimed damage
- survey findings
- repair estimate
- repair amount

Check for material inconsistencies between these sources.

Do not determine whether the repair amount is reasonable unless
the available policy evidence specifically makes that relevant.

THIRD-PARTY INVOLVEMENT

Use only the available evidence.

Compare the claim form and supporting evidence.

Do not infer third-party involvement without evidence.

POLICE/FIR INFORMATION

Use the available evidence.

Do not mark this category VALID merely because the claim says
there was no FIR.

Do not invent a legal requirement for an FIR.

Use INSUFFICIENT_EVIDENCE when the available evidence cannot
establish an important police/FIR fact.

OVERALL STATUS

Use:

INVALID when a validity problem is established.

CONCERN when further investigation is required but invalidity
is not established.

INSUFFICIENT_EVIDENCE when an important determination cannot be
made from the available evidence.

VALID only when the evidence is sufficient across the
investigated areas and no validity problem is identified.

MISSING INFORMATION

Only include materially relevant missing information.

A missing optional field is not automatically material.

CONTRADICTIONS

Only include actual contradictions between available evidence.

A missing value is not a contradiction.

Return only the structured investigation result.

ONLINE CLAIM FORM

<claim_form>

{claim_form}

</claim_form>

DOCUMENT VALIDATION

<document_validation>

{document_validation}

</document_validation>

EXTRACTED CLAIM DATA

<extracted_claim_data>

{extraction.model_dump_json(indent=2)}

</extracted_claim_data>

{previous_review}

""".strip()


def _create_deterministic_finding(
    category: str,
    status: InvestigationStatus,
    extraction: ClaimExtraction,
) -> InvestigationFinding:

    if category == POLICY_VALIDITY:

        if status == "VALID":

            finding = (
                "The accident date falls within the "
                "stated insurance period."
            )

        elif status == "INVALID":

            finding = (
                "The accident date falls outside the "
                "stated insurance period."
            )

        else:

            finding = (
                "Policy validity could not be established "
                "from the available dates."
            )

        evidence = (
            f"Insurance period is "
            f"{extraction.policy.insurance_period}; "
            f"accident date is "
            f"{extraction.accident.date}."
        )

    else:

        if status == "VALID":

            finding = (
                "The driver's licence was unexpired on "
                "the accident date. This does not confirm "
                "licence-vehicle compatibility."
            )

        elif status == "INVALID":

            finding = (
                "The driver's licence was not valid on "
                "the accident date."
            )

        else:

            finding = (
                "Driver licence validity could not be "
                "established from the available dates."
            )

        evidence = (
            f"Licence expiry date is "
            f"{extraction.driver.license_expiry_date}; "
            f"accident date is "
            f"{extraction.accident.date}."
        )

    return InvestigationFinding(
        category=category,
        status=status,
        finding=finding,
        evidence=evidence,
    )


def _deduplicate_findings(
    findings: list[InvestigationFinding],
) -> list[InvestigationFinding]:

    unique_findings = {}

    for finding in findings:

        if finding.category not in unique_findings:
            unique_findings[finding.category] = finding

    return list(
        unique_findings.values()
    )


def _add_missing_information(
    investigation: InvestigationResult,
    message: str,
) -> None:

    if message not in investigation.missing_information:

        investigation.missing_information.append(
            message
        )


def _add_contradiction(
    investigation: InvestigationResult,
    message: str,
) -> None:

    if message not in investigation.contradictions:

        investigation.contradictions.append(
            message
        )


def _check_value_consistency(
    investigation: InvestigationResult,
    claim_value: str | None,
    extracted_value: str | None,
    field_name: str,
    normalizer,
) -> None:

    claim_normalized = normalizer(
        claim_value
    )

    extracted_normalized = normalizer(
        extracted_value
    )

    if (
        claim_normalized
        and extracted_normalized
    ):

        if claim_normalized != extracted_normalized:

            _add_contradiction(
                investigation,
                (
                    f"{field_name} differs between the online "
                    f"claim form and extracted document data: "
                    f"claim form='{claim_value}', "
                    f"extracted='{extracted_value}'."
                ),
            )

    elif (
        claim_normalized
        and not extracted_normalized
    ):

        _add_missing_information(
            investigation,
            (
                f"{field_name} is provided in the online claim "
                f"form but is not available in the extracted "
                f"document data."
            ),
        )


def _check_date_consistency(
    investigation: InvestigationResult,
    claim_value: str | None,
    extracted_value: str | None,
    field_name: str,
) -> None:

    if claim_value and extracted_value:

        claim_date = parse_date(
            claim_value
        )

        extracted_date = parse_date(
            extracted_value
        )

        if claim_date and extracted_date:

            if (
                claim_date.date()
                != extracted_date.date()
            ):

                _add_contradiction(
                    investigation,
                    (
                        f"{field_name} differs between the online "
                        f"claim form and extracted document data: "
                        f"claim form='{claim_value}', "
                        f"extracted='{extracted_value}'."
                    ),
                )

            return

    _check_value_consistency(
        investigation,
        claim_value,
        extracted_value,
        field_name,
        normalize_text,
    )


def _check_time_consistency(
    investigation: InvestigationResult,
    claim_value: str | None,
    extracted_value: str | None,
    field_name: str,
) -> None:

    claim_normalized = normalize_time(
        claim_value
    )

    extracted_normalized = normalize_time(
        extracted_value
    )

    if (
        claim_normalized
        and extracted_normalized
    ):

        if (
            claim_normalized
            != extracted_normalized
        ):

            _add_contradiction(
                investigation,
                (
                    f"{field_name} differs between the online "
                    f"claim form and extracted document data: "
                    f"claim form='{claim_value}', "
                    f"extracted='{extracted_value}'."
                ),
            )

    elif (
        claim_normalized
        and not extracted_normalized
    ):

        _add_missing_information(
            investigation,
            (
                f"{field_name} is provided in the online claim "
                f"form but is not available in the extracted "
                f"document data."
            ),
        )


def _apply_deterministic_consistency_checks(
    investigation: InvestigationResult,
    state: ClaimState,
) -> None:

    extraction = state.extracted_data

    if extraction is None:
        return

    claim_form = state.claim_form

    _check_value_consistency(
        investigation,
        claim_form.policy_number,
        extraction.policy.policy_number,
        "Policy number",
        normalize_policy_number,
    )

    _check_value_consistency(
        investigation,
        claim_form.vehicle_registration_number,
        extraction.vehicle.registration_number,
        "Vehicle registration number",
        normalize_registration_number,
    )

    _check_date_consistency(
        investigation,
        claim_form.accident_date,
        extraction.accident.date,
        "Accident date",
    )

    _check_time_consistency(
        investigation,
        claim_form.accident_time,
        extraction.accident.time,
        "Accident time",
    )

    _check_value_consistency(
        investigation,
        claim_form.driver_license_number,
        extraction.driver.license_number,
        "Driver licence number",
        normalize_license_number,
    )

    _check_value_consistency(
        investigation,
        claim_form.driver_name,
        extraction.driver.name,
        "Driver name",
        normalize_name,
    )

    _check_value_consistency(
        investigation,
        claim_form.vehicle_make,
        extraction.vehicle.make,
        "Vehicle make",
        normalize_vehicle_value,
    )

    _check_value_consistency(
        investigation,
        claim_form.vehicle_model,
        extraction.vehicle.model,
        "Vehicle model",
        normalize_vehicle_value,
    )


def _enforce_deterministic_status(
    investigation: InvestigationResult,
    policy_status: InvestigationStatus,
    license_status: InvestigationStatus,
    extraction: ClaimExtraction,
) -> None:

    investigation.findings = (
        _deduplicate_findings(
            investigation.findings
        )
    )

    overrides = {
        POLICY_VALIDITY: policy_status,
        DRIVER_LICENCE: license_status,
    }

    findings_by_category = {
        finding.category: finding
        for finding in investigation.findings
    }

    for category, status in overrides.items():

        if category in findings_by_category:

            findings_by_category[
                category
            ].status = status

        else:

            investigation.findings.append(
                _create_deterministic_finding(
                    category,
                    status,
                    extraction,
                )
            )

    if "INVALID" in {
        policy_status,
        license_status,
    }:

        investigation.overall_status = "INVALID"


def _record_usage(
    state: ClaimState,
    response,
) -> None:

    if response.usage is None:
        return

    input_tokens = (
        response.usage.input_tokens
        or 0
    )

    output_tokens = (
        response.usage.output_tokens
        or 0
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


def _execute_policy_tool(
    arguments: str,
) -> str:

    try:

        parsed_arguments = json.loads(
            arguments
        )

    except json.JSONDecodeError as exc:

        raise ValueError(
            "Policy tool returned invalid arguments"
        ) from exc

    query = parsed_arguments.get(
        "query"
    )

    product = parsed_arguments.get(
        "product"
    )

    if not isinstance(
        query,
        str,
    ) or not query.strip():

        raise ValueError(
            "Policy tool query is required"
        )

    if not isinstance(
        product,
        str,
    ) or not product.strip():

        raise ValueError(
            "Policy tool product is required"
        )

    if product != "private_car":

        raise ValueError(
            "The current investigation scope supports "
            "private_car only"
        )

    return search_policy(
        query=query,
        product=product,
    )


def _run_investigation_model(
    state: ClaimState,
    policy_status: InvestigationStatus,
    license_status: InvestigationStatus,
) -> InvestigationResult | None:

    if not can_make_model_call(state):
        return None

    prompt = build_investigation_prompt(
        state,
        policy_status,
        license_status,
    )

    input_items = [
        {
            "role": "system",
            "content": (
                "You are a conservative motor insurance "
                "claim investigator."
            ),
        },
        {
            "role": "user",
            "content": prompt,
        },
    ]

    allowed_output_tokens = max_output_tokens(
        state
    )

    if allowed_output_tokens <= 0:
        return None

    response = client.responses.create(
        model=OPENAI_MODEL,
        input=input_items,
        tools=[
            POLICY_SEARCH_TOOL
        ],
        max_output_tokens=allowed_output_tokens,
    )

    _record_usage(
        state,
        response,
    )

    tool_calls = [
        item
        for item in response.output
        if item.type == "function_call"
        and item.name == "search_policy"
    ]

    policy_evidence = []

    for tool_call in tool_calls[
        :MAX_POLICY_SEARCHES
    ]:

        result = _execute_policy_tool(
            tool_call.arguments
        )

        policy_evidence.append(
            {
                "call_id": tool_call.call_id,
                "arguments": tool_call.arguments,
                "result": result,
            }
        )

    if budget_exceeded(state):
        return None

    evidence_text = ""

    if policy_evidence:

        evidence_text = (
            "\nPOLICY SEARCH EVIDENCE\n"
        )

        for index, evidence in enumerate(
            policy_evidence,
            start=1,
        ):

            evidence_text += (
                f"\nPolicy search {index}\n"
                f"Query: {evidence['arguments']}\n"
                f"Evidence:\n"
                f"{evidence['result']}\n"
            )

    extraction = state.extracted_data

    if extraction is None:
        return None

    compact_final_prompt = f"""

Produce the final structured investigation result.

You must return exactly 7 findings:

1. Policy Validity

2. Driver and Licence Information

3. Vehicle Information

4. Accident Information

5. Damage Information

6. Third-Party Involvement

7. Police/FIR Information

Allowed finding statuses:

VALID

INVALID

CONCERN

INSUFFICIENT_EVIDENCE

Use these deterministic statuses exactly:

Policy Validity: {policy_status}

Driver and Licence Information: {license_status}

Use the evidence below.

When evaluating Damage Information, distinguish between:

- Section I / Own Damage evidence
- Section I exclusions and conditions
- deductibles
- unrelated add-on or optional covers

Do not use unrelated add-on coverage as evidence for Section I
Own Damage.

Do not conclude that accidental collision damage is covered unless
the retrieved policy evidence actually supports that conclusion.

If the policy evidence does not establish whether the specific
accident circumstances are covered, state that the coverage
determination remains unsupported by the available policy evidence.

Keep every finding concise:

- finding: one or two short sentences

- evidence: one or two short sentences

Do not invent facts.

Do not infer fraud.

Do not invent policy requirements.

Do not make a payout or approval decision.

For missing_information:

include only material missing information.

For contradictions:

include only actual contradictions.

Overall status:

- INVALID if a validity problem is established.

- CONCERN if further investigation is needed without
  established invalidity.

- INSUFFICIENT_EVIDENCE if an important determination
  cannot be made.

- VALID only when evidence is sufficient and no validity
  problem exists.

CLAIM FORM:

{state.claim_form.model_dump_json()}

DOCUMENT VALIDATION:

{build_document_validation_context(state)}

EXTRACTED DATA:

{extraction.model_dump_json()}

{evidence_text}

Return only the structured InvestigationResult.

""".strip()

    final_output_tokens = min(
        max_output_tokens(state),
        FINAL_OUTPUT_TOKEN_LIMIT,
    )

    if final_output_tokens <= 0:
        return None

    final_response = client.responses.parse(
        model=OPENAI_MODEL,
        input=[
            {
                "role": "system",
                "content": (
                    "Return a concise structured motor "
                    "insurance investigation result."
                ),
            },
            {
                "role": "user",
                "content": compact_final_prompt,
            },
        ],
        text_format=InvestigationResult,
        max_output_tokens=final_output_tokens,
    )

    _record_usage(
        state,
        final_response,
    )

    investigation = (
        final_response.output_parsed
    )

    if investigation is None:

        raise ValueError(
            "No structured investigation was returned"
        )

    return investigation


def investigate_claim(
    state: ClaimState,
) -> ClaimState:

    if state.extracted_data is None:

        raise ValueError(
            "Claim data must be extracted before investigation"
        )

    policy_status = (
        calculate_policy_validity(
            state.extracted_data
        )
    )

    license_status = (
        calculate_license_validity(
            state.extracted_data
        )
    )

    try:

        investigation = (
            _run_investigation_model(
                state,
                policy_status,
                license_status,
            )
        )

    except Exception as exc:

        raise RuntimeError(
            f"Investigation model call failed: {exc}"
        ) from exc

    if investigation is None:

        state.status = "budget_exceeded"
        state.current_agent = "supervisor"
        state.step_count += 1
        return state

    _apply_deterministic_consistency_checks(
        investigation,
        state,
    )

    _enforce_deterministic_status(
        investigation,
        policy_status,
        license_status,
        state.extracted_data,
    )

    state.investigation = investigation
    state.current_agent = "supervisor"
    state.status = "in_progress"
    state.step_count += 1
    return state


if __name__ == "__main__":

    print(
        "Investigator module loaded successfully."
    )