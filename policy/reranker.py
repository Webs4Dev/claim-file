import re


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


INTENT_TERMS = {
    "own_damage": {
        "own",
        "own-damage",
        "accidental",
        "accident",
        "damage",
        "collision",
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
        "authorised",
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
        "insured declared value",
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
    "personal_accident": {
        "personal",
        "accident",
        "owner-driver",
        "owner",
        "driver",
    },
    "claim_conditions": {
        "claim",
        "condition",
        "conditions",
        "notification",
        "notice",
        "obligation",
        "duties",
        "report",
    },
}


SCOPE_TERMS = {
    "own_damage": {
        "section i",
        "own damage",
        "own-damage",
        "loss or damage",
        "vehicle insured",
        "insured vehicle",
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
        "conditions when a claim arises",
        "claim",
        "notification",
        "notice",
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
        "authorised driver",
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


PREFERRED_DOCUMENT_TYPES = {
    "idv": {
        "idv_tl_ctl_criteria",
    },
    "own_damage": {
        "policy_wording",
    },
    "third_party": {
        "policy_wording",
    },
    "personal_accident": {
        "policy_wording",
    },
    "claim_conditions": {
        "policy_wording",
    },
    "theft": {
        "policy_wording",
    },
    "driver": {
        "policy_wording",
    },
    "deductible": {
        "policy_wording",
    },
    "repair": {
        "policy_wording",
    },
    "police": {
        "policy_wording",
    },
}


def tokenize(text: str) -> list[str]:
    text = text.lower()

    text = re.sub(
        r"[^a-z0-9\s-]",
        " ",
        text,
    )

    return [
        token
        for token in text.split()
        if token
    ]


def normalize_text(text: str) -> str:
    return " ".join(
        tokenize(text)
    )


def get_query_terms(query: str) -> set[str]:
    return {
        token
        for token in tokenize(query)
        if token not in STOP_WORDS
    }


def detect_intent(query: str) -> str:
    normalized = normalize_text(query)

    if (
        "insured declared value"
        in normalized
        or "idv" in normalized
    ):
        return "idv"

    if (
        "total loss" in normalized
        or "constructive total loss"
        in normalized
    ):
        return "idv"

    intent_scores = {}

    for intent, terms in INTENT_TERMS.items():
        score = 0

        for term in terms:
            normalized_term = normalize_text(term)

            if normalized_term in normalized:
                score += 1

        intent_scores[intent] = score

    if not intent_scores:
        return "general"

    best_intent = max(
        intent_scores,
        key=intent_scores.get,
    )

    if intent_scores[best_intent] == 0:
        return "general"

    return best_intent


def detect_query_type(query: str) -> str:
    normalized = normalize_text(query)

    exclusion_terms = {
        "exclusion",
        "exclusions",
        "excluded",
        "exclude",
        "not covered",
        "not cover",
        "exception",
        "exceptions",
        "does not cover",
        "doesnt cover",
    }

    coverage_terms = {
        "covered",
        "cover",
        "coverage",
        "insure",
        "insured",
        "pay",
        "payable",
        "indemnify",
    }

    condition_terms = {
        "condition",
        "conditions",
        "claim",
        "claims",
        "notification",
        "notice",
        "obligation",
        "obligations",
        "duties",
        "requirements",
        "making a claim",
        "making claim",
    }

    if any(
        term in normalized
        for term in exclusion_terms
    ):
        return "exclusion"

    if any(
        term in normalized
        for term in condition_terms
    ):
        return "claim_conditions"

    if any(
        term in normalized
        for term in coverage_terms
    ):
        return "coverage"

    return "general"


def calculate_term_coverage(
    query: str,
    text: str,
) -> float:
    query_terms = get_query_terms(query)

    if not query_terms:
        return 0.0

    text_terms = set(
        tokenize(text)
    )

    matches = len(
        query_terms & text_terms
    )

    return matches / len(query_terms)


def calculate_phrase_match(
    query: str,
    text: str,
) -> float:
    query_normalized = normalize_text(query)
    text_normalized = normalize_text(text)

    if not query_normalized:
        return 0.0

    if query_normalized in text_normalized:
        return 1.0

    query_terms = query_normalized.split()

    if len(query_terms) < 2:
        return 0.0

    matched = 0

    for index in range(
        len(query_terms) - 1
    ):
        phrase = (
            f"{query_terms[index]} "
            f"{query_terms[index + 1]}"
        )

        if phrase in text_normalized:
            matched += 1

    return min(
        matched / (len(query_terms) - 1),
        1.0,
    )


def calculate_section_match(
    scope: str,
    section: str | None,
) -> float:
    if not section:
        return 0.0

    scope_terms = SCOPE_TERMS.get(
        scope,
        set(),
    )

    if not scope_terms:
        return 0.0

    section_normalized = normalize_text(
        section
    )

    matches = 0

    for term in scope_terms:
        if normalize_text(term) in section_normalized:
            matches += 1

    return min(
        matches / len(scope_terms),
        1.0,
    )


def calculate_scope_match(
    scope: str,
    text: str,
    section: str | None,
) -> float:
    scope_terms = SCOPE_TERMS.get(
        scope,
        set(),
    )

    if not scope_terms:
        return 0.0

    combined_text = normalize_text(
        f"{section or ''} {text}"
    )

    matches = 0

    for term in scope_terms:
        if normalize_text(term) in combined_text:
            matches += 1

    return min(
        matches / len(scope_terms),
        1.0,
    )


def calculate_intent_match(
    intent: str,
    text: str,
    section: str | None,
) -> float:
    intent_terms = INTENT_TERMS.get(
        intent,
        set(),
    )

    if not intent_terms:
        return 0.0

    combined_text = normalize_text(
        f"{section or ''} {text}"
    )

    combined_terms = set(
        tokenize(combined_text)
    )

    matches = len(
        intent_terms & combined_terms
    )

    phrase_matches = 0

    for term in intent_terms:
        normalized_term = normalize_text(term)

        if " " in normalized_term:
            if normalized_term in combined_text:
                phrase_matches += 1

    total_matches = matches + phrase_matches

    return min(
        total_matches / len(intent_terms),
        1.0,
    )


def calculate_document_type_score(
    intent: str,
    document_type: str,
) -> float:
    preferred_types = (
        PREFERRED_DOCUMENT_TYPES.get(
            intent,
            set(),
        )
    )

    if not preferred_types:
        return 0.0

    if document_type in preferred_types:
        return 1.0

    return 0.0


def calculate_add_on_penalty(
    text: str,
    section: str | None,
    intent: str,
    query_type: str,
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
        "battery",
        "cng",
        "lpg",
    }

    matches = sum(
        1
        for term in add_on_terms
        if normalize_text(term) in combined_text
    )

    if matches >= 4:
        penalty = 1.0
    elif matches == 3:
        penalty = 0.85
    elif matches == 2:
        penalty = 0.65
    elif matches == 1:
        penalty = 0.30
    else:
        penalty = 0.0

    if query_type == "coverage":
        penalty *= 1.35

    return min(
        penalty,
        1.0,
    )


def calculate_scope_conflict(
    scope: str,
    text: str,
    section: str | None,
) -> float:
    combined_text = normalize_text(
        f"{section or ''} {text}"
    )

    if scope == "own_damage":
        conflicting_terms = {
            "third party liability",
            "section ii",
            "personal accident",
            "owner driver",
            "owner-driver",
        }

    elif scope == "third_party":
        conflicting_terms = {
            "section i",
            "own damage",
            "own-damage",
            "personal accident",
        }

    elif scope == "personal_accident":
        conflicting_terms = {
            "section i",
            "own damage",
            "own-damage",
            "section ii",
            "third party liability",
        }

    elif scope == "idv":
        conflicting_terms = {
            "third party liability",
            "personal accident",
        }

    else:
        conflicting_terms = set()

    if not conflicting_terms:
        return 0.0

    matches = sum(
        1
        for term in conflicting_terms
        if normalize_text(term) in combined_text
    )

    return min(
        matches / len(conflicting_terms),
        1.0,
    )


def calculate_query_type_score(
    query_type: str,
    text: str,
    section: str | None,
) -> float:
    combined_text = normalize_text(
        f"{section or ''} {text}"
    )

    if query_type == "coverage":
        preferred_terms = {
            "section i",
            "what is covered",
            "loss or damage",
            "accidental loss or damage",
            "we will cover",
            "we will pay",
            "indemnify",
            "covered under",
        }

    elif query_type == "exclusion":
        preferred_terms = {
            "general exceptions",
            "what is not covered",
            "not covered",
            "exceptions",
            "shall not be liable",
            "will not cover",
            "not be liable",
        }

    elif query_type == "claim_conditions":
        preferred_terms = {
            "conditions when a claim arises",
            "duties and obligations",
            "notice shall be given",
            "notice of claim",
            "immediately",
            "claim arises",
            "conditions during the contract",
        }

    else:
        return 0.0

    matches = 0

    for term in preferred_terms:
        if normalize_text(term) in combined_text:
            matches += 1

    return min(
        matches / 3,
        1.0,
    )


def calculate_base_section_bonus(
    intent: str,
    query_type: str,
    section: str | None,
) -> float:
    section_normalized = normalize_text(
        section or ""
    )

    if intent == "idv":
        if "under motor policy" in section_normalized:
            return 1.0

        if "age of the vehicle" in section_normalized:
            return 0.90

        if "total loss" in section_normalized:
            return 0.80

    if intent == "own_damage":
        if query_type == "coverage":
            if "section i" in section_normalized:
                return 1.0

            if (
                "what is covered"
                in section_normalized
            ):
                return 0.65

        if query_type == "exclusion":
            if (
                "general exceptions"
                in section_normalized
            ):
                return 1.0

            if "section i" in section_normalized:
                return 0.70

            if (
                "what is not covered"
                in section_normalized
            ):
                return 0.90

    if intent == "claim_conditions":
        if (
            "conditions when a claim arises"
            in section_normalized
        ):
            return 1.0

        if (
            "general exceptions"
            in section_normalized
        ):
            return 0.90

        if (
            "general conditions"
            in section_normalized
        ):
            return 0.85

    return 0.0


def calculate_rerank_score(
    query: str,
    candidate: dict,
    intent: str,
    scope: str,
    original_rank: int,
) -> float:
    text = candidate.get(
        "text",
        "",
    )

    section = candidate.get(
        "section"
    )

    document_type = candidate.get(
        "document_type",
        "",
    )

    query_type = detect_query_type(
        query
    )

    term_coverage = calculate_term_coverage(
        query=query,
        text=text,
    )

    phrase_match = calculate_phrase_match(
        query=query,
        text=text,
    )

    section_match = calculate_section_match(
        scope=scope,
        section=section,
    )

    scope_match = calculate_scope_match(
        scope=scope,
        text=text,
        section=section,
    )

    intent_match = calculate_intent_match(
        intent=intent,
        text=text,
        section=section,
    )

    document_type_score = (
        calculate_document_type_score(
            intent=intent,
            document_type=document_type,
        )
    )

    query_type_score = (
        calculate_query_type_score(
            query_type=query_type,
            text=text,
            section=section,
        )
    )

    base_section_bonus = (
        calculate_base_section_bonus(
            intent=intent,
            query_type=query_type,
            section=section,
        )
    )

    add_on_penalty = calculate_add_on_penalty(
        text=text,
        section=section,
        intent=intent,
        query_type=query_type,
    )

    scope_conflict = calculate_scope_conflict(
        scope=scope,
        text=text,
        section=section,
    )

    rank_score = 1 / max(
        original_rank,
        1,
    )

    return (
        term_coverage * 0.14
        + phrase_match * 0.08
        + section_match * 0.10
        + scope_match * 0.18
        + intent_match * 0.08
        + document_type_score * 0.12
        + query_type_score * 0.15
        + base_section_bonus * 0.30
        + rank_score * 0.03
        - add_on_penalty * 0.18
        - scope_conflict * 0.15
    )


def rerank_policy_chunks(
    query: str,
    candidates: list[dict],
    intent: str,
    scope: str,
    top_k: int = 5,
) -> list[dict]:
    if not query.strip():
        raise ValueError(
            "Query cannot be empty"
        )

    if not candidates:
        return []

    if top_k < 1:
        raise ValueError(
            "top_k must be at least 1"
        )

    reranked = []

    detected_intent = detect_intent(
        query
    )

    if detected_intent != "general":
        intent = detected_intent

    if intent == "idv":
        scope = "idv"

    for rank, candidate in enumerate(
        candidates,
        start=1,
    ):
        updated_candidate = {
            **candidate,
            "_rerank_score": (
                calculate_rerank_score(
                    query=query,
                    candidate=candidate,
                    intent=intent,
                    scope=scope,
                    original_rank=rank,
                )
            ),
        }

        reranked.append(
            updated_candidate
        )

    reranked.sort(
        key=lambda candidate: (
            candidate["_rerank_score"],
            candidate.get(
                "bm25_score",
                0.0,
            ),
        ),
        reverse=True,
    )

    selected = reranked[:top_k]

    for candidate in selected:
        candidate.pop(
            "_rerank_score",
            None,
        )

    return selected