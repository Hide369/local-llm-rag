"""関連度しきい値を決めるために距離を実測する。

関連する質問の最大距離 < 圏外の質問の最小距離 が成り立てば足切りが機能する。
成り立たない場合はチャンクサイズか埋め込みモデルの見直しが必要。

挨拶のような意味的に空な入力は、コーパスの重心付近に埋め込まれるため、際どい
（弱い）関連質問と距離だけでは分離できない。これは実測で確認された構造的な
限界であり、合否判定の対象には含めない。この入力は Task 10 の
ingest/prompting.py にある「根拠がなければ答えない」プロンプトが受け持つ。
"""
import chromadb

from ingest import embedder, store
from ingest.retrieval import search
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


def main() -> int:
    embedder.check_ollama()
    collection = store.open_collection(chromadb.PersistentClient(path=str(DB_DIR)))
    print(f"総チャンク数: {collection.count()}\n")

    session = embedder.new_session()
    try:
        relevant_max = 0.0
        print("=== 関連する質問（最も近いチャンクとの距離） ===")
        for question in RELEVANT:
            hits = search(collection, question, session=session, threshold=99.0, n_results=1)
            distance = hits[0].distance
            relevant_max = max(relevant_max, distance)
            print(f"  {distance:.3f}  {question}  → {hits[0].citation}")

        out_of_domain_min = 99.0
        print("\n=== 圏外の質問（最も近いチャンクとの距離） ===")
        for question in OUT_OF_DOMAIN:
            hits = search(collection, question, session=session, threshold=99.0, n_results=1)
            distance = hits[0].distance
            out_of_domain_min = min(out_of_domain_min, distance)
            print(f"  {distance:.3f}  {question}  → {hits[0].citation}")

        print("\n=== 挨拶（参考値。距離では分離できないため合否判定には使わない） ===")
        print(
            "  意味的に空な入力はコーパスの重心付近に埋め込まれるため、際どい関連質問"
            "より近傍にヒットすることがある。ingest/prompting.py の「根拠がなければ"
            "答えない」プロンプトがこの入力を受け持つ。"
        )
        for question in GREETINGS:
            hits = search(collection, question, session=session, threshold=99.0, n_results=1)
            distance = hits[0].distance
            print(f"  {distance:.3f}  {question}  → {hits[0].citation}")
    finally:
        session.close()

    print(f"\n関連の最大: {relevant_max:.3f}")
    print(f"圏外の最小: {out_of_domain_min:.3f}")
    if relevant_max < out_of_domain_min:
        print(f"分離できています。推奨しきい値: {(relevant_max + out_of_domain_min) / 2:.3f}")
        return 0
    print("分離できていません（挨拶を除く）。チャンクサイズか埋め込みモデルの見直しが必要です。")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
