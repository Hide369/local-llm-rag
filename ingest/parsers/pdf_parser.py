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

from ingest.image_text import describe_image, has_caption, has_ocr
from ingest.models import PAGE, ParsedUnit

OCR_MIN_CHARS = 30

# ロゴ・アイコン等の装飾画像を除外するための閾値（px角）。実データでの実測は
# design docの5節を参照。未実測の仮値であり、後日調整する前提。
MIN_IMAGE_WIDTH = 150
MIN_IMAGE_HEIGHT = 150


def _describe_images(doc, page, page_number: int, source_name: str, caption_image, ocr_bytes) -> list[str]:
    """ページに埋め込まれた図・写真を説明文と文字にする。1枚失敗しても残りは続ける。

    画像の取り出し自体が失敗することもある（壊れたxref等）ため、取り出しは
    ここで握る。caption_image / ocr_bytes 側の失敗は describe_image が
    別々に握っており、片方が落ちてももう片方の結果は残る。
    """
    blocks = []
    for xref, _smask, width, height, *_rest in page.get_images(full=True):
        if width < MIN_IMAGE_WIDTH or height < MIN_IMAGE_HEIGHT:
            continue
        try:
            image_bytes = doc.extract_image(xref)["image"]
        except Exception as error:
            print(
                f"警告: 画像を取り出せませんでした（{source_name} p.{page_number}）: {error}",
                file=sys.stderr,
            )
            continue
        text = describe_image(
            image_bytes, caption_image, ocr_bytes=ocr_bytes, label=f"{source_name} p.{page_number}"
        )
        if text:
            blocks.append(text)
    return blocks


def parse_pdf(
    path: Path, caption_image=None, on_missing_image=None, ocr_page=None, ocr_bytes=None
) -> list[ParsedUnit]:
    """PDFを1ページ1ユニットで読む。

    ocr_page/caption_image はテストで差し替えられるよう引数にしている。
    caption_image・ocr_bytes をどちらも省略した場合（既定）は画像の
    説明文化を一切行わない。
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
                _describe_images(doc, page, number, path.name, caption_image, ocr_bytes)
                if caption_image is not None or ocr_bytes is not None
                else []
            )

            if needs_ocr:
                if captions:
                    # スキャンページは埋め込み画像の説明で置き換える。OCRは誤認識が
                    # 残るため（README「既知の制約」参照）、VLMが使える場合は
                    # そちらを優先する。1枚も説明文が得られなかった場合のみ
                    # OCRへフォールバックし、ページの中身が消えるのを避ける。
                    text = "\n\n".join(captions)
                    used_vlm = has_caption(text)
                    used_ocr = has_ocr(text)
                else:
                    text = ocr_page(page).strip()
                    used_ocr = True
            elif captions:
                for block in captions:
                    text = f"{text}\n\n{block}".strip()
                used_vlm = has_caption(text)
                used_ocr = has_ocr(text)

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
