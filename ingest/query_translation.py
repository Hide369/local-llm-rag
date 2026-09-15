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

    「節の名前に寄せた語を選べ」という指示をここへ足す案を2通り測って、どちらも
    入れていない（実測 2026-09-14、docs/コーディング対応ライブラリ.md
    「翻訳プロンプトを直そうとして、やめた」）。1問を救う代わりに1〜2問を落とす
    のに加え、プロンプトを伸ばすと gpt-oss:20b が空文字を返す頻度が上がり、
    translate_query が原文へフォールバックする。文言を足す前にここを読むこと。
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


def _topic_prompt(request: str) -> str:
    """依頼から「調べるべき話題」を引き出すプロンプト。

    translate_query の文面を流用しない。あちらは「訳せ」と言っており、依頼を
    渡せば依頼のまま訳される。ここで要るのは訳ではなく、何を調べるかである。

    「write / create のような語を入れるな」と明示するのは、実測でその語が
    残ったクエリがリランカーに切られていたためである（topic_query の docstring
    に数字がある）。言語名・ライブラリ名・API名は残させる。translate_query の
    コメントにあるとおり、API名を引き出せるかどうかが検索精度を左右する。
    """
    return (
        "あなたは技術ドキュメント検索のためのクエリ作成者です。\n"
        "次は、ソースコードや文書を書く依頼です。この依頼に答えるために"
        "技術ドキュメントで何を調べるべきかを考え、英語の検索クエリを"
        "1つ作ってください。\n"
        "依頼文を翻訳しないでください。調べる話題を短いキーワードの並びで"
        "表してください。\n"
        "write, create, implement のような「書く」ことを指す語は"
        "入れないでください。\n"
        "言語名・ライブラリ名・関数名などのAPI名が推測できる場合は、"
        "必ず含めてください。\n"
        '次のJSON形式だけを返してください。説明や前置きは書かないでください。\n'
        '{"query": "検索クエリ"}\n\n'
        f"依頼: {request}"
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
    return _ask_for_query(_prompt(query), query, ask)


def _ask_for_query(prompt: str, fallback: str, ask) -> str:
    """LLM に検索クエリを1つ作らせる。使えない返答なら fallback を返す。

    translate_query と topic_query が共有する。プロンプトだけが違い、返答の
    検証は同じものでなければならない。2つに分けると、片方にだけ検証が足された
    状態が例外を出さずに成立する。
    """
    if not fallback or not fallback.strip():
        return fallback
    try:
        raw = ask(prompt)
    except Exception:  # LLM側の事情で検索まで巻き添えにしない
        return fallback
    try:
        loaded = json.loads(raw)
    except (TypeError, ValueError):
        return fallback
    if not isinstance(loaded, dict):
        return fallback
    made = loaded.get("query")
    if not isinstance(made, str):
        return fallback
    # 前後の引用符（モデルがJSON文字列の中でさらに引用符を書いた場合）を落とす。
    made = made.strip().strip('"').strip("'").strip()
    if not made or len(made) > _MAX_QUERY_LENGTH:
        return fallback
    return made


def topic_query(request: str, ask) -> str:
    """生成の依頼文から、技術ドキュメントで調べるべき話題の検索クエリを作る。

    translate_query は「検索クエリを英語にする」ものであり、入力が質問なら
    質問のまま訳す。Cowork の入力は「〜を書いて」という依頼であり、訳しても
    依頼のまま届く。リランカーは「この文章はこの問いに答えているか」を測るので、
    依頼に対しては話題が合っていても低いスコアしか付けない。

    実測 2026-09-15（docs_store.sqlite3 54,054チャンク、bge-reranker-v2-m3、
    DOCS_RERANK_FLOOR = 1.0）:
        "How do goroutines work in Go?"      最高  2.87  → 床を通り3件残る
        "Go で取り込み処理を書いて"             最高 -2.01  → 全件却下
        "Write an ingestion routine in Go"   最高 -3.82  → 全件却下
        "Go file reading and io package"     最高  2.76  → 通る
    日本語の依頼での1位は go-spec.md であり、**話題は当たっていた**。落として
    いたのは形である。

    床を下げる案は採れない。同じ実測で、関連する依頼の最低(-3.82)が無関係な
    依頼の最高(-0.79)を下回っており、どこに床を引いても分離できない。

    この関数を通した後の実測（同じ日・同じ条件、クエリ生成は qwen2.5:7b-instruct。
    **本番の gpt-oss:20b では測れていない**——手元の Ollama に無いため）:
        依頼                              作られたクエリ                最高   床通過
        Go で JSON を解析する…            Go parse JSON library        1.76    1件
        Go で取り込み処理を…              Go import processing         1.26    1件
        C# で CSV を読む…                 C# read CSV class           -1.61    0件
        Python で asyncio を…             Python asyncio example       4.00    4件
        経費精算の規程について…            expense reimbursement …     -1.27    0件
        第5回 AI活用検討会の議事録…        5th AI … meeting minutes    -3.09    0件
    関連4問中3問が床を通り（修正前は Go の取り込みが -3.82 で全滅）、無関係2問は
    どちらも0件のままである。

    C# の CSV だけ 0件 が残る。CSV の読み書きは言語仕様ではなくクラスライブラリの
    話題であり、このコーパス（csharp は language-reference と spec）に無い可能性が
    高い。その場合の0件は正しい結果である。コーパスを足したら測り直すこと。

    失敗時に request をそのまま返すのは translate_query と同じ判断である。
    検索の的が外れるだけに留め、生成そのものは止めない。
    """
    return _ask_for_query(_topic_prompt(request), request, ask)
