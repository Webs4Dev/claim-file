import redis

from state.schema import ClaimState


redis_client = redis.Redis(
    host="localhost",
    port=6379,
    decode_responses=True,
)


def save_claim(
    state: ClaimState,
) -> None:
    redis_client.set(
        f"claim:{state.claim_id}",
        state.model_dump_json(),
    )


def load_claim(
    claim_id: str,
) -> ClaimState | None:
    data = redis_client.get(
        f"claim:{claim_id}"
    )

    if data is None:
        return None

    return ClaimState.model_validate_json(data)


def save_snapshot(
    state: ClaimState,
) -> None:
    snapshot = state.model_dump_json()

    redis_client.set(
        f"snapshot:{state.claim_id}",
        snapshot,
    )

    redis_client.rpush(
        f"snapshots:{state.claim_id}",
        snapshot,
    )


def load_snapshot(
    claim_id: str,
) -> ClaimState | None:
    data = redis_client.get(
        f"snapshot:{claim_id}"
    )

    if data is None:
        return None

    return ClaimState.model_validate_json(data)


def load_snapshots(
    claim_id: str,
) -> list[ClaimState]:
    snapshots = redis_client.lrange(
        f"snapshots:{claim_id}",
        0,
        -1,
    )

    return [
        ClaimState.model_validate_json(snapshot)
        for snapshot in snapshots
    ]