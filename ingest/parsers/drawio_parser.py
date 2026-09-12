"""draw.io の図のテキスト抽出。

design: docs/superpowers/specs/2026-09-11-image-ingestion-design.md 7節

この形式だけは describe_image を通らない。.drawio は mxGraph の XML であり、
図形のラベル文字が構造化されたままファイルの中にある。画像化してOCRにかけるのは、
手元にある正解を捨てて推測し直すのと同じである。加えて画像化には draw.io
デスクトップ版のCLIが要り、サーバー環境へ外部バイナリを1つ増やすことになる。

失うのは図の見た目の説明だけである。矢印の向きや囲みの入れ子は取れない。
"""
import base64
import binascii
import re
import sys
import urllib.parse
import zlib
from pathlib import Path
from xml.etree import ElementTree

from ingest.models import DIAGRAM, ParsedUnit

# ラベルにはHTMLが入る（実測: '<b>受注</b><br>登録'）。落とさないとタグの文字列が
# そのまま索引され、StreamlitのMarkdownにも文字として出る（answer_text が
# 回答側で同じ問題を扱っている）。
_TAG = re.compile(r"<[^>]+>")

# 座標を持たない要素（辺のラベル等）を末尾へ送るための番兵。
_NO_POSITION = float("inf")

# 展開後サイズの上限（zip bomb対策）。.drawio はアップロード可能な形式であり、
# 数KBのファイルが圧縮率次第で数GBに膨らみうる。md_parser._resolve が資料の
# 中身をファイルシステムへ渡す前に防御しているのと同じ考え方で、ここでは
# 展開そのものに歯止めをかける。実際の図はテキストラベルの羅列でしかなく
# 展開後も数百KB程度に収まるため、50MBは実運用のどんな図面より十分大きい。
_MAX_DECOMPRESSED_BYTES = 50 * 1024 * 1024


def _model_element(diagram):
    """<diagram> の中身を mxGraphModel 要素にする。

    draw.io の既定は base64(raw deflate(urlencode(XML))) をテキストとして
    <diagram> の中に持つが、設定で圧縮を切れる。切った場合の mxGraphModel は
    ファイル全体を読み込むときに ElementTree がすでに実の子要素として
    パース済みで、<diagram>.text には残らない（要素と地の文を分けるのは
    パーサの仕事であり、非圧縮時はここに元のXML文字列は現れない）。
    両方を受けないと、切ってある資料が丸ごと落ちる。

    zlib.decompress の -15 は raw deflate（zlibヘッダ無し）を指す。省くと必ず
    zlib.error になる。
    """
    children = list(diagram)
    if children:
        return children[0]
    text = (diagram.text or "").strip()
    if not text:
        return None
    decompressor = zlib.decompressobj(-15)
    raw = decompressor.decompress(base64.b64decode(text), _MAX_DECOMPRESSED_BYTES)
    if decompressor.unconsumed_tail:
        # 上限に達してもまだ展開しきれていない = zip bomb とみなして
        # このページを諦める。zlib.error に載せるのは、呼び出し元
        # (parse_drawio) が既に拾っている例外の型を増やさないため。
        raise zlib.error(
            f"展開後サイズが上限（{_MAX_DECOMPRESSED_BYTES}バイト）を超えました"
        )
    xml = urllib.parse.unquote(raw.decode("utf-8"))
    return ElementTree.fromstring(xml)


def _label(element) -> str:
    """図形のラベル文字。mxCell は value、object は label に持つ。

    片方だけを見ると、カスタムプロパティ付きの図形が黙って消える。
    """
    return element.get("value") or element.get("label") or ""


def _position(element):
    """読み順（行優先）で並べるための整列キー。

    XML上の並び順は作成順であり、図を読む順とは一致しない。pptx_parser が
    シェイプに対して抱えているのと同じ問題・同じ解き方である。
    """
    geometry = element.find("mxGeometry")
    if geometry is None:
        # object は mxGeometry を子の mxCell 側に持つ。
        cell = element.find("mxCell")
        geometry = cell.find("mxGeometry") if cell is not None else None
    if geometry is None:
        return (_NO_POSITION, _NO_POSITION)
    # 辺（矢印）は draw.io が必ず <mxGeometry relative="1" as="geometry"/> を
    # 書き出すため、要素そのものは常に見つかる。x も y も持たず、
    # geometry.get(..., 0) に頼ると (0, 0) — 座標を持つどの図形よりも前 —
    # に化けてしまう。座標が両方とも無いときだけ番兵を返す。片方だけ無い
    # 場合（droppable な相対配置ではない）は位置ありとして扱う。
    y, x = geometry.get("y"), geometry.get("x")
    if y is None and x is None:
        return (_NO_POSITION, _NO_POSITION)
    return (float(y or 0), float(x or 0))


def _clean(label: str) -> str:
    """HTMLを落とし、1行の文字列にする。<br> は空白にする。"""
    text = _TAG.sub(" ", label)
    return " ".join(text.split())


def _page_labels(model) -> list[str]:
    elements = [element for element in model.iter() if _label(element)]
    elements.sort(key=_position)
    return [text for text in (_clean(_label(element)) for element in elements) if text]


def parse_drawio(path: Path, caption_image=None, on_missing_image=None) -> list[ParsedUnit]:
    """1ページ=1ユニットで読む。caption_image / on_missing_image は使わない。"""
    root = ElementTree.fromstring(path.read_text(encoding="utf-8"))
    units: list[ParsedUnit] = []
    for diagram in root.iter("diagram"):
        name = diagram.get("name", "")
        try:
            model = _model_element(diagram)
            labels = _page_labels(model) if model is not None else []
        except (
            zlib.error,
            binascii.Error,
            ElementTree.ParseError,
            UnicodeDecodeError,
            ValueError,
        ) as error:
            # 1ページの失敗で他のページと他の資料を道連れにしない
            # （pdf_parser._describe_images と同じ方針）。ValueError は
            # _position() の float(y or 0) が非数値の座標に当たったときに出る。
            # これが漏れると、1ページの壊れた座標がファイル全体を落としていた。
            print(
                f"警告: 図を読めませんでした（{path.name} 図「{name}」）: {error}",
                file=sys.stderr,
            )
            continue
        if not labels:
            # ラベルが1つも無いページはユニットを作らない。空チャンクは
            # どの質問にも弱く一致する。
            continue
        units.append(
            ParsedUnit(
                # ページ名を本文の先頭に置く。ページ単体で引かれたとき何の図か
                # 分からなくなるのを防ぐためで、xlsx_parser がシート名を、
                # md_parser がH1を置いているのと同じ判断である。
                text="\n".join([name, *labels] if name else labels),
                location_type=DIAGRAM,
                # 通し番号にするのはページ名の重複でチャンクIDが衝突しない
                # ようにするため。表示には heading を使う。
                location=len(units) + 1,
                heading=name,
            )
        )
    return units
