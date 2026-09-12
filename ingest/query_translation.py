"""技術ドキュメント検索のためだけに、検索クエリを英語へ翻訳する。

内部コーパス（社内資料）は日本語で書かれており、BM25（ingest/lexical.py の
文字bigram）もRELEVANCE_THRESHOLDも日本語のテキストに合わせて調整済みである。
一方、scripts/fetch_docs.py で取り込む技術ドキュメント（streamlit,
langchain-text-splitters, ollama, huggingface_hub, pymupdf、計11,993チャンク）は
英語で書かれている。日本語の質問をそのまま埋め込み・BM25にかけると、コーパスと
質問の言語が食い違い、検索そのものが成立しない。

実測（gpt-oss:20b、docs_store.sqlite3、2026-09-12）:
    - 「Streamlitのキャッシュはどう書く？」（日本語）
      → 1位はCLIコマンド `streamlit cache clear`。リランカーは0.06、
        以降-3.33, -3.45, -4.66（シグモイド化前のロジット）。
    - 「How do I cache data in Streamlit?」（英語）
      → Cachingの節、続けて `@st.cache_data` の例。リランカー5.73。
    - 「st.cache_data」（API名そのもの）
      → 該当箇所にほぼ完全一致。リランカー7.02。
内部にcache_dataを含むチャンクは56件、dialogを含むチャンクは47件あり、
「資料に記述がありません」という回答は検索が的外れだったために起きていた
（モデルの誤りではない）。日本語の質問のまま英語クエリで検索し直すと、
`st.cache_data` の実例や `st.dialog` の現行シグネチャ、`st.mermaid_chart` が
的確に引けることを確認済み。つまり生成（回答文面）は原文の日本語質問のままで
問題なく、直す必要があるのは検索クエリだけである。

このモジュールは検索クエリの翻訳だけを行い、生成には一切関与しない。
呼び出し側（rag_chat_app.py）は、この関数の戻り値を search() にだけ渡し、
build_docs_prompt(question, hits) には必ず原文の質問を渡すこと。翻訳を誤っても
検索の的が外れるだけに留め、回答文の生成過程を汚染しないための設計である。

ingest/conditions.py と同じ理由で、LLMの呼び出しは ask として外から渡す。
ここをモジュール内でOllamaクライアントに束縛すると、翻訳規則のテストに
実機のOllamaが要るようになるため。
"""
import json

# 検索クエリとして想定する長さを大きく超える返答は、プロンプトの「短いクエリで」
# という指示を無視して文章を書いたとみなし、破棄して原文へフォールバックする。
# 実在のAPI名を含む検索クエリ（例: "modal dialog st.dialog"）は十分収まる長さである。
_MAX_QUERY_LENGTH = 200


def _prompt(query: str) -> str:
    """翻訳プロンプト。

    「丁寧な英文ではなく検索クエリを」「API名が分かれば必ず含める」の2点を
    明記しているのは、実測で API名（st.cache_data）を含むクエリがリランカー
    7.02、英語の丁寧文が5.73、日本語原文が0.06〜-4.66 だったため。API名を
    引き出せるかどうかが最終的な検索精度を左右する。
    """
    return (
        "あなたは技術ドキュメント検索のためのクエリ翻訳者です。\n"
        "次の検索クエリを、英語で書かれた技術ドキュメントを検索するための"
        "英語の検索クエリに翻訳してください。\n"
        "既に英語で書かれている場合は、そのまま（必要なら軽く整えるだけで）"
        "返してください。\n"
        "関数名・クラス名・メソッド名などのAPI名（例: st.cache_data, st.dialog）が"
        "推測できる場合は、翻訳した文章ではなく、そのAPI名を必ず含めてください。\n"
        "丁寧な英文の質問ではなく、検索エンジンに打ち込むような短いキーワードの"
        "並びにしてください。\n"
        '次のJSON形式だけを返してください。説明や前置きは書かないでください。\n'
        '{"query": "翻訳した検索クエリ"}\n\n'
        f"検索クエリ: {query}"
    )


def translate_query(query: str, ask) -> str:
    """検索クエリを英語へ翻訳する。失敗時は原文の query をそのまま返す。

    ここでの「失敗」は例外だけでなく、JSONとして壊れている・queryが空や
    文字列以外・想定より長すぎる（説明文を書いてしまった）場合も含む。
    いずれも例外を投げず、今日までの「日本語のまま検索する」動作へ静かに
    フォールバックする。翻訳が壊れても質問への回答自体は止めない
    （ingest/conditions.py の extract が failed=True で通常検索に落とすのと
    同じ考え方だが、こちらは利用者に伝えるべき失敗ではないため
    Extraction のような通知用の型は持たない）。
    """
    if not query or not query.strip():
        return query
    try:
        raw = ask(_prompt(query))
    except Exception:  # LLM側の事情で検索まで巻き添えにしない
        return query
    try:
        loaded = json.loads(raw)
    except (TypeError, ValueError):
        return query
    if not isinstance(loaded, dict):
        return query
    translated = loaded.get("query")
    if not isinstance(translated, str):
        return query
    # 前後の引用符（モデルがJSON文字列の中でさらに引用符を書いた場合）を落とす。
    translated = translated.strip().strip('"').strip("'").strip()
    if not translated or len(translated) > _MAX_QUERY_LENGTH:
        return query
    return translated
