"""Retrieval checks for the policy knowledge base.

Run from the project root:

    venv/bin/python -m tests.eval_policy_retrieval

Exits non-zero if any check fails. The live checks make a few embedding
calls, so OPENAI_API_KEY must be set and the index must be built.
"""

import json
import sys
from types import SimpleNamespace

from agents.investigator import build_policy_search_queries
from policy.ingestion import ingest_policy
from scripts.build_index import POLICIES
from tools.policy import search_policy


PRODUCT = "private_car"

FOOTER_MARKERS = [
    "Registered office:",
    "Customer Support No.:",
    "IRDA of India Registration No.:",
]

# claim_001 as submitted through the claim form (tests/test_pipeline.py).
CLAIM_001 = SimpleNamespace(
    extracted_data=SimpleNamespace(
        accident=SimpleNamespace(description=None),
        damage=SimpleNamespace(description=None),
        driver=SimpleNamespace(condition_at_accident=None),
    ),
    claim_form=SimpleNamespace(
        accident_description="Vehicle accident resulting in damage.",
        damage_description=(
            "Front bumper, bonnet, left headlight "
            "and radiator grille damaged."
        ),
    ),
)

IDV_QUERY = "How is the Insured Declared Value (IDV) determined?"

failures = []


def check(name: str, passed: bool) -> None:
    print(f"  [{'PASS' if passed else 'FAIL'}] {name}")

    if not passed:
        failures.append(name)


def any_text_contains(results: list[dict], phrase: str) -> bool:
    phrase = phrase.lower()

    return any(
        phrase in f"{result['section'] or ''} {result['text']}".lower()
        for result in results
    )


def print_results(results: list[dict]) -> None:
    for result in results:
        preview = " ".join(result["text"].split())[:140]
        print(
            f"    p{result['page_start']} "
            f"[{result['section']}] {preview}"
        )


def run_offline_checks() -> None:
    print("\nOFFLINE: chunking")

    chunks = []

    for policy in POLICIES:
        chunks.extend(
            ingest_policy(
                path=policy["path"],
                product=policy["product"],
                document_type=policy["document_type"],
            )
        )

    lengths = [len(chunk.text) for chunk in chunks]
    print(
        f"  {len(chunks)} chunks, min {min(lengths)}, "
        f"median {sorted(lengths)[len(lengths) // 2]}, "
        f"max {max(lengths)} chars"
    )

    check(
        "no chunk under 100 chars",
        min(lengths) >= 100,
    )

    check(
        "no footer boilerplate in chunks",
        not any(
            line.startswith(marker)
            for chunk in chunks
            for line in chunk.text.splitlines()
            for marker in FOOTER_MARKERS
        ),
    )

    peril_chunks = [
        chunk
        for chunk in chunks
        if "accidental external means" in chunk.text
    ]

    check(
        "perils list is labelled as Section I",
        any(
            "Section I " in (chunk.section or "") + " "
            for chunk in peril_chunks
        ),
    )


def run_live_checks() -> None:
    coverage, exclusions, deductible = build_policy_search_queries(
        CLAIM_001
    )

    cases = [
        ("coverage", coverage, "accidental external means"),
        ("exclusions", exclusions, "general exceptions"),
        ("deductible", deductible, "deductible"),
    ]

    for name, query, phrase in cases:
        print(f"\nLIVE: {name} query")
        results = json.loads(search_policy(query, PRODUCT))
        print_results(results)
        check(f"{name} returns '{phrase}'", any_text_contains(results, phrase))

    print("\nLIVE: IDV query")
    results = json.loads(search_policy(IDV_QUERY, PRODUCT))
    print_results(results)
    check(
        "IDV returns idv_tl_ctl_criteria",
        any(
            result["document_type"] == "idv_tl_ctl_criteria"
            for result in results
        ),
    )


if __name__ == "__main__":
    run_offline_checks()
    run_live_checks()

    print()

    if failures:
        print(f"{len(failures)} check(s) failed.")
        sys.exit(1)

    print("All checks passed.")
