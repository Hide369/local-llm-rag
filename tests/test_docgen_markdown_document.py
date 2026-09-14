"""Markdown を中間構造へ解析し、4形式へ組む。

Markdown を一度だけ解析して共通の構造にするのは、形式ごとに読み直すと記法の
解釈が4箇所に分かれるためである。
"""
from docgen import markdown_document as md


def test_headings_keep_their_level():
    blocks = md.parse("# 設計書\n\n## 構成\n")

    assert blocks == [md.Heading(1, "設計書"), md.Heading(2, "構成")]


def test_consecutive_lines_become_one_paragraph():
    """Markdown では空行が段落の区切りである。改行1つで切ると、
    折り返しただけの文が別々の段落になる。"""
    blocks = md.parse("これは1つの\n段落である。\n\n次の段落。\n")

    assert blocks == [md.Paragraph("これは1つの 段落である。"), md.Paragraph("次の段落。")]


def test_bullets_are_collected_into_one_block():
    blocks = md.parse("- 一つ目\n- 二つ目\n")

    assert blocks == [md.Bullets(["一つ目", "二つ目"])]


def test_numbered_lists_are_bullets_too():
    """番号付きも箇条書きとして扱う。docx と pptx で番号を復元する価値より、
    2種類を持ち回る複雑さのほうが大きい。"""
    blocks = md.parse("1. 一つ目\n2. 二つ目\n")

    assert blocks == [md.Bullets(["一つ目", "二つ目"])]


def test_a_table_keeps_its_header_and_rows():
    text = "| 区分 | 日数 |\n| --- | --- |\n| 6か月 | 10日 |\n"

    blocks = md.parse(text)

    assert blocks == [md.Table(["区分", "日数"], [["6か月", "10日"]])]


def test_a_fenced_block_is_code():
    blocks = md.parse("```python\nprint(1)\n```\n")

    assert blocks == [md.Code("print(1)")]


def test_a_mermaid_fence_is_a_diagram():
    """図として描ける可能性があるものを、ただのコードと区別する。"""
    blocks = md.parse("```mermaid\ngraph TD\nA-->B\n```\n")

    assert blocks == [md.Diagram("graph TD\nA-->B")]


def test_a_heading_inside_a_fence_is_not_a_heading():
    """コード例の中の # を見出しにすると、文書の構造が崩れる。"""
    blocks = md.parse("```\n# これはコメント\n```\n")

    assert blocks == [md.Code("# これはコメント")]


def test_an_empty_document_has_no_blocks():
    assert md.parse("   \n\n") == []


def test_a_blank_line_is_what_separates_two_tables():
    """2つの表を分ける方法は空行である。GFM の標準動作として、空行がなければ
    2つのテーブル構文が1つにマージされる。これは仕様であり、バグではない。"""
    # 空行なし：マージされて1つのテーブルになる
    text_no_blank = "| a | b |\n| - | - |\n| 1 | 2 |\n| c | d |\n| - | - |\n| 3 | 4 |\n"
    blocks_no_blank = md.parse(text_no_blank)
    assert blocks_no_blank == [
        md.Table(["a", "b"], [["1", "2"], ["c", "d"], ["-", "-"], ["3", "4"]])
    ]

    # 空行あり：2つの別々のテーブルになる
    text_with_blank = "| a | b |\n| - | - |\n| 1 | 2 |\n\n| c | d |\n| - | - |\n| 3 | 4 |\n"
    blocks_with_blank = md.parse(text_with_blank)
    assert blocks_with_blank == [
        md.Table(["a", "b"], [["1", "2"]]),
        md.Table(["c", "d"], [["3", "4"]])
    ]


def test_a_short_row_is_padded_to_header_width():
    """セル数がヘッダーより少ない行は、空文字列でパディングされる。
    docx/xlsx/pptx レンダラーは固定列数で構築されるため、不揃いな行が
    列ずれを引き起こさないように正規化が必須である。"""
    text = "| a | b |\n| - | - |\n| 1 |\n"

    blocks = md.parse(text)

    assert blocks == [md.Table(["a", "b"], [["1", ""]])]


def test_a_long_row_surplus_cells_are_dropped():
    """セル数がヘッダーより多い行の余剰セルは削除される。
    GFM の仕様に準じ、下流レンダラーが誤配置しない形に整形する。"""
    text = "| a | b |\n| - | - |\n| 1 | 2 | 3 |\n"

    blocks = md.parse(text)

    assert blocks == [md.Table(["a", "b"], [["1", "2"]])]


def test_a_table_with_legitimate_dash_data_rows_keeps_all_rows():
    """データ行に | - | - | が含まれる場合、先読みで表を分けようとすると
    区切り行と見分けが付かず、この行が消える。複数の表でマージを許容する以上、
    シンプルな停止条件（空行まで続ける）が唯一の正解である。"""
    text = "| a | b |\n| - | - |\n| 1 | 2 |\n| - | - |\n| 3 | 4 |\n"

    blocks = md.parse(text)

    assert blocks == [md.Table(["a", "b"], [["1", "2"], ["-", "-"], ["3", "4"]])]
