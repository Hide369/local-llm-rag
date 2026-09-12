"""ローカル文書RAGチャット。

取り込み処理は ingest/ 側にあり、このファイルは表示と入出力だけを担当する。
初回の取り込みは13分かかるため、CLI (python -m scripts.ingest_source) で行う。
このUIのボタンは差分取り込み（通常は数秒）を想定している。

source/ はサーバー側にあり、ブラウザーから使う利用者は資料を置けない。サイドバーの
「資料をアップロード」ダイアログがクライアントから資料を入れる唯一の経路である。
"""
import tempfile
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

# OLLAMA_HOST を ingest.embedder がインポート時に読むため、他のプロジェクト内
# importより先に .env を読み込む必要がある。ColabのL4 GPUに繋ぐ場合、ここで
# OLLAMA_HOST（ngrokのURL）と OLLAMA_API_KEY を上書きする。
load_dotenv()

from ingest import (
    answer_text,
    catalog,
    chat,
    conditions,
    display_mode,
    embedder,
    reranker,
    store,
    vlm,
)
from ingest.parsers import SUPPORTED_SUFFIXES
from ingest.prompting import (
    build_catalog_prompt,
    build_docs_prompt,
    build_prompt,
    format_hit_caption,
    format_report,
)
from ingest.retrieval import build_index, contextual_query, search
from scripts.ingest_source import (
    DEFAULT_SOURCE_DIR,
    UPLOAD_PREFIX,
    ingest_directory,
    ingest_uploads,
)

DB_PATH = str(store.DB_PATH)

# 技術ドキュメントの取り込み先。社内資料とはファイルごと分ける。
# 同じDBに入れると、社内規程の質問にライブラリのドキュメントが混ざり、
# 「社内資料に無ければ答えない」という歯止めが効かなくなる。
DOCS_DB_PATH = str(store.DB_PATH.parent / "docs_store.sqlite3")

CORPUS_INTERNAL = "社内資料"
CORPUS_DOCS = "技術ドキュメント"

# 技術ドキュメントの取り込み・更新に使う2コマンド。空のときの警告と、空でない
# ときのキャプションの両方で使うため、ここ一箇所にまとめる（二重管理を避ける）。
DOCS_INGEST_COMMAND = (
    "python -m scripts.fetch_docs のあと "
    "python -m scripts.ingest_source --source-dir docs_source "
    "--db docs_store.sqlite3 --keep-code-blocks"
)


@st.cache_resource
def get_collection(db_path):
    return store.open_store(db_path)


@st.cache_resource
def get_schema(_collection, db_path, revision):
    """絞り込みに使える属性の一覧。

    revision を引数に取るのは、新しい数値属性を持つ資料を取り込んだあとも
    プロセスを再起動するまで絞り込みに出てこない、という状態を防ぐため。
    ただし revision だけでは足りない。revision は各DBが自分の meta テーブルに
    持つ、ファイルごとに独立したカウンタであり、社内資料と技術ドキュメントの
    2つのDBが同じ数値になることは普通に起こる。db_path を鍵に加えないと、
    たまたま revision が一致した瞬間に、後から呼ばれた側が先に呼ばれた側の
    コーパスの属性一覧をそのまま受け取ってしまう。

    先頭のアンダースコアは、Streamlitに _collection をハッシュさせないための
    目印。VectorStoreはsqlite3.Connectionを抱えており、ハッシュ化できない。
    db_path は素の文字列なのでそのままハッシュ可能なキーになる。
    """
    return conditions.available_keys(_collection)


@st.cache_resource
def get_index(_collection, db_path, revision):
    """BM25インデックスをDBから組む。

    ディスクに持たないため起動のたびに作り直す。DBとファイルで状態が二重管理に
    なると差分取り込みのたびに食い違い、例外も出ないまま検索結果が古くなるためで、
    ingest/store.py の「信頼できる情報源は常にDBひとつにする」方針に揃えてある。

    revision を引数に取るのは、書き込みと不可分に進む値だけがキャッシュの
    鮮度を正しく判定できるため。チャンク数を鍵にすると「同数の差し替え」を
    取りこぼし、消えた旧チャンクIDを持ったままのBM25索引が、理由の説明なく
    ヒットを落とす（設計書4.5節）。

    revision だけでは足りない。revision は各DBが自分の meta テーブルに持つ、
    ファイルごとに独立したカウンタであり、社内資料と技術ドキュメントの2つの
    DBが同じ数値になることは普通に起こる（どちらも取り込みのたびに1ずつ
    進むだけの独立したカウンタである）。db_path を鍵に加えないと、たまたま
    revision が一致した瞬間に、後から呼ばれた側が先に呼ばれた側のコーパスの
    BM25索引をそのまま受け取ってしまう。

    先頭のアンダースコアはStreamlitに _collection をハッシュさせないための
    目印で、VectorStoreはsqlite3.Connectionを抱えておりハッシュ化できない。
    db_path は素の文字列なのでそのままハッシュ可能なキーになる。
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
            others = hit.all_citations()[1:]
            if others:
                # 見出しは代表しか名乗らない。同じ記述がどこにあるかを
                # 資料を開かずに追えるようにする。
                st.caption("同じ記述: " + " ／ ".join(others))
            st.write(hit.text)


# 図表があるとVLMが画像1枚ごとに同期のAPI呼び出しを行うため、資料によっては
# 取り込みが大きく伸びる。待たされる理由を画面に残す。
SPINNER_MESSAGE = "取り込み中…（図表があると時間がかかります）"


def caption_image_or_reason():
    """図表の説明文化に使う関数と、使えないときの理由。

    VLMが無いことは取り込みを止める理由にしない。図表の説明が付かないだけで、
    本文は取り込めるためである。かといって caption_image を渡したまま失敗させる
    のも取らない。画像1枚ごとに4回のリトライ（1+2+4秒）が走り、モデル未pullの
    環境では取り込みが極端に遅くなる（ingest/vlm.py の _MAX_ATTEMPTS）。
    先に1回だけ確かめて、駄目なら渡さない。
    """
    try:
        vlm.check_vlm()
    except vlm.VlmError as error:
        return None, f"図表の説明文化は行いません: {error}"
    return vlm.caption_image, None


def uploaded_sources(collection):
    """アップロード経由で入った資料のキー。

    source/ 由来の資料は出さない。原本がサーバー側にあり、画面から消しても
    次の差分取り込みで戻ってくるため、消せるように見せるのは嘘になる。
    """
    return sorted(
        source
        for source in store.indexed_sources(collection)
        if source.startswith(UPLOAD_PREFIX)
    )


@st.dialog("資料をアップロードして取り込む")
def upload_dialog(collection):
    """クライアントの手元にある資料を取り込む。

    source/ はサーバー側にあり、利用者のブラウザーからは置けない。ここが
    クライアントから資料を入れる唯一の経路である。

    取り込んだあと st.rerun() は呼ばない。呼ぶとダイアログごと閉じて結果表示が
    消える。BM25索引と属性一覧は collection.revision() を鍵にしており、次に
    画面が動いたときに勝手に組み直される（サイドバーの取り込みボタンと違い、
    ここでは利用者がダイアログを閉じる操作が必ず入る）。
    """
    st.caption(
        "アップロードした資料は source/ には残りません。DBには残り、"
        "全利用者の検索対象になります。不要になったら下の一覧から削除してください。"
    )
    uploaded = st.file_uploader(
        "取り込む資料",
        type=sorted(suffix.lstrip(".") for suffix in SUPPORTED_SUFFIXES),
        accept_multiple_files=True,
        key="upload_files",
    )

    if st.button("取り込む", key="run_upload"):
        if not uploaded:
            st.warning("先にファイルを選んでください。")
        else:
            try:
                # 取り込みを始めてから落ちるのを防ぐ。サイドバーの取り込み
                # ボタンおよびCLIと同じ配線にする。
                embedder.check_ollama()
            except embedder.EmbeddingError as error:
                st.error(str(error))
            else:
                caption_image, reason = caption_image_or_reason()
                if reason:
                    st.warning(reason)
                with st.spinner(SPINNER_MESSAGE):
                    # 一時ディレクトリは取り込みが終われば消える。原本を残さない
                    # のは設計上の選択であり、DBのチャンクだけが残る。
                    with tempfile.TemporaryDirectory() as workspace:
                        paths = []
                        for file in uploaded:
                            path = Path(workspace) / file.name
                            path.write_bytes(file.getvalue())
                            paths.append(path)
                        report = ingest_uploads(
                            paths, collection, caption_image=caption_image
                        )
                st.success(format_report(report))

    # 「閉じる」を一覧より先に置く。一覧の下にあると、資料が増えたときに
    # ダイアログの外へ流れて押せなくなる。
    if st.button("閉じる", key="close_upload_dialog"):
        st.session_state.upload_dialog_open = False
        st.rerun()

    sources = uploaded_sources(collection)
    if sources:
        st.divider()
        st.caption("アップロード済みの資料")
        # 高さを固定するとStreamlitが縦スクロールを出す。固定しないと件数の
        # 分だけダイアログが縦に伸び、下の要素が画面外へ出る。
        # 一覧が空のときはコンテナごと出さない。空の箱だけが残るのを避ける。
        with st.container(height=240, border=True):
            for source in sources:
                name, remove = st.columns([4, 1])
                name.write(source[len(UPLOAD_PREFIX):])
                if remove.button("削除", key=f"delete_{source}"):
                    # 空のチャンク列を渡すとその資料はDBから消える（ingest/store.py）。
                    store.replace_source(collection, source, [], [])
                    st.rerun()


def render_diagrams(text):
    """マーメイドの定義を図として描く。

    記法だけでも図だけでも足りない。記法は他所へ持ち出すため、図はその場で
    読むために要る（要望）。

    回答全体ではなくフェンスの中身だけを渡す。全体を渡すと地の文が
    mermaid の構文エラーになり、代わりに st.write(回答) で描くと地の文が
    上のコードブロックと二重に出る。
    """
    for definition in answer_text.mermaid_definitions(text):
        # st.mermaid_chart は本文をフェンスで包んで markdown として出す。
        # 自分でフェンスを組み立てると、本文中のバッククォートでフェンスが
        # 早閉じする問題を自前で抱えることになる。
        st.mermaid_chart(definition)


def render_answer(text, mode):
    """回答の本文を描く。記法で頼まれたときはコードブロックで出す。

    st.write はマークダウンを描画し、Streamlit 1.61 は mermaid も同梱していて
    ```mermaid フェンスを図にする。どちらも「レンダリング後」しか画面に残らず、
    記法を見たい・他所へ持ち出したい利用者はそれを取り出せない。st.code は
    右上にコピーボタンを付けるので、持ち出したいという狙いにそのまま応える。

    マーメイドのときだけ、記法の下に図も描く。マークダウンでは描かない。
    マークダウンのレンダリング結果は「何も頼まなければ出てくる見え方」そのもので、
    並べても新しく分かることがないためである。

    生表示では strip_html_tags を通さない。<br> を落としているのは Streamlit が
    HTMLを描画せず文字として残るからであって、全部が文字になる生表示では、
    落とすとモデルが実際に書いた記法ではなくなる。
    """
    if mode:
        st.code(text, language=mode)
        if mode == "mermaid":
            render_diagrams(text)
    else:
        st.write(answer_text.strip_html_tags(text))


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
# gpt-oss:20b の1つだけなのは、接続先のOllamaに置いてある生成モデルがこれだけ
# だからである（同居する bge-m3 は埋め込み、qwen2.5vl:7b はVLM専用で、
# どちらも回答生成には使わない）。以前は qwen2.5:7b-instruct / llama3.1:8b /
# qwen3:32b も並べていたが、pull されていないモデルは選んだ時点で生成が失敗する
# だけなので外した。使いたければ先に ollama pull してからここに足す。
# 過去に取った実測比較はREADMEの「モデルの比較」に残してある。
MODELS = ["gpt-oss:20b"]
model = st.sidebar.selectbox("モデル名", MODELS)
temperature = st.sidebar.slider("Temperature", 0.0, 1.0, 0.3, 0.1)
# サイドバーには出さない。利用者に編集させる項目ではないため。
# 出典付き回答の指示は ingest/prompting.py が質問側に組み込む。ここは口調と
# 日付だけを受け持ち、検索結果の扱い方の指示とは置き場所を分けている。
SYSTEM_PROMPT = (
    f"あなたは有能なアシスタントです。今日の日付は{datetime.today():%Y年%m月%d日}です。\n"
    "日本語で回答して下さい。"
)

# どちらを検索するかは利用者が選ぶ。質問文からの自動判定にしないのは、
# 誤判定が利用者から見えない失敗になるためである。選択はそのまま
# 「どちらを検索したか」の表示も兼ねる。
corpus = st.sidebar.radio("検索対象", [CORPUS_INTERNAL, CORPUS_DOCS])
searching_docs = corpus == CORPUS_DOCS

# get_collection と違い get_index / get_schema はコレクションをハッシュに
# 使わない（先頭アンダースコア）ため、どちらのDBを開いたかを鍵に加える必要が
# ある。DB_PATH / DOCS_DB_PATH を渡すのは get_collection のキャッシュキーと
# 揃えるためで、両者の不一致がそのままバグになる。
db_path = DOCS_DB_PATH if searching_docs else DB_PATH
collection = get_collection(db_path)
index = get_index(collection, db_path, collection.revision())
chunk_count = collection.count()
st.sidebar.metric("インデックス済みチャンク", chunk_count)

st.sidebar.divider()
if searching_docs:
    if chunk_count == 0:
        # open_store はパスを間違えても例外を出さず空のDBを新規作成する
        # （ingest/store.py）。CLIをまだ一度も走らせていない場合、切り替えた
        # 直後は検索が黙って全部空になるだけで、利用者には理由が分からない。
        # 設計書5.4節がCLI側に要求している「0件なら警告」の画面側にあたる。
        st.sidebar.warning(
            f"技術ドキュメントのDBが空です。次の2つのコマンドで取り込んでください: {DOCS_INGEST_COMMAND}"
        )
    else:
        st.sidebar.caption(f"更新は CLI で行います: {DOCS_INGEST_COMMAND}")
else:
    st.sidebar.caption(f"取り込み元: {DEFAULT_SOURCE_DIR.name}/")
    if st.sidebar.button("差分を取り込む"):
        try:
            embedder.check_ollama()
        except embedder.EmbeddingError as error:
            st.sidebar.error(str(error))
        else:
            caption_image, reason = caption_image_or_reason()
            with st.spinner(SPINNER_MESSAGE):
                report = ingest_directory(
                    DEFAULT_SOURCE_DIR, collection, caption_image=caption_image
                )
            # ここで st.sidebar.success() を呼んでも画面には出ない。直後の st.rerun()
            # がこの実行の描画をまとめて捨てるため（実測）。次の実行で描くために預ける。
            st.session_state.ingest_report = format_report(report)
            st.session_state.ingest_notice = reason
            # 明示的な clear() は要らない。再実行時に読み直す revision が
            # 書き込みで進んでおり、BM25索引も属性一覧も鍵ごと入れ替わる。
            st.rerun()

    # 直前の取り込みの結果。取り出したら消す。次に画面が動くまで表示は残る。
    ingest_notice = st.session_state.pop("ingest_notice", None)
    if ingest_notice:
        st.sidebar.warning(ingest_notice)
    ingest_report = st.session_state.pop("ingest_report", None)
    if ingest_report:
        st.sidebar.success(ingest_report)

    # クライアントの画面から取り込むための入口。source/ に置けるのはサーバーを
    # 触れる管理者だけなので、上の「差分を取り込む」だけでは利用者は資料を足せない。
    if st.sidebar.button("資料をアップロード", key="open_upload_dialog"):
        st.session_state.upload_dialog_open = True

    # フラグで開閉する。ボタン押下は次の再実行では False に戻るため、押した瞬間に
    # 呼ぶだけではダイアログ内の操作1回目で閉じてしまう。
    if st.session_state.get("upload_dialog_open"):
        upload_dialog(collection)

# 検索結果は常に並べ替える。1問あたり約1.3秒（実測。8候補の中央値）であり常用に
# 耐える。切る手段を画面に置いていたが、使うかどうかを判断する材料は画面に無く、
# 外したままにすれば並べ替えが黙って落ちるだけだった。落ちたことは結果からは
# 分からない（図表の説明文化を自動にしたのと同じ理由）。
#
# 初回はモデルの取得に570MB・約1分かかる。質問の途中で無言で止まらないよう、
# ここで先に確認する（embedder.check_ollama / vlm.check_vlm と同じ役割）。
rerank_callable = None
try:
    with st.spinner("リランカーのモデルを確認中…（初回は570MBの取得に約1分）"):
        ensure_reranker()
except reranker.RerankError as error:
    # 並べ替えは検索が成立する条件ではない。順序が良くなるだけである。理由と、
    # そのまま検索することの両方を書く。切る手段を取り上げた以上、利用者が
    # 次に何が起きるかを画面から読み取れないと手の打ちようがない。
    st.sidebar.warning(f"Rerankerで並べ替えません: {error}")
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
        render_answer(message["content"], message.get("display"))
        render_evidence(message)

# 絞り込みは社内の製品仕様書に固有の仕組みである。技術ドキュメントでは
# 属性一覧を組み立てない（条件抽出のLLM呼び出しも走らせない）。
schema = None if searching_docs else get_schema(collection, db_path, collection.revision())


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

    # 「マークダウンで表示して」と頼まれたら、描画せず記法のまま出す。
    # 判定は質問1つごとに閉じる（ingest/display_mode.py）。前のターンの指定を
    # 持ち越すと、利用者が何も言っていないのにコードブロックで返り続ける。
    display = display_mode.detect(question)

    # 技術ドキュメントでは条件抽出を走らせない。型番の絞り込みは社内の
    # 製品仕様書に固有の仕組みであり、ここではLLM呼び出しが1回無駄に増えるだけ。
    extraction = (
        conditions.Extraction()
        if searching_docs
        else conditions.extract(question, schema, ask_json)
    )

    table = None
    hits = []
    user_content = None
    # ベクトル検索は埋め込みAPIを呼ぶ。Ollamaが止まっていればここで
    # EmbeddingError になるため、生成時（下のchat.ChatError）と同じ見せ方に揃える。
    # 捕まえずにいると生のトレースバックが画面に出る。
    search_error = None
    try:
        if searching_docs:
            # 検索には直前の質問を継ぎ足す（追質問は単独では引けない）。社内資料側の
            # 検索経路（下の else 節）と同じ判断である。
            query = contextual_query(question, st.session_state.messages[:-1])
            hits = search(collection, query, index=index, rerank=rerank_callable)
            user_content = build_docs_prompt(question, hits)
        elif extraction.conditions:
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
    # 履歴へ残すときの表示形式。エラー文は記法ではないので、書式を頼まれていても
    # 普通に読める形で出す。生成が最後まで通った経路だけが display を受け取る。
    answer_display = None
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
                # 「答え：」の言い直しはラベルだけ落とす（ingest/answer_text.py）。
                # 口癖であって記法ではないので、生表示でも落とす。
                stream = answer_text.without_label(
                    chat.stream_chat(model, history, temperature)
                )
                if display:
                    # st.write_stream は中身をMarkdownとして描画してしまうので
                    # 使えない。自前で溜めながらコードブロックを書き換える。
                    # 1行ずつまとめて出さないのは、8トークン毎秒では1行あたり
                    # 数秒待たされるためで、without_label が行頭でだけ文字を
                    # 溜めているのと同じ判断である。
                    placeholder = st.empty()
                    received = []
                    for chunk in stream:
                        received.append(chunk)
                        placeholder.code("".join(received), language=display)
                    answer = "".join(received)
                    if display == "mermaid":
                        # 図は生成が終わってから描く。途中の定義は必ず
                        # 構文エラーになり、描き直すたびにエラーの枠が出る。
                        render_diagrams(answer)
                else:
                    # 表のセル内の <br>・<ul>・<li> は、描画する場合にだけ落とす。
                    answer = st.write_stream(answer_text.strip_html_tags_stream(stream))
                answer_display = display
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
                "display": answer_display,
            }
        )

    # 入力欄を再度有効化する。ここで再実行しないと、次に利用者が何か操作する
    # まで画面上は無効化されたままになる。
    st.session_state.generating = False
    st.session_state.pending_question = None
    st.rerun()
