"""雛形なしでソースコードを書かせる。

文書の経路（docgen/freeform.py → docgen/markdown_document.py）とは分ける。
Markdown の解析器にコードを通すと `#` コメントが見出しに、`|` が表になる。
"""
import pytest

from docgen import filling, source_code


class _Hit:
    def __init__(self, citation, text):
        self.citation = citation
        self.text = text


def test_the_prompt_names_the_language_it_wants():
    """「コードを書け」だけでは何の言語か決まらない。"""
    assert "Go" in source_code.build_prompt("APIを書いて", [], [], "", ".go")
    assert "C#" in source_code.build_prompt("APIを書いて", [], [], "", ".cs")


def test_the_prompt_forbids_fences_and_prose():
    """前置きやフェンスが混ざると、そのままファイルに書けばコンパイルが通らない。

    剥がす処理は入れてあるが、そもそも書かせないほうが確実である。
    """
    prompt = source_code.build_prompt("依頼", [], [], "", ".go")

    assert "フェンス" in prompt
    assert "説明" in prompt


def test_the_prompt_carries_the_request_and_every_source():
    prompt = source_code.build_prompt(
        "取り込み処理を書いて",
        [("社内資料", [_Hit("設計書.docx p.2", "1ファイル=1ユニットとする。")])],
        [("main.go", "package main")],
        "- main.go (120 bytes)",
        ".go",
    )

    assert "取り込み処理を書いて" in prompt
    assert "設計書.docx p.2" in prompt
    assert "1ファイル=1ユニットとする。" in prompt
    assert "package main" in prompt
    assert "main.go (120 bytes)" in prompt


def test_an_unsupported_suffix_is_rejected():
    with pytest.raises(source_code.UnsupportedLanguageError):
        source_code.build_prompt("依頼", [], [], "", ".rb")


def test_a_fenced_reply_loses_its_fence():
    """モデルは頼まれても ```go で包むことがある。

    そのまま書くとファイルの1行目が ```go になり、コンパイルが通らない。
    """
    reply = "```go\npackage main\n\nfunc main() {}\n```"

    assert source_code.strip_fence(reply) == "package main\n\nfunc main() {}"


def test_prose_around_the_fence_is_dropped_with_it():
    """「以下のコードです」のような前置きもファイルには要らない。"""
    reply = "以下が実装です。\n\n```go\npackage main\n```\n\n説明: main だけです。"

    assert source_code.strip_fence(reply) == "package main"


def test_an_unfenced_reply_is_left_alone():
    assert source_code.strip_fence("package main\n") == "package main"


def test_the_references_go_in_a_comment_at_the_top(tmp_path):
    """何を根拠にしたかの記録はコードでも要る。

    文書と同じく、この一覧はコードが組み立てる。モデルに書かせると、渡して
    いないファイルを参照元として並べうる。
    """
    data, warnings = source_code.build(
        "package main", ["main.go", "ingest/store.py"], ["議事録.docx p.1"], ".go"
    )
    text = data.decode("utf-8")

    assert warnings == []
    assert text.startswith("// 参照したファイル\n")
    assert "// - main.go" in text
    assert "// - ingest/store.py" in text
    assert "// - 議事録.docx p.1" in text
    assert text.rstrip().endswith("package main")


def test_without_any_reference_no_comment_block_is_added():
    """空の見出しだけが先頭に残ると、読む人には何も伝わらない。"""
    text = source_code.build("package main", [], [], ".go")[0].decode("utf-8")

    assert "参照したファイル" not in text
    assert text.startswith("package main")


def test_build_strips_the_fence_too():
    """呼び出し元が2回に分けて覚えなくて済むようにする。"""
    text = source_code.build("```go\npackage main\n```", [], [], ".go")[0].decode("utf-8")

    assert text.startswith("package main")


def test_write_source_returns_what_the_model_wrote():
    result = source_code.write_source(
        "依頼", [], [], "", ".go", lambda prompt: "```go\npackage main\n```"
    )

    assert result == "```go\npackage main\n```"


def test_write_source_stops_before_calling_the_model_when_too_long():
    """呼んでから落ちると、利用者は30〜60秒待たされたうえで何も受け取れない。"""
    huge = [("巨大.md", "あ" * (filling.MAX_PROMPT_CHARS + 1))]

    with pytest.raises(filling.PromptTooLongError):
        source_code.write_source("依頼", [], huge, "", ".go", lambda prompt: "package main")
def test_python_and_powershell_are_offered_too():
    assert set(source_code.OUTPUT_SUFFIXES) == {".go", ".cs", ".py", ".ps1"}


def test_the_prompt_names_python_and_powershell():
    assert "Python" in source_code.build_prompt("依頼", [], [], "", ".py")
    assert "PowerShell" in source_code.build_prompt("依頼", [], [], "", ".ps1")


def test_the_reference_comment_uses_the_marker_of_each_language():
    """Python と PowerShell の行コメントは # である。// を入れると構文エラーになり、
    保存したファイルがそのままでは動かない。"""
    go = source_code.build("package main", ["main.go"], [], ".go")[0].decode("utf-8")
    cs = source_code.build("class P {}", ["main.go"], [], ".cs")[0].decode("utf-8")
    py = source_code.build("def main(): pass", ["main.go"], [], ".py")[0].decode("utf-8")
    ps1 = source_code.build("Write-Host 1", ["main.go"], [], ".ps1")[0].decode("utf-8")

    assert go.startswith("// 参照したファイル")
    assert cs.startswith("// 参照したファイル")
    assert py.startswith("# 参照したファイル")
    assert ps1.startswith("# 参照したファイル")
    assert "# - main.go" in py
    assert "// - main.go" in go
