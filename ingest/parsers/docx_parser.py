"""Word文書のテキスト抽出。

docxにはページの概念が（レンダリングするまで）存在しないため、
文書全体を1つのユニットとして扱う。

1ユニットにまとめる以上、埋め込み画像を本文のどの位置へ入れるかがそのまま
読みやすさになる。段落を走査し、その段落に画像があればその場に差し込む。
"""
from pathlib import Path

from docx import Document

from ingest.image_text import describe_image, has_caption, has_ocr
from ingest.models import DOCUMENT, ParsedUnit


def _paragraph_image_ids(paragraph) -> list[str]:
    """段落に埋め込まれた画像の関係ID。読み順で返る。

    ._p は python-docx の私的属性である。公開APIに段落中の画像を辿る口が
    無い。xlsx_parser の ws._images と同じ扱いで、requirements.txt で
    バージョンを固定していることと、テストが画像1枚を検出することをもって
    受け入れる。
    """
    return list(paragraph._p.xpath(".//a:blip/@r:embed"))


def _image_parts(document) -> dict:
    """関係ID → 画像パート。本文に紐づかない画像を拾うためにも使う。"""
    return {
        rid: part
        for rid, part in document.part.related_parts.items()
        if part.content_type.startswith("image/")
    }


def parse_docx(path: Path, caption_image=None, on_missing_image=None, ocr_bytes=None) -> list[ParsedUnit]:
    """文書全体を1ユニットにする。on_missing_image は使わない（署名を揃えるため）。

    ocr_bytes はテストで差し替えるための引数である（pdf_parser の ocr_page と
    同じ形）。省略時は describe_image が ingest.ocr を遅延importする。
    """
    document = Document(path)
    parts = _image_parts(document)
    # 画像を読む手立てが1つも無いなら、走査もしない。従来どおり段落だけを読む。
    read_images = bool(parts) and (caption_image is not None or ocr_bytes is not None)

    blocks: list[str] = []
    seen: set[str] = set()
    for paragraph in document.paragraphs:
        if paragraph.text.strip():
            blocks.append(paragraph.text)
        if not read_images:
            continue
        for rid in _paragraph_image_ids(paragraph):
            part = parts.get(rid)
            if part is None or rid in seen:
                continue
            seen.add(rid)
            described = describe_image(
                part.blob, caption_image, ocr_bytes=ocr_bytes, label=path.name
            )
            if described:
                blocks.append(described)

    # 表のセル・浮動配置の画像は document.paragraphs に現れない（実測で確認済み）。
    # 段落を辿るだけでは黙って落ちるため、残りを末尾に付ける。表の中まで辿る
    # 実装より短く、取りこぼしを構造的に無くせる。位置は失うが、失うのは
    # 本文のどこにも紐づかない画像だけである。
    # なおヘッダー・フッターの画像はここでは拾えない（README「既知の制約」参照）。
    # それらはヘッダー/フッターパート配下にあり、document.part.related_parts に
    # 現れるのはヘッダー/フッターパートそのものであって、画像はさらにその先の
    # related_parts にある。_image_parts() が見ているのは document.part 直下
    # なので、たどり着けない。
    if read_images:
        for rid, part in parts.items():
            if rid in seen:
                continue
            described = describe_image(
                part.blob, caption_image, ocr_bytes=ocr_bytes, label=path.name
            )
            if described:
                blocks.append(described)

    text = "\n".join(blocks)
    if not text.strip():
        return []
    return [
        ParsedUnit(
            text=text,
            location_type=DOCUMENT,
            location=0,
            ocr=has_ocr(text),
            vlm=has_caption(text),
        )
    ]
