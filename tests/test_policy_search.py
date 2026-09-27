from policy.retrieval import retrieve_policy_chunks


QUERY = (
    "Does the private car policy provide accidental "
    "own damage coverage for an accident?"
)


results = retrieve_policy_chunks(
    query=QUERY,
    product="private_car",
    top_k=10,
)


print("=" * 70)
print("POLICY SEARCH RESULTS")
print("=" * 70)

for index, result in enumerate(results, start=1):
    print()
    print(f"RESULT {index}")
    print("-" * 70)
    print("SOURCE:", result["source"])
    print("DOCUMENT TYPE:", result["document_type"])
    print("PAGE:", result["page_start"], "-", result["page_end"])
    print("SECTION:", result["section"])
    print("DISTANCE:", result["distance"])
    print()
    print(result["text"])