"""ローカル文書RAGチャット。

取り込み処理は ingest/ 側にあり、このファイルは表示と入出力だけを担当する。
初回の取り込みは13分かかるため、CLI (python -m scripts.ingest_source) で行う。
このUIのボタンは差分取り込み（通常は数秒）を想定している。
"""
from datetime import datetime
from pathlib import Path

import chromadb
import streamlit as st
from dotenv import load_dotenv

# OLLAMA_HOST を ingest.embedder がインポート時に読むため、他のプロジェクト内
# importより先に .env を読み込む必要がある。ColabのL4 GPUに繋ぐ場合、ここで
# OLLAMA_HOST（ngrokのURL）と OLLAMA_API_KEY を上書きする。
load_dotenv()

from ingest import answer_text, catalog, chat, conditions, embedder, reranker, store, vlm
from ingest.prompting import (
    build_catalog_prompt,
    build_prompt,
    format_hit_caption,
    format_report,
)
from ingest.retrieval import build_index, contextual_query, search
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


@st.cache_resource
def get_index(_collection, chunk_count):
    """BM25インデックスをDBから組む。

    ディスクに持たないため起動のたびに作り直す。DBとファイルで状態が二重管理に
    なると差分取り込みのたびに食い違い、例外も出ないまま検索結果が古くなるためで、
    ingest/store.py の「信頼できる情報源は常にDBひとつにする」方針に揃えてある。

    chunk_count を引数に取るのは、差分取り込みでチャンク数が変わったときに
    キャッシュを無効化するため。先頭のアンダースコアはStreamlitにこの引数を
    ハッシュさせないための目印で、ChromaDBのコレクションはハッシュ化できない。
    """
    return build_index(_collection)


@st.cache_resource
def ensure_reranker():
    """モデルが手元にあることを1回だけ確認する。

    Streamlitは操作のたびにスクリプトを再実行するため、素直に書くと
    クリックのたびに hf_hub_download が走る。キャッシュ済みでも既定では
    リモートへ etag を問い合わせるので、そのたびに待たされることになる。
    get_collection / get_index と同じくプロセス内1回に限定する。
    """
    reranker.check_reranker()


def render_hits(hits):
    if not hits:
        return
    with st.expander(f"参考にした情報（{len(hits)}件）"):
        for hit in hits:
            st.caption(format_hit_caption(hit))
            st.write(hit.text)


def render_evidence(message):
    """根拠の表示。絞り込み経路は表を、検索経路はチャンクを見せる。"""
    if message.get("table"):
        with st.expander("絞り込んだ一覧"):
            st.code(message["table"])
    render_hits(message.get("hits"))


st.set_page_config(page_title="社内文書RAGチャット")
st.sidebar.title("設定")

# ollama pull済みのモデルだけを並べる。自由入力にしていた頃は打ち間違いや
# 未取得のモデル名が、生成時のchat.ChatErrorになるまで分からなかった。
# 先頭が既定値。qwen2.5:7b-instruct を先に置いてあるのは、条件抽出の取りこぼしが
# 少ない llama3.1:8b より遅く精度も劣るという実測（READMEの「モデルの比較」）にも
# かかわらず、既定を変えるのは本節の変更範囲外だからである。gpt-oss:20bは
# 同じ形式の実測はまだ無い（動作確認のみ）。
MODELS = ["qwen2.5:7b-instruct", "llama3.1:8b", "gpt-oss:20b", "qwen3:32b"]
model = st.sidebar.selectbox("モデル名", MODELS)
temperature = st.sidebar.slider("Temperature", 0.0, 1.0, 0.3, 0.1)
# サイドバーには出さない。利用者に編集させる項目ではないため。
# 出典付き回答の指示は ingest/prompting.py が質問側に組み込む。ここは口調と
# 日付だけを受け持ち、検索結果の扱い方の指示とは置き場所を分けている。
SYSTEM_PROMPT = (
    f"あなたは有能なアシスタントです。今日の日付は{datetime.today():%Y年%m月%d日}です。\n"
    "日本語で回答して下さい。"
)

collection = get_collection(DB_DIR)
index = get_index(collection, collection.count())
st.sidebar.metric("インデックス済みチャンク", collection.count())

st.sidebar.divider()
st.sidebar.caption(f"取り込み元: {DEFAULT_SOURCE_DIR.name}/")
# 既定はOFF。VLMは画像1枚ごとに同期の/api/chat呼び出しが挟まり、画像点数の多い
# 資料では取り込み時間が大きく伸びるため（scripts/ingest_source.pyの--with-vlmと
# 同じ配線をチェックボックスで明示させる）。
use_vlm = st.sidebar.checkbox(
    "画像も説明文化する（VLM・時間がかかります）",
    help="PDF/PPTX内の図表・写真をOllamaのVLMで説明文にして取り込みます。",
)
if st.sidebar.button("差分を取り込む"):
    try:
        embedder.check_ollama()
        if use_vlm:
            vlm.check_vlm()
    except (embedder.EmbeddingError, vlm.VlmError) as error:
        st.sidebar.error(str(error))
    else:
        with st.spinner("取り込み中…"):
            report = ingest_directory(
                DEFAULT_SOURCE_DIR,
                collection,
                caption_image=vlm.caption_image if use_vlm else None,
            )
        st.sidebar.success(format_report(report))
        # 取り込んだ資料がベクトル検索でだけ引ける状態になるのを防ぐ。
        get_index.clear()
        st.rerun()

# 既定ON。VLMが既定OFFなのは画像1枚ごとに同期のAPI呼び出しが挟まり取り込みが
# 大幅に遅くなるためだが、リランカーは1問あたり約1.3秒（実測。8候補の中央値）
# であり常用に耐える。
use_reranker = st.sidebar.checkbox(
    "Rerankerで並べ替える（+約1.3秒）",
    value=True,
    help="検索結果の上位8件をbge-reranker-v2-m3で測り直して並べ替えます。",
)
# 初回はモデルの取得に570MB・約1分かかる。質問の途中で無言で止まらないよう、
# ここで先に確認する（embedder.check_ollama / vlm.check_vlm と同じ役割）。
rerank_callable = None
if use_reranker:
    try:
        with st.spinner("リランカーのモデルを確認中…（初回は570MBの取得に約1分）"):
            ensure_reranker()
    except reranker.RerankError as error:
        st.sidebar.error(str(error))
    else:
        rerank_callable = reranker.rerank

if st.sidebar.button("会話履歴をリセット"):
    st.session_state.messages = []
    st.rerun()

st.title("社内文書RAGチャット")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message.get("note"):
            st.warning(message["note"])
        st.write(answer_text.strip_html_tags(message["content"]))
        render_evidence(message)

schema = get_schema(collection)


def ask_json(prompt: str) -> str:
    """条件抽出用にJSONだけを返させる（ingest/chat.py、ネイティブAPI）。"""
    return chat.ask_json(model, prompt)

if "generating" not in st.session_state:
    st.session_state.generating = False

# 生成中は入力欄を無効化する。無効化しないと応答待ちの間にもう一度送信でき、
# Streamlitが実行中のストリーミングを打ち切って新しい実行に切り替えてしまう。
# その結果、そこまでの途中経過だけが履歴に残る（qwen3:32bのように最初の
# 1文字まで40秒以上かかるモデルで実際に起きた）。
question = st.chat_input("メッセージを入力", disabled=st.session_state.generating)

if question and not st.session_state.generating:
    st.session_state.messages.append({"role": "user", "content": question})
    st.session_state.pending_question = question
    st.session_state.generating = True
    st.rerun()

if st.session_state.generating:
    question = st.session_state.pending_question

    extraction = conditions.extract(question, schema, ask_json)

    table = None
    hits = []
    user_content = None
    # ベクトル検索は埋め込みAPIを呼ぶ。Ollamaが止まっていればここで
    # EmbeddingError になるため、生成時（下のchat.ChatError）と同じ見せ方に揃える。
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
            hits = search(collection, query, index=index, rerank=rerank_callable)
            user_content = build_prompt(question, hits)
    except embedder.EmbeddingError as error:
        search_error = error

    # 条件抽出の失敗を伝えるのは、その先の検索が成立したときだけにする。
    # Ollamaが止まっていれば条件抽出（LLM）も検索（埋め込み）も同じ理由で失敗し、
    # 「通常の検索で回答します」と告げた直後にその検索が落ちることになるため。
    # 履歴のnoteとして残すのは、エラー文と同じ理由（直後のst.rerun()で
    # このままでは画面から消えるため）。
    note = None
    if extraction.failed and search_error is None:
        note = "条件を解釈できませんでした。通常の検索で回答します。"
        st.warning(note)

    answer = None
    with st.chat_message("assistant"):
        # 疎通確認をしないため、Ollama未起動やモデル名の誤りは生成時に初めて
        # わかる。ingestボタンのエラー表示（st.sidebar.error）と同じ見せ方で、
        # 生のトレースバックの代わりにチャット欄へ短いメッセージを出す。
        #
        # エラー文もanswerに入れて履歴へ残す。入力欄を再有効化するための
        # 直後のst.rerun()でこのブロックの描画は消えるため、ここでst.error()を
        # 呼ぶだけでは再実行後に画面から跡形もなく消えてしまう。
        if search_error is not None:
            answer = f"検索できませんでした: {search_error}"
            st.error(answer)
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
                # 「答え：」の言い直しはラベルだけ落とし、表のセル内の
                # <br>・<ul>・<li> も描画されずに残らないよう落とす
                # （ingest/answer_text.py）。
                answer = st.write_stream(
                    answer_text.strip_html_tags_stream(
                        answer_text.without_label(
                            chat.stream_chat(model, history, temperature)
                        )
                    )
                )
                render_evidence({"hits": hits, "table": table})
            except chat.ChatError as error:
                answer = f"回答を生成できませんでした: {error}"
                st.error(answer)

    if answer is not None:
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": answer,
                "hits": hits,
                "table": table,
                "note": note,
            }
        )

    # 入力欄を再度有効化する。ここで再実行しないと、次に利用者が何か操作する
    # まで画面上は無効化されたままになる。
    st.session_state.generating = False
    st.session_state.pending_question = None
    st.rerun()
