"""プレーンテキストの抽出。

txtには見出しもページも無く、書き手が引いた境界の手がかりが存在しない。
推測で段落を切ると資料ごとに切れ方が変わるため、文書全体を1ユニットにし、
分割はCHUNK_SIZEを持つ chunk_units に一任する。docxを1ユニットにしているのと
同じ理由である。

この形式の難しさは中身ではなく文字コードにある。
"""
from pathlib import Path

from ingest.models import DOCUMENT, ParsedUnit

# utf-8-sig を先に試すのは、BOM付きでもBOM無しでも正しく読めるためである
# （ingest/parsers/md_parser.py と同じ判断）。BOMを残すとU+FEFFが先頭語に
# くっつき、その語で永久に引けなくなる。
#
# cp932 を後ろに置くのは、Windowsのメモ帳が長らく既定でこれを使っており、
# 社内資料に現に混ざるためである。utf-8 だけで決め打つと UnicodeDecodeError
# になり、その資料は「取り込み失敗」として丸ごと落ちる。
#
# 逆順にはできない。cp932 はほぼ任意のバイト列を（無意味な文字列としてでも）
# 復号してしまうため、先に試すとUTF-8の資料が文字化けしたまま通ってしまう。
_ENCODINGS = ("utf-8-sig", "cp932")


def _read(path: Path) -> str:
    last_error: UnicodeDecodeError | None = None
    for encoding in _ENCODINGS:
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError as error:
            last_error = error
    raise ValueError(
        f"文字コードを判別できません（{' / '.join(_ENCODINGS)} で失敗）: {path.name}"
    ) from last_error


def parse_txt(path: Path, caption_image=None, on_missing_image=None) -> list[ParsedUnit]:
    text = _read(path).replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return []
    return [ParsedUnit(text=text, location_type=DOCUMENT, location=0)]
