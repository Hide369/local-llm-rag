import pytest

from ingest.retrieval import Hit, contextual_query, search


class _FakeCollection:
    def __init__(self, documents, distances, metadatas):
        self._payload = {
            "documents": [documents],
            "distances": [distances],
            "metadatas": [metadatas],
        }

    def count(self):
        return len(self._payload["documents"][0])

    def query(self, query_embeddings, n_results):
        return self._payload


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
