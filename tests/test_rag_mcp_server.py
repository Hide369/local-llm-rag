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
