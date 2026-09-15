"""ローカル文書RAGチャット。

取り込み処理は ingest/ 側にあり、このファイルは表示と入出力だけを担当する。
初回の取り込みは13分かかるため、CLI (python -m scripts.ingest_source) で行う。
このUIのボタンは差分取り込み（通常は数秒）を想定している。

source/ はサーバー側にあり、ブラウザーから使う利用者は資料を置けない。サイドバーの
「資料をアップロード」ダイアログがクライアントから資料を入れる唯一の経路である。
"""
import tempfile
from datetime import date, datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

# OLLAMA_HOST を ingest.embedder がインポート時に読むため、他のプロジェクト内
# importより先に .env を読み込む必要がある。ColabのL4 GPUに繋ぐ場合、ここで
# OLLAMA_HOST（ngrokのURL）と OLLAMA_API_KEY を上書きする。
load_dotenv()

import docgen
from docgen import filling as docgen_filling
from docgen import freeform as docgen_freeform
from docgen import markdown_document
from docgen import project as docgen_project
from docgen import source_code as docgen_source_code
from docgen import templates as docgen_templates
from ingest import (
    answer_text,
    catalog,
    chat,
    conditions,
    display_mode,
    embedder,
    query_translation,
    reranker,
    store,
    vlm,
)
from ingest.parsers import SUPPORTED_SUFFIXES, parse
from ingest.prompting import (
    build_catalog_prompt,
    build_docs_prompt,
    build_prompt,
    format_hit_caption,
    format_report,
)
from ingest.retrieval import (
    DOCS_RERANK_FLOOR,
    build_index,
    contextual_query,
    search,
)
from scripts.ingest_source import (
    DEFAULT_SOURCE_DIR,
    UPLOAD_PREFIX,
    ingest_directory,
    ingest_uploads,
)

DB_PATH = str(store.DB_PATH)

# 技術ドキュメントの取り込み先。パスの組み立ては ingest/store.py に置いてある
# （社内資料と分ける理由もそちら）。ここで綴り直すと、実測スクリプトと画面で
# 別のDBを開いても例外が出ないまま食い違う。
DOCS_DB_PATH = str(store.DOCS_DB_PATH)

CORPUS_INTERNAL = "社内資料"
CORPUS_DOCS = "技術ドキュメント"

MODE_CHAT = "チャット"
MODE_COWORK = "Cowork"

# 雛形を選ばない選択肢。プルダウンの先頭に置く。雛形が0件でも画面が成立する
# ようにするため、選択肢そのものを常に存在させる。
NO_TEMPLATE = "（雛形なし）"

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
        "アップロードした資料はDBに残り、全利用者の検索対象になります。"
        "不要になったら下の一覧から削除してください。"
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


@st.dialog("雛形を登録・削除する")
def template_dialog():
    st.caption(
        "雛形の空欄は {{会議名}} のように書いてください。"
        "登録した雛形はこのマシンの templates/ に残ります。"
    )
    uploaded = st.file_uploader(
        "雛形のファイル",
        type=sorted(suffix.lstrip(".") for suffix in docgen.SUPPORTED_SUFFIXES),
        accept_multiple_files=True,
        key="template_files",
    )
    if st.button("登録する", key="run_template_register"):
        if not uploaded:
            st.warning("先にファイルを選んでください。")
        else:
            with tempfile.TemporaryDirectory() as workspace:
                for file in uploaded:
                    path = Path(workspace) / file.name
                    path.write_bytes(file.getvalue())
                    docgen_templates.register(path)
            st.success(f"{len(uploaded)}件を登録しました。")

    if st.button("閉じる", key="close_template_dialog"):
        st.session_state.template_dialog_open = False
        st.rerun()

    for path in docgen_templates.templates():
        left, right = st.columns([4, 1])
        try:
            # 印を添えるのは、登録した雛形に印が1つも無いことをこの場で気づける
            # ようにするため。生成してから空の結果を見るより早い。
            names = docgen.placeholders(path)
        except Exception as error:
            # register() は拡張子しか見ないため、中身が壊れた雛形も登録できて
            # しまう。ここで例外を投げたまま落ちると、この画面がその雛形を
            # 消せる唯一の場所であるにもかかわらず削除ボタンごと出せなくなる。
            left.write(f"{path.name} — 開けません: {error}")
        else:
            left.write(f"{path.name} — 印 {len(names)}個: {'、'.join(names) or 'なし'}")
        if right.button("削除", key=f"remove_{path.name}"):
            docgen_templates.remove(path.name)
            st.rerun()


def render_cowork_result(result):
    """前の実行で ためた Cowork の結果を描く。

    generating を戻すための下の st.rerun()（チャットの入力欄再有効化と同じ
    理由）は、_generate_document がその場で st.error 等を呼んでも同じ実行の
    描画ごと消してしまう。チャットの回答を messages に積んで次の実行で
    読み直すのと同じやり方で、結果は st.session_state.cowork_result に積み、
    ここで次の実行として描き直す。
    """
    for message in result["errors"]:
        st.error(message)
    if result["warnings"]:
        # 黄色の枠で並べると、生成のたびに画面の大半が警告で埋まる。実測
        # 2026-09-15: ingest/ を指定した回は「読まなかったファイル」だけで
        # 28件・452字になり、成果物のダウンロードボタンが下へ押し流されていた。
        #
        # 捨てはしない。根拠が足りないまま書かれた文書を、根拠があるものとして
        # 読ませないための情報である。畳んだ場所へ移し、件数だけを見出しに出す。
        with st.expander(f"補足（{len(result['warnings'])}件）"):
            for message in result["warnings"]:
                st.write(message)
    for message in result["infos"]:
        st.info(message)
    download = result["download"]
    if download:
        st.download_button(
            "ダウンロード", data=download["data"], file_name=download["file_name"]
        )
    for kind, hits in result["sources"]:
        if hits:
            # 両方のコーパスを引いた回は expander が2つ並ぶ。名前を出さないと
            # どちらが社内資料でどちらが技術ドキュメントか見分けられない。
            st.caption(kind)
            render_hits(hits)


def _empty_cowork_result():
    return {"errors": [], "warnings": [], "infos": [], "download": None, "sources": []}


def _cowork_error(message):
    result = _empty_cowork_result()
    result["errors"].append(message)
    return result


def _has_no_evidence(use_internal, use_docs, attachments, project_folder):
    """根拠が1つも無いかを判定する。

    雛形あり・なしの両方の分岐が同じ条件で「呼んでも中身の無い文書が出る
    だけ」の回を止める。判定を2箇所に書くと、プロジェクトフォルダのような
    根拠を1つ足すたびに片方だけ直して片方を古いまま取り残す恐れがある
    ため、ここへ1つにまとめる。
    """
    return (
        not use_internal
        and not use_docs
        and not attachments
        and not project_folder.strip()
    )


def _why_the_docs_search_was_empty(documents, used_query, question, docs_index):
    """技術ドキュメントが0件だった理由を切り分ける材料を返す。

    「0件でした」だけでは、クエリが的外れだったのか、DOCS_RERANK_FLOOR が
    切ったのか、そもそも資料が無いのかを画面から区別できない。実際その区別が
    付かないまま、直したつもりの修正が本番で効いていないことが起きた
    （2026-09-15）。

    床を外してもう一度引くので、リランカーがもう1回（候補8件・1〜2秒）走る。
    払うのは0件だった回だけである。

    使ったクエリを出すのが要点の1つ。依頼文がそのまま出ていれば
    query_translation.topic_query が失敗して原文へフォールバックしており、
    直すべきはクエリ生成であって床ではない。
    """
    notes = [f"技術ドキュメントの検索に使ったクエリ: 「{used_query}」"]
    if used_query.strip() == question.strip():
        notes.append(
            "依頼文がそのまま検索に使われています。"
            "検索クエリの生成に失敗して原文へフォールバックした状態です。"
        )
    unfloored = search(
        documents,
        used_query,
        index=docs_index,
        rerank=rerank_callable,
    )
    if not unfloored:
        notes.append(
            f"採否の下限（{DOCS_RERANK_FLOOR}）を外しても0件でした。"
            "このクエリでは資料に当たっていません。"
        )
        return notes
    best = getattr(unfloored[0], "rerank_score", None)
    notes.append(
        f"採否の下限（{DOCS_RERANK_FLOOR}）を外すと{len(unfloored)}件あり、"
        f"最高スコアは {best:.2f} でした。下限が切っています。"
        if isinstance(best, (int, float))
        else f"採否の下限（{DOCS_RERANK_FLOOR}）を外すと{len(unfloored)}件ありました。"
    )
    notes.append(f"最も近かったのは {unfloored[0].citation} です。")
    return notes


def _collect_project_files(folder, question, ask_tools_call, result):
    """フォルダを走査して本文を読む。読めなければ None を返す。

    LLM を呼ぶ前にパスと対象件数を確かめるのは、呼んでから落ちると利用者が
    30〜60秒待たされたうえで何も受け取れないためである。
    """
    if not folder.strip():
        return [], ""
    root = Path(folder.strip())
    try:
        entries = docgen_project.tree(root)
    except docgen_project.ProjectFolderError as error:
        st.session_state.cowork_result = _cowork_error(str(error))
        return None
    if not entries:
        # 0件でも止めない。**プロジェクトフォルダは資料源であると同時に出力先
        # でもある。** これから作るプロジェクトを指定して書かせたい回に、中身が
        # 無いという理由で何も受け取れないのは筋が通らない。根拠が1つ減るだけ
        # なので、伝えたうえで生成へ進む。
        #
        # 受け付ける形式を並べるのは、件数が0になる理由がほぼ拡張子の食い違いで
        # あり、文言に出ていないと利用者には確かめる手段が画面上に無いためである
        # （実測 2026-09-15: .py が対象から漏れていて Python のプロジェクトが
        # 全部0件になったとき、原因が拡張子だと分かるまで時間がかかった）。
        result["warnings"].append(
            f"{root} に取り込める形式のファイルがありません。"
            f"取り込めるのは {' '.join(sorted(SUPPORTED_SUFFIXES))} です。"
            "このフォルダは出力先としてのみ使います。"
        )
        return [], ""
    listing, omitted = docgen_project.tree_text(entries)
    if omitted:
        # 選ばれなかった理由が「関係が無い」のか「一覧に載らなかった」のか、
        # 伝えないと利用者には区別が付かない。
        result["warnings"].append(
            f"ファイルが多く、一覧に{omitted}件を載せきれませんでした。"
            "モデルが選べるのは載った分だけです。"
        )
    try:
        files, skipped = docgen_project.gather(root, entries, question, ask_tools_call)
    except chat.ChatError as error:
        st.session_state.cowork_result = _cowork_error(str(error))
        return None
    if not files:
        # 道具を1度も呼ばないモデルはここへ来る。止めずにツリーだけを渡す。
        result["warnings"].append(
            "読むファイルを選べませんでした。ファイル一覧だけを渡します。"
        )
    if skipped:
        result["warnings"].append(
            "読まなかったファイル: " + "、".join(skipped)
        )
    return files, listing


def _collect_evidence(question, attachments, use_internal, use_docs, project_folder, result):
    """検索結果・添付・プロジェクトフォルダの本文を集める。

    失敗したら結果に積んで None を返す。雛形あり・なしの両方がこれを呼ぶ。
    どちらか一方にだけ検索の修正が入る状態を作らないため、1つにまとめてある。

    どのコーパスを引くかは画面が決め、filling.py / freeform.py へは
    (種類の名前, ヒット) の並びで渡す。生成側にコーパスの知識を持たせない
    （設計書6節）。

    返り値の3つ目はプロジェクトフォルダのファイル一覧をプロンプトへ載せる形に
    したものである。freeform.write_markdown はモデルの選択が壊れて空になった
    回にもこれだけは渡すので、呼び出し元はここで捨てずに次へ渡すこと。

    プロジェクトフォルダの検証を検索より先に行うのは、パスの打ち間違いを
    伝えるのに、埋め込み検索や技術ドキュメントの英訳（LLM呼び出し）を
    通す理由がないためである。呼んでから落ちると利用者は30〜60秒待たされた
    うえで何も受け取れない。
    """

    def ask_json_call(prompt):
        return chat.ask_json(model, prompt, num_ctx=docgen_filling.GENERATION_NUM_CTX)

    def ask_tools_call(messages, tools):
        return chat.ask_tools(
            model, messages, tools, num_ctx=docgen_filling.GENERATION_NUM_CTX
        )

    collected_project = _collect_project_files(
        project_folder, question, ask_tools_call, result
    )
    if collected_project is None:
        return None
    project_files, tree_text = collected_project

    sources = []
    try:
        if use_internal:
            internal = get_collection(DB_PATH)
            sources.append((
                CORPUS_INTERNAL,
                search(
                    internal,
                    question,
                    index=get_index(internal, DB_PATH, internal.revision()),
                    rerank=rerank_callable,
                ),
            ))
        if use_docs:
            documents = get_collection(DOCS_DB_PATH)
            if documents.count() == 0:
                # 取り込み前でも生成は止めない。社内資料と添付だけで埋める。
                result["infos"].append(
                    "技術ドキュメントが取り込まれていません。この検索は飛ばしました。"
                )
            else:
                # 英語のコーパスなので日本語のままでは当たらず、採否も距離では
                # 決まらない（PR #41）。
                #
                # チャット側と違い translate_query は使わない。Cowork の入力は
                # 「〜を書いて」という依頼であり、訳しても依頼のまま届く。
                # リランカーは「この文章はこの問いに答えているか」を測るので、
                # 依頼に対しては話題が合っていても低く出て、DOCS_RERANK_FLOOR に
                # 全件切られる（実測は query_translation.topic_query の docstring）。
                # ここでは依頼から「調べるべき話題」を作らせる。
                english = query_translation.topic_query(question, ask_json)
                docs_index = get_index(documents, DOCS_DB_PATH, documents.revision())
                hits = search(
                    documents,
                    english,
                    index=docs_index,
                    rerank=rerank_callable,
                    rerank_floor=DOCS_RERANK_FLOOR,
                )
                if not hits:
                    result["warnings"].extend(
                        _why_the_docs_search_was_empty(
                            documents, english, question, docs_index
                        )
                    )
                sources.append((CORPUS_DOCS, hits))
    except embedder.EmbeddingError as error:
        st.session_state.cowork_result = _cowork_error(str(error))
        return None
    except chat.ChatError as error:
        # 英訳もLLMである。落ちたら伝えて止める。
        st.session_state.cowork_result = _cowork_error(str(error))
        return None

    texts = []
    if attachments:
        # アップロード経路（upload_dialog）と同じ判断: VLMが無いことは止める
        # 理由にしないが、caption_image を渡さずに parse を呼ぶと画面の図や
        # スクリーンショットに説明が付かず、OCRで拾えた文字だけになる。
        caption_image, reason = caption_image_or_reason()
        if reason:
            result["warnings"].append(reason)
        with tempfile.TemporaryDirectory() as workspace:
            for file in attachments:
                path = Path(workspace) / file.name
                path.write_bytes(file.getvalue())
                try:
                    # 添付はDBに入れない。取り出した本文をその場で使うだけである。
                    units = parse(path, caption_image=caption_image)
                except Exception as error:
                    # register() 同様、拡張子だけでは中身の壊れたファイルを
                    # 弾けない。壊れたファイルを添付されて素通りさせると
                    # 生のトレースバックで止まる。
                    st.session_state.cowork_result = _cowork_error(
                        f"{file.name} を開けませんでした: {error}"
                    )
                    return None
                text = "\n".join(unit.text for unit in units)
                if not text:
                    # 説明文もOCR文字も得られなかった画像。空の見出しだけが
                    # プロンプトに載ると、利用者には何も伝わらない。
                    result["warnings"].append(
                        f"{file.name} から本文を取り出せませんでした。"
                    )
                texts.append((file.name, text))

    # プロジェクトの本文は「添付の自動版」であり、専用の受け口を作らない
    # （docgen/project.py のモジュールdocstring参照）。先頭に置くのは、
    # 依頼者が明示的に選んだ添付より先に見せる理由が特にあるわけではなく、
    # 単に呼び出し順をそのまま反映しただけである。
    texts = project_files + texts
    return sources, texts, tree_text


def _generate_document(template_path, names, question, attachments, use_internal, use_docs, project_folder):
    """雛形を埋め、結果を st.session_state.cowork_result に積む。

    ここで直接 st.error や st.download_button を呼ばないのは、generating を
    戻すための下の st.rerun() が同じ実行の描画ごと消してしまうためである。
    render_cowork_result が次の実行でこれを描く。

    どのコーパスを引くかは画面が決め、filling.py へは (種類の名前, ヒット) の
    並びで渡す。filling.py にコーパスの知識を持たせない（設計書6節）。
    """
    result = _empty_cowork_result()

    def ask(prompt):
        return chat.ask_json(
            model, prompt, num_ctx=docgen_filling.GENERATION_NUM_CTX
        )

    collected = _collect_evidence(
        question, attachments, use_internal, use_docs, project_folder, result
    )
    if collected is None:
        return
    sources, texts, tree_text = collected
    if tree_text:
        # 選択が壊れて空になっても、ツリーだけは載せる（設計書5節）。
        # freeform 経路は write_markdown の4番目の引数で直接受け取るが、
        # 雛形ありのこちらには専用の受け口が無いので、添付と同じ列（texts）に
        # 1件足す。プロジェクトの本文は「添付の自動版」であり、専用の受け口を
        # 作らない方針（docgen/project.py のモジュールdocstring）と同じ扱いにする。
        texts = texts + [("（プロジェクトのファイル一覧）", tree_text)]

    try:
        values = docgen_filling.fill_values(names, question, sources, texts, ask)
    except docgen_filling.PromptTooLongError as error:
        st.session_state.cowork_result = _cowork_error(str(error))
        return
    except chat.ChatError as error:
        st.session_state.cowork_result = _cowork_error(str(error))
        return

    undrawn = []
    try:
        data = docgen.fill(
            template_path, values, lambda name, reason: undrawn.append((name, reason))
        )
    except Exception as error:
        st.session_state.cowork_result = _cowork_error(
            f"{template_path.name} を開けませんでした: {error}"
        )
        return
    missing = [name for name in names if name not in values]
    if missing:
        result["warnings"].append(
            f"埋まらなかった欄: {'、'.join(missing)}（雛形の {{{{印}}}} が残ります）"
        )
    if undrawn:
        # 図にできなかったことは開く前に伝える。黙って Mermaid のテキストが
        # 入っていると、利用者は成果物を開くまで気づけない。
        result["warnings"].append(
            "図にできなかった欄: "
            + "、".join(f"{name}（{reason}）" for name, reason in undrawn)
        )
    for name, hits in sources:
        if not hits:
            result["infos"].append(f"{name}の検索は0件でした。")
    stem = template_path.stem
    result["download"] = {
        "data": data,
        "file_name": f"{stem}_{date.today().isoformat()}{template_path.suffix}",
    }
    if project_folder.strip():
        try:
            written = docgen_project.write_output(
                Path(project_folder.strip()),
                result["download"]["file_name"],
                result["download"]["data"],
            )
        except OSError as error:
            # 書けなくても成果物そのものは渡す。ダウンロードボタンは出る。
            result["warnings"].append(f"フォルダへ書き出せませんでした: {error}")
        else:
            result["infos"].append(f"{written} に書き出しました。")
    result["sources"] = sources
    st.session_state.cowork_result = result


def _generate_freeform(suffix, question, attachments, use_internal, use_docs, project_folder):
    """雛形なしで文書を作り、結果を st.session_state.cowork_result に積む。

    _generate_document と同じく、ここで st.error や st.download_button を直接
    呼ばない（generating を戻す st.rerun() が同じ実行の描画ごと消すため）。
    """
    result = _empty_cowork_result()

    def ask_text(prompt):
        return chat.ask_text(model, prompt, num_ctx=docgen_filling.GENERATION_NUM_CTX)

    collected = _collect_evidence(
        question, attachments, use_internal, use_docs, project_folder, result
    )
    if collected is None:
        return
    sources, texts, tree_text = collected

    paths = [name for name, _ in texts]
    citations = [hit.citation for _, hits in sources for hit in hits]
    # ソースコードは Markdown の経路に乗せない。あちらは見出し・表・箇条書きへ
    # 解析してから組む作りで、コードを通すと `//` コメントが見出しに、`|` を
    # 含む行が表になる。コードに文書の構造は無いので中間表現を挟まない。
    is_source = suffix.lower() in docgen_source_code.OUTPUT_SUFFIXES

    try:
        written_text = (
            docgen_source_code.write_source(
                question, sources, texts, tree_text, suffix, ask_text
            )
            if is_source
            else docgen_freeform.write_markdown(
                question, sources, texts, tree_text, suffix, ask_text
            )
        )
    except (docgen_filling.PromptTooLongError, chat.ChatError) as error:
        st.session_state.cowork_result = _cowork_error(str(error))
        return

    undrawn = []
    if is_source:
        data, warnings = docgen_source_code.build(
            written_text, paths, citations, suffix
        )
    else:
        blocks = markdown_document.parse(written_text)
        blocks.append(
            markdown_document.References(paths=paths, citations=citations)
        )
        data, warnings = markdown_document.build(
            blocks, suffix, lambda name, reason: undrawn.append((name, reason))
        )
    result["warnings"].extend(warnings)
    if undrawn:
        result["warnings"].append(
            "図にできなかった箇所: "
            + "、".join(f"{name}（{reason}）" for name, reason in undrawn)
        )
    for name, hits in sources:
        if not hits:
            result["infos"].append(f"{name}の検索は0件でした。")
    # 雛形が無いと拡張子だけでは名前を選べない。プロジェクトフォルダを
    # 指定した回はそのフォルダ名を使う（設計書8節）。
    stem = Path(project_folder.strip()).name if project_folder.strip() else "文書"
    result["download"] = {
        "data": data,
        "file_name": f"{stem}_{date.today().isoformat()}{suffix}",
    }
    if project_folder.strip():
        try:
            written = docgen_project.write_output(
                Path(project_folder.strip()),
                result["download"]["file_name"],
                result["download"]["data"],
            )
        except OSError as error:
            # 書けなくても成果物そのものは渡す。ダウンロードボタンは出る。
            result["warnings"].append(f"フォルダへ書き出せませんでした: {error}")
        else:
            result["infos"].append(f"{written} に書き出しました。")
            if is_source:
                # 走査からは外してあるが、言語のツールチェーンは別の規則で動く。
                # 文書と違い、ソースコードは置いた場所がビルドの対象になりうる。
                result["warnings"].append(
                    "ソースコードをプロジェクトの中に書き出しました。"
                    "`go build ./...` や `dotnet build` のような全体ビルドは"
                    "この位置のファイルを拾います。残さない場合は移動するか"
                    "消してください。"
                )
    result["sources"] = sources
    st.session_state.cowork_result = result


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


st.set_page_config(page_title="社内文書RAG")
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
#
# 生成中は chat_input と同じ理由（下の約470行、disabled=st.session_state.generating
# のコメント参照）でこのラジオも無効化する。ここを空けたままだと、ストリーミング中に
# 切り替えてもStreamlitが実行中の生成を打ち切って新しい実行を始めてしまう点は
# chat_input と同じだが、こちらは打ち切った上できき目が違う。打ち切り後の実行では
# 下のコーパス切り替えブロックが messages を空にする一方、generating と
# pending_question はこの後の初期化ブロックまで前回の値のまま残るため、
# 「消したはずの質問」を新しく選んだコーパスに対してもう一度検索してしまう。
# chat_input を無効化しているのと同じ手当てをラジオにも及ぼせば、切り替え自体が
# 生成中は起こらなくなり、この食い違いも生まれない。
corpus = st.sidebar.radio(
    "検索対象",
    [CORPUS_INTERNAL, CORPUS_DOCS],
    key="corpus_radio",
    disabled=st.session_state.get("generating", False),
)
searching_docs = corpus == CORPUS_DOCS

# コーパスを切り替えたら会話履歴を破棄する。残したままだと、
# contextual_query（ingest/retrieval.py）が前のコーパス向けの直前の質問を
# 継ぎ足してしまい、切り替え後の質問と混ざった文字列が translate_query
# （ingest/query_translation.py）に渡って検索クエリごと壊れる
# （例：「就業規則の有給休暇は？ キャッシュの書き方は？」を英訳すると
# 検索が両方とも外れる）。history にも前コーパスの回答が残り、
# build_docs_prompt の「ドキュメントに書いてあることだけを使う」という
# 指示と矛盾する。on_change コールバックではなく、前回値を session_state に
# 覚えておいて差分を見る方式にしているのは、初回描画（前回値がまだ無い）と
# 区別するためである。
if "last_corpus" not in st.session_state:
    st.session_state.last_corpus = corpus
elif st.session_state.last_corpus != corpus:
    st.session_state.last_corpus = corpus
    if st.session_state.get("messages"):
        st.session_state.messages = []
        # 履歴が消えたことを画面から読み取れないと、利用者は「さっきの
        # 話の続き」のつもりで質問し、検索対象が変わったことに気づけない。
        # 空DBの警告（下のst.sidebar.warning）と同じ理由で、サイドバーに
        # 明示する。
        st.sidebar.info("検索対象を切り替えたため、会話履歴をリセットしました。")

    # generating / pending_question も念のためここで打ち切る。ラジオは
    # 生成中disabled（上の約330行、chat_inputと同じ理由）にしてあり、通常は
    # 生成中に切り替えが起こること自体がない。ただし disabled はブラウザ側の
    # 見た目を止めるだけで、session_state を守るものではない。何らかの理由で
    # （Streamlit自体の不具合、テストのように内部状態を直接書き換える経路など）
    # 切り替えが素通りした場合、消したはずの pending_question が
    # generating=True のまま残り、下の「if st.session_state.generating:」が
    # 新しく選ばれたコーパスに対してそれを再検索してしまう。messages を
    # 空にするのと矛盾しないよう、ここでも合わせて解除しておく。
    st.session_state.generating = False
    st.session_state.pending_question = None

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

st.title("社内文書RAG")

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
# 1文字まで40秒以上かかるモデルで実際に起きた）。サイドバーのコーパス切り替え
# ラジオ（上の約330行）も同じ disabled=st.session_state.generating を使っている。
# 理由も同じ打ち切りだが、あちらは打ち切り後に messages だけが空になり、
# generating と pending_question は次の初期化まで前回値のまま残るため、消した
# はずの質問を新しいコーパスへ再送してしまう食い違いが起きる。
#
# st.chat_input の中にウィジェットは置けないため、トグルは入力欄のすぐ上に置く。
mode = st.segmented_control(
    "モード",
    [MODE_CHAT, MODE_COWORK],
    default=MODE_CHAT,
    key="mode",
    label_visibility="collapsed",
    disabled=st.session_state.generating,
)

template_path = None
attachments = []
project_folder = ""
# 既定は社内資料だけ。議事録や報告書はそれで足りる。
use_internal, use_docs = True, False
if mode == MODE_COWORK:
    left, right = st.columns([3, 1])
    # 生成は30〜60秒かかる。その最中にここを触れると、その場で再実行が
    # 走って生成が打ち切られ、雛形や参照先が入れ替わった状態のまま
    # generating と pending_question だけが前回の質問を抱えて残る。
    # サイドバーのコーパス切り替えラジオ（上の約510行）と同じ食い違いが
    # 起きるため、同じく生成中は無効化する。
    #
    # 雛形が0件でも「（雛形なし）」があるので、プルダウンは常に出せる。
    # 以前は0件のときプルダウンを出さず警告だけにしていたが、雛形なしが
    # 正規の選択肢になった今、その警告は行き止まりを指すだけになる。
    choices = [NO_TEMPLATE] + docgen_templates.templates()
    template_choice = left.selectbox(
        "雛形",
        choices,
        format_func=lambda item: item if item == NO_TEMPLATE else item.name,
        key="template",
        disabled=st.session_state.generating,
    )
    template_path = None if template_choice == NO_TEMPLATE else template_choice
    # 登録ボタンは雛形が0件でも出す。ここを「1件以上あるとき」の側に置くと、
    # 初めて Cowork を開いた人の画面に雛形を登録する手段が1つも無くなり、
    # 警告文だけが存在しないボタンを指す行き止まりになる。
    if right.button("雛形を登録・削除", disabled=st.session_state.generating):
        st.session_state.template_dialog_open = True

    output_suffix = markdown_document.OUTPUT_SUFFIXES[0]
    if template_path is None:
        output_suffix = st.selectbox(
            "出力形式",
            # 文書とソースコードで生成の経路が違うので、選択肢も2つの
            # モジュールから合わせて作る。片方だけに足すと、選べるのに
            # 生成できない拡張子が画面に出る。
            markdown_document.OUTPUT_SUFFIXES + docgen_source_code.OUTPUT_SUFFIXES,
            key="output_suffix",
            disabled=st.session_state.generating,
        )

    # 出力形式がソースコードなら、技術ドキュメントを既定で引く。コードを書かせる
    # 回に言語仕様やライブラリの説明が要らないことはまずない。下のチェックは
    # 既定でオフだが（英訳のLLM呼び出しが1回と検索が1本増え、生成が30〜60秒
    # 遅くなる）、その代金を払う価値があるのはまさにこの回である。
    #
    # 形式が変わった回にだけ書き換える。毎回書き換えると、利用者が自分で外した
    # チェックが次の実行で勝手に戻る。ウィジェットを作る前に session_state へ
    # 入れるのは、キー付きのウィジェットが value= より session_state を優先する
    # ためで、value= を変えるだけでは切り替わらない。
    if st.session_state.get("last_output_suffix") != output_suffix:
        st.session_state.last_output_suffix = output_suffix
        st.session_state.cowork_docs = (
            output_suffix.lower() in docgen_source_code.OUTPUT_SUFFIXES
        )

    # コーパスのチェックボックスと添付は、雛形の有無に関わらず出す。雛形
    # なしの生成でも検索結果と添付を使うためである（if available: の中に
    # あった頃は雛形なしのとき画面から消え、根拠を渡す手段が無かった）。
    #
    # どの資料を引くかは雛形と依頼で決まるので、利用者に選ばせる。
    # 技術ドキュメントを入れると英訳のLLM呼び出しが1回と検索が1本増え、
    # 生成が30〜60秒遅くなる。要らない回に払う理由がない。
    corpora = st.columns(2)
    use_internal = corpora[0].checkbox(
        "社内資料を参照",
        value=True,
        key="cowork_internal",
        disabled=st.session_state.generating,
    )
    use_docs = corpora[1].checkbox(
        "技術ドキュメントを参照",
        value=False,
        key="cowork_docs",
        disabled=st.session_state.generating,
    )
    attached = st.file_uploader(
        "添付（この回だけ使い、DBには入れません）",
        type=sorted(suffix.lstrip(".") for suffix in SUPPORTED_SUFFIXES),
        accept_multiple_files=True,
        key="cowork_files",
        disabled=st.session_state.generating,
    )
    attachments = attached or []
    project_folder = st.text_input(
        "プロジェクトフォルダ（このマシン上のパス。空欄可）",
        key="project_folder",
        disabled=st.session_state.generating,
    )

    # 生成の結果は st.session_state に積んで次の実行で描く。generating を戻す
    # ための下の st.rerun()（チャットの入力欄再有効化と同じ理由）が、ここで
    # 直接 st.error 等を呼んでも同じ実行の描画ごと消してしまうため。
    cowork_result = st.session_state.pop("cowork_result", None)
    if cowork_result:
        render_cowork_result(cowork_result)

if st.session_state.get("template_dialog_open"):
    template_dialog()

question = st.chat_input("メッセージを入力", disabled=st.session_state.generating)

if question and not st.session_state.generating:
    if mode == MODE_CHAT:
        # Cowork の依頼文は結果パネル（render_cowork_result）が受け持つので
        # チャット履歴には積まない。積むと、返信の無い user メッセージが
        # 履歴に残り、次のチャットの contextual_query（ingest/retrieval.py）が
        # それを直前の質問として拾って検索クエリを汚す。
        st.session_state.messages.append({"role": "user", "content": question})
    st.session_state.pending_question = question
    st.session_state.generating = True
    st.rerun()

if st.session_state.generating:
    question = st.session_state.pending_question

    # generating / pending_question を戻す処理を try/finally にするのは、
    # この中のどこかで未捕捉の例外が出ても（雛形の一覧側で捕まえきれない
    # 想定外の壊れ方など）、生成中の状態から必ず抜けられるようにするため。
    # ここが素通りすると入力欄も雛形選択も無効化されたまま戻らず、利用者は
    # ブラウザーのセッションを捨てる以外の出口を失う。
    try:
        if mode == MODE_COWORK and template_path is None:
            # template_path is None は「雛形が無い」ではなく「雛形なしを選んだ」
            # という意味になった。根拠が1つも無ければ、呼んでも中身の無い文書が
            # 出るだけなので、その場合だけ止める。
            if _has_no_evidence(use_internal, use_docs, attachments, project_folder):
                st.session_state.cowork_result = _cowork_error(
                    "参照する資料も添付ファイルもありません。根拠が無いため生成しません。"
                )
            else:
                _generate_freeform(
                    output_suffix,
                    question,
                    attachments,
                    use_internal,
                    use_docs,
                    project_folder,
                )
        elif mode == MODE_COWORK:
            try:
                names = docgen.placeholders(template_path)
            except Exception as error:
                # templates.register は拡張子しか見ないため、中身が壊れた
                # ファイルも登録できてしまう（誤操作として起こりうる）。
                st.session_state.cowork_result = _cowork_error(
                    f"{template_path.name} を開けませんでした: {error}"
                )
            else:
                if not names:
                    # ここで直接 st.error を呼ばないのは、generating を戻すための下の
                    # st.rerun() が同じ実行の描画ごと消してしまうためである
                    # （render_cowork_result 参照）。
                    st.session_state.cowork_result = _cowork_error(
                        f"{template_path.name} に {{{{印}}}} がありません。"
                        "埋める欄が無いため生成しません。"
                    )
                elif _has_no_evidence(use_internal, use_docs, attachments, project_folder):
                    # 根拠が1つも無ければ、呼んでも全欄が埋まらない。
                    # LLMを呼ぶ前に止める。
                    st.session_state.cowork_result = _cowork_error(
                        "参照する資料も添付ファイルもありません。根拠が無いため生成しません。"
                    )
                else:
                    _generate_document(
                        template_path,
                        names,
                        question,
                        attachments,
                        use_internal,
                        use_docs,
                        project_folder,
                    )
        else:
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
                    # 技術ドキュメントは英語、質問は日本語のことが多い。継ぎ足した文字列
                    # ごと英語の検索クエリへ翻訳する（前の質問だけ訳して繋ぐより1回の
                    # LLM呼び出しで済み、追質問の文脈も一緒に訳せる）。生成は原文の
                    # question のまま行う（build_docs_prompt）。詳細は
                    # ingest/query_translation.py のモジュールdocstring参照。
                    query = query_translation.translate_query(query, ask_json)
                    # 技術ドキュメントだけ、1件ごとの採否をリランカーのスコアで決める。
                    # このコーパスでは距離のしきい値が関門にならない（実測は
                    # ingest/retrieval.py の DOCS_RERANK_FLOOR）。社内資料側（下の経路）
                    # には渡さない。あちらは距離が分離しており、床の実測もしていない。
                    hits = search(
                        collection,
                        query,
                        index=index,
                        rerank=rerank_callable,
                        rerank_floor=DOCS_RERANK_FLOOR,
                    )
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

    finally:
        # 入力欄を再度有効化する。ここで再実行しないと、次に利用者が何か操作する
        # まで画面上は無効化されたままになる。try/finally にしているのは、この中で
        # 未捕捉の例外が出ても、generating と pending_question を必ず戻すためである。
        st.session_state.generating = False
        st.session_state.pending_question = None

    st.rerun()
