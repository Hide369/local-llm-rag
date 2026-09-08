"""MCPサーバの整形。

サーバを起動せずに検証する。@mcp.tool() は元の関数をそのまま返すため、
ツール関数もモジュールから直接呼べる。
"""
from ingest.retrieval import Hit
from scripts.rag_mcp_server import format_results


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


def test_search_passes_n_results_through(monkeypatch):
    """n_results がそのまま search() に渡る。"""
    from scripts import rag_mcp_server

    seen = {}

    def fake_search(collection, query, **kwargs):
        seen.update(kwargs)
        return []

    monkeypatch.setattr(rag_mcp_server, "_open", lambda: _FakeCollection())
    monkeypatch.setattr(rag_mcp_server, "build_index", lambda collection: "索引")
    monkeypatch.setattr(rag_mcp_server, "_ensure_reranker", lambda: None)
    monkeypatch.setattr(rag_mcp_server, "search", fake_search)

    rag_mcp_server.search_documents("質問", n_results=2)
    assert seen["n_results"] == 2


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
