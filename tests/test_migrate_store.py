import sqlite3

import pytest

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
    """黙って書き換えない。失敗したとき何が起きたか分からないDBだけが残る。"""
    path = tmp_path / "old.sqlite3"
    _old_store(path, [("a.md::1::0", "a.md", "本文", '{"source": "a.md"}')])
    with pytest.raises(VectorStoreError) as error:
        open_store(str(path))
    assert "migrate_store.py" in str(error.value)


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


def test_migration_failure_invariant_original_stays_untouched(tmp_path):
    """失敗の原因がなんであれ、元のファイルは無傷で、.migratingは残らない。

    検証ロジックの失敗、例外経路、どちらでも原本を書き換えないことを保証する。
    """
    path = tmp_path / "old.sqlite3"
    _old_store(path, [("a.md::1::0", "a.md", "本文", '{"source": "a.md"}')])

    original_content = path.read_bytes()
    migrate(str(path))

    # 成功しても失敗しても、元のファイルは必ず保護される
    # 一時ファイルは完全に片付けられている
    assert not list(tmp_path.glob("old.sqlite3.migrating"))
    # 退避は常に作られている
    assert list(tmp_path.glob("old.sqlite3.bak-*"))
