"""Mermaid のテキストを PNG にする。

mmdc は呼ばない。描けることは実測（設計書7節）で確かめてあり、テストのたびに
Chromium を起動すると遅く、mmdc の無い環境では必ず落ちる。ここで確かめるのは
「描けなかったことが呼び出し元に伝わる」という一点である。
"""
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from docgen import mermaid

DIAGRAM = "```mermaid\nsequenceDiagram\n  利用者->>画面: 生成を頼む\n```"
SOURCE = "sequenceDiagram\n  利用者->>画面: 生成を頼む"
PNG = b"\x89PNG\r\n\x1a\n"


def test_a_mermaid_block_is_a_diagram():
    assert mermaid.is_diagram(DIAGRAM)


def test_plain_text_is_not_a_diagram():
    assert not mermaid.is_diagram("第5回 定例会議")


def test_a_code_block_of_another_language_is_not_a_diagram():
    assert not mermaid.is_diagram("```python\nprint(1)\n```")


def test_text_after_the_block_is_not_a_diagram():
    """図とその説明が混ざった値は、図にせず文字列として扱う。

    一部だけ図にすると説明文が消える。図にしなければ Mermaid の記法が
    そのまま見えるだけで、利用者は何が起きたか分かる。
    """
    assert not mermaid.is_diagram(DIAGRAM + "\n\n上の図のとおりです。")


def test_the_source_comes_back_without_the_fence():
    assert mermaid.diagram_source(DIAGRAM) == SOURCE


def test_render_returns_what_the_tool_wrote():
    def fake_run(command, **kwargs):
        Path(command[command.index("-o") + 1]).write_bytes(PNG)
        return subprocess.CompletedProcess(command, 0, "", "")

    with patch("docgen.mermaid.shutil.which", return_value="mmdc.cmd"):
        with patch("docgen.mermaid.subprocess.run", side_effect=fake_run):
            assert mermaid.render(SOURCE) == PNG


def test_render_raises_when_the_tool_is_not_installed():
    with patch("docgen.mermaid.shutil.which", return_value=None):
        with pytest.raises(mermaid.MermaidError):
            mermaid.render(SOURCE)


def test_render_raises_when_the_tool_fails():
    failed = subprocess.CompletedProcess([], 1, "", "Parse error on line 2")
    with patch("docgen.mermaid.shutil.which", return_value="mmdc.cmd"):
        with patch("docgen.mermaid.subprocess.run", return_value=failed):
            with pytest.raises(mermaid.MermaidError, match="Parse error"):
                mermaid.render(SOURCE)


def test_render_raises_when_the_tool_does_not_return():
    timeout = subprocess.TimeoutExpired("mmdc", mermaid.RENDER_TIMEOUT)
    with patch("docgen.mermaid.shutil.which", return_value="mmdc.cmd"):
        with patch("docgen.mermaid.subprocess.run", side_effect=timeout):
            with pytest.raises(mermaid.MermaidError):
                mermaid.render(SOURCE)


def test_rendered_keeps_plain_values_as_text():
    texts, images = mermaid.rendered({"会議名": "第5回 定例会議"})
    assert texts == {"会議名": "第5回 定例会議"}
    assert images == {}


def test_rendered_turns_a_diagram_into_bytes():
    with patch("docgen.mermaid.render", return_value=PNG):
        texts, images = mermaid.rendered({"シーケンス図": DIAGRAM})
    assert texts == {}
    assert images == {"シーケンス図": PNG}


def test_a_diagram_that_cannot_be_drawn_stays_as_text_and_is_reported():
    """黙って落とさない。利用者は成果物を開くまで気づけない。"""
    reported = []
    with patch("docgen.mermaid.render", side_effect=mermaid.MermaidError("mmdc が見つかりません")):
        texts, images = mermaid.rendered(
            {"シーケンス図": DIAGRAM}, lambda name, reason: reported.append((name, reason))
        )
    assert texts == {"シーケンス図": DIAGRAM}
    assert images == {}
    assert reported == [("シーケンス図", "mmdc が見つかりません")]
