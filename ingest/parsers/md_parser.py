"""Markdownのテキスト抽出。

`##` 見出しは書き手が引いた話題の境界そのものなので、PPTXのスライドと同じく
1見出し=1ユニットとする。source/家電製品/ の30件を実測したところ、セクションは
最小76字・中央値157字・最大448字であり、CHUNK_SIZE(800)を超えないため
再分割は一度も起きない。

各ユニットの先頭にはH1（例 'UD-0900i IoTコンパクト'）を1行付ける。
'## 設置情報' だけを検索で引いたときに、どの製品の設置情報なのか分からなく
なるのを防ぐためで、これがこの形式を扱ううえでの要になる。
"""
from pathlib import Path

from ingest.models import SECTION, ParsedUnit

_FENCE = "```"


def _read_lines(path: Path) -> list[str]:
    r"""CRLFを正規化して行に分ける。

    実データ30件はすべてCRLFであり、そのままだと見出し文字列の末尾に \r が残って
    出典が「＞ 設置情報\r」のように壊れる。encoding を省略しないのは、Windowsの
    既定が CP932 で日本語の読み込みに必ず失敗するため。

    utf-8 ではなく utf-8-sig を使うのは、BOM付きファイルだとBOM文字（U+FEFF）が
    先頭行の '---' にくっつき、_split_frontmatter が先頭のフロントマター境界を
    認識できず、フロントマターの生のYAMLがそのまま索引されてしまうため。
    BOMなしのファイルはutf-8-sigでも同じ結果になるので、常にこちらを使ってよい。
    """
    text = path.read_text(encoding="utf-8-sig")
    return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")


def _scalar(value: str):
    """YAMLのスカラー値をPythonの型に直す。採用しない値には None を返す。

    数値に見えるものを int / float にするのは、ChromaDB の where が
    数値比較をするため。文字列のまま入れると $lte が黙って効かなくなる。
    """
    text = value.strip()
    if not text or text.startswith("["):
        return None  # 配列は where が部分一致を扱えず、実用にならない
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return text


def _parse_attributes(lines: list[str]) -> dict:
    """`key: value` の平らな行だけを拾う。

    字下げされた行は入れ子の属性であり、平らなメタデータには載せられないので飛ばす。
    """
    attributes: dict = {}
    for line in lines:
        if line[:1].isspace():
            continue
        key, separator, value = line.partition(":")
        if not separator:
            continue
        scalar = _scalar(value)
        if key.strip() and scalar is not None:
            attributes[key.strip()] = scalar
    return attributes


def _split_frontmatter(lines: list[str]) -> tuple[dict, list[str]]:
    """先頭のYAMLフロントマターを属性として取り出し、本文と分けて返す。

    フロントマターを埋め込みテキストに入れない判断は当初から変えていない。
    YAMLの生テキストより散文のほうが日本語の質問との類似度が出るためである。
    変えたのは「捨てる」ことのほうで、noise_wash_db は30製品中24製品で本文に
    一度も現れず、捨てると索引から永久に失われることが実測で分かった。
    """
    if not lines or lines[0].strip() != "---":
        return {}, lines
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return _parse_attributes(lines[1:index]), lines[index + 1 :]
    return {}, lines  # 閉じられていないなら本文とみなす


def parse_md(path: Path) -> list[ParsedUnit]:
    attributes, body_lines = _split_frontmatter(_read_lines(path))
    title = ""
    sections: list[tuple[str, list[str]]] = []
    heading: str = ""
    body: list[str] = []
    in_fence = False

    for line in body_lines:
        if line.startswith(_FENCE):
            in_fence = not in_fence
        elif not in_fence:
            if line.startswith("## "):
                sections.append((heading, body))
                heading, body = line[3:].strip(), []
                continue
            if not title and line.startswith("# "):
                title = line[2:].strip()
                continue
        body.append(line)
    sections.append((heading, body))

    units: list[ParsedUnit] = []
    for section_heading, section_body in sections:
        text = "\n".join(section_body).strip()
        if not text:
            continue
        units.append(
            ParsedUnit(
                text="\n".join(part for part in (title, section_heading, text) if part),
                location_type=SECTION,
                # 見出し文字列ではなく通し番号を位置にする。同じ見出しが2つある文書で
                # チャンクIDが衝突するのを防ぐため、IDの一意性を文書構造に依存させない。
                location=len(units) + 1,
                heading=section_heading,
                attributes=attributes,
            )
        )
    return units
