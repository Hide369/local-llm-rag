import pytest
from docx import Document
from pptx import Presentation
from pptx.util import Inches

from ingest.parsers import UnsupportedFormatError, parse
from ingest.parsers.docx_parser import parse_docx
from ingest.parsers.pptx_parser import parse_pptx


@pytest.fixture
def docx_path(tmp_path):
    """テスト用のdocxをその場で生成する（バイナリをリポジトリに置かないため）。"""
    doc = Document()
    doc.add_paragraph("会議名：キックオフ")
    doc.add_paragraph("")  # 空段落は無視されること
    doc.add_paragraph("決定事項：RAGを導入する")
    path = tmp_path / "議事録.docx"
    doc.save(path)
    return path


@pytest.fixture
def pptx_path(tmp_path):
    prs = Presentation()
    blank = prs.slide_layouts[6]

    slide1 = prs.slides.add_slide(blank)
    box = slide1.shapes.add_textbox(Inches(1), Inches(1), Inches(4), Inches(1))
    box.text_frame.text = "一枚目のタイトル"

    slide2 = prs.slides.add_slide(blank)
    box2 = slide2.shapes.add_textbox(Inches(1), Inches(1), Inches(4), Inches(1))
    box2.text_frame.text = "二枚目の本文"
    slide2.notes_slide.notes_text_frame.text = "発表者ノート"

    path = tmp_path / "資料.pptx"
    prs.save(path)
    return path


def test_docx_becomes_a_single_document_unit(docx_path):
    units = parse_docx(docx_path)
    assert len(units) == 1
    assert units[0].location_type == "document"
    assert units[0].location == 0


def test_docx_joins_paragraphs_and_drops_empty_ones(docx_path):
    text = parse_docx(docx_path)[0].text
    assert "会議名：キックオフ" in text
    assert "決定事項：RAGを導入する" in text
    assert "\n\n" not in text


def test_pptx_produces_one_unit_per_slide(pptx_path):
    units = parse_pptx(pptx_path)
    assert len(units) == 2
    assert [u.location for u in units] == [1, 2]
    assert all(u.location_type == "slide" for u in units)


def test_pptx_includes_speaker_notes(pptx_path):
    """ノート欄には本文に書かれない補足が入るため取り込み対象にする。"""
    assert "発表者ノート" in parse_pptx(pptx_path)[1].text


def test_pptx_slide_text_is_captured(pptx_path):
    assert "一枚目のタイトル" in parse_pptx(pptx_path)[0].text


def test_office_parsers_are_not_marked_as_ocr(docx_path, pptx_path):
    assert parse_docx(docx_path)[0].ocr is False
    assert all(u.ocr is False for u in parse_pptx(pptx_path))


def test_dispatch_routes_by_suffix(docx_path, pptx_path):
    assert parse(docx_path)[0].location_type == "document"
    assert parse(pptx_path)[0].location_type == "slide"


def test_dispatch_rejects_unsupported_suffix(tmp_path):
    other = tmp_path / "memo.txt"
    other.write_text("本文", encoding="utf-8")
    with pytest.raises(UnsupportedFormatError):
        parse(other)
