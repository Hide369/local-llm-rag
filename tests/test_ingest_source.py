import sys

import pytest
from docx import Document

from ingest.embedder import EMBED_DIM
from ingest.store import open_collection, stored_file_hash
from scripts import ingest_source
from scripts.ingest_source import _target_files, file_hash, ingest_directory
from tests.conftest import ephemeral_client


@pytest.fixture
def collection():
    """EphemeralClientは"ephemeral"固定キーのシステムを使い回すため、

    クリアしないとテストをまたいでデータが残る
    （tests/test_store.py と同じchromadbの既知の制約への対処）。
    """
    client = ephemeral_client()
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


def _write_md(directory, name, text):
    path = directory / name
    path.write_text(text, encoding="utf-8")
    return path


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
    _write_docx(source_dir, "議事録.docx", "初版として作成した本文がここに入っています。")
    ingest_directory(source_dir, collection, session=_FakeSession())
    _write_docx(source_dir, "議事録.docx", "内容を修正した本文がここに新しく入っています。")
    report = ingest_directory(source_dir, collection, session=_FakeSession())
    assert report.indexed == {"議事録.docx": 1}
    assert stored_file_hash(collection, "議事録.docx") == file_hash(
        source_dir / "議事録.docx"
    )


def test_force_reindexes_even_when_unchanged(source_dir, collection):
    _write_docx(source_dir, "議事録.docx", "強制再取り込みの確認に使う本文です。")
    ingest_directory(source_dir, collection, session=_FakeSession())
    report = ingest_directory(source_dir, collection, session=_FakeSession(), force=True)
    assert report.indexed == {"議事録.docx": 1}
    assert report.skipped == []


def test_deleted_file_is_pruned(source_dir, collection):
    _write_docx(source_dir, "残す.docx", "この資料は削除テストで残す側の本文です。")
    path = _write_docx(source_dir, "消す.docx", "この資料は削除テストで消す側の本文です。")
    ingest_directory(source_dir, collection, session=_FakeSession())
    path.unlink()
    report = ingest_directory(source_dir, collection, session=_FakeSession())
    assert report.removed == ["消す.docx"]


def test_unsupported_files_are_ignored(source_dir, collection):
    (source_dir / "memo.txt").write_text("本文", encoding="utf-8")
    report = ingest_directory(source_dir, collection, session=_FakeSession())
    assert report.indexed == {}
    assert report.failed == {}


def test_office_lock_files_are_not_picked_up(source_dir):
    """Officeが編集中に作る ~$ 始まりの一時ファイルは、対応拡張子でも対象外にする。

    実際に source/ に ~$生成AI活用セミナー.pptx が存在し、放置すると
    PermissionError で取り込み全体が失敗扱いになる。"""
    _write_docx(source_dir, "議事録.docx", "本文")
    (source_dir / "~$議事録.docx").write_bytes(b"lock file placeholder")
    files = _target_files(source_dir)
    assert [path.name for path in files] == ["議事録.docx"]


def test_one_broken_file_does_not_stop_the_others(source_dir, collection):
    _write_docx(source_dir, "正常.docx", "これは正常に読み込める本文です。")
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


def test_files_in_subdirectories_are_indexed(source_dir, collection):
    """資料を分類して置けるようにする。iterdir のままでは中身に到達しない。"""
    sub = source_dir / "家電製品"
    sub.mkdir()
    _write_docx(sub, "仕様.docx", "この製品の仕様書の本文がここにあります。")
    report = ingest_directory(source_dir, collection, session=_FakeSession())
    assert report.indexed == {"家電製品/仕様.docx": 1}


def test_top_level_identifier_stays_the_bare_filename(source_dir, collection):
    """既存279チャンクを再取り込みさせないための保証。

    相対パスは直下のファイルではファイル名と一致するため、識別子は変わらない。
    """
    _write_docx(source_dir, "議事録.docx", "決定事項：RAGを導入するという結論です。")
    report = ingest_directory(source_dir, collection, session=_FakeSession())
    assert report.indexed == {"議事録.docx": 1}
    assert stored_file_hash(collection, "議事録.docx") is not None


def test_subdirectory_files_are_not_pruned_as_orphans(source_dir, collection):
    """孤児判定を相対パスに揃え忘れると、毎回削除と再取り込みを繰り返す。"""
    sub = source_dir / "家電製品"
    sub.mkdir()
    _write_docx(sub, "仕様.docx", "この製品の仕様書の本文がここにあります。")
    ingest_directory(source_dir, collection, session=_FakeSession())
    report = ingest_directory(source_dir, collection, session=_FakeSession())
    assert report.removed == []
    assert report.skipped == ["家電製品/仕様.docx"]


def test_markdown_file_in_subdirectory_is_indexed_with_section_metadata(source_dir, collection):
    """docxしか通していなかった構成（サブフォルダ×相対パスsource×sectionチャンクID×
    heading メタデータ）をMarkdownで一気通貫に確認する。"""
    sub = source_dir / "家電製品"
    sub.mkdir()
    text = (
        "---\n"
        "model_id: UD-0900i\n"
        "---\n\n"
        "# UD-0900i IoTコンパクト\n\n"
        "## 機種概要\n\n"
        "打田電器のUD-0900iは、洗濯容量9キログラムのコンパクトなIoTモデルです。\n\n"
        "## 設置情報\n\n"
        "外形寸法は幅598ミリメートル、奥行き700ミリメートルです。\n"
    )
    _write_md(sub, "spec.md", text)

    report = ingest_directory(source_dir, collection, session=_FakeSession())

    source = "家電製品/spec.md"
    assert report.indexed == {source: 2}

    stored = collection.get(where={"source": source}, include=["metadatas"])
    assert set(stored["ids"]) == {f"{source}::section1::0", f"{source}::section2::0"}
    headings_by_id = {
        chunk_id: metadata["heading"]
        for chunk_id, metadata in zip(stored["ids"], stored["metadatas"])
    }
    assert headings_by_id[f"{source}::section1::0"] == "機種概要"
    assert headings_by_id[f"{source}::section2::0"] == "設置情報"


def test_same_filename_in_two_folders_does_not_collide(source_dir, collection):
    """ファイル名だけを識別子にすると、片方がもう片方を上書きしてしまう。"""
    for folder in ("A", "B"):
        directory = source_dir / folder
        directory.mkdir()
        _write_docx(directory, "仕様.docx", f"{folder}フォルダの仕様書の本文です。")
    report = ingest_directory(source_dir, collection, session=_FakeSession())
    assert set(report.indexed) == {"A/仕様.docx", "B/仕様.docx"}
    assert collection.count() == 2


def test_only_suffix_limits_the_files(source_dir, collection):
    _write_docx(source_dir, "議事録.docx", "決定事項：RAGを導入するという結論です。")
    _write_md(source_dir, "仕様.md", "# 製品\n\n## 節\n\n本文がここにあります。\n")
    report = ingest_directory(
        source_dir, collection, session=_FakeSession(), only_suffix=".md"
    )
    assert set(report.indexed) == {"仕様.md"}


def test_only_suffix_accepts_a_bare_extension(source_dir, collection):
    """--only-suffix md と .md を同じに扱う。書き分けを覚える理由がない。"""
    _write_md(source_dir, "仕様.md", "# 製品\n\n## 節\n\n本文がここにあります。\n")
    report = ingest_directory(
        source_dir, collection, session=_FakeSession(), only_suffix="md"
    )
    assert set(report.indexed) == {"仕様.md"}


def test_only_suffix_skips_orphan_pruning(source_dir, collection):
    """ここを飛ばさないと、対象外の拡張子の資料が全部孤児として消える。"""
    _write_docx(source_dir, "議事録.docx", "決定事項：RAGを導入するという結論です。")
    _write_md(source_dir, "仕様.md", "# 製品\n\n## 節\n\n本文がここにあります。\n")
    ingest_directory(source_dir, collection, session=_FakeSession())
    report = ingest_directory(
        source_dir, collection, session=_FakeSession(), force=True, only_suffix=".md"
    )
    assert report.removed == []
    assert stored_file_hash(collection, "議事録.docx") is not None


def test_full_run_still_prunes_orphans(source_dir, collection):
    """部分取り込みの分岐を入れても、通常の取り込みの孤児削除は残っていること。"""
    path = _write_docx(source_dir, "議事録.docx", "決定事項：RAGを導入するという結論です。")
    ingest_directory(source_dir, collection, session=_FakeSession())
    path.unlink()
    report = ingest_directory(source_dir, collection, session=_FakeSession())
    assert report.removed == ["議事録.docx"]


class _FakeCollectionForMain:
    def count(self):
        return 0


def test_main_forwards_force_flag_to_ingest_directory(tmp_path, monkeypatch):
    """argparseが--forceを受け取っても、main()がingest_directoryへ渡さなければ
    死んだフラグになる。Trueだけを確認するとforce=True決め打ちの実装でも通って
    しまうため、--force省略時にFalseが渡ることも合わせて検証する。
    実DBにもOllamaにも触れないよう、main()が呼ぶものはすべてスタブに差し替える。
    """
    source_dir = tmp_path / "source"
    source_dir.mkdir()

    received_force = []

    def _fake_ingest_directory(*_args, **kwargs):
        received_force.append(kwargs.get("force"))
        return ingest_source.IngestReport()

    monkeypatch.setattr(ingest_source, "ingest_directory", _fake_ingest_directory)
    monkeypatch.setattr(ingest_source.embedder, "check_ollama", lambda: None)
    monkeypatch.setattr(
        ingest_source.chromadb, "PersistentClient", lambda path: object()
    )
    monkeypatch.setattr(
        ingest_source.store, "open_collection", lambda client: _FakeCollectionForMain()
    )

    monkeypatch.setattr(
        sys, "argv", ["ingest_source.py", "--source-dir", str(source_dir), "--force"]
    )
    ingest_source.main()

    monkeypatch.setattr(
        sys, "argv", ["ingest_source.py", "--source-dir", str(source_dir)]
    )
    ingest_source.main()

    assert received_force == [True, False]


def test_main_forwards_only_suffix_to_ingest_directory(monkeypatch, tmp_path):
    captured = {}

    def fake_ingest_directory(source_dir, collection, on_progress=None, **kwargs):
        captured.update(kwargs)
        return ingest_source.IngestReport()

    monkeypatch.setattr(ingest_source, "ingest_directory", fake_ingest_directory)
    monkeypatch.setattr(ingest_source.embedder, "check_ollama", lambda: None)
    monkeypatch.setattr(
        ingest_source.store, "open_collection", lambda _client: _FakeCollectionForMain()
    )
    monkeypatch.setattr(ingest_source.chromadb, "PersistentClient", lambda path: None)
    monkeypatch.setattr(
        sys, "argv", ["ingest_source", "--source-dir", str(tmp_path), "--only-suffix", "md"]
    )
    ingest_source.main()
    assert captured["only_suffix"] == "md"
