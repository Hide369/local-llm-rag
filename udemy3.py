from datetime import datetime  # <--- 追加
from pathlib import Path
import streamlit as st
from openai import OpenAI
import chromadb
from chromadb.api.shared_system_client import SharedSystemClient
from docx import Document
import requests


# ChromaDBの設定
# 起動時のカレントディレクトリに左右されないよう、このファイル基準の絶対パスにする
DB_DIR = str(Path(__file__).parent / "chroma_db")  # ChromaDBの保存先ディレクトリ
COLLECTION_NAME = "local_docs"

# Ollamaのnomic-embed-textが返すベクトルは正規化されていない（ノルム約23）。
# ChromaDB既定のL2距離だとベクトルの長さに引きずられ、関連する質問と無関係な質問の
# 距離が重なってしまう（議事録5件21チャンクでの実測: 関連max 284 > 無関係min 277）。
# cosineならベクトルの長さが影響しないため分離できる（同条件: 関連max 0.334 < 無関係min 0.348）。
DISTANCE_SPACE = "cosine"

# 検索結果を採用するcosine距離のしきい値（0に近いほど類似）。上記の実測値の間を取っている。
# 扱う文書を入れ替えたら適切な値も変わるので、折りたたみに出るスコアを見て調整すること。
RELEVANCE_THRESHOLD = 0.34

# 検索で取得する件数
SEARCH_RESULT_COUNT = 2


@st.cache_resource
def get_chroma_client(db_dir):
    """ChromaDBクライアントをプロセス内で1回だけ生成する。

    chromadbは初期化に失敗しても、bindingsを持たない壊れたSystemをクラス変数
    (SharedSystemClient._identifier_to_system) に残す。Streamlitは操作のたびに
    スクリプトを再実行するため、そのままだと以降すべての実行が真の原因とは無関係な
    「AttributeError: 'RustBindingsAPI' object has no attribute 'bindings'」に
    すり替わってしまう。失敗時はキャッシュを破棄し、元の例外をそのまま見せる。
    """
    try:
        return chromadb.PersistentClient(path=db_dir)
    except Exception:
        SharedSystemClient.clear_system_cache()
        raise


client_chroma = get_chroma_client(DB_DIR)


def open_collection():
    """ChromaDBのコレクション（テーブル）を作成または取得する。"""
    return client_chroma.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": DISTANCE_SPACE},
    )


def collection_space(collection):
    """コレクションが実際に使っている距離空間を返す。

    get_or_create_collection にmetadataを渡しても、既存のコレクションの距離空間は
    変わらない（作成時に確定する）。渡した値ではなく実体を見る必要がある。
    """
    config = getattr(collection, "configuration_json", None) or {}
    return (config.get("hnsw") or {}).get("space")


if "collection" not in st.session_state:
    st.session_state.collection = open_collection()

# 既存インデックスがL2で作られている場合、しきい値の基準が変わって足切りが機能しない
space_mismatch = collection_space(st.session_state.collection) != DISTANCE_SPACE

# Ollamaの埋め込みモデルを使用してテキストをベクトル化する関数
def embed_text(text):
    # Ollamaの埋め込みモデルを使用してテキストをベクトル化する
    response = requests.post(
        "http://localhost:12000/api/embeddings",
        json={"model": "nomic-embed-text", "prompt": text}
    )
    data = response.json()
    return data["embedding"]

# Wordファイルを読み込む関数（分割された各チャンクデータは改行コードで結合する）
def load_word_file_to_chromadb(file_path):
    return "\n".join(para.text for para in Document(file_path).paragraphs if para.text.strip())

# チャンクを使った分割関数
def chunk_text(text):
    chunk_size = 200  # チャンクのサイズを指定
    overlap = 50  # チャンク間の重複部分のサイズを指定
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        start += chunk_size - overlap  # 重複部分を考慮して次のチャンクの開始位置を調整

    return chunks

# 質問に関連するチャンクだけを検索して返す関数
def search_context(query, collection):
    """(チャンク, cosine距離) のリストを返す。しきい値より遠いものは無関係として捨てる。

    足切りをしないと、挨拶のような検索対象外の入力でも必ず最近傍が1件返ってきて、
    無関係な文書がコンテキストに紛れ込んでしまう。
    """
    if collection.count() == 0:
        return []
    results = collection.query(
        query_embeddings=[embed_text(query)],
        n_results=SEARCH_RESULT_COUNT
    )
    hits = zip(results["documents"][0], results["distances"][0])
    return [(doc, dist) for doc, dist in hits if doc and dist <= RELEVANCE_THRESHOLD]

# 参考にした検索結果を折りたたみで表示する関数
def render_context(context):
    """回答の根拠を確認できるようにしつつ、会話の流れを邪魔しないよう畳んでおく。"""
    if not context:
        return
    with st.expander(f"参考にした情報（{len(context)}件）"):
        for doc, dist in context:
            st.caption(f"cosine距離: {dist:.3f}（しきい値 {RELEVANCE_THRESHOLD}）")
            st.write(doc)

# サイドバーの設定

# 今日の日付を取得 (例: 2026年08月09日)
today_str = datetime.today().strftime("%Y年%m月%d日")

st.set_page_config(page_title="Local LLM Chat")  
st.sidebar.title("設定") 
 
# モデル名の入力欄をサイドバーに追加
model = st.sidebar.text_input("モデル名", value="llama3.1:8b") 

# Temperatureのスライダーをサイドバーに追加
temperature = st.sidebar.slider("Temperature", min_value=0.0, max_value=1.0, value=0.3, step=0.1) 

# プロンプトの入力欄をサイドバーに追加（初期値に今日の日付を含める）
system_prompt = st.sidebar.text_area(
    "System Prompt", 
    f"あなたは有能なアシスタントです。今日の日付は{today_str}です。日本語で回答して下さい。"
) 

# ドキュメントのアップロード機能をサイドバーに追加
uploaded_file = st.sidebar.file_uploader("Wordファイルをアップロード", 
                                         type=["docx"],
                                         accept_multiple_files=True
                                         )

if st.sidebar.button("インデックス作成"):
    if uploaded_file:
        for file in uploaded_file:
            # Wordファイルを読み込む
            text = load_word_file_to_chromadb(file)
            # テキストをチャンクに分割
            chunks = chunk_text(text)
            # 各チャンクをベクトル化してChromaDBに保存
            for i, chunk in enumerate(chunks):
                embedding = embed_text(chunk)  # Ollamaの埋め込みモデルを使用してチャンクをベクトル化
                st.session_state.collection.add(
                    documents=[chunk],
                    metadatas=[{"source": file.name, "chunk_index": i}],
                    embeddings=[embedding],
                    ids=[f"{file.name}_{i}"]
                )
        st.sidebar.success("インデックス作成が完了しました。")
    else:
        st.sidebar.warning("まずWordファイルをアップロードしてください。")

if st.sidebar.button("インデックスを削除して作り直す"):
    client_chroma.delete_collection(COLLECTION_NAME)
    st.session_state.collection = open_collection()
    st.rerun()

if space_mismatch:
    st.sidebar.error(
        f"既存のインデックスは距離空間 {collection_space(st.session_state.collection)} で"
        f"作られているため、{DISTANCE_SPACE} 前提のしきい値が使えず検索を停止しています。"
        "「インデックスを削除して作り直す」を押したあと、Wordファイルをアップロードして"
        "インデックス作成をやり直してください。"
    )

# タイトル
st.title("Local LLM Chat")

# 会話の履歴を保管
if "messages" not in st.session_state:
    st.session_state.messages = []

# 会話の履歴をリセット
if st.sidebar.button("会話履歴をリセット"):
    st.session_state.messages = []
    st.sidebar.success("会話履歴をリセットしました。")

# 会話履歴を表示
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])
        render_context(message.get("context"))

client = OpenAI(
    api_key="ollama",  # OllamaのAPIキー（ダミー値で可）
    base_url="http://localhost:12000/v1"  # ローカルOllamaサーバの指定
)

# プロンプトの入力欄（入力されるまでは None になる）
prompt = st.chat_input("メッセージを入力")  

# ユーザーがメッセージを入力して送信したときだけ実行する
if prompt:
    # ユーザーの入力を画面と履歴に追加
    with st.chat_message("user"):
        st.write(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # RAG検索（質問に十分近いチャンクだけを採用する）
    context = [] if space_mismatch else search_context(prompt, st.session_state.collection)
    if context:
        retrieved_text = "\n".join(doc for doc, _ in context)
        # 検索結果をプロンプトに追加してアシスタントに渡す
        prompt_with_context = f"以下の情報を参考にしてください:\n{retrieved_text}\n\nユーザーの質問: {prompt}"
    else:
        prompt_with_context = prompt  # 関連する情報がない場合は元のプロンプトを使用

    # APIに渡すmessages配列を作成（会話履歴を含める）
    # 検索結果を付けるのは「今回のユーザー入力」だけ。st.session_state.messages には
    # 生の入力を残しておき、次のターン以降の履歴に古いコンテキストが混ざらないようにする。
    # 履歴には表示用の "context" も入っているので、APIにはrole/contentだけを渡す
    history_for_api = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.messages[:-1]
    ] + [{"role": "user", "content": prompt_with_context}]

    if system_prompt.strip():  # system_promptが空でない場合のみ追加
        messages_for_api = [{"role": "system", "content": system_prompt}] + history_for_api
    else:
        messages_for_api = history_for_api

    # アシスタントの回答エリアを作成してストリーミング表示
    with st.chat_message("assistant"):
        stream = client.chat.completions.create(
            model=model,
            messages=messages_for_api,
            temperature=temperature,
            stream=True  # ストリーミングモードを有効化
        )
        # st.write_stream にジェネレータ関数を渡して出力と結果取得を同時に行う
        def response_generator():
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        bot_response = st.write_stream(response_generator())
        # 参考にした情報は回答のあとに折りたたんで置く（回答を先に読ませるため）
        render_context(context)

    # 会話履歴にアシスタントの回答を追加（再実行後も参考情報を表示できるよう一緒に保存）
    st.session_state.messages.append(
        {"role": "assistant", "content": bot_response, "context": context}
    )