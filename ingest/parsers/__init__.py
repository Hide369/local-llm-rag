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
from ingest.parsers.html_parser import parse_html
from ingest.parsers.image_parser import parse_image
from ingest.parsers.md_parser import parse_md
from ingest.parsers.pdf_parser import parse_pdf
from ingest.parsers.pptx_parser import parse_pptx
from ingest.parsers.txt_parser import parse_txt
from ingest.parsers.xlsx_parser import parse_xlsx


class UnsupportedFormatError(Exception):
    """取り込み対象外の拡張子を渡された。"""


# ソースコードと設定ファイルは txt と同じ扱いにする。専用のパーサーは作らない。
# どれもプレーンテキストであり、書き手が引いた見出しやページの境界を持たない
# ため、txt_parser の判断（文書全体で1ユニット、分割は chunk_units に一任）が
# そのまま当てはまる。文字コードの揺れも同じで、日本語Windowsで書かれた .bat は
# 現に cp932 である。
#
# .mod と .sum は拡張子だけでは形式が決まらない（Fortranのモジュール等でも使う）。
# ここで受けているのは go.mod / go.sum である。
#
# .py と .ps1 は後から足した。この一覧は当初「社内資料に混ざる形式」として
# 作ったため、このシステム自身が書かれている言語が漏れていた。実測 2026-09-15:
# Cowork でプロジェクトフォルダに ingest/ を指定すると走査結果が0件になり、
# 「取り込める形式のファイルがありません」で止まっていた（中身は全部 .py）。
# 用途が社内資料からソースコードへ広がった時点で、この一覧の前提も変わっている。
_CODE_SUFFIXES = (
    ".go",
    ".cs",
    ".sh",
    ".py",
    ".ps1",
    ".ts",
    ".tsx",
    ".js",
    ".vue",
    ".json",
    ".bat",
    ".yaml",
    ".yml",
    ".mod",
    ".sum",
)

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
    ".html": parse_html,
    ".htm": parse_html,
    **{suffix: parse_txt for suffix in _CODE_SUFFIXES},
}

SUPPORTED_SUFFIXES = set(_PARSERS)


def parse(path: Path, caption_image=None, on_missing_image=None) -> list[ParsedUnit]:
    parser = _PARSERS.get(path.suffix.lower())
    if parser is None:
        raise UnsupportedFormatError(f"未対応の形式です: {path.name}")
    return parser(path, caption_image=caption_image, on_missing_image=on_missing_image)
