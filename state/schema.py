from typing import Literal

from pydantic import BaseModel, Field


POLICY_VALIDITY = "Policy Validity"
DRIVER_LICENCE = "Driver and Licence Information"
VEHICLE_INFO = "Vehicle Information"
ACCIDENT_INFO = "Accident Information"
DAMAGE_INFO = "Damage Information"
THIRD_PARTY = "Third-Party Involvement"
POLICE_FIR = "Police/FIR Information"


InvestigationCategory = Literal[
    "Policy Validity",
    "Driver and Licence Information",
    "Vehicle Information",
    "Accident Information",
    "Damage Information",
    "Third-Party Involvement",
    "Police/FIR Information",
]


InvestigationStatus = Literal[
    "VALID",
    "INVALID",
    "CONCERN",
    "INSUFFICIENT_EVIDENCE",
]


ClaimStatus = Literal[
    "pending",
    "in_progress",
    "waiting_for_documents",
    "budget_exceeded",
    "human_approval",
    "complete",
    "terminated",
]


DocumentType = Literal[
    "policy_schedule",
    "policy_document",
    "vehicle_registration",
    "driving_license",
    "damage_survey_report",
    "repair_estimate",
    "repair_invoice",
    "police_report",
    "fir_document",
    "accident_report",
]


DocumentValidity = Literal[
    "VALID",
    "INVALID",
]


class ClaimForm(BaseModel):
    policy_number: str | None = None
    insured_name: str | None = None

    vehicle_registration_number: str | None = None
    vehicle_make: str | None = None
    vehicle_model: str | None = None

    accident_date: str | None = None
    accident_time: str | None = None
    accident_location: str | None = None
    accident_description: str | None = None

    driver_name: str | None = None
    driver_license_number: str | None = None

    damage_description: str | None = None

    third_party_involved: bool | None = None

    additional_information: dict[str, str] = Field(
        default_factory=dict
    )


class PolicyDetails(BaseModel):
    policy_number: str | None = None
    insurance_period: str | None = None


class VehicleDetails(BaseModel):
    registration_number: str | None = None
    make: str | None = None
    model: str | None = None


class AccidentDetails(BaseModel):
    date: str | None = None
    time: str | None = None
    location: str | None = None
    description: str | None = None


class DriverDetails(BaseModel):
    name: str | None = None
    license_number: str | None = None
    license_expiry_date: str | None = None
    authorized_vehicle_types: list[str] = Field(
        default_factory=list
    )


class DamageDetails(BaseModel):
    description: str | None = None
    estimated_repair_cost: float | None = None


class PoliceDetails(BaseModel):
    fir_number: str | None = None
    fir_date: str | None = None
    police_station: str | None = None


class ClaimExtraction(BaseModel):
    policy: PolicyDetails = Field(
        default_factory=PolicyDetails
    )
    vehicle: VehicleDetails = Field(
        default_factory=VehicleDetails
    )
    accident: AccidentDetails = Field(
        default_factory=AccidentDetails
    )
    driver: DriverDetails = Field(
        default_factory=DriverDetails
    )
    damage: DamageDetails = Field(
        default_factory=DamageDetails
    )
    police: PoliceDetails = Field(
        default_factory=PoliceDetails
    )
    third_party_involved: bool | None = None


class ClaimDocument(BaseModel):
    document_type: DocumentType
    file_path: str | None = None
    uploaded: bool = False
    validity: DocumentValidity | None = None
    required: bool = False
    validation_reason: str | None = None


class DocumentValidationResult(BaseModel):
    all_required_documents_present: bool

    documents: list[ClaimDocument] = Field(
        default_factory=list
    )

    missing_documents: list[DocumentType] = Field(
        default_factory=list
    )

    invalid_documents: list[DocumentType] = Field(
        default_factory=list
    )

class InvestigationFinding(BaseModel):
    category: InvestigationCategory
    status: InvestigationStatus
    finding: str
    evidence: str


class InvestigationResult(BaseModel):
    overall_status: InvestigationStatus

    findings: list[InvestigationFinding] = Field(
        default_factory=list
    )

    missing_information: list[str] = Field(
        default_factory=list
    )

    contradictions: list[str] = Field(
        default_factory=list
    )


class RequiredDocument(BaseModel):
    document_type: DocumentType
    description: str
    reason: str


class ReviewResult(BaseModel):
    status: Literal[
        "APPROVED",
        "NEEDS_INVESTIGATION",
        "REJECTED",
    ]

    summary: str

    concerns: list[str] = Field(
        default_factory=list
    )

    required_actions: list[str] = Field(
        default_factory=list
    )

    required_documents: list[RequiredDocument] = Field(
        default_factory=list
    )


class ClaimState(BaseModel):
    claim_id: str
    claim_form: ClaimForm = Field(
        default_factory=ClaimForm
    )
    documents: list[str] = Field(
        default_factory=list
    )
    claim_documents: list[ClaimDocument] = Field(
        default_factory=list
    )
    pending_documents: list[RequiredDocument] = Field(
        default_factory=list
    )
    extracted_data: ClaimExtraction | None = None
    document_validation: DocumentValidationResult | None = None
    investigation: InvestigationResult | None = None
    review: ReviewResult | None = None
    current_agent: str = "supervisor"
    status: ClaimStatus = "pending"
    step_count: int = 0
    token_usage: int = 0
    estimated_cost: float = 0.0
    workflow_trace: list[dict] = Field(default_factory=list)