"""Codex から社内資料を引く stdio MCP サーバ。

取り込み済みのDBを検索し、根拠となる原文をそのまま返す。回答文を作らないのは、
コーディングエージェントに要るのが判断済みの答えではなく、コードや設定へ統合
できる原文だからである（設計書3.2節）。

サーバは常駐し、リクエストのたびに revision() を読んでBM25索引の鮮度を見る。
ストアはプロセスの生存期間で1度だけ開く。開く操作は読み取りではないため
（_get_store の説明を参照）、取り込み中の検索が待たされる可能性は
「サーバの生存期間に最大1回」まで減らせるが、ゼロにはならない（設計書5節）。
"""
from dataclasses import dataclass

from mcp.server import MCPServer

from ingest import reranker, store
from ingest.embedder import EmbeddingError
from ingest.prompting import format_hit_caption
from ingest.retrieval import SEARCH_RESULT_COUNT, build_index, search

# 0件のときに返す文言。空文字や空配列を返してはならない。エージェントは根拠が
# 無いときこそ自分の知識で答えにいくため、「探したが無かった」ことを明示的に
# 伝える必要がある（設計書4.6節）。
_NO_HITS = (
    "社内資料を検索しましたが、この質問に関連する記述は見つかりませんでした。\n"
    "推測で答えず、社内資料からは回答できない旨を伝えてください。"
)

# 結果の末尾に添える歯止め。build_prompt が持っていたものを引き継ぐ（設計書4.6節）。
# しきい値0.50は関連度の高さまでは保証しないため、距離が閾値内であることを
# 関連性の根拠にしてはならない。AGENTS.md にも同じ規範を書くが、そちらを
# 読んでいない経路でも効くよう、結果自体にも添える。
_CAUTION = (
    "---\n"
    "上記は検索結果です。質問に関連しない場合は根拠に使わず、"
    "資料からは回答できない旨を伝えてください（距離が閾値内であることは"
    "関連性を保証しません）。資料に書かれていない主体を補わないでください。"
)


def format_results(hits: list) -> str:
    """Hit の並びを Markdown に組む。

    出典は all_citations() で全件並べる。画面表示に使う citation は
    「ほか6資料」と丸めるが、エージェントは出典ファイルを直接開くため、
    丸めるとその経路が塞がる（設計書4.5節）。
    """
    if not hits:
        return _NO_HITS

    blocks = [f"社内資料から {len(hits)} 件が見つかりました。"]
    for number, hit in enumerate(hits, start=1):
        # スコア部分だけを取る。出典は下で全件並べるため重複させない。
        # 右から刻む。caption は「出典 ／ 距離 ／ BM25 ／ Reranker」の4欄で
        # 固定だが、左から1回で切ると、出典（ファイル名）自身が " ／ " を
        # 含んだときに見出しへその後半が紛れ込む。
        scores = " ／ ".join(format_hit_caption(hit).rsplit(" ／ ", 3)[1:])
        citations = "\n".join(f"- {one}" for one in hit.all_citations())
        blocks.append(f"## [{number}] {scores}\n出典:\n{citations}\n\n{hit.text}")
    blocks.append(_CAUTION)
    return "\n\n".join(blocks)


@dataclass
class _State:
    """プロセスの生存期間だけ持つ状態。

    サーバは Codex がセッションごとに起こす子プロセスであり、常駐する。
    常駐する理由はDBを開くのが重いからではない（実測0.40ms）。BM25索引の
    構築が57msかかり、エージェントは1タスク中に何度も検索するためである
    （2026-09-08、570出現・本文512種の実測）。
    """

    store: object | None = None
    index: object | None = None
    index_revision: int | None = None
    reranker_ready: bool = False


def _get_index(state: _State, collection):
    """BM25索引を返す。revision が変わっていれば組み直す。

    revision は replace_source() の書き込みトランザクションの内側で加算される
    ため、これだけを見れば鮮度を判定できる。読むコストは0.02msで、57msの
    組み直しを避けられるかの判定には十分に軽い。
    """
    revision = collection.revision()
    if state.index is None or revision != state.index_revision:
        state.index = build_index(collection)
        state.index_revision = revision
    return state.index


mcp = MCPServer("local_docs")
_state = _State()


def _open():
    """DBを開く。

    パスは store.DB_PATH（rag_chat_app.py・scripts/ingest_source.py と共通）を
    使う。引数や環境変数で受け取らないのは、3か所で食い違うと open_store が
    例外を出さずに空のDBを新規作成し、検索が黙って全部空になる状態が
    生まれるためである（ingest/store.py のコメント参照）。
    """
    return store.open_store(str(store.DB_PATH))


def _get_store(state: _State):
    """ストアを返す。開くのはプロセスの生存期間で1度だけ。

    リクエストごとに開き直してはならない。open_store() は読み取りではなく、
    VectorStore.__init__（ingest/vector_store.py:146-150）が
    executescript(_SCHEMA) と commit() を実行する。つまり開くたびにSQLiteの
    書き込みロックを取りにいくため、取り込みの書き込みと重なると busy_timeout
    ぶん待たされ、"database is locked" で終わる。開きっぱなしにするのは
    rag_chat_app.py:30-32 の @st.cache_resource と同じ形である。

    これで消えるのは「毎リクエスト」であって「必ず」ではない。最初の検索は
    今もそのスキーマ確認の書き込みを1回行うので、サーバ起動後の最初の検索が
    たまたま取り込みの書き込みと重なれば、その1回はやはり待たされる。
    """
    if state.store is None:
        state.store = _open()
    return state.store


def _ensure_reranker():
    """初回検索時にだけリランカーを用意する。

    起動時にロードしない。Codex はセッション開始時にサーバを起こすため、
    検索を1度もしないセッションにモデルの取得と読み込みを払わせないためである
    （設計書4.4節は3.3秒・約570MBと見積もっている）。

    代償は初回検索が遅いこと。同一クエリ5回の実測（2026-09-08、i5-1240P、
    570出現・本文512種）で 6.99秒 → 3.55 / 3.41 / 3.48 / 3.53秒。初回の
    上乗せ約3.5秒のうち、この check_reranker() 自体は1.18秒（HuggingFace Hub
    へのHEAD6回）で、残りは初回 rerank() のONNXセッション構築である。

    取得に失敗しても検索は続ける。既存の劣化運転方針に揃える（設計書7節）。
    """
    if _state.reranker_ready:
        return reranker.rerank
    try:
        reranker.check_reranker()
    except reranker.RerankError:
        return None
    _state.reranker_ready = True
    return reranker.rerank


@mcp.tool()
def search_documents(query: str, n_results: int = SEARCH_RESULT_COUNT) -> str:
    """社内資料を検索し、根拠となる原文を出典つきで返す。

    Args:
        query: 検索したい内容。自然文で書く。
        n_results: 返すチャンク数。
    """
    try:
        collection = _get_store(_state)
        if collection.count() == 0:
            # 「関連する記述が無い」と取り違えさせない。取り込みを忘れている
            # 利用者は、質問を言い換え続けても永遠に0件を得る（設計書7節）。
            return (
                "ベクトルDBが空です。取り込みが未実行の可能性があります。"
                "python -m scripts.ingest_source を実行してください。"
            )
        index = _get_index(_state, collection)
        hits = search(
            collection,
            query,
            index=index,
            n_results=n_results,
            rerank=_ensure_reranker(),
        )
    except EmbeddingError as error:
        # 文言をそのまま返す。embedder は「ollama pull bge-m3 を実行して
        # ください」のように、利用者が次に何をすればよいかを書いている。
        #
        # 拾うのはこの1種類だけにする。広く Exception を拾っていた版は
        # 「サーバを落とさない」ことを理由にしていたが、その心配は要らない。
        # インストール済み mcp 2.2.0 のソースでは、ツール関数が投げた例外は
        # mcp/server/mcpserver/tools/base.py:208-210 の
        # `except Exception as exc: raise UnexpectedToolError(...) from exc`
        # を通り、mcp/server/mcpserver/server.py:447 で is_error=True の
        # CallToolResult になる。ただし**そこに載るのは元の例外文ではない**。
        # 定型文 "Error executing tool search_documents" だけであり、
        # mcp/server/mcpserver/exceptions.py:66-67 が「nothing from the original
        # reaches the client」と明記している（実測ではなく、上記のソースを
        # 読んで確認）。
        # それでも狭めるのは、詳細が失われる代償を払ってでも、バグが正常な
        # 検索結果と見分けのつく形で届くほうが良いからである。広い except では
        # TypeError が「0件でした」や「Ollamaが落ちています」と同じ顔をして
        # エージェントに届く。
        #
        # RerankError はここへ来ない。check_reranker の失敗は _ensure_reranker
        # が、rerank の失敗は retrieval._reranked が、それぞれ手前で捕まえる。
        return str(error)
    return format_results(hits)


if __name__ == "__main__":
    mcp.run()
