from collections import Counter
from typing import NamedTuple

import redis

from state.schema import ClaimState


redis_client = redis.Redis(
    host="localhost",
    port=6379,
    decode_responses=True,
)

# Indexes kept next to each claim so a list request reads one page of
# claims, not every claim in Redis. Scores are created_at timestamps.
CLAIMS_BY_CREATED = "claims:by_created"
CLAIM_STATUSES = "claims:status"
CLAIM_SEARCH_TEXT = "claims:search"


def owner_index_key(owner_id: str) -> str:
    return f"claims:by_owner:{owner_id}"


class ClaimPage(NamedTuple):
    claims: list[ClaimState]
    total: int
    status_counts: dict[str, int]


def search_text(state: ClaimState) -> str:
    form = state.claim_form
    return " ".join(
        str(value or "")
        for value in (
            state.claim_id,
            form.insured_name,
            form.vehicle_registration_number,
            form.policy_number,
        )
    ).lower()


def index_claim(pipeline, state: ClaimState) -> None:
    score = state.created_at.timestamp()
    pipeline.zadd(CLAIMS_BY_CREATED, {state.claim_id: score})
    if state.owner_id:
        pipeline.zadd(owner_index_key(state.owner_id), {state.claim_id: score})
    pipeline.hset(CLAIM_STATUSES, state.claim_id, state.status)
    pipeline.hset(CLAIM_SEARCH_TEXT, state.claim_id, search_text(state))


def save_claim(state: ClaimState) -> None:
    # One transaction, so the indexes never disagree with the claim.
    pipeline = redis_client.pipeline()
    pipeline.set(
        f"claim:{state.claim_id}",
        state.model_dump_json(),
    )
    index_claim(pipeline, state)
    pipeline.execute()


def delete_claim(claim_id: str) -> None:
    claim = load_claim(claim_id)

    pipeline = redis_client.pipeline()
    pipeline.delete(f"claim:{claim_id}")
    pipeline.zrem(CLAIMS_BY_CREATED, claim_id)
    if claim and claim.owner_id:
        pipeline.zrem(owner_index_key(claim.owner_id), claim_id)
    pipeline.hdel(CLAIM_STATUSES, claim_id)
    pipeline.hdel(CLAIM_SEARCH_TEXT, claim_id)
    pipeline.execute()


def load_claim(claim_id: str) -> ClaimState | None:
    data = redis_client.get(f"claim:{claim_id}")

    if data is None:
        return None

    return ClaimState.model_validate_json(data)


def list_claims(
    owner_id: str | None = None,
    statuses: set[str] | None = None,
    query: str = "",
    oldest_first: bool = False,
    offset: int = 0,
    limit: int = 50,
) -> ClaimPage:
    """One page of claims, newest first unless oldest_first.

    owner_id limits the list to that owner's claims. status_counts covers
    every claim in that scope, ignoring the status and search filters, so
    dashboards can show totals while listing a single page.

    Reads every id and status in scope (small strings, not claim bodies),
    which is fine for thousands of claims; past that, page with ZRANGE
    directly and keep status counts as counters.
    """
    # Claims saved before these indexes existed: build them once.
    if not redis_client.exists(CLAIMS_BY_CREATED):
        reindex_all_claims()

    index_key = (
        owner_index_key(owner_id) if owner_id is not None else CLAIMS_BY_CREATED
    )
    claim_ids = redis_client.zrange(index_key, 0, -1, desc=not oldest_first)

    if not claim_ids:
        return ClaimPage([], 0, {})

    claim_statuses = redis_client.hmget(CLAIM_STATUSES, claim_ids)
    status_counts = Counter(status for status in claim_statuses if status)

    matches = [
        claim_id
        for claim_id, status in zip(claim_ids, claim_statuses)
        if status and (not statuses or status in statuses)
    ]

    query = query.strip().lower()
    if query and matches:
        texts = redis_client.hmget(CLAIM_SEARCH_TEXT, matches)
        matches = [
            claim_id
            for claim_id, text in zip(matches, texts)
            if text and query in text
        ]

    page_ids = matches[offset:offset + limit]
    claims = []

    missing = []

    if page_ids:
        blobs = redis_client.mget([f"claim:{claim_id}" for claim_id in page_ids])
        for claim_id, data in zip(page_ids, blobs):
            if data is None:
                missing.append(claim_id)
                continue
            try:
                claim = ClaimState.model_validate_json(data)
            except Exception:
                continue
            # Defence in depth: the owner index should only hold this
            # owner's claims, but never return anyone else's.
            if owner_id is not None and claim.owner_id != owner_id:
                continue
            claims.append(claim)

    # Index entries whose claim was deleted outside delete_claim: drop them
    # so totals and "Load more" stay honest from the next request on.
    if missing:
        unindex_claims(missing, owner_id)

    return ClaimPage(claims, len(matches) - len(missing), dict(status_counts))


def unindex_claims(claim_ids: list[str], owner_id: str | None = None) -> None:
    pipeline = redis_client.pipeline()
    pipeline.zrem(CLAIMS_BY_CREATED, *claim_ids)
    if owner_id is not None:
        pipeline.zrem(owner_index_key(owner_id), *claim_ids)
    pipeline.hdel(CLAIM_STATUSES, *claim_ids)
    pipeline.hdel(CLAIM_SEARCH_TEXT, *claim_ids)
    pipeline.execute()


def reindex_all_claims() -> int:
    """Rebuild the list indexes from the stored claims. Safe to rerun."""
    count = 0
    pipeline = redis_client.pipeline()

    for key in redis_client.scan_iter(match="claim:*"):
        data = redis_client.get(key)
        if data is None:
            continue
        try:
            claim = ClaimState.model_validate_json(data)
        except Exception:
            continue
        index_claim(pipeline, claim)
        count += 1

    pipeline.execute()
    return count


def save_snapshot(state: ClaimState) -> None:
    snapshot = state.model_dump_json()

    redis_client.set(
        f"snapshot:{state.claim_id}",
        snapshot,
    )

    redis_client.rpush(
        f"snapshots:{state.claim_id}",
        snapshot,
    )


def load_snapshot(claim_id: str) -> ClaimState | None:
    data = redis_client.get(f"snapshot:{claim_id}")

    if data is None:
        return None

    return ClaimState.model_validate_json(data)


def load_snapshots(claim_id: str) -> list[ClaimState]:
    snapshots = redis_client.lrange(
        f"snapshots:{claim_id}",
        0,
        -1,
    )

    return [
        ClaimState.model_validate_json(snapshot)
        for snapshot in snapshots
    ]


def load_submission_claim(idempotency_key: str) -> str | None:
    return redis_client.get(f"claim_submission:{idempotency_key}")


def save_submission_claim(idempotency_key: str, claim_id: str) -> bool:
    return bool(
        redis_client.set(
            f"claim_submission:{idempotency_key}",
            claim_id,
            nx=True,
        )
    )
