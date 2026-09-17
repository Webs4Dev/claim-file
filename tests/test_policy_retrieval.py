from policy.retrieval import retrieve_policy_chunks


QUERIES = [
    "What accidental damage to the insured vehicle is covered?",
    "What exclusions apply to accidental damage?",
    "How is the Insured Declared Value (IDV) determined?",
    "What conditions must be followed when making a claim?",
]


def main():
    for query in QUERIES:
        print("\n" + "=" * 80)
        print(f"QUERY: {query}")
        print("=" * 80)

        results = retrieve_policy_chunks(
            query=query,
            product="private_car",
            top_k=5,
        )

        for index, result in enumerate(results, start=1):
            print(f"\nRESULT {index}")
            print(f"Source: {result['source']}")
            print(f"Document type: {result['document_type']}")
            print(
                f"Pages: "
                f"{result['page_start']}-{result['page_end']}"
            )
            print(f"Section: {result['section']}")
            print(f"Distance: {result['distance']}")
            print(f"\n{result['text']}")


if __name__ == "__main__":
    main()