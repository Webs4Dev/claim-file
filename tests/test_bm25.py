from policy.bm25 import search_bm25


QUERIES = [
    "What accidental damage to the insured vehicle is covered?",
    "What exclusions apply to accidental damage?",
    "How is the Insured Declared Value determined?",
]


def main():
    for query in QUERIES:
        print("\n" + "=" * 80)
        print(f"QUERY: {query}")
        print("=" * 80)

        results = search_bm25(
            query=query,
            product="private_car",
            top_k=10,
        )

        for index, result in enumerate(
            results,
            start=1,
        ):
            print(f"\nRESULT {index}")
            print(
                f"BM25 score: "
                f"{result['bm25_score']:.6f}"
            )
            print(
                f"Source: "
                f"{result['source']}"
            )
            print(
                f"Pages: "
                f"{result['page_start']}-"
                f"{result['page_end']}"
            )
            print(
                f"Section: "
                f"{result['section']}"
            )
            print(
                f"Text: "
                f"{result['text'][:500]}"
            )


if __name__ == "__main__":
    main()