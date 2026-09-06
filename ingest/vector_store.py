"""SQLite + numpy によるベクトルストア。

design: docs/superpowers/specs/2026-09-05-sqlite-vector-store-design.md

近似最近傍探索（HNSW）を持たない。686件・1024次元での総当たりcosine検索は
実測0.19msであり、100倍の規模でも8.93msで済む。索引を持たないことは性能上の
妥協ではなく、索引の破損という故障モードを持たないための選択である。
"""

import hashlib
import json
import sqlite3
import threading

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
        elif key.startswith("$"):
            # $or などは条件が「消える」のではなく、全件が落ちる方向に静かに
            # 壊れる（metadata に "$or" というキーは無いため常に不一致）。
            # 根拠が1件も出ない理由が分からなくなるので、例外にする。
            raise WhereError(f"未対応の論理演算子です: {key}")
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


def _normalised(embeddings) -> np.ndarray:
    """L2正規化する。cosine距離を内積で計算するための前提。

    呼び出し側に正規化の責任を持たせない。片方だけ正規化された状態は例外を
    出さず、距離だけを静かに狂わせる。
    """
    matrix = np.asarray(embeddings, dtype="float32")
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    if not np.all(norms > 0):
        raise VectorStoreError("ノルム0のベクトルは扱えません")
    return matrix / norms


def _text_id(text: str) -> str:
    """本文のSHA-256。短縮しない。

    切り詰めると別々の本文が同じIDになり得る。そのとき起きるのは例外ではなく、
    片方の本文が黙って消えることである。64文字の保存コストで構造的に防ぐ。
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def open_store(path: str) -> "VectorStore":
    return VectorStore(path)


class VectorStore:
    def __init__(self, path: str):
        # check_same_thread=False は Streamlit が @st.cache_resource で保持した
        # 接続を別スレッドから触るため。UIの「差分を取り込む」はこの接続から
        # 書くので、読むだけではない。
        #
        # sqlite3 が直列化するのはAPI呼び出し1回ごとであってトランザクションでは
        # ない。2セッションが同時に取り込むと、片方のcommitがもう片方の途中の
        # DELETEまで確定させ、そちらが例外で終わってもロールバックされない。
        # 実測では資料が丸ごと消え、例外は誰にも出ず、count() は新しい値を
        # 正しく返した。設計書4.2が消そうとしている故障そのものなので、
        # 書き込みは _write_lock で直列化する。
        self._connection = sqlite3.connect(path, check_same_thread=False)
        # sqlite3 は既定で外部キーを検査しない。本文の無い出現が生まれても
        # 黙って通る。削除は「出現 → 孤児の本文」の順であり正しい手順なら
        # 制約に触れないので、これが火を噴くのは手順を間違えたときだけである。
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._reject_old_schema()
        self._connection.executescript(_SCHEMA)
        self._connection.commit()
        # revisionは書き込みトランザクションの中で不可分に更新されるため、
        # これが変わっていない限り全件再読み込みは不要（Task 6のキャッシュ判定）。
        self._cached_revision = None
        self._entries = []
        self._matrix = None
        # 書き込みトランザクションを直列化する。別プロセス（=別接続）の競合は
        # SQLiteのロックが "database is locked" として表に出すが、同一接続を
        # 共有するスレッド間ではそれが一切効かない。
        self._write_lock = threading.Lock()

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
                "旧スキーマのDBです。scripts/migrate_store.py を実行して変換してください:\n"
                "    python -m scripts.migrate_store vector_store.sqlite3"
            )

    def count(self) -> int:
        """出現の数。入れた件数がそのまま返るという既存の意味を保つ。"""
        return self._connection.execute("SELECT COUNT(*) FROM occurrences").fetchone()[0]

    def chunk_count(self) -> int:
        """本文の種類数。畳み込みがどれだけ効いたかはこちらに現れる。"""
        return self._connection.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]

    def _insert(self, cursor, ids, documents, metadatas, embeddings) -> None:
        """正規化して1行ずつ書く。呼び出し側がトランザクションを持つ。

        正規化を最初に済ませるのは、1行も書く前に不正なベクトルを弾くため。
        長さ検証はさらにその前に置く。`zip` は長さが揃っていないと黙って
        短い方に切り詰める。`replace` の中でこれが起きると、DELETEで旧チャンクを
        消した後に新チャンクの一部だけを書いてコミットしてしまい、「帳簿は
        進んだのに実体が欠けている」という今回捨てたはずの壊れ方を作ってしまう。

        本文が同じならベクトルも同じなので、通常この UPDATE は無駄である。
        しかし埋め込みモデルを差し替えて入れ直したとき、IGNORE では古いモデルの
        ベクトルが残る。件数は正しく、例外も出ず、距離だけが静かに狂う。
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

    def add(self, ids, documents, metadatas, embeddings) -> None:
        with self._write_lock, self._connection:
            self._insert(
                self._connection, ids, documents, metadatas, embeddings
            )
            self._delete_orphan_chunks(self._connection)
            self._bump_revision(self._connection)

    def replace(self, source, ids, documents, metadatas, embeddings) -> None:
        """1つの資料のチャンクを丸ごと入れ替える。ここが原子性の要である。

        削除と追加を別々のトランザクションにしてはならない。間で落ちると
        資料が消えたまま残る。全部入るか1件も入らないかにするために、
        1つの with で囲う。
        """
        # 列とJSONで source が食い違うと、その行は source では二度と届かなく
        # なる（DELETE は列を、delete(where=) はJSONを見る）。それでも count()
        # に数えられ search にも出続ける。1つの事実に2つの帳簿を持たせない。
        mismatched = [m.get("source") for m in metadatas if m.get("source") != source]
        if mismatched:
            raise VectorStoreError(
                f"metadata の source が引数と違います: {source!r} に対して {mismatched!r}"
            )
        with self._write_lock, self._connection:
            self._connection.execute(
                "DELETE FROM occurrences WHERE source = ?", (source,)
            )
            self._insert(
                self._connection, ids, documents, metadatas, embeddings
            )
            self._delete_orphan_chunks(self._connection)
            self._bump_revision(self._connection)

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

    @staticmethod
    def _bump_revision(cursor) -> None:
        cursor.execute("UPDATE meta SET value = value + 1 WHERE key = 'revision'")

    def _rows(self):
        """(出現ID, 本文, メタデータ) を全件返す。get() の土台。"""
        return [
            (occurrence_id, text, json.loads(metadata))
            for occurrence_id, text, metadata in self._connection.execute(
                "SELECT o.id, c.text, o.metadata"
                " FROM occurrences o JOIN chunks c ON c.id = o.chunk_id"
            )
        ]

    def get(self, ids=None, where=None, limit=None, include=None) -> dict:
        """条件に合うチャンクを返す。

        include は ChromaDB との互換のために受け取るが無視する。686件では
        取捨選択に意味が無く、引数を見て分岐するほうがバグを生む。
        """
        rows = self._rows()
        if ids is not None:
            # 呼び出し側が渡した並びを保つ。現在の消費者はどちらも自前で
            # 組み直しており（scripts/check_retrieval.py は「getは並び順を
            # 保証しない」前提で書かれている）依存はしていないが、返り値だけで
            # 対応付けできるほうが誤用を生みにくい。
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

    def search(self, vector, limit: int):
        """cosine距離の小さい順に返す。

        距離は 1 - 内積（両者をL2正規化）で、ChromaDBの hnsw:space="cosine" と
        同一の定義である。ここを変えると ingest/retrieval.py の
        RELEVANCE_THRESHOLD をはじめ、scripts/check_retrieval.py で積み上げた
        実測値がすべて意味を失う。しかも例外は出ない。
        """
        entries, matrix = self._current()
        if not entries:
            return []
        query = _normalised([vector])[0]
        distances = 1.0 - matrix @ query
        count = min(limit, len(entries))
        # argpartition は上位count件を選ぶだけで並べない。そのあと選んだ分だけ整列する。
        candidates = np.argpartition(distances, count - 1)[:count]
        # 同点はチャンクIDで決める。distanceだけで並べると、同点の中の順序が
        # argpartitionの内部実装やSELECTの物理順（rowid）に依存してしまう。
        # ingest/retrieval.py の rrf_score 計算はこの順位を土台にしており、
        # そこでも同じ理由（再現性）で同点をIDまで含めた全順序にしている。
        ordered = sorted(candidates, key=lambda i: (float(distances[i]), entries[i][0]))
        return [
            (entries[i][0], float(distances[i]), entries[i][1], entries[i][2])
            for i in ordered
        ]
