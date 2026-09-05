"""SQLite + numpy によるベクトルストア。

design: docs/superpowers/specs/2026-09-05-sqlite-vector-store-design.md

近似最近傍探索（HNSW）を持たない。686件・1024次元での総当たりcosine検索は
実測0.19msであり、100倍の規模でも8.93msで済む。索引を持たないことは性能上の
妥協ではなく、索引の破損という故障モードを持たないための選択である。
"""

import json
import sqlite3

import numpy as np


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

    def _insert(self, cursor, ids, documents, metadatas, embeddings) -> None:
        """正規化して1行ずつ書く。呼び出し側がトランザクションを持つ。

        正規化を最初に済ませるのは、1行も書く前に不正なベクトルを弾くため。
        長さ検証はさらにその前に置く。`zip` は長さが揃っていないと黙って
        短い方に切り詰める。`replace` の中でこれが起きると、DELETEで旧チャンクを
        消した後に新チャンクの一部だけを書いてコミットしてしまい、「帳簿は
        進んだのに実体が欠けている」という今回捨てたはずの壊れ方を作ってしまう。
        """
        if not ids:
            return
        lengths = {
            "ids": len(ids),
            "documents": len(documents),
            "metadatas": len(metadatas),
            "embeddings": len(embeddings),
        }
        if len(set(lengths.values())) != 1:
            raise VectorStoreError(f"ids/documents/metadatas/embeddingsの件数が揃っていません: {lengths}")
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
