"""プレーンテキストの抽出。

txtには見出しもページも無く、書き手が引いた境界の手がかりが存在しない。
推測で段落を切ると資料ごとに切れ方が変わるため、文書全体を1ユニットにし、
分割はCHUNK_SIZEを持つ chunk_units に一任する。docxを1ユニットにしているのと
同じ理由である。

ソースコードと設定ファイル（.go .cs .sh .json .bat .yaml .yml .mod .sum）も
同じ理由でここへ振り分けている（ingest/parsers/__init__.py）。

この形式の難しさは中身ではなく文字コードにあり、その判定は
ingest/parsers/text_file.py が持つ（HTMLと共有するため）。
"""
from pathlib import Path

from ingest.models import DOCUMENT, ParsedUnit
from ingest.parsers.text_file import read_text_file


def parse_txt(path: Path, caption_image=None, on_missing_image=None) -> list[ParsedUnit]:
    text = read_text_file(path).strip()
    if not text:
        return []
    return [ParsedUnit(text=text, location_type=DOCUMENT, location=0)]
