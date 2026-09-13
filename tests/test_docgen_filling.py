"""印の値を決める。

ask を引数で受け取るため、実機のOllamaに触れずにテストできる
（ingest/conditions.py と同じ方針）。
"""
import json

import pytest

from docgen import filling
from ingest.retrieval import Hit


def _hit(text, source="議事録.docx"):
    return Hit(text=text, distance=0.3, occurrences=[{"source": source}])


def _answering(payload):
    def ask(prompt):
        return json.dumps(payload, ensure_ascii=False)

    return ask


def test_the_values_come_back_keyed_by_placeholder_name():
    values = filling.fill_values(
        ["会議名", "決定事項"],
        "第5回会議の議事録を作って",
        [("社内資料", [_hit("第5回 AI活用検討会を開催した。")])],
        [],
        _answering({"会議名": "第5回 AI活用検討会", "決定事項": "・継続"}),
    )
    assert values == {"会議名": "第5回 AI活用検討会", "決定事項": "・継続"}


def test_a_key_that_is_not_a_placeholder_is_dropped():
    """雛形に無い欄を返してくることがある。そのまま通すと、置換されない値が
    黙って捨てられたのか、そもそも印が無かったのかが分からなくなる。"""
    values = filling.fill_values(
        ["会議名"], "質問", [], [], _answering({"会議名": "第5回", "余計": "x"})
    )
    assert values == {"会議名": "第5回"}


def test_a_value_that_is_not_a_string_is_dropped():
    """数値や配列を返してくることがある。置換は文字列にしかできない。"""
    values = filling.fill_values(
        ["会議名", "出席者"],
        "質問",
        [],
        [],
        _answering({"会議名": "第5回", "出席者": ["田中", "佐藤"]}),
    )
    assert values == {"会議名": "第5回"}


def test_an_empty_value_is_dropped():
    """空文字は「埋まった」ではない。印を残したほうが利用者は気づける。"""
    values = filling.fill_values(
        ["会議名", "決定事項"], "質問", [], [], _answering({"会議名": "第5回", "決定事項": ""})
    )
    assert values == {"会議名": "第5回"}


def test_broken_json_yields_no_values_instead_of_raising():
    """壊れて返ることがある。止めると、雛形すら受け取れない。
    全欄が埋まらなかった扱いになり、印の残った雛形が出る（設計書6節）。"""
    assert filling.fill_values(["会議名"], "質問", [], [], lambda prompt: "not json") == {}


def test_a_json_array_yields_no_values():
    assert filling.fill_values(["会議名"], "質問", [], [], lambda prompt: "[1, 2]") == {}


def test_an_llm_failure_is_not_swallowed():
    """LLMが落ちたことは利用者に伝える。黙って空の雛形を返さない。"""

    def broken(prompt):
        raise RuntimeError("模擬失敗")

    with pytest.raises(RuntimeError, match="模擬失敗"):
        filling.fill_values(["会議名"], "質問", [], [], broken)


def test_the_prompt_contains_the_placeholder_names_and_the_question():
    prompt = filling.build_prompt(["会議名"], "第5回会議の議事録", [], [])
    assert "会議名" in prompt
    assert "第5回会議の議事録" in prompt


def test_the_prompt_contains_the_search_results_with_their_citations():
    prompt = filling.build_prompt(
        ["会議名"],
        "質問",
        [("社内資料", [_hit("第5回を開催した。", source="第5回議事録.docx")])],
        [],
    )
    assert "第5回を開催した。" in prompt
    assert "第5回議事録.docx" in prompt


def test_each_kind_of_source_gets_its_own_section():
    """混ぜて並べると、どれが社内の決定事項でどれが外部ライブラリの説明なのかを
    モデルが区別できない。"""
    prompt = filling.build_prompt(
        ["図"],
        "質問",
        [
            ("社内資料", [_hit("社内の決定事項。")]),
            ("技術ドキュメント", [_hit("sequenceDiagram syntax", source="mermaid.md")]),
        ],
        [],
    )
    assert prompt.index("社内資料") < prompt.index("技術ドキュメント")
    assert "sequenceDiagram syntax" in prompt


def test_the_prompt_says_a_diagram_may_be_returned():
    """この1文が無いと、モデルは図の欄にも散文を返す。記法を覚える役目は
    利用者ではなくプロンプトが引き受ける（設計書7節）。"""
    prompt = filling.build_prompt(["シーケンス図"], "質問", [], [])
    assert "mermaid" in prompt


def test_the_prompt_contains_the_attachments_with_their_names():
    prompt = filling.build_prompt(["会議名"], "質問", [], [("録音.txt", "本日の会議を始めます")])
    assert "録音.txt" in prompt
    assert "本日の会議を始めます" in prompt


def test_a_prompt_over_the_limit_is_refused():
    """切り詰めると、議事録の後半が抜けたことに利用者が気づけない（設計書7節）。"""
    long_text = "あ" * (filling.MAX_PROMPT_CHARS + 1)
    with pytest.raises(filling.PromptTooLongError, match="長すぎ"):
        filling.fill_values(["会議名"], "質問", [], [("長い.txt", long_text)], _answering({}))
