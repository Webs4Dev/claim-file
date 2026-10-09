from openai import OpenAI

from config import OPENAI_API_KEY
from policy.bm25 import search_bm25
from policy.index import get_collection
from policy.reranker import rerank_policy_chunks


client = OpenAI(
    api_key=OPENAI_API_KEY
)


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
    "is",
    "of",
    "to",
    "a",
    "an",
    "in",
    "on",
    "under",
    "can",
}


IMPORTANT_TERMS = {
    "covered",
    "coverage",
    "cover",
    "damage",
    "accidental",
    "accident",
    "collision",
    "own",
    "own-damage",
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
    "third-party",
    "liability",
    "driver",
    "licence",
    "license",
    "deductible",
}


COVERAGE_TERMS = {
    "covered",
    "coverage",
    "cover",
    "accidental",
    "accident",
    "collision",
    "own",
    "own-damage",
    "damage",
    "exclusion",
    "excluded",
    "condition",
    "conditions",
    "insured",
    "vehicle",
}


POLICY_SECTION_TERMS = {
    "what is covered",
    "what is not covered",
    "exclusions",
    "general exceptions",
    "special conditions",
    "coverage conditions",
    "conditions during the contract",
}


INTENT_TERMS = {
    "own_damage": {
        "own",
        "own-damage",
        "collision",
        "accidental",
        "damage",
        "vehicle",
    },
    "third_party": {
        "third-party",
        "third",
        "party",
        "liability",
        "injury",
        "property",
    },
    "theft": {
        "theft",
        "stolen",
        "steal",
        "burglary",
    },
    "driver": {
        "driver",
        "driving",
        "licence",
        "license",
        "authorized",
    },
    "deductible": {
        "deductible",
        "excess",
    },
    "idv": {
        "idv",
        "insured",
        "declared",
        "value",
        "total",
        "loss",
    },
    "repair": {
        "repair",
        "replace",
        "replacement",
        "garage",
        "workshop",
    },
    "police": {
        "police",
        "fir",
        "report",
        "station",
        "complaint",
    },
}


SCOPE_TERMS = {
    "own_damage": {
        "section i",
        "own damage",
        "own-damage",
        "loss or damage",
        "insured vehicle",
        "vehicle insured",
    },
    "third_party": {
        "section ii",
        "third party",
        "third-party",
        "liability",
        "bodily injury",
        "property damage",
    },
    "personal_accident": {
        "section iii",
        "personal accident",
        "owner-driver",
        "owner driver",
    },
    "idv": {
        "insured declared value",
        "idv",
        "total loss",
        "constructive total loss",
        "ctl",
        "tl",
    },
    "claim_conditions": {
        "general conditions",
        "conditions during the contract",
        "duties and obligations",
        "claim",
        "notification",
        "reasonable care",
    },
    "theft": {
        "theft",
        "stolen",
        "burglary",
        "section i",
    },
    "driver": {
        "driver",
        "driving licence",
        "driving license",
        "authorized driver",
        "licence",
        "license",
    },
    "deductible": {
        "deductible",
        "excess",
        "policy schedule",
    },
    "repair": {
        "repair",
        "replacement",
        "workshop",
        "garage",
    },
    "police": {
        "police",
        "fir",
        "report",
        "complaint",
    },
}


SCOPE_PREFERENCES = {
    "own_damage": {
        "own_damage": 1.00,
        "theft": 0.75,
        "claim_conditions": 0.45,
        "deductible": 0.40,
        "repair": 0.35,
        "idv": 0.25,
        "third_party": -0.55,
        "personal_accident": -0.45,
    },
    "third_party": {
        "third_party": 1.00,
        "claim_conditions": 0.40,
        "own_damage": -0.55,
        "personal_accident": -0.45,
    },
    "theft": {
        "theft": 1.00,
        "own_damage": 0.65,
        "claim_conditions": 0.45,
        "idv": 0.35,
        "third_party": -0.55,
        "personal_accident": -0.45,
    },
    "driver": {
        "driver": 1.00,
        "claim_conditions": 0.40,
        "own_damage": 0.20,
        "third_party": 0.20,
    },
    "deductible": {
        "deductible": 1.00,
        "own_damage": 0.45,
        "claim_conditions": 0.30,
        "idv": 0.20,
    },
    "idv": {
        "idv": 1.00,
        "own_damage": 0.40,
        "theft": 0.35,
        "claim_conditions": 0.20,
    },
    "repair": {
        "repair": 1.00,
        "own_damage": 0.55,
        "claim_conditions": 0.30,
    },
    "police": {
        "police": 1.00,
        "claim_conditions": 0.45,
        "theft": 0.30,
        "own_damage": 0.20,
    },
}


def create_query_embedding(
    query: str,
) -> list[float]:
    if not query.strip():
        raise ValueError(
            "Query cannot be empty"
        )

    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=query,
    )

    return response.data[0].embedding


def tokenize(
    text: str,
) -> list[str]:
    tokens = []

    for word in text.split():
        cleaned = word.strip(
            ".,:;!?()[]{}'\""
        ).lower()

        if cleaned:
            tokens.append(cleaned)

    return tokens


def normalize_text(
    text: str,
) -> str:
    return " ".join(
        tokenize(text)
    )


def detect_query_intent(
    query: str,
) -> str:
    query_tokens = {
        token
        for token in tokenize(query)
        if token not in STOP_WORDS
    }

    query_text = normalize_text(query)

    # Section I is the policy's own-damage section. Treat it as a strong
    # signal even when the question also names a deductible or condition.
    if (
        "section i" in query_text
        or "own damage" in query_text
        or "own-damage" in query_text
    ):
        return "own_damage"

    if (
        "third party" in query_text
        or "third-party" in query_text
        or "liability" in query_tokens
    ):
        return "third_party"

    if (
        "personal accident" in query_text
        or "owner driver" in query_text
        or "owner-driver" in query_text
    ):
        return "personal_accident"

    best_intent = "general"
    best_score = 0

    for intent, terms in INTENT_TERMS.items():
        score = len(
            query_tokens & terms
        )

        if score > best_score:
            best_score = score
            best_intent = intent

    return best_intent


def detect_scope(
    query: str,
    intent: str,
) -> str:
    query_text = normalize_text(query)

    # Scope identifies the policy section. A query can also contain a
    # subtopic such as "deductible" or "conditions"; that must not move it
    # out of Section I and into a different retrieval universe.
    if (
        "section i" in query_text
        or "own damage" in query_text
        or "own-damage" in query_text
        or (
            intent == "own_damage"
            and any(
                term in query_text
                for term in (
                    "collision",
                    "accidental damage",
                    "loss or damage",
                    "insured vehicle",
                )
            )
        )
    ):
        return "own_damage"

    if (
        "personal accident" in query_text
        or "owner driver" in query_text
        or "owner-driver" in query_text
    ):
        return "personal_accident"

    if (
        "third party" in query_text
        or "third-party" in query_text
        or "third party liability" in query_text
    ):
        return "third_party"

    if (
        "insured declared value" in query_text
        or "idv" in query_text
        or "constructive total loss" in query_text
        or "total loss" in query_text
    ):
        return "idv"

    if (
        "deductible" in query_text
        or "excess" in query_text
    ):
        return "deductible"

    if (
        "driving licence" in query_text
        or "driving license" in query_text
        or "authorized driver" in query_text
        or "authorised driver" in query_text
    ):
        return "driver"

    if (
        "police" in query_text
        or "fir" in query_text
        or "first information report" in query_text
    ):
        return "police"

    if (
        "repair" in query_text
        or "replacement" in query_text
        or "workshop" in query_text
        or "garage" in query_text
    ):
        return "repair"

    if (
        "theft" in query_text
        or "stolen" in query_text
        or "burglary" in query_text
    ):
        return "theft"

    if (
        "condition" in query_text
        or "conditions" in query_text
        or "claim procedure" in query_text
        or "claim process" in query_text
        or "notify" in query_text
        or "notification" in query_text
    ):
        return "claim_conditions"

    if intent == "own_damage":
        return "own_damage"

    if intent in SCOPE_TERMS:
        return intent

    return "general"


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

    text_tokens = set(
        tokenize(text)
    )

    section_tokens = set(
        tokenize(section or "")
    )

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
        if token in IMPORTANT_TERMS
        and token in text_tokens
    )

    if important_matches:
        score += (
            0.10
            * important_matches
            / len(query_tokens)
        )

    return min(
        score,
        1.0,
    )


def calculate_phrase_score(
    query: str,
    text: str,
    section: str | None,
) -> float:
    query_normalized = normalize_text(
        query
    )

    text_normalized = normalize_text(
        text
    )

    section_normalized = normalize_text(
        section or ""
    )

    if query_normalized in text_normalized:
        return 1.0

    query_words = (
        query_normalized.split()
    )

    if len(query_words) < 2:
        return 0.0

    matched_phrases = 0

    for index in range(
        len(query_words) - 1
    ):
        phrase = (
            f"{query_words[index]} "
            f"{query_words[index + 1]}"
        )

        if phrase in text_normalized:
            matched_phrases += 1

        if phrase in section_normalized:
            matched_phrases += 1

    return min(
        matched_phrases
        / (len(query_words) - 1),
        1.0,
    )


def calculate_section_score(
    query: str,
    section: str | None,
) -> float:
    if not section:
        return 0.0

    query_tokens = {
        token
        for token in tokenize(query)
        if token not in STOP_WORDS
    }

    section_tokens = set(
        tokenize(section)
    )

    if not query_tokens:
        return 0.0

    return (
        len(
            query_tokens
            & section_tokens
        )
        / len(query_tokens)
    )


def calculate_coverage_score(
    query: str,
    text: str,
    section: str | None,
) -> float:
    query_tokens = {
        token
        for token in tokenize(query)
        if token not in STOP_WORDS
    }

    if not query_tokens:
        return 0.0

    text_tokens = set(
        tokenize(text)
    )

    section_tokens = set(
        tokenize(section or "")
    )

    query_coverage_terms = (
        query_tokens
        & COVERAGE_TERMS
    )

    if not query_coverage_terms:
        return 0.0

    text_matches = len(
        query_coverage_terms
        & text_tokens
    )

    section_matches = len(
        query_coverage_terms
        & section_tokens
    )

    text_score = (
        text_matches
        / len(query_coverage_terms)
    )

    section_score = (
        section_matches
        / len(query_coverage_terms)
    )

    return min(
        text_score * 0.75
        + section_score * 0.25,
        1.0,
    )


def calculate_section_priority(
    section: str | None,
) -> float:
    if not section:
        return 0.0

    normalized = normalize_text(
        section
    )

    for policy_section in (
        POLICY_SECTION_TERMS
    ):
        normalized_section = (
            normalize_text(
                policy_section
            )
        )

        if normalized_section == normalized:
            return 1.0

    return 0.0


def calculate_intent_relevance(
    query: str,
    text: str,
    section: str | None,
    intent: str,
) -> float:
    if intent == "general":
        return 0.0

    intent_terms = INTENT_TERMS.get(
        intent,
        set(),
    )

    if not intent_terms:
        return 0.0

    query_tokens = set(
        tokenize(query)
    )

    text_tokens = set(
        tokenize(text)
    )

    section_tokens = set(
        tokenize(section or "")
    )

    relevant_query_terms = (
        query_tokens
        & intent_terms
    )

    if not relevant_query_terms:
        relevant_query_terms = (
            intent_terms
        )

    text_matches = len(
        relevant_query_terms
        & text_tokens
    )

    section_matches = len(
        relevant_query_terms
        & section_tokens
    )

    text_score = (
        text_matches
        / len(relevant_query_terms)
    )

    section_score = (
        section_matches
        / len(relevant_query_terms)
    )

    return min(
        text_score * 0.70
        + section_score * 0.30,
        1.0,
    )


def detect_candidate_scopes(
    text: str,
    section: str | None,
) -> dict[str, float]:
    combined = normalize_text(
        f"{section or ''} {text}"
    )

    scores = {}

    for scope, terms in (
        SCOPE_TERMS.items()
    ):
        matches = 0

        for term in terms:
            normalized_term = (
                normalize_text(term)
            )

            if normalized_term in combined:
                matches += 1

        if matches == 0:
            scores[scope] = 0.0
        else:
            scores[scope] = min(
                matches
                / max(len(terms), 1),
                1.0,
            )

    return scores


def calculate_scope_score(
    query: str,
    text: str,
    section: str | None,
    scope: str,
) -> float:
    if scope == "general":
        return 0.0

    candidate_scopes = (
        detect_candidate_scopes(
            text=text,
            section=section,
        )
    )

    preferences = (
        SCOPE_PREFERENCES.get(
            scope,
            {},
        )
    )

    if not preferences:
        return 0.0

    score = 0.0

    for (
        candidate_scope,
        preference,
    ) in preferences.items():
        candidate_score = (
            candidate_scopes.get(
                candidate_scope,
                0.0,
            )
        )

        score += (
            candidate_score
            * preference
        )

    query_text = normalize_text(
        query
    )

    direct_scope_terms = (
        SCOPE_TERMS.get(
            scope,
            set(),
        )
    )

    direct_matches = 0

    for term in direct_scope_terms:
        if normalize_text(term) in query_text:
            direct_matches += 1

    if direct_scope_terms:
        query_scope_score = (
            direct_matches
            / len(direct_scope_terms)
        )
    else:
        query_scope_score = 0.0

    score += (
        query_scope_score
        * 0.20
    )

    return max(
        min(score, 1.0),
        -1.0,
    )


def calculate_add_on_penalty(
    text: str,
    section: str | None,
    intent: str,
) -> float:
    if intent == "general":
        return 0.0

    combined_text = normalize_text(
        f"{section or ''} {text}"
    )

    add_on_terms = {
        "add-on",
        "addon",
        "protector",
        "protection",
        "personal",
        "belongings",
        "tyre",
        "tire",
        "panel",
        "key",
        "engine",
    }

    matches = sum(
        1
        for term in add_on_terms
        if term in combined_text
    )

    if matches >= 3:
        return 1.0

    if matches == 2:
        return 0.7

    if matches == 1:
        return 0.3

    return 0.0


def calculate_chroma_score(
    distance: float,
) -> float:
    return 1 / (
        1 + max(
            distance,
            0.0,
        )
    )


def normalize_bm25_scores(
    results: list[dict],
) -> list[dict]:
    if not results:
        return results

    scores = [
        result.get(
            "bm25_score",
            0.0,
        )
        for result in results
    ]

    maximum = max(scores)
    minimum = min(scores)

    if maximum == minimum:
        for result in results:
            result[
                "bm25_normalized"
            ] = 1.0

        return results

    for result in results:
        result[
            "bm25_normalized"
        ] = (
            (
                result.get(
                    "bm25_score",
                    0.0,
                )
                - minimum
            )
            / (maximum - minimum)
        )

    return results


def build_query_variants(
    query: str,
    intent: str,
) -> list[str]:
    normalized_query = query.strip()

    variants = [
        normalized_query
    ]

    if intent == "own_damage":
        variants.append(
            (
                f"{normalized_query} "
                "Section I Own Damage accidental loss or damage "
                "to the insured vehicle"
            )
        )

        query_text = normalize_text(normalized_query)

        if any(
            term in query_text
            for term in (
                "exclusion",
                "exclusions",
                "general exception",
                "not covered",
            )
        ):
            variants.append(
                (
                    f"{normalized_query} "
                    "Section I Own Damage exclusions general exceptions "
                    "what is not covered"
                )
            )

        if any(
            term in query_text
            for term in (
                "condition",
                "conditions",
                "reasonable care",
                "claim condition",
            )
        ):
            variants.append(
                (
                    f"{normalized_query} "
                    "Section I Own Damage conditions reasonable care "
                    "conditions when a claim arises"
                )
            )

        if (
            "deductible" in query_text
            or "excess" in query_text
        ):
            variants.append(
                (
                    f"{normalized_query} "
                    "Section I Own Damage deductible excess policy schedule"
                )
            )

    elif intent == "third_party":
        variants.append(
            (
                f"{normalized_query} "
                "third party liability "
                "property damage bodily injury"
            )
        )

    elif intent == "theft":
        variants.append(
            (
                f"{normalized_query} "
                "theft stolen vehicle "
                "theft conditions exclusions"
            )
        )

    elif intent == "driver":
        variants.append(
            (
                f"{normalized_query} "
                "driver licence license "
                "valid driving licence"
            )
        )

    elif intent == "deductible":
        variants.append(
            (
                f"{normalized_query} "
                "deductible excess amount "
                "policy schedule"
            )
        )

    elif intent == "idv":
        variants.append(
            (
                f"{normalized_query} "
                "insured declared value IDV "
                "total loss"
            )
        )

    elif intent == "repair":
        variants.append(
            (
                f"{normalized_query} "
                "repair replacement workshop "
                "reasonable repair costs"
            )
        )

    elif intent == "police":
        variants.append(
            (
                f"{normalized_query} "
                "police FIR report "
                "claim notification"
            )
        )

    return variants


def retrieve_chroma_candidates(
    query: str,
    product: str,
    candidate_count: int,
) -> list[dict]:
    query_embedding = (
        create_query_embedding(query)
    )

    collection = get_collection(
        product.strip()
    )

    results = collection.query(
        query_embeddings=[
            query_embedding
        ],
        n_results=candidate_count,
        include=[
            "documents",
            "metadatas",
            "distances",
        ],
    )

    candidates = []

    documents = results.get(
        "documents",
        [[]],
    )[0]

    metadatas = results.get(
        "metadatas",
        [[]],
    )[0]

    distances = results.get(
        "distances",
        [[]],
    )[0]

    for (
        document,
        metadata,
        distance,
    ) in zip(
        documents,
        metadatas,
        distances,
    ):
        metadata = metadata or {}

        candidates.append(
            {
                "text": document,
                "source": metadata.get(
                    "source",
                    "",
                ),
                "product": metadata.get(
                    "product",
                    "",
                ),
                "document_type": metadata.get(
                    "document_type",
                    "",
                ),
                "page_start": metadata.get(
                    "page_start",
                ),
                "page_end": metadata.get(
                    "page_end",
                ),
                "section": metadata.get(
                    "section"
                ) or None,
                "chroma_distance": distance,
                "chroma_score": (
                    calculate_chroma_score(
                        distance
                    )
                ),
            }
        )

    return candidates


def create_candidate_key(
    candidate: dict,
) -> tuple:
    return (
        candidate.get(
            "source",
            "",
        ),
        candidate.get(
            "document_type",
            "",
        ),
        candidate.get(
            "page_start"
        ),
        candidate.get(
            "page_end"
        ),
        candidate.get(
            "text",
            "",
        ),
    )


def merge_candidates(
    chroma_candidates: list[dict],
    bm25_candidates: list[dict],
) -> list[dict]:
    merged = {}

    bm25_candidates = (
        normalize_bm25_scores(
            bm25_candidates
        )
    )

    for candidate in (
        chroma_candidates
    ):
        key = create_candidate_key(
            candidate
        )

        if key not in merged:
            merged[key] = {
                **candidate,
                "bm25_score": 0.0,
                "bm25_normalized": 0.0,
            }
            continue

        # A chunk may be returned for several query variants. Keep the best
        # semantic match instead of retaining whichever variant was searched
        # first (usually the least specific original query).
        existing = merged[key]

        if candidate.get(
            "chroma_score",
            0.0,
        ) > existing.get(
            "chroma_score",
            0.0,
        ):
            existing.update(candidate)

    for candidate in (
        bm25_candidates
    ):
        key = create_candidate_key(
            candidate
        )

        if key not in merged:
            merged[key] = {
                **candidate,
                "chroma_distance": None,
                "chroma_score": 0.0,
            }

            continue

        existing = merged[key]

        if candidate.get(
            "bm25_normalized",
            0.0,
        ) > existing.get(
            "bm25_normalized",
            0.0,
        ):
            existing[
                "bm25_normalized"
            ] = candidate[
                "bm25_normalized"
            ]

            existing[
                "bm25_score"
            ] = candidate[
                "bm25_score"
            ]

    return list(
        merged.values()
    )


def calculate_hybrid_score(
    query: str,
    candidate: dict,
    intent: str,
    scope: str,
) -> float:
    text = candidate.get(
        "text",
        "",
    )

    section = candidate.get(
        "section"
    )

    semantic_score = candidate.get(
        "chroma_score",
        0.0,
    )

    bm25_score = candidate.get(
        "bm25_normalized",
        0.0,
    )

    keyword_score = (
        calculate_keyword_score(
            query=query,
            text=text,
            section=section,
        )
    )

    phrase_score = (
        calculate_phrase_score(
            query=query,
            text=text,
            section=section,
        )
    )

    section_score = (
        calculate_section_score(
            query=query,
            section=section,
        )
    )

    coverage_score = (
        calculate_coverage_score(
            query=query,
            text=text,
            section=section,
        )
    )

    section_priority = (
        calculate_section_priority(
            section
        )
    )

    intent_score = (
        calculate_intent_relevance(
            query=query,
            text=text,
            section=section,
            intent=intent,
        )
    )

    scope_score = (
        calculate_scope_score(
            query=query,
            text=text,
            section=section,
            scope=scope,
        )
    )

    add_on_penalty = (
        calculate_add_on_penalty(
            text=text,
            section=section,
            intent=intent,
        )
    )

    return (
        semantic_score * 0.20
        + bm25_score * 0.20
        + keyword_score * 0.10
        + phrase_score * 0.07
        + section_score * 0.07
        + coverage_score * 0.07
        + section_priority * 0.04
        + intent_score * 0.10
        + scope_score * 0.25
        - add_on_penalty * 0.15
    )


def is_duplicate(
    text: str,
    selected_texts: list[str],
) -> bool:
    normalized = set(
        tokenize(text)
    )

    if not normalized:
        return True

    for selected in selected_texts:
        selected_tokens = set(
            tokenize(selected)
        )

        if not selected_tokens:
            continue

        overlap = (
            len(
                normalized
                & selected_tokens
            )
            / min(
                len(normalized),
                len(selected_tokens),
            )
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
        raise ValueError(
            "Query cannot be empty"
        )

    if not product.strip():
        raise ValueError(
            "Product cannot be empty"
        )

    if top_k < 1:
        raise ValueError(
            "top_k must be at least 1"
        )

    intent = detect_query_intent(
        query
    )

    scope = detect_scope(
        query=query,
        intent=intent,
    )

    query_variants = (
        build_query_variants(
            query=query,
            intent=intent,
        )
    )

    candidate_count = max(
        top_k * 4,
        12,
    )

    all_chroma_candidates = []
    all_bm25_candidates = []

    for query_variant in (
        query_variants
    ):
        chroma_candidates = (
            retrieve_chroma_candidates(
                query=query_variant,
                product=product,
                candidate_count=candidate_count,
            )
        )

        bm25_candidates = search_bm25(
            query=query_variant,
            product=product,
            top_k=candidate_count,
        )

        all_chroma_candidates.extend(
            chroma_candidates
        )

        all_bm25_candidates.extend(
            bm25_candidates
        )

    candidates = merge_candidates(
        chroma_candidates=(
            all_chroma_candidates
        ),
        bm25_candidates=(
            all_bm25_candidates
        ),
    )

    for candidate in candidates:
        candidate["_score"] = (
            calculate_hybrid_score(
                query=query,
                candidate=candidate,
                intent=intent,
                scope=scope,
            )
        )

    candidates.sort(
        key=lambda result: result[
            "_score"
        ],
        reverse=True,
    )

    candidate_pool_size = max(
        top_k * 3,
        12,
    )

    candidate_pool = candidates[
        :candidate_pool_size
    ]

    reranked_candidates = (
        rerank_policy_chunks(
            query=query,
            candidates=candidate_pool,
            intent=intent,
            scope=scope,
            top_k=top_k,
        )
    )

    selected = []
    selected_texts = []

    for candidate in (
        reranked_candidates
    ):
        if is_duplicate(
            candidate["text"],
            selected_texts,
        ):
            continue

        selected.append(candidate)

        selected_texts.append(
            candidate["text"]
        )

        if len(selected) == top_k:
            break

    for result in selected:
        result.pop(
            "_score",
            None,
        )

        result.pop(
            "bm25_normalized",
            None,
        )

        result.pop(
            "chroma_score",
            None,
        )

        result.pop(
            "chroma_distance",
            None,
        )

    return selected
