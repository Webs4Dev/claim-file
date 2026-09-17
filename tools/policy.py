import json

from policy.retrieval import retrieve_policy_chunks


def search_tata_aig_policy(
    query: str,
    product: str,
) -> str:
    results = retrieve_policy_chunks(
        query=query,
        product=product,
        top_k=5,
    )

    return json.dumps(
        results,
        ensure_ascii=False,
    )


POLICY_SEARCH_TOOL = {
    "type": "function",
    "name": "search_tata_aig_policy",
    "description": (
        "Search the Tata AIG policy knowledge base for relevant "
        "policy wording, coverage, exclusions, conditions, "
        "definitions, or other policy rules. Use this tool when "
        "policy evidence is needed to investigate a claim. "
        "Do not treat general insurance knowledge as policy evidence."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "The specific policy question or information "
                    "that needs to be verified."
                ),
            },
            "product": {
                "type": "string",
                "description": (
                    "The Tata AIG motor insurance product whose "
                    "policy should be searched, for example "
                    "'private_car'."
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