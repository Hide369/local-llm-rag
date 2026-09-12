"""拡張子に応じて適切なパーサーへ振り分ける。

新しい形式に対応するときは、パーサーを1つ書いて _PARSERS に登録するだけでよい。
そのために全パーサーの署名を揃えてある。使わない引数を受け取るパーサーが
あるが、使う側だけに足すとこのディスパッチャが拡張子を見て引数を出し分ける
ことになり、形式を足すたびに分岐が伸びる（設計書12節）。
"""
from pathlib import Path

from ingest.models import ParsedUnit
from ingest.parsers.docx_parser import parse_docx
from ingest.parsers.drawio_parser import parse_drawio
from ingest.parsers.image_parser import parse_image
from ingest.parsers.md_parser import parse_md
from ingest.parsers.pdf_parser import parse_pdf
from ingest.parsers.pptx_parser import parse_pptx
from ingest.parsers.txt_parser import parse_txt
from ingest.parsers.xlsx_parser import parse_xlsx


class UnsupportedFormatError(Exception):
    """取り込み対象外の拡張子を渡された。"""


_PARSERS = {
    ".pdf": parse_pdf,
    ".docx": parse_docx,
    ".pptx": parse_pptx,
    ".md": parse_md,
    ".txt": parse_txt,
    ".xlsx": parse_xlsx,
    ".png": parse_image,
    ".jpg": parse_image,
    ".jpeg": parse_image,
    ".drawio": parse_drawio,
}

SUPPORTED_SUFFIXES = set(_PARSERS)


def parse(path: Path, caption_image=None, on_missing_image=None) -> list[ParsedUnit]:
    parser = _PARSERS.get(path.suffix.lower())
    if parser is None:
        raise UnsupportedFormatError(f"未対応の形式です: {path.name}")
    return parser(path, caption_image=caption_image, on_missing_image=on_missing_image)
