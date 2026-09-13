"""PowerPoint の雛形。

docx と同じく段落単位で扱う。実測 2026-09-13 では pptx でも
`{{会議名}}` が `['会議名：{{会議', '名}}']` の2つの run に割れていた。

図形はグループにまとめられるため、図形の走査は再帰する。グループの中を
見ないと印を取りこぼし、しかも「印が無い雛形」と同じ見え方になる。
"""
import io
from pathlib import Path

from pptx import Presentation

from docgen import marks


def _paragraphs(presentation):
    """全スライドの全図形から段落を取得する。

    テーブルセルとグループ図形の中も見る。グループの中を見ないと
    取りこぼし、しかも「印が無い雛形」と同じ見え方になる。
    """
    for slide in presentation.slides:
        yield from _shape_paragraphs(slide.shapes)


def _shape_paragraphs(shapes):
    """図形の列から段落を取得する。再帰的にグループの中も見る。"""
    for shape in shapes:
        # テキストフレームを持つ図形から段落を取得
        if shape.shape_type is not None and shape.has_text_frame:
            yield from shape.text_frame.paragraphs
        # テーブルセルから段落を取得
        if shape.has_table:
            for row in shape.table.rows:
                for cell in row.cells:
                    yield from cell.text_frame.paragraphs
        # グループ図形は .shapes を持つ。中の図形も同じ扱いにする。
        if hasattr(shape, "shapes"):
            yield from _shape_paragraphs(shape.shapes)


def placeholders(path: Path) -> list[str]:
    """雛形に含まれる印の名前を、出現順・重複なしで返す。"""
    found: list[str] = []
    for paragraph in _paragraphs(Presentation(path)):
        text = "".join(run.text for run in paragraph.runs)
        for name in marks.names(text):
            if name not in found:
                found.append(name)
    return found


def fill(path: Path, values: dict[str, str]) -> bytes:
    """印を値で埋めた結果をバイト列で返す。"""
    presentation = Presentation(path)
    for paragraph in _paragraphs(presentation):
        _fill_paragraph(paragraph, values)
    buffer = io.BytesIO()
    presentation.save(buffer)
    return buffer.getvalue()


def _fill_paragraph(paragraph, values: dict[str, str]) -> None:
    """段落の印を値で置換する。

    段落のテキストを組み立てて置換し、先頭の run に書き戻す。
    pptx の run は文字しか持たないため、他の run を空にしても問題ない。
    印が無い段落には触らない。
    """
    if not paragraph.runs:
        return
    original = "".join(run.text for run in paragraph.runs)
    replaced = marks.replace(original, values)
    if replaced == original:
        # 印が無い段落には触らない。触ると書式が先頭 run のものに潰れる。
        return
    paragraph.runs[0].text = replaced
    for run in paragraph.runs[1:]:
        run.text = ""
