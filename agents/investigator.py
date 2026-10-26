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
    ACCIDENT_INFO,
    DRIVER_LICENCE,
    POLICY_VALIDITY,
    ClaimExtraction,
    ClaimState,
    InvestigationFinding,
    InvestigationResult,
    InvestigationStatus,
)

from tools.policy import search_policy


client = OpenAI(
    api_key=OPENAI_API_KEY,
)


MAX_POLICY_SEARCHES = 3

FINAL_OUTPUT_TOKEN_LIMIT = 5000


def parse_date(
    value: str | None,
) -> datetime | None:

    if not value:
        return None

    value = value.strip()

    date_match = re.search(
        r"\b\d{2}[/.]\d{2}[/.]\d{4}\b",
        value,
    )

    if date_match:
        value = date_match.group()

    for date_format in (
        "%d/%m/%Y",
        "%d.%m.%Y",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(
                value,
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


def normalize_vehicle_model(
    value: str | None,
) -> str:

    if not value:
        return ""

    value = value.strip().lower()

    value = re.sub(
        r"\\([^)]*\\)",
        "",
        value,
    )

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

            return parsed.strftime(
                "%H:%M"
            )

        except ValueError:
            continue

    time_match = re.search(
        r"\b\d{1,2}:\d{2}(?::\d{2})?\b",
        value,
    )

    if time_match:
        extracted_time = time_match.group()

        for time_format in (
            "%H:%M",
            "%H:%M:%S",
        ):
            try:
                parsed = datetime.strptime(
                    extracted_time,
                    time_format,
                )

                return parsed.strftime(
                    "%H:%M"
                )

            except ValueError:
                continue

    return normalize_text(value)


def calculate_policy_validity(
    extraction: ClaimExtraction,
) -> InvestigationStatus:

    insurance_period = (
        extraction.policy.insurance_period
    )

    accident_date = (
        extraction.accident.date
    )

    if not insurance_period:
        return "INSUFFICIENT_EVIDENCE"

    if not accident_date:
        return "INSUFFICIENT_EVIDENCE"

    period_parts = re.split(
        r"\s+to\s+",
        insurance_period,
        maxsplit=1,
        flags=re.IGNORECASE,
    )

    if len(period_parts) != 2:
        return "INSUFFICIENT_EVIDENCE"

    start_date = parse_date(
        period_parts[0]
    )

    end_date = parse_date(
        period_parts[1]
    )

    accident = parse_date(
        accident_date
    )

    if (
        not start_date
        or not end_date
        or not accident
    ):
        return "INSUFFICIENT_EVIDENCE"

    if start_date <= accident <= end_date:
        return "VALID"

    return "INVALID"


def calculate_license_validity(
    extraction: ClaimExtraction,
) -> InvestigationStatus:

    expiry_date = (
        extraction.driver.license_expiry_date
    )

    accident_date = (
        extraction.accident.date
    )

    if not expiry_date:
        return "INSUFFICIENT_EVIDENCE"

    if not accident_date:
        return "INSUFFICIENT_EVIDENCE"

    parsed_expiry = parse_date(
        expiry_date
    )

    parsed_accident = parse_date(
        accident_date
    )

    if (
        not parsed_expiry
        or not parsed_accident
    ):
        return "INSUFFICIENT_EVIDENCE"

    if parsed_accident <= parsed_expiry:
        return "VALID"

    return "INVALID"


def has_valid_policy_schedule(
    state: ClaimState,
) -> bool:

    for document in state.claim_documents:
        if (
            document.document_type == "policy_schedule"
            and document.uploaded
            and document.validity == "VALID"
        ):
            return True

    return False


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


def build_pending_investigation_actions(
    state: ClaimState,
) -> str:

    if not state.pending_investigation_actions:
        return (
            "No specific investigation actions were "
            "requested by the previous review."
        )

    actions = "\n".join(
        f"{index}. {action}"
        for index, action in enumerate(
            state.pending_investigation_actions,
            start=1,
        )
    )

    return f"""
The previous Reviewer identified the following unresolved
investigation actions:

{actions}

These actions are the priority for this investigation cycle.

You MUST address these actions using the available evidence.

If an action requires policy verification, use the
search_policy tool with a focused query.

Do not ignore these actions and perform only a generic
investigation.

Do not treat the requested actions themselves as evidence.
They are investigation instructions only.
""".strip()


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

    claim_form = (
        state.claim_form.model_dump_json(
            indent=2
        )
    )

    document_validation = (
        build_document_validation_context(
            state
        )
    )

    pending_actions = (
        build_pending_investigation_actions(
            state
        )
    )

    previous_review = ""

    if state.review is not None:
        previous_review = f"""
PREVIOUS REVIEW

{state.review.model_dump_json(indent=2)}

Use the previous review only to identify issues
that require re-examination.

Do not treat previous review conclusions as factual
evidence.
"""

    return f"""
You are the Investigator agent for a motor insurance claim.

Your task is to investigate the claim using only the
available evidence.

Use:

1. Extracted claim data.
2. Online claim form data.
3. Document validation results.
4. Policy evidence retrieved through the policy search tool.

Do not perform document extraction.

Do not verify document authenticity.

Do not invent facts.

Do not infer facts that are not explicitly supported.

Do not make a final payout decision.

Do not make the final approval decision.

The uploaded documents are considered authentic by the
system. Document validation determines whether a submitted
document is usable as evidence.

VALID documents may be used as evidence.

INVALID documents must not be treated as reliable evidence.

Do not request another document merely because an existing
document is VALID.

CURRENT DETERMINISTIC RESULTS

Policy Validity: {policy_status}

Driver and Licence Information: {license_status}

These two statuses are calculated by the system and must
not be overridden.

The licence status only checks whether the licence was
unexpired on the accident date.

Do not infer vehicle-class compatibility unless the
available evidence explicitly establishes it.

PRIORITY INVESTIGATION ACTIONS

{pending_actions}

If priority investigation actions are present, address them
using available evidence before performing unrelated
investigation.

A requested reconciliation or verification action is not
itself evidence of a contradiction.

Only report a contradiction when the underlying evidence
actually establishes that two values conflict.

POLICY EVIDENCE

A policy schedule is documentary evidence establishing
policy identity, policy period, and policy status.

A policy number stated only on the online claim form is a
claimant-provided assertion. It must not by itself be treated
as documentary evidence establishing policy validity.

If there is no valid policy schedule, Policy Validity must
remain INSUFFICIENT_EVIDENCE even if the claim form contains
a policy number and extracted data contains an insurance
period.

Do not treat the policy knowledge base as evidence that the
specific claimant's policy was active. The knowledge base is
used for policy wording only.

POLICY SEARCH

The policy knowledge base contains the configured motor
insurance policy for product "private_car".

Use the search_policy tool only when a specific policy
wording question requires verification.

You may perform at most two policy searches.

Prioritize the most important unresolved policy question.

Ask one focused policy question per search.

Do not use general insurance knowledge when the answer
depends on the policy wording.

For accidental damage to the insured vehicle, policy
searches must focus on Section I / Own Damage.

Use the actual accident circumstances to make the search
specific.

For example, if the accident evidence states that the
vehicle collided with a concrete median divider, the
policy search should explicitly mention collision with
a fixed object or similar circumstances.

For the first search, prioritize:

- Section I / Own Damage
- accidental loss or damage
- the actual accident circumstances
- whether the specific type of accident falls within
  Section I coverage

If a second search is necessary, prioritize:

- Section I exclusions
- applicable conditions
- reasonable-care requirements
- applicable deductible
- conditions affecting the specific accident

Only investigate accident reporting or FIR requirements if
the available claim evidence indicates that police/FIR status
is material to this claim.

Do not search for an FIR requirement merely because the claim
states that no FIR was filed.

Do not use unrelated add-on sections as evidence for
Section I Own Damage.

For example, personal belongings, tyre add-ons, No Claim
Bonus protection, electric vehicle battery coverage, or
other optional covers must not be treated as evidence
that Section I covers the claimed vehicle damage unless
the policy wording explicitly connects them.

Do not conclude that accidental damage is covered merely
because the policy contains general accidental-damage
language.

The policy evidence must be relevant to the actual claim
circumstances.

If policy evidence does not establish coverage, report
INSUFFICIENT_EVIDENCE or CONCERN rather than assuming
coverage.

DETERMINISTIC CONSISTENCY CHECKS

Compare these fields between the online claim form and
extracted data:

- policy number
- vehicle registration number
- accident date
- accident time
- driver licence number
- driver name
- vehicle make
- vehicle model

If both values exist and genuinely differ after
normalization, report a contradiction.

A policy number may appear in extracted data together
with a source label, document label, or multiple explicit
representations of the same policy identifier.

For example, if the claim form contains:

3510203118

and extracted data contains:

3510203118 (claim form); TEST-POL-3510203118
(supporting documents)

do not treat the combined representation itself as a
contradiction.

If one representation contains the claim-form policy
number and the additional text identifies its source,
the values are not automatically contradictory.

Only report a policy-number contradiction when the
available evidence establishes that the actual policy
identifiers refer to different policies or cannot
reasonably be reconciled from the available evidence.

If the claim form has a value but extracted data does not,
report missing information.

A missing value is not a contradiction.

Do not invent contradictions.

INVESTIGATION CATEGORIES

Produce exactly one finding for each category:

1. Policy Validity
2. Driver and Licence Information
3. Vehicle Information
4. Accident Information
5. Damage Information
6. Third-Party Involvement
7. Police/FIR Information

Each finding must contain:

- category
- status
- finding
- evidence

Allowed statuses:

- VALID
- INVALID
- CONCERN
- INSUFFICIENT_EVIDENCE

Keep findings concise.

POLICY VALIDITY

Use the deterministic Policy Validity status.

Consider:

- policy number
- insurance period
- accident date
- policy schedule evidence
- policy wording when relevant

A policy number appearing on the online claim form does not
establish policy validity by itself.

If no valid policy schedule is available, report
INSUFFICIENT_EVIDENCE.

Do not mark policy validity invalid solely because
different documents use a source-specific identifier
representation unless the evidence establishes an actual
policy identity conflict.

DRIVER AND LICENCE INFORMATION

Use the deterministic Driver and Licence Information
status.

Consider:

- driver identity
- licence number
- licence expiry date
- available driver information

Do not claim vehicle-class compatibility unless explicitly
supported by evidence.

VEHICLE INFORMATION

Consider:

- registration number
- make
- model
- vehicle identity
- consistency between available sources

If the available sources agree, treat the information
as consistent.

ACCIDENT INFORMATION

Consider:

- accident date
- accident time
- accident location
- accident description

Use deterministic checks for date and time.

If the claim form or supporting documents explicitly provide
the accident date, time, location, and circumstances and the
available evidence is internally consistent, this category
can be VALID.

Do not require independent third-party corroboration merely
because it is not present.

Independent corroboration is additional evidence, not an
automatic requirement for establishing the reported accident
information.

Use CONCERN only when the available evidence contains an actual
contradiction or material inconsistency.

Use INSUFFICIENT_EVIDENCE only when material accident information
is actually missing.

DAMAGE INFORMATION

Consider:

- claimed damage
- survey findings
- repair estimate
- repair amount
- policy evidence relevant to the damage

Distinguish between:

- Section I / Own Damage coverage
- Section I exclusions
- policy conditions
- deductibles
- unrelated optional/add-on covers

Do not use unrelated add-on coverage as evidence for
Section I Own Damage.

Do not determine whether a repair amount is reasonable
unless the available evidence specifically supports that
determination.

THIRD-PARTY INVOLVEMENT

Use only available evidence.

Compare the claim form and supporting documents.

If the available evidence explicitly states that no third party
was involved and there is no contradictory evidence, this
category can be VALID.

A collision with a fixed object such as a divider, wall, pole,
barrier, or similar object can support no-third-party
involvement when the submitted evidence explicitly supports it.

Do not require independent corroboration merely because it is
not present.

Do not infer third-party involvement without evidence.

Use CONCERN only when there is contradictory evidence.

Use INSUFFICIENT_EVIDENCE only when the available evidence does
not allow a reasonable determination.

POLICE/FIR INFORMATION

Use only available evidence.

The absence of an FIR is not, by itself, an unresolved
claim issue.

If the available evidence explicitly states that no FIR was
filed and there is no evidence that police reporting is
material to claim eligibility, treat this category as VALID.

Do not invent a legal or policy requirement for an FIR.

Use INSUFFICIENT_EVIDENCE or CONCERN only when the available
evidence explicitly establishes that police reporting, an FIR,
or the absence of one is material to the claim and the issue
cannot be resolved from the available evidence.

OVERALL STATUS

Use:

INVALID when a validity problem is established.

CONCERN when further investigation is required but
invalidity is not established.

INSUFFICIENT_EVIDENCE when an important determination
cannot be made from the available evidence.

VALID only when the evidence is sufficient across the
investigated areas and no validity problem is identified.

MISSING INFORMATION

Include only materially relevant missing information.

A missing optional field is not automatically material.

If no valid policy schedule is available, include the
absence of the policy schedule as material missing
information because policy validity cannot be established
from the claim form policy number alone.

The absence of an FIR is not material missing information
unless the available evidence establishes that police/FIR
reporting affects this claim.

CONTRADICTIONS

Include only actual contradictions between available
evidence.

Return only the structured InvestigationResult.

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


def create_deterministic_finding(
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
                "from the available evidence."
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


def deduplicate_findings(
    findings: list[InvestigationFinding],
) -> list[InvestigationFinding]:

    unique_findings = {}

    for finding in findings:

        if finding.category not in unique_findings:
            unique_findings[finding.category] = finding

    return list(
        unique_findings.values()
    )


def add_missing_information(
    investigation: InvestigationResult,
    message: str,
) -> None:

    if message not in investigation.missing_information:
        investigation.missing_information.append(
            message
        )


def add_contradiction(
    investigation: InvestigationResult,
    message: str,
) -> None:

    if message not in investigation.contradictions:
        investigation.contradictions.append(
            message
        )


def values_are_consistent(
    claim_value: str,
    extracted_value: str,
    field_name: str,
    normalizer,
) -> bool:

    claim_normalized = normalizer(
        claim_value
    )

    extracted_normalized = normalizer(
        extracted_value
    )

    if not claim_normalized or not extracted_normalized:
        return False

    if claim_normalized == extracted_normalized:
        return True

    if field_name == "Policy number":
        return claim_normalized in extracted_normalized

    if field_name == "Vehicle model":

        claim_model = normalize_vehicle_model(
            claim_value
        )

        extracted_model = normalize_vehicle_model(
            extracted_value
        )

        return (
            bool(claim_model)
            and bool(extracted_model)
            and claim_model == extracted_model
        )

    return False


def check_value_consistency(
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

        if not values_are_consistent(
            claim_value,
            extracted_value,
            field_name,
            normalizer,
        ):

            add_contradiction(
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

        add_missing_information(
            investigation,
            (
                f"{field_name} is provided in the online claim "
                f"form but is not available in the extracted "
                f"document data."
            ),
        )


def check_date_consistency(
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

                add_contradiction(
                    investigation,
                    (
                        f"{field_name} differs between the online "
                        f"claim form and extracted document data: "
                        f"claim form='{claim_value}', "
                        f"extracted='{extracted_value}'."
                    ),
                )

            return

    check_value_consistency(
        investigation,
        claim_value,
        extracted_value,
        field_name,
        normalize_text,
    )


def check_time_consistency(
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

            add_contradiction(
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

        add_missing_information(
            investigation,
            (
                f"{field_name} is provided in the online claim "
                f"form but is not available in the extracted "
                f"document data."
            ),
        )


def apply_deterministic_consistency_checks(
    investigation: InvestigationResult,
    state: ClaimState,
) -> None:

    extraction = state.extracted_data

    if extraction is None:
        return

    claim_form = state.claim_form

    check_value_consistency(
        investigation,
        claim_form.policy_number,
        extraction.policy.policy_number,
        "Policy number",
        normalize_policy_number,
    )

    check_value_consistency(
        investigation,
        claim_form.vehicle_registration_number,
        extraction.vehicle.registration_number,
        "Vehicle registration number",
        normalize_registration_number,
    )

    check_date_consistency(
        investigation,
        claim_form.accident_date,
        extraction.accident.date,
        "Accident date",
    )

    check_time_consistency(
        investigation,
        claim_form.accident_time,
        extraction.accident.time,
        "Accident time",
    )

    check_value_consistency(
        investigation,
        claim_form.driver_license_number,
        extraction.driver.license_number,
        "Driver licence number",
        normalize_license_number,
    )

    check_value_consistency(
        investigation,
        claim_form.driver_name,
        extraction.driver.name,
        "Driver name",
        normalize_name,
    )

    check_value_consistency(
        investigation,
        claim_form.vehicle_make,
        extraction.vehicle.make,
        "Vehicle make",
        normalize_vehicle_value,
    )

    check_value_consistency(
        investigation,
        claim_form.vehicle_model,
        extraction.vehicle.model,
        "Vehicle model",
        normalize_vehicle_value,
    )

    check_document_identifiers(
        investigation,
        state,
    )


def check_document_identifiers(
    investigation: InvestigationResult,
    state: ClaimState,
) -> None:
    """Compare each document's own identifiers with the claim form.

    The merged extraction keeps one value per field, so a document that
    disagrees with the rest is only visible here.
    """
    extraction = state.extracted_data
    claim_form = state.claim_form

    checks = [
        (
            "Policy number",
            claim_form.policy_number,
            "policy_number",
            normalize_policy_number,
        ),
        (
            "Vehicle registration number",
            claim_form.vehicle_registration_number,
            "vehicle_registration_number",
            normalize_registration_number,
        ),
        (
            "Driver licence number",
            claim_form.driver_license_number,
            "driver_license_number",
            normalize_license_number,
        ),
    ]

    for identifiers in extraction.document_identifiers:
        for field_name, claim_value, attribute, normalizer in checks:
            document_value = getattr(identifiers, attribute)

            if not normalizer(claim_value) or not normalizer(document_value):
                continue

            if values_are_consistent(
                claim_value,
                document_value,
                field_name,
                normalizer,
            ):
                continue

            add_contradiction(
                investigation,
                (
                    f"{field_name} differs between the online claim "
                    f"form and the {identifiers.document_type} "
                    f"document: claim form='{claim_value}', "
                    f"document='{document_value}'."
                ),
            )


def apply_intoxication_check(
    investigation: InvestigationResult,
    extraction: ClaimExtraction,
) -> None:
    """A reported intoxicated driver makes the claim INVALID.

    The policy excludes loss or damage while the driver is under the
    influence of intoxicating liquor or drugs (Section I, 2.c). The
    model alternated between CONCERN and INVALID for the same evidence,
    so the outcome is fixed here.
    """
    if extraction.driver.intoxication_reported is not True:
        return

    condition = (
        extraction.driver.condition_at_accident
        or "intoxication reported in the claim documents"
    )

    exclusion_text = (
        "The documents report that the driver was under the "
        "influence at the time of the accident, which engages the "
        "policy exclusion for intoxicating liquor or drugs."
    )

    accident_finding = next(
        (
            finding
            for finding in investigation.findings
            if finding.category == ACCIDENT_INFO
        ),
        None,
    )

    if accident_finding is None:
        investigation.findings.append(
            InvestigationFinding(
                category=ACCIDENT_INFO,
                status="INVALID",
                finding=exclusion_text,
                evidence=f"Driver condition: {condition}",
            )
        )
    elif accident_finding.status != "INVALID":
        accident_finding.status = "INVALID"
        accident_finding.finding = (
            f"{accident_finding.finding} {exclusion_text}"
        )
        accident_finding.evidence = (
            f"{accident_finding.evidence} Driver condition: {condition}"
        )

    investigation.overall_status = "INVALID"


def enforce_deterministic_status(
    investigation: InvestigationResult,
    policy_status: InvestigationStatus,
    license_status: InvestigationStatus,
    extraction: ClaimExtraction,
) -> None:

    investigation.findings = (
        deduplicate_findings(
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
                create_deterministic_finding(
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

    elif (
        policy_status == "INSUFFICIENT_EVIDENCE"
        or license_status == "INSUFFICIENT_EVIDENCE"
    ):

        if investigation.overall_status == "VALID":
            investigation.overall_status = (
                "INSUFFICIENT_EVIDENCE"
            )

    elif investigation.contradictions:

        if investigation.overall_status == "VALID":
            investigation.overall_status = "CONCERN"

    reconcile_overall_status(investigation)


# Worst first. Missing evidence blocks a decision, so it outranks CONCERN.
STATUS_SEVERITY = {
    "VALID": 0,
    "CONCERN": 1,
    "INSUFFICIENT_EVIDENCE": 2,
    "INVALID": 3,
}


def reconcile_overall_status(
    investigation: InvestigationResult,
) -> None:
    """Keep overall_status consistent with the individual findings.

    The reviewer rejects investigations whose overall status contradicts
    their findings (e.g. INVALID overall with no INVALID finding).
    """
    if not investigation.findings:
        return

    worst = max(
        (finding.status for finding in investigation.findings),
        key=STATUS_SEVERITY.__getitem__,
    )

    if worst == "INVALID":
        investigation.overall_status = "INVALID"

    elif investigation.overall_status == "INVALID":
        investigation.overall_status = (
            "CONCERN" if worst == "VALID" else worst
        )

    elif (
        STATUS_SEVERITY[worst]
        > STATUS_SEVERITY[investigation.overall_status]
    ):
        investigation.overall_status = worst


def record_usage(
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


def execute_policy_tool(
    arguments: str,
) -> str:

    try:

        parsed_arguments = json.loads(
            arguments
        )

    except json.JSONDecodeError as exc:

        raise ValueError(
            "Policy tool returned invalid arguments."
        ) from exc

    query = parsed_arguments.get(
        "query"
    )

    product = parsed_arguments.get(
        "product"
    )

    if (
        not isinstance(query, str)
        or not query.strip()
    ):

        raise ValueError(
            "Policy tool query is required."
        )

    if (
        not isinstance(product, str)
        or not product.strip()
    ):

        raise ValueError(
            "Policy tool product is required."
        )

    if product != "private_car":

        raise ValueError(
            "The current investigation scope supports "
            "private_car only."
        )

    return search_policy(
        query=query,
        product=product,
    )


def build_policy_search_queries(
    state: ClaimState,
) -> list[str]:
    """Create a complete, non-overlapping evidence plan.

    Coverage, exclusions, and deductibles are separate policy questions.
    Keeping them separate prevents a deductible term from pulling the whole
    retrieval operation away from the Section I evidence needed to assess an
    own-damage collision.
    """
    extraction = state.extracted_data

    if extraction is None:
        return []

    circumstances = (
        extraction.accident.description
        or state.claim_form.accident_description
        or "the reported accident"
    ).strip()

    damage = (
        extraction.damage.description
        or state.claim_form.damage_description
        or "damage to the insured vehicle"
    ).strip()

    # Exclusions often turn on the driver's state (alcohol, drugs), which
    # the accident description alone may not mention.
    exclusion_circumstances = circumstances

    if extraction.driver.condition_at_accident:
        exclusion_circumstances = (
            f"{circumstances} Driver condition: "
            f"{extraction.driver.condition_at_accident.strip()}"
        )

    return [
        (
            "Section I Own Damage coverage: retrieve the operative wording "
            "for accidental loss of or damage to the insured vehicle caused "
            f"by these circumstances: {circumstances}. "
            f"The reported damage is: {damage}."
        ),
        (
            "Section I Own Damage exclusions, general exceptions, and "
            "conditions: retrieve provisions that could affect a claim for "
            f"this accident: {exclusion_circumstances}. Include any reasonable-care "
            "or claim-condition provisions that apply."
        ),
        (
            "Section I Own Damage deductible or excess and endorsements: "
            "retrieve the applicable deductible/excess wording and any "
            "endorsement provisions that can affect an accidental collision "
            f"claim for: {circumstances}."
        ),
    ]


def collect_policy_searches(
    state: ClaimState,
) -> list[dict]:
    """Run the required policy searches without delegating query choice.

    The prior implementation relied on a model to select up to two tool
    calls. It routinely combined exclusions, conditions, deductibles, and
    endorsements into one query, so the retrieval ranker selected evidence
    for only one of those subjects.
    """
    policy_evidence = []

    for query in build_policy_search_queries(state)[
        :MAX_POLICY_SEARCHES
    ]:
        arguments = {
            "query": query,
            "product": "private_car",
        }

        try:
            result = search_policy(**arguments)
        except Exception as exc:
            result = (
                "Policy search was unavailable for this question: "
                f"{exc}"
            )

        policy_evidence.append(
            {
                "arguments": json.dumps(arguments),
                "result": result,
            }
        )

    return policy_evidence


def build_policy_evidence_text(
    policy_evidence: list[dict],
) -> str:

    if not policy_evidence:
        return (
            "No policy search was performed."
        )

    sections = [
        "POLICY SEARCH EVIDENCE"
    ]

    for index, evidence in enumerate(
        policy_evidence,
        start=1,
    ):

        sections.append(
            f"""
Policy search {index}

Query:

{evidence["arguments"]}

Evidence:

{evidence["result"]}
""".strip()
        )

    return "\n\n".join(
        sections
    )


def run_investigation_model(
    state: ClaimState,
    policy_status: InvestigationStatus,
    license_status: InvestigationStatus,
) -> InvestigationResult | None:

    if not can_make_model_call(state):
        return None

    allowed_output_tokens = max_output_tokens(
        state
    )

    if allowed_output_tokens <= 0:
        return None

    # Search before the structured investigation call. The policy evidence
    # plan is deterministic, complete, and uses the actual claim facts.
    policy_evidence = collect_policy_searches(state)

    if budget_exceeded(state):
        return None

    extraction = state.extracted_data

    if extraction is None:
        return None

    evidence_text = build_policy_evidence_text(
        policy_evidence
    )

    pending_actions = (
        build_pending_investigation_actions(
            state
        )
    )

    compact_final_prompt = f"""
Produce the final structured investigation result.

Return exactly 7 findings:

1. Policy Validity
2. Driver and Licence Information
3. Vehicle Information
4. Accident Information
5. Damage Information
6. Third-Party Involvement
7. Police/FIR Information

Allowed finding statuses:

- VALID
- INVALID
- CONCERN
- INSUFFICIENT_EVIDENCE

Use these deterministic statuses exactly:

Policy Validity: {policy_status}

Driver and Licence Information: {license_status}

Do not override these statuses.

If Policy Validity is INSUFFICIENT_EVIDENCE because no valid
policy schedule is available, the final Policy Validity finding
must clearly state that the claim-form policy number alone does
not establish policy validity.

When a valid policy schedule is available, do not list the policy
schedule, its policy identity details, or its policy period as
missing information. The schedule establishes policy status.

The policy knowledge base, rather than a replacement schedule from
the claimant, is the source for policy wording such as Section I
coverage, exclusions, conditions, deductibles, and endorsements.
If that wording cannot be retrieved, describe the missing policy
wording precisely; do not call it missing policy-schedule details.

Customer-specific amounts are NOT in the policy wording. The wording
refers to them as "stated in the Schedule". Their values are in
EXTRACTED DATA under policy: insured_declared_value,
compulsory_deductible, voluntary_deductible, and add_on_covers.
When those fields are present, state the applicable deductible and
IDV in the Damage Information evidence, and do not list them as
missing information. Only list a deductible or IDV as missing when
the extracted policy field is null.

If EXTRACTED DATA driver.intoxication_reported is true, or
driver.condition_at_accident describes alcohol or drug influence,
report it in Accident Information and check it against the
exclusions in the policy evidence (for example loss or damage while
the driver is under the influence of intoxicating liquor or drugs).
Do not mark Accident Information or the overall result VALID in
that case.

EXTRACTED DATA document_identifiers lists the identifiers printed in
each document. If one document shows a different policy number,
registration number, or licence number from the claim form, report
it as a contradiction.

The previous Reviewer may have supplied investigation
actions. Those actions are instructions for what to
investigate, not evidence.

PRIORITY INVESTIGATION ACTIONS:

{pending_actions}

The final result must reflect the evidence actually found
while addressing these actions.

For policy identity:

Do not treat a source label, document label, or combined
representation of a policy number as an actual contradiction.

If the claim-form policy number appears inside the extracted
policy-number representation, do not create a contradiction
merely because additional source-specific text is present.

Only report a contradiction when the evidence establishes
that the actual policy identifiers conflict or cannot be
reasonably reconciled.

When evaluating Damage Information, distinguish between:

- Section I / Own Damage evidence
- Section I exclusions and conditions
- deductibles
- unrelated add-on or optional covers

Do not use unrelated add-on coverage as evidence for
Section I Own Damage.

Do not conclude that accidental collision damage is covered
unless the retrieved policy evidence actually supports that
conclusion.

If the policy evidence does not establish whether the
specific accident circumstances are covered, state that
the coverage determination remains unsupported by the
available policy evidence.

For Police/FIR Information:

- Do not create an investigation issue merely because no FIR
  was filed.

- If the evidence states that no FIR was filed and does not
  establish that an FIR or police report is material to claim
  eligibility, mark Police/FIR Information as VALID.

- Only mark this category as INSUFFICIENT_EVIDENCE or CONCERN
  when available evidence establishes a material police/FIR
  requirement or effect that remains unresolved.

Keep every finding concise.

Finding:

one or two short sentences.

Evidence:

one or two short sentences.

Do not invent facts.

Do not infer fraud.

Do not invent policy requirements.

Do not make a payout or approval decision.

For missing_information, include only material missing
information.

For contradictions, include only actual contradictions.

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

    record_usage(
        state,
        final_response,
    )

    investigation = (
        final_response.output_parsed
    )

    if investigation is None:
        raise ValueError(
            "No structured investigation was returned."
        )

    return investigation


def investigate_claim(
    state: ClaimState,
) -> ClaimState:

    if state.extracted_data is None:
        raise ValueError(
            "Claim data must be extracted before investigation."
        )

    policy_status = calculate_policy_validity(
        state.extracted_data
    )

    if not has_valid_policy_schedule(state):
        policy_status = "INSUFFICIENT_EVIDENCE"

    license_status = calculate_license_validity(
        state.extracted_data
    )

    try:

        investigation = run_investigation_model(
            state,
            policy_status,
            license_status,
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

    if not has_valid_policy_schedule(state):

        add_missing_information(
            investigation,
            (
                "A valid policy schedule is not available. "
                "The policy number stated on the online claim "
                "form alone does not establish the policy period "
                "or policy status."
            ),
        )

        findings_by_category = {
            finding.category: finding
            for finding in investigation.findings
        }

        policy_finding = findings_by_category.get(
            POLICY_VALIDITY
        )

        if policy_finding is not None:

            policy_finding.status = (
                "INSUFFICIENT_EVIDENCE"
            )

            policy_finding.finding = (
                "Policy validity cannot be established because "
                "a valid policy schedule is not available."
            )

            policy_finding.evidence = (
                "The online claim form provides a policy number, "
                "but no valid policy schedule is available to "
                "establish the policy period."
            )

        if investigation.overall_status == "VALID":
            investigation.overall_status = (
                "INSUFFICIENT_EVIDENCE"
            )

    apply_deterministic_consistency_checks(
        investigation,
        state,
    )

    apply_intoxication_check(
        investigation,
        state.extracted_data,
    )

    enforce_deterministic_status(
        investigation,
        policy_status,
        license_status,
        state.extracted_data,
    )

    state.investigation = investigation

    state.pending_investigation_actions = []

    state.current_agent = "supervisor"

    state.status = "in_progress"

    state.step_count += 1

    return state


if __name__ == "__main__":
    print(
        "Investigator module loaded successfully."
    )
