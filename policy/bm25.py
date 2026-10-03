import json
import math
from pathlib import Path

from rank_bm25 import BM25Okapi


INDEX_PATH = Path("data/policy_bm25")


def tokenize(text: str) -> list[str]:
    tokens = []

    for word in text.lower().split():
        cleaned = word.strip(
            ".,:;!?()[]{}'\""
        )

        if cleaned:
            tokens.append(cleaned)

    return tokens


def get_index_path(product: str) -> Path:
    product = product.strip()

    if not product:
        raise ValueError("Product cannot be empty")

    return INDEX_PATH / f"{product}.json"


def build_bm25_index(
    chunks: list[dict],
    product: str,
) -> None:

    if not chunks:
        raise ValueError("No chunks were provided")

    product = product.strip()

    if not product:
        raise ValueError("Product cannot be empty")

    if any(
        chunk.get("product", "").strip() != product
        for chunk in chunks
    ):
        raise ValueError(
            "All chunks must belong to the same product"
        )

    documents = []

    for chunk in chunks:
        documents.append(
            {
                "text": chunk.get("text", ""),
                "source": chunk.get("source", ""),
                "product": chunk.get("product", ""),
                "document_type": chunk.get(
                    "document_type",
                    "",
                ),
                "page_start": chunk.get("page_start"),
                "page_end": chunk.get("page_end"),
                "section": chunk.get("section"),
            }
        )

    corpus = [
        tokenize(document["text"])
        for document in documents
    ]

    bm25 = BM25Okapi(corpus)

    INDEX_PATH.mkdir(
        parents=True,
        exist_ok=True,
    )

    index_data = {
        "product": product,
        "documents": documents,
        "corpus": corpus,
        "idf": bm25.idf,
    }

    index_path = get_index_path(product)

    index_path.write_text(
        json.dumps(
            index_data,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def load_bm25_index(
    product: str,
) -> tuple[BM25Okapi, list[dict]]:

    index_path = get_index_path(product)

    if not index_path.exists():
        raise FileNotFoundError(
            f"BM25 index not found: {index_path}"
        )

    data = json.loads(
        index_path.read_text(
            encoding="utf-8",
        )
    )

    documents = data["documents"]

    corpus = [
        tokenize(document["text"])
        for document in documents
    ]

    bm25 = BM25Okapi(corpus)

    return bm25, documents


def search_bm25(
    query: str,
    product: str,
    top_k: int = 10,
) -> list[dict]:

    if not query.strip():
        raise ValueError("Query cannot be empty")

    if not product.strip():
        raise ValueError("Product cannot be empty")

    if top_k < 1:
        raise ValueError("top_k must be at least 1")

    bm25, documents = load_bm25_index(
        product
    )

    query_tokens = tokenize(query)

    if not query_tokens:
        return []

    scores = bm25.get_scores(query_tokens)

    ranked_indexes = sorted(
        range(len(scores)),
        key=lambda index: scores[index],
        reverse=True,
    )

    results = []

    for index in ranked_indexes[:top_k]:
        document = documents[index]

        results.append(
            {
                "text": document["text"],
                "source": document["source"],
                "product": document["product"],
                "document_type": document[
                    "document_type"
                ],
                "page_start": document["page_start"],
                "page_end": document["page_end"],
                "section": document["section"],
                "bm25_score": float(scores[index]),
            }
        )

    return results