import json

from policy.retrieval import retrieve_policy_chunks


def search_tata_aig_policy(
    query: str,
    product: str,
) -> str:
    results = retrieve_policy_chunks(
        query=query,
        product=product,
        top_k=3,
    )

    formatted_results = []

    for index, result in enumerate(results, start=1):
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
                "distance": result["distance"],
            }
        )

    return json.dumps(
        formatted_results,
        ensure_ascii=False,
    )


POLICY_SEARCH_TOOL = {
    "type": "function",
    "name": "search_tata_aig_policy",
    "description": (
        "Search the Tata AIG motor insurance policy knowledge base "
        "for authoritative policy evidence. "
        "Use this tool only when a specific policy question needs "
        "verification. "
        "Ask one focused policy question per search. "
        "Prioritize the most important unresolved policy issue. "
        "The tool returns the most relevant policy evidence. "
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
                    "The Tata AIG motor insurance product to search. "
                    "Use 'private_car' for Tata AIG Private Car "
                    "policies."
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