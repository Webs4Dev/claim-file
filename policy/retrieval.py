from openai import OpenAI

from config import OPENAI_API_KEY
from policy.index import get_collection


client = OpenAI(api_key=OPENAI_API_KEY)


def create_query_embedding(query: str) -> list[float]:
    if not query.strip():
        raise ValueError("Query cannot be empty")

    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=query,
    )

    return response.data[0].embedding


def retrieve_policy_chunks(
    query: str,
    product: str,
    top_k: int = 5,
) -> list[dict]:
    if not query.strip():
        raise ValueError("Query cannot be empty")

    if not product.strip():
        raise ValueError("Product cannot be empty")

    if top_k < 1:
        raise ValueError("top_k must be at least 1")

    collection = get_collection(product)
    query_embedding = create_query_embedding(query)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=[
            "documents",
            "metadatas",
            "distances",
        ],
    )

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    retrieved_chunks = []

    for document, metadata, distance in zip(
        documents,
        metadatas,
        distances,
    ):
        retrieved_chunks.append(
            {
                "text": document,
                "source": metadata["source"],
                "product": metadata["product"],
                "document_type": metadata["document_type"],
                "page_start": metadata["page_start"],
                "page_end": metadata["page_end"],
                "section": metadata["section"] or None,
                "distance": distance,
            }
        )

    return retrieved_chunks