import chromadb
from openai import OpenAI

from config import OPENAI_API_KEY
from policy.ingestion import PolicyChunk


client = OpenAI(
    api_key=OPENAI_API_KEY
)

embedding_client = chromadb.PersistentClient(
    path="data/policy_index"
)


def get_collection_name(product: str) -> str:
    product = product.strip()

    if not product:
        raise ValueError("Product cannot be empty")

    return f"policy_{product}"


def get_collection(product: str):
    # Read-only: a missing index must fail loudly, not return an empty
    # collection that makes every claim look unsupported by the policy.
    try:
        return embedding_client.get_collection(
            name=get_collection_name(product)
        )
    except Exception as exc:
        raise ValueError(
            f"No policy index found for product {product!r}. "
            "Run: python -m scripts.build_index"
        ) from exc


def get_staging_collection_name(product: str) -> str:
    return f"{get_collection_name(product)}_staging"


def create_staging_collection(product: str):
    """Fresh collection for a rebuild. The live index keeps serving claims
    until promote_staging_collection swaps this one in."""
    staging_name = get_staging_collection_name(product)

    # Left over from an earlier rebuild that failed part-way.
    try:
        embedding_client.delete_collection(
            name=staging_name
        )
    except Exception:
        pass

    return embedding_client.create_collection(
        name=staging_name
    )


def promote_staging_collection(product: str) -> None:
    """Replace the live collection with the finished staging one."""
    live_name = get_collection_name(product)

    try:
        embedding_client.delete_collection(
            name=live_name
        )
    except Exception:
        pass

    embedding_client.get_collection(
        name=get_staging_collection_name(product)
    ).modify(
        name=live_name
    )


def create_embeddings(
    texts: list[str],
) -> list[list[float]]:
    if not texts:
        raise ValueError(
            "No texts were provided for embedding"
        )

    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=texts,
    )

    return [
        item.embedding
        for item in response.data
    ]


def index_policy_chunks(
    chunks: list[PolicyChunk],
    collection,
) -> None:
    if not chunks:
        raise ValueError(
            "No policy chunks were provided"
        )

    product = chunks[0].product.strip()

    if not product:
        raise ValueError(
            "Policy product cannot be empty"
        )

    if any(
        chunk.product.strip() != product
        for chunk in chunks
    ):
        raise ValueError(
            "All chunks must belong to the same product"
        )

    texts = [
        chunk.text
        for chunk in chunks
    ]

    # Embed each chunk with its section so continuation chunks keep their
    # context (e.g. "Section I" vs a TA add-on). The stored text is unchanged.
    embeddings = create_embeddings(
        [
            f"{chunk.section}\n{chunk.text}"
            if chunk.section
            and not chunk.text.startswith(chunk.section)
            else chunk.text
            for chunk in chunks
        ]
    )

    collection.upsert(
        ids=[
            chunk.chunk_id
            for chunk in chunks
        ],
        embeddings=embeddings,
        documents=texts,
        metadatas=[
            {
                "source": chunk.source,
                "product": chunk.product,
                "document_type": chunk.document_type,
                "page_start": chunk.page_start,
                "page_end": chunk.page_end,
                "section": chunk.section or "",
            }
            for chunk in chunks
        ],
    )