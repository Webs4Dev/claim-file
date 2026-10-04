from tools.policy import search_policy


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

        result = search_policy(
            query=query,
            product="private_car",
        )

        print(result)


if __name__ == "__main__":
    main()