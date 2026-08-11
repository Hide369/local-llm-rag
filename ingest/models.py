"""取り込みパイプライン全体で共有するデータ構造。

各パーサーはPDF・PPTX・DOCXの違いをすべて ParsedUnit に吸収する。
これにより後続のチャンク分割・埋め込み・保存は元の形式を知る必要がない。
"""
from dataclasses import dataclass, field

# 出典位置の種別。docxのようにページ概念を持たない形式は "document" を使う。
PAGE = "page"
SLIDE = "slide"
DOCUMENT = "document"

_LABEL_FORMATS = {PAGE: "p.{}", SLIDE: "スライド{}"}


@dataclass(frozen=True)
class ParsedUnit:
    """パーサーが返す最小単位。1ページ、1スライド、または文書全体。"""

    text: str
    location_type: str
    location: int
    ocr: bool = False

    @property
    def label(self) -> str:
        """出典表示に使う位置ラベル。位置概念がない形式では空文字を返す。"""
        fmt = _LABEL_FORMATS.get(self.location_type)
        return fmt.format(self.location) if fmt else ""


@dataclass(frozen=True)
class Chunk:
    """ベクトルDBに保存する単位。"""

    id: str
    text: str
    metadata: dict = field(default_factory=dict)
