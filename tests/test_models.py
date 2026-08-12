from ingest.models import Chunk, ParsedUnit


def test_page_unit_label():
    unit = ParsedUnit(text="本文", location_type="page", location=48)
    assert unit.label == "p.48"


def test_slide_unit_label():
    unit = ParsedUnit(text="本文", location_type="slide", location=12)
    assert unit.label == "スライド12"


def test_document_unit_has_no_label():
    """docxのようにページ概念を持たない形式では位置ラベルを出さない。"""
    unit = ParsedUnit(text="本文", location_type="document", location=0)
    assert unit.label == ""


def test_unit_is_not_ocr_by_default():
    assert ParsedUnit(text="本文", location_type="page", location=1).ocr is False


def test_chunk_holds_id_text_and_metadata():
    chunk = Chunk(id="a.pdf::page1::0", text="本文", metadata={"source": "a.pdf"})
    assert chunk.id == "a.pdf::page1::0"
    assert chunk.metadata["source"] == "a.pdf"
