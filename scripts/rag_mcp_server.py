"""Codex から社内資料を引く stdio MCP サーバ。

取り込み済みのDBを検索し、根拠となる原文をそのまま返す。回答文を作らないのは、
コーディングエージェントに要るのが判断済みの答えではなく、コードや設定へ統合
できる原文だからである（設計書3.2節）。

サーバは常駐し、リクエストのたびに revision() を読んでBM25索引の鮮度を見る。
取り込み中でもロックは取らない。SQLiteの読み手は書き込み中も一貫した
スナップショットを得るため（設計書5節、実測で待ち0ms）。
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
        scores = format_hit_caption(hit).split(" ／ ", 1)[1]
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


def _ensure_reranker():
    """初回検索時にだけリランカーを用意する。

    起動時にロードしない。Codex はセッション開始時にサーバを起こすため、
    検索を1度もしないセッションが3.3秒と約570MBを払うことになる（実測）。
    代償は初回検索が4.75秒になることで、2回目以降は0.72秒である。

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
        collection = _open()
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
    except (EmbeddingError, reranker.RerankError) as error:
        # 文言をそのまま返す。embedder は「ollama pull bge-m3 を実行して
        # ください」のように、利用者が次に何をすればよいかを書いている。
        #
        # ここで拾うのはこの2種類だけにする。広く Exception を拾っていた版は、
        # 「サーバを落とさない」という理由で正当化していたが、その心配は
        # 要らない。インストール済み mcp 2.2.0 のソースを読むと、ツール関数が
        # 投げた例外は mcp/server/mcpserver/tools/base.py:199 の
        # `except Exception as exc: raise UnexpectedToolError(...) from exc`
        # を通り、mcp/server/mcpserver/server.py:447 の
        # `CallToolResult(content=[TextContent(...)], is_error=True)` に
        # 変換されるだけで、サーバプロセスは死なない（実測ではなく、上記2箇所
        # のソースコードを読んで確認）。広い except は、この is_error=True と
        # いう「異常でした」という信号を、素通しにして正常な検索結果へ
        # ロンダリングしてしまう。TypeError のようなバグが、エージェントには
        # 「0件でした」や「Ollamaが落ちています」と見分けがつかない形で
        # 届くことになる。
        return str(error)
    return format_results(hits)


if __name__ == "__main__":
    mcp.run()
