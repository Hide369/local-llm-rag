"""Word の雛形。

印は段落単位で扱う。実測 2026-09-13 では、人が編集した docx は1つの段落が
複数の run に割れており、`{{会議名}}` が `['会議名：{{会議', '名}}']` の
2つになっていた。run を1つずつ見て置換すると印が見つからない。

差し込みは、段落のテキストを組み立てて置換し、先頭の run に書き戻して残りの
run を空にする。書式は先頭 run のものになる。印を含まない段落には触らない。
触ると、書式の違う run が先頭のものに潰れる。

書き戻す先は「文字を持つ run」に限る。実測 2026-09-13:
`run.text = ...` の setter は `CT_R.clear_content()` を呼び、w:rPr 以外の
子要素を全部消す。画像だけの run（w:drawing）を書き戻し先にすると、その run
にある画像が消える。ヘッダーにロゴを置く雛形では、印より画像の run が先に
来る並びの方が普通であり、位置で「先頭かどうか」を判断すると事故る。
"""
import io
from pathlib import Path

import docx
from docx.shared import Inches

from docgen import marks, mermaid

# mmdc の既定の PNG は幅800px（約8.3インチ）で、A4縦の段幅（約6.5インチ）より
# 広い。そのまま入れると右へはみ出すので、幅を決めて高さは比で追従させる。
DIAGRAM_WIDTH = Inches(6.0)


def _paragraphs(document):
    """本文・表・ヘッダー・フッターの全段落を返す。

    ヘッダーまで見るのは、会議名をヘッダーに入れる雛形があるためである。
    本文だけ見ていると取りこぼし、しかも「印が無い雛形」と同じ見え方になる。
    """
    yield from document.paragraphs
    for table in document.tables:
        yield from _table_paragraphs(table)
    for section in document.sections:
        for part in (section.header, section.footer):
            yield from part.paragraphs
            for table in part.tables:
                yield from _table_paragraphs(table)


def _table_paragraphs(table):
    """表のセルの段落。セルの中に表が入ることがあるので再帰する。"""
    for row in table.rows:
        for cell in row.cells:
            yield from cell.paragraphs
            for nested in cell.tables:
                yield from _table_paragraphs(nested)


def placeholders(path: Path) -> list[str]:
    document = docx.Document(path)
    found: list[str] = []
    for paragraph in _paragraphs(document):
        for name in marks.names(paragraph.text):
            if name not in found:
                found.append(name)
    return found


def fill(path: Path, values: dict[str, str], on_diagram_error=None) -> bytes:
    texts, images = mermaid.rendered(values, on_diagram_error)
    document = docx.Document(path)
    for paragraph in _paragraphs(document):
        _fill_paragraph(paragraph, texts, images)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def _fill_paragraph(paragraph, values: dict[str, str], images=None) -> None:
    images = images or {}
    # 文字を持つ run だけを書き戻し先の候補にする。位置に関係なく、文字を
    # 持たない run（画像だけの run 等）には一切触らない。段落の先頭がロゴの
    # run というヘッダーの並びでも、これでロゴは消えない。
    carriers = [run for run in paragraph.runs if run.text]
    if not carriers:
        return
    original = "".join(run.text for run in carriers)
    here = [name for name in marks.names(original) if name in images]
    # 図にする印はいったん空文字にしてから画像を足す。消さないと、画像の脇に
    # {{シーケンス図}} の文字が残る。
    replaced = marks.replace(original, {**values, **{name: "" for name in here}})
    if replaced == original:
        # 印が無い、あるいは値が1つも当たらなかった段落。触らない。
        # 触ると、書式の違う run が先頭 run のものに潰れる。
        return
    # 改行は run.text の setter が <w:br/> に変換する（実測 2026-09-13）。
    # タブも同じで、run.text は w:tab を \t として往復する。
    carriers[0].text = replaced
    for run in carriers[1:]:
        run.text = ""
    for name in here:
        carriers[0].add_picture(io.BytesIO(images[name]), width=DIAGRAM_WIDTH)
