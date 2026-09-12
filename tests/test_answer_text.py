import pytest

from ingest.answer_text import (
    mermaid_definitions,
    strip_html_tags,
    strip_html_tags_stream,
    strip_label,
    without_label,
)


def _joined(chunks):
    return "".join(without_label(chunks))


def _tag_joined(chunks):
    return "".join(strip_html_tags_stream(chunks))


def _tokenised(text):
    """1文字ずつ届く、いちばん細かいストリームを作る。"""
    return list(text)


@pytest.mark.parametrize(
    "line, expected",
    [
        ("答え： 型番：UD-1100iE 達成率：125%", "型番：UD-1100iE 達成率：125%"),
        ("答え:UD-1100iE", "UD-1100iE"),
        ("答え ： UD-1100iE", "UD-1100iE"),
        ("　答え：UD-1100iE", "UD-1100iE"),
    ],
)
def test_strips_the_label_and_keeps_the_content(line, expected):
    assert strip_label(line) == expected


@pytest.mark.parametrize(
    "line",
    [
        "答えは125%です。",  # 文中の「答え」はラベルではない
        "この答え：は文の途中にある",  # 行頭でなければ残す
        "省エネ基準達成率：125%",
    ],
)
def test_leaves_ordinary_japanese_alone(line):
    assert strip_label(line) == line


def test_removes_the_label_from_a_streamed_answer():
    """ラベルはトークンに分かれて届く。1文字ずつでも落とせる。"""
    text = "型番はUD-1100iEです。\n答え： 型番：UD-1100iE 達成率：125%"
    assert _joined(_tokenised(text)) == "型番はUD-1100iEです。\n型番：UD-1100iE 達成率：125%"


def test_keeps_the_sentence_when_the_answer_itself_follows_the_label():
    """回答本体がラベル行にしか無い出力でも、中身は消さない。"""
    text = "答え：省エネ基準達成率が125%の機種は、UD-1100iEです。"
    assert _joined(_tokenised(text)) == "省エネ基準達成率が125%の機種は、UD-1100iEです。"


def test_passes_an_answer_without_the_label_through_unchanged():
    text = "省エネ基準達成率が最も高いのはUD-1100iEです。\n\n出典：[1] UD-1100iE_spec_step3.md\n"
    assert _joined(_tokenised(text)) == text


def test_does_not_depend_on_where_the_chunk_boundaries_fall():
    text = "1行目\n答え：2行目\n答えは3行目\n"
    expected = "1行目\n2行目\n答えは3行目\n"
    for size in range(1, len(text) + 1):
        chunks = [text[start : start + size] for start in range(0, len(text), size)]
        assert _joined(chunks) == expected, f"size={size}"


def test_holds_back_only_the_first_few_characters_of_a_line():
    """行末まで溜め込まない。溜めると1行あたり数秒待たされて表示が固まる。

    「答え」になりえないと分かった時点で流すので、長い行の途中は素通りする。
    """
    emitted = list(without_label(["これは長い行の先頭で、", "続きがすぐ流れる必要がある"]))
    assert emitted[0] == "これは長い行の先頭で、"


@pytest.mark.parametrize(
    "text, expected",
    [
        ("①検出。<br>②判定。", "①検出。②判定。"),
        ("①検出。<BR>②判定。", "①検出。②判定。"),
        ("①検出。<br/>②判定。", "①検出。②判定。"),
        ("①検出。<br />②判定。", "①検出。②判定。"),
        ("見出し<br>本文", "見出し本文"),
        ("普通の文には影響しない", "普通の文には影響しない"),
        ("<ul><li>A</li><li>B</li></ul>", "・A ・B "),
        ("<UL><LI>A</LI></UL>", "・A "),
    ],
)
def test_strips_html_tags(text, expected):
    assert strip_html_tags(text) == expected


def test_strip_html_tags_stream_does_not_depend_on_where_the_chunk_boundaries_fall():
    text = "①検出。<br />②判定。<br>③転送。<ul><li>④確認。</li></ul>"
    expected = "①検出。②判定。③転送。・④確認。 "
    for size in range(1, len(text) + 1):
        chunks = [text[start : start + size] for start in range(0, len(text), size)]
        assert _tag_joined(chunks) == expected, f"size={size}"


def test_strip_html_tags_stream_leaves_an_unrelated_angle_bracket_alone():
    """既知のタグになりえないとわかれば、溜めていた "<" ごとそのまま流す。"""
    assert _tag_joined(["a<b>c"]) == "a<b>c"


# --- マーメイドの定義の取り出し -------------------------------------------
#
# 「マーメイドで表示して」と頼まれたとき、記法と図の両方を出す。記法は回答を
# 丸ごとコードブロックに入れれば足りるが、図はフェンスの中身だけを
# st.mermaid_chart() へ渡す必要がある。回答全体を渡すと地の文が構文エラーになり、
# st.write() で描くと地の文がコードブロックと二重に出る。


def test_a_fenced_definition_is_extracted():
    text = "以下のとおりです。\n\n```mermaid\ngraph TD;\n  A-->B;\n```\n"

    assert mermaid_definitions(text) == ["graph TD;\n  A-->B;"]


def test_every_fence_is_extracted():
    """図を2つ描いた回答で、片方だけが消えるのを防ぐ。"""
    text = "```mermaid\ngraph TD;\n  A-->B;\n```\n次に\n```mermaid\ngraph LR;\n  C-->D;\n```"

    assert mermaid_definitions(text) == ["graph TD;\n  A-->B;", "graph LR;\n  C-->D;"]


def test_text_without_a_fence_is_taken_as_one_definition():
    """モデルが素の定義だけを返すことがある。フェンスが無いから図を出さない、
    では要望に応えられない。
    """
    assert mermaid_definitions("graph TD;\n  A-->B;") == ["graph TD;\n  A-->B;"]


def test_a_longer_fence_is_handled():
    """st.mermaid_chart 自身が4本以上のバッククォートで包む（本文中の
    バッククォートでフェンスが早閉じしないようにするため）。同じ形を受ける。
    """
    text = "````mermaid\ngraph TD;\n  A-->B;\n````"

    assert mermaid_definitions(text) == ["graph TD;\n  A-->B;"]


def test_the_language_tag_is_matched_case_insensitively():
    assert mermaid_definitions("```Mermaid\ngraph TD;\n```") == ["graph TD;"]


def test_a_non_mermaid_fence_is_not_extracted():
    """python のコード例を図として描こうとすると構文エラーの枠が出る。"""
    text = "```python\nprint(1)\n```"

    assert mermaid_definitions(text) == [text]


def test_empty_text_yields_nothing():
    assert mermaid_definitions("") == []
    assert mermaid_definitions("   \n  ") == []


def test_an_empty_fence_is_dropped():
    """中身の無いフェンスを渡すと mermaid が構文エラーの枠を出す。"""
    assert mermaid_definitions("```mermaid\n\n```") == []
