"""取り込みパイプライン全体で共有するデータ構造。

各パーサーはPDF・PPTX・DOCX・Markdownの違いをすべて ParsedUnit に吸収する。
これにより後続のチャンク分割・埋め込み・保存は元の形式を知る必要がない。
"""
from dataclasses import dataclass, field

# 出典位置の種別。docxのようにページ概念を持たない形式は "document" を使う。
PAGE = "page"
SLIDE = "slide"
DOCUMENT = "document"
SECTION = "section"


@dataclass(frozen=True)
class ParsedUnit:
    """パーサーが返す最小単位。1ページ、1スライド、1見出し、または文書全体。"""

    text: str
    location_type: str
    location: int
    ocr: bool = False
    # PDF/PPTXに埋め込まれた図表・写真をVLMで説明文化し、本文へ追記したかどうか。
    vlm: bool = False
    # Markdownの見出し文字列。出典を「ファイル名 ＞ 設置情報」と表示するために運ぶ。
    # 位置の一意性は location（通し番号）が持ち、heading は表示専用である。
    heading: str = ""
    # Markdownのフロントマター由来の属性。埋め込みテキストには入れず、
    # メタデータとしてのみ運ぶ。ベクトルは「510以下」のような数値条件を
    # 表現できないため、絞り込みは where に任せる必要がある。
    attributes: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Chunk:
    """ベクトルDBに保存する単位。"""

    id: str
    text: str
    metadata: dict = field(default_factory=dict)
