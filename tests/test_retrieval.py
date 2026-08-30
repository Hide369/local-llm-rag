import pytest

from ingest import lexical
from ingest.reranker import RerankError
from ingest.retrieval import (
    RERANK_CANDIDATE_COUNT,
    Hit,
    build_index,
    contextual_query,
    search,
)


class _FakeCollection:
    def __init__(self, documents, distances, metadatas, ids=None, vector_limit=None):
        self._ids = ids or [f"id-{n}" for n in range(len(documents))]
        self._documents = documents
        self._distances = distances
        self._metadatas = metadatas
        # 実Chromaは距離の昇順で返す。挿入順のまま返すと、RRFの並べ替えを検証する
        # テストが「ベクトル1位＝BM25 1位」の自明なケースになってしまう。
        self._order = sorted(range(len(documents)), key=lambda row: distances[row])
        # ベクトル側が返す件数の上限。BM25だけが見つけるチャンクを作るために使う。
        self._vector_limit = vector_limit

    def count(self):
        return len(self._documents)

    def query(self, query_embeddings, n_results):
        rows = self._order[: min(n_results, self._vector_limit or n_results)]
        return {
            "ids": [[self._ids[row] for row in rows]],
            "documents": [[self._documents[row] for row in rows]],
            "distances": [[self._distances[row] for row in rows]],
            "metadatas": [[self._metadatas[row] for row in rows]],
        }

    def get(self, ids=None, include=None):
        # ids 省略は全件（store.all_documents がこの形で呼ぶ）。
        # 知らないIDは黙って落とす。実Chromaも消えたIDの行は返さない。
        rows = (
            list(range(len(self._ids)))
            if ids is None
            else [self._ids.index(i) for i in ids if i in self._ids]
        )
        return {
            "ids": [self._ids[row] for row in rows],
            "documents": [self._documents[row] for row in rows],
            "metadatas": [self._metadatas[row] for row in rows],
        }


def _meta(source="a.pdf", location_type="page", location=48, ocr=False, heading=""):
    return {
        "source": source,
        "location_type": location_type,
        "location": location,
        "ocr": ocr,
        "heading": heading,
    }


@pytest.fixture(autouse=True)
def _no_real_embedding(monkeypatch):
    monkeypatch.setattr("ingest.retrieval.embed_query", lambda _q, session=None: [0.1])


def test_page_citation():
    hit = Hit(text="本文", distance=0.1, metadata=_meta())
    assert hit.citation == "a.pdf p.48"


def test_slide_citation():
    hit = Hit(text="本文", distance=0.1, metadata=_meta(location_type="slide", location=12))
    assert hit.citation == "a.pdf スライド12"


def test_document_citation_has_no_position():
    hit = Hit(text="本文", distance=0.1, metadata=_meta(location_type="document", location=0))
    assert hit.citation == "a.pdf"


def test_section_citation_shows_the_heading():
    hit = Hit(
        text="本文",
        distance=0.1,
        metadata=_meta(
            source="家電製品/UD-0900i_spec_step3.md",
            location_type="section",
            location=3,
            heading="設置情報",
        ),
    )
    assert hit.citation == "家電製品/UD-0900i_spec_step3.md ＞ 設置情報"


def test_section_without_a_heading_shows_only_the_file():
    """見出しのないMarkdownでは、空の『＞』を出さない。"""
    hit = Hit(
        text="本文",
        distance=0.1,
        metadata=_meta(location_type="section", location=1, heading=""),
    )
    assert hit.citation == "a.pdf"


def test_ocr_hits_are_marked():
    """OCR由来は小書き仮名が崩れることがあるため、根拠として示すときに明示する。"""
    hit = Hit(text="本文", distance=0.1, metadata=_meta(ocr=True))
    assert hit.citation == "a.pdf p.48（OCR）"


def test_contextual_query_is_the_question_itself_without_history():
    assert contextual_query("決定事項を教えてほしい", []) == "決定事項を教えてほしい"


def test_contextual_query_prepends_the_previous_question():
    """追質問は単独では検索できない。

    実測: 「決定事項を教えてほしい」だけで引くと上位4件は導入ガイドPDFと就業規則で、
    議事録は1件も入らなかった（距離0.456〜0.459）。直前の質問を継ぎ足すと
    第5回議事録が0.401で1位になる。
    """
    history = [
        {"role": "user", "content": "第5回会議のタイトルを教えてほしい"},
        {"role": "assistant", "content": "「AI活用プロジェクト 第5回…」です。"},
    ]
    assert contextual_query("決定事項を教えてほしい", history) == (
        "第5回会議のタイトルを教えてほしい 決定事項を教えてほしい"
    )


def test_contextual_query_uses_only_the_latest_previous_question():
    """履歴を全部つなぐと、古い話題が検索を引っ張る。継ぎ足すのは直前の1問だけ。"""
    history = [
        {"role": "user", "content": "有給休暇は何日もらえますか"},
        {"role": "assistant", "content": "…"},
        {"role": "user", "content": "第5回会議のタイトルを教えてほしい"},
        {"role": "assistant", "content": "…"},
    ]
    query = contextual_query("決定事項を教えてほしい", history)
    assert query == "第5回会議のタイトルを教えてほしい 決定事項を教えてほしい"
    assert "有給休暇" not in query


def test_far_results_are_dropped():
    collection = _FakeCollection(["近い", "遠い"], [0.10, 0.90], [_meta(), _meta()])
    hits = search(collection, "質問", threshold=0.5)
    assert [h.text for h in hits] == ["近い"]


def test_empty_collection_returns_nothing():
    assert search(_FakeCollection([], [], []), "質問", threshold=0.5) == []


def test_hits_keep_their_distance():
    collection = _FakeCollection(["本文"], [0.25], [_meta()])
    assert search(collection, "質問", threshold=0.5)[0].distance == 0.25


def _hybrid(documents, distances, vector_limit=None):
    """フェイクのコレクションと、その全文から作ったBM25インデックスの対。"""
    ids = [f"id-{n}" for n in range(len(documents))]
    collection = _FakeCollection(
        documents,
        distances,
        [_meta()] * len(documents),
        ids=ids,
        vector_limit=vector_limit,
    )
    return collection, lexical.build(ids, documents)


def test_a_bm25_hit_is_admitted_when_the_question_is_in_domain():
    """今回の症状そのもの。語を含むチャンクのベクトル距離がしきい値を超えていても、
    質問自体が圏内ならBM25側が拾う。"""
    collection, index = _hybrid(
        ["ファインチューニングとは追加学習である", "この資料の概要です"],
        [0.60, 0.10],
    )
    hits = search(collection, "ファインチューニング", index=index, threshold=0.5)
    rescued = next(h for h in hits if h.text.startswith("ファインチューニング"))
    assert rescued.distance == 0.60
    assert rescued.bm25_score > 0


def test_no_bm25_hit_is_admitted_when_the_gate_is_closed():
    """圏外の質問。ベクトル側が1件も閾値を通らなければ、語が一致しても採用しない。
    BM25スコアに下限を置かない代わりに、この関門が圏外を落とす。"""
    collection, index = _hybrid(
        ["ファインチューニングとは追加学習である", "無関係な文章"],
        [0.60, 0.62],
    )
    assert search(collection, "ファインチューニング", index=index, threshold=0.5) == []


def test_a_vector_hit_is_admitted_with_no_lexical_match():
    """言い換えの質問はBM25では引けない。ベクトル側だけで通ること。"""
    collection, index = _hybrid(["近い", "遠い"], [0.10, 0.90])
    hits = search(collection, "まったく別の語", index=index, threshold=0.5)
    assert [h.text for h in hits] == ["近い"]
    assert hits[0].bm25_score is None


def test_results_are_ordered_by_rrf_not_by_distance():
    """両アームで上位のものが、ベクトル単独で1位のものより上に来る。"""
    collection, index = _hybrid(
        ["ファインチューニングの解説", "やや近いだけの文章"], [0.30, 0.20]
    )
    hits = search(collection, "ファインチューニング", index=index, threshold=0.5)
    assert hits[0].text == "ファインチューニングの解説"


def test_hits_carry_both_scores():
    collection, index = _hybrid(["ファインチューニングの解説"], [0.30])
    hit = search(collection, "ファインチューニング", index=index, threshold=0.5)[0]
    assert hit.distance == 0.30
    assert hit.bm25_score > 0
    assert hit.rrf_score > 0


def test_n_results_caps_the_output():
    collection, index = _hybrid(
        ["ファインチューニング一", "ファインチューニング二", "ファインチューニング三"],
        [0.10, 0.11, 0.12],
    )
    hits = search(
        collection, "ファインチューニング", index=index, threshold=0.5, n_results=2
    )
    assert len(hits) == 2


def test_a_chunk_only_bm25_finds_is_fetched_from_the_collection():
    """BM25側にしか現れないチャンクは本文もメタデータも持っていない。
    collection.get で取りに行かないと、根拠として画面に出せない。"""
    collection, index = _hybrid(
        ["この資料の概要です", "ファインチューニングとは追加学習である"],
        [0.10, 0.60],
        vector_limit=1,
    )
    hits = search(collection, "ファインチューニング", index=index, threshold=0.5)
    fetched = next(h for h in hits if h.text.startswith("ファインチューニング"))
    assert fetched.distance is None
    assert fetched.bm25_score > 0


def test_a_stale_index_entry_is_skipped():
    """インデックスは起動時のスナップショット。取り込みでチャンクが消えると
    存在しないIDが残り、collection.get はその行を返さない。落とさず読み飛ばす。"""
    collection, _ = _hybrid(["この資料の概要です"], [0.10])
    stale = lexical.build(
        ["id-0", "消えたID"],
        ["この資料の概要です", "ファインチューニングとは追加学習である"],
    )
    hits = search(collection, "ファインチューニング", index=stale, threshold=0.5)
    assert [h.text for h in hits] == ["この資料の概要です"]


def test_build_index_over_an_empty_collection_is_safe():
    assert build_index(_FakeCollection([], [], [])).document_count == 0


def test_rerank_is_not_called_when_not_given():
    """既存の呼び出しは1件も結果が変わらない（後方互換の回帰）。"""
    collection = _FakeCollection(
        ["あ" * 20, "い" * 20, "う" * 20],
        [0.10, 0.20, 0.30],
        [_meta(location=1), _meta(location=2), _meta(location=3)],
    )
    hits = search(collection, "質問")
    assert [hit.metadata["location"] for hit in hits] == [1, 2, 3]
    assert all(hit.rerank_score is None for hit in hits)


def test_rerank_reorders_the_results():
    """RRF 3位のチャンクをリランカーが1位に押し上げられる。"""
    collection = _FakeCollection(
        ["あ" * 20, "い" * 20, "う" * 20],
        [0.10, 0.20, 0.30],
        [_meta(location=1), _meta(location=2), _meta(location=3)],
    )

    def fake_rerank(query, texts):
        # 距離が遠いチャンク（3番目）に最高スコアを与える
        return [0.0, 1.0, 5.0]

    hits = search(collection, "質問", rerank=fake_rerank)
    assert [hit.metadata["location"] for hit in hits] == [3, 2, 1]
    assert hits[0].rerank_score == 5.0


def test_only_the_top_candidates_are_reranked():
    """RERANK_CANDIDATE_COUNT 件までしかリランカーに渡さない。1.34秒の根拠。"""
    count = 12
    collection = _FakeCollection(
        [f"本文{n}" * 10 for n in range(count)],
        [0.10 + n * 0.01 for n in range(count)],
        [_meta(location=n) for n in range(count)],
    )
    seen = []

    def fake_rerank(query, texts):
        seen.append(len(texts))
        return [float(n) for n in range(len(texts))]

    search(collection, "質問", rerank=fake_rerank)
    assert seen == [RERANK_CANDIDATE_COUNT]


def test_rerank_failure_falls_back_to_the_rrf_order():
    """リランカーは増幅器であって関門ではない。失敗しても結果は残す。"""
    collection = _FakeCollection(
        ["あ" * 20, "い" * 20, "う" * 20],
        [0.10, 0.20, 0.30],
        [_meta(location=1), _meta(location=2), _meta(location=3)],
    )

    def broken_rerank(query, texts):
        raise RerankError("模擬失敗")

    hits = search(collection, "質問", rerank=broken_rerank)
    assert [hit.metadata["location"] for hit in hits] == [1, 2, 3]


def test_rerank_failure_leaves_the_score_unmeasured():
    """失敗を隠さない。None は「低い」ではなく「測っていない」を意味する。"""
    collection = _FakeCollection(
        ["あ" * 20], [0.10], [_meta(location=1)]
    )

    def broken_rerank(query, texts):
        raise RerankError("模擬失敗")

    hits = search(collection, "質問", rerank=broken_rerank)
    assert hits[0].rerank_score is None


def test_rerank_does_not_open_the_gate():
    """圏外の質問はリランカーを渡しても空のまま。ゲートは距離が単独で担う。"""
    collection = _FakeCollection(
        ["あ" * 20], [0.90], [_meta(location=1)]
    )
    called = []

    def fake_rerank(query, texts):
        called.append(1)
        return [99.0]

    assert search(collection, "質問", rerank=fake_rerank) == []
    assert called == []


def test_reranked_ties_are_broken_deterministically():
    """同点でも並びが決まること。揺れると同じ質問で根拠の順序が再現しない。"""
    collection = _FakeCollection(
        ["あ" * 20, "い" * 20, "う" * 20],
        [0.30, 0.10, 0.20],
        [_meta(location=1), _meta(location=2), _meta(location=3)],
    )

    def flat_rerank(query, texts):
        return [1.0] * len(texts)

    first = search(collection, "質問", rerank=flat_rerank)
    second = search(collection, "質問", rerank=flat_rerank)
    assert [h.metadata["location"] for h in first] == [
        h.metadata["location"] for h in second
    ]
