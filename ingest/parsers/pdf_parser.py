"""PDFのテキスト抽出。画像ページはOCR、またはVLMが使えるならVLMの説明文へ回す。

source/ の実測では、テキストPDF(モデル就業規則)は最少ページでも66文字、
画像PDF(Claude_Code_法人導入ガイド)は全23ページが0文字だった。
30文字を境界にすれば実データ上は完全に分離できる。

VLM（caption_image）が渡されているページは、OCRの誤認識（README「既知の制約」
参照）を避けるためVLMの説明文を優先し、OCRは説明文が1件も得られなかったときの
フォールバックにする。
"""
import sys
from pathlib import Path

import pymupdf

from ingest.models import PAGE, ParsedUnit

OCR_MIN_CHARS = 30

# ロゴ・アイコン等の装飾画像を除外するための閾値（px角）。実データでの実測は
# design docの5節を参照。未実測の仮値であり、後日調整する前提。
MIN_IMAGE_WIDTH = 150
MIN_IMAGE_HEIGHT = 150


def _describe_images(doc, page, page_number: int, source_name: str, caption_image) -> list[str]:
    """ページに埋め込まれた図・写真をVLMで説明文にする。1枚失敗しても残りは続ける。

    画像の取り出し自体が失敗することもある（壊れたxref等）ため、取り出しと
    caption_image呼び出しの両方を同じtryに含める。scripts/ingest_source.pyが
    1ファイルの失敗で全体を止めないのと同じ理由で、1枚の画像の失敗が他の画像・
    本文を道連れにしないようにする。
    """
    captions = []
    for xref, _smask, width, height, *_rest in page.get_images(full=True):
        if width < MIN_IMAGE_WIDTH or height < MIN_IMAGE_HEIGHT:
            continue
        try:
            image_bytes = doc.extract_image(xref)["image"]
            caption = caption_image(image_bytes)
        except Exception as error:
            print(
                f"警告: 画像の説明取得に失敗しました（{source_name} p.{page_number}）: {error}",
                file=sys.stderr,
            )
            continue
        if caption.strip() and caption.strip() != "装飾画像":
            captions.append(caption)
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
            needs_ocr = len(text) < OCR_MIN_CHARS
            used_ocr = False
            used_vlm = False

            captions = (
                _describe_images(doc, page, number, path.name, caption_image)
                if caption_image is not None
                else []
            )

            if needs_ocr:
                if captions:
                    # スキャンページはVLMの説明文で置き換える。OCRは誤認識が
                    # 残るため（README「既知の制約」参照）、VLMが使える場合は
                    # そちらを優先する。1枚も説明文が得られなかった場合のみ
                    # OCRへフォールバックし、ページの中身が消えるのを避ける。
                    text = "\n\n".join(f"[図の説明] {caption}" for caption in captions)
                    used_vlm = True
                else:
                    text = ocr_page(page).strip()
                    used_ocr = True
            elif captions:
                for caption in captions:
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
