import sqlite3

import pytest

from ingest import vector_store
from ingest.vector_store import VectorStoreError, open_store
from scripts.migrate_store import migrate

_OLD_SCHEMA = """
CREATE TABLE chunks (
    id        TEXT PRIMARY KEY,
    source    TEXT NOT NULL,
    text      TEXT NOT NULL,
    metadata  TEXT NOT NULL,
    embedding BLOB NOT NULL
);
CREATE TABLE meta (key TEXT PRIMARY KEY, value INTEGER);
INSERT INTO meta (key, value) VALUES ('revision', 7);
"""


def _old_store(path, rows):
    """rows は (id, source, text, metadata_json) の並び。"""
    connection = sqlite3.connect(path)
    connection.executescript(_OLD_SCHEMA)
    connection.executemany(
        "INSERT INTO chunks (id, source, text, metadata, embedding)"
        " VALUES (?, ?, ?, ?, ?)",
        [(i, s, t, m, b"\x00\x00\x80\x3f") for i, s, t, m in rows],
    )
    connection.commit()
    connection.close()


def test_opening_an_old_store_stops_with_the_command_to_run(tmp_path):
    """黙って書き換えない。失敗したとき何が起きたか分からないDBだけが残る。

    示すのは実際に動く起動方法でなければならない。`python scripts/migrate_store.py`
    は `ModuleNotFoundError: No module named 'ingest'` で落ちる。行き詰まった
    利用者にとってこのメッセージが唯一の手がかりなので、`-m` 形式を拘束する。
    """
    path = tmp_path / "old.sqlite3"
    _old_store(path, [("a.md::1::0", "a.md", "本文", '{"source": "a.md"}')])
    with pytest.raises(VectorStoreError) as error:
        open_store(str(path))
    message = str(error.value)
    assert "python -m scripts.migrate_store" in message
    assert "scripts/migrate_store.py" not in message


def test_migration_folds_the_shared_text_and_keeps_every_occurrence(tmp_path):
    path = tmp_path / "old.sqlite3"
    _old_store(
        path,
        [
            ("a.md::1::0", "a.md", "共有", '{"source": "a.md"}'),
            ("b.md::1::0", "b.md", "共有", '{"source": "b.md"}'),
            ("b.md::2::0", "b.md", "固有", '{"source": "b.md"}'),
        ],
    )
    assert migrate(str(path)) == 0
    store = open_store(str(path))
    assert store.count() == 3
    assert store.chunk_count() == 2


def test_migration_keeps_a_backup(tmp_path):
    path = tmp_path / "old.sqlite3"
    _old_store(path, [("a.md::1::0", "a.md", "本文", '{"source": "a.md"}')])
    migrate(str(path))
    assert list(tmp_path.glob("old.sqlite3.bak-*")), "退避が作られていない"


def test_migrating_a_new_store_changes_nothing(tmp_path):
    path = tmp_path / "new.sqlite3"
    store = open_store(str(path))
    store.add(
        ids=["a.md::1::0"],
        documents=["本文"],
        metadatas=[{"source": "a.md"}],
        embeddings=[[1.0, 0.0, 0.0, 0.0]],
    )
    assert migrate(str(path)) == 0
    assert open_store(str(path)).count() == 1


def test_migration_returns_1_on_corrupted_json_and_leaves_original_untouched(tmp_path):
    """壊れたJSONで例外が出ても、元のファイルは無傷で、.migratingは残らない。"""
    path = tmp_path / "old.sqlite3"
    # 壊れたJSONメタデータを持つ旧DB
    _old_store(path, [("a.md::1::0", "a.md", "本文", '{"source": broken json')])

    original_content = path.read_bytes()
    assert migrate(str(path)) == 1

    # 元のファイルが変わっていない
    assert path.read_bytes() == original_content
    # 一時ファイルが残っていない
    assert not list(tmp_path.glob("old.sqlite3.migrating"))
    # 退避は作られている
    assert list(tmp_path.glob("old.sqlite3.bak-*"))


def test_migration_returns_1_on_validation_failure_and_leaves_original_untouched(tmp_path, monkeypatch):
    """検証に失敗しても、元のファイルは無傷で、.migratingは残らない。

    本文数の不一致を検出する検証が失敗する場合、
    原本を書き換えず、一時ファイルも片付け、退避を示して終了する。
    """
    path = tmp_path / "old.sqlite3"
    # 異なる本文を2件
    _old_store(
        path,
        [
            ("a.md::1::0", "a.md", "text1", '{"source": "a.md"}'),
            ("b.md::1::0", "b.md", "text2", '{"source": "b.md"}'),
        ],
    )

    original_content = path.read_bytes()

    # ハッシュ衝突を起こす。違う本文が同じIDを返すようにする。
    # これは64文字IDが防ぐためにある実災害。
    import scripts.migrate_store
    def fake_text_id(text: str) -> str:
        return "collision"  # 常に同じIDを返す
    monkeypatch.setattr(scripts.migrate_store, "_text_id", fake_text_id)

    # 移行は検証に失敗する。期待する本文数は2だが、
    # ハッシュ衝突で1つのチャンクにまとまり、チャンク数は1になる。
    result = migrate(str(path))
    assert result == 1, "検証失敗時は1を返すべき"

    # 元のファイルが変わっていない
    assert path.read_bytes() == original_content, "元のファイルは書き換わっていない"
    # 一時ファイルが残っていない
    assert not list(tmp_path.glob("old.sqlite3.migrating")), ".migratingが残されていない"
    # 退避が残っている
    assert list(tmp_path.glob("old.sqlite3.bak-*")), "退避が作られている"


def test_rejecting_an_old_store_does_not_leak_the_connection(tmp_path, monkeypatch):
    """例外で抜けるときも接続を閉じる。

    CLIは即終了するので漏れても気づけない。気づくのは Streamlit の
    @st.cache_resource で、例外のたびに開き直すためリロードごとに
    ファイルハンドルが積み上がる。
    """
    path = tmp_path / "old.sqlite3"
    _old_store(path, [("a.md::1::0", "a.md", "本文", '{"source": "a.md"}')])

    opened = []
    real_connect = sqlite3.connect

    def spy(*args, **kwargs):
        connection = real_connect(*args, **kwargs)
        opened.append(connection)
        return connection

    monkeypatch.setattr(vector_store.sqlite3, "connect", spy)
    with pytest.raises(VectorStoreError):
        open_store(str(path))

    assert opened, "接続が開かれていない。この経路を通っていない"
    for connection in opened:
        with pytest.raises(sqlite3.ProgrammingError):
            connection.execute("SELECT 1")


def test_migrating_a_file_that_is_not_a_database_says_why(tmp_path, capsys):
    """生のトレースバックで死なせない。

    sqlite3.connect はファイルを開くだけで中身を読まないため、SQLiteでない
    ファイルは最初の問い合わせまで気づけない。そこで素通しすると、退避も変換も
    していないのに何が起きたのか分からないまま終わる。
    """
    path = tmp_path / "notes.txt"
    path.write_text("これはSQLiteのDBではない", encoding="utf-8")

    assert migrate(str(path)) == 1

    output = capsys.readouterr().out
    assert "SQLiteのDBとして読めません" in output
    # 引き返すだけで、退避も .migrating も作らない。
    assert list(tmp_path.iterdir()) == [path]
