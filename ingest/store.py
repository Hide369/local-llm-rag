"""ChromaDBへの保存と差分管理。

差分判定に使う file_hash は各チャンクのメタデータに持たせる。別途マニフェスト
ファイルを置くとDBとファイルで状態が二重管理になり、必ず食い違うため。
信頼できる情報源は常にDBひとつにする。
"""
from ingest.models import Chunk

# udemy3.py が使う local_docs (nomic-embed-text / 768次元) とは別に作る。
# 同じコレクションを使い回すと次元不一致で既存の教材が動かなくなる。
COLLECTION_NAME = "local_docs_v2"
DISTANCE_SPACE = "cosine"


def open_collection(client):
    return client.get_or_create_collection(
        name=COLLECTION_NAME, metadata={"hnsw:space": DISTANCE_SPACE}
    )


def stored_file_hash(collection, source: str) -> str | None:
    """登録済みならそのファイルのハッシュを返す。未登録ならNone。"""
    found = collection.get(where={"source": source}, limit=1, include=["metadatas"])
    metadatas = found.get("metadatas") or []
    return metadatas[0].get("file_hash") if metadatas else None


def replace_source(collection, source: str, chunks: list[Chunk], embeddings) -> None:
    """1つの資料のチャンクを丸ごと入れ替える。

    先に古いチャンクを消してから入れる。ページ数が減った資料を再取り込みしたとき、
    上書きだけでは末尾の古いページが残ってしまうため。
    """
    collection.delete(where={"source": source})
    if not chunks:
        return
    collection.add(
        ids=[chunk.id for chunk in chunks],
        documents=[chunk.text for chunk in chunks],
        metadatas=[chunk.metadata for chunk in chunks],
        embeddings=list(embeddings),
    )


def indexed_sources(collection) -> set[str]:
    if collection.count() == 0:
        return set()
    metadatas = collection.get(include=["metadatas"]).get("metadatas") or []
    return {meta["source"] for meta in metadatas if "source" in meta}


def delete_orphans(collection, known_sources: set[str]) -> list[str]:
    """source/ に存在しなくなった資料のチャンクを削除し、削除した資料名を返す。"""
    orphans = sorted(indexed_sources(collection) - set(known_sources))
    for source in orphans:
        collection.delete(where={"source": source})
    return orphans
