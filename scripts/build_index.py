from policy.bm25 import build_bm25_index
from policy.index import index_policy_chunks, reset_collection
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
    all_chunks = []

    for product in {policy["product"] for policy in POLICIES}:
        reset_collection(product)

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

        index_policy_chunks(chunks)

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

    build_bm25_index(
        chunks=all_chunks,
        product="private_car",
    )

    print(
        f"Indexed {len(all_chunks)} chunks in BM25"
    )


if __name__ == "__main__":
    build_index()