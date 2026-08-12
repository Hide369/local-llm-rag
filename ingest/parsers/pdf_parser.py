"""PDFのテキスト抽出。画像ページはOCRへ回す。

source/ の実測では、テキストPDF(モデル就業規則)は最少ページでも66文字、
画像PDF(Claude_Code_法人導入ガイド)は全23ページが0文字だった。
30文字を境界にすれば実データ上は完全に分離できる。
"""
from pathlib import Path

import pymupdf

from ingest.models import PAGE, ParsedUnit

OCR_MIN_CHARS = 30


def parse_pdf(path: Path, ocr_page=None) -> list[ParsedUnit]:
    """PDFを1ページ1ユニットで読む。

    ocr_page はテストで差し替えられるよう引数にしている。省略時は実際のOCRを使う。
    """
    if ocr_page is None:
        from ingest.ocr import ocr_page as ocr_page_impl

        ocr_page = ocr_page_impl

    units = []
    doc = pymupdf.open(path)
    try:
        for number, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()
            used_ocr = False
            if len(text) < OCR_MIN_CHARS:
                text = ocr_page(page).strip()
                used_ocr = True
            if text:
                units.append(
                    ParsedUnit(
                        text=text, location_type=PAGE, location=number, ocr=used_ocr
                    )
                )
    finally:
        doc.close()
    return units
