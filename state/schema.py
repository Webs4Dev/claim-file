from pydantic import BaseModel, Field
from typing import Any

class ClaimState(BaseModel):
    claim_id: str
    documents: list[str] = Field(default_factory=list)

    extracted_data: dict[str, Any] = Field(default_factory=dict)
    investigation: dict[str, Any] = Field(default_factory=dict)
    review: dict[str, Any] = Field(default_factory=dict)

    current_agent: str = "supervisor"
    status: str = "pending"

    step_count: int = 0
    token_usage: int = 0
    estimated_cost: float = 0.0