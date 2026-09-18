from collections import Counter

from openai import OpenAI

from config import OPENAI_API_KEY
from policy.index import get_collection


client = OpenAI(api_key=OPENAI_API_KEY)


STOP_WORDS = {
    "what",
    "which",
    "when",
    "where",
    "does",
    "this",
    "that",
    "with",
    "from",
    "have",
    "must",
    "will",
    "shall",
    "the",
    "and",
    "for",
    "are",
    "how",
    "any",
    "you",
    "your",
}


IMPORTANT_TERMS = {
    "covered",
    "coverage",
    "damage",
    "accidental",
    "exclusion",
    "excluded",
    "condition",
    "conditions",
    "claim",
    "policy",
    "idv",
    "insured",
    "vehicle",
    "total",
    "loss",
    "theft",
    "repair",
    "depreciation",
    "third-party",
    "liability",
    "driver",
    "licence",
    "license",
}


def create_query_embedding(query: str) -> list[float]:
    if not query.strip():
        raise ValueError("Query cannot be empty")

    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=query,
    )

    return response.data[0].embedding


def tokenize(text: str) -> list[str]:
    return [
        word.strip(".,:;!?()[]{}'\"").lower()
        for word in text.split()
        if word.strip(".,:;!?()[]{}'\"").lower()
    ]


def calculate_keyword_score(
    query: str,
    text: str,
    section: str | None,
) -> float:
    query_tokens = [
        token
        for token in tokenize(query)
        if token not in STOP_WORDS
    ]

    if not query_tokens:
        return 0.0

    text_tokens = set(tokenize(text))
    section_tokens = set(tokenize(section or ""))

    matches = sum(
        1
        for token in query_tokens
        if token in text_tokens
    )

    score = matches / len(query_tokens)

    section_matches = sum(
        1
        for token in query_tokens
        if token in section_tokens
    )

    if section_matches:
        score += 0.20

    important_matches = sum(
        1
        for token in query_tokens
        if token in IMPORTANT_TERMS and token in text_tokens
    )

    if important_matches:
        score += (
            0.10
            * important_matches
            / len(query_tokens)
        )

    return min(score, 1.0)


def calculate_phrase_score(
    query: str,
    text: str,
    section: str | None,
) -> float:
    query_normalized = " ".join(
        tokenize(query)
    )

    text_normalized = " ".join(
        tokenize(text)
    )

    section_normalized = " ".join(
        tokenize(section or "")
    )

    if query_normalized in text_normalized:
        return 1.0

    query_words = query_normalized.split()

    if len(query_words) < 2:
        return 0.0

    matched_phrases = 0

    for index in range(len(query_words) - 1):
        phrase = (
            f"{query_words[index]} "
            f"{query_words[index + 1]}"
        )

        if phrase in text_normalized:
            matched_phrases += 1

        if phrase in section_normalized:
            matched_phrases += 1

    return min(
        matched_phrases / (len(query_words) - 1),
        1.0,
    )


def calculate_section_score(
    query: str,
    section: str | None,
) -> float:
    if not section:
        return 0.0

    query_tokens = set(
        token
        for token in tokenize(query)
        if token not in STOP_WORDS
    )

    section_tokens = set(tokenize(section))

    if not query_tokens:
        return 0.0

    return len(
        query_tokens & section_tokens
    ) / len(query_tokens)


def calculate_final_score(
    query: str,
    text: str,
    section: str | None,
    distance: float,
) -> float:
    semantic_score = 1 / (1 + distance)

    keyword_score = calculate_keyword_score(
        query=query,
        text=text,
        section=section,
    )

    phrase_score = calculate_phrase_score(
        query=query,
        text=text,
        section=section,
    )

    section_score = calculate_section_score(
        query=query,
        section=section,
    )

    return (
        semantic_score * 0.55
        + keyword_score * 0.20
        + phrase_score * 0.15
        + section_score * 0.10
    )


def is_duplicate(
    text: str,
    selected_texts: list[str],
) -> bool:
    normalized = set(tokenize(text))

    if not normalized:
        return True

    for selected in selected_texts:
        selected_tokens = set(tokenize(selected))

        if not selected_tokens:
            continue

        overlap = len(
            normalized & selected_tokens
        ) / min(
            len(normalized),
            len(selected_tokens),
        )

        if overlap >= 0.85:
            return True

    return False


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

    candidate_count = max(top_k * 5, 25)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=candidate_count,
        include=[
            "documents",
            "metadatas",
            "distances",
        ],
    )

    candidates = []

    for document, metadata, distance in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        section = metadata["section"] or None

        score = calculate_final_score(
            query=query,
            text=document,
            section=section,
            distance=distance,
        )

        candidates.append(
            {
                "text": document,
                "source": metadata["source"],
                "product": metadata["product"],
                "document_type": metadata["document_type"],
                "page_start": metadata["page_start"],
                "page_end": metadata["page_end"],
                "section": section,
                "distance": distance,
                "_score": score,
            }
        )

    candidates.sort(
        key=lambda result: result["_score"],
        reverse=True,
    )

    selected = []
    selected_texts = []

    for candidate in candidates:
        if is_duplicate(
            candidate["text"],
            selected_texts,
        ):
            continue

        selected.append(candidate)
        selected_texts.append(candidate["text"])

        if len(selected) == top_k:
            break

    for result in selected:
        result.pop("_score", None)

    return selected