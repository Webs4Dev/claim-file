"""Build the claim list indexes from the claims already in Redis.

    venv/bin/python -m scripts.reindex_claims

/claims builds the indexes by itself when they are missing, and new and
updated claims are indexed on save, so this is only needed to repair them
by hand. Rerunning is harmless.
"""

from state.store import reindex_all_claims


if __name__ == "__main__":
    print(f"Indexed {reindex_all_claims()} claims.")
