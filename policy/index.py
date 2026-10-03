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


def get_collection(product: str):
    product = product.strip()

    if not product:
        raise ValueError("Product cannot be empty")

    collection_name = f"policy_{product}"

    return embedding_client.get_or_create_collection(
        name=collection_name
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

    collection = get_collection(product)

    texts = [
        chunk.text
        for chunk in chunks
    ]

    embeddings = create_embeddings(
        texts
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