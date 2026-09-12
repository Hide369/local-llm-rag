"""draw.io の図の取り込み。

.drawio は mxGraph の XML であり、図形のラベル文字が構造化されたまま
ファイルの中にある。画像化してOCRにかけるのは、手元にある正解を捨てて
推測し直すのと同じで、誤認識を新たに持ち込むことになる。
"""
import base64
import urllib.parse
import zlib

import pytest

from ingest.models import DIAGRAM
from ingest.parsers import SUPPORTED_SUFFIXES, parse
from ingest.parsers.drawio_parser import parse_drawio

_MODEL = (
    '<mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/>'
    '<mxCell id="2" value="&lt;b&gt;受注&lt;/b&gt;&lt;br&gt;登録" vertex="1" parent="1">'
    '<mxGeometry x="40" y="200" width="120" height="60"/></mxCell>'
    '<mxCell id="3" value="在庫引当" vertex="1" parent="1">'
    '<mxGeometry x="40" y="40" width="120" height="60"/></mxCell>'
    '<object label="承認" id="4"><mxCell vertex="1" parent="1">'
    '<mxGeometry x="300" y="40" width="120" height="60"/></mxCell></object>'
    "</root></mxGraphModel>"
)


def _pack(xml):
    """draw.io の既定の格納形式: URLエンコード → raw deflate → base64。"""
    return base64.b64encode(
        zlib.compress(urllib.parse.quote(xml, safe="").encode())[2:-4]
    ).decode()


@pytest.fixture
def compressed_path(tmp_path):
    path = tmp_path / "構成図.drawio"
    path.write_text(
        f'<mxfile><diagram name="業務フロー" id="a">{_pack(_MODEL)}</diagram></mxfile>',
        encoding="utf-8",
    )
    return path


@pytest.fixture
def plain_path(tmp_path):
    """draw.io は設定で圧縮を切れる。両方を受けないと片方が丸ごと落ちる。"""
    path = tmp_path / "非圧縮.drawio"
    path.write_text(
        f'<mxfile><diagram name="業務フロー" id="a">{_MODEL}</diagram></mxfile>',
        encoding="utf-8",
    )
    return path


def test_a_compressed_diagram_is_read(compressed_path):
    assert "在庫引当" in parse_drawio(compressed_path)[0].text


def test_an_uncompressed_diagram_is_read(plain_path):
    assert "在庫引当" in parse_drawio(plain_path)[0].text


def test_each_page_becomes_one_unit(tmp_path):
    """ページは書き手が引いた区切りそのものである。PDFのページと同じ扱いにする。"""
    path = tmp_path / "二枚.drawio"
    path.write_text(
        f'<mxfile><diagram name="一枚目" id="a">{_pack(_MODEL)}</diagram>'
        f'<diagram name="二枚目" id="b">{_pack(_MODEL)}</diagram></mxfile>',
        encoding="utf-8",
    )

    units = parse_drawio(path)

    assert len(units) == 2
    assert [unit.location_type for unit in units] == [DIAGRAM, DIAGRAM]
    assert [unit.location for unit in units] == [1, 2]
    assert [unit.heading for unit in units] == ["一枚目", "二枚目"]


def test_labels_are_ordered_top_to_bottom_then_left_to_right(compressed_path):
    """XML上の並びは作成順であり、図を読む順とは一致しない。"""
    text = parse_drawio(compressed_path)[0].text

    assert text.index("在庫引当") < text.index("承認")
    assert text.index("承認") < text.index("受注")


def test_object_labels_are_collected_too(compressed_path):
    """カスタムプロパティ付きの図形は object/@label を使う。
    片方だけを見ると図の半分が黙って消える。
    """
    assert "承認" in parse_drawio(compressed_path)[0].text


def test_html_in_a_label_is_stripped(compressed_path):
    """タグを残すと索引にも入り、Streamlitの画面にも文字として出る。"""
    text = parse_drawio(compressed_path)[0].text

    assert "<b>" not in text
    assert "受注 登録" in text


def test_the_page_name_leads_the_text(compressed_path):
    """ページ単体で引かれたとき何の図か分からなくなるのを防ぐ。
    md_parser がH1を、xlsx_parser がシート名を先頭に置くのと同じ。
    """
    assert parse_drawio(compressed_path)[0].text.startswith("業務フロー")


def test_an_edge_label_without_coordinates_sorts_after_vertices(tmp_path):
    """draw.io は辺にも必ず <mxGeometry relative="1" as="geometry"/> を書くが、
    x も y も持たない。それを (0, 0) 扱いにすると、辺のラベルがどの図形よりも
    先頭に来てしまう（実物のエクスポートで発生・要修正だった不具合）。
    XML上は辺を先頭に置き、座標に頼らず並べ替えられているかを確かめる。
    """
    model = (
        '<mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/>'
        '<mxCell id="5" value="次へ" edge="1" parent="1" source="2" target="3">'
        '<mxGeometry relative="1" as="geometry"/></mxCell>'
        '<mxCell id="2" value="受注" vertex="1" parent="1">'
        '<mxGeometry x="40" y="200" width="120" height="60"/></mxCell>'
        '<mxCell id="3" value="在庫引当" vertex="1" parent="1">'
        '<mxGeometry x="40" y="40" width="120" height="60"/></mxCell>'
        "</root></mxGraphModel>"
    )
    path = tmp_path / "辺.drawio"
    path.write_text(
        f'<mxfile><diagram name="ページ" id="a">{_pack(model)}</diagram></mxfile>',
        encoding="utf-8",
    )

    text = parse_drawio(path)[0].text

    assert text.index("在庫引当") < text.index("次へ")
    assert text.index("受注") < text.index("次へ")


def test_a_page_without_labels_produces_no_unit(tmp_path):
    path = tmp_path / "空.drawio"
    empty = '<mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/></root></mxGraphModel>'
    path.write_text(
        f'<mxfile><diagram name="空" id="a">{_pack(empty)}</diagram></mxfile>', encoding="utf-8"
    )

    assert parse_drawio(path) == []


def test_drawio_is_routed_by_the_registry(compressed_path):
    assert ".drawio" in SUPPORTED_SUFFIXES
    assert parse(compressed_path)[0].heading == "業務フロー"
