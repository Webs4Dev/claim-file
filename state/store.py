import redis

from state.schema import ClaimState

redis_client = redis.Redis(
    host="localhost",
    port=6379,
    decode_responses=True
)


def save_claim(state: ClaimState) -> None:
    redis_client.set(
        f"claim:{state.claim_id}",
        state.model_dump_json()
    )

def load_claim(claim_id: str) -> ClaimState | None:
    data = redis_client.get(f"claim:{claim_id}")

    if data is None:
        return None

    return ClaimState.model_validate_json(data)

def save_snapshot(state: ClaimState) -> None:
    redis_client.set(
        f"snapshot:{state.claim_id}",
        state.model_dump_json()
    )

def load_snapshot(claim_id: str) -> ClaimState | None:
    data = redis_client.get(f"snapshot:{claim_id}")

    if data is None:
        return None

    return ClaimState.model_validate_json(data)