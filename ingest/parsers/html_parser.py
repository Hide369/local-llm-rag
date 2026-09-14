"""HTMLのテキスト抽出。

本文はタグの隙間にしかない。生のまま取り込むと検索語がマークアップに埋もれ、
script や style の中身まで埋め込まれてベクトルが本文から引き離される。

ユニットの切り方は txt と同じく文書全体で1つにする。HTMLの見出し(h1-h6)は
Markdownの `##` と違って入れ子の深さも使われ方も資料ごとにばらばらで、
書き手が引いた話題の境界として当てにできないためである。分割は CHUNK_SIZE を
持つ chunk_units に一任する。

標準ライブラリの html.parser だけで書いている。lxml が（python-docx 等の推移的な
依存として）入ってはいるが、requirements.txt は直接importするものだけを固定する
方針であり、この程度の抽出のために依存を1つ増やす理由がない。

**既知の制約**: `<pre>` の字下げは保たれない。HTMLでは空白が意味を持たないため
一律に畳んでおり、貼り付けられたコード例は字下げを失う。
"""
import re
from html.parser import HTMLParser
from pathlib import Path

from ingest.models import DOCUMENT, ParsedUnit
from ingest.parsers.text_file import read_text_file

# 中身を本文として扱わないタグ。JSとCSSは資料の中身ではない。
_SKIP_TAGS = frozenset({"script", "style"})

# 境目で改行を入れるタグ。入れないと別の段落の語がつながって1語になり
# （'第1条' と '第2条' が '第1条第2条' になる）、どちらの語でも引けなくなる。
_BLOCK_TAGS = frozenset(
    {
        "address", "article", "aside", "blockquote", "br", "caption", "dd",
        "div", "dl", "dt", "fieldset", "figcaption", "figure", "footer", "form",
        "h1", "h2", "h3", "h4", "h5", "h6", "header", "hr", "li", "main", "nav",
        "ol", "p", "pre", "section", "table", "tbody", "tfoot", "thead", "ul",
    }
)

# 表のセルは改行ではなく ` | ` でつなぎ、行の終わりで改行する。セルを1行ずつ
# 並べると見出し行との対応が復元できなくなるためで、xlsx_parser._row_text() と
# 同じ判断である。
_CELL_TAGS = frozenset({"td", "th"})
_CELL_MARK = "|"
_CELL_SEPARATOR = f" {_CELL_MARK} "

_BLANK_LINES = re.compile(r"\n{3,}")
_INLINE_SPACES = re.compile(r"[ \t]+")


class _TextExtractor(HTMLParser):
    """本文を集める。タグは構造の手がかりとしてだけ使い、出力には残さない。"""

    def __init__(self) -> None:
        # convert_charrefs=True で &amp; や &nbsp; が復号される。復号しないと
        # 記号を含む語がその形のまま埋め込まれ、本文の表記では引けなくなる。
        super().__init__(convert_charrefs=True)
        self.title = ""
        self._parts: list[str] = []
        self._skip_depth = 0
        self._in_title = False

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
        elif tag == "title":
            self._in_title = True
        elif tag in _BLOCK_TAGS:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS:
            # 閉じが無いまま終わる壊れたHTMLで負にしないための max。
            self._skip_depth = max(0, self._skip_depth - 1)
        elif tag == "title":
            self._in_title = False
        elif tag in _CELL_TAGS:
            self._parts.append(_CELL_SEPARATOR)
        elif tag == "tr":
            self._parts.append("\n")
        elif tag in _BLOCK_TAGS:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._in_title:
            self.title += data
            return
        if not data.strip():
            # 整形のための字下げと改行。HTMLでは空白に意味が無いので、語の
            # 区切りとしてだけ残す。そのまま通すとタグの境目ごとに空行が生まれ、
            # 表の行が1行おきになり、CHUNK_SIZE(800字)を空白で食いつぶす。
            # 本当の改行はブロック要素の境目（handle_starttag / handle_endtag）
            # から入るので、ここで落としても段落は潰れない。
            self._parts.append(" ")
            return
        self._parts.append(data)

    def text(self) -> str:
        return "".join(self._parts)


def _tidy(text: str) -> str:
    """HTMLでは空白に意味が無いので畳む。字下げやタグ間の改行がそのまま残ると、
    本文より空白のほうが多いチャンクができる。"""
    # NBSP は見た目が空白なのに別の文字であり、残すと語の区切りとして働かない。
    text = text.replace("\xa0", " ")
    lines = []
    for line in text.split("\n"):
        line = _INLINE_SPACES.sub(" ", line).strip()
        # 行頭と行末のセル区切りを落とす。最後のセルの後ろにも区切りを
        # 付けているため、そのままだと表の全行が ' | ' で終わる。中身の
        # 無いセルだけが並んだ行（'| |' など）はこれで空行になり、下で畳まれる。
        lines.append(line.strip(_CELL_MARK).strip())
    return _BLANK_LINES.sub("\n\n", "\n".join(lines)).strip()


def parse_html(path: Path, caption_image=None, on_missing_image=None) -> list[ParsedUnit]:
    extractor = _TextExtractor()
    extractor.feed(read_text_file(path))
    extractor.close()

    body = _tidy(extractor.text())
    if not body:
        # タイトルだけの資料は中身が無い。ユニットを作ると空のチャンクが残る。
        return []

    # タイトルを1行目に残すのは、本文の断片だけが検索に当たったときに何の資料か
    # 分からなくなるのを防ぐためである（md_parser が各ユニットの先頭にH1を付ける
    # のと同じ狙い）。
    title = _tidy(extractor.title)
    text = f"{title}\n{body}" if title else body
    return [ParsedUnit(text=text, location_type=DOCUMENT, location=0)]
