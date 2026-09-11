"""画像ファイル単体のテキスト化。

1ファイル=1ユニットにする。画像1枚には見出しもページも無く、書き手が引いた
境界の手がかりが存在しないためで、txt_parser が文書全体を1ユニットにしているのと
同じ判断である。

.drawio.png のようにXMLを埋め込んだPNGもここへ来る。埋め込みXMLの取り出しは
行わず、画像として読む（設計書15節）。
"""
from pathlib import Path

from ingest.image_text import describe_image, has_caption, has_ocr
from ingest.models import DOCUMENT, ParsedUnit


def parse_image(path: Path, caption_image=None, on_missing_image=None, ocr_bytes=None) -> list[ParsedUnit]:
    """画像1枚をユニットにする。読めなければ空リストを返す。

    ocr_bytes はテストで差し替えるための引数である（pdf_parser の ocr_page と
    同じ形）。省略時は describe_image が ingest.ocr を遅延importする。

    on_missing_image は受け取るが使わない。全パーサーの署名を揃えるためである
    （設計書12節）。
    """
    text = describe_image(
        path.read_bytes(), caption_image, ocr_bytes=ocr_bytes, label=path.name
    )
    if text is None:
        # 読めなかった画像はユニットを作らない。空チャンクがDBに入ると
        # どの質問にも弱く一致する(xlsx_parser が空シートを飛ばすのと同じ)。
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
