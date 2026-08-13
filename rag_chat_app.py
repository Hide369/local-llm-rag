"""ローカル文書RAGチャット。

取り込み処理は ingest/ 側にあり、このファイルは表示と入出力だけを担当する。
初回の取り込みは13分かかるため、CLI (python -m scripts.ingest_source) で行う。
このUIのボタンは差分取り込み（通常は数秒）を想定している。
"""
from datetime import datetime
from pathlib import Path

import chromadb
import streamlit as st
from openai import APIError, OpenAI

from ingest import answer_text, catalog, conditions, embedder, store
from ingest.prompting import build_catalog_prompt, build_prompt, format_report
from ingest.retrieval import RELEVANCE_THRESHOLD, contextual_query, search
from scripts.ingest_source import DEFAULT_SOURCE_DIR, ingest_directory

DB_DIR = str(Path(__file__).parent / "chroma_db")


@st.cache_resource
def get_collection(db_dir):
    return store.open_collection(chromadb.PersistentClient(path=db_dir))


@st.cache_resource
def get_schema(_collection):
    """絞り込みに使える属性の一覧。起動時に1回だけ集める。

    先頭のアンダースコアは、Streamlitにこの引数をハッシュさせないための目印。
    ChromaDBのコレクションはハッシュ化できない。
    """
    return conditions.available_keys(_collection)


def render_hits(hits):
    if not hits:
        return
    with st.expander(f"参考にした情報（{len(hits)}件）"):
        for hit in hits:
            st.caption(f"{hit.citation} ／ cosine距離 {hit.distance:.3f}（しきい値 {RELEVANCE_THRESHOLD}）")
            st.write(hit.text)


def render_evidence(message):
    """根拠の表示。絞り込み経路は表を、検索経路はチャンクを見せる。"""
    if message.get("table"):
        with st.expander("絞り込んだ一覧"):
            st.code(message["table"])
    render_hits(message.get("hits"))


st.set_page_config(page_title="社内文書RAGチャット")
st.sidebar.title("設定")

model = st.sidebar.text_input("モデル名", value="llama3.1:8b")
temperature = st.sidebar.slider("Temperature", 0.0, 1.0, 0.3, 0.1)
# サイドバーには出さない。利用者に編集させる項目ではないため。
# 出典付き回答の指示は ingest/prompting.py が質問側に組み込む。ここは口調と
# 日付だけを受け持ち、検索結果の扱い方の指示とは置き場所を分けている。
SYSTEM_PROMPT = (
    f"あなたは有能なアシスタントです。今日の日付は{datetime.today():%Y年%m月%d日}です。\n"
    "日本語で回答して下さい。"
)

collection = get_collection(DB_DIR)
st.sidebar.metric("インデックス済みチャンク", collection.count())

st.sidebar.divider()
st.sidebar.caption(f"取り込み元: {DEFAULT_SOURCE_DIR.name}/")
if st.sidebar.button("差分を取り込む"):
    try:
        embedder.check_ollama()
    except embedder.EmbeddingError as error:
        st.sidebar.error(str(error))
    else:
        with st.spinner("取り込み中…"):
            report = ingest_directory(DEFAULT_SOURCE_DIR, collection)
        st.sidebar.success(format_report(report))
        st.rerun()

if st.sidebar.button("会話履歴をリセット"):
    st.session_state.messages = []
    st.rerun()

st.title("社内文書RAGチャット")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])
        render_evidence(message)

client = OpenAI(api_key="ollama", base_url=f"{embedder.OLLAMA_HOST}/v1")

schema = get_schema(collection)


def ask_json(prompt: str) -> str:
    """条件抽出用にJSONだけを返させる。

    temperature=0 なのは、同じ質問で条件が揺れると再現性のない誤りになるため。
    """
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content

question = st.chat_input("メッセージを入力")

if question:
    with st.chat_message("user"):
        st.write(question)
    st.session_state.messages.append({"role": "user", "content": question})

    extraction = conditions.extract(question, schema, ask_json)

    table = None
    hits = []
    user_content = None
    # ベクトル検索は埋め込みAPIを呼ぶ。Ollamaが止まっていればここで
    # EmbeddingError になるため、生成時（下のAPIError）と同じ見せ方に揃える。
    # 捕まえずにいると生のトレースバックが画面に出る。
    search_error = None
    try:
        if extraction.conditions:
            # 「最大の洗濯容量は」に答えるための並べ替え。最大・最小を尋ねる語が
            # 無ければLLMは呼ばれない（ingest/conditions.py の _SUPERLATIVES）。
            ranking = conditions.extract_ranking(question, schema, ask_json)
            matched = catalog.select(collection, extraction.conditions)
            relaxed = catalog.relaxations(collection, extraction.conditions)
            # 条件から外れるが上位の機種（「もっと大容量が欲しいが設置できない」）は
            # 画面にだけ出す。モデルに渡すと、設置できない機種を答えとして挙げる。
            # 実測（8回）では、最大値の要約行を添えた表で5回、UD-1400X（545mm必要）を
            # 「条件に合う機種」として答えた。渡さなければ起こらない。
            beyond = catalog.exceeding(collection, extraction.conditions, ranking, matched)
            prompt_table = catalog.format_table(
                extraction.conditions, matched, relaxed, ranking
            )
            # 画面（絞り込んだ一覧）には beyond も含めて見せる。
            table = catalog.format_table(
                extraction.conditions, matched, relaxed, ranking, beyond
            )
            user_content = build_catalog_prompt(question, prompt_table)
        else:
            # 検索には直前の質問を継ぎ足す（追質問は単独では引けない）。
            # モデルへ渡す質問は生のままにする。会話履歴は history で渡しており、
            # 継ぎ足した文字列まで質問として見せると同じ問いが二重になる。
            query = contextual_query(question, st.session_state.messages[:-1])
            hits = search(collection, query)
            user_content = build_prompt(question, hits)
    except embedder.EmbeddingError as error:
        search_error = error

    # 条件抽出の失敗を伝えるのは、その先の検索が成立したときだけにする。
    # Ollamaが止まっていれば条件抽出（LLM）も検索（埋め込み）も同じ理由で失敗し、
    # 「通常の検索で回答します」と告げた直後にその検索が落ちることになるため。
    if extraction.failed and search_error is None:
        st.warning("条件を解釈できませんでした。通常の検索で回答します。")

    answer = None
    with st.chat_message("assistant"):
        # 疎通確認をしないため、Ollama未起動やモデル名の誤りは生成時に初めて
        # わかる。ingestボタンのエラー表示（st.sidebar.error）と同じ見せ方で、
        # 生のトレースバックの代わりにチャット欄へ短いメッセージを出す。
        if search_error is not None:
            st.error(f"検索できませんでした: {search_error}")
        else:
            history = (
                [{"role": "system", "content": SYSTEM_PROMPT}]
                + [
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages[:-1]
                ]
                + [{"role": "user", "content": user_content}]
            )
            try:
                stream = client.chat.completions.create(
                    model=model, messages=history, temperature=temperature, stream=True
                )

                def tokens():
                    for chunk in stream:
                        if chunk.choices and chunk.choices[0].delta.content:
                            yield chunk.choices[0].delta.content

                # 「答え：」の言い直しはラベルだけ落とす（ingest/answer_text.py）。
                answer = st.write_stream(answer_text.without_label(tokens()))
                render_evidence({"hits": hits, "table": table})
            except APIError as error:
                st.error(f"回答を生成できませんでした: {error}")

    if answer is not None:
        st.session_state.messages.append(
            {"role": "assistant", "content": answer, "hits": hits, "table": table}
        )
