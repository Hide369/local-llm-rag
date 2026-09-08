"""MCPサーバの整形。

サーバを起動せずに検証する。@mcp.tool() は元の関数をそのまま返すため、
ツール関数もモジュールから直接呼べる。
"""
import pytest

from ingest.retrieval import Hit
from scripts import rag_mcp_server
from scripts.rag_mcp_server import format_results


@pytest.fixture(autouse=True)
def _fresh_state(monkeypatch):
    """テストごとに常駐状態を捨てる。

    _state はプロセスの生存期間だけ持つキャッシュで、開いたストア・BM25索引・
    リランカーの準備済みフラグを抱える。テスト側で差し替え忘れると、前の
    テストが開いたストアをそのまま引き継ぎ、そのテストは何も検証しないまま
    緑になる。autouse にするのは、忘れる余地を無くすためである。
    """
    monkeypatch.setattr(rag_mcp_server, "_state", rag_mcp_server._State())


def _hit(text="本文です。", distance=0.413, bm25=45.76, rerank=1.9, occurrences=None):
    return Hit(
        text=text,
        distance=distance,
        occurrences=occurrences
        or [
            {"source": "セミナー資料/CNN画像認識セミナー.pptx",
             "location_type": "slide", "location": 25},
        ],
        bm25_score=bm25,
        rerank_score=rerank,
    )


def test_no_hits_returns_the_instruction_not_an_empty_string():
    """0件のときこそ空を返してはいけない。

    エージェントは根拠が無いときに自分の知識で答えにいく。空文字や空配列は
    「探したが無かった」ではなく「何も起きなかった」と読まれる（設計書4.6節）。
    """
    text = format_results([])
    assert text.strip()
    assert "見つかりませんでした" in text
    assert "推測で答えず" in text


def test_every_source_is_listed_not_rolled_up():
    """出典は全件並べる。

    Hit.citation は「ほか6資料」と丸めるが、エージェントはどのファイルを
    開けばよいか分からなくなる（設計書4.5節）。
    """
    hit = _hit(occurrences=[
        {"source": "a.pptx", "location_type": "slide", "location": 25},
        {"source": "b.pptx", "location_type": "slide", "location": 22},
        {"source": "c.pdf", "location_type": "page", "location": 12},
    ])
    text = format_results([hit])
    assert "a.pptx" in text
    assert "b.pptx" in text
    assert "c.pdf" in text
    assert "ほか" not in text


def test_the_caption_comes_from_prompting_not_a_reimplementation():
    """整形を再実装していないことの確認。

    位置種別（ページ・スライド・見出し）の書式は Hit と prompting が持つ。
    ここで組み直すと、画面とMCPで出典の見え方が食い違う。
    """
    from ingest.prompting import format_hit_caption

    hit = _hit()
    text = format_results([hit])
    caption = format_hit_caption(hit)
    # caption は「出典 ／ 距離 ／ BM25 ／ Reranker」の1行。
    # 出典部分は別に並べるため、スコア部分が本文に現れることを見る。
    scores = caption.split(" ／ ", 1)[1]
    assert scores in text


def test_a_citation_containing_the_separator_does_not_leak_into_the_heading():
    """出典がスコアの区切りと同じ " ／ " を含んでも見出しを汚さない。

    caption は「出典 ／ 距離 ／ BM25 ／ Reranker」の4欄で固定である。左から
    1回だけ切ると、区切りを含むファイル名の後半が見出しに残り、出典が二重に
    出たうえスコア行として読めなくなる。例外は出ない。
    """
    hit = _hit(occurrences=[
        {"source": "設計 ／ 運用ガイド.pptx", "location_type": "slide", "location": 3},
    ])
    text = format_results([hit])

    heading = next(line for line in text.splitlines() if line.startswith("## [1]"))
    assert heading.startswith("## [1] cosine距離"), heading
    assert "運用ガイド" not in heading, heading


def test_the_body_text_is_included():
    text = format_results([_hit(text="第38条 年次有給休暇は…")])
    assert "第38条 年次有給休暇は…" in text


def test_the_caution_is_appended_to_the_results():
    """歯止めをツール結果の末尾に置く（設計書4.6節）。

    build_prompt が持っていた2つの歯止め（無関係な根拠を使わない、資料にない
    主体を補わない）は、チャンクを返す方式では失われる。AGENTS.md に恒久的な
    規範として書くのに加えて、結果そのものにも添える。AGENTS.md を読んでいない
    経路でも歯止めが効くようにするためである。
    """
    text = format_results([_hit()])
    assert "関連しない場合は根拠に使わず" in text
    assert "資料に書かれていない主体を補わないでください" in text


def test_hits_are_numbered_in_order():
    text = format_results([_hit(text="いち"), _hit(text="に")])
    assert text.index("[1]") < text.index("いち")
    assert text.index("[2]") < text.index("に")
    assert text.index("いち") < text.index("[2]")


class _FakeCollection:
    """revision() と count() だけを持つ最小のストア。"""

    def __init__(self, revision=1000):
        self._revision = revision

    def revision(self):
        # 実物は SQLite から毎回読むため、同じ値でも別のオブジェクトが返る。
        # CPython が整数をキャッシュするのは256までなので、257以上では
        # `is` 比較が毎回偽になり、毎リクエスト索引を組み直す実装が
        # 静かに通ってしまう。ここで別オブジェクトを返して差を出す。
        return int(str(self._revision))

    def count(self):
        return 512

    def bump(self):
        self._revision += 1


def test_the_index_is_built_once_and_reused(monkeypatch):
    """revision が変わらない限り組み直さない。

    判定を誤って常に真にすると、毎リクエストで57msの索引構築が走る。
    例外は出ず、遅くなるだけなので、テストでしか捕まえられない。
    """
    from scripts import rag_mcp_server

    calls = []
    monkeypatch.setattr(
        rag_mcp_server, "build_index", lambda collection: calls.append(1) or "索引"
    )
    state = rag_mcp_server._State()
    collection = _FakeCollection()

    assert rag_mcp_server._get_index(state, collection) == "索引"
    assert rag_mcp_server._get_index(state, collection) == "索引"
    assert rag_mcp_server._get_index(state, collection) == "索引"
    assert len(calls) == 1, "revisionが変わっていないのに組み直している"


def test_the_index_is_rebuilt_when_the_revision_changes(monkeypatch):
    """取り込みが走ったら組み直す。

    revision は書き込みトランザクションの内側で加算される。チャンク数を鍵に
    すると「同数の差し替え」を取りこぼし、消えた旧チャンクIDを持ったままの
    索引が理由の説明なくヒットを落とす（設計書6節）。
    """
    from scripts import rag_mcp_server

    calls = []
    monkeypatch.setattr(
        rag_mcp_server, "build_index", lambda collection: calls.append(1) or "索引"
    )
    state = rag_mcp_server._State()
    collection = _FakeCollection()

    rag_mcp_server._get_index(state, collection)
    collection.bump()
    rag_mcp_server._get_index(state, collection)

    assert len(calls) == 2


def test_the_reranker_is_not_loaded_until_the_first_search(monkeypatch):
    """検索しないセッションはリランカーを払わない。

    Codex はセッション開始時にサーバを起こす。起動時にロードすると、検索を
    1度もしないセッションが3.3秒と約570MBを払う（実測）。常にロードするよう
    壊しても例外は出ず、遅くなるだけなのでテストでしか捕まえられない。

    spy を仕掛けてから reload するのが要点である。import 済みのモジュールに
    後から spy を入れて表明しても、起動時ロードは既に終わっており、壊れた実装
    でもテストが通ってしまう（隔離環境で再現済み）。
    """
    import importlib

    from ingest import reranker
    from scripts import rag_mcp_server

    loaded = []
    monkeypatch.setattr(reranker, "check_reranker", lambda: loaded.append(1))
    importlib.reload(rag_mcp_server)

    assert loaded == [], "検索していないのにリランカーをロードしている"


def test_search_returns_the_no_hits_text_when_nothing_is_in_range(monkeypatch):
    """圏外なら0件が返り、その旨の文言になる。"""
    from scripts import rag_mcp_server

    monkeypatch.setattr(rag_mcp_server, "_open", lambda: _FakeCollection())
    monkeypatch.setattr(rag_mcp_server, "build_index", lambda collection: "索引")
    monkeypatch.setattr(rag_mcp_server, "_ensure_reranker", lambda: None)
    monkeypatch.setattr(rag_mcp_server, "search", lambda *a, **k: [])

    text = rag_mcp_server.search_documents("圏外の質問")
    assert "見つかりませんでした" in text


def test_every_argument_search_needs_is_wired_through(monkeypatch):
    """search() への配線を4つとも固定する。

    どれを外しても例外は出ない。index を落とせばハイブリッド検索のBM25側が
    黙って消え、rerank を落とせば並べ替えが効かなくなり、query を取り違えれば
    別の質問の答えが返る。いずれも「それらしい検索結果」の顔をして届くため、
    ここで固定しなければ気づけない。
    """
    from scripts import rag_mcp_server

    seen = {}
    reranker_marker = object()

    def fake_search(*args, **kwargs):
        seen["args"] = args
        seen["kwargs"] = kwargs
        return []

    monkeypatch.setattr(rag_mcp_server, "_open", lambda: _FakeCollection())
    monkeypatch.setattr(rag_mcp_server, "build_index", lambda collection: "索引")
    monkeypatch.setattr(rag_mcp_server, "_ensure_reranker", lambda: reranker_marker)
    monkeypatch.setattr(rag_mcp_server, "search", fake_search)

    rag_mcp_server.search_documents("有給休暇の付与日数", n_results=2)

    # query は位置引数で渡るため、kwargs だけを見ていると空文字への
    # すり替えを見逃す。
    args, kwargs = seen["args"], seen["kwargs"]
    positional = dict(zip(("collection", "query"), args))
    passed = {**positional, **kwargs}
    assert passed["query"] == "有給休暇の付与日数", "検索語がそのまま渡っていない"
    assert passed["index"] == "索引", "BM25索引を渡していない（ベクトル単独に退化する）"
    assert passed["rerank"] is reranker_marker, "リランカーを渡していない"
    assert passed["n_results"] == 2


def test_every_hit_search_returns_is_formatted(monkeypatch):
    """search() が返した件数をそのまま整形する。

    切り詰めても例外は出ず、エージェントには「2件しか無かった」と読める
    結果が届く。
    """
    from scripts import rag_mcp_server

    hits = [_hit(text="いち"), _hit(text="に"), _hit(text="さん")]

    monkeypatch.setattr(rag_mcp_server, "_open", lambda: _FakeCollection())
    monkeypatch.setattr(rag_mcp_server, "build_index", lambda collection: "索引")
    monkeypatch.setattr(rag_mcp_server, "_ensure_reranker", lambda: None)
    monkeypatch.setattr(rag_mcp_server, "search", lambda *a, **k: hits)

    text = rag_mcp_server.search_documents("質問")
    assert "3 件が見つかりました" in text
    for body in ("いち", "に", "さん"):
        assert body in text


def test_an_empty_store_says_the_ingest_has_not_run(monkeypatch):
    """0チャンクは「見つかりませんでした」ではない（設計書7節）。

    取り込みを忘れているのか、資料に無いのかを取り違えると、利用者は
    延々と質問を言い換えることになる。
    """
    from scripts import rag_mcp_server

    class _Empty(_FakeCollection):
        def count(self):
            return 0

    monkeypatch.setattr(rag_mcp_server, "_open", lambda: _Empty())

    text = rag_mcp_server.search_documents("質問")
    assert "取り込みが未実行" in text


def test_ollama_failure_is_returned_as_its_own_message(monkeypatch):
    """Ollama 未疎通の文言をそのまま返す。

    サーバは起動時に疎通確認しない。Codex がセッション開始時にサーバを起こす
    ため、そこで失敗させると Ollama を使わない作業まで巻き添えになる
    （設計書4.4節）。確認は最初の検索時に行う。
    """
    from ingest.embedder import EmbeddingError
    from scripts import rag_mcp_server

    def boom(*a, **k):
        raise EmbeddingError("Ollamaに接続できません（http://localhost:11434）")

    monkeypatch.setattr(rag_mcp_server, "_open", lambda: _FakeCollection())
    monkeypatch.setattr(rag_mcp_server, "build_index", lambda collection: "索引")
    monkeypatch.setattr(rag_mcp_server, "_ensure_reranker", lambda: None)
    monkeypatch.setattr(rag_mcp_server, "search", boom)

    text = rag_mcp_server.search_documents("質問")
    assert "Ollamaに接続できません" in text


def test_an_unexpected_error_is_not_disguised_as_a_search_result(monkeypatch):
    """想定外の例外は握りつぶさず、そのまま外へ出す。

    mcp 2.2.0 は、ツール関数が投げた例外を
    `CallToolResult(content=[...], is_error=True)` に変換して返す
    （mcp/server/mcpserver/tools/base.py:208-210 の
    `raise UnexpectedToolError(f"Error executing tool {self.name}") from exc` と
    mcp/server/mcpserver/server.py:447 を読んで確認、実測ではない）。
    エージェントが読めるのは定型文 "Error executing tool search_documents"
    だけで、元の例外文は届かない（mcp/server/mcpserver/exceptions.py:66-67 が
    「nothing from the original reaches the client」と明記している）。
    それでも外へ出すのは、詳細が失われる代償を払ってでも、バグが正常な検索結果と
    見分けのつく形で届くほうが良いからである。ここで拾うと、TypeError のような
    バグが「0件でした」や「Ollamaが落ちています」と見分けのつかない、正常な
    検索結果の顔をしてエージェントに届く。
    """
    import pytest

    from scripts import rag_mcp_server

    def boom(*a, **k):
        raise TypeError("bad argument")

    monkeypatch.setattr(rag_mcp_server, "_open", lambda: _FakeCollection())
    monkeypatch.setattr(rag_mcp_server, "build_index", lambda collection: "索引")
    monkeypatch.setattr(rag_mcp_server, "_ensure_reranker", lambda: None)
    monkeypatch.setattr(rag_mcp_server, "search", boom)

    with pytest.raises(TypeError):
        rag_mcp_server.search_documents("質問")


def test_check_reranker_is_called_only_once_across_two_searches(monkeypatch):
    """一度用意できたら、以降の検索では確認をやり直さない。

    やり直しても例外にはならず、無駄な確認が毎回走るだけなので、テストでしか
    捕まえられない。
    """
    from scripts import rag_mcp_server

    monkeypatch.setattr(rag_mcp_server, "_open", lambda: _FakeCollection())
    monkeypatch.setattr(rag_mcp_server, "build_index", lambda collection: "索引")
    monkeypatch.setattr(rag_mcp_server, "search", lambda *a, **k: [])

    calls = []
    monkeypatch.setattr(
        rag_mcp_server.reranker, "check_reranker", lambda: calls.append(1)
    )

    rag_mcp_server.search_documents("質問1")
    rag_mcp_server.search_documents("質問2")

    assert len(calls) == 1, "reranker_ready になった後も確認をやり直している"


def test_a_failed_reranker_check_is_retried_on_the_next_search(monkeypatch):
    """確認が失敗したら ready にしない。次の検索でまた試す。

    失敗しても ready を立てたままにすると、Ollama やモデル取得が後で直っても
    リランカーが二度と有効にならない。
    """
    from scripts import rag_mcp_server

    monkeypatch.setattr(rag_mcp_server, "_open", lambda: _FakeCollection())
    monkeypatch.setattr(rag_mcp_server, "build_index", lambda collection: "索引")
    monkeypatch.setattr(rag_mcp_server, "search", lambda *a, **k: [])

    calls = []

    def boom():
        calls.append(1)
        raise rag_mcp_server.reranker.RerankError("モデルを取得できません")

    monkeypatch.setattr(rag_mcp_server.reranker, "check_reranker", boom)

    rag_mcp_server.search_documents("質問1")
    rag_mcp_server.search_documents("質問2")

    assert len(calls) == 2, "確認が失敗したのに ready のまま扱っている"


def test_the_store_is_opened_once_across_two_searches(monkeypatch):
    """ストアを開くのはプロセスで1度だけ。

    open_store() は読み取りではない。VectorStore.__init__ が
    executescript(_SCHEMA) と commit() を実行するため、開くたびにSQLiteの
    書き込みロックを取りにいく。毎リクエスト開き直す実装は、取り込みが
    走っている最中の検索を busy_timeout ぶん待たせたうえ
    "database is locked" で落とす。平時は何も起きないので、テストでしか
    捕まえられない。
    """
    from scripts import rag_mcp_server

    opens = []

    def counting_open():
        opens.append(1)
        return _FakeCollection()

    monkeypatch.setattr(rag_mcp_server, "_open", counting_open)
    monkeypatch.setattr(rag_mcp_server, "build_index", lambda collection: "索引")
    monkeypatch.setattr(rag_mcp_server, "_ensure_reranker", lambda: None)
    monkeypatch.setattr(rag_mcp_server, "search", lambda *a, **k: [])

    rag_mcp_server.search_documents("質問1")
    rag_mcp_server.search_documents("質問2")

    assert len(opens) == 1, "リクエストごとにDBを開き直している"
