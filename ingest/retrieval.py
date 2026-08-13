"""ベクトル検索と出典の組み立て。

足切りをしないと、挨拶のような検索対象外の入力でも必ず最近傍が1件返ってきて、
無関係な文書がコンテキストに紛れ込む。
"""
from dataclasses import dataclass

from ingest.embedder import embed_query

SEARCH_RESULT_COUNT = 4

# 検索結果を採用するcosine距離のしきい値（0に近いほど類似）。
# scripts/check_retrieval.py の実測（bge-m3 / 約460チャンク、うち家電製品仕様書
# 181チャンク。社内文書と製品カタログが混在した状態で、機種の照会と条件による
# 絞り込みの両方を含む質問で再測定した）:
#   関連する質問の最大距離 = 0.459、圏外の質問の最小距離 = 0.549
# 家電製品の質問はいずれも0.286〜0.361に収まり、279チャンク時点の最大・最小
# （社内文書のみの質問由来）を更新しなかった。この2つの間を取っている。
# 扱う資料を入れ替えたら再度実測して調整すること。
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
        """「ファイル名 p.48（OCR）」の形式で出典を組み立てる。

        出典整形はここが唯一の置き場所である。位置種別を増やすときはこのメソッドだけを直す。
        """
        source = self.metadata.get("source", "")
        location_type = self.metadata.get("location_type")
        location = self.metadata.get("location")
        if location_type == "page":
            source = f"{source} p.{location}"
        elif location_type == "slide":
            source = f"{source} スライド{location}"
        elif location_type == "section":
            # 見出し文字列で示す。通し番号（location）は利用者にとって意味がない。
            heading = self.metadata.get("heading")
            if heading:
                source = f"{source} ＞ {heading}"
        if self.metadata.get("ocr"):
            source = f"{source}（OCR）"
        return source


def contextual_query(question: str, history) -> str:
    """直前の質問を検索クエリの前に置く。

    「決定事項を教えてほしい」のような追質問は、それ単独では検索できない。実測では
    上位4件が導入ガイドPDFと就業規則で埋まり、議事録は1件も入らなかった
    （距離0.456〜0.459）。直前の質問を継ぎ足すと第5回議事録が0.401で1位になる。

    継ぎ足すのは直前の1問だけである。履歴を全部つなぐと古い話題がクエリを引っ張る。
    話題が変わったときは継ぎ足した分が雑音になるが、実測では順位は保たれた
    （有給休暇の質問に会議の質問を継ぎ足しても就業規則が1位。距離は0.296→0.352）。

    LLMによる書き換えを使わないのは、1問あたり数秒の追加コストを避けるため。
    llama3.1:8b はこのPCで8トークン毎秒しか出ない。

    history は Streamlit の会話履歴（role/content の辞書の並び）で、今回の質問は
    含めない。
    """
    previous = next(
        (
            message["content"]
            for message in reversed(history)
            if message.get("role") == "user"
        ),
        None,
    )
    return f"{previous} {question}" if previous else question


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
