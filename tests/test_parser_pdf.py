import pymupdf
import pytest

from ingest.parsers import parse
from ingest.parsers.pdf_parser import OCR_MIN_CHARS, parse_pdf


def _make_pdf(tmp_path, page_texts):
    """指定した文字列を各ページに書いたPDFを生成する。空文字なら白紙ページ。"""
    doc = pymupdf.open()
    for text in page_texts:
        page = doc.new_page()
        if text:
            page.insert_text((72, 72), text, fontsize=14)
    path = tmp_path / "test.pdf"
    doc.save(path)
    doc.close()
    return path


@pytest.fixture
def text_pdf(tmp_path):
    return _make_pdf(tmp_path, ["Chapter one has plenty of extractable text here."])


@pytest.fixture
def image_pdf(tmp_path):
    """テキストを持たない白紙ページ = 画像PDFと同じ扱いになる。"""
    return _make_pdf(tmp_path, [""])


def test_text_page_is_extracted_without_ocr(text_pdf):
    def _fail(_page):
        raise AssertionError("テキストがあるページでOCRを呼んではいけない")

    units = parse_pdf(text_pdf, ocr_page=_fail)
    assert len(units) == 1
    assert "Chapter one" in units[0].text
    assert units[0].ocr is False


def test_page_without_text_falls_back_to_ocr(image_pdf):
    units = parse_pdf(image_pdf, ocr_page=lambda _page: "OCRで読んだ文字")
    assert len(units) == 1
    assert units[0].text == "OCRで読んだ文字"
    assert units[0].ocr is True


def test_pages_are_numbered_from_one(tmp_path):
    path = _make_pdf(tmp_path, ["First page with enough text to skip OCR entirely.",
                                "Second page with enough text to skip OCR entirely."])
    units = parse_pdf(path, ocr_page=lambda _page: "")
    assert [u.location for u in units] == [1, 2]
    assert all(u.location_type == "page" for u in units)


def test_page_is_skipped_when_ocr_also_finds_nothing(image_pdf):
    """白紙ページで空チャンクを作らない。"""
    assert parse_pdf(image_pdf, ocr_page=lambda _page: "") == []


def test_ocr_threshold_is_30_characters():
    """就業規則PDFの最少ページが66字、画像PDFが0字。この境界で完全に分離できる。"""
    assert OCR_MIN_CHARS == 30


def test_dispatch_handles_pdf(text_pdf):
    assert parse(text_pdf)[0].location_type == "page"
