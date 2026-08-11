import chromadb
import pytest
from docx import Document

from ingest.embedder import EMBED_DIM
from ingest.store import open_collection, stored_file_hash
from scripts.ingest_source import file_hash, ingest_directory


@pytest.fixture
def collection():
    """EphemeralClientは"ephemeral"固定キーのシステムを使い回すため、

    クリアしないとテストをまたいでデータが残る
    （tests/test_store.py と同じchromadbの既知の制約への対処）。
    """
    client = chromadb.EphemeralClient()
    yield open_collection(client)
    client.clear_system_cache()


@pytest.fixture
def source_dir(tmp_path):
    directory = tmp_path / "source"
    directory.mkdir()
    return directory


def _write_docx(directory, name, body):
    doc = Document()
    doc.add_paragraph(body)
    doc.save(directory / name)
    return directory / name


class _FakeSession:
    """埋め込みAPIの代わりに固定長のベクトルを返す。"""

    def __init__(self):
        self.calls = 0

    def post(self, url, json, timeout):
        self.calls += 1
        count = len(json["input"])
        return _FakeResponse({"embeddings": [[0.1] * EMBED_DIM for _ in range(count)]})

    def close(self):
        pass


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def test_hash_changes_with_content(source_dir):
    first = _write_docx(source_dir, "a.docx", "内容A")
    before = file_hash(first)
    _write_docx(source_dir, "a.docx", "内容Bで違う長さの本文")
    assert file_hash(first) != before


def test_hash_is_stable_for_unchanged_file(source_dir):
    path = _write_docx(source_dir, "a.docx", "内容A")
    assert file_hash(path) == file_hash(path)


def test_documents_are_indexed(source_dir, collection):
    _write_docx(source_dir, "議事録.docx", "決定事項：RAGを導入する")
    report = ingest_directory(source_dir, collection, session=_FakeSession())
    assert report.indexed == {"議事録.docx": 1}
    assert collection.count() == 1


def test_unchanged_file_is_skipped_on_second_run(source_dir, collection):
    _write_docx(source_dir, "議事録.docx", "決定事項：RAGを導入する")
    session = _FakeSession()
    ingest_directory(source_dir, collection, session=session)
    calls_after_first = session.calls

    report = ingest_directory(source_dir, collection, session=session)
    assert report.skipped == ["議事録.docx"]
    assert report.indexed == {}
    assert session.calls == calls_after_first, "スキップ時に埋め込みを呼んではいけない"


def test_changed_file_is_reindexed(source_dir, collection):
    _write_docx(source_dir, "議事録.docx", "初版の本文")
    ingest_directory(source_dir, collection, session=_FakeSession())
    _write_docx(source_dir, "議事録.docx", "改訂された本文")
    report = ingest_directory(source_dir, collection, session=_FakeSession())
    assert report.indexed == {"議事録.docx": 1}
    assert stored_file_hash(collection, "議事録.docx") == file_hash(
        source_dir / "議事録.docx"
    )


def test_force_reindexes_even_when_unchanged(source_dir, collection):
    _write_docx(source_dir, "議事録.docx", "本文")
    ingest_directory(source_dir, collection, session=_FakeSession())
    report = ingest_directory(source_dir, collection, session=_FakeSession(), force=True)
    assert report.indexed == {"議事録.docx": 1}
    assert report.skipped == []


def test_deleted_file_is_pruned(source_dir, collection):
    _write_docx(source_dir, "残す.docx", "本文")
    path = _write_docx(source_dir, "消す.docx", "本文")
    ingest_directory(source_dir, collection, session=_FakeSession())
    path.unlink()
    report = ingest_directory(source_dir, collection, session=_FakeSession())
    assert report.removed == ["消す.docx"]


def test_unsupported_files_are_ignored(source_dir, collection):
    (source_dir / "memo.txt").write_text("本文", encoding="utf-8")
    report = ingest_directory(source_dir, collection, session=_FakeSession())
    assert report.indexed == {}
    assert report.failed == {}


def test_one_broken_file_does_not_stop_the_others(source_dir, collection):
    _write_docx(source_dir, "正常.docx", "読める本文")
    (source_dir / "壊れた.docx").write_bytes(b"this is not a docx")
    report = ingest_directory(source_dir, collection, session=_FakeSession())
    assert report.indexed == {"正常.docx": 1}
    assert "壊れた.docx" in report.failed


def test_progress_is_reported_per_file(source_dir, collection):
    _write_docx(source_dir, "a.docx", "本文")
    _write_docx(source_dir, "b.docx", "本文")
    messages = []
    ingest_directory(
        source_dir, collection, session=_FakeSession(), on_progress=messages.append
    )
    assert any("a.docx" in m for m in messages)
    assert any("b.docx" in m for m in messages)
