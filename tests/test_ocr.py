import pymupdf
import pytest

import ingest.ocr as ocr_module
from ingest.ocr import OCR_DPI, ocr_page, reset_engine


class _FakeResult:
    def __init__(self, txts):
        self.txts = txts


@pytest.fixture(autouse=True)
def _clean_engine():
    reset_engine()
    yield
    reset_engine()


@pytest.fixture
def blank_page():
    doc = pymupdf.open()
    doc.new_page()
    yield doc[0]
    doc.close()


def test_engine_is_not_created_until_first_use():
    """エンジン生成に実測4.8秒かかるため、画像ページに遭遇するまで作らない。"""
    assert ocr_module._engine is None


def test_recognized_texts_are_joined(blank_page, monkeypatch):
    monkeypatch.setattr(
        ocr_module, "_build_engine", lambda: (lambda _img: _FakeResult(["社内", "ナレッジ"]))
    )
    assert ocr_page(blank_page) == "社内 ナレッジ"


def test_engine_is_built_only_once(blank_page, monkeypatch):
    calls = []

    def _build():
        calls.append(1)
        return lambda _img: _FakeResult(["文字"])

    monkeypatch.setattr(ocr_module, "_build_engine", _build)
    ocr_page(blank_page)
    ocr_page(blank_page)
    assert len(calls) == 1


def test_no_recognized_text_returns_empty_string(blank_page, monkeypatch):
    monkeypatch.setattr(
        ocr_module, "_build_engine", lambda: (lambda _img: _FakeResult(None))
    )
    assert ocr_page(blank_page) == ""


def test_dpi_is_200():
    """150/200/300dpiで精度も速度も変わらなかったため、上げる意味がない。"""
    assert OCR_DPI == 200


@pytest.mark.integration
def test_real_engine_reads_japanese_from_the_source_pdf():
    """実機確認。初回はモデルのダウンロードが走る。"""
    from pathlib import Path

    pdf = Path("source/Claude_Code_法人導入ガイド_スライド.pdf")
    if not pdf.exists():
        pytest.skip("source PDFがありません")
    doc = pymupdf.open(pdf)
    text = ocr_page(doc[0])
    doc.close()
    assert "本コース" in text
