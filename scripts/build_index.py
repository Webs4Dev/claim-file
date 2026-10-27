from policy.bm25 import build_bm25_index, get_index_path
from policy.index import (
    create_staging_collection,
    index_policy_chunks,
    promote_staging_collection,
)
from policy.ingestion import ingest_policy


POLICIES = [
    {
        "path": "data/policies/tata_aig/private_car/policy_wording.pdf",
        "product": "private_car",
        "document_type": "policy_wording",
    },
    {
        "path": "data/policies/tata_aig/private_car/idv_tl_ctl_criteria.pdf",
        "product": "private_car",
        "document_type": "idv_tl_ctl_criteria",
    },
]


def build_index() -> None:
    """Rebuild into staging copies and swap them in only once everything
    has succeeded, so a failed run (bad PDF, embedding API error) leaves
    the live index serving claims unchanged."""
    all_chunks = []

    staging_collections = {
        product: create_staging_collection(product)
        for product in {policy["product"] for policy in POLICIES}
    }

    for policy in POLICIES:
        chunks = ingest_policy(
            path=policy["path"],
            product=policy["product"],
            document_type=policy["document_type"],
        )

        print(
            f"{policy['document_type']}: "
            f"{len(chunks)} chunks"
        )

        index_policy_chunks(
            chunks,
            staging_collections[policy["product"]],
        )

        all_chunks.extend(
            [
                {
                    "text": chunk.text,
                    "source": chunk.source,
                    "product": chunk.product,
                    "document_type": chunk.document_type,
                    "page_start": chunk.page_start,
                    "page_end": chunk.page_end,
                    "section": chunk.section,
                }
                for chunk in chunks
            ]
        )

        print(
            f"Indexed {policy['document_type']} "
            "in ChromaDB"
        )

    bm25_path = get_index_path("private_car")
    staging_bm25_path = bm25_path.with_suffix(".staging.json")

    build_bm25_index(
        chunks=all_chunks,
        product="private_car",
        index_path=staging_bm25_path,
    )

    for product in staging_collections:
        promote_staging_collection(product)

    # Atomic on the same filesystem: readers see the old file or the new one.
    staging_bm25_path.replace(bm25_path)

    print(
        f"Indexed {len(all_chunks)} chunks in BM25"
    )


if __name__ == "__main__":
    build_index()