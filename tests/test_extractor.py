from agents.extractor import extract_claim_data
from state.schema import ClaimState


state = ClaimState(
    claim_id="CLM-001",
    documents=["data/sample_claims/claim_001.pdf"]
)

state = extract_claim_data(state)

assert state.extracted_data is not None

extraction = state.extracted_data

assert extraction.policy.policy_number is not None
assert extraction.vehicle.registration_number is not None
assert extraction.accident.date is not None
assert extraction.driver.name is not None
assert extraction.damage.description is not None
assert state.step_count == 1

print("=" * 50)
print("CLAIM DATA")
print("=" * 50)
print(extraction.model_dump_json(indent=2))
print("=" * 50)
print("BUDGET USAGE")
print("=" * 50)
print(f"Tokens used: {state.token_usage}")
print(f"Estimated cost: ${state.estimated_cost:.6f}")