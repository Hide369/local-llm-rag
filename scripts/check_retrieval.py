"""BM25_FLOORを決めるために、ベクトルとBM25の両アームを実測する。

関連する質問の最大距離 < 圏外の質問の最小距離 が成り立てば足切りが機能する。
成り立たない場合はチャンクサイズか埋め込みモデルの見直しが必要。

挨拶のような意味的に空な入力は、コーパスの重心付近に埋め込まれるため、際どい
（弱い）関連質問と距離だけでは分離できない。これは実測で確認された構造的な
限界であり、合否判定の対象には含めない。この入力は Task 10 の
ingest/prompting.py にある「根拠がなければ答えない」プロンプトが受け持つ。
"""
import chromadb

from ingest import embedder, lexical, store
from ingest.retrieval import RELEVANCE_THRESHOLD, Hit, build_index
from scripts.ingest_source import DB_DIR

# 取り込んだ資料に確実に答えがある質問
RELEVANT = [
    "懲戒解雇となるのはどのような場合ですか",
    "裁判員になったとき休暇はもらえますか",
    "育児休業は誰が取得できますか",
    "コンテキスト使用率の危険ラインは何％ですか",
    "本コースで選んだRAGの手法は何ですか",
    "セミナーの講師は誰ですか",
    "AI活用プロジェクトの初期スコープは何ですか",
    # 上の「セミナーの講師は誰ですか」の言い換え。他の言い回しでも同じように際どい
    # 距離になるかを確かめる追加データ点であり、元の質問の置き換えではない。
    "講師の名前を教えてください",
    # 家電製品の仕様書（source/家電製品/）。特定機種の照会と条件による絞り込みの両方を測る。
    "UD-0900iの設置に必要な防水パンの奥行きは何ミリですか",
    "UD-0900iの乾燥方式は何ですか",
    "スマートフォンから遠隔操作できる洗濯機はどれですか",
    "一人暮らし向けのコンパクトな洗濯機を教えてください",
    # ハイブリッド検索の回帰ケース（spec 1）。いずれも
    # 「生成AI活用セミナー.pptx スライド11」が出典として期待される。
    # 前者はベクトル4位・距離0.514で足切りされ、後者はベクトル最良が0.523で全滅していた。
    "ファインチューニングについて教えてほしい",
    "ファインチューニング",
]

# 資料のどこにも答えがない「問い」。しきい値の合否判定はこちらだけで行う。
OUT_OF_DOMAIN = [
    "今日の東京の天気を教えてください",
    "おすすめのラーメン屋はどこですか",
    "1たす1はいくつですか",
]

# 意味的に空な入力（挨拶）。コーパスの重心付近にヒットするため、距離では
# 際どい関連質問と切り分けられない。参考値として記録するだけで、合否判定には使わない。
GREETINGS = [
    "こんにちは",
    "おはようございます",
    "ありがとう",
]


def _vector_best(collection, question, session):
    """ベクトル側の最良ヒット。距離と出典を返す。"""
    results = collection.query(
        query_embeddings=[embedder.embed_query(question, session=session)],
        n_results=1,
    )
    hit = Hit(
        text=results["documents"][0][0],
        distance=results["distances"][0][0],
        metadata=results["metadatas"][0][0],
    )
    return hit.distance, hit.citation


def _lexical_best(collection, index, question):
    """BM25側の最良ヒット。スコアと出典を返す。該当なしは (0.0, "—")。"""
    ranked = lexical.search(index, question, limit=1)
    if not ranked:
        return 0.0, "—"
    chunk_id, score = ranked[0]
    found = collection.get(ids=[chunk_id], include=["documents", "metadatas"])
    hit = Hit(
        text=found["documents"][0], distance=None, metadata=found["metadatas"][0]
    )
    return score, hit.citation


def _report(collection, index, session, title, questions):
    """1グループ分を表示し、(距離, BM25スコア) の並びを返す。"""
    print(f"\n=== {title} ===")
    measured = []
    for question in questions:
        distance, vector_citation = _vector_best(collection, question, session)
        score, lexical_citation = _lexical_best(collection, index, question)
        measured.append((distance, score))
        print(f"  {question}")
        print(f"      ベクトル {distance:.3f}  → {vector_citation}")
        print(f"      BM25     {score:6.2f}  → {lexical_citation}")
    return measured


def main() -> int:
    embedder.check_ollama()
    collection = store.open_collection(chromadb.PersistentClient(path=str(DB_DIR)))
    print(f"総チャンク数: {collection.count()}")
    index = build_index(collection)
    print(f"BM25インデックス: {index.document_count}文書 / {len(index.postings)}トークン")

    session = embedder.new_session()
    try:
        relevant = _report(collection, index, session, "関連する質問", RELEVANT)
        out_of_domain = _report(collection, index, session, "圏外の質問", OUT_OF_DOMAIN)
        _report(
            collection,
            index,
            session,
            "挨拶（参考値。距離では分離できないため合否判定には使わない）",
            GREETINGS,
        )
        print(
            "  意味的に空な入力はコーパスの重心付近に埋め込まれるため、際どい関連質問"
            "より近傍にヒットすることがある。ingest/prompting.py の「根拠がなければ"
            "答えない」プロンプトがこの入力を受け持つ。"
        )
    finally:
        session.close()

    relevant_max_distance = max(distance for distance, _ in relevant)
    out_of_domain_min_distance = min(distance for distance, _ in out_of_domain)
    out_of_domain_max_bm25 = max(score for _, score in out_of_domain)
    # ベクトル側の足切りを通らない関連質問は、BM25側が拾わなければ救えない。
    rescued = [score for distance, score in relevant if distance > RELEVANCE_THRESHOLD]

    print(f"\n関連の最大距離: {relevant_max_distance:.3f}")
    print(f"圏外の最小距離: {out_of_domain_min_distance:.3f}")
    print(f"圏外の最大BM25: {out_of_domain_max_bm25:.2f}")
    if rescued:
        print(f"BM25で救う必要がある関連質問の最小BM25: {min(rescued):.2f}")

    if not rescued:
        print("ベクトル側だけで全件通っています。BM25_FLOOR は現状の値のままで構いません。")
        return 0
    if out_of_domain_max_bm25 < min(rescued):
        print(f"分離できています。推奨 BM25_FLOOR: {(out_of_domain_max_bm25 + min(rescued)) / 2:.2f}")
        return 0
    print(
        "BM25では分離できていません。spec 16 の縮退構成"
        "（ベクトル側を圏内判定のゲートに使う）へ切り替えてください。"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
