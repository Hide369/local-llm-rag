"""ハイブリッド検索のしきい値と回帰ケースを実測する。

判定は2つある。

1. ゲートの分離: 関連する質問の最大距離 ≤ RELEVANCE_THRESHOLD < 圏外の質問の最小距離。
   ベクトル側は圏内・圏外を分ける唯一の関門なので、ここが崩れると圏外の質問にも
   回答してしまう。成り立たない場合はしきい値の再調整か、チャンクサイズ・
   埋め込みモデルの見直しが必要。
2. 回帰ケース: 設計書 第1節の2問で、BM25側の上位に期待する出典が入ること。
   圏内と判定された質問のBM25ヒットはスコアを問わず採用されるため、これがそのまま
   「欲しいチャンクが根拠に入るか」になる。

数値のBM25_FLOORは設けない。理由は main() 末尾のコメントを参照。

挨拶のような意味的に空な入力は、コーパスの重心付近に埋め込まれるため、際どい
（弱い）関連質問と距離だけでは分離できない。これは実測で確認された構造的な限界で
あり、合否判定の対象には含めない。挨拶は元からベクトル側のゲートを通っており
（実測0.349〜0.381）、ゲート方式でもこの扱いは変わらない。この入力は
ingest/prompting.py の「根拠がなければ答えない」プロンプトが受け持つ。
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
    # 前者はベクトル4位で足切りされ、後者はベクトル最良が全滅していた。
    # 再チャンク化後の実測では両方ともゲートを通る（0.414 / 0.456）。詳しくは REGRESSION を参照。
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

# 設計書 第1節の発端となった2問。ゲート方式では圏内と判定された質問のBM25ヒットが
# スコアを問わず採用されるため、BM25側の上位に期待する出典が入るかがそのまま合否になる。
# 再チャンク化前の実測では「ファインチューニング」単独でスライド11が4位0.529と
# 足切りされていた。「ファインチューニングについて教えてほしい」は再チャンク化後
# スライド11が0.486でベクトル側を単独でも通る（現在はどちらもRELEVANTのしきい値
# 内に収まる。詳しくはRELEVANTのコメントを参照）。
# RELEVANT にも入れてあるのは、距離の分離判定にこの2問も含めるためである。
REGRESSION = [
    "ファインチューニングについて教えてほしい",
    "ファインチューニング",
]
REGRESSION_EXPECTED = "生成AI活用セミナー.pptx スライド11"
REGRESSION_TOP_N = 3


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


def _lexical_top(collection, index, question, limit):
    """BM25側の上位を (出典, スコア) の並びで返す。スコアの高い順。

    collection.get はIDの並び順を保証しないため、取得したメタデータを引き当てて
    lexical.search が返した順に組み直す。
    """
    ranked = lexical.search(index, question, limit=limit)
    if not ranked:
        return []
    found = collection.get(
        ids=[chunk_id for chunk_id, _ in ranked], include=["documents", "metadatas"]
    )
    metadata_by_id = dict(zip(found["ids"], found["metadatas"]))
    return [
        (Hit(text="", distance=None, metadata=metadata_by_id[chunk_id]).citation, score)
        for chunk_id, score in ranked
        if chunk_id in metadata_by_id
    ]


def _lexical_best(collection, index, question):
    """BM25側の最良ヒット。スコアと出典を返す。該当なしは (0.0, "—")。"""
    top = _lexical_top(collection, index, question, 1)
    if not top:
        return 0.0, "—"
    citation, score = top[0]
    return score, citation


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
    relevant_min_bm25 = min(score for _, score in relevant)

    print(f"\n=== 回帰ケース（BM25側の上位{REGRESSION_TOP_N}件）===")
    regression_ok = True
    for question in REGRESSION:
        top = _lexical_top(collection, index, question, REGRESSION_TOP_N)
        hit = any(citation.startswith(REGRESSION_EXPECTED) for citation, _ in top)
        regression_ok = regression_ok and hit
        print(f"  {question} — {'OK' if hit else 'NG'}")
        for rank, (citation, score) in enumerate(top, start=1):
            print(f"      {rank}. {score:6.2f}  {citation}")

    print(f"\n関連の最大距離: {relevant_max_distance:.3f}")
    print(f"圏外の最小距離: {out_of_domain_min_distance:.3f}")
    # 数値のBM25_FLOORを設けない理由の記録。境界の片側（圏外の最大BM25）だけでは
    # 床が引けるかどうか判断できないため、圏内側の最小BM25（関連する質問のBM25
    # 最良スコアの最小値）も測って両側を並べる。結果は 関連の最小 < 圏外の最大
    # であり、圏内・圏外の2つの集団はBM25スコアだけでは順方向にも逆方向にも
    # 分離していない。つまり床は「一応引ける」どころか、どこに引いても
    # 関連質問を落とすか圏外質問を通すかのどちらかになる。加えてBM25スコアは
    # 正規化されておらずクエリ長にほぼ比例するため、長い圏外質問ひとつで
    # 容易に逆転もする。ゲート方式は距離だけで圏外を落とすのでこの脆さを
    # 持たない。将来また床を検討する人のために両側の測定値を残す。
    print(f"圏外の最大BM25（参考。床は設けない）: {out_of_domain_max_bm25:.2f}")
    print(f"関連の最小BM25（参考。床はこれ以下でないと関連質問を落とす）: {relevant_min_bm25:.2f}")

    # 実測が分離しているだけでは足りない。実際のゲートは RELEVANCE_THRESHOLD で
    # 切るので、その定数が実測値の間に収まっていることまで確かめる。
    separated = relevant_max_distance <= RELEVANCE_THRESHOLD < out_of_domain_min_distance
    if separated:
        print(
            f"ゲートは分離できています: {relevant_max_distance:.3f} ≤ "
            f"{RELEVANCE_THRESHOLD} < {out_of_domain_min_distance:.3f}"
        )
    else:
        print(
            f"ゲートが分離できていません（RELEVANCE_THRESHOLD={RELEVANCE_THRESHOLD}）。"
            "しきい値の再調整か、チャンクサイズ・埋め込みモデルの見直しが必要です。"
        )
    if not regression_ok:
        print(
            f"回帰ケースが失敗しています。BM25側の上位{REGRESSION_TOP_N}件に "
            f"{REGRESSION_EXPECTED} が入りません。"
        )
    return 0 if separated and regression_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
