"""雛形の印を見つけて、値で埋める。

拡張子に応じて適切なモジュールへ振り分ける。形式を増やすときはモジュールを
1つ書いて _TEMPLATES に登録するだけでよい。そのために全モジュールの署名を
揃えてある（ingest/parsers/__init__.py と同じ方針）。

対象は docx / xlsx / pptx / md の4つだけである。PDF を入れていないのは、PDFが
文字を「位置」で持つ形式で、印より長い文字列を入れると溢れて重なるためである
（設計書2節に実測あり）。
"""
from pathlib import Path

from docgen.docx_template import fill as _fill_docx
from docgen.docx_template import placeholders as _placeholders_docx
from docgen.md_template import fill as _fill_md
from docgen.md_template import placeholders as _placeholders_md
from docgen.pptx_template import fill as _fill_pptx
from docgen.pptx_template import placeholders as _placeholders_pptx
from docgen.xlsx_template import fill as _fill_xlsx
from docgen.xlsx_template import placeholders as _placeholders_xlsx


class UnsupportedTemplateError(Exception):
    """雛形として扱えない拡張子を渡された。"""


_TEMPLATES = {
    ".md": (_placeholders_md, _fill_md),
    ".docx": (_placeholders_docx, _fill_docx),
    ".xlsx": (_placeholders_xlsx, _fill_xlsx),
    ".pptx": (_placeholders_pptx, _fill_pptx),
}

SUPPORTED_SUFFIXES = {".docx", ".xlsx", ".pptx", ".md"}


def _module(path: Path):
    found = _TEMPLATES.get(path.suffix.lower())
    if found is None:
        raise UnsupportedTemplateError(f"雛形として使えない形式です: {path.name}")
    return found


def placeholders(path: Path) -> list[str]:
    """雛形に含まれる印の名前を、出現順・重複なしで返す。"""
    return _module(path)[0](path)


def fill(path: Path, values: dict[str, str]) -> bytes:
    """印を値で埋めた結果をバイト列で返す。

    バイト列を返すのは st.download_button がそれを受け取るためで、中間ファイルを
    作らずに済む。
    """
    return _module(path)[1](path, values)
