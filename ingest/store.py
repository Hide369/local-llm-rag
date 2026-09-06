"""取り込みドメインの操作。

差分判定に使う file_hash は各チャンクのメタデータに持たせる。別途マニフェスト
ファイルを置くとDBとファイルで状態が二重管理になり、必ず食い違うため。
信頼できる情報源は常にDBひとつにする。

ストレージの詳細（SQLite・正規化・トランザクション）は ingest/vector_store.py に
置く。このモジュールは「資料単位で入れ替える」「source/ から消えた資料を消す」
という取り込みの都合だけを持つ。
"""
from pathlib import Path

from ingest.models import Chunk
from ingest.vector_store import open_store  # noqa: F401  再公開

DB_FILENAME = "vector_store.sqlite3"
# パスの単一の情報源。呼び出し側が各自で組み立てると、片方だけ間違えても
# open_store は例外を出さずに空のDBを新規作成するため、件数0で検索が全部空に
# なるだけで、テストも緑のまま通ってしまう。
DB_PATH = Path(__file__).resolve().parent.parent / DB_FILENAME


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
