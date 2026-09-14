"""プロジェクトフォルダの走査・選択・読み取り・書き出し。

このモジュールの要点は2つある。LLM が返した文字列でファイルを読むこと（root の
外を拒む必要がある）と、自分の出力先を走査から外すこと（外さないと2回目から
自分が書いた設計書を根拠に設計書を書く）。
"""
from pathlib import Path

import pytest

from docgen import project


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="")


def test_tree_lists_supported_files_with_their_size(tmp_path):
    _write(tmp_path, "main.go", "package main\n")
    _write(tmp_path, "docs/設計.md", "# 設計\n")

    assert project.tree(tmp_path) == [
        ("docs/設計.md", len("# 設計\n".encode("utf-8"))),
        ("main.go", len("package main\n".encode("utf-8"))),
    ]


def test_tree_skips_unsupported_suffixes(tmp_path):
    """取り込めない形式を並べても、LLM が選べるものが増えるわけではない。"""
    _write(tmp_path, "main.go", "package main\n")
    _write(tmp_path, "logo.svg", "<svg/>")

    assert [name for name, _ in project.tree(tmp_path)] == ["main.go"]


def test_tree_skips_hidden_and_generated_directories(tmp_path):
    """.git や __pycache__ の中身は書いた人の資料ではない。"""
    _write(tmp_path, "main.go", "package main\n")
    _write(tmp_path, ".git/config.json", "{}")
    _write(tmp_path, "__pycache__/x.json", "{}")
    _write(tmp_path, "node_modules/pkg/index.json", "{}")
    _write(tmp_path, "myvenv313/Lib/x.json", "{}")

    assert [name for name, _ in project.tree(tmp_path)] == ["main.go"]


def test_tree_skips_the_output_directory(tmp_path):
    """外さないと、2回目から自分が書いた設計書を根拠にして設計書を書く。

    1回目は正しく動き、例外も出ないので気づけない。ここで固定する。
    """
    _write(tmp_path, "main.go", "package main\n")
    _write(tmp_path, f"{project.OUTPUT_DIR_NAME}/設計_2026-09-14.md", "# 前回の出力\n")

    assert [name for name, _ in project.tree(tmp_path)] == ["main.go"]


def test_tree_rejects_a_path_that_is_not_a_directory(tmp_path):
    path = tmp_path / "main.go"
    path.write_text("package main\n", encoding="utf-8")

    with pytest.raises(project.ProjectFolderError):
        project.tree(path)


def test_tree_of_an_empty_folder_is_empty(tmp_path):
    """0件は異常ではない。呼び出し元が「対象がありません」と伝えられればよい。"""
    assert project.tree(tmp_path) == []
