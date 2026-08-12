from ingest.models import SECTION, Chunk, ParsedUnit


def test_unit_is_not_ocr_by_default():
    assert ParsedUnit(text="本文", location_type="page", location=1).ocr is False


def test_unit_has_no_heading_by_default():
    """ページやスライド由来のユニットは見出しを持たない。"""
    assert ParsedUnit(text="本文", location_type="page", location=1).heading == ""


def test_section_unit_keeps_its_heading():
    """Markdownの見出しは出典表示に使うため、ユニットが運ぶ必要がある。"""
    unit = ParsedUnit(
        text="本文", location_type=SECTION, location=3, heading="設置情報"
    )
    assert unit.heading == "設置情報"


def test_section_location_type_is_section():
    assert SECTION == "section"


def test_chunk_holds_id_text_and_metadata():
    chunk = Chunk(id="a.pdf::page1::0", text="本文", metadata={"source": "a.pdf"})
    assert chunk.id == "a.pdf::page1::0"
    assert chunk.metadata["source"] == "a.pdf"
