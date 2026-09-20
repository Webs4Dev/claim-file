from pathlib import Path

from graph.workflow import app
from state.schema import ClaimState
from state.store import (
    load_snapshot,
    save_claim,
)


def create_claim(
    claim_id: str,
    document_path: str,
) -> ClaimState:
    document = Path(document_path)

    if not document.exists():
        raise FileNotFoundError(
            f"Claim document not found: {document_path}"
        )

    state = ClaimState(
        claim_id=claim_id,
        documents=[str(document)],
    )

    result = app.invoke(state)

    final_state = ClaimState.model_validate(result)

    save_claim(final_state)

    return final_state


def resume_claim(
    claim_id: str,
) -> ClaimState:
    state = load_snapshot(claim_id)

    if state is None:
        raise ValueError(
            f"No snapshot found for claim: {claim_id}"
        )

    result = app.invoke(state)

    final_state = ClaimState.model_validate(result)

    save_claim(final_state)

    return final_state


if __name__ == "__main__":
    claim = create_claim(
        claim_id="claim-001",
        document_path="data/sample_claims/claim_001.pdf",
    )

    print(
        claim.model_dump_json(
            indent=2
        )
    )