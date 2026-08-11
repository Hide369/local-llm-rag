import chromadb
import pytest

from ingest.embedder import EMBED_DIM
from ingest.models import Chunk
from ingest.store import (
    COLLECTION_NAME,
    DISTANCE_SPACE,
    delete_orphans,
    indexed_sources,
    open_collection,
    replace_source,
    stored_file_hash,
)


@pytest.fixture
def collection():
    """ディスクに触れないインメモリのChromaを使う。

    EphemeralClientは同一プロセス内で "ephemeral" という固定キーのシステムを
    使い回す（chromadb側の既知の制約）ため、そのままではテストをまたいで前の
    データが残ってしまう。chromadb自身のテストスイートに倣い、テストごとに
    system cacheをクリアして完全に独立させる。
    """
    client = chromadb.EphemeralClient()
    yield open_collection(client)
    client.clear_system_cache()


def _chunks(source, file_hash, count=2):
    return [
        Chunk(
            id=f"{source}::page{i}::0",
            text=f"{source}の{i}ページ目",
            metadata={
                "source": source,
                "file_hash": file_hash,
                "location_type": "page",
                "location": i,
                "ocr": False,
                "chunk_index": 0,
                "indexed_at": "2026-08-11",
            },
        )
        for i in range(1, count + 1)
    ]


def _vectors(count):
    return [[0.1] * EMBED_DIM for _ in range(count)]


def _add(collection, source, file_hash, count=2):
    chunks = _chunks(source, file_hash, count)
    replace_source(collection, source, chunks, _vectors(len(chunks)))
    return chunks


def test_collection_name_does_not_collide_with_the_course_collection():
    """local_docs は udemy3.py が768次元で使い続けるため触らない。"""
    assert COLLECTION_NAME == "local_docs_v2"


def test_collection_uses_cosine(collection):
    config = getattr(collection, "configuration_json", None) or {}
    assert (config.get("hnsw") or {}).get("space") == DISTANCE_SPACE == "cosine"


def test_stored_hash_is_none_for_unknown_source(collection):
    assert stored_file_hash(collection, "未登録.pdf") is None


def test_stored_hash_is_returned_after_adding(collection):
    _add(collection, "a.pdf", "hash1")
    assert stored_file_hash(collection, "a.pdf") == "hash1"


def test_replacing_a_source_removes_its_old_chunks(collection):
    _add(collection, "a.pdf", "hash1", count=5)
    _add(collection, "a.pdf", "hash2", count=2)
    assert collection.count() == 2
    assert stored_file_hash(collection, "a.pdf") == "hash2"


def test_replacing_a_source_leaves_other_sources_intact(collection):
    _add(collection, "a.pdf", "hash1", count=3)
    _add(collection, "b.pptx", "hash2", count=2)
    _add(collection, "a.pdf", "hash3", count=1)
    assert collection.count() == 3
    assert stored_file_hash(collection, "b.pptx") == "hash2"


def test_indexed_sources_lists_every_source(collection):
    _add(collection, "a.pdf", "hash1")
    _add(collection, "b.pptx", "hash2")
    assert indexed_sources(collection) == {"a.pdf", "b.pptx"}


def test_orphans_are_deleted(collection):
    """source/ から資料を消したら、DB側も追従しないと幽霊の出典が出る。"""
    _add(collection, "a.pdf", "hash1")
    _add(collection, "消した.pptx", "hash2")
    removed = delete_orphans(collection, known_sources={"a.pdf"})
    assert removed == ["消した.pptx"]
    assert indexed_sources(collection) == {"a.pdf"}


def test_nothing_is_deleted_when_all_sources_are_known(collection):
    _add(collection, "a.pdf", "hash1")
    assert delete_orphans(collection, known_sources={"a.pdf"}) == []
    assert collection.count() == 2


def test_metadata_survives_a_round_trip(collection):
    _add(collection, "a.pdf", "hash1", count=1)
    stored = collection.get(include=["metadatas"])["metadatas"][0]
    assert stored["location"] == 1
    assert stored["location_type"] == "page"
    assert stored["ocr"] is False
