from state.schema import ClaimState

def extract_claim_data(state: ClaimState) -> ClaimState:
    state.extracted_data = {
        "claim_type": "vehicle_damage",
        "estimated_damage": 85000,
        "incident_date": "2026-09-01",
        "vehicle": "Honda City"
    }

    state.current_agent = "supervisor"
    state.step_count += 1

    return state