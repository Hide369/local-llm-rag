"""拡張子に応じて適切なパーサーへ振り分ける。

新しい形式に対応するときは、パーサーを1つ書いて _PARSERS に登録するだけでよい。
"""
from pathlib import Path

from ingest.models import ParsedUnit
from ingest.parsers.docx_parser import parse_docx
from ingest.parsers.md_parser import parse_md
from ingest.parsers.pdf_parser import parse_pdf
from ingest.parsers.pptx_parser import parse_pptx


class UnsupportedFormatError(Exception):
    """取り込み対象外の拡張子を渡された。"""


_PARSERS = {
    ".pdf": parse_pdf,
    ".docx": parse_docx,
    ".pptx": parse_pptx,
    ".md": parse_md,
}

SUPPORTED_SUFFIXES = set(_PARSERS)


def parse(path: Path) -> list[ParsedUnit]:
    parser = _PARSERS.get(path.suffix.lower())
    if parser is None:
        raise UnsupportedFormatError(f"未対応の形式です: {path.name}")
    return parser(path)
