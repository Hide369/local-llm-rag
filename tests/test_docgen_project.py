"""プロジェクトフォルダの走査・選択・読み取り・書き出し。

このモジュールの要点は2つある。LLM が返した文字列でファイルを読むこと（root の
外を拒む必要がある）と、自分の出力先を走査から外すこと（外さないと2回目から
自分が書いた設計書を根拠に設計書を書く）。
"""
from pathlib import Path

import pytest

from docgen import project
from ingest import chat


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


def test_a_python_project_folder_is_not_empty(tmp_path):
    """.py が対象から漏れていると、Python のプロジェクトを指定した回が
    「取り込める形式のファイルがありません」で止まる。

    実測 2026-09-15: このリポジトリの ingest/ docgen/ scripts/ はいずれも走査
    結果が0件だった。中身はすべて .py である。Cowork でプロジェクトフォルダを
    指定した利用者は、この画面のエラーだけを見て理由が分からなかった。
    """
    _write(tmp_path, "main.py", "def main():\n    pass\n")
    _write(tmp_path, "run.ps1", "Write-Host 'start'\n")

    assert [name for name, _ in project.tree(tmp_path)] == ["main.py", "run.ps1"]


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


def test_read_returns_the_body_of_each_selected_file(tmp_path):
    _write(tmp_path, "main.go", "package main\n")
    _write(tmp_path, "docs/設計.md", "# 設計\n\n本文\n")

    files, skipped = project.read(tmp_path, ["main.go", "docs/設計.md"])

    assert skipped == []
    assert files[0][0] == "main.go"
    assert "package main" in files[0][1]
    assert "本文" in files[1][1]


def test_read_stops_at_the_budget_and_names_what_it_dropped(tmp_path):
    """黙って捨てると、利用者は根拠が足りないまま書かれた文書を
    根拠があるものとして読む。"""
    _write(tmp_path, "大.md", "あ" * 200)
    _write(tmp_path, "小.md", "い" * 10)

    files, skipped = project.read(tmp_path, ["大.md", "小.md"], budget=100)

    assert [name for name, _ in files] == ["小.md"]
    assert skipped == ["大.md"]


def test_read_rejects_a_path_outside_the_root(tmp_path):
    """この経路は LLM が返した文字列でファイルを読む。

    docgen/templates.py の _checked と ingest/parsers/md_parser.py の _resolve が
    同じ理由で .. を拒んでいる。規則を揃える。
    """
    _write(tmp_path, "project/main.go", "package main\n")
    _write(tmp_path, "秘密.md", "外のファイル\n")

    files, skipped = project.read(tmp_path / "project", ["../秘密.md"])

    assert files == []
    assert skipped == ["../秘密.md"]


def test_read_rejects_an_absolute_path(tmp_path):
    _write(tmp_path, "project/main.go", "package main\n")
    outside = tmp_path / "秘密.md"
    outside.write_text("外のファイル\n", encoding="utf-8")

    files, skipped = project.read(tmp_path / "project", [str(outside)])

    assert files == []
    assert skipped == [str(outside)]


def test_read_skips_a_file_it_cannot_open_and_keeps_going(tmp_path):
    """1つ壊れているだけで生成ごと落とすと、残りの根拠まで失う。"""
    _write(tmp_path, "main.go", "package main\n")
    (tmp_path / "壊れた.xlsx").write_bytes(b"not a workbook")

    files, skipped = project.read(tmp_path, ["壊れた.xlsx", "main.go"])

    assert [name for name, _ in files] == ["main.go"]
    assert skipped == ["壊れた.xlsx"]


def test_read_skips_a_missing_path(tmp_path):
    """LLM は一覧に無いパスを返すことがある。"""
    _write(tmp_path, "main.go", "package main\n")

    files, skipped = project.read(tmp_path, ["存在しない.md"])

    assert files == []
    assert skipped == ["存在しない.md"]


def test_read_rejects_a_symlink_pointing_outside_the_root(tmp_path):
    """文字列で `..` を探す実装に戻されても、このテストだけが落ちる。

    Path.resolve() はシンボリックリンクの再解析ポイントを辿って、その先の
    絶対パスが root の下にあるか確認する。これが是非で最も価値の高い不変式である。
    """
    # シンボリックリンク作成を試みる。Windows で開発者モードがない環境では
    # OSError が出る。その場合、このテストは skip する。
    try:
        outside = tmp_path.parent / "外のファイル.md"
        outside.write_text("外のファイル\n", encoding="utf-8")
        symlink = tmp_path / "symlink.md"
        symlink.symlink_to(outside)
    except OSError as e:
        pytest.skip(f"シンボリックリンク作成不可: {e}")

    files, skipped = project.read(tmp_path, ["symlink.md"])

    assert files == []
    assert skipped == ["symlink.md"]


def test_select_returns_the_paths_the_model_chose():
    entries = [("main.go", 120), ("README.md", 800)]

    chosen = project.select(entries, "設計書を書いて", lambda prompt: '["main.go"]')

    assert chosen == ["main.go"]


def test_select_drops_paths_that_are_not_in_the_tree():
    """一覧に無いパスを返させない。read 側でも弾くが、ここで落とせば
    存在しないファイル名が「読まなかった」一覧に並ぶのを防げる。"""
    entries = [("main.go", 120)]

    chosen = project.select(entries, "依頼", lambda prompt: '["main.go", "/etc/passwd"]')

    assert chosen == ["main.go"]


def test_select_returns_nothing_when_the_json_is_broken():
    """止めない。ツリーだけでもファイル構成は伝わる。

    fill_values が壊れた JSON で止めず、query_translation が翻訳の失敗で原文に
    落ちるのと同じ考え方である。
    """
    entries = [("main.go", 120)]

    assert project.select(entries, "依頼", lambda prompt: "すみません、") == []


def test_select_returns_nothing_when_the_json_is_not_a_list():
    entries = [("main.go", 120)]

    assert project.select(entries, "依頼", lambda prompt: '{"file": "main.go"}') == []


def test_select_reraises_when_the_model_itself_fails():
    """LLM が落ちたことは利用者に伝えるべき失敗である。黙って空を返さない。"""
    def ask(prompt):
        raise chat.ChatError("Ollama に繋がりません")

    with pytest.raises(chat.ChatError):
        project.select([("main.go", 120)], "依頼", ask)


def test_select_puts_the_tree_and_the_request_in_the_prompt():
    seen = {}

    def ask(prompt):
        seen["prompt"] = prompt
        return "[]"

    project.select([("main.go", 120)], "設計書を書いて", ask)

    assert "main.go" in seen["prompt"]
    assert "設計書を書いて" in seen["prompt"]


def test_tree_text_shows_the_size_of_each_file():
    text, omitted = project.tree_text([("main.go", 120)])

    assert text == "- main.go (120 bytes)"
    assert omitted == 0


def test_tree_text_stays_unchanged_when_everything_fits_the_budget():
    """予算に収まる一覧は、末尾に何も足さない。"""
    entries = [(f"file{i}.go", 10) for i in range(5)]

    text, omitted = project.tree_text(entries, budget=10_000)

    assert omitted == 0
    assert "載せきれません" not in text


def test_tree_text_truncates_at_the_budget_and_names_the_exact_count_dropped():
    """一覧を無制限に載せると、このリポジトリのように一覧だけで
    MAX_PROMPT_CHARS を超え、雛形なしの生成が本文0件・検索結果0件のまま
    PromptTooLongError で止まる。落とした件数を正確に伝える。"""
    # 1行23文字（先頭以外は改行込みで24文字）になるよう桁数を揃える。
    entries = [(f"file{i:03d}.go", 10) for i in range(20)]

    text, omitted = project.tree_text(entries, budget=130)

    expected_lines = [f"- file{i:03d}.go (10 bytes)" for i in range(5)]
    expected_lines.append("- （ほか 15 件は一覧に載せきれませんでした）")
    assert text == "\n".join(expected_lines)
    assert omitted == 15


def test_write_output_creates_the_output_directory(tmp_path):
    written = project.write_output(tmp_path, "設計_2026-09-14.md", b"# \xe8\xa8\xad\xe8\xa8\x88")

    assert written == tmp_path / project.OUTPUT_DIR_NAME / "設計_2026-09-14.md"
    assert written.read_bytes() == b"# \xe8\xa8\xad\xe8\xa8\x88"


def test_write_output_never_overwrites(tmp_path):
    """ファイル名に日付が入っていても、同じ日に2回作れば衝突する。
    上書きすると1回目の成果物が黙って消える。"""
    first = project.write_output(tmp_path, "設計_2026-09-14.md", b"one")
    second = project.write_output(tmp_path, "設計_2026-09-14.md", b"two")
    third = project.write_output(tmp_path, "設計_2026-09-14.md", b"three")

    assert first.name == "設計_2026-09-14.md"
    assert second.name == "設計_2026-09-14_2.md"
    assert third.name == "設計_2026-09-14_3.md"
    assert first.read_bytes() == b"one"


def test_write_output_rejects_a_name_with_a_path_separator(tmp_path):
    """名前は画面が組み立てるが、利用者が触れる値を信じる形にはしない
    （docgen/templates.py の _checked と同じ理由）。"""
    with pytest.raises(ValueError):
        project.write_output(tmp_path, "../逃げる.md", b"x")
