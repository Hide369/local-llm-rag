"""ベクトル検索と出典の組み立て。

足切りをしないと、挨拶のような検索対象外の入力でも必ず最近傍が1件返ってきて、
無関係な文書がコンテキストに紛れ込む。
"""
from dataclasses import dataclass

from ingest import lexical, store
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

# 各アームから取る候補数。融合してから採否を決めるため、しきい値付近のチャンクが
# 片方のアームで圏外に落ちないよう、採用件数より十分に大きく取る。
CANDIDATE_COUNT = 30

# RRFの定数。順位の逆数を足し合わせるときに上位の影響を和らげる。60は慣用値。
RRF_K = 60


@dataclass(frozen=True)
class Hit:
    text: str
    distance: float | None
    metadata: dict
    # BM25だけで当たった場合は distance が None、ベクトルだけで当たった場合は
    # bm25_score が None になる。どちらの経路で拾ったかを画面に出すために持つ。
    bm25_score: float | None = None
    rrf_score: float = 0.0

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


def _vector_candidates(collection, query, session):
    """(チャンクID → 順位) と、IDをキーにした (距離, 本文, メタデータ) を返す。"""
    results = collection.query(
        query_embeddings=[embed_query(query, session=session)],
        n_results=CANDIDATE_COUNT,
    )
    ids = results["ids"][0]
    ranks = {chunk_id: rank for rank, chunk_id in enumerate(ids, start=1)}
    rows = {
        chunk_id: (distance, text, metadata)
        for chunk_id, distance, text, metadata in zip(
            ids,
            results["distances"][0],
            results["documents"][0],
            results["metadatas"][0],
        )
    }
    return ranks, rows


def search(
    collection,
    query,
    index=None,
    session=None,
    threshold=None,
    n_results=SEARCH_RESULT_COUNT,
):
    """ベクトル検索とBM25を融合して検索する。

    index を渡さないとベクトル単独で動く。BM25を必要としない呼び出しのために残してある。

    並べ替えはRRFで行う。cosine距離とBM25スコアは互いに正規化できず、重み付き和は
    意味を持たないためである。一方でRRFスコアは順位のみに依存し、圏外の質問でも
    1位は必ず 1/(RRF_K+1) を得るため、採否の判定には使えない。

    採否はベクトル側を圏内判定の関門にする。ベクトル側に閾値を通った候補が1件でも
    あればその質問は資料で答えられるものとみなし、BM25側のヒットもスコアを問わず
    採用する。BM25スコアに下限を設けないのは、スコアが正規化されておらずクエリ長に
    ほぼ比例するからである。実測では長い圏外質問が29.87、短い圏内質問が35.93で
    差は6.06しかなく、長い圏外質問ひとつで逆転する。距離のほうは関連の最大0.456・
    圏外の最小0.522で分離しており、こちらを関門にするほうが堅い。
    いずれも scripts/check_retrieval.py の実測。資料を入れ替えたら再実測すること。
    """
    if collection.count() == 0:
        return []
    limit = threshold if threshold is not None else RELEVANCE_THRESHOLD

    vector_ranks, vector_rows = _vector_candidates(collection, query, session)
    # 圏内判定はベクトル側だけで行う。Chromaは距離の昇順で返すので、
    # 1件でも閾値を通っていればこの質問は圏内である。
    in_domain = any(distance <= limit for distance, _, _ in vector_rows.values())

    lexical_ranked = lexical.search(index, query, CANDIDATE_COUNT) if index else []
    lexical_scores = dict(lexical_ranked)
    lexical_ranks = {
        chunk_id: rank for rank, (chunk_id, _) in enumerate(lexical_ranked, start=1)
    }

    # BM25だけで当たったチャンクは本文もメタデータも持っていないので取りに行く。
    missing = [chunk_id for chunk_id in lexical_scores if chunk_id not in vector_rows]
    if missing:
        found = collection.get(ids=missing, include=["documents", "metadatas"])
        for chunk_id, text, metadata in zip(
            found["ids"], found["documents"], found["metadatas"]
        ):
            vector_rows[chunk_id] = (None, text, metadata)

    hits = []
    for chunk_id in set(vector_ranks) | set(lexical_ranks):
        row = vector_rows.get(chunk_id)
        # インデックスは起動時のスナップショットである。取り込みで消えたチャンクの
        # IDが残っていることがあり、collection.get はその行を返さない。
        if row is None:
            continue
        distance, text, metadata = row
        score = lexical_scores.get(chunk_id)
        near = distance is not None and distance <= limit
        if not text or not (near or (in_domain and score is not None)):
            continue
        rrf_score = 0.0
        if chunk_id in vector_ranks:
            rrf_score += 1 / (RRF_K + vector_ranks[chunk_id])
        if chunk_id in lexical_ranks:
            rrf_score += 1 / (RRF_K + lexical_ranks[chunk_id])
        hits.append(
            Hit(
                text=text,
                distance=distance,
                metadata=metadata,
                bm25_score=score,
                rrf_score=rrf_score,
            )
        )
    # 同点はベクトル距離の昇順、次にBM25スコアの降順で決める。並びを決定的に
    # しないと、同じ質問で根拠の順序が変わって再現しなくなる。
    hits.sort(
        key=lambda hit: (
            -hit.rrf_score,
            hit.distance if hit.distance is not None else 99.0,
            -(hit.bm25_score or 0.0),
        )
    )
    return hits[:n_results]


def build_index(collection):
    """DBの全チャンクからBM25インデックスを組む。

    永続化しないのは、DBとファイルで状態が二重管理になると差分取り込みの
    たびに食い違い、例外も出ないまま検索結果が古くなるためである。
    """
    return lexical.build(*store.all_documents(collection))
