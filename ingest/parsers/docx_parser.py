"""Word文書のテキスト抽出。

docxにはページの概念が（レンダリングするまで）存在しないため、
文書全体を1つのユニットとして扱う。
"""
from pathlib import Path

from docx import Document

from ingest.models import DOCUMENT, ParsedUnit


def parse_docx(path: Path) -> list[ParsedUnit]:
    text = "\n".join(p.text for p in Document(path).paragraphs if p.text.strip())
    if not text.strip():
        return []
    return [ParsedUnit(text=text, location_type=DOCUMENT, location=0)]
