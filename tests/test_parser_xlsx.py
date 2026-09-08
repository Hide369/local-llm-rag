"""Excelブックの取り込み。

表は本文と違い、行と列の関係が意味を持つ。埋め込みに渡す時点で1本の文字列に
潰す以上、どの列の値なのかが読み取れる形にしておかないと、数字の羅列になって
検索でも回答でも使えない。
"""
import pytest
from openpyxl import Workbook

from ingest.models import SHEET
from ingest.parsers import SUPPORTED_SUFFIXES, parse
from ingest.parsers.xlsx_parser import parse_xlsx


@pytest.fixture
def book_path(tmp_path):
    book = Workbook()
    first = book.active
    first.title = "商品一覧"
    first.append(["商品コード", "商品名", "価格"])
    first.append(["A-001", "洗濯機", 89800])
    second = book.create_sheet("備考")
    second.append(["納期は三営業日"])
    path = tmp_path / "一覧.xlsx"
    book.save(path)
    return path


def test_each_sheet_becomes_one_unit(book_path):
    units = parse_xlsx(book_path)

    assert len(units) == 2
    assert [unit.location_type for unit in units] == [SHEET, SHEET]
    assert [unit.location for unit in units] == [1, 2]


def test_the_sheet_name_is_carried_in_the_text(book_path):
    """シート単体で引かれたとき、何の表なのかが分からなくなるのを防ぐ。

    Markdownのユニットが見出しにH1を付けているのと同じ理由である。
    """
    assert parse_xlsx(book_path)[0].text.startswith("商品一覧")


def test_a_row_keeps_its_cells_in_one_line(book_path):
    """行の並びが崩れると、どの値がどの列なのか復元できなくなる。"""
    text = parse_xlsx(book_path)[0].text

    assert "商品コード | 商品名 | 価格" in text
    assert "A-001 | 洗濯機 | 89800" in text


def test_the_sheet_name_is_available_for_the_citation(book_path):
    """出典に「一覧.xlsx シート名」と出すため、headingで運ぶ。"""
    assert parse_xlsx(book_path)[0].heading == "商品一覧"


def test_an_empty_sheet_produces_no_unit(tmp_path):
    """空シートはブックに残りがちで、そのままだと空チャンクがDBに入る。"""
    book = Workbook()
    book.active.title = "空"
    book.create_sheet("中身あり").append(["値"])
    path = tmp_path / "空あり.xlsx"
    book.save(path)

    units = parse_xlsx(path)

    assert len(units) == 1
    assert units[0].heading == "中身あり"


def test_empty_cells_do_not_leave_the_string_none(tmp_path):
    """未入力セルは openpyxl が None を返す。str() すると本文に None が並ぶ。"""
    book = Workbook()
    book.active.title = "穴あき"
    book.active.append(["A", None, "C"])
    path = tmp_path / "穴あき.xlsx"
    book.save(path)

    assert "None" not in parse_xlsx(path)[0].text


def test_a_formula_is_stored_as_its_computed_value(tmp_path):
    """数式そのものを索引しても検索の役に立たない。

    data_only を落とすと本文が「=SUM(A1:A2)」になり、利用者が読む値は
    どこにも残らない。Excelが計算結果を保存していない場合は値が無いため、
    その場合にセルが消えることまでを含めてこの挙動である。
    """
    book = Workbook()
    sheet = book.active
    sheet.title = "計算"
    sheet["A1"] = 1
    sheet["A2"] = 2
    sheet["A3"] = "=SUM(A1:A2)"
    path = tmp_path / "計算.xlsx"
    book.save(path)

    assert "=SUM" not in parse_xlsx(path)[0].text


def test_xlsx_is_routed_by_the_registry(book_path):
    """拡張子の登録を忘れると、source/ に置いても黙って無視される。"""
    assert ".xlsx" in SUPPORTED_SUFFIXES
    assert parse(book_path)[0].heading == "商品一覧"
