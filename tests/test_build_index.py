"""Policy index rebuilds must never leave the live index broken.

Uses an in-memory Chroma client, a temporary BM25 folder and fake
embeddings, so no OpenAI calls are made and the real index is untouched.
"""

import json

import chromadb
import pytest

import policy.bm25 as bm25
import policy.index as index
import scripts.build_index as build
from policy.ingestion import PolicyChunk

PRODUCT = "private_car"


@pytest.fixture
def stores(monkeypatch, tmp_path):
    client = chromadb.EphemeralClient()
    for collection in client.list_collections():
        client.delete_collection(name=collection.name)

    monkeypatch.setattr(index, "embedding_client", client)
    monkeypatch.setattr(bm25, "INDEX_PATH", tmp_path)
    monkeypatch.setattr(
        index, "create_embeddings", lambda texts: [[0.1, 0.2, 0.3] for _ in texts]
    )

    # The "old" live index: one chunk in Chroma, one marker in BM25.
    live = client.create_collection(name=index.get_collection_name(PRODUCT))
    live.add(ids=["old"], embeddings=[[0.0, 0.0, 1.0]], documents=["old text"])
    bm25.get_index_path(PRODUCT).write_text('{"marker": "old"}')

    return client


def fake_chunks(document_type: str) -> list[PolicyChunk]:
    return [
        PolicyChunk(
            chunk_id=f"{document_type}-{number}",
            source=f"{document_type}.pdf",
            product=PRODUCT,
            document_type=document_type,
            page_start=1,
            page_end=1,
            section="Section I",
            text=f"Own damage cover text {number}",
        )
        for number in range(3)
    ]


def test_failed_rebuild_keeps_the_live_index(stores, monkeypatch):
    def ingest(path, product, document_type):
        if document_type == "idv_tl_ctl_criteria":
            raise RuntimeError("embedding API down")
        return fake_chunks(document_type)

    monkeypatch.setattr(build, "ingest_policy", ingest)

    with pytest.raises(RuntimeError):
        build.build_index()

    live = stores.get_collection(name=index.get_collection_name(PRODUCT))
    assert live.get()["ids"] == ["old"]
    assert json.loads(bm25.get_index_path(PRODUCT).read_text()) == {"marker": "old"}


def test_successful_rebuild_replaces_the_live_index(stores, monkeypatch):
    monkeypatch.setattr(
        build,
        "ingest_policy",
        lambda path, product, document_type: fake_chunks(document_type),
    )

    build.build_index()

    live = stores.get_collection(name=index.get_collection_name(PRODUCT))
    assert live.count() == 6
    assert "old" not in live.get()["ids"]
    assert [c.name for c in stores.list_collections()] == [
        index.get_collection_name(PRODUCT)
    ]

    data = json.loads(bm25.get_index_path(PRODUCT).read_text())
    assert len(data["documents"]) == 6
    assert not list(bm25.INDEX_PATH.glob("*.staging.json"))


def test_rebuild_after_a_failed_run_discards_leftover_staging(stores, monkeypatch):
    stale = stores.create_collection(name=index.get_staging_collection_name(PRODUCT))
    stale.add(ids=["stale"], embeddings=[[1.0, 0.0, 0.0]], documents=["stale"])
    monkeypatch.setattr(
        build,
        "ingest_policy",
        lambda path, product, document_type: fake_chunks(document_type),
    )

    build.build_index()

    live = stores.get_collection(name=index.get_collection_name(PRODUCT))
    assert "stale" not in live.get()["ids"]
