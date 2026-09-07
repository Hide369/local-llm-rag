"""Codex から社内資料を引く stdio MCP サーバ。

取り込み済みのDBを検索し、根拠となる原文をそのまま返す。回答文を作らないのは、
コーディングエージェントに要るのが判断済みの答えではなく、コードや設定へ統合
できる原文だからである（設計書3.2節）。

サーバは常駐し、リクエストのたびに revision() を読んでBM25索引の鮮度を見る。
取り込み中でもロックは取らない。SQLiteの読み手は書き込み中も一貫した
スナップショットを得るため（設計書5節、実測で待ち0ms）。
"""
from dataclasses import dataclass

from ingest.prompting import format_hit_caption
from ingest.retrieval import build_index

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
