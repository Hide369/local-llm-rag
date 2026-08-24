import io

import pymupdf
import pytest
from PIL import Image

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


def _png_bytes(width, height, color="red"):
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color).save(buf, format="PNG")
    return buf.getvalue()


def _make_pdf_with_image(tmp_path, text, image_bytes, filename="画像入り.pdf"):
    doc = pymupdf.open()
    page = doc.new_page()
    if text:
        page.insert_text((72, 72), text, fontsize=14)
    page.insert_image(pymupdf.Rect(50, 200, 250, 400), stream=image_bytes)
    path = tmp_path / filename
    doc.save(path)
    doc.close()
    return path


@pytest.fixture
def pdf_with_large_image(tmp_path):
    return _make_pdf_with_image(
        tmp_path,
        "Chapter one has plenty of extractable text here.",
        _png_bytes(300, 300),
    )


@pytest.fixture
def pdf_with_small_image(tmp_path):
    return _make_pdf_with_image(
        tmp_path,
        "Chapter one has plenty of extractable text here.",
        _png_bytes(40, 40),
    )


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


def test_page_at_exactly_threshold_is_not_sent_to_ocr(tmp_path):
    """しきい値ちょうど(30文字)はOCRへ回さず抽出テキストをそのまま使う。

    ``if len(text) < OCR_MIN_CHARS`` が誤って ``<=`` に変わっても、
    定数値だけを見る test_ocr_threshold_is_30_characters では検知できない。
    この境界値テストで分岐の向きそのものを保証する。
    """
    # 抽出後の文字数を手計算で当てにせず、PDFへ書き込んだ文字列と同じ長さになる
    # ことを実測済みのパターンで組み立てる（check_len3.py で 29/30 文字とも
    # 抽出前後で完全一致することを確認済み）。
    text = ("Boundary text " + "x" * OCR_MIN_CHARS)[:OCR_MIN_CHARS]
    assert len(text) == OCR_MIN_CHARS
    path = _make_pdf(tmp_path, [text])

    def _fail(_page):
        raise AssertionError("しきい値ちょうどのページでOCRを呼んではいけない")

    units = parse_pdf(path, ocr_page=_fail)
    assert len(units) == 1
    assert units[0].text == text
    assert units[0].ocr is False


def test_page_one_under_threshold_is_sent_to_ocr(tmp_path):
    """しきい値-1文字(29文字)は抽出テキストを捨ててOCRへ回す。

    しきい値ちょうどのテストと対にすることで、境界の両側を分岐させる
    ``<`` の向きを直接検証する。
    """
    text = ("Boundary text " + "x" * (OCR_MIN_CHARS - 1))[: OCR_MIN_CHARS - 1]
    assert len(text) == OCR_MIN_CHARS - 1
    path = _make_pdf(tmp_path, [text])

    units = parse_pdf(path, ocr_page=lambda _page: "OCRフォールバック文字列")
    assert len(units) == 1
    assert units[0].text == "OCRフォールバック文字列"
    assert units[0].ocr is True


def test_dispatch_handles_pdf(text_pdf):
    assert parse(text_pdf)[0].location_type == "page"


def test_caption_image_not_called_when_not_provided(pdf_with_large_image):
    def _fail(_bytes):
        raise AssertionError("caption_imageが未指定なら呼ばれてはいけない")

    units = parse_pdf(pdf_with_large_image, ocr_page=_fail, caption_image=None)
    assert "[図の説明]" not in units[0].text
    assert units[0].vlm is False


def test_large_embedded_image_is_captioned(pdf_with_large_image):
    def _ocr_not_called(_page):
        raise AssertionError("テキストがあるページでOCRを呼んではいけない")

    units = parse_pdf(
        pdf_with_large_image,
        ocr_page=_ocr_not_called,
        caption_image=lambda _bytes: "赤い正方形の図です。",
    )
    assert "Chapter one" in units[0].text
    assert "[図の説明] 赤い正方形の図です。" in units[0].text
    assert units[0].vlm is True


def test_small_embedded_image_is_not_captioned(pdf_with_small_image):
    def _fail(_bytes):
        raise AssertionError("閾値未満の画像でcaption_imageが呼ばれてはいけない")

    def _ocr_not_called(_page):
        raise AssertionError("テキストがあるページでOCRを呼んではいけない")

    units = parse_pdf(pdf_with_small_image, ocr_page=_ocr_not_called, caption_image=_fail)
    assert "[図の説明]" not in units[0].text
    assert units[0].vlm is False


def test_caption_failure_is_skipped_with_a_warning(pdf_with_large_image, capsys):
    from ingest.vlm import VlmError

    def _ocr_not_called(_page):
        raise AssertionError("テキストがあるページでOCRを呼んではいけない")

    def _raise(_bytes):
        raise VlmError("boom")

    units = parse_pdf(pdf_with_large_image, ocr_page=_ocr_not_called, caption_image=_raise)
    assert "[図の説明]" not in units[0].text
    assert units[0].vlm is False
    assert "boom" in capsys.readouterr().err
