"""PowerPointのテキスト抽出。

スライドは話題の区切りそのものなので、1スライド=1ユニットとする。
"""
from pathlib import Path

from pptx import Presentation

from ingest.models import SLIDE, ParsedUnit


def _slide_text(slide) -> str:
    parts = [
        shape.text_frame.text for shape in slide.shapes if shape.has_text_frame
    ]
    # ノート欄には本文に書かれていない補足や発表意図が入るため取り込む。
    if slide.has_notes_slide:
        parts.append(slide.notes_slide.notes_text_frame.text)
    return "\n".join(part for part in parts if part.strip())


def parse_pptx(path: Path) -> list[ParsedUnit]:
    units = []
    for number, slide in enumerate(Presentation(path).slides, start=1):
        text = _slide_text(slide)
        if text.strip():
            units.append(ParsedUnit(text=text, location_type=SLIDE, location=number))
    return units
