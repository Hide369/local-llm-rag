import sys

import pytest
from docx import Document

from ingest import store
from ingest.embedder import EMBED_DIM
from ingest.store import open_store, stored_file_hash
from scripts import ingest_source
from scripts.ingest_source import _target_files, file_hash, ingest_directory


@pytest.fixture
def collection():
    """インメモリのストア。ディスクには触れない。"""
    return open_store(":memory:")


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
    # 未対応の拡張子は _target_files が拾わない。対応形式が増えても
    # 意味が残るよう、テキストを取り出せない形式を使う。
    (source_dir / "資料.zip").write_bytes(b"PK")
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

    def chunk_count(self):
        return 0

    def integrity(self):
        return (0, 0)


class _FakeHealthyCollection:
    """件数があり、開き直した検索もベクトルを返す健全なストア。"""

    def count(self):
        return 3

    def chunk_count(self):
        return 3

    def search(self, vector, limit):
        return [("hash-a", 0.1, "本文", [{"source": "a.md"}])]

    def integrity(self):
        return (0, 0)


class _FakeSilentlyBrokenCollection:
    """件数は正しいのにベクトルが引けないストア。ChromaDBの破損はこの形だった。"""

    def count(self):
        return 3

    def chunk_count(self):
        return 3

    def search(self, vector, limit):
        return []

    def integrity(self):
        return (0, 0)


class _FakeOrphanedCollection:
    """出現の無い本文が残っているストア。

    孤児はベクトル行列に載り続けるが、出現が引けないため結果からは落ちる。
    上位の枠だけ取って消えるので、本物のヒットを黙って押し出す。count() は
    出現を数えるので孤児は表れず、件数と検索が両方とも正常に見える。
    整合性を数えない限り露見しない。
    """

    def count(self):
        return 3

    def chunk_count(self):
        return 4

    def search(self, vector, limit):
        return [("hash-a", 0.1, "本文", [{"source": "a.md"}])]

    def integrity(self):
        return (1, 0)


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
        ingest_source.store, "open_store", lambda path: _FakeCollectionForMain()
    )

    monkeypatch.setattr(
        sys, "argv", ["ingest_source.py", "--source-dir", str(source_dir), "--force"]
    )
    assert ingest_source.main() == 0

    monkeypatch.setattr(
        sys, "argv", ["ingest_source.py", "--source-dir", str(source_dir)]
    )
    assert ingest_source.main() == 0

    assert received_force == [True, False]


def test_main_forwards_only_suffix_to_ingest_directory(monkeypatch, tmp_path):
    captured = {}

    def fake_ingest_directory(source_dir, collection, on_progress=None, **kwargs):
        captured.update(kwargs)
        return ingest_source.IngestReport()

    monkeypatch.setattr(ingest_source, "ingest_directory", fake_ingest_directory)
    monkeypatch.setattr(ingest_source.embedder, "check_ollama", lambda: None)
    monkeypatch.setattr(
        ingest_source.store, "open_store", lambda path: _FakeCollectionForMain()
    )
    monkeypatch.setattr(
        sys, "argv", ["ingest_source", "--source-dir", str(tmp_path), "--only-suffix", "md"]
    )
    assert ingest_source.main() == 0
    assert captured["only_suffix"] == "md"


def test_main_opens_the_shared_store_path(monkeypatch, tmp_path):
    """開く先を間違えても open_store は空のDBを黙って作り、件数0で検索が全部
    空になるだけで例外は出ない。パスの出どころを1件だけ拘束しておく。"""
    opened = []

    monkeypatch.setattr(
        ingest_source, "ingest_directory", lambda *a, **k: ingest_source.IngestReport()
    )
    monkeypatch.setattr(ingest_source.embedder, "check_ollama", lambda: None)
    monkeypatch.setattr(
        ingest_source.store,
        "open_store",
        lambda path: (opened.append(path), _FakeCollectionForMain())[1],
    )
    monkeypatch.setattr(sys, "argv", ["ingest_source", "--source-dir", str(tmp_path)])
    assert ingest_source.main() == 0

    # 取り込み用と、取り込み後に開き直す検証用の2回。どちらも同じパスであること。
    assert opened == [str(store.DB_PATH), str(store.DB_PATH)]


def test_main_prints_the_resolved_absolute_db_path(monkeypatch, tmp_path, capsys):
    """--db に相対パスを渡しても、画面には解決済みの絶対パスを出す。

    open_store はパスを間違えても例外を出さず空のDBを新規作成する
    （ingest/store.py）。相対パスのまま表示すると、実行時のカレント
    ディレクトリが違うだけで実際には別のファイルを開いていても表示上は
    同じ文字列になり、「どこを開いたか見せる」というこのprintの目的が
    果たせない。
    """
    monkeypatch.chdir(tmp_path)
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    monkeypatch.setattr(
        ingest_source, "ingest_directory", lambda *a, **k: ingest_source.IngestReport()
    )
    monkeypatch.setattr(ingest_source.embedder, "check_ollama", lambda: None)
    monkeypatch.setattr(
        ingest_source.store, "open_store", lambda path: _FakeCollectionForMain()
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "ingest_source",
            "--source-dir",
            str(source_dir),
            "--db",
            "relative.sqlite3",
        ],
    )

    assert ingest_source.main() == 0

    expected = str((tmp_path / "relative.sqlite3").resolve())
    assert f"取り込み先: {expected}" in capsys.readouterr().out


def _run_main_with(monkeypatch, tmp_path, collection):
    """main() が触る外部をすべてスタブし、渡したストアだけを見せて実行する。"""
    monkeypatch.setattr(
        ingest_source, "ingest_directory", lambda *a, **k: ingest_source.IngestReport()
    )
    monkeypatch.setattr(ingest_source.embedder, "check_ollama", lambda: None)
    monkeypatch.setattr(ingest_source.store, "open_store", lambda path: collection)
    monkeypatch.setattr(sys, "argv", ["ingest_source", "--source-dir", str(tmp_path)])
    return ingest_source.main()


def test_a_store_that_counts_rows_but_finds_none_fails_the_run(
    monkeypatch, tmp_path, capsys
):
    """取り込めたことと、開き直して読めることは別の事実である。

    ChromaDBでは前者だけが成立した。件数は最後まで正しく返っていたため、
    ベクトルが失われたことが次回起動まで露見しなかった。件数だけを見る検証では
    まさにその障害を見逃すので、検索まで通してベクトルの層に触る。
    """
    assert _run_main_with(monkeypatch, tmp_path, _FakeSilentlyBrokenCollection()) == 1
    assert "検証に失敗" in capsys.readouterr().out


def test_ingest_fails_when_a_text_has_no_occurrence(monkeypatch, tmp_path, capsys):
    """帳簿が2つに分かれたぶん、片方だけが残る壊れ方が新しく生まれる。

    孤児の本文は検索に出続けるのに、count() も search() も正常に見える。
    次に開くまで露見しなかったChromaDBの破損と同じ形なので、ここで止める。
    """
    assert _run_main_with(monkeypatch, tmp_path, _FakeOrphanedCollection()) == 1
    assert "整合性" in capsys.readouterr().out


def test_a_healthy_store_finishes_successfully(monkeypatch, tmp_path):
    """検証を足したせいで正常な取り込みまで失敗になっては本末転倒である。"""
    assert _run_main_with(monkeypatch, tmp_path, _FakeHealthyCollection()) == 0


def test_main_prints_the_navigation_summary_lines(monkeypatch, tmp_path, capsys):
    """CLI要約のナビゲーション関連の2行はformat_report()を経由せずmain()が
    直接printしている。ここを直接見るテストが無いと、main()を触ったときに
    無言でこの2行が消えても誰も気づけない（ingest/prompting.pyのformat_report()を
    見るtest_prompting.pyのテストはCLI側の出力を検証しない）。
    """
    def fake_ingest_directory(*_args, **_kwargs):
        report = ingest_source.IngestReport()
        report.dropped = {"a.pptx": 4}
        report.kept_all_navigation = ["nav_only.pptx"]
        return report

    monkeypatch.setattr(ingest_source, "ingest_directory", fake_ingest_directory)
    monkeypatch.setattr(ingest_source.embedder, "check_ollama", lambda: None)
    monkeypatch.setattr(
        ingest_source.store, "open_store", lambda path: _FakeHealthyCollection()
    )
    monkeypatch.setattr(sys, "argv", ["ingest_source", "--source-dir", str(tmp_path)])

    assert ingest_source.main() == 0
    out = capsys.readouterr().out
    assert "ナビゲーション除外: 4件 / 1ファイル" in out
    assert (
        "全ユニットがナビゲーション判定のため除外しませんでした: nav_only.pptx" in out
    )


def test_integrity_detects_orphaned_chunks(collection):
    """integrity() は出現を持たない本文を見つける。"""
    # 本文を追加
    from ingest.embedder import EMBED_DIM
    collection.add(
        ids=["test-id"],
        documents=["テスト本文"],
        metadatas=[{"source": "test.md"}],
        embeddings=[[0.1] * EMBED_DIM],
    )
    # 正常な状態を確認
    assert collection.integrity() == (0, 0)

    # 外部キー制約を一時的に無効にして、出現だけを削除（孤児を作る）
    collection._connection.execute("PRAGMA foreign_keys = OFF")
    try:
        collection._connection.execute("DELETE FROM occurrences WHERE source = ?", ("test.md",))
        collection._connection.commit()
        # 孤児がいることを確認
        orphans, dangling = collection.integrity()
        assert orphans == 1
    finally:
        collection._connection.execute("PRAGMA foreign_keys = ON")


def test_integrity_detects_dangling_occurrences(collection):
    """integrity() は本文を持たない出現を見つける。"""
    from ingest.embedder import EMBED_DIM

    # 健全な状態を確認
    assert collection.integrity() == (0, 0)

    # 本文と出現を追加
    collection.add(
        ids=["test-id"],
        documents=["テスト本文"],
        metadatas=[{"source": "test.md"}],
        embeddings=[[0.1] * EMBED_DIM],
    )
    assert collection.integrity() == (0, 0)

    # 外部キー制約を一時的に無効にして、本文だけを削除
    collection._connection.execute("PRAGMA foreign_keys = OFF")
    try:
        collection._connection.execute("DELETE FROM chunks")
        collection._connection.commit()
        # 本文の無い出現が検出される
        orphans, dangling = collection.integrity()
        assert dangling == 1
    finally:
        collection._connection.execute("PRAGMA foreign_keys = ON")


def test_integrity_returns_healthy_for_valid_store(collection):
    """integrity() は健全な状態で (0, 0) を返す。"""
    from ingest.embedder import EMBED_DIM

    assert collection.integrity() == (0, 0)

    # データを追加しても健全
    collection.add(
        ids=["id1", "id2"],
        documents=["本文1", "本文2"],
        metadatas=[{"source": "a.md"}, {"source": "b.md"}],
        embeddings=[[0.1] * EMBED_DIM, [0.2] * EMBED_DIM],
    )
    assert collection.integrity() == (0, 0)


_NAV_SECTION = "## 1\n\n転移学習とファインチューニング\n"


def test_ingest_drops_a_navigation_section_and_reports_how_many(
    source_dir, collection
):
    """章扉は取り込まれず、除外件数が報告に載る。本文の節は残る。"""
    _write_md(
        source_dir,
        "mixed.md",
        _NAV_SECTION
        + "\n## 本編\n\nRAGは検索した文書を根拠にして回答を組み立てる仕組みである。"
        "実務では社内文書を対象にする。\n",
    )

    report = ingest_directory(source_dir, collection, session=_FakeSession())

    assert report.dropped == {"mixed.md": 1}
    stored = collection.get()["documents"]
    assert "1\n転移学習とファインチューニング" not in stored
    assert any("RAGは検索した文書を根拠に" in text for text in stored)


def test_ingest_keeps_everything_when_every_unit_looks_like_navigation(
    source_dir, collection
):
    """全滅したら何も落とさない。

    落とすと store.replace_source() が空のチャンク列を受け取り、資料が
    DBから丸ごと消える。規則が誤爆したときに最も起きてほしくない結果である。
    """
    messages = []
    _write_md(source_dir, "nav_only.md", _NAV_SECTION)

    report = ingest_directory(
        source_dir,
        collection,
        session=_FakeSession(),
        on_progress=messages.append,
    )

    assert "nav_only.md" not in report.dropped
    assert report.indexed["nav_only.md"] == 1
    assert collection.count() == 1, "資料がDBから消えていないことを直接見る"
    assert report.kept_all_navigation == ["nav_only.md"]
    assert any("警告" in message and "nav_only.md" in message for message in messages)


class _BrokenSession:
    """埋め込みが必ず失敗するセッション。

    requests の例外ではなく RuntimeError を投げる。requests の例外だと
    ingest/embedder.py が指数バックオフで再試行し、テストが数秒待たされる。
    """

    def post(self, url, json, timeout):
        raise RuntimeError("Ollama に接続できません")

    def close(self):
        pass


def test_a_file_that_fails_is_not_reported_as_kept_all_navigation(
    source_dir, collection
):
    """埋め込みに失敗した資料を kept_all_navigation に載せない。

    載せると要約に「失敗」と「全ユニットがナビゲーション判定のため除外しません
    でした」が両方出る。後者は「丸ごと取り込んだ」と読めるが、実際はDBに1件も
    入っていない。
    """
    _write_md(source_dir, "nav_only.md", _NAV_SECTION)

    report = ingest_directory(source_dir, collection, session=_BrokenSession())

    assert "nav_only.md" in report.failed
    assert report.kept_all_navigation == []
    assert collection.count() == 0


def test_the_progress_line_names_which_units_were_dropped(source_dir, collection):
    """件数だけでなく、どの位置が消えたのかを出す。

    誤検出が起きたときに何が消えたのか追える唯一の手段である。
    """
    messages = []
    _write_md(
        source_dir,
        "mixed.md",
        _NAV_SECTION
        + "\n## 本編\n\nRAGは検索した文書を根拠にして回答を組み立てる仕組みである。"
        "実務では社内文書を対象にする。\n",
    )

    ingest_directory(
        source_dir,
        collection,
        session=_FakeSession(),
        on_progress=messages.append,
    )

    assert any("ナビゲーション1件を除外: 1" in message for message in messages)


def test_dropped_positions_uses_the_same_wording_as_the_citation():
    """スライドとページは出典表示と同じ言い方で並べる。"""
    from ingest.models import PAGE, SLIDE, ParsedUnit

    dropped = [
        ParsedUnit(text="1\n序論", location_type=SLIDE, location=4),
        ParsedUnit(text="－ 目次 －", location_type=SLIDE, location=5),
        ParsedUnit(text="ご清聴ありがとうございました", location_type=SLIDE, location=27),
    ]
    assert ingest_source._dropped_positions(dropped) == "スライド4,5,27"

    pages = [ParsedUnit(text="3\n第3章", location_type=PAGE, location=48)]
    assert ingest_source._dropped_positions(pages) == "p.48"


def test_dropped_positions_uses_the_heading_when_the_number_means_nothing():
    """Markdownの通し番号は利用者にとって意味がないので見出しを出す。"""
    from ingest.models import SECTION, ParsedUnit

    dropped = [
        ParsedUnit(text="1\n転移学習", location_type=SECTION, location=1, heading="1"),
        ParsedUnit(
            text="ご清聴ありがとうございました",
            location_type=SECTION,
            location=7,
            heading="おわりに",
        ),
    ]
    assert ingest_source._dropped_positions(dropped) == "1,おわりに"


# --- アップロード取り込み（画面のダイアログ経由） -------------------------
#
# 画面から一時ファイルとして取り込む経路。source/ には原本を残さないため、
# 通常の取り込みとは次の2点で振る舞いが違う。
#   1. 孤児削除をしない（一時ディレクトリを唯一の入力とみなすと source/ 由来の
#      資料が全滅する）
#   2. 資料キーに uploads/ を前置する（source/ 直下の同名資料と衝突させない）


def test_uploaded_file_is_indexed_under_the_uploads_prefix(tmp_path, collection):
    upload = _write_docx(tmp_path, "持ち込み資料.docx", "本日の議題は取り込みUIです。")
    report = ingest_source.ingest_uploads(
        [upload], collection, session=_FakeSession()
    )
    assert report.indexed == {"uploads/持ち込み資料.docx": 1}


def test_uploading_does_not_prune_the_existing_sources(
    source_dir, tmp_path, collection
):
    """一時ディレクトリを唯一の入力とみなすと source/ 由来の資料が全部消える。"""
    _write_docx(source_dir, "議事録.docx", "決定事項：RAGを導入するという結論です。")
    ingest_directory(source_dir, collection, session=_FakeSession())
    upload = _write_docx(tmp_path, "持ち込み資料.docx", "本日の議題は取り込みUIです。")
    report = ingest_source.ingest_uploads(
        [upload], collection, session=_FakeSession()
    )
    assert report.removed == []
    assert stored_file_hash(collection, "議事録.docx") is not None


def test_uploading_does_not_overwrite_a_source_file_with_the_same_name(
    source_dir, tmp_path, collection
):
    """同名でも別の資料として扱う。接頭辞を外すとここで source/ の中身が消える。"""
    _write_docx(source_dir, "議事録.docx", "決定事項：RAGを導入するという結論です。")
    ingest_directory(source_dir, collection, session=_FakeSession())
    upload_dir = tmp_path / "upload"
    upload_dir.mkdir()
    _write_docx(upload_dir, "議事録.docx", "こちらは持ち込みの別資料です。")
    ingest_source.ingest_uploads(
        [upload_dir / "議事録.docx"], collection, session=_FakeSession()
    )
    assert store.indexed_sources(collection) == {"議事録.docx", "uploads/議事録.docx"}


def test_a_source_run_keeps_the_uploaded_documents(source_dir, tmp_path, collection):
    """孤児削除の対象から外さないと、誰かが「差分を取り込む」を押した瞬間に消える。"""
    _write_docx(source_dir, "議事録.docx", "決定事項：RAGを導入するという結論です。")
    upload = _write_docx(tmp_path, "持ち込み資料.docx", "本日の議題は取り込みUIです。")
    ingest_source.ingest_uploads([upload], collection, session=_FakeSession())
    report = ingest_directory(source_dir, collection, session=_FakeSession())
    assert report.removed == []
    assert stored_file_hash(collection, "uploads/持ち込み資料.docx") is not None


def test_a_source_subdirectory_named_uploads_is_refused(source_dir, collection):
    """キーが衝突する。黙って混ざるより、取り込みを止めて名前を直させる。"""
    (source_dir / "uploads").mkdir()
    _write_docx(source_dir / "uploads", "議事録.docx", "決定事項：RAGを導入します。")
    with pytest.raises(ValueError, match="uploads"):
        ingest_directory(source_dir, collection, session=_FakeSession())


def test_missing_images_are_collected_per_source(source_dir, collection):
    """見つからない画像は、どの資料のどの参照先だったのかまで残す。

    件数だけでは追えない。dropped を件数ではなく現物で持っているのと同じ理由。
    画面からmdだけをアップロードした利用者が必ず通る経路でもある。
    """
    _write_md(source_dir, "手順書.md", "# 手順\n\n## 節\n本文は残る。\n![無い](images/none.png)\n")

    report = ingest_directory(
        source_dir,
        collection,
        session=_FakeSession(),
        caption_image=lambda _blob: "図です。",
    )

    assert report.missing_images == {"手順書.md": ["images/none.png"]}
    # 取り込み自体は成功している。画像が付かなかっただけである。
    assert report.indexed["手順書.md"] >= 1
    assert report.failed == {}


def test_no_missing_images_key_when_every_reference_resolves(source_dir, collection):
    """1件も無いときにキーを作ると、0件なのか機能が働いていないのか区別できない。"""
    _write_md(source_dir, "製品.md", "# UD-0900i\n\n## 設置情報\n幅は600mmです。\n")

    report = ingest_directory(source_dir, collection, session=_FakeSession())

    assert report.missing_images == {}


def test_ingest_directory_passes_keep_code_blocks_to_the_chunker(tmp_path, monkeypatch):
    """取り込み経路の端から端まで通っていることを見る。

    chunk_units まで届いていなければ、コードブロック保持の実装が
    あっても技術ドキュメントの取り込みでは一切効かない。
    """
    from ingest import chunker

    (tmp_path / "a.md").write_text(
        "# 題\n\n## 節\n\n" + "説明です。" * 200 + "\n\n```python\nx = 1\n```\n",
        encoding="utf-8",
    )
    seen = []
    real = chunker.chunk_units

    def spy(units, source, file_hash, indexed_at, keep_code_blocks=False):
        seen.append(keep_code_blocks)
        return real(units, source, file_hash, indexed_at, keep_code_blocks=keep_code_blocks)

    monkeypatch.setattr(ingest_source, "chunk_units", spy)

    collection = open_store(":memory:")
    ingest_source.ingest_directory(
        tmp_path, collection, session=_FakeSession(), keep_code_blocks=True
    )

    assert seen == [True]


def test_ingest_directory_does_not_keep_code_blocks_by_default(tmp_path, monkeypatch):
    from ingest import chunker

    (tmp_path / "a.md").write_text("# 題\n\n## 節\n\n本文です。\n", encoding="utf-8")
    seen = []
    real = chunker.chunk_units

    def spy(units, source, file_hash, indexed_at, keep_code_blocks=False):
        seen.append(keep_code_blocks)
        return real(units, source, file_hash, indexed_at, keep_code_blocks=keep_code_blocks)

    monkeypatch.setattr(ingest_source, "chunk_units", spy)

    collection = open_store(":memory:")
    ingest_source.ingest_directory(tmp_path, collection, session=_FakeSession())

    assert seen == [False]
