from typing import Any
from pydantic import BaseModel, Field

from pydantic import BaseModel, Field


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
    authorized_vehicle_types: list[str] = Field(default_factory=list)

class DamageDetails(BaseModel):
    description: str | None = None
    estimated_repair_cost: float | None = None

class PoliceDetails(BaseModel):
    fir_number: str | None = None
    fir_date: str | None = None
    police_station: str | None = None



class ClaimExtraction(BaseModel):
    policy: PolicyDetails = Field(default_factory=PolicyDetails)
    vehicle: VehicleDetails = Field(default_factory=VehicleDetails)
    accident: AccidentDetails = Field(default_factory=AccidentDetails)
    driver: DriverDetails = Field(default_factory=DriverDetails)
    damage: DamageDetails = Field(default_factory=DamageDetails)
    police: PoliceDetails = Field(default_factory=PoliceDetails)
    
    third_party_involved: bool | None = None


class ClaimState(BaseModel):
    claim_id: str
    documents: list[str] = Field(default_factory=list)

    extracted_data: ClaimExtraction | None = None
    investigation: dict[str, Any] = Field(default_factory=dict)
    review: dict[str, Any] = Field(default_factory=dict)

    current_agent: str = "supervisor"
    status: str = "pending"

    step_count: int = 0
    token_usage: int = 0
    estimated_cost: float = 0.0