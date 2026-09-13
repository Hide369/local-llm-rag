"""PowerPoint の雛形。

docx と同じく段落単位で扱う。実測 2026-09-13 では pptx でも
`{{会議名}}` が `['会議名：{{会議', '名}}']` の2つの run に割れていた。

図形はグループにまとめられるため、図形の走査は再帰する。グループの中を
見ないと印を取りこぼし、しかも「印が無い雛形」と同じ見え方になる。
"""
import io
from pathlib import Path

from pptx import Presentation

from docgen import marks, mermaid


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
        if shape.has_text_frame:
            yield from shape.text_frame.paragraphs
        if shape.has_table:
            # テーブルセルの段落も見ないと、テーブル内の印を取りこぼす。
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


def fill(path: Path, values: dict[str, str], on_diagram_error=None) -> bytes:
    """印を値で埋めた結果をバイト列で返す。"""
    texts, images = mermaid.rendered(values, on_diagram_error)
    presentation = Presentation(path)
    placed: set[str] = set()
    for slide in presentation.slides:
        placed |= _place_diagrams(slide, images)
    for name in images:
        if name in placed:
            continue
        # 貼る先が決まらなかった図は、Mermaid のテキストとして入れる。印が
        # 空のまま残ると、利用者は図が消えたことに気づけない。
        texts[name] = values[name]
        if on_diagram_error is not None:
            # 貼れない理由は「グループ図形の中」だけではない。スライド上の
            # 表のセルに図の印を置いた場合もここに来るが、表の中にグループは
            # ないため、グループと決め打つ文言は嘘になる（レビューで実測）。
            on_diagram_error(name, "この場所には図を貼れません（グループ図形や表の中）")
    for paragraph in _paragraphs(presentation):
        _fill_paragraph(paragraph, texts)
    buffer = io.BytesIO()
    presentation.save(buffer)
    return buffer.getvalue()


def _place_diagrams(slide, images: dict[str, bytes]) -> set[str]:
    """図の印を持つ図形の位置に画像を置き、印の文字を消す。置けた印を返す。

    ここだけグループの中へ入らない。グループの中の図形の left/top はグループ
    からの相対値であり、slide.shapes.add_picture にそのまま渡すと見当違いの
    場所へ貼られる。黙ってずれるより、置かずに呼び出し元へ返す。
    """
    placed: set[str] = set()
    # 走査の途中で図形が増えるため、先に並びを固定する。
    for shape in list(slide.shapes):
        if not shape.has_text_frame:
            continue
        here = [name for name in marks.names(shape.text_frame.text) if name in images]
        if not here:
            continue
        for name in here:
            # 幅は図形に合わせ、高さは比を保って python-pptx に決めさせる。
            slide.shapes.add_picture(
                io.BytesIO(images[name]), shape.left, shape.top, width=shape.width
            )
            placed.add(name)
        for paragraph in shape.text_frame.paragraphs:
            _fill_paragraph(paragraph, {name: "" for name in here})
    return placed


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
