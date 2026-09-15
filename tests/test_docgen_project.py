"""プロジェクトフォルダの走査・選択・読み取り・書き出し。

このモジュールの要点は2つある。LLM が返した文字列でファイルを読むこと（root の
外を拒む必要がある）と、自分の出力先を走査から外すこと（外さないと2回目から
自分が書いた設計書を根拠に設計書を書く）。
"""
import json
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

    files, skipped, _ = project.read(tmp_path, ["main.go", "docs/設計.md"])

    assert skipped == []
    assert files[0][0] == "main.go"
    assert "package main" in files[0][1]
    assert "本文" in files[1][1]


def test_read_stops_at_the_budget_and_names_what_it_dropped(tmp_path):
    """黙って捨てると、利用者は根拠が足りないまま書かれた文書を
    根拠があるものとして読む。"""
    _write(tmp_path, "大.md", "あ" * 200)
    _write(tmp_path, "小.md", "い" * 10)

    files, skipped, _ = project.read(tmp_path, ["大.md", "小.md"], budget=100)

    assert [name for name, _ in files] == ["小.md"]
    assert skipped == ["大.md"]


def test_read_rejects_a_path_outside_the_root(tmp_path):
    """この経路は LLM が返した文字列でファイルを読む。

    docgen/templates.py の _checked と ingest/parsers/md_parser.py の _resolve が
    同じ理由で .. を拒んでいる。規則を揃える。
    """
    _write(tmp_path, "project/main.go", "package main\n")
    _write(tmp_path, "秘密.md", "外のファイル\n")

    files, skipped, _ = project.read(tmp_path / "project", ["../秘密.md"])

    assert files == []
    assert skipped == ["../秘密.md"]


def test_read_rejects_an_absolute_path(tmp_path):
    _write(tmp_path, "project/main.go", "package main\n")
    outside = tmp_path / "秘密.md"
    outside.write_text("外のファイル\n", encoding="utf-8")

    files, skipped, _ = project.read(tmp_path / "project", [str(outside)])

    assert files == []
    assert skipped == [str(outside)]


def test_read_skips_a_file_it_cannot_open_and_keeps_going(tmp_path):
    """1つ壊れているだけで生成ごと落とすと、残りの根拠まで失う。"""
    _write(tmp_path, "main.go", "package main\n")
    (tmp_path / "壊れた.xlsx").write_bytes(b"not a workbook")

    files, skipped, _ = project.read(tmp_path, ["壊れた.xlsx", "main.go"])

    assert [name for name, _ in files] == ["main.go"]
    assert skipped == ["壊れた.xlsx"]


def test_read_skips_a_missing_path(tmp_path):
    """LLM は一覧に無いパスを返すことがある。"""
    _write(tmp_path, "main.go", "package main\n")

    files, skipped, _ = project.read(tmp_path, ["存在しない.md"])

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

    files, skipped, _ = project.read(tmp_path, ["symlink.md"])

    assert files == []
    assert skipped == ["symlink.md"]


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


def _fill(root: Path) -> None:
    """全部は予算に収まらない状況を作る。

    gather は「全部入るなら選ばせない」ため、ループを試すテストはこれを置いて
    入りきらない状態にする。読む対象そのものは小さいままにしておく。
    """
    _write(root, "かさ増し.md", "あ" * 500)


class _Model:
    """あらかじめ決めた返答を順に返す。道具の呼び出しは (名前, 引数) で書く。"""

    def __init__(self, replies):
        self._replies = list(replies)
        self.conversations = []

    def __call__(self, messages, tools):
        self.conversations.append(list(messages))
        if not self._replies:
            return {"role": "assistant", "content": "もう十分です"}
        reply = self._replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        if isinstance(reply, str):
            return {"role": "assistant", "content": reply}
        return {
            "role": "assistant",
            "tool_calls": [
                {"function": {"name": "read_files", "arguments": arguments}}
                for arguments in reply
            ],
        }


def test_gather_reads_what_the_model_asked_for(tmp_path):
    _write(tmp_path, "main.go", "package main")
    _fill(tmp_path)
    entries = project.tree(tmp_path)
    model = _Model([[{"paths": ["main.go"]}], "書けます"])

    files, skipped, _ = project.gather(tmp_path, entries, "設計書を書いて", model, budget=200)

    assert [name for name, _ in files] == ["main.go"]
    assert skipped == []


def test_gather_lets_the_model_ask_for_more_after_reading(tmp_path):
    """1回で選ばせる形では、読んでみて初めて要ると分かったファイルを取れない。

    これがこの機能の理由そのものである。
    """
    _write(tmp_path, "main.go", "package main")
    _write(tmp_path, "store.go", "package main")
    _fill(tmp_path)
    entries = project.tree(tmp_path)
    model = _Model([[{"paths": ["main.go"]}], [{"paths": ["store.go"]}], "書けます"])

    files, _, _ = project.gather(tmp_path, entries, "設計書を書いて", model, budget=200)

    assert [name for name, _ in files] == ["main.go", "store.go"]


def test_gather_does_not_stop_when_the_model_never_asks(tmp_path):
    """道具を呼ばないモデルでも止まらない。

    以前はここで0件を返し、成果物はファイル一覧だけを根拠に書かれていた。
    今は代わりに読む（test_gather_falls_back_to_reading_in_listing_order_when_nothing_was_chosen）。
    """
    _write(tmp_path, "main.go", "package main")
    _fill(tmp_path)
    entries = project.tree(tmp_path)

    files, _, _ = project.gather(tmp_path, entries, "依頼", _Model(["読みません"]), budget=200)

    assert "main.go" in [name for name, _ in files]


def test_gather_shares_one_budget_across_every_round(tmp_path):
    """周ごとに予算を配ると、3周で上限の3倍をプロンプトへ積むことになる。

    ループの履歴にはファイル本文がそのまま残るため、合計で抑えないと
    プロンプト上限（28,000字）を超える。
    """
    _write(tmp_path, "大.md", "あ" * 80)
    _write(tmp_path, "小.md", "い" * 80)
    entries = project.tree(tmp_path)
    model = _Model([[{"paths": ["大.md"]}], [{"paths": ["小.md"]}], "書けます"])

    files, skipped, _ = project.gather(tmp_path, entries, "依頼", model, budget=100)

    assert [name for name, _ in files] == ["大.md"]
    assert skipped == ["小.md"]


def test_gather_stops_after_the_round_limit(tmp_path):
    """道具を呼び続けるモデルで無限に回らない。"""
    _write(tmp_path, "main.go", "package main")
    _write(tmp_path, "a.go", "package main")
    _write(tmp_path, "b.go", "package main")
    _write(tmp_path, "c.go", "package main")
    _fill(tmp_path)
    entries = project.tree(tmp_path)
    model = _Model([[{"paths": [name]}] for name in ("main.go", "a.go", "b.go", "c.go")])

    project.gather(tmp_path, entries, "依頼", model, budget=200)

    assert len(model.conversations) == project.MAX_ROUNDS


def test_gather_refuses_a_path_outside_the_root(tmp_path):
    """道具の引数はモデルが書いた文字列である。read の検査をそのまま通す。

    root の外を要求した回は、そのパスが skipped に入り、中身はどの経路からも
    渡らない。読めたものが0件になるため代わりに読む経路へ進むが、そちらが
    読むのは走査済みの一覧（root の中）だけである。
    """
    _write(tmp_path, "project/main.go", "package main")
    _write(tmp_path, "秘密.md", "外のファイル")
    root = tmp_path / "project"
    _fill(root)
    entries = project.tree(root)
    model = _Model([[{"paths": ["../秘密.md"]}], "書けます"])

    files, skipped, _ = project.gather(root, entries, "依頼", model, budget=200)

    assert "../秘密.md" in skipped
    assert "../秘密.md" not in [name for name, _ in files]
    assert not any("外のファイル" in text for _, text in files)


def test_gather_does_not_read_the_same_file_twice(tmp_path):
    """同じファイルを2度読むと、予算を二重に使ったうえで履歴も膨らむ。"""
    _write(tmp_path, "main.go", "package main")
    _fill(tmp_path)
    entries = project.tree(tmp_path)
    model = _Model([[{"paths": ["main.go"]}], [{"paths": ["main.go"]}], "書けます"])

    files, _, _ = project.gather(tmp_path, entries, "依頼", model, budget=200)

    assert [name for name, _ in files] == ["main.go"]


def test_gather_accepts_arguments_that_arrive_as_a_json_string(tmp_path):
    """引数を辞書で返すモデルと文字列で返すモデルがある。"""
    _write(tmp_path, "main.go", "package main")
    _fill(tmp_path)
    entries = project.tree(tmp_path)
    model = _Model([['{"paths": ["main.go"]}'], "書けます"])
    model._replies[0] = [json.dumps({"paths": ["main.go"]})]

    files, _, _ = project.gather(tmp_path, entries, "依頼", model, budget=200)

    assert [name for name, _ in files] == ["main.go"]


def test_gather_reraises_when_the_model_itself_fails(tmp_path):
    """LLM が落ちたことは利用者に伝えるべき失敗である。"""
    _write(tmp_path, "main.go", "package main")
    _fill(tmp_path)
    entries = project.tree(tmp_path)

    with pytest.raises(chat.ChatError):
        project.gather(tmp_path, entries, "依頼", _Model([chat.ChatError("落ちた")]), budget=200)


def test_the_opening_message_shows_the_listing_and_the_request(tmp_path):
    _write(tmp_path, "main.go", "package main")
    _fill(tmp_path)
    entries = project.tree(tmp_path)
    model = _Model(["読みません"])

    project.gather(tmp_path, entries, "設計書を書いて", model, budget=200)

    opening = model.conversations[0][0]["content"]
    assert "main.go" in opening
    assert "設計書を書いて" in opening


def test_gather_reads_everything_without_asking_when_it_all_fits(tmp_path):
    """全部が予算に収まるなら、選ばせる意味がない。

    実測 2026-09-15: gpt-oss:20b は read_files を1度も呼ばず、警告だけが毎回
    出ていた。入るものを入れるのにモデルの協力を要求しない。LLM 呼び出しも
    1回減る。
    """
    _write(tmp_path, "main.go", "package main")
    _write(tmp_path, "store.go", "package main")
    entries = project.tree(tmp_path)

    def must_not_be_called(messages, tools):
        raise AssertionError("全部入るのにモデルへ選択を頼んだ")

    files, skipped, _ = project.gather(tmp_path, entries, "依頼", must_not_be_called)

    assert [name for name, _ in files] == ["main.go", "store.go"]
    assert skipped == []


def test_gather_still_asks_when_the_folder_does_not_fit(tmp_path):
    """入りきらないときだけ選ばせる。ここが往復の存在理由である。"""
    _write(tmp_path, "大.md", "あ" * 200)
    _write(tmp_path, "小.md", "い" * 10)
    entries = project.tree(tmp_path)
    model = _Model([[{"paths": ["小.md"]}], "書けます"])

    files, _, _ = project.gather(tmp_path, entries, "依頼", model, budget=100)

    assert [name for name, _ in files] == ["小.md"]
    assert model.conversations, "入りきらないのにモデルへ聞いていない"


def test_gather_falls_back_to_reading_in_listing_order_when_nothing_was_chosen(tmp_path):
    """モデルが1ファイルも読まなかった回に、こちらで読む。

    実測 2026-09-15: gpt-oss:20b は read_files を1度も呼ばず、成果物は毎回
    ファイル一覧だけを根拠に書かれていた。選び方の精度は落ちても、0件よりは
    確実によい。何を読んだかは成果物の「参照したファイル」に出る。

    順は一覧と同じ（パスの昇順）。小さい順だと些末なファイルで予算が埋まり、
    大きい順だと1本で使い切る。
    """
    _write(tmp_path, "a.go", "package a")
    _write(tmp_path, "b.go", "package b")
    _fill(tmp_path)

    files, _, _ = project.gather(
        tmp_path, project.tree(tmp_path), "依頼", _Model(["読みません"]), budget=200
    )

    assert [name for name, _ in files] == ["a.go", "b.go"]


def test_the_fallback_respects_the_budget(tmp_path):
    """代わりに読むといっても、上限は同じである。"""
    _write(tmp_path, "a.md", "あ" * 80)
    _write(tmp_path, "b.md", "い" * 80)
    _fill(tmp_path)

    files, skipped, _ = project.gather(
        tmp_path, project.tree(tmp_path), "依頼", _Model(["読みません"]), budget=100
    )

    assert [name for name, _ in files] == ["a.md"]
    assert "b.md" in skipped


def test_no_fallback_when_the_model_did_read_something(tmp_path):
    """1つでも読めていれば、モデルの選択を尊重する。勝手に足さない。"""
    _write(tmp_path, "a.go", "package a")
    _write(tmp_path, "b.go", "package b")
    _fill(tmp_path)
    model = _Model([[{"paths": ["b.go"]}], "書けます"])

    files, _, _ = project.gather(tmp_path, project.tree(tmp_path), "依頼", model, budget=200)

    assert [name for name, _ in files] == ["b.go"]


def test_a_file_larger_than_the_budget_is_read_from_the_top(tmp_path):
    """丸ごと捨てると、そのファイルは1文字も根拠に入らない。

    実測 2026-09-15（このリポジトリ）: 予算16,000字を超えるファイルが
    docs/ で58件中37件、ingest/ で32件中2件（retrieval.py と
    vector_store.py）あった。説明が要るファイルほど大きく、丸ごと落ちていた。
    先頭には概要（モジュールのdocstring・見出し・import）があり、何も無いより
    はるかによい。
    """
    _write(tmp_path, "大.md", "あ" * 20000)

    files, skipped, truncated = project.read(tmp_path, ["大.md"], budget=8000)

    assert skipped == []
    assert truncated == ["大.md"]
    assert len(files[0][1]) == 4000  # 残り8,000の半分


def test_a_truncated_file_still_leaves_room_for_the_next_one(tmp_path):
    """大きいファイルが1つ先頭にあるだけで、後ろのファイルを捨てない。

    予算いっぱいまで読ませるとこの性質が壊れる。1ファイルに渡すのは残りの
    半分までとし、何件続いても必ず次の分が残るようにしてある。
    """
    _write(tmp_path, "1大.md", "あ" * 20000)
    _write(tmp_path, "2小.md", "小さい本文")

    files, skipped, truncated = project.read(
        tmp_path, ["1大.md", "2小.md"], budget=8000
    )

    assert [name for name, _ in files] == ["1大.md", "2小.md"]
    assert skipped == []


def test_a_head_too_short_to_say_anything_is_not_read(tmp_path):
    """切れ端は本文の役に立たず、「参照したファイル」に名前が並ぶ分だけ誤解を招く。"""
    _write(tmp_path, "大.md", "あ" * 20000)

    files, skipped, truncated = project.read(tmp_path, ["大.md"], budget=1500)

    assert files == []
    assert skipped == ["大.md"]
    assert truncated == []


def test_the_tool_reply_tells_the_model_a_file_was_cut():
    """伝えないと、モデルは全文を読んだつもりで書く。"""
    reply = project._tool_reply([("大.md", "先頭だけ")], [], ["大.md"])

    assert "大.md" in reply
    assert "先頭" in reply
