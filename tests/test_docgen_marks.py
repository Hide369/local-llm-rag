"""印の記法。

記法を知る場所をここ1つに閉じている。4つの形式すべてが同じ規則で動く必要が
あり、形式ごとに正規表現を書くと、片方だけ直した状態が例外を出さずに成立する。
"""
from docgen import marks


def test_names_are_returned_in_the_order_they_appear():
    text = "会議名：{{会議名}}\n日時：{{開催日}}"
    assert marks.names(text) == ["会議名", "開催日"]


def test_a_name_that_appears_twice_is_listed_once():
    """同じ印を2箇所に置く雛形がある（表紙とヘッダーなど）。

    2回数えると、画面の「埋まらなかった欄」も二重に出る。
    """
    text = "{{会議名}}\n\n---\n\n{{会議名}} 議事録"
    assert marks.names(text) == ["会議名"]


def test_text_without_any_mark_has_no_names():
    assert marks.names("ただの本文です。") == []


def test_replace_fills_only_the_marks_that_have_a_value():
    """値の無い印は残す。空にすると、もともと空欄なのか埋め損ねたのか分からない。"""
    text = "会議名：{{会議名}}\n決定事項：{{決定事項}}"
    filled = marks.replace(text, {"会議名": "第5回"})
    assert filled == "会議名：第5回\n決定事項：{{決定事項}}"


def test_replace_ignores_a_value_whose_name_is_not_in_the_text():
    assert marks.replace("{{会議名}}", {"会議名": "第5回", "余計": "x"}) == "第5回"


def test_replace_fills_every_occurrence_of_the_same_name():
    assert marks.replace("{{名}}と{{名}}", {"名": "A"}) == "AとA"


def test_a_multi_line_value_is_inserted_as_is():
    """件数が変わる中身は1つの印に複数行で入れる（設計書5節）。"""
    assert marks.replace("{{決定事項}}", {"決定事項": "・A\n・B"}) == "・A\n・B"


def test_a_mark_containing_braces_is_not_matched():
    """入れ子の { } は印ではない。コード例を載せた雛形を壊さない。"""
    assert marks.names("{{ {x} }}") == []


def test_a_name_with_surrounding_whitespace_is_stripped():
    """`{{ 会議名 }}` のように印の名前の内側に空白があっても、
    利用者が書く `{{会議名}}` と同じ名前として扱う。"""
    assert marks.names("{{ 会議名 }}") == ["会議名"]
    assert marks.replace("{{ 会議名 }}", {"会議名": "第5回"}) == "第5回"
