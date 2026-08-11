import subprocess
import sys
from pathlib import Path

import pymupdf
import pytest

import ingest.ocr as ocr_module
from ingest.ocr import OCR_DPI, ocr_page, reset_engine

_REPO_ROOT = Path(__file__).resolve().parent.parent


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
    """エンジン生成に実測4.8秒かかるため、画像ページに遭遇するまで作らない。

    同一プロセス内で `ocr_module._engine is None` を見ても検証にならない。
    autouseフィクスチャ `_clean_engine` が毎テストのsetupで `reset_engine()`
    を呼ぶため、実装がimport時にエンジンを生成していようがいまいが、この
    アサーションは常に真になってしまう（＝遅延初期化を壊す回帰を検知できない）。
    そこで別プロセスを起動し、`import ingest.ocr` した直後の時点で
    RapidOCRの依存先である `rapidocr` が `sys.modules` にまだ存在しない
    ことを確認する。これなら import時に `_build_engine()` を呼ぶような
    実装に壊れた場合、子プロセスのassertが失敗し終了コードが非ゼロになる。
    """
    script = (
        "import sys\n"
        "import ingest.ocr\n"
        "assert 'rapidocr' not in sys.modules, "
        "'rapidocr was imported at ingest.ocr import time'\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        cwd=_REPO_ROOT,
    )
    assert result.returncode == 0, result.stderr


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
    pdf = Path("source/Claude_Code_法人導入ガイド_スライド.pdf")
    if not pdf.exists():
        pytest.skip("source PDFがありません")
    doc = pymupdf.open(pdf)
    text = ocr_page(doc[0])
    doc.close()
    assert "本コース" in text
