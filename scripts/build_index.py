from policy.index import index_policy_chunks
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

        print(
            f"Indexed {policy['document_type']}"
        )


if __name__ == "__main__":
    build_index()