"""ベクトル検索と出典の組み立て。

足切りをしないと、挨拶のような検索対象外の入力でも必ず最近傍が1件返ってきて、
無関係な文書がコンテキストに紛れ込む。
"""
from dataclasses import dataclass

from ingest.embedder import embed_query

SEARCH_RESULT_COUNT = 4

# 検索結果を採用するcosine距離のしきい値（0に近いほど類似）。
# scripts/check_retrieval.py の実測（bge-m3 / 279チャンク。MIN_CHUNK_CHARS導入で
# 内容のない1字チャンクを取り除いた後の再測定）:
#   関連する質問の最大距離 = 0.459、圏外の質問の最小距離 = 0.549
# この2つの間を取っている。扱う資料を入れ替えたら再度実測して調整すること。
# 挨拶のような意味的に空な入力（実測 0.412〜0.436）は距離では切り分けられない。
# コーパスの重心付近に落ちるためで、これは ingest/prompting.py の
# 「根拠がなければ答えない」プロンプトが受け持つ。
RELEVANCE_THRESHOLD = 0.50


@dataclass(frozen=True)
class Hit:
    text: str
    distance: float
    metadata: dict

    @property
    def citation(self) -> str:
        """「ファイル名 p.48（OCR）」の形式で出典を組み立てる。"""
        source = self.metadata.get("source", "")
        location_type = self.metadata.get("location_type")
        location = self.metadata.get("location")
        if location_type == "page":
            source = f"{source} p.{location}"
        elif location_type == "slide":
            source = f"{source} スライド{location}"
        if self.metadata.get("ocr"):
            source = f"{source}（OCR）"
        return source


def search(collection, query, session=None, threshold=None, n_results=SEARCH_RESULT_COUNT):
    if collection.count() == 0:
        return []
    limit = threshold if threshold is not None else RELEVANCE_THRESHOLD
    results = collection.query(
        query_embeddings=[embed_query(query, session=session)], n_results=n_results
    )
    hits = zip(
        results["documents"][0], results["distances"][0], results["metadatas"][0]
    )
    return [
        Hit(text=text, distance=distance, metadata=metadata)
        for text, distance, metadata in hits
        if text and distance <= limit
    ]
