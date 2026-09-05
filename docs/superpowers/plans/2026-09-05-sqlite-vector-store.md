# SQLiteベクトルストア 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ChromaDB を SQLite + numpy の自作ベクトルストアに置き換え、取り込みの部分書き込みでDBが読めなくなる障害を原理的に消す。

**Architecture:** SQLite に `chunks` テーブル（本文・メタデータJSON・float32のBLOB）を持ち、1資料の入れ替えを1トランザクションで行う。検索は全ベクトルを numpy 配列に読み込んで総当たりの内積を取る（686件で0.19ms実測）。近似索引は持たない。

**Tech Stack:** Python 3.13 / sqlite3（標準ライブラリ）/ numpy 2.5.2 / pytest

**Spec:** `docs/superpowers/specs/2026-09-05-sqlite-vector-store-design.md`

## Global Constraints

- 実行は必ず `myvenv313\Scripts\python.exe -m ...` 経由（README「コマンドは必ず `python.exe -m` 経由で実行すること」）
- コメントは「なぜ」を書く。「何を」はコードで表現する（既存コードの流儀に揃える）
- 新規の pip 依存を追加しない。`numpy` と標準ライブラリ `sqlite3`・`json` のみ
- `chroma_db/` には一切書き込まない（`udemy3.py` が使い続ける）
- ベクトルの次元は `ingest/embedder.py` の `EMBED_DIM` を唯一の情報源とし、他所に固定値を書かない
- cosine距離は `1 - 内積`（両者をL2正規化）。ChromaDBの `hnsw:space="cosine"` と同一定義
- コミットメッセージはコンベンショナルコミット形式・英語

## File Structure

| ファイル | 責務 |
|---|---|
| `ingest/vector_store.py`（新規） | ストレージエンジン。SQLite の読み書き、`where` 評価、総当たり検索。ドメイン知識を持たない |
| `ingest/store.py`（書き換え） | 取り込みドメインの操作（資料単位の入れ替え、孤児削除、ハッシュ判定）。エンジンに委譲する |
| `tests/test_vector_store.py`（新規） | エンジンのテスト |
| `tests/test_store.py`（修正） | ドメイン操作のテスト。フィクスチャを差し替え |

分割の理由は、SQLite の詳細（BLOB・トランザクション・正規化）と、取り込みの都合
（`source` 単位の入れ替え、`file_hash` による差分判定）が別の変更理由を持つため。
既存の `store.py` は後者だけを担っていた。

---

### Task 1: `where` 評価器

**Files:**
- Create: `ingest/vector_store.py`
- Test: `tests/test_vector_store.py`

**Interfaces:**
- Consumes: なし
- Produces: `matches(metadata: dict, where: dict | None) -> bool`、例外 `WhereError`

`where` は3つの形で渡ってくる（実コードで確認済み）。

- `{"source": "a.md"}` — 素の等値（`ingest/store.py`）
- `{"key": {"$lte": 26}}` — 単一条件（`ingest/catalog.py` の `_where`）
- `{"$and": [{"k1": {"$gte": 1}}, {"k2": {"$eq": "x"}}]}` — 2つ以上

- [ ] **Step 1: 失敗するテストを書く**

```python
# tests/test_vector_store.py
import pytest

from ingest.vector_store import WhereError, matches


def test_plain_value_is_equality():
    assert matches({"source": "a.md"}, {"source": "a.md"})
    assert not matches({"source": "b.md"}, {"source": "a.md"})


def test_no_condition_matches_everything():
    assert matches({"source": "a.md"}, None)
    assert matches({"source": "a.md"}, {})


def test_comparison_operators():
    metadata = {"noise_wash_db": 26}
    assert matches(metadata, {"noise_wash_db": {"$lte": 26}})
    assert matches(metadata, {"noise_wash_db": {"$gte": 26}})
    assert not matches(metadata, {"noise_wash_db": {"$lte": 25}})


def test_and_requires_every_clause():
    metadata = {"noise_wash_db": 26, "brand": "打田電器"}
    where = {"$and": [{"noise_wash_db": {"$lte": 30}}, {"brand": {"$eq": "打田電器"}}]}
    assert matches(metadata, where)
    assert not matches(metadata, {"$and": [{"noise_wash_db": {"$lte": 20}}]})


def test_missing_key_does_not_match():
    """属性を持たないPDF由来のチャンクが、条件に合致してはならない。"""
    assert not matches({"source": "a.pdf"}, {"noise_wash_db": {"$lte": 26}})


def test_incomparable_types_do_not_match():
    """文字列と数値の大小比較はTypeErrorになる。例外ではなく不一致として扱う。"""
    assert not matches({"price_tier": "エントリー"}, {"price_tier": {"$lte": 26}})


def test_unsupported_operator_raises():
    """黙って無視すると条件が消えたまま全件が返る。"""
    with pytest.raises(WhereError):
        matches({"k": 1}, {"k": {"$ne": 1}})
```

- [ ] **Step 2: 失敗を確認する**

Run: `myvenv313\Scripts\python.exe -m pytest tests/test_vector_store.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'ingest.vector_store'`）

- [ ] **Step 3: 最小の実装を書く**

```python
# ingest/vector_store.py
"""SQLite + numpy によるベクトルストア。

design: docs/superpowers/specs/2026-09-05-sqlite-vector-store-design.md

近似最近傍探索（HNSW）を持たない。686件・1024次元での総当たりcosine検索は
実測0.19msであり、100倍の規模でも8.93msで済む。索引を持たないことは性能上の
妥協ではなく、索引の破損という故障モードを持たないための選択である。
"""


class WhereError(Exception):
    """絞り込み条件が扱えない。"""


# ChromaDBの where から実際に使われている演算子だけを実装する。
# 増やすときは ingest/conditions.py の COMPARISONS / EQUALITY も揃えること。
_OPERATORS = {
    "$eq": lambda actual, expected: actual == expected,
    "$gte": lambda actual, expected: actual >= expected,
    "$lte": lambda actual, expected: actual <= expected,
}


def _compare(operator: str, actual, expected) -> bool:
    compare = _OPERATORS.get(operator)
    if compare is None:
        # 黙って無視してはならない。条件が消えたまま全件が返り、誤った一覧が
        # 根拠として使われる（ingest/conditions.py が記録している事故と同じ形）。
        raise WhereError(f"未対応の演算子です: {operator}")
    try:
        return compare(actual, expected)
    except TypeError:
        # 文字列と数値の大小比較。条件に合わないだけであり、異常ではない。
        return False


def matches(metadata: dict, where: dict | None) -> bool:
    """1件のメタデータが条件に合うかを判定する。

    SQLへ翻訳せずPythonで評価するのは、演算子の対応付けと文字列の組み立てが
    静かに間違える種類のコードだからである。686件では総当たりでも数マイクロ秒で、
    性能上の理由は無い。
    """
    if not where:
        return True
    for key, condition in where.items():
        if key == "$and":
            if not all(matches(metadata, clause) for clause in condition):
                return False
        elif isinstance(condition, dict):
            if key not in metadata:
                return False
            if not all(
                _compare(operator, metadata[key], expected)
                for operator, expected in condition.items()
            ):
                return False
        elif metadata.get(key) != condition:
            return False
    return True
```

- [ ] **Step 4: 通ることを確認する**

Run: `myvenv313\Scripts\python.exe -m pytest tests/test_vector_store.py -v`
Expected: PASS（7件）

- [ ] **Step 5: コミット**

```bash
git add ingest/vector_store.py tests/test_vector_store.py
git commit -m "feat: add where-clause evaluation for the new vector store"
```

---

### Task 2: ストアを開く・件数・追加

**Files:**
- Modify: `ingest/vector_store.py`
- Test: `tests/test_vector_store.py`

**Interfaces:**
- Consumes: Task 1 の `matches`
- Produces: `open_store(path: str) -> VectorStore`、`VectorStore.count() -> int`、
  `VectorStore.add(ids: list[str], documents: list[str], metadatas: list[dict], embeddings) -> None`、
  例外 `VectorStoreError`

`path` に `":memory:"` を渡せばインメモリで開く（テスト用）。

- [ ] **Step 1: 失敗するテストを書く**

```python
# tests/test_vector_store.py の末尾に追記
from ingest.vector_store import VectorStoreError, open_store


def _vector(seed: float, dim: int = 4) -> list[float]:
    return [seed] + [0.0] * (dim - 1)


@pytest.fixture
def empty_store():
    return open_store(":memory:")


def test_new_store_is_empty(empty_store):
    assert empty_store.count() == 0


def test_added_rows_are_counted(empty_store):
    empty_store.add(
        ids=["a::1", "a::2"],
        documents=["本文1", "本文2"],
        metadatas=[{"source": "a.md"}, {"source": "a.md"}],
        embeddings=[_vector(1.0), _vector(2.0)],
    )
    assert empty_store.count() == 2


def test_zero_vector_is_rejected(empty_store):
    """ノルム0は正規化でゼロ除算になる。埋め込みが空を返した事故を静かに通さない。"""
    with pytest.raises(VectorStoreError):
        empty_store.add(
            ids=["a::1"],
            documents=["本文"],
            metadatas=[{"source": "a.md"}],
            embeddings=[[0.0, 0.0, 0.0, 0.0]],
        )


def test_rejected_add_leaves_the_store_empty(empty_store):
    """弾いた書き込みが中途半端に残ってはならない。"""
    with pytest.raises(VectorStoreError):
        empty_store.add(
            ids=["a::1", "a::2"],
            documents=["良い", "悪い"],
            metadatas=[{"source": "a.md"}, {"source": "a.md"}],
            embeddings=[_vector(1.0), [0.0, 0.0, 0.0, 0.0]],
        )
    assert empty_store.count() == 0


def test_store_persists_across_connections(tmp_path):
    """別プロセス相当の開き直しで読めること。今回の障害はここで露見した。"""
    path = str(tmp_path / "store.sqlite3")
    open_store(path).add(
        ids=["a::1"],
        documents=["本文"],
        metadatas=[{"source": "a.md"}],
        embeddings=[_vector(1.0)],
    )
    assert open_store(path).count() == 1
```

- [ ] **Step 2: 失敗を確認する**

Run: `myvenv313\Scripts\python.exe -m pytest tests/test_vector_store.py -v`
Expected: FAIL（`ImportError: cannot import name 'open_store'`）

- [ ] **Step 3: 最小の実装を書く**

`ingest/vector_store.py` の先頭のimportに追記し、末尾にクラスを足す。

```python
import json
import sqlite3

import numpy as np


class VectorStoreError(Exception):
    """ストアの操作に失敗した。"""


_SCHEMA = """
CREATE TABLE IF NOT EXISTS chunks (
    id        TEXT PRIMARY KEY,
    source    TEXT NOT NULL,
    text      TEXT NOT NULL,
    metadata  TEXT NOT NULL,
    embedding BLOB NOT NULL
);
CREATE INDEX IF NOT EXISTS chunks_source ON chunks(source);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value INTEGER);
INSERT OR IGNORE INTO meta (key, value) VALUES ('revision', 0);
"""


def _normalised(embeddings) -> np.ndarray:
    """L2正規化する。cosine距離を内積で計算するための前提。

    呼び出し側に正規化の責任を持たせない。片方だけ正規化された状態は例外を
    出さず、距離だけを静かに狂わせる。
    """
    matrix = np.asarray(embeddings, dtype="float32")
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    if not np.all(norms > 0):
        raise VectorStoreError("ノルム0のベクトルは登録できません")
    return matrix / norms


def open_store(path: str) -> "VectorStore":
    return VectorStore(path)


class VectorStore:
    def __init__(self, path: str):
        # check_same_thread=False は Streamlit が @st.cache_resource で保持した
        # 接続を別スレッドから触るため。書き込みは取り込みプロセスのみで、
        # このプロセスは読むだけなので競合しない。
        self._connection = sqlite3.connect(path, check_same_thread=False)
        self._connection.executescript(_SCHEMA)
        self._connection.commit()

    def count(self) -> int:
        return self._connection.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]

    def add(self, ids, documents, metadatas, embeddings) -> None:
        matrix = _normalised(embeddings)
        rows = [
            (
                chunk_id,
                metadata.get("source", ""),
                text,
                json.dumps(metadata, ensure_ascii=False),
                vector.tobytes(),
            )
            for chunk_id, text, metadata, vector in zip(
                ids, documents, metadatas, matrix
            )
        ]
        with self._connection:
            self._connection.executemany(
                "INSERT OR REPLACE INTO chunks"
                " (id, source, text, metadata, embedding) VALUES (?, ?, ?, ?, ?)",
                rows,
            )
            self._connection.execute(
                "UPDATE meta SET value = value + 1 WHERE key = 'revision'"
            )
```

`_normalised` が `add` の**最初**に来ているのが要点。ゼロベクトルは1行も書く前に
弾かれるため、`test_rejected_add_leaves_the_store_empty` が通る。

- [ ] **Step 4: 通ることを確認する**

Run: `myvenv313\Scripts\python.exe -m pytest tests/test_vector_store.py -v`
Expected: PASS（12件）

- [ ] **Step 5: コミット**

```bash
git add ingest/vector_store.py tests/test_vector_store.py
git commit -m "feat: create and populate the SQLite-backed vector store"
```

---

### Task 3: `get`

**Files:**
- Modify: `ingest/vector_store.py`
- Test: `tests/test_vector_store.py`

**Interfaces:**
- Consumes: Task 1 `matches`、Task 2 `VectorStore`
- Produces: `VectorStore.get(ids=None, where=None, limit=None, include=None) -> dict`
  戻り値は `{"ids": list[str], "documents": list[str], "metadatas": list[dict]}`

ChromaDB と違い**入れ子にしない**。`include` は互換のため受け取るが無視する
（686件では取捨選択に意味が無く、分岐がバグを生むため。設計書4.6節）。

- [ ] **Step 1: 失敗するテストを書く**

```python
# tests/test_vector_store.py の末尾に追記
@pytest.fixture
def filled_store():
    store = open_store(":memory:")
    store.add(
        ids=["a::1", "a::2", "b::1"],
        documents=["あ1", "あ2", "い1"],
        metadatas=[
            {"source": "a.md", "noise_wash_db": 26},
            {"source": "a.md", "noise_wash_db": 30},
            {"source": "b.md"},
        ],
        embeddings=[_vector(1.0), _vector(2.0), _vector(3.0)],
    )
    return store


def test_get_on_an_empty_store_returns_empty_lists(empty_store):
    """0件でも呼び出し側が zip できる形を返すこと。"""
    found = empty_store.get()
    assert found == {"ids": [], "documents": [], "metadatas": []}


def test_get_returns_everything_by_default(filled_store):
    found = filled_store.get()
    assert sorted(found["ids"]) == ["a::1", "a::2", "b::1"]
    assert len(found["documents"]) == 3
    assert len(found["metadatas"]) == 3


def test_get_by_ids_keeps_them_aligned(filled_store):
    found = filled_store.get(ids=["b::1", "a::1"])
    rows = dict(zip(found["ids"], found["documents"]))
    assert rows == {"b::1": "い1", "a::1": "あ1"}


def test_get_ignores_unknown_ids(filled_store):
    """BM25側のインデックスには取り込みで消えたIDが残ることがある。"""
    found = filled_store.get(ids=["a::1", "存在しない"])
    assert found["ids"] == ["a::1"]


def test_get_filters_by_where(filled_store):
    found = filled_store.get(where={"source": "a.md"})
    assert sorted(found["ids"]) == ["a::1", "a::2"]


def test_get_applies_limit(filled_store):
    assert len(filled_store.get(where={"source": "a.md"}, limit=1)["ids"]) == 1


def test_metadata_survives_the_round_trip(filled_store):
    """JSONに落として戻すため、数値が文字列になっていないことを確かめる。"""
    found = filled_store.get(ids=["a::1"])
    assert found["metadatas"][0]["noise_wash_db"] == 26
    assert isinstance(found["metadatas"][0]["noise_wash_db"], int)
```

- [ ] **Step 2: 失敗を確認する**

Run: `myvenv313\Scripts\python.exe -m pytest tests/test_vector_store.py -v`
Expected: FAIL（`AttributeError: 'VectorStore' object has no attribute 'get'`）

- [ ] **Step 3: 最小の実装を書く**

```python
    def _rows(self):
        """(id, text, metadata) を全件返す。"""
        return [
            (chunk_id, text, json.loads(metadata))
            for chunk_id, text, metadata in self._connection.execute(
                "SELECT id, text, metadata FROM chunks"
            )
        ]

    def get(self, ids=None, where=None, limit=None, include=None) -> dict:
        """条件に合うチャンクを返す。

        include は ChromaDB との互換のために受け取るが無視する。686件では
        取捨選択に意味が無く、引数を見て分岐するほうがバグを生む。
        """
        rows = self._rows()
        if ids is not None:
            # 呼び出し側が渡した並びを保つ。lexical.search の順位を組み直す
            # 経路（scripts/check_retrieval.py）がこの並びに依存する。
            by_id = {chunk_id: (text, metadata) for chunk_id, text, metadata in rows}
            rows = [
                (chunk_id, *by_id[chunk_id]) for chunk_id in ids if chunk_id in by_id
            ]
        rows = [row for row in rows if matches(row[2], where)]
        if limit is not None:
            rows = rows[:limit]
        return {
            "ids": [row[0] for row in rows],
            "documents": [row[1] for row in rows],
            "metadatas": [row[2] for row in rows],
        }
```

- [ ] **Step 4: 通ることを確認する**

Run: `myvenv313\Scripts\python.exe -m pytest tests/test_vector_store.py -v`
Expected: PASS（19件）

- [ ] **Step 5: コミット**

```bash
git add ingest/vector_store.py tests/test_vector_store.py
git commit -m "feat: read chunks back out of the vector store"
```

---

### Task 4: `replace` と原子性、`delete`

**Files:**
- Modify: `ingest/vector_store.py`
- Test: `tests/test_vector_store.py`

**Interfaces:**
- Consumes: Task 2 `add`、Task 3 `get`
- Produces: `VectorStore.replace(source, ids, documents, metadatas, embeddings) -> None`、
  `VectorStore.delete(where=None) -> None`

**この課題が本設計の核心である。** `replace()` が原子的な基本操作で、削除と追加を
1つのトランザクションに収める。`delete()` と `add()` を別々に呼んで済ませてはならない。
その間にプロセスが落ちると、資料が消えたまま残る。

- [ ] **Step 1: 失敗するテストを書く**

```python
# tests/test_vector_store.py の末尾に追記
def test_replace_swaps_only_that_source(filled_store):
    filled_store.replace(
        "a.md",
        ids=["a::9"],
        documents=["差し替え後"],
        metadatas=[{"source": "a.md"}],
        embeddings=[_vector(9.0)],
    )
    assert sorted(filled_store.get()["ids"]) == ["a::9", "b::1"]


def test_replace_drops_chunks_that_no_longer_exist(filled_store):
    """ページ数が減った資料を取り込み直したとき、末尾の古いページを残さない。"""
    filled_store.replace(
        "a.md", ids=[], documents=[], metadatas=[], embeddings=[]
    )
    assert filled_store.get()["ids"] == ["b::1"]


def test_failed_replace_leaves_the_previous_content(filled_store):
    """今回の障害の回帰テスト。

    書き込みの途中で失敗しても、中途半端な状態を残さない。ChromaDBでは
    「帳簿だけが進んで実体が無い」状態が作れてしまい、次にDBを開いた時点で
    初めて壊れていることが分かった。
    """
    with pytest.raises(VectorStoreError):
        filled_store.replace(
            "a.md",
            ids=["a::9"],
            documents=["差し替え後"],
            metadatas=[{"source": "a.md"}],
            embeddings=[[0.0, 0.0, 0.0, 0.0]],
        )
    assert sorted(filled_store.get()["ids"]) == ["a::1", "a::2", "b::1"]


def test_delete_removes_matching_rows(filled_store):
    filled_store.delete(where={"source": "a.md"})
    assert filled_store.get()["ids"] == ["b::1"]
```

- [ ] **Step 2: 失敗を確認する**

Run: `myvenv313\Scripts\python.exe -m pytest tests/test_vector_store.py -v`
Expected: FAIL（`AttributeError: 'VectorStore' object has no attribute 'replace'`）

- [ ] **Step 3: 最小の実装を書く**

Task 2 の `add` を、`replace` を土台にした形へ書き直す。

```python
    def _insert(self, cursor, ids, documents, metadatas, embeddings) -> None:
        """正規化して1行ずつ書く。呼び出し側がトランザクションを持つ。

        正規化を最初に済ませるのは、1行も書く前に不正なベクトルを弾くため。
        """
        if not ids:
            return
        matrix = _normalised(embeddings)
        cursor.executemany(
            "INSERT OR REPLACE INTO chunks"
            " (id, source, text, metadata, embedding) VALUES (?, ?, ?, ?, ?)",
            [
                (
                    chunk_id,
                    metadata.get("source", ""),
                    text,
                    json.dumps(metadata, ensure_ascii=False),
                    vector.tobytes(),
                )
                for chunk_id, text, metadata, vector in zip(
                    ids, documents, metadatas, matrix
                )
            ],
        )

    def add(self, ids, documents, metadatas, embeddings) -> None:
        with self._connection:
            self._insert(
                self._connection, ids, documents, metadatas, embeddings
            )
            self._bump_revision(self._connection)

    def replace(self, source, ids, documents, metadatas, embeddings) -> None:
        """1つの資料のチャンクを丸ごと入れ替える。ここが原子性の要である。

        削除と追加を別々のトランザクションにしてはならない。間で落ちると
        資料が消えたまま残る。全部入るか1件も入らないかにするために、
        1つの with で囲う。
        """
        with self._connection:
            self._connection.execute("DELETE FROM chunks WHERE source = ?", (source,))
            self._insert(
                self._connection, ids, documents, metadatas, embeddings
            )
            self._bump_revision(self._connection)

    def delete(self, where=None) -> None:
        targets = self.get(where=where)["ids"]
        if not targets:
            return
        with self._connection:
            self._connection.executemany(
                "DELETE FROM chunks WHERE id = ?", [(t,) for t in targets]
            )
            self._bump_revision(self._connection)

    @staticmethod
    def _bump_revision(cursor) -> None:
        cursor.execute("UPDATE meta SET value = value + 1 WHERE key = 'revision'")
```

`with self._connection:` は例外時に自動でロールバックする。`_normalised` が
`_insert` の中で例外を投げるため、`DELETE` も巻き戻る。これが
`test_failed_replace_leaves_the_previous_content` が通る仕組みである。

- [ ] **Step 4: 通ることを確認する**

Run: `myvenv313\Scripts\python.exe -m pytest tests/test_vector_store.py -v`
Expected: PASS（23件）

- [ ] **Step 5: コミット**

```bash
git add ingest/vector_store.py tests/test_vector_store.py
git commit -m "feat: replace a document's chunks in one transaction"
```

---

### Task 5: `search`（cosine距離）

**Files:**
- Modify: `ingest/vector_store.py`
- Test: `tests/test_vector_store.py`

**Interfaces:**
- Consumes: Task 2 `VectorStore`
- Produces: `VectorStore.search(vector, limit) -> list[tuple[str, float, str, dict]]`
  （`(id, distance, text, metadata)` を距離の昇順で返す）

**距離の定義を絶対に取り違えないこと。** `1 - 内積`（両者をL2正規化）である。
ここを誤ると `RELEVANCE_THRESHOLD = 0.50` 以下すべての実測値が意味を失い、
**例外は出ない**。

- [ ] **Step 1: 失敗するテストを書く**

```python
# tests/test_vector_store.py の末尾に追記
def test_identical_vector_has_distance_zero(filled_store):
    found = filled_store.search(_vector(1.0), limit=1)
    chunk_id, distance, text, metadata = found[0]
    assert chunk_id == "a::1"
    assert distance == pytest.approx(0.0, abs=1e-6)
    assert text == "あ1"
    assert metadata["source"] == "a.md"


def test_distance_is_one_minus_cosine_similarity():
    """ChromaDBの hnsw:space='cosine' と同一の定義であることを固定する。"""
    store = open_store(":memory:")
    store.add(
        ids=["直交", "逆向き"],
        documents=["直交", "逆向き"],
        metadatas=[{"source": "x"}, {"source": "x"}],
        embeddings=[[0.0, 1.0], [-1.0, 0.0]],
    )
    by_id = {chunk_id: distance for chunk_id, distance, _, _ in store.search([1.0, 0.0], limit=2)}
    assert by_id["直交"] == pytest.approx(1.0, abs=1e-6)
    assert by_id["逆向き"] == pytest.approx(2.0, abs=1e-6)


def test_unnormalised_query_gives_the_same_distance(filled_store):
    """呼び出し側に正規化の責任を持たせない。長さ違いで距離が変わってはならない。"""
    short = filled_store.search([1.0, 0.0, 0.0, 0.0], limit=1)[0][1]
    long = filled_store.search([23.0, 0.0, 0.0, 0.0], limit=1)[0][1]
    assert short == pytest.approx(long, abs=1e-6)


def test_results_are_sorted_by_distance(filled_store):
    distances = [distance for _, distance, _, _ in filled_store.search(_vector(1.0), limit=3)]
    assert distances == sorted(distances)


def test_search_on_empty_store_returns_nothing(empty_store):
    assert empty_store.search([1.0, 0.0, 0.0, 0.0], limit=4) == []


def test_limit_larger_than_the_corpus_is_safe(filled_store):
    """CANDIDATE_COUNT=30 に対して資料が3件しかない状況は普通に起きる。"""
    assert len(filled_store.search(_vector(1.0), limit=30)) == 3
```

- [ ] **Step 2: 失敗を確認する**

Run: `myvenv313\Scripts\python.exe -m pytest tests/test_vector_store.py -v`
Expected: FAIL（`AttributeError: 'VectorStore' object has no attribute 'search'`）

- [ ] **Step 3: 最小の実装を書く**

```python
    def _load_matrix(self):
        """全ベクトルを1つの配列に読み込む。

        686件×1024次元で2.8MB、総当たりの内積は実測0.19ms。索引を持たない
        代わりに毎回この配列を使う。
        """
        rows = self._connection.execute(
            "SELECT id, text, metadata, embedding FROM chunks"
        ).fetchall()
        if not rows:
            return [], np.zeros((0, 0), dtype="float32")
        entries = [
            (chunk_id, text, json.loads(metadata)) for chunk_id, text, metadata, _ in rows
        ]
        matrix = np.stack(
            [np.frombuffer(blob, dtype="float32") for _, _, _, blob in rows]
        )
        return entries, matrix

    def search(self, vector, limit: int):
        """cosine距離の小さい順に返す。

        距離は 1 - 内積（両者をL2正規化）で、ChromaDBの hnsw:space="cosine" と
        同一の定義である。ここを変えると ingest/retrieval.py の
        RELEVANCE_THRESHOLD をはじめ、scripts/check_retrieval.py で積み上げた
        実測値がすべて意味を失う。しかも例外は出ない。
        """
        entries, matrix = self._load_matrix()
        if not entries:
            return []
        query = _normalised([vector])[0]
        distances = 1.0 - matrix @ query
        count = min(limit, len(entries))
        # argpartition は上位count件を選ぶだけで並べない。そのあと選んだ分だけ整列する。
        candidates = np.argpartition(distances, count - 1)[:count]
        ordered = candidates[np.argsort(distances[candidates], kind="stable")]
        return [
            (entries[i][0], float(distances[i]), entries[i][1], entries[i][2])
            for i in ordered
        ]
```

- [ ] **Step 4: 通ることを確認する**

Run: `myvenv313\Scripts\python.exe -m pytest tests/test_vector_store.py -v`
Expected: PASS（29件）

- [ ] **Step 5: コミット**

```bash
git add ingest/vector_store.py tests/test_vector_store.py
git commit -m "feat: search the vector store by exact cosine distance"
```

---

### Task 6: `revision` によるキャッシュの鮮度

**Files:**
- Modify: `ingest/vector_store.py`
- Test: `tests/test_vector_store.py`

**Interfaces:**
- Consumes: Task 5 `_load_matrix`
- Produces: `VectorStore.revision() -> int`。`search` が行列をキャッシュする

毎回の全件読み込みをやめ、`meta('revision')` が変わったときだけ読み直す。
`revision` は書き込みトランザクションの中で更新されるため、**書き込みと不可分**である。
mtime やチャンク数で代用しない（前者は書き込み以外でも動き、後者は同数の
差し替えを取りこぼす）。

- [ ] **Step 1: 失敗するテストを書く**

```python
# tests/test_vector_store.py の末尾に追記
def test_revision_advances_on_write(empty_store):
    before = empty_store.revision()
    empty_store.add(
        ids=["a::1"],
        documents=["本文"],
        metadatas=[{"source": "a.md"}],
        embeddings=[_vector(1.0)],
    )
    assert empty_store.revision() > before


def test_matrix_is_not_reloaded_when_nothing_changed(filled_store, monkeypatch):
    """判定を誤って常に真にしても例外は出ず、遅くなるだけなので明示的に測る。"""
    calls = []
    original = filled_store._load_matrix
    monkeypatch.setattr(
        filled_store, "_load_matrix", lambda: (calls.append(1), original())[1]
    )
    filled_store.search(_vector(1.0), limit=1)
    filled_store.search(_vector(2.0), limit=1)
    assert len(calls) == 1


def test_matrix_is_reloaded_after_a_write(filled_store):
    """同じ件数のまま内容だけ差し替わっても拾うこと。"""
    filled_store.replace(
        "b.md",
        ids=["b::1"],
        documents=["差し替え後"],
        metadatas=[{"source": "b.md"}],
        embeddings=[_vector(3.0)],
    )
    found = filled_store.search(_vector(3.0), limit=1)
    assert found[0][2] == "差し替え後"


def test_a_second_connection_sees_the_first_ones_writes(tmp_path):
    """取り込みプロセスの更新を、チャットのプロセスが拾えること。"""
    path = str(tmp_path / "store.sqlite3")
    writer = open_store(path)
    reader = open_store(path)
    writer.add(
        ids=["a::1"],
        documents=["本文"],
        metadatas=[{"source": "a.md"}],
        embeddings=[_vector(1.0)],
    )
    assert reader.search(_vector(1.0), limit=1)[0][0] == "a::1"
```

- [ ] **Step 2: 失敗を確認する**

Run: `myvenv313\Scripts\python.exe -m pytest tests/test_vector_store.py -v`
Expected: FAIL（`AttributeError: 'VectorStore' object has no attribute 'revision'`）

- [ ] **Step 3: 最小の実装を書く**

`__init__` の末尾にキャッシュ用の属性を足す。

```python
        self._cached_revision = None
        self._entries = []
        self._matrix = None
```

そのうえでメソッドを足し、`search` の冒頭を差し替える。

```python
    def revision(self) -> int:
        return self._connection.execute(
            "SELECT value FROM meta WHERE key = 'revision'"
        ).fetchone()[0]

    def _current(self):
        """世代が変わっていれば読み直す。変わっていなければキャッシュを返す。"""
        revision = self.revision()
        if revision != self._cached_revision:
            self._entries, self._matrix = self._load_matrix()
            self._cached_revision = revision
        return self._entries, self._matrix
```

`search` の1行目を `entries, matrix = self._load_matrix()` から
`entries, matrix = self._current()` に変える。

- [ ] **Step 4: 通ることを確認する**

Run: `myvenv313\Scripts\python.exe -m pytest tests/test_vector_store.py -v`
Expected: PASS（33件）

- [ ] **Step 5: コミット**

```bash
git add ingest/vector_store.py tests/test_vector_store.py
git commit -m "feat: reload the search matrix only when the store changed"
```

---

### Task 7: `ingest/store.py` を新エンジンへ載せ替える

**Files:**
- Modify: `ingest/store.py`（全面）
- Modify: `tests/test_store.py`

**Interfaces:**
- Consumes: Task 1〜6 の `ingest.vector_store`
- Produces: `store.open_store(path) -> VectorStore`（`vector_store.open_store` の再公開）、
  既存の `stored_file_hash` / `replace_source` / `indexed_sources` / `delete_orphans` /
  `all_documents` はシグネチャを変えない

`open_collection(client)` は ChromaDB のクライアントを受け取る形なので廃止する。
`COLLECTION_NAME` / `DISTANCE_SPACE` も不要になる。

- [ ] **Step 1: テストのフィクスチャを差し替える**

`tests/test_store.py` の冒頭を次に置き換える。`ephemeral_client` の import と、
system cache をクリアするフィクスチャは丸ごと不要になる。

```python
import pytest

from ingest import store
from ingest.embedder import EMBED_DIM
from ingest.models import Chunk
from ingest.store import (
    delete_orphans,
    indexed_sources,
    open_store,
    replace_source,
    stored_file_hash,
)


@pytest.fixture
def collection():
    """インメモリのストア。ディスクには触れない。"""
    return open_store(":memory:")
```

`COLLECTION_NAME` / `DISTANCE_SPACE` を検証しているテストがあれば削除する
（コレクションという概念が無くなるため）。

- [ ] **Step 2: 失敗を確認する**

Run: `myvenv313\Scripts\python.exe -m pytest tests/test_store.py -v`
Expected: FAIL（`ImportError: cannot import name 'open_store' from 'ingest.store'`）

- [ ] **Step 3: `ingest/store.py` を書き換える**

```python
"""取り込みドメインの操作。

差分判定に使う file_hash は各チャンクのメタデータに持たせる。別途マニフェスト
ファイルを置くとDBとファイルで状態が二重管理になり、必ず食い違うため。
信頼できる情報源は常にDBひとつにする。

ストレージの詳細（SQLite・正規化・トランザクション）は ingest/vector_store.py に
置く。このモジュールは「資料単位で入れ替える」「source/ から消えた資料を消す」
という取り込みの都合だけを持つ。
"""
from ingest.models import Chunk
from ingest.vector_store import open_store  # noqa: F401  再公開

DB_FILENAME = "vector_store.sqlite3"


def stored_file_hash(collection, source: str) -> str | None:
    """登録済みならそのファイルのハッシュを返す。未登録ならNone。"""
    found = collection.get(where={"source": source}, limit=1)
    metadatas = found["metadatas"]
    return metadatas[0].get("file_hash") if metadatas else None


def replace_source(collection, source: str, chunks: list[Chunk], embeddings) -> None:
    """1つの資料のチャンクを丸ごと入れ替える。

    削除と追加は vector_store.replace が1トランザクションで行う。別々に呼ぶと、
    間で落ちたときに資料が消えたまま残る。
    """
    collection.replace(
        source,
        ids=[chunk.id for chunk in chunks],
        documents=[chunk.text for chunk in chunks],
        metadatas=[chunk.metadata for chunk in chunks],
        embeddings=list(embeddings),
    )


def indexed_sources(collection) -> set[str]:
    if collection.count() == 0:
        return set()
    return {
        meta["source"] for meta in collection.get()["metadatas"] if "source" in meta
    }


def delete_orphans(collection, known_sources: set[str]) -> list[str]:
    """source/ に存在しなくなった資料のチャンクを削除し、削除した資料名を返す。"""
    orphans = sorted(indexed_sources(collection) - set(known_sources))
    for source in orphans:
        collection.delete(where={"source": source})
    return orphans


def all_documents(collection) -> tuple[list[str], list[str]]:
    """全チャンクのIDと本文を、並びを揃えて返す。

    BM25インデックスをディスクに持たず起動時に組み直すため、その入力を
    ここから供給する。DBを唯一の情報源に保つための経路である。
    """
    if collection.count() == 0:
        return [], []
    found = collection.get()
    return found["ids"], found["documents"]
```

- [ ] **Step 4: 通ることを確認する**

Run: `myvenv313\Scripts\python.exe -m pytest tests/test_store.py -v`
Expected: PASS

- [ ] **Step 5: コミット**

```bash
git add ingest/store.py tests/test_store.py
git commit -m "refactor: back ingest domain operations with the SQLite store"
```

---

### Task 8: `retrieval.py` を `search()` へ

**Files:**
- Modify: `ingest/retrieval.py:114-132`（`_vector_candidates`）
- Test: `tests/test_retrieval.py`

**Interfaces:**
- Consumes: Task 5 `VectorStore.search`
- Produces: 変更なし（`_vector_candidates` の戻り値の形は保つ）

- [ ] **Step 1: `_FakeCollection` を新APIに合わせる**

`tests/test_retrieval.py` は実物のChromaではなく手書きの `_FakeCollection`
（14行目）を使っている。その `query()` を `search()` に置き換える。入れ子が
なくなるぶん短くなる。

```python
    def search(self, vector, limit):
        rows = self._order[: min(limit, self._vector_limit or limit)]
        return [
            (
                self._ids[row],
                self._distances[row],
                self._documents[row],
                self._metadatas[row],
            )
            for row in rows
        ]
```

`count()` と `get()` はそのまま残す（Task 3 で互換を保っているため）。

- [ ] **Step 2: 失敗を確認する**

Run: `myvenv313\Scripts\python.exe -m pytest tests/test_retrieval.py -v`
Expected: FAIL（`AttributeError: '_FakeCollection' object has no attribute 'query'`。
`retrieval.py` がまだ `query()` を呼んでいる）

- [ ] **Step 3: `_vector_candidates` を書き換える**

```python
def _vector_candidates(collection, query, session):
    """(チャンクID → 順位) と、IDをキーにした (距離, 本文, メタデータ) を返す。"""
    found = collection.search(
        embed_query(query, session=session), limit=CANDIDATE_COUNT
    )
    ranks = {chunk_id: rank for rank, (chunk_id, _, _, _) in enumerate(found, start=1)}
    rows = {
        chunk_id: (distance, text, metadata)
        for chunk_id, distance, text, metadata in found
    }
    return ranks, rows
```

`retrieval.py:194` の `collection.get(ids=missing, include=[...])` は変更不要。
`include` は無視されるが受け取れる（設計書4.6節）。

- [ ] **Step 4: 通ることを確認する**

Run: `myvenv313\Scripts\python.exe -m pytest tests/test_retrieval.py -v`
Expected: PASS

- [ ] **Step 5: コミット**

```bash
git add ingest/retrieval.py tests/test_retrieval.py
git commit -m "refactor: take vector candidates from the store's search API"
```

---

### Task 9: `scripts/check_retrieval.py`

**Files:**
- Modify: `scripts/check_retrieval.py:92-103`（`_vector_best`）、`:180` 付近（クライアント生成）
- Test: なし（計測スクリプトであり、Task 12 で実行して確認する）

**Interfaces:**
- Consumes: Task 5 `search`、Task 7 `open_store`
- Produces: なし

- [ ] **Step 1: `_vector_best` を書き換える**

```python
def _vector_best(collection, question, session):
    """ベクトル側の最良ヒット。距離と出典を返す。"""
    found = collection.search(
        embedder.embed_query(question, session=session), limit=1
    )
    if not found:
        return None, ""
    _, distance, text, metadata = found[0]
    hit = Hit(text=text, distance=distance, metadata=metadata)
    return hit.distance, hit.citation
```

- [ ] **Step 2: クライアント生成を差し替える**

`chromadb.PersistentClient(...)` と `store.open_collection(...)` の2行を、
`store.open_store(str(DB_PATH))` の1行にする。`import chromadb` を削除し、
`DB_DIR` を `DB_PATH = Path(__file__).resolve().parent.parent / store.DB_FILENAME`
に置き換える。

- [ ] **Step 3: 構文が通ることを確認する**

Run: `myvenv313\Scripts\python.exe -c "import scripts.check_retrieval"`
Expected: エラーなし

- [ ] **Step 4: コミット**

```bash
git add scripts/check_retrieval.py
git commit -m "refactor: measure retrieval against the SQLite store"
```

---

### Task 10: 取り込みCLIとUI、残りのテスト、`conftest.py` の削除

**Files:**
- Modify: `scripts/ingest_source.py:180` 付近と `DB_DIR`
- Modify: `rag_chat_app.py:30-34`
- Modify: `tests/test_catalog.py`、`tests/test_conditions.py`、`tests/test_ingest_source.py`、`tests/test_rag_chat_app.py`
- Delete: `tests/conftest.py`

**Interfaces:**
- Consumes: Task 7 `open_store`、`DB_FILENAME`
- Produces: なし

- [ ] **Step 1: 4つのテストのフィクスチャを差し替える**

各ファイルの `from tests.conftest import ephemeral_client` を削除し、
`client = ephemeral_client()` とそれに続くコレクション生成を
`collection = store.open_store(":memory:")` に置き換える。

`tests/test_rag_chat_app.py` は `patch("chromadb.PersistentClient", ...)` で
差し替えているので、`patch("ingest.store.open_store", ...)` に変える。

- [ ] **Step 2: 失敗を確認する**

Run: `myvenv313\Scripts\python.exe -m pytest -q`
Expected: FAIL（本体がまだ ChromaDB を開いているため）

- [ ] **Step 3: CLI と UI を差し替える**

`scripts/ingest_source.py`:

```python
DB_PATH = Path(__file__).resolve().parent.parent / store.DB_FILENAME
```

```python
    collection = store.open_store(str(DB_PATH))
```

`import chromadb` を削除する。

`rag_chat_app.py`:

```python
DB_PATH = str(Path(__file__).parent / store.DB_FILENAME)


@st.cache_resource
def get_collection(db_path):
    return store.open_store(db_path)
```

`import chromadb` を削除し、`get_collection(DB_DIR)` の呼び出しを
`get_collection(DB_PATH)` にする。

- [ ] **Step 4: `tests/conftest.py` を削除する**

ChromaDB の `EphemeralClient` が Windows で起こす access violation への回避策
だったので、ChromaDB を使わなくなれば存在理由が無い。

```bash
git rm tests/conftest.py
```

- [ ] **Step 5: 全テストが通ることを確認する**

Run: `myvenv313\Scripts\python.exe -m pytest -q`
Expected: PASS（既存345件＋新規33件。deselected 3件はそのまま）

出力に faulthandler のスタックトレースが**出ないこと**も確認する。

- [ ] **Step 6: コミット**

```bash
git add -A
git commit -m "refactor: open the SQLite store from the CLI, the UI and the tests"
```

---

### Task 11: `chromadb` 依存の除去とドキュメント更新

**Files:**
- Modify: `requirements.txt`
- Modify: `docs/依存関係一覧.md`
- Modify: `docs/処理箇所マップ.md`
- Modify: `README.md`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: なし
- Produces: なし

- [ ] **Step 1: `requirements.txt` から `chromadb` を削除する**

`chromadb==1.0.16` の行を消す。`tokenizers` のコメントが「chromadbの依存としても
入る」と書いているので、その一文を「リランカーが直接使う」に直す。

`numpy` のコメントに「ベクトルストアの総当たり検索でも使う」を足す。

- [ ] **Step 2: `docs/依存関係一覧.md` を更新する**

`chromadb` の行を削除し、`numpy` の使用箇所に `ingest/vector_store.py` を足す。

- [ ] **Step 3: `docs/処理箇所マップ.md` の2節を更新する**

見出し「2. チャンクデータを ChromaDB に格納している箇所」を
「2. チャンクデータをベクトルストアに格納している箇所」に変え、
`store.py` の行番号表を新しい内容に差し替える。冒頭の流れ図の
「ingest/store.py ChromaDB へ格納」「ベクトル検索（ChromaDB）」も直す。

- [ ] **Step 4: `README.md` を更新する**

- 「構成」節の `chroma_db/` に関する段落を、`vector_store.sqlite3` の説明に差し替える。
  `local_docs` / `local_docs_v2` の共存の話は `udemy3.py` 側の事情として残す
- 「**取り込み中は `chroma_db` を開くプロセスを他に一切起動しないこと。**」を削除する。
  SQLite のトランザクションで守られるため、この制約は無くなった
- 「既知の制約」の ChromaDB 由来の記述を見直す
- リランカーの節の「chromadbが依存として持ち込む `tokenizers`」を直す

- [ ] **Step 5: `.gitignore` に追記する**

```
# ベクトルストア（source からいつでも再生成できるため追跡しない）
vector_store.sqlite3
```

`chroma_db/` の行は**残す**（`udemy3.py` が使い続ける）。

- [ ] **Step 6: テストが通ることを確認する**

Run: `myvenv313\Scripts\python.exe -m pytest -q`
Expected: PASS

- [ ] **Step 7: コミット**

```bash
git add -A
git commit -m "chore: drop the chromadb dependency"
```

---

### Task 12: 全量取り込みと健全性の実測

**Files:**
- Modify: `scripts/ingest_source.py`（末尾に検証を追加）

**Interfaces:**
- Consumes: Task 10 まで
- Produces: なし

取り込みの成功と、**別プロセスから読めること**は別の事実である。今回の障害は
まさにその差で露見した。取り込みの最後に検証を入れる。

- [ ] **Step 1: 取り込み後の健全性検証を足す**

`scripts/ingest_source.py` の `main()` の末尾、結果表示のあとに追加する。
`from ingest.embedder import EMBED_DIM` を import に足すこと（`embedder` は
既に import 済みなので `embedder.EMBED_DIM` と書いてもよい）。

```python
    # 取り込めたことと、次にDBを開いたときに読めることは別の事実である。
    # ChromaDB では前者だけが成立し、破損が次回起動まで露見しなかった。
    #
    # 件数だけでは足りない。今回の障害はベクトルの読み込みで起きており、
    # 件数は最後まで正しく返っていた。検索を1回通してベクトルまで触る。
    try:
        verified = store.open_store(str(DB_PATH))
        indexed = verified.count()
        if indexed and not verified.search([1.0] + [0.0] * (EMBED_DIM - 1), limit=1):
            raise RuntimeError(f"{indexed}件あるのに検索が0件を返しました")
    except Exception as error:  # noqa: BLE001  何が起きても取り込みは失敗とする
        print(f"取り込み後の検証に失敗しました: {error}")
        return 1
```

- [ ] **Step 2: 全量取り込みを実行する**

事前に Ollama へ疎通すること（`.env` の `OLLAMA_HOST` / `OLLAMA_API_KEY`）。
Streamlit は停止しておく。

Run: `myvenv313\Scripts\python.exe -m scripts.ingest_source`
Expected: 686チャンク前後・49ファイル。実測約24分

- [ ] **Step 3: 別プロセスで読めることを確認する**

Run: `myvenv313\Scripts\python.exe -c "from ingest import store; print(store.open_store('vector_store.sqlite3').count())"`
Expected: 取り込み時と同じ件数

- [ ] **Step 4: 検索品質を実測する**

Run: `myvenv313\Scripts\python.exe -m scripts.check_retrieval`
Expected: 「ゲートは分離できています」と表示されること

**関連の最大距離・圏外の最小距離を記録する。** ChromaDB 時代の実測は
関連 0.420 / 圏外 0.522 だった。厳密検索になったので**同等かわずかに改善**する
はずである。大きく変わっていたら距離の定義を疑うこと（設計書4.4節）。

- [ ] **Step 5: 差分取り込みを2回行い、壊れないことを確認する**

今回の障害は差分取り込みで再現した。同じ操作で壊れないことを確かめる。

```
myvenv313\Scripts\python.exe -m scripts.ingest_source --only-suffix .md --force
myvenv313\Scripts\python.exe -m scripts.check_retrieval
```

Expected: 2回とも成功し、`check_retrieval` が完走すること

- [ ] **Step 6: コミット**

```bash
git add scripts/ingest_source.py
git commit -m "feat: verify the store is readable after ingestion"
```

---

## 完了条件

- 全テストが通る（既存345件＋新規33件、faulthandler のノイズが出ない）
- `check_retrieval` のゲートが分離している
- 差分取り込みを2回繰り返してもDBが読める
- `requirements.txt` に `chromadb` が無い
- `chroma_db/` が変更されていない（`udemy3.py` が動く）
