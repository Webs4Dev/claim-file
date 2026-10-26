from state.store import redis_client

# Snapshots and idempotency keys point at claims, so they must be cleared
# with them. A leftover claim_submission key would make that client's
# next submission fail with 409 forever.
PATTERNS = ["claim:*", "snapshot:*", "snapshots:*", "claim_submission:*"]

keys = [
    key
    for pattern in PATTERNS
    for key in redis_client.scan_iter(match=pattern)
]

claim_count = sum(1 for key in keys if key.startswith("claim:"))

if not keys:
    print("No claims found.")
else:
    confirm = input(
        f"Delete {claim_count} claims ({len(keys)} keys incl. snapshots and "
        "submission keys)? Type DELETE to confirm: "
    )

    if confirm == "DELETE":
        deleted = redis_client.delete(*keys)
        print(f"Deleted {deleted} keys.")
    else:
        print("Deletion cancelled.")
