"""雛形なしの文書生成。

雛形ありの経路（docgen/filling.py）と同じ材料を使い、埋める欄の一覧の代わりに
出力の形の指示を載せる。
"""
import pytest

from docgen import filling, freeform


class _Hit:
    def __init__(self, citation, text):
        self.citation = citation
        self.text = text


def test_the_prompt_carries_the_request_and_every_source():
    prompt = freeform.build_prompt(
        "設計書を書いて",
        [("社内資料", [_Hit("議事録.docx p.1", "第5回を開催した。")])],
        [("メモ.txt", "補足事項")],
        "- main.go (120 bytes)",
        ".md",
    )

    assert "設計書を書いて" in prompt
    assert "議事録.docx p.1" in prompt
    assert "第5回を開催した。" in prompt
    assert "メモ.txt" in prompt
    assert "補足事項" in prompt
    assert "main.go" in prompt


def test_the_prompt_keeps_the_no_invention_rule():
    """根拠の無い文書を作らないという方針は、雛形の有無で変わらない。"""
    prompt = freeform.build_prompt("依頼", [], [], "", ".md")

    assert "書かれていないこと" in prompt


def test_only_the_excel_prompt_asks_for_a_table():
    """一覧表が欲しいのに文章が返ると、変換のしようがない。"""
    assert "シート名" in freeform.build_prompt("依頼", [], [], "", ".xlsx")
    assert "シート名" not in freeform.build_prompt("依頼", [], [], "", ".md")


def test_write_markdown_returns_what_the_model_wrote():
    result = freeform.write_markdown(
        "依頼", [], [], "", ".md", lambda prompt: "# 設計書\n\n本文"
    )

    assert result == "# 設計書\n\n本文"


def test_write_markdown_stops_before_calling_the_model_when_too_long():
    """呼んでから落ちると、利用者は30〜60秒待たされたうえで何も受け取れない。"""
    huge = [("巨大.md", "あ" * (filling.MAX_PROMPT_CHARS + 1))]

    with pytest.raises(filling.PromptTooLongError):
        freeform.write_markdown("依頼", [], huge, "", ".md", lambda prompt: "本文")
