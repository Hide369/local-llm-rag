# 重複チャンクの畳み込み 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 同じ本文を複数の資料が共有するとき、本文を1行にまとめ、出典を複数持てるようにする。

**Architecture:** `chunks`（本文とベクトル）と `occurrences`（資料ごとの出現とメタデータ）の2テーブルに分ける。出現のIDは従来の `source::location::index` のまま保つため、`get()` を見ている `ingest/catalog.py` は変更しない。検索だけが本文単位（538件）になる。

**Tech Stack:** Python 3.13 / sqlite3 / numpy / pytest

**Spec:** `docs/superpowers/specs/2026-09-06-chunk-folding-design.md`

## Global Constraints

- 本文のIDは **SHA-256 の全長64文字**。短縮しない（衝突すると別の本文が黙って融合する）。
- 出現のIDは従来と同じ **`source::location::index`**。変えない。
- `count()` は**出現数**を返す。本文の種類数は `chunk_count()`。
- 接続時に **`PRAGMA foreign_keys = ON`** を立てる。
- `replace()` は **1つの `with self._write_lock, self._connection:`** で全手順を囲う。分割しない。
- `chunks` への書き込みは **upsert で embedding を更新**する。`INSERT OR IGNORE` にしない。
- 出現の並びは **`(source, location)` の昇順**に固定する。
- **`ingest/catalog.py` は変更しない。**
- テストは振る舞いを書く。SQL を直接検査しない。
- 実行環境: `./myvenv313/Scripts/python.exe -m pytest`
- コミットメッセージは英語。

---

### Task 1: 保存を2テーブルに分ける（振る舞いは変えない）

保存の形だけを変える。`count()`・`get()`・`search()` の返り値は現状と同一に保つ。
畳み込みの効果はまだ現れない。純粋なリファクタリングとして通す。

**Files:**
- Modify: `ingest/vector_store.py`（`_SCHEMA`、`__init__`、`count`、`_insert`、`_rows`、`_load_matrix`）
- Test: `tests/test_vector_store.py`

**Interfaces:**
- Consumes: なし
- Produces: `VectorStore.chunk_count() -> int`、内部ヘルパ `_text_id(text: str) -> str`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_vector_store.py` の `test_zero_vector_is_rejected` の直前に足す。

```python
def test_the_same_text_from_two_sources_is_stored_once(empty_store):
    """本文が同じなら行は1つ。出典は2つ数える。"""
    for source in ("a.md", "b.md"):
        empty_store.add(
            ids=[f"{source}::1::0"],
            documents=["共有されている本文"],
            metadatas=[{"source": source}],
            embeddings=[_vector(1.0)],
        )
    assert empty_store.count() == 2
    assert empty_store.chunk_count() == 1


def test_one_different_character_is_not_folded(empty_store):
    """完全一致だけを畳む。1文字違えば別の本文である。"""
    empty_store.add(
        ids=["a.md::1::0", "b.md::1::0"],
        documents=["講師プロフィール 年齢52歳", "講師プロフィール"],
        metadatas=[{"source": "a.md"}, {"source": "b.md"}],
        embeddings=[_vector(1.0), _vector(2.0)],
    )
    assert empty_store.chunk_count() == 2
```

- [ ] **Step 2: 落ちることを確認する**

Run: `./myvenv313/Scripts/python.exe -m pytest tests/test_vector_store.py -k "folded or stored_once" -v`
Expected: FAIL — `AttributeError: 'VectorStore' object has no attribute 'chunk_count'`

- [ ] **Step 3: スキーマを差し替える**

`ingest/vector_store.py` の `_SCHEMA` を置き換える。

```python
_SCHEMA = """
CREATE TABLE IF NOT EXISTS chunks (
    id        TEXT PRIMARY KEY,
    text      TEXT NOT NULL,
    embedding BLOB NOT NULL
);
CREATE TABLE IF NOT EXISTS occurrences (
    id       TEXT PRIMARY KEY,
    chunk_id TEXT NOT NULL REFERENCES chunks(id),
    source   TEXT NOT NULL,
    metadata TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS occurrences_source ON occurrences(source);
CREATE INDEX IF NOT EXISTS occurrences_chunk  ON occurrences(chunk_id);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value INTEGER);
INSERT OR IGNORE INTO meta (key, value) VALUES ('revision', 0);
"""
```

ファイル先頭の import に `hashlib` を足し、`_normalised` の下にヘルパを置く。

```python
def _text_id(text: str) -> str:
    """本文のSHA-256。短縮しない。

    切り詰めると別々の本文が同じIDになり得る。そのとき起きるのは例外ではなく、
    片方の本文が黙って消えることである。64文字の保存コストで構造的に防ぐ。
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
```

- [ ] **Step 4: 接続で外部キーを有効にする**

`__init__` の `sqlite3.connect(...)` の直後、`executescript` の前に足す。

```python
        # sqlite3 は既定で外部キーを検査しない。本文の無い出現が生まれても
        # 黙って通る。削除は「出現 → 孤児の本文」の順であり正しい手順なら
        # 制約に触れないので、これが火を噴くのは手順を間違えたときだけである。
        self._connection.execute("PRAGMA foreign_keys = ON")
```

- [ ] **Step 5: 件数の2つの入口を実装する**

`count` を置き換え、直後に `chunk_count` を足す。

```python
    def count(self) -> int:
        """出現の数。入れた件数がそのまま返るという既存の意味を保つ。"""
        return self._connection.execute("SELECT COUNT(*) FROM occurrences").fetchone()[0]

    def chunk_count(self) -> int:
        """本文の種類数。畳み込みがどれだけ効いたかはこちらに現れる。"""
        return self._connection.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
```

- [ ] **Step 6: 書き込みを2テーブルに分ける**

`_insert` の `cursor.executemany(...)` 以降を置き換える。長さ検証と `_normalised`
の呼び出しはそのまま残す（1行も書く前に弾くという順序が要る）。

```python
        matrix = _normalised(embeddings)
        chunk_ids = [_text_id(text) for text in documents]
        cursor.executemany(
            "INSERT INTO chunks (id, text, embedding) VALUES (?, ?, ?)"
            " ON CONFLICT(id) DO UPDATE SET embedding = excluded.embedding",
            [
                (chunk_id, text, vector.tobytes())
                for chunk_id, text, vector in zip(chunk_ids, documents, matrix)
            ],
        )
        cursor.executemany(
            "INSERT OR REPLACE INTO occurrences"
            " (id, chunk_id, source, metadata) VALUES (?, ?, ?, ?)",
            [
                (
                    occurrence_id,
                    chunk_id,
                    metadata.get("source", ""),
                    json.dumps(metadata, ensure_ascii=False),
                )
                for occurrence_id, chunk_id, metadata in zip(ids, chunk_ids, metadatas)
            ],
        )
```

`ON CONFLICT DO UPDATE` にする理由を `_insert` の docstring 末尾に足す。

```
        本文が同じならベクトルも同じなので、通常この UPDATE は無駄である。
        しかし埋め込みモデルを差し替えて入れ直したとき、IGNORE では古いモデルの
        ベクトルが残る。件数は正しく、例外も出ず、距離だけが静かに狂う。
```

- [ ] **Step 7: 読み出しを結合に変える**

`_rows` と `_load_matrix` を置き換える。`get()` の本体は変更しない。

```python
    def _rows(self):
        """(出現ID, 本文, メタデータ) を全件返す。get() の土台。"""
        return [
            (occurrence_id, text, json.loads(metadata))
            for occurrence_id, text, metadata in self._connection.execute(
                "SELECT o.id, c.text, o.metadata"
                " FROM occurrences o JOIN chunks c ON c.id = o.chunk_id"
            )
        ]
```

`_load_matrix` は当面これまでどおり**出現単位**で読む。畳むのは Task 5 で行う。

```python
    def _load_matrix(self):
        """全ベクトルを1つの配列に読み込む。

        686件×1024次元で2.8MB、総当たりの内積は実測0.19ms。索引を持たない
        代わりに毎回この配列を使う。
        """
        rows = self._connection.execute(
            "SELECT o.id, c.text, o.metadata, c.embedding"
            " FROM occurrences o JOIN chunks c ON c.id = o.chunk_id"
        ).fetchall()
        if not rows:
            return [], np.zeros((0, 0), dtype="float32")
        entries = [
            (occurrence_id, text, json.loads(metadata))
            for occurrence_id, text, metadata, _ in rows
        ]
        matrix = np.stack(
            [np.frombuffer(blob, dtype="float32") for _, _, _, blob in rows]
        )
        return entries, matrix
```

- [ ] **Step 8: テストを通す**

Run: `./myvenv313/Scripts/python.exe -m pytest tests/test_vector_store.py -v`
Expected: PASS（新規2件を含む全件）

- [ ] **Step 9: 既存の全体が壊れていないことを確認する**

Run: `./myvenv313/Scripts/python.exe -m pytest -q`
Expected: PASS

`test_the_same_id_twice_overwrites_without_complaining` は引き続き通る。出現の
`INSERT OR REPLACE` が同じ振る舞いを保つためである。

- [ ] **Step 10: コミット**

```bash
git add ingest/vector_store.py tests/test_vector_store.py
git commit -F- <<'EOF'
refactor: split storage into chunks and occurrences

The same text appearing in several documents was stored once per document,
so retrieval spent its candidate slots on copies. Separate what can be
shared (text, vector) from what cannot (source, location, file hash,
product attributes) — measurement showed every metadata field is
per-document.

Behaviour is unchanged in this commit: count(), get() and search() still
answer per occurrence. Only the layout moves, so the refactor can be
reviewed on its own.
EOF
```

---

### Task 2: 共有チャンクの寿命

1つの資料を取り込み直したとき、他の資料が使っている本文を巻き込まない。
これが本設計で新しく生まれる故障の形であり、例外を出さずにデータが変わる。

**Files:**
- Modify: `ingest/vector_store.py`（`replace`、`delete`）
- Test: `tests/test_vector_store.py`

**Interfaces:**
- Consumes: Task 1 の `_text_id`、`chunk_count()`
- Produces: `_delete_orphan_chunks(cursor) -> None`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_vector_store.py` の末尾に足す。

```python
def _add_one(store, source, text, seed=1.0, location=1):
    store.add(
        ids=[f"{source}::{location}::0"],
        documents=[text],
        metadatas=[{"source": source, "location": location}],
        embeddings=[_vector(seed)],
    )


def test_reingesting_one_source_keeps_the_shared_text_for_the_others(empty_store):
    """A を入れ直しても、B が使っている本文は残る。

    これを落とすと B の根拠が消える。例外は出ず、count() は減った値を
    正しく返すため、次に検索するまで誰も気づかない。
    """
    _add_one(empty_store, "a.md", "共有されている本文")
    _add_one(empty_store, "b.md", "共有されている本文", seed=2.0)
    empty_store.replace(
        source="a.md",
        ids=["a.md::1::0"],
        documents=["A だけの新しい本文"],
        metadatas=[{"source": "a.md", "location": 1}],
        embeddings=[_vector(3.0)],
    )
    remaining = empty_store.get(where={"source": "b.md"})
    assert remaining["documents"] == ["共有されている本文"]
    assert empty_store.chunk_count() == 2


def test_the_last_source_to_drop_a_text_removes_it(empty_store):
    """誰も使わなくなった本文は残さない。孤児はベクトル行列に載り続ける。"""
    _add_one(empty_store, "a.md", "共有されている本文")
    _add_one(empty_store, "b.md", "共有されている本文", seed=2.0)
    for source in ("a.md", "b.md"):
        empty_store.replace(
            source=source,
            ids=[f"{source}::1::0"],
            documents=[f"{source} だけの本文"],
            metadatas=[{"source": source, "location": 1}],
            embeddings=[_vector(4.0)],
        )
    assert empty_store.chunk_count() == 2
    assert "共有されている本文" not in empty_store.get()["documents"]


def test_deleting_one_source_keeps_a_text_another_source_shares(empty_store):
    """delete(where=) も同じ規則で動く。store.delete_orphans がこれを呼ぶ。"""
    _add_one(empty_store, "a.md", "共有されている本文")
    _add_one(empty_store, "b.md", "共有されている本文", seed=2.0)
    empty_store.delete(where={"source": "a.md"})
    assert empty_store.count() == 1
    assert empty_store.chunk_count() == 1


def test_the_same_text_twice_in_one_source_keeps_both_occurrences(empty_store):
    """1資料が同じ本文を2箇所に持つとき、出現は2件のまま。"""
    empty_store.add(
        ids=["a.md::1::0", "a.md::5::0"],
        documents=["繰り返される本文", "繰り返される本文"],
        metadatas=[
            {"source": "a.md", "location": 1},
            {"source": "a.md", "location": 5},
        ],
        embeddings=[_vector(1.0), _vector(1.0)],
    )
    assert empty_store.count() == 2
    assert empty_store.chunk_count() == 1
```

- [ ] **Step 2: 落ちることを確認する**

Run: `./myvenv313/Scripts/python.exe -m pytest tests/test_vector_store.py -k "shared or last_source or deleting_one" -v`
Expected: FAIL — `replace` が `DELETE FROM chunks WHERE source = ?` を実行し、
`no such column: source` になる

- [ ] **Step 3: 孤児掃除を実装する**

`_bump_revision` の直前に足す。

```python
    @staticmethod
    def _delete_orphan_chunks(cursor) -> None:
        """どの資料からも参照されなくなった本文を消す。

        参照が残っている限り消さないのがこの設計の要である。1つの資料を
        取り込み直しただけで、他の資料が使っている本文まで消えてはならない。
        """
        cursor.execute(
            "DELETE FROM chunks"
            " WHERE id NOT IN (SELECT chunk_id FROM occurrences)"
        )
```

- [ ] **Step 4: replace と delete を書き換える**

`replace` の `with` の中を置き換える。source 不一致の検査はそのまま残す。

```python
        with self._write_lock, self._connection:
            self._connection.execute(
                "DELETE FROM occurrences WHERE source = ?", (source,)
            )
            self._insert(self._connection, ids, documents, metadatas, embeddings)
            self._delete_orphan_chunks(self._connection)
            self._bump_revision(self._connection)
```

`add` にも同じ掃除を足す。同じ出現IDに違う本文を入れると、前の本文が
どこからも参照されないまま `chunks` に残る。件数には表れず、ベクトル行列に
載って検索に出続ける。

```python
    def add(self, ids, documents, metadatas, embeddings) -> None:
        with self._write_lock, self._connection:
            self._insert(self._connection, ids, documents, metadatas, embeddings)
            self._delete_orphan_chunks(self._connection)
            self._bump_revision(self._connection)
```

`delete` も同じ形にする。

```python
    def delete(self, where=None) -> None:
        targets = self.get(where=where)["ids"]
        if not targets:
            return
        with self._write_lock, self._connection:
            self._connection.executemany(
                "DELETE FROM occurrences WHERE id = ?", [(t,) for t in targets]
            )
            self._delete_orphan_chunks(self._connection)
            self._bump_revision(self._connection)
```

- [ ] **Step 5: テストを通す**

Run: `./myvenv313/Scripts/python.exe -m pytest tests/test_vector_store.py -v`
Expected: PASS

- [ ] **Step 6: 原子性のテストが2テーブルを見ていることを確かめる**

`test_replace_that_fails_while_writing_keeps_the_old_chunks` と
`test_rejected_add_leaves_the_store_empty` に `chunk_count()` の表明を足す。

```python
    assert empty_store.count() == 0
    assert empty_store.chunk_count() == 0
```

失敗した書き込みが `chunks` にだけ行を残す形は、`count()` を見ているだけでは
検出できない。孤児はベクトル行列に載り、検索に出続ける。

- [ ] **Step 7: 全体を確認してコミット**

Run: `./myvenv313/Scripts/python.exe -m pytest -q`
Expected: PASS

```bash
git add ingest/vector_store.py tests/test_vector_store.py
git commit -F- <<'EOF'
feat: keep a shared text alive while any source still uses it

Re-ingesting one document must not delete text that other documents share.
Delete the occurrences of that source, then delete only the chunks left
with no occurrence at all. Both happen inside the existing transaction, so
a failure still leaves neither table changed.

The failure this guards against is silent: the row vanishes, no exception
is raised, and count() reports the smaller number correctly.
EOF
```

---

### Task 3: 旧DBの検出と移行

既存の `vector_store.sqlite3` は旧スキーマである。黙って書き換えず、明示的に変換する。
再埋め込みは不要で、本文・メタデータ・ベクトルはすべて旧DBに揃っている。

**Files:**
- Modify: `ingest/vector_store.py`（`__init__`）
- Create: `scripts/migrate_store.py`
- Test: `tests/test_migrate_store.py`

**Interfaces:**
- Consumes: Task 1 の `_SCHEMA`、`_text_id`
- Produces: `migrate(path: str) -> int`（0=成功または不要、1=失敗）

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_migrate_store.py` を新規作成する。

```python
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
```

- [ ] **Step 2: 落ちることを確認する**

Run: `./myvenv313/Scripts/python.exe -m pytest tests/test_migrate_store.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.migrate_store'`

- [ ] **Step 3: 旧スキーマの検出を実装する**

`ingest/vector_store.py` の `__init__` で、`executescript` の**前**に検査する。

```python
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._reject_old_schema()
        self._connection.executescript(_SCHEMA)
```

メソッドを `count` の直前に足す。

```python
    def _reject_old_schema(self) -> None:
        """1テーブル時代のDBを開こうとしたら止める。

        自動で変換しない。移行が途中で失敗すると、何が起きたのか分からない
        DBだけが残る。退避を取ってから明示的に走らせる。
        """
        columns = {
            row[1]
            for row in self._connection.execute("PRAGMA table_info(chunks)")
        }
        if "source" in columns:
            raise VectorStoreError(
                "旧スキーマのDBです。次を実行して変換してください:\n"
                "    python -m scripts.migrate_store vector_store.sqlite3"
            )
```

- [ ] **Step 4: 移行スクリプトを書く**

`scripts/migrate_store.py` を新規作成する。

```python
"""1テーブル時代のベクトルストアを chunks / occurrences に変換する。

再埋め込みは要らない。本文もメタデータもベクトルも旧DBに揃っている。
変換して検証が通ってから初めて元のファイルを置き換える。
"""
import json
import shutil
import sqlite3
import sys
from datetime import date
from pathlib import Path

from ingest.vector_store import _SCHEMA, _text_id


def _is_old(connection) -> bool:
    columns = {row[1] for row in connection.execute("PRAGMA table_info(chunks)")}
    return "source" in columns


def migrate(path: str) -> int:
    source_path = Path(path)
    if not source_path.exists():
        print(f"見つかりません: {source_path}")
        return 1

    connection = sqlite3.connect(source_path)
    try:
        if not _is_old(connection):
            print("すでに新しいスキーマです。何もしません。")
            return 0
        rows = connection.execute(
            "SELECT id, text, metadata, embedding FROM chunks"
        ).fetchall()
        revision = connection.execute(
            "SELECT value FROM meta WHERE key = 'revision'"
        ).fetchone()[0]
    finally:
        connection.close()

    backup = source_path.with_name(
        f"{source_path.name}.bak-{date.today():%Y%m%d}"
    )
    shutil.copy2(source_path, backup)
    print(f"退避しました: {backup}")

    target_path = source_path.with_name(f"{source_path.name}.migrating")
    target_path.unlink(missing_ok=True)
    target = sqlite3.connect(target_path)
    try:
        target.executescript(_SCHEMA)
        with target:
            for occurrence_id, text, metadata, embedding in rows:
                chunk_id = _text_id(text)
                target.execute(
                    "INSERT INTO chunks (id, text, embedding) VALUES (?, ?, ?)"
                    " ON CONFLICT(id) DO NOTHING",
                    (chunk_id, text, embedding),
                )
                target.execute(
                    "INSERT INTO occurrences (id, chunk_id, source, metadata)"
                    " VALUES (?, ?, ?, ?)",
                    (
                        occurrence_id,
                        chunk_id,
                        json.loads(metadata).get("source", ""),
                        metadata,
                    ),
                )
            target.execute(
                "UPDATE meta SET value = ? WHERE key = 'revision'", (revision,)
            )

        occurrences = target.execute("SELECT COUNT(*) FROM occurrences").fetchone()[0]
        chunks = target.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        orphans = target.execute(
            "SELECT COUNT(*) FROM chunks"
            " WHERE id NOT IN (SELECT chunk_id FROM occurrences)"
        ).fetchone()[0]
    finally:
        target.close()

    expected_chunks = len({text for _, text, _, _ in rows})
    problems = []
    if occurrences != len(rows):
        problems.append(f"出現数が合いません: {occurrences} ≠ {len(rows)}")
    if chunks != expected_chunks:
        problems.append(f"本文の種類数が合いません: {chunks} ≠ {expected_chunks}")
    if orphans:
        problems.append(f"孤児の本文が {orphans} 件あります")
    if problems:
        # 書き戻さない。元のファイルは触っていないので、退避も含めて無傷である。
        for problem in problems:
            print(f"検証に失敗: {problem}")
        print(f"元のファイルは変更していません: {source_path}")
        target_path.unlink(missing_ok=True)
        return 1

    target_path.replace(source_path)
    print(f"変換しました: {len(rows)}出現 / {chunks}本文（{len(rows) - chunks}行削減）")
    return 0


def main() -> int:
    if len(sys.argv) != 2:
        print("使い方: python -m scripts.migrate_store <DBのパス>")
        return 1
    return migrate(sys.argv[1])


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: テストを通す**

Run: `./myvenv313/Scripts/python.exe -m pytest tests/test_migrate_store.py -v`
Expected: PASS

- [ ] **Step 6: 全体を確認してコミット**

Run: `./myvenv313/Scripts/python.exe -m pytest -q`
Expected: PASS

```bash
git add ingest/vector_store.py scripts/migrate_store.py tests/test_migrate_store.py
git commit -F- <<'EOF'
feat: convert an existing store instead of silently rewriting it

Opening a one-table database now stops and names the command to run. The
migration copies the file aside first, builds the new layout in a
temporary file, and only replaces the original once the occurrence count,
the distinct-text count and the orphan count all check out.

No re-embedding: the old database already holds every vector.
EOF
```

---

### Task 4: 本文単位の入口を足す

追加だけを行う。既存の `get()` と `search()` は触らない。次のタスクの土台になる。

**Files:**
- Modify: `ingest/vector_store.py`
- Test: `tests/test_vector_store.py`

**Interfaces:**
- Consumes: Task 1〜2
- Produces:
  - `VectorStore.chunks() -> tuple[list[str], list[str]]` — `(chunk_id の並び, 本文の並び)`
  - `VectorStore.chunks_by_ids(ids: list[str]) -> dict[str, tuple[str, list[dict]]]`
    — `chunk_id → (本文, 出現メタデータの並び)`。出現は `(source, location)` の昇順。

- [ ] **Step 1: 失敗するテストを書く**

```python
def test_chunks_returns_one_entry_per_text(empty_store):
    _add_one(empty_store, "a.md", "共有されている本文")
    _add_one(empty_store, "b.md", "共有されている本文", seed=2.0)
    _add_one(empty_store, "b.md", "固有の本文", seed=3.0, location=2)
    ids, texts = empty_store.chunks()
    assert len(ids) == 2
    assert sorted(texts) == ["共有されている本文", "固有の本文"]


def test_chunks_by_ids_lists_every_occurrence_in_source_order(empty_store):
    """代表は取り込み順ではなく (source, location) の昇順で決まる。

    b.md を先に入れても a.md が先頭に来る。取り込み順で変わると、同じ質問の
    出典が再取り込みのたびに入れ替わる。
    """
    _add_one(empty_store, "b.md", "共有されている本文", seed=2.0)
    _add_one(empty_store, "a.md", "共有されている本文")
    (chunk_id,), _ = empty_store.chunks()
    text, occurrences = empty_store.chunks_by_ids([chunk_id])[chunk_id]
    assert text == "共有されている本文"
    assert [o["source"] for o in occurrences] == ["a.md", "b.md"]


def test_chunks_by_ids_drops_unknown_ids(empty_store):
    """取り込みで消えたチャンクのIDが索引に残ることがある。落として通す。"""
    _add_one(empty_store, "a.md", "本文")
    (chunk_id,), _ = empty_store.chunks()
    found = empty_store.chunks_by_ids([chunk_id, "no-such-id"])
    assert list(found) == [chunk_id]
```

- [ ] **Step 2: 落ちることを確認する**

Run: `./myvenv313/Scripts/python.exe -m pytest tests/test_vector_store.py -k chunks_ -v`
Expected: FAIL — `AttributeError: 'VectorStore' object has no attribute 'chunks'`

- [ ] **Step 3: 実装する**

`get` の直後に足す。

```python
    @staticmethod
    def _occurrence_order(metadata: dict):
        """(source, location) の昇順。location は型が混ざるので文字列で比べる。"""
        return (metadata.get("source", ""), str(metadata.get("location", "")))

    def chunks(self) -> tuple[list[str], list[str]]:
        """本文単位のIDと本文。BM25インデックスの入力になる。"""
        rows = self._connection.execute("SELECT id, text FROM chunks").fetchall()
        return [row[0] for row in rows], [row[1] for row in rows]

    def chunks_by_ids(self, ids: list[str]) -> dict[str, tuple[str, list[dict]]]:
        """本文とその出現をまとめて返す。知らないIDは黙って落とす。

        出現を (source, location) の昇順に固定する。代表が取り込み順で
        変わると、同じ質問に対する出典が再取り込みのたびに入れ替わる。
        """
        if not ids:
            return {}
        placeholders = ",".join("?" * len(ids))
        rows = self._connection.execute(
            "SELECT c.id, c.text, o.metadata"
            " FROM chunks c JOIN occurrences o ON o.chunk_id = c.id"
            f" WHERE c.id IN ({placeholders})",
            list(ids),
        ).fetchall()
        found: dict[str, tuple[str, list[dict]]] = {}
        for chunk_id, text, metadata in rows:
            found.setdefault(chunk_id, (text, []))[1].append(json.loads(metadata))
        for _, occurrences in found.values():
            occurrences.sort(key=self._occurrence_order)
        return {chunk_id: found[chunk_id] for chunk_id in ids if chunk_id in found}
```

- [ ] **Step 4: テストを通す**

Run: `./myvenv313/Scripts/python.exe -m pytest tests/test_vector_store.py -v`
Expected: PASS

- [ ] **Step 5: コミット**

```bash
git add ingest/vector_store.py tests/test_vector_store.py
git commit -F- <<'EOF'
feat: add text-addressed accessors to the store

chunks() feeds the BM25 index and chunks_by_ids() resolves a text back to
every document it appears in, ordered by (source, location) so the
representative does not move when documents are re-ingested.

Purely additive; get() stays addressed by occurrence.
EOF
```

---

### Task 5: 検索を本文単位に畳む

ここで初めて畳み込みが検索に現れる。`search` の返り値が変わるため、
`ingest/retrieval.py`・`ingest/store.py`・`scripts/check_retrieval.py` が同時に追随する。
分割すると木が赤いままになるので1タスクにまとめる。

**Files:**
- Modify: `ingest/vector_store.py`（`_load_matrix`、`search`）
- Modify: `ingest/retrieval.py`（`Hit`、`_vector_candidates`、`search`）
- Modify: `ingest/store.py`（`all_documents`）
- Modify: `scripts/check_retrieval.py`（`_vector_best`）
- Test: `tests/test_vector_store.py`、`tests/test_retrieval.py`

**Interfaces:**
- Consumes: Task 4 の `chunks()`、`chunks_by_ids()`
- Produces:
  - `VectorStore.search(vector, limit) -> list[tuple[str, float, str, list[dict]]]`
    — `(chunk_id, 距離, 本文, 出現メタデータの並び)`
  - `Hit(text, distance, occurrences, bm25_score=None, rrf_score=0.0, rerank_score=None)`
    と読み取り専用の `Hit.metadata`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_vector_store.py` に足す。

```python
def test_search_returns_a_shared_text_once_with_every_source(empty_store):
    """重複が候補枠を食わない。これが畳み込みの目的である。"""
    _add_one(empty_store, "a.md", "共有されている本文")
    _add_one(empty_store, "b.md", "共有されている本文", seed=2.0)
    found = empty_store.search(_vector(1.0), limit=10)
    assert len(found) == 1
    _, _, text, occurrences = found[0]
    assert text == "共有されている本文"
    assert [o["source"] for o in occurrences] == ["a.md", "b.md"]
```

- [ ] **Step 2: 落ちることを確認する**

Run: `./myvenv313/Scripts/python.exe -m pytest tests/test_vector_store.py -k search_returns_a_shared -v`
Expected: FAIL — `assert 2 == 1`（出現単位のまま2件返る）

- [ ] **Step 3: 行列を本文単位にする**

`_load_matrix` を置き換える。

```python
    def _load_matrix(self):
        """全ベクトルを1つの配列に読み込む。本文単位である。

        538件×1024次元で2.2MB、総当たりの内積は実測0.19ms。索引を持たない
        代わりに毎回この配列を使う。同じ本文を何度も載せると、候補の枠を
        コピーが食い合う。
        """
        rows = self._connection.execute(
            "SELECT id, text, embedding FROM chunks ORDER BY id"
        ).fetchall()
        if not rows:
            return [], np.zeros((0, 0), dtype="float32")
        entries = [(chunk_id, text) for chunk_id, text, _ in rows]
        matrix = np.stack(
            [np.frombuffer(blob, dtype="float32") for _, _, blob in rows]
        )
        return entries, matrix
```

- [ ] **Step 4: search を書き換える**

末尾の返り値の組み立てだけを変える。同点の決め方（距離→ID）は変えない。

```python
        ordered = sorted(candidates, key=lambda i: (float(distances[i]), entries[i][0]))
        found = self.chunks_by_ids([entries[i][0] for i in ordered])
        return [
            (
                entries[i][0],
                float(distances[i]),
                entries[i][1],
                found[entries[i][0]][1],
            )
            for i in ordered
            if entries[i][0] in found
        ]
```

- [ ] **Step 5: BM25 の入力を本文単位にする**

`ingest/store.py` の `all_documents` を置き換える。

```python
def all_documents(collection) -> tuple[list[str], list[str]]:
    """全チャンクのIDと本文を、並びを揃えて返す。

    BM25インデックスをディスクに持たず起動時に組み直すため、その入力を
    ここから供給する。DBを唯一の情報源に保つための経路である。

    本文単位で返す。出現単位で返すと、複数の資料が共有する定型文が上位を
    占め、中身の違う根拠を押し出す（実測では上位6件中5件が同一本文だった）。
    """
    return collection.chunks()
```

- [ ] **Step 6: Hit を出現の並びで持つようにする**

`ingest/retrieval.py` の `Hit` を書き換える。`metadata` フィールドを消し、
`occurrences` を置き、`metadata` はプロパティにする。

**既存の `citation` プロパティは消さないこと。** 下のコード片はフィールドと
`metadata` だけを示している。クラス全体を置き換えると `citation` が失われ、
`ingest/prompting.py` と `scripts/check_retrieval.py` が壊れる。`citation` の
書式を変えるのは Task 6 である。

```python
@dataclass
class Hit:
    text: str
    distance: float | None
    # 1つの本文が複数の資料に現れる。(source, location) の昇順で、先頭が代表。
    occurrences: list[dict]
    bm25_score: float | None = None
    rrf_score: float = 0.0
    rerank_score: float | None = None

    @property
    def metadata(self) -> dict:
        """代表の出現。

        フィールドとして別に持たせない。同じ事実に2つの帳簿ができ、片方だけ
        更新された状態が例外を出さずに成立する。
        """
        return self.occurrences[0]
```

- [ ] **Step 7: 検索の合流を本文空間に揃える**

`_vector_candidates` の `rows` の値を差し替える。

```python
    ranks = {chunk_id: rank for rank, (chunk_id, _, _, _) in enumerate(found, start=1)}
    rows = {
        chunk_id: (distance, text, occurrences)
        for chunk_id, distance, text, occurrences in found
    }
```

`search` の中で BM25 だけが当てたチャンクを補完する箇所を書き換える。

```python
    # BM25だけで当たったチャンクは本文もメタデータも持っていないので取りに行く。
    missing = [chunk_id for chunk_id in lexical_scores if chunk_id not in vector_rows]
    if missing:
        for chunk_id, (text, occurrences) in collection.chunks_by_ids(missing).items():
            vector_rows[chunk_id] = (None, text, occurrences)
```

`Hit` を組み立てる箇所の変数名と引数を変える。

```python
        distance, text, occurrences = row
```

```python
                Hit(
                    text=text,
                    distance=distance,
                    occurrences=occurrences,
                    bm25_score=score,
                    rrf_score=rrf_score,
                ),
```

- [ ] **Step 8: 偽コレクションを追随させる**

`tests/test_retrieval.py` の `_FakeCollection` を書き換える。`get` は
`store.all_documents` の経路から外れるため、`chunks` と `chunks_by_ids` を持たせる。

```python
    def chunks(self):
        return list(self._ids), list(self._documents)

    def chunks_by_ids(self, ids):
        # 知らないIDは黙って落とす。実ストアも消えたIDの行は返さない。
        return {
            chunk_id: (
                self._documents[self._ids.index(chunk_id)],
                [self._metadatas[self._ids.index(chunk_id)]],
            )
            for chunk_id in ids
            if chunk_id in self._ids
        }

    def search(self, vector, limit):
        rows = self._order[: min(limit, self._vector_limit or limit)]
        return [
            (
                self._ids[row],
                self._distances[row],
                self._documents[row],
                [self._metadatas[row]],
            )
            for row in rows
        ]
```

`Hit(...)` を直接組み立てているテストがあれば `metadata=` を `occurrences=[...]`
に書き換える。次で洗い出す。

Run: `grep -rn "Hit(" tests/ scripts/`

- [ ] **Step 9: check_retrieval を追随させる**

`scripts/check_retrieval.py` の `_vector_best` を書き換える。

```python
    _, distance, text, occurrences = found[0]
    hit = Hit(text=text, distance=distance, occurrences=occurrences)
    return hit.distance, hit.citation
```

`_lexical_top` は `collection.get` でメタデータを引き当てている。BM25 のIDが
本文ハッシュになったため、`chunks_by_ids` に切り替える。docstring の
「collection.get は」も実態に合わせる。返り値は従来どおり `(出典, スコア)` の
並びで、スコアの高い順である。

```python
def _lexical_top(collection, index, question, limit):
    """BM25側の上位を (出典, スコア) の並びで返す。スコアの高い順。

    chunks_by_ids は渡した並びを保つが、知らないIDは落とす。取り込みで消えた
    チャンクのIDが索引に残っていることがあるため、lexical.search が返した順に
    組み直しつつ、引けなかったものは飛ばす。
    """
    ranked = lexical.search(index, question, limit=limit)
    if not ranked:
        return []
    found = collection.chunks_by_ids([chunk_id for chunk_id, _ in ranked])
    return [
        (
            Hit(
                text=found[chunk_id][0],
                distance=None,
                occurrences=found[chunk_id][1],
            ).citation,
            score,
        )
        for chunk_id, score in ranked
        if chunk_id in found
    ]
```

- [ ] **Step 10: テストを通す**

Run: `./myvenv313/Scripts/python.exe -m pytest -q`
Expected: PASS

- [ ] **Step 11: コミット**

```bash
git add ingest/vector_store.py ingest/retrieval.py ingest/store.py scripts/check_retrieval.py tests/test_vector_store.py tests/test_retrieval.py
git commit -F- <<'EOF'
feat: search one text once instead of once per document

Both the vector matrix and the BM25 index are now built from chunks, so a
passage shared by seven decks occupies one candidate slot rather than
seven. Measured on the real corpus, the expected slide for "ファイン
チューニングについて教えてほしい" moves from 10th to 4th.

search() returns the occurrences of a hit rather than a single metadata
dict, and Hit.metadata becomes a property over that list so the two can
never disagree.
EOF
```

---

### Task 6: 出典に「ほか N 資料」を出す

**Files:**
- Modify: `ingest/retrieval.py`（`Hit.citation`）
- Modify: `rag_chat_app.py`（詳細表示）
- Test: `tests/test_retrieval.py`

**Interfaces:**
- Consumes: Task 5 の `Hit.occurrences`
- Produces: `Hit.citation` の書式変更、`Hit.all_citations() -> list[str]`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_retrieval.py` に足す。

```python
def _hit(occurrences):
    return Hit(text="本文", distance=0.1, occurrences=occurrences)


def test_a_single_occurrence_reads_exactly_as_before():
    """大半のチャンクは出典が1つである。文字列を変えてはならない。"""
    hit = _hit([{"source": "資料.pdf", "location_type": "page", "location": 48}])
    assert hit.citation == "資料.pdf p.48"


def test_several_occurrences_name_the_first_and_count_the_rest():
    hit = _hit(
        [
            {"source": "A.pptx", "location_type": "slide", "location": 25},
            {"source": "B.pptx", "location_type": "slide", "location": 23},
            {"source": "C.pptx", "location_type": "slide", "location": 24},
        ]
    )
    assert hit.citation == "A.pptx スライド25 ほか2資料"


def test_all_citations_lists_every_occurrence():
    """画面の詳細表示はすべて出す。プロンプトに入るのは短い形だけ。"""
    hit = _hit(
        [
            {"source": "A.pptx", "location_type": "slide", "location": 25},
            {"source": "B.pptx", "location_type": "slide", "location": 23},
        ]
    )
    assert hit.all_citations() == ["A.pptx スライド25", "B.pptx スライド23"]
```

- [ ] **Step 2: 落ちることを確認する**

Run: `./myvenv313/Scripts/python.exe -m pytest tests/test_retrieval.py -k citation -v`
Expected: FAIL — `AttributeError: 'Hit' object has no attribute 'all_citations'`

- [ ] **Step 3: 実装する**

`ingest/retrieval.py` の `citation` を、1件分を組み立てる私的メソッドと
公開プロパティに分ける。

```python
    @staticmethod
    def _one_citation(metadata: dict) -> str:
        """「ファイル名 p.48（OCR）」の形式で1つの出典を組み立てる。

        出典整形はここが唯一の置き場所である。位置種別を増やすときはこのメソッド
        だけを直す。
        """
        source = metadata.get("source", "")
        location_type = metadata.get("location_type")
        location = metadata.get("location")
        if location_type == "page":
            source = f"{source} p.{location}"
        elif location_type == "slide":
            source = f"{source} スライド{location}"
        elif location_type == "section":
            # 見出し文字列で示す。通し番号（location）は利用者にとって意味がない。
            heading = metadata.get("heading")
            if heading:
                source = f"{source} ＞ {heading}"
        if metadata.get("ocr"):
            source = f"{source}（OCR）"
        return source

    def all_citations(self) -> list[str]:
        """すべての出典。画面の詳細表示で使う。"""
        return [self._one_citation(metadata) for metadata in self.occurrences]

    @property
    def citation(self) -> str:
        """代表の出典。2件以上あるときだけ残りの数を添える。

        プロンプトにはこの短い形だけを入れる。7つのファイル名を読ませても、
        どれを引くかの判断を増やすだけで精度に寄与しない。
        """
        citation = self._one_citation(self.metadata)
        others = len(self.occurrences) - 1
        return f"{citation} ほか{others}資料" if others else citation
```

- [ ] **Step 4: テストを通す**

Run: `./myvenv313/Scripts/python.exe -m pytest tests/test_retrieval.py -v`
Expected: PASS

- [ ] **Step 5: 画面の詳細表示にすべて並べる**

`rag_chat_app.py` の `render_hits` を書き換える。出現が2件以上のときだけ、
残りの出典を続けて出す。

```python
def render_hits(hits):
    if not hits:
        return
    with st.expander(f"参考にした情報（{len(hits)}件）"):
        for hit in hits:
            st.caption(format_hit_caption(hit))
            others = hit.all_citations()[1:]
            if others:
                # 見出しは代表しか名乗らない。同じ記述がどこにあるかを
                # 資料を開かずに追えるようにする。
                st.caption("同じ記述: " + " ／ ".join(others))
            st.write(hit.text)
```

`ingest/prompting.py` の `format_hit_caption`（150行目付近の
`f"{hit.citation} ／ {distance} ／ {score} ／ {reranked}"`）は変更しない。
1行に収める書式であり、短い形が適している。

- [ ] **Step 6: 全体を確認してコミット**

Run: `./myvenv313/Scripts/python.exe -m pytest -q`
Expected: PASS

```bash
git add ingest/retrieval.py rag_chat_app.py tests/test_retrieval.py
git commit -F- <<'EOF'
feat: say how many documents a shared passage came from

A folded chunk cites its first source and counts the rest — "A.pptx
スライド25 ほか2資料" — so a reader searching the other decks for the same
wording is not told it is absent. Chunks with one source read exactly as
before.

The prompt gets the short form only; the detail view lists them all.
EOF
```

---

### Task 7: 取り込み後の整合性検証と件数表示

**Files:**
- Modify: `scripts/ingest_source.py`
- Test: `tests/test_ingest_source.py`

**Interfaces:**
- Consumes: Task 1 の `chunk_count()`、Task 2 の孤児掃除
- Produces: なし

- [ ] **Step 1: 失敗するテストを書く**

既存の偽ストアは `_FakeHealthyCollection` / `_FakeSilentlyBrokenCollection` で、
`_run_main_with(monkeypatch, tmp_path, collection)` に渡して `main()` の戻り値を
見る形になっている。まず既存の2つに新しい入口を足し、そのうえで孤児を持つ
ストアを加える。

`_FakeSilentlyBrokenCollection` の直後（`test_main_forwards_force_flag_to_ingest_directory`
の前）に足す。

```python
class _FakeOrphanedCollection:
    """出現の無い本文が残っているストア。

    孤児はベクトル行列に載って検索に出続けるが、count() には表れない。
    件数と検索が両方とも正常に見えるため、整合性を数えない限り露見しない。
    """

    def count(self):
        return 3

    def chunk_count(self):
        return 4

    def search(self, vector, limit):
        return [("hash-a", 0.1, "本文", [{"source": "a.md"}])]

    def integrity(self):
        return (1, 0)
```

既存の2つにも `chunk_count` と `integrity` を足す。`search` の4番目は Task 5 で
リストになったので、そこも揃える。

```python
class _FakeHealthyCollection:
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
```

（`_FakeHealthyCollection` の既存の定義を実物で確認し、`count` と `search` は
そのまま残して2つのメソッドを足すこと。）

テスト本体を、壊れたストアを使う既存テスト（393行目付近）の直後に足す。

```python
def test_ingest_fails_when_a_text_has_no_occurrence(monkeypatch, tmp_path, capsys):
    """帳簿が2つに分かれたぶん、片方だけが残る壊れ方が新しく生まれる。

    孤児の本文は検索に出続けるのに、count() も search() も正常に見える。
    次に開くまで露見しなかったChromaDBの破損と同じ形なので、ここで止める。
    """
    assert _run_main_with(monkeypatch, tmp_path, _FakeOrphanedCollection()) == 1
    assert "整合性" in capsys.readouterr().out
```

- [ ] **Step 2: 落ちることを確認する**

Run: `./myvenv313/Scripts/python.exe -m pytest tests/test_ingest_source.py -k orphan -v`
Expected: FAIL — 検証が無いため 0 が返る

- [ ] **Step 3: 検証を足す**

`scripts/ingest_source.py` の取り込み後検証に整合性の確認を加える。

```python
    try:
        verified = store.open_store(str(DB_PATH))
        indexed = verified.count()
        if indexed and not verified.search(
            [1.0] + [0.0] * (embedder.EMBED_DIM - 1), limit=1
        ):
            raise RuntimeError(f"{indexed}件あるのに検索が0件を返しました")
        # 帳簿が2つに分かれたぶん、片方だけが残る壊れ方が新しく生まれる。
        # 孤児の本文はベクトル行列に載って検索に出続け、出現だけの行は
        # 本文が引けない。どちらも件数には表れない。
        orphans, dangling = verified.integrity()
        if orphans or dangling:
            raise RuntimeError(
                f"整合性が壊れています: 孤児の本文{orphans}件 / 本文の無い出現{dangling}件"
            )
    except Exception as error:  # noqa: BLE001  何が起きても取り込みは失敗とする
        print(f"取り込み後の検証に失敗しました: {error}")
        return 1
```

`ingest/vector_store.py` に `integrity` を足す（`chunk_count` の直後）。

```python
    def integrity(self) -> tuple[int, int]:
        """(孤児の本文, 本文の無い出現) を数える。0, 0 が健全である。"""
        orphans = self._connection.execute(
            "SELECT COUNT(*) FROM chunks"
            " WHERE id NOT IN (SELECT chunk_id FROM occurrences)"
        ).fetchone()[0]
        dangling = self._connection.execute(
            "SELECT COUNT(*) FROM occurrences"
            " WHERE chunk_id NOT IN (SELECT id FROM chunks)"
        ).fetchone()[0]
        return orphans, dangling
```

- [ ] **Step 4: 件数の表示を両方にする**

```python
    print(f"DB内の総チャンク数: {collection.count()}（本文{collection.chunk_count()}種）")
```

- [ ] **Step 5: テストを通してコミット**

Run: `./myvenv313/Scripts/python.exe -m pytest -q`
Expected: PASS

```bash
git add ingest/vector_store.py scripts/ingest_source.py tests/test_ingest_source.py
git commit -F- <<'EOF'
feat: check both tables agree before calling an ingest successful

Splitting the ledger creates a new way to break that the counts do not
show: a text with no occurrence still rides in the vector matrix and keeps
appearing in results. Fail the ingest when either side is dangling, and
report both numbers in the summary.
EOF
```

---

### Task 8: 実データでの確認と文書の更新

単体テストとは別に、実際のコーパスで測る。設計書第2.3節の数字が基準になる。

**Files:**
- Modify: `README.md`、`docs/処理箇所マップ.md`、`docs/依存関係一覧.md`（該当箇所のみ）
- Modify: `colab/run_tests.ipynb`（`BRANCH`）

- [ ] **Step 1: 既存DBを移行する**

```bash
./myvenv313/Scripts/python.exe -m scripts.migrate_store vector_store.sqlite3
```

Expected: `変換しました: 608出現 / 538本文（70行削減）`、退避ファイルが作られる

- [ ] **Step 2: 移行後のDBが読めることを確認する**

```bash
./myvenv313/Scripts/python.exe -c "
from ingest import store
c = store.open_store(str(store.DB_PATH))
print(c.count(), c.chunk_count(), c.integrity())
"
```

Expected: `608 538 (0, 0)`

- [ ] **Step 3: 順位を測る**

Ollama を起動したうえで実行する。

```bash
./myvenv313/Scripts/python.exe -m scripts.check_retrieval
```

記録すること:
- 関連の最大距離と圏外の最小距離（**0.420 / 0.522 から動かないこと**）
- 回帰ケース2問の判定（「ファインチューニング」は OK、もう1問は **NG のまま**）

BM25 の順位は次で測る。

```bash
./myvenv313/Scripts/python.exe -c "
from ingest import store, lexical
c = store.open_store(str(store.DB_PATH))
ids, docs = c.chunks()
index = lexical.build(ids, docs)
for q in ['ファインチューニングについて教えてほしい', 'ファインチューニング']:
    ranked = lexical.search(index, q, 10)
    found = c.chunks_by_ids([i for i, _ in ranked])
    for rank, (cid, score) in enumerate(ranked, 1):
        if cid in found and any('生成AI活用セミナー.pptx' in o.get('source','') and o.get('location')==11 for o in found[cid][1]):
            print(q, '->', rank, '位'); break
"
```

Expected: 4位 / 3位（設計書第2.3節の実測と一致）

- [ ] **Step 4: 差分取り込みが壊れないことを確認する**

```bash
./myvenv313/Scripts/python.exe -u -m scripts.ingest_source
./myvenv313/Scripts/python.exe -u -m scripts.ingest_source
```

Expected: 1回目も2回目もスキップされ、終了コード0、整合性 `(0, 0)`

続いて1ファイルだけ入れ直し、共有チャンクが生きていることを確認する。

```bash
./myvenv313/Scripts/python.exe -u -m scripts.ingest_source --only-suffix .pptx --force
```

Expected: 終了コード0、`608（本文538種）`、整合性 `(0, 0)`

- [ ] **Step 5: 文書を更新する**

- `README.md` — ストアの構造の説明に `chunks` / `occurrences` を反映。出典が
  「ほか N 資料」になる場合があることを書く。測定値（70行削減、10位→4位、
  回帰は NG のまま）を記録する。
- `docs/処理箇所マップ.md` — `vector_store.py` の行番号と、`search` /
  `chunks` / `chunks_by_ids` の行を更新。`migrate_store.py` を追加。
- `docs/依存関係一覧.md` — 変更が無ければ触らない。

行番号は必ず実物を見て書くこと。以前、コードを見ずに書いた記述が誤りとして
指摘されている。

- [ ] **Step 6: Colab のブランチを合わせる**

`colab/run_tests.ipynb` の `BRANCH` を `feat/fold-duplicate-chunks` にする。

- [ ] **Step 7: コミットして押す**

```bash
git add README.md docs/処理箇所マップ.md colab/run_tests.ipynb
git commit -F- <<'EOF'
docs: record what folding duplicate chunks actually bought

608 occurrences over 538 texts — 70 rows fewer. The expected slide for
"ファインチューニングについて教えてほしい" moves from 10th to 4th in BM25,
and the gate distances (0.420 relevant / 0.522 out of domain) do not move.

The regression case is still NG. Three navigational slides — a section
divider, the folded 事前質問 chunk and a table of contents — now hold the
top three. That is a separate problem from duplication and is left to its
own branch.
EOF
git push -u origin feat/fold-duplicate-chunks
```

- [ ] **Step 8: Colab で全件を回す**

ローカルは全件実行中に3回クラッシュしているため、Colab L4 が検証経路である。
末尾の `tested: feat/fold-duplicate-chunks @ <コミット>` を確認すること。

Expected: 全件 PASS

---

## 完了の条件

- [ ] Colab で全件 PASS
- [ ] `count()` 608 / `chunk_count()` 538 / `integrity()` `(0, 0)`
- [ ] 関連の最大距離 0.420 / 圏外の最小距離 0.522 が動いていない
- [ ] 回帰ケースが「ファインチューニング」OK、もう1問 NG（**直ったことにしない**）
- [ ] 差分取り込みを2回連続で実行しても破損しない
- [ ] `ingest/catalog.py` に変更が無い
