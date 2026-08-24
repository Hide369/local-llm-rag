"""PDFのテキスト抽出。画像ページはOCRへ回す。

source/ の実測では、テキストPDF(モデル就業規則)は最少ページでも66文字、
画像PDF(Claude_Code_法人導入ガイド)は全23ページが0文字だった。
30文字を境界にすれば実データ上は完全に分離できる。
"""
import sys
from pathlib import Path

import pymupdf

from ingest.models import PAGE, ParsedUnit
from ingest.vlm import VlmError

OCR_MIN_CHARS = 30

# ロゴ・アイコン等の装飾画像を除外するための閾値（px角）。実データでの実測は
# design docの5節を参照。未実測の仮値であり、後日調整する前提。
MIN_IMAGE_WIDTH = 150
MIN_IMAGE_HEIGHT = 150


def _describe_images(doc, page, page_number: int, source_name: str, caption_image) -> list[str]:
    """ページに埋め込まれた図・写真をVLMで説明文にする。1枚失敗しても残りは続ける。"""
    captions = []
    for xref, _smask, width, height, *_rest in page.get_images(full=True):
        if width < MIN_IMAGE_WIDTH or height < MIN_IMAGE_HEIGHT:
            continue
        image_bytes = doc.extract_image(xref)["image"]
        try:
            captions.append(caption_image(image_bytes))
        except VlmError as error:
            print(
                f"警告: 画像の説明取得に失敗しました（{source_name} p.{page_number}）: {error}",
                file=sys.stderr,
            )
    return captions


def parse_pdf(path: Path, ocr_page=None, caption_image=None) -> list[ParsedUnit]:
    """PDFを1ページ1ユニットで読む。

    ocr_page/caption_image はテストで差し替えられるよう引数にしている。
    caption_image を省略した場合（既定）は画像の説明文化を一切行わない。
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

            used_vlm = False
            if caption_image is not None:
                for caption in _describe_images(doc, page, number, path.name, caption_image):
                    text = f"{text}\n\n[図の説明] {caption}".strip()
                    used_vlm = True

            if text:
                units.append(
                    ParsedUnit(
                        text=text,
                        location_type=PAGE,
                        location=number,
                        ocr=used_ocr,
                        vlm=used_vlm,
                    )
                )
    finally:
        doc.close()
    return units
