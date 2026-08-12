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

from ingest import catalog, conditions, embedder, store
from ingest.prompting import build_catalog_prompt, build_prompt, format_report
from ingest.retrieval import RELEVANCE_THRESHOLD, search
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
    if extraction.failed:
        st.warning("条件を解釈できませんでした。通常の検索で回答します。")

    table = None
    hits = []
    if extraction.conditions:
        matched = catalog.select(collection, extraction.conditions)
        relaxed = catalog.relaxations(collection, extraction.conditions)
        table = catalog.format_table(extraction.conditions, matched, relaxed)
        user_content = build_catalog_prompt(question, table)
    else:
        hits = search(collection, question)
        user_content = build_prompt(question, hits)

    history = (
        [{"role": "system", "content": SYSTEM_PROMPT}]
        + [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.messages[:-1]
        ]
        + [{"role": "user", "content": user_content}]
    )

    with st.chat_message("assistant"):
        # 疎通確認をしないため、Ollama未起動やモデル名の誤りは生成時に初めて
        # わかる。ingestボタンのエラー表示（st.sidebar.error）と同じ見せ方で、
        # 生のトレースバックの代わりにチャット欄へ短いメッセージを出す。
        answer = None
        try:
            stream = client.chat.completions.create(
                model=model, messages=history, temperature=temperature, stream=True
            )

            def tokens():
                for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content

            answer = st.write_stream(tokens())
            render_evidence({"hits": hits, "table": table})
        except APIError as error:
            st.error(f"回答を生成できませんでした: {error}")

    if answer is not None:
        st.session_state.messages.append(
            {"role": "assistant", "content": answer, "hits": hits, "table": table}
        )
