"""Mermaid の値が図として入ること。

mmdc は呼ばない。docgen.mermaid.render を差し替えて PNG を返させる。
確かめるのは「画像が1つ増えること」と「描けなかったときに Mermaid の
テキストがそのまま残り、そのことが呼び出し元へ伝わること」である。
"""
import base64
import inspect
import io
import zipfile
from unittest.mock import patch

import docx
import openpyxl
import pytest
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.util import Inches

import docgen
from docgen import mermaid

DIAGRAM = "```mermaid\nsequenceDiagram\n  利用者->>画面: 生成を頼む\n```"

# 1x1 の PNG。python-docx も openpyxl も Pillow で実際に開くため、
# でたらめなバイト列では差し込めない。
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


@pytest.fixture
def drawn():
    with patch("docgen.mermaid.render", return_value=PNG) as render:
        yield render


@pytest.fixture
def undrawable():
    error = mermaid.MermaidError("mmdc が見つかりません")
    with patch("docgen.mermaid.render", side_effect=error):
        yield


def _word(tmp_path, text):
    path = tmp_path / "設計書.docx"
    document = docx.Document()
    document.add_paragraph(text)
    document.save(path)
    return path


def _slide_with(tmp_path, shapes_of):
    path = tmp_path / "設計書.pptx"
    presentation = Presentation()
    slide = presentation.slides.add_slide(presentation.slide_layouts[6])
    box = shapes_of(slide).add_textbox(Inches(1), Inches(2), Inches(4), Inches(1))
    box.text_frame.text = "{{シーケンス図}}"
    presentation.save(path)
    return path


def _all_text(shapes) -> str:
    found = []
    for shape in shapes:
        if shape.has_text_frame:
            found.append(shape.text_frame.text)
        if hasattr(shape, "shapes"):
            found.append(_all_text(shape.shapes))
    return "\n".join(found)


def test_word_gets_a_picture_instead_of_the_mark(tmp_path, drawn):
    path = _word(tmp_path, "{{シーケンス図}}")
    filled = docx.Document(io.BytesIO(docgen.fill(path, {"シーケンス図": DIAGRAM})))
    assert len(filled.inline_shapes) == 1
    assert "mermaid" not in filled.paragraphs[0].text
    assert "{{" not in filled.paragraphs[0].text


def test_word_keeps_the_mermaid_text_when_it_cannot_be_drawn(tmp_path, undrawable):
    """黙って図が消えるのが最悪である。利用者は成果物を開くまで気づけない。"""
    path = _word(tmp_path, "{{シーケンス図}}")
    reported = []
    result = docgen.fill(
        path, {"シーケンス図": DIAGRAM}, lambda name, reason: reported.append(name)
    )
    filled = docx.Document(io.BytesIO(result))
    assert len(filled.inline_shapes) == 0
    assert "sequenceDiagram" in filled.paragraphs[0].text
    assert reported == ["シーケンス図"]


def test_powerpoint_puts_the_picture_where_the_shape_was(tmp_path, drawn):
    path = _slide_with(tmp_path, lambda slide: slide.shapes)
    filled = Presentation(io.BytesIO(docgen.fill(path, {"シーケンス図": DIAGRAM})))
    shapes = filled.slides[0].shapes
    pictures = [s for s in shapes if s.shape_type == MSO_SHAPE_TYPE.PICTURE]
    assert len(pictures) == 1
    assert (pictures[0].left, pictures[0].top) == (Inches(1), Inches(2))
    assert "{{シーケンス図}}" not in _all_text(shapes)


def test_powerpoint_reports_a_mark_inside_a_group(tmp_path, drawn):
    """グループの中の left/top はグループからの相対値で、スライドへ貼ると
    見当違いの場所に出る。ずれた場所に置くより、置けないことを伝える。"""
    path = _slide_with(tmp_path, lambda slide: slide.shapes.add_group_shape().shapes)
    reported = []
    result = docgen.fill(
        path, {"シーケンス図": DIAGRAM}, lambda name, reason: reported.append(name)
    )
    shapes = Presentation(io.BytesIO(result)).slides[0].shapes
    assert [s for s in shapes if s.shape_type == MSO_SHAPE_TYPE.PICTURE] == []
    assert reported == ["シーケンス図"]
    assert "sequenceDiagram" in _all_text(shapes)


def test_excel_anchors_the_picture_to_the_marked_cell(tmp_path, drawn):
    """保存した中身で確かめる。openpyxl で読み直したときの画像の扱いは版に
    依存するため、xlsx の中に画像の部品があることを直接見る。"""
    path = tmp_path / "設計書.xlsx"
    book = openpyxl.Workbook()
    book.active["B3"] = "{{シーケンス図}}"
    book.save(path)

    result = docgen.fill(path, {"シーケンス図": DIAGRAM})
    with zipfile.ZipFile(io.BytesIO(result)) as archive:
        assert [name for name in archive.namelist() if name.startswith("xl/media/")]
    assert openpyxl.load_workbook(io.BytesIO(result)).active["B3"].value in (None, "")


def test_markdown_keeps_the_code_block(tmp_path, drawn):
    """.md は描かない。コードブロックのままで図として表示される。"""
    path = tmp_path / "設計書.md"
    path.write_text("# 設計書\n\n{{シーケンス図}}\n", encoding="utf-8")
    filled = docgen.fill(path, {"シーケンス図": DIAGRAM}).decode("utf-8")
    assert "```mermaid" in filled
    assert not drawn.called


def test_every_filler_accepts_the_callback():
    """1つでも受け取り損ねると、その形式の雛形を選んだときだけ TypeError に
    なる。画面からは4形式を同じ呼び方で呼ぶ。"""
    from docgen import _TEMPLATES

    for suffix, (_, filler) in _TEMPLATES.items():
        assert "on_diagram_error" in inspect.signature(filler).parameters, suffix
