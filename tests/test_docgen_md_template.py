"""Markdown の雛形と、拡張子による振り分け。

4形式のうち最も単純なものでディスパッチャの形を確立する。ingest/parsers/ が
「拡張子ごとに1ファイル＋振り分け役の __init__.py」でうまく動いているので、
書く側も同じ形にする。
"""
import pytest

import docgen


def _write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_placeholders_are_found_in_a_markdown_template(tmp_path):
    path = _write(tmp_path, "議事録.md", "# {{会議名}}\n\n日時：{{開催日}}\n")
    assert docgen.placeholders(path) == ["会議名", "開催日"]


def test_fill_returns_the_filled_bytes(tmp_path):
    path = _write(tmp_path, "議事録.md", "# {{会議名}}\n")
    assert docgen.fill(path, {"会議名": "第5回"}).decode("utf-8") == "# 第5回\n"


def test_an_unfilled_mark_is_left_in_place(tmp_path):
    path = _write(tmp_path, "議事録.md", "# {{会議名}}\n{{決定事項}}\n")
    filled = docgen.fill(path, {"会議名": "第5回"}).decode("utf-8")
    assert filled == "# 第5回\n{{決定事項}}\n"


def test_an_unsupported_suffix_is_refused(tmp_path):
    """PDF は対象外である（設計書2節）。黙って空を返すと、印が0個の雛形と
    区別がつかない。"""
    path = _write(tmp_path, "議事録.pdf", "{{会議名}}")
    with pytest.raises(docgen.UnsupportedTemplateError, match="議事録.pdf"):
        docgen.placeholders(path)


def test_the_supported_suffixes_are_the_four_agreed_formats():
    assert docgen.SUPPORTED_SUFFIXES == {".docx", ".xlsx", ".pptx", ".md"}
