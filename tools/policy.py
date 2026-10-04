import json

from policy.retrieval import retrieve_policy_chunks


def search_policy(
    query: str,
    product: str,
) -> str:
    results = retrieve_policy_chunks(
        query=query,
        product=product,
        top_k=3,
    )

    formatted_results = []

    for index, result in enumerate(
        results,
        start=1,
    ):
        formatted_results.append(
            {
                "result_number": index,
                "source": result["source"],
                "product": result["product"],
                "document_type": result["document_type"],
                "page_start": result["page_start"],
                "page_end": result["page_end"],
                "section": result["section"],
                "text": result["text"],
            }
        )

    return json.dumps(
        formatted_results,
        ensure_ascii=False,
    )


POLICY_SEARCH_TOOL = {
    "type": "function",
    "name": "search_policy",
    "description": (
        "Search the configured motor insurance policy knowledge base "
        "for authoritative policy evidence. "
        "The knowledge base contains the policy documents applicable "
        "to this ClaimFile deployment. "
        "Use this tool only when a specific policy question needs "
        "verification. "
        "Ask one focused policy question per search. "
        "Prioritize the most important unresolved policy issue. "
        "Do not rely on general insurance knowledge when policy "
        "evidence can be retrieved from this tool."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "One specific policy question that needs to be "
                    "verified. Include the relevant claim issue, "
                    "coverage, exclusion, condition, or rule."
                ),
            },
            "product": {
                "type": "string",
                "description": (
                    "The motor insurance product whose policy "
                    "documents are stored in the configured "
                    "knowledge base."
                ),
            },
        },
        "required": [
            "query",
            "product",
        ],
        "additionalProperties": False,
    },
}