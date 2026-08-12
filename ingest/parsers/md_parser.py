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
    """CRLFを正規化して行に分ける。

    実データ30件はすべてCRLFであり、そのままだと見出し文字列の末尾に \r が残って
    出典が「＞ 設置情報\r」のように壊れる。encoding を省略しないのは、Windowsの
    既定が CP932 で日本語の読み込みに必ず失敗するため。
    """
    text = path.read_text(encoding="utf-8")
    return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")


def _drop_frontmatter(lines: list[str]) -> list[str]:
    """先頭のYAMLフロントマターを取り除く。

    model_id と product_name はH1前置で全ユニットに行き渡り、その他の属性は
    本文の散文が保持している。YAMLの生テキストを埋め込むより散文のほうが
    日本語の質問との類似度が出るため、索引には入れない。
    """
    if not lines or lines[0].strip() != "---":
        return lines
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return lines[index + 1 :]
    return lines  # 閉じられていないなら本文とみなす


def parse_md(path: Path) -> list[ParsedUnit]:
    title = ""
    sections: list[tuple[str, list[str]]] = []
    heading: str = ""
    body: list[str] = []
    in_fence = False

    for line in _drop_frontmatter(_read_lines(path)):
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
            )
        )
    return units
