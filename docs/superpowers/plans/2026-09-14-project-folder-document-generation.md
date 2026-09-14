# プロジェクトフォルダからの文書生成 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cowork でプロジェクトフォルダを資料源に指定し、雛形なしで md / docx / xlsx / pptx を生成して、そのフォルダの `generated_docs/` に書き出せるようにする。

**Architecture:** フォルダの中身は「ツリーを LLM に見せて選ばせ、選ばれたファイルを丸ごと渡す」。プロンプト上限 28,000字に対しこのリポジトリは 4,188,651字あり、選別は前提である。選ばれた本文は `filling.fill_values` が既に受けている `(名前, 本文)` の形に乗るので、雛形ありの経路は変えずに済む。雛形なしの生成は Markdown を1回書かせ、共通の中間構造に解析してから4形式へ組む。

**Tech Stack:** Python 3.13 / Streamlit 1.61.1 / python-docx 1.2.0 / openpyxl 3.1.5 / python-pptx 1.0.2 / pytest 9.1.1。**新しい依存は足さない。**

**Spec:** [docs/superpowers/specs/2026-09-14-project-folder-document-generation-design.md](../specs/2026-09-14-project-folder-document-generation-design.md)

## Global Constraints

- **仮想環境とテストの実行:** `./myvenv313/Scripts/python.exe -m pytest ...`（PowerShell でもこのパスで動く）
- **新しい依存を足さない。** `requirements.txt` は変更しない
- **コメントは「なぜ」を書く。** 「何を」はコードで表す。既存モジュールの docstring の密度に合わせる
- **`ask` は引数で受け取る。** モジュール内で Ollama クライアントに束縛しない（`docgen/filling.py` `ingest/conditions.py` と同じ）
- **画面は `st.session_state.cowork_result` に積む。** `st.error` / `st.download_button` を生成処理の中で直接呼ばない（`generating` を戻す `st.rerun()` が同じ実行の描画ごと消すため）
- **プロンプト上限:** `docgen.filling.MAX_PROMPT_CHARS = 28000`。雛形なしの経路もこれを使う
- **除外ディレクトリと出力先ディレクトリは `docgen/project.py` の定数1組。** 片方だけ変わると自分の出力を根拠に読み始める
- 各タスクは `git commit` で終える。コミットメッセージは英語のコンベンショナルコミット

## 仕様からの1点の具体化

仕様書5節は `tree(root)` が「パスと**文字数**」を返すと書いている。実装は
**バイト数**（`path.stat().st_size`）を使う。文字数を出すには全ファイルを
`parse` する必要があり、PDF や docx が混ざったフォルダでは走査だけで数十秒
かかる。ツリーは LLM が「どれが要るか」を判断するための目安であり、その用途に
バイト数で足りる。

## File Structure

| ファイル | 責務 |
|---|---|
| `ingest/chat.py` | **変更。** 平文を返す `ask_text` を足す |
| `docgen/project.py` | **新規。** フォルダの走査・選択・読み取り・書き出し。除外と出力先の定数を持つ唯一の場所 |
| `docgen/markdown_document.py` | **新規。** Markdown を中間構造へ解析し、4形式へ組む |
| `docgen/freeform.py` | **新規。** 雛形なしのプロンプトを組み、Markdown を受け取る |
| `rag_chat_app.py` | **変更。** 雛形なしの選択・出力形式・フォルダのパス入力・書き出しの配線 |
| `tests/test_chat.py` | **変更。** `ask_text` |
| `tests/test_docgen_project.py` | **新規** |
| `tests/test_docgen_markdown_document.py` | **新規** |
| `tests/test_docgen_freeform.py` | **新規** |
| `tests/test_rag_chat_app_cowork.py` | **変更。** 画面の追加分 |
| `README.md` | **変更。** 使い方と既知の制約 |

## タスクの並び

タスク1〜5でプロジェクトフォルダが**雛形ありの経路で使えるようになる**（タスク13の前半）。
タスク6〜11で雛形なしの生成が揃う。タスク12〜13が画面である。

---

### Task 1: `ingest/chat.py` に `ask_text` を足す

**Files:**
- Modify: `ingest/chat.py`
- Test: `tests/test_chat.py`

**Interfaces:**
- Consumes: なし
- Produces: `chat.ask_text(model: str, prompt: str, session=None, num_ctx: int = NUM_CTX) -> str`

`ask_json` は `format: "json"` を固定で送る。数千字の Markdown を JSON 文字列に
押し込むと、改行・引用符・バックスラッシュのエスケープで壊れやすい。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_chat.py` の末尾に足す。既存のテストがどう `requests` を差し替えて
いるかを先に読み、同じやり方に合わせること。合っていなければ以下をその形へ直す。

```python
def test_ask_text_does_not_ask_for_json(monkeypatch):
    """format: json を送ると、モデルは長い Markdown を JSON 文字列へ押し込もうと
    して、改行と引用符のエスケープで壊れる。"""
    sent = {}

    class _Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"message": {"content": "# 設計書\n\n本文"}}

    class _Session:
        def post(self, url, json, timeout):
            sent.update(json)
            return _Response()

        def close(self):
            pass

    monkeypatch.setattr(chat, "new_session", _Session)

    result = chat.ask_text("qwen3:32b", "設計書を書いて")

    assert result == "# 設計書\n\n本文"
    assert "format" not in sent


def test_ask_text_leaves_temperature_to_the_model(monkeypatch):
    """temperature=0 は条件抽出の再現性のための値である。文章生成にその要求はない。"""
    sent = {}

    class _Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"message": {"content": "本文"}}

    class _Session:
        def post(self, url, json, timeout):
            sent.update(json)
            return _Response()

        def close(self):
            pass

    monkeypatch.setattr(chat, "new_session", _Session)

    chat.ask_text("qwen3:32b", "依頼")

    assert "temperature" not in sent["options"]
    assert sent["options"]["num_ctx"] == chat.NUM_CTX
```

- [ ] **Step 2: テストが落ちることを確認する**

```
./myvenv313/Scripts/python.exe -m pytest tests/test_chat.py -q -k ask_text
```

Expected: FAIL（`AttributeError: module 'ingest.chat' has no attribute 'ask_text'`）

- [ ] **Step 3: 最小の実装を書く**

`ingest/chat.py` の `ask_json` の直後に足す。再試行とタイムアウトの扱いは
`ask_json` と同じにする。

```python
def ask_text(model: str, prompt: str, session=None, num_ctx: int = NUM_CTX) -> str:
    """平文をそのまま返させる。文書生成用。

    ask_json と違って format を送らない。数千字の Markdown を JSON 文字列へ
    押し込ませると、改行・引用符・バックスラッシュのエスケープで壊れる。

    temperature も送らない。ask_json が 0 を固定するのは条件抽出で答えが揺れると
    再現性のない誤りになるためで、文章生成にその要求はない。
    """
    own_session = session is None
    session = session or new_session()
    try:
        url = f"{OLLAMA_HOST}/api/chat"
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "keep_alive": "30m",
            "options": {"num_ctx": num_ctx},
        }
        last_error = None
        for attempt in range(_MAX_ATTEMPTS):
            try:
                response = session.post(url, json=payload, timeout=_TIMEOUT)
                response.raise_for_status()
                return response.json()["message"]["content"]
            except (requests.RequestException, KeyError, ValueError) as error:
                last_error = error
                if attempt < _MAX_ATTEMPTS - 1:
                    time.sleep(2**attempt)
        raise ChatError(
            f"{OLLAMA_HOST} への生成リクエストが{_MAX_ATTEMPTS}回失敗しました: {last_error}"
        )
    finally:
        if own_session:
            session.close()
```

- [ ] **Step 4: テストが通ることを確認する**

```
./myvenv313/Scripts/python.exe -m pytest tests/test_chat.py -q
```

Expected: PASS（既存のテストも含めて）

- [ ] **Step 5: コミット**

```bash
git add ingest/chat.py tests/test_chat.py
git commit -m "feat: add ask_text for plain-text generation"
```

---

### Task 2: `docgen/project.py` — フォルダの走査（`tree`）

**Files:**
- Create: `docgen/project.py`
- Test: `tests/test_docgen_project.py`

**Interfaces:**
- Consumes: `ingest.parsers.SUPPORTED_SUFFIXES`
- Produces:
  - `project.EXCLUDED_DIR_NAMES: frozenset[str]`
  - `project.OUTPUT_DIR_NAME: str`（`"generated_docs"`）
  - `project.PROJECT_BUDGET_CHARS: int`（`16000`）
  - `project.ProjectFolderError(Exception)`
  - `project.tree(root: Path) -> list[tuple[str, int]]`（`(POSIX形式の相対パス, バイト数)`、パスの昇順）

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_docgen_project.py` を新規作成。

```python
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
    path.write_text(text, encoding="utf-8")


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
```

- [ ] **Step 2: テストが落ちることを確認する**

```
./myvenv313/Scripts/python.exe -m pytest tests/test_docgen_project.py -q
```

Expected: FAIL（`ModuleNotFoundError: No module named 'docgen.project'`）

- [ ] **Step 3: 最小の実装を書く**

`docgen/project.py` を新規作成。

```python
"""プロジェクトフォルダを資料源として扱う。

走査して一覧を作り、依頼に要るファイルを選ばせ、本文を読み、成果物を書き戻す。

除外する名前（EXCLUDED_DIR_NAMES）と書き出し先（OUTPUT_DIR_NAME）を同じ場所に
置いているのは、この2つが必ず同時に動かなければならないためである。書き出し先を
走査から外し忘れると、1回目は正しく動き、2回目から自分が書いた文書を根拠にして
次の文書を書く。例外は出ないので気づけない。
"""
from pathlib import Path

from ingest.parsers import SUPPORTED_SUFFIXES

# このシステム自身の出力先。走査から外す（モジュールdocstring参照）。
OUTPUT_DIR_NAME = "generated_docs"

# 隠しディレクトリ（.git .venv .pytest_cache 等）は名前の規則で一括して落とすので
# ここには挙げない。ここに挙げるのは、隠しでない生成物・依存物である。
EXCLUDED_DIR_NAMES = frozenset(
    {OUTPUT_DIR_NAME, "__pycache__", "node_modules", "venv", ".venv"}
)

# 仮想環境のディレクトリ名は決まっていない（myvenv / myvenv313 / .venv など）。
# 前方一致で落とす。
EXCLUDED_DIR_PREFIXES = ("myvenv", "venv")

# プロンプトへ載せるプロジェクト本文の上限。filling.MAX_PROMPT_CHARS(28,000)の
# うち、検索結果・添付・依頼文・指示文に残す分を引いた値である。ここを超える分は
# 落とし、落とした名前を呼び出し元へ返す。
PROJECT_BUDGET_CHARS = 16000


class ProjectFolderError(Exception):
    """指定されたパスをプロジェクトフォルダとして扱えない。"""


def _excluded(name: str) -> bool:
    return (
        name.startswith(".")
        or name in EXCLUDED_DIR_NAMES
        or name.startswith(EXCLUDED_DIR_PREFIXES)
    )


def tree(root: Path) -> list[tuple[str, int]]:
    """`(相対パス, バイト数)` をパスの昇順で返す。

    大きさに文字数ではなくバイト数を使うのは、文字数を出すには全ファイルを
    parse する必要があり、PDF や docx が混ざったフォルダでは走査だけで数十秒
    かかるためである。この一覧は LLM が「どれが要るか」を判断するための目安で
    あり、その用途にはバイト数で足りる。
    """
    if not root.is_dir():
        raise ProjectFolderError(f"フォルダではありません: {root}")
    found = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(_excluded(part) for part in relative.parts[:-1]):
            continue
        if path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        found.append((relative.as_posix(), path.stat().st_size))
    return sorted(found)
```

- [ ] **Step 4: テストが通ることを確認する**

```
./myvenv313/Scripts/python.exe -m pytest tests/test_docgen_project.py -q
```

Expected: PASS（6件）

- [ ] **Step 5: コミット**

```bash
git add docgen/project.py tests/test_docgen_project.py
git commit -m "feat: scan a project folder, excluding its own output"
```

---

### Task 2 note: 隠しファイル

`_excluded` は `relative.parts[:-1]`（ディレクトリ部分）にしか当てない。
`.env` のような隠し**ファイル**は拡張子が `SUPPORTED_SUFFIXES` に無いので
自然に落ちる。拡張子で落ちる以上、名前でも落とす二重の規則は足さない。

---

### Task 3: `docgen/project.py` — 本文の読み取りと予算（`read`）

**Files:**
- Modify: `docgen/project.py`
- Test: `tests/test_docgen_project.py`

**Interfaces:**
- Consumes: `project.tree`、`project.PROJECT_BUDGET_CHARS`、`ingest.parsers.parse`
- Produces: `project.read(root: Path, paths: list[str], budget: int = PROJECT_BUDGET_CHARS) -> tuple[list[tuple[str, str]], list[str]]`
  - 1つ目: `(相対パス, 本文)` の並び。`filling.fill_values` の `attachments` にそのまま渡せる形
  - 2つ目: 読まなかったファイル名の並び（予算超過・パス不正・開けなかったもの）

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_docgen_project.py` に足す。

```python
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
```

- [ ] **Step 2: テストが落ちることを確認する**

```
./myvenv313/Scripts/python.exe -m pytest tests/test_docgen_project.py -q -k read
```

Expected: FAIL（`AttributeError: module 'docgen.project' has no attribute 'read'`）

- [ ] **Step 3: 最小の実装を書く**

`docgen/project.py` に足す。冒頭の import に `from ingest.parsers import SUPPORTED_SUFFIXES, parse` を加える。

```python
def _resolved(root: Path, relative: str) -> Path | None:
    """root の下にある実在のファイルなら絶対パスを、そうでなければ None を返す。

    判定は解決後の絶対パスが root の下にあることで行う。文字列に '..' が含まれるか
    で見ると、シンボリックリンクで外へ出る経路を見逃す。
    """
    root = root.resolve()
    try:
        candidate = (root / relative).resolve()
    except OSError:
        return None
    if not candidate.is_relative_to(root):
        return None
    return candidate if candidate.is_file() else None


def read(
    root: Path, paths: list[str], budget: int = PROJECT_BUDGET_CHARS
) -> tuple[list[tuple[str, str]], list[str]]:
    """選ばれたファイルの本文を、予算の範囲で読む。

    返り値の1つ目は (相対パス, 本文) の並びで、filling.fill_values の attachments に
    そのまま渡せる形である。プロジェクトフォルダは「添付の自動版」であり、専用の
    受け口を作らない。

    2つ目は読まなかったファイル名の並びである。予算で溢れたもの、root の外を
    指していたもの、開けなかったものをすべて含む。呼び出し元が画面で伝える。

    予算で溢れたファイルは飛ばして次へ進む（そこで打ち切らない）。大きいファイルが
    1つ先頭にあるだけで、後ろの小さいファイルまで捨てる理由がない。
    """
    files: list[tuple[str, str]] = []
    skipped: list[str] = []
    used = 0
    for relative in paths:
        path = _resolved(root, relative)
        if path is None:
            skipped.append(relative)
            continue
        try:
            units = parse(path)
        except Exception:
            # 壊れたファイル1つで生成ごと落とすと、残りの根拠まで失う。
            skipped.append(relative)
            continue
        text = "\n".join(unit.text for unit in units).strip()
        if not text or used + len(text) > budget:
            skipped.append(relative)
            continue
        files.append((relative, text))
        used += len(text)
    return files, skipped
```

- [ ] **Step 4: テストが通ることを確認する**

```
./myvenv313/Scripts/python.exe -m pytest tests/test_docgen_project.py -q
```

Expected: PASS（12件）

- [ ] **Step 5: コミット**

```bash
git add docgen/project.py tests/test_docgen_project.py
git commit -m "feat: read selected project files within a character budget"
```

---

### Task 4: `docgen/project.py` — ファイル選択（`select`）

**Files:**
- Modify: `docgen/project.py`
- Test: `tests/test_docgen_project.py`

**Interfaces:**
- Consumes: `project.tree` の返り値
- Produces:
  - `project.tree_text(entries: list[tuple[str, int]]) -> str`（プロンプトに載せる形）
  - `project.select(entries: list[tuple[str, int]], question: str, ask) -> list[str]`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_docgen_project.py` に足す。

```python
from ingest import chat


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
    assert project.tree_text([("main.go", 120)]) == "- main.go (120 bytes)"
```

- [ ] **Step 2: テストが落ちることを確認する**

```
./myvenv313/Scripts/python.exe -m pytest tests/test_docgen_project.py -q -k "select or tree_text"
```

Expected: FAIL（`AttributeError: module 'docgen.project' has no attribute 'tree_text'`）

- [ ] **Step 3: 最小の実装を書く**

`docgen/project.py` に足す。冒頭に `import json` を加える。

```python
def tree_text(entries: list[tuple[str, int]]) -> str:
    """ツリーをプロンプトに載せる形にする。"""
    return "\n".join(f"- {name} ({size} bytes)" for name, size in entries)


def build_selection_prompt(entries: list[tuple[str, int]], question: str) -> str:
    return (
        "あなたは社内文書を作成する担当者です。\n"
        "次の依頼に答えるために、どのファイルの中身を読む必要があるかを選んで"
        "ください。\n\n"
        f"## 依頼\n{question}\n\n"
        f"## ファイル一覧\n{tree_text(entries)}\n\n"
        "読むべきファイルのパスだけを、JSONの配列で返してください。"
        "説明や前置きは書かないでください。\n"
        "一覧に無いパスは返さないでください。\n"
        "依頼に関係のないファイルは選ばないでください。"
        "多く選ぶほど1つあたりに割ける分量が減ります。\n"
    )


def select(entries: list[tuple[str, int]], question: str, ask) -> list[str]:
    """読むべきファイルの相対パスを返す。決まらなければ空を返す。

    壊れた JSON が返っても例外は投げない。止めるとツリーすら渡せず、利用者は
    何も受け取れない。ツリーだけでもファイル構成は伝わる（fill_values が壊れた
    JSON で止めず、ingest/query_translation.py が翻訳の失敗で原文に落ちるのと
    同じ考え方）。

    ask が投げる ChatError は投げ直す。LLM そのものが落ちたことは利用者に伝える
    べき失敗であり、黙って「選択なし」にしてはいけない。
    """
    raw = ask(build_selection_prompt(entries, question))
    try:
        loaded = json.loads(raw)
    except (TypeError, ValueError):
        return []
    if not isinstance(loaded, list):
        return []
    known = {name for name, _ in entries}
    return [name for name in loaded if isinstance(name, str) and name in known]
```

- [ ] **Step 4: テストが通ることを確認する**

```
./myvenv313/Scripts/python.exe -m pytest tests/test_docgen_project.py -q
```

Expected: PASS（19件）

- [ ] **Step 5: コミット**

```bash
git add docgen/project.py tests/test_docgen_project.py
git commit -m "feat: let the model choose which project files to read"
```

---

### Task 5: `docgen/project.py` — 成果物の書き出し（`write_output`）

**Files:**
- Modify: `docgen/project.py`
- Test: `tests/test_docgen_project.py`

**Interfaces:**
- Consumes: `project.OUTPUT_DIR_NAME`
- Produces: `project.write_output(root: Path, file_name: str, data: bytes) -> Path`

- [ ] **Step 1: 失敗するテストを書く**

```python
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
```

- [ ] **Step 2: テストが落ちることを確認する**

```
./myvenv313/Scripts/python.exe -m pytest tests/test_docgen_project.py -q -k write_output
```

Expected: FAIL（`AttributeError: module 'docgen.project' has no attribute 'write_output'`）

- [ ] **Step 3: 最小の実装を書く**

```python
def write_output(root: Path, file_name: str, data: bytes) -> Path:
    """成果物を <root>/generated_docs/ に書き、置いた場所を返す。

    既存のファイルは上書きしない。ファイル名に日付が入っていても同じ日に2回
    作れば衝突し、上書きすると1回目の成果物が黙って消える。

    このフォルダは走査から外れている（EXCLUDED_DIR_NAMES）。外れていないと、
    2回目から自分が書いた文書を根拠にして次の文書を書く。
    """
    if file_name != Path(file_name).name or file_name in ("", ".", ".."):
        raise ValueError(f"成果物の名前はファイル名でなければなりません: {file_name}")
    directory = root / OUTPUT_DIR_NAME
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / file_name
    stem, suffix = destination.stem, destination.suffix
    serial = 2
    while destination.exists():
        destination = directory / f"{stem}_{serial}{suffix}"
        serial += 1
    destination.write_bytes(data)
    return destination
```

- [ ] **Step 4: テストが通ることを確認する**

```
./myvenv313/Scripts/python.exe -m pytest tests/test_docgen_project.py -q
```

Expected: PASS（22件）

- [ ] **Step 5: コミット**

```bash
git add docgen/project.py tests/test_docgen_project.py
git commit -m "feat: write generated documents into the project folder"
```

---

### Task 6: `docgen/markdown_document.py` — Markdown の解析

**Files:**
- Create: `docgen/markdown_document.py`
- Test: `tests/test_docgen_markdown_document.py`

**Interfaces:**
- Consumes: なし
- Produces（以降のタスクが全部使う）:
  - `Heading(level: int, text: str)`
  - `Paragraph(text: str)`
  - `Bullets(items: list[str])`
  - `Table(header: list[str], rows: list[list[str]])`
  - `Code(text: str)`
  - `Diagram(source: str)`
  - `References(paths: list[str], citations: list[str])`
  - `markdown_document.parse(text: str) -> list[Block]`

`References` はここでは作られない。タスク7以降で呼び出し元が末尾に足す。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_docgen_markdown_document.py` を新規作成。

```python
"""Markdown を中間構造へ解析し、4形式へ組む。

Markdown を一度だけ解析して共通の構造にするのは、形式ごとに読み直すと記法の
解釈が4箇所に分かれるためである。
"""
from docgen import markdown_document as md


def test_headings_keep_their_level():
    blocks = md.parse("# 設計書\n\n## 構成\n")

    assert blocks == [md.Heading(1, "設計書"), md.Heading(2, "構成")]


def test_consecutive_lines_become_one_paragraph():
    """Markdown では空行が段落の区切りである。改行1つで切ると、
    折り返しただけの文が別々の段落になる。"""
    blocks = md.parse("これは1つの\n段落である。\n\n次の段落。\n")

    assert blocks == [md.Paragraph("これは1つの 段落である。"), md.Paragraph("次の段落。")]


def test_bullets_are_collected_into_one_block():
    blocks = md.parse("- 一つ目\n- 二つ目\n")

    assert blocks == [md.Bullets(["一つ目", "二つ目"])]


def test_numbered_lists_are_bullets_too():
    """番号付きも箇条書きとして扱う。docx と pptx で番号を復元する価値より、
    2種類を持ち回る複雑さのほうが大きい。"""
    blocks = md.parse("1. 一つ目\n2. 二つ目\n")

    assert blocks == [md.Bullets(["一つ目", "二つ目"])]


def test_a_table_keeps_its_header_and_rows():
    text = "| 区分 | 日数 |\n| --- | --- |\n| 6か月 | 10日 |\n"

    blocks = md.parse(text)

    assert blocks == [md.Table(["区分", "日数"], [["6か月", "10日"]])]


def test_a_fenced_block_is_code():
    blocks = md.parse("```python\nprint(1)\n```\n")

    assert blocks == [md.Code("print(1)")]


def test_a_mermaid_fence_is_a_diagram():
    """図として描ける可能性があるものを、ただのコードと区別する。"""
    blocks = md.parse("```mermaid\ngraph TD\nA-->B\n```\n")

    assert blocks == [md.Diagram("graph TD\nA-->B")]


def test_a_heading_inside_a_fence_is_not_a_heading():
    """コード例の中の # を見出しにすると、文書の構造が崩れる。"""
    blocks = md.parse("```\n# これはコメント\n```\n")

    assert blocks == [md.Code("# これはコメント")]


def test_an_empty_document_has_no_blocks():
    assert md.parse("   \n\n") == []
```

- [ ] **Step 2: テストが落ちることを確認する**

```
./myvenv313/Scripts/python.exe -m pytest tests/test_docgen_markdown_document.py -q
```

Expected: FAIL（`ModuleNotFoundError: No module named 'docgen.markdown_document'`）

- [ ] **Step 3: 最小の実装を書く**

`docgen/markdown_document.py` を新規作成。

```python
"""Markdown を中間構造へ解析し、md / docx / xlsx / pptx へ組む。

雛形なしの生成は LLM に Markdown を1回書かせ、その1つの出力から4形式を作る。
形式ごとにプロンプトを分けると、プロンプトが4本になり、品質のばらつきも4箇所で
別々に面倒を見ることになる。

解析は一度だけ行い、共通の構造（Heading/Paragraph/Bullets/Table/Code/Diagram/
References）にする。形式ごとに Markdown を読み直すと、記法の解釈が4箇所に分かれ、
片方だけ直した状態が例外を出さずに成立する。

ここは docgen/*_template.py と役割が違う。あちらは「他人が作った文書の印を
埋める」役で、書式・レイアウト・ロゴを保つことが仕事である。こちらに原本は
存在しない。混ぜない。
"""
import re
from dataclasses import dataclass, field


@dataclass
class Heading:
    level: int
    text: str


@dataclass
class Paragraph:
    text: str


@dataclass
class Bullets:
    items: list[str]


@dataclass
class Table:
    header: list[str]
    rows: list[list[str]]


@dataclass
class Code:
    text: str


@dataclass
class Diagram:
    source: str


@dataclass
class References:
    """何を根拠にしたかの記録。コードが組み立て、LLM には書かせない。

    書かせると、渡していないファイルを参照元として並べうる。
    """
    paths: list[str] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)


_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_BULLET = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(.*)$")
_FENCE = re.compile(r"^\s*```\s*(\w*)\s*$")
_TABLE_ROW = re.compile(r"^\s*\|(.+)\|\s*$")
_TABLE_RULE = re.compile(r"^\s*\|[\s:|-]+\|\s*$")


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in _TABLE_ROW.match(line).group(1).split("|")]


def parse(text: str) -> list:
    """Markdown をブロックの並びにする。

    フェンスの中を先に判定するのは、コード例の中の `#` や `|` を見出しや表と
    取り違えないためである（ingest/parsers/md_parser.py の scan_fences が同じ
    理由でフェンスを先に数えている）。
    """
    blocks: list = []
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    index = 0
    paragraph: list[str] = []
    bullets: list[str] = []

    def flush():
        nonlocal paragraph, bullets
        if paragraph:
            blocks.append(Paragraph(" ".join(paragraph)))
            paragraph = []
        if bullets:
            blocks.append(Bullets(bullets))
            bullets = []

    while index < len(lines):
        line = lines[index]
        fence = _FENCE.match(line)
        if fence:
            flush()
            language = fence.group(1).lower()
            index += 1
            body: list[str] = []
            while index < len(lines) and not _FENCE.match(lines[index]):
                body.append(lines[index])
                index += 1
            index += 1  # 閉じフェンス
            source = "\n".join(body).strip("\n")
            blocks.append(Diagram(source) if language == "mermaid" else Code(source))
            continue
        if _TABLE_ROW.match(line) and index + 1 < len(lines) and _TABLE_RULE.match(lines[index + 1]):
            flush()
            header = _cells(line)
            index += 2
            rows = []
            while index < len(lines) and _TABLE_ROW.match(lines[index]):
                rows.append(_cells(lines[index]))
                index += 1
            blocks.append(Table(header, rows))
            continue
        heading = _HEADING.match(line)
        if heading:
            flush()
            blocks.append(Heading(len(heading.group(1)), heading.group(2).strip()))
            index += 1
            continue
        bullet = _BULLET.match(line)
        if bullet:
            if paragraph:
                blocks.append(Paragraph(" ".join(paragraph)))
                paragraph = []
            bullets.append(bullet.group(1).strip())
            index += 1
            continue
        if not line.strip():
            flush()
            index += 1
            continue
        if bullets:
            blocks.append(Bullets(bullets))
            bullets = []
        paragraph.append(line.strip())
        index += 1

    flush()
    return blocks
```

- [ ] **Step 4: テストが通ることを確認する**

```
./myvenv313/Scripts/python.exe -m pytest tests/test_docgen_markdown_document.py -q
```

Expected: PASS（9件）

- [ ] **Step 5: コミット**

```bash
git add docgen/markdown_document.py tests/test_docgen_markdown_document.py
git commit -m "feat: parse generated Markdown into a shared block structure"
```

---

### Task 7: `markdown_document` — `build` の骨組みと `.md`

**Files:**
- Modify: `docgen/markdown_document.py`
- Test: `tests/test_docgen_markdown_document.py`

**Interfaces:**
- Consumes: Task 6 のブロック
- Produces:
  - `markdown_document.OUTPUT_SUFFIXES: tuple[str, ...]`（`(".md", ".docx", ".xlsx", ".pptx")`）
  - `markdown_document.UnsupportedOutputError(Exception)`
  - `markdown_document.build(blocks, suffix: str, on_diagram_error=None) -> tuple[bytes, list[str]]`（返り値は `(データ, 警告の並び)`）

- [ ] **Step 1: 失敗するテストを書く**

```python
import pytest


def test_build_md_round_trips_the_blocks():
    blocks = [md.Heading(1, "設計書"), md.Paragraph("本文"), md.Bullets(["一つ目"])]

    data, warnings = md.build(blocks, ".md")

    assert warnings == []
    assert data.decode("utf-8") == "# 設計書\n\n本文\n\n- 一つ目\n"


def test_build_md_keeps_mermaid_as_a_fence():
    """.md は GitHub・VS Code・画面のプレビューが図として表示する。
    PNG にする理由が無い（docgen/md_template.py と同じ判断）。"""
    data, _ = md.build([md.Diagram("graph TD\nA-->B")], ".md")

    assert data.decode("utf-8") == "```mermaid\ngraph TD\nA-->B\n```\n"


def test_build_md_writes_the_references_section():
    blocks = [md.Paragraph("本文"), md.References(["main.go"], ["議事録.docx p.1"])]

    text = md.build(blocks, ".md")[0].decode("utf-8")

    assert "## 参照したファイル" in text
    assert "- main.go" in text
    assert "- 議事録.docx p.1" in text


def test_build_rejects_an_unsupported_suffix():
    with pytest.raises(md.UnsupportedOutputError):
        md.build([md.Paragraph("本文")], ".pdf")
```

- [ ] **Step 2: テストが落ちることを確認する**

```
./myvenv313/Scripts/python.exe -m pytest tests/test_docgen_markdown_document.py -q -k build
```

Expected: FAIL（`AttributeError: module 'docgen.markdown_document' has no attribute 'build'`）

- [ ] **Step 3: 最小の実装を書く**

`docgen/markdown_document.py` に足す。

```python
# 参照したファイルの節の見出し。4形式すべてがこの文字列を使う。
REFERENCES_HEADING = "参照したファイル"


class UnsupportedOutputError(Exception):
    """出力形式として扱えない拡張子を渡された。"""


def _table_markdown(block: Table) -> str:
    lines = ["| " + " | ".join(block.header) + " |"]
    lines.append("| " + " | ".join("---" for _ in block.header) + " |")
    lines.extend("| " + " | ".join(row) + " |" for row in block.rows)
    return "\n".join(lines)


def _build_md(blocks, on_diagram_error=None) -> tuple[bytes, list[str]]:
    parts: list[str] = []
    for block in blocks:
        if isinstance(block, Heading):
            parts.append("#" * block.level + " " + block.text)
        elif isinstance(block, Paragraph):
            parts.append(block.text)
        elif isinstance(block, Bullets):
            parts.append("\n".join(f"- {item}" for item in block.items))
        elif isinstance(block, Table):
            parts.append(_table_markdown(block))
        elif isinstance(block, Code):
            parts.append(f"```\n{block.text}\n```")
        elif isinstance(block, Diagram):
            parts.append(f"```mermaid\n{block.source}\n```")
        elif isinstance(block, References):
            parts.append(f"## {REFERENCES_HEADING}")
            parts.append("\n".join(f"- {name}" for name in block.paths + block.citations))
    return ("\n\n".join(parts) + "\n").encode("utf-8"), []


_BUILDERS = {".md": _build_md}

OUTPUT_SUFFIXES = (".md", ".docx", ".xlsx", ".pptx")


def build(blocks, suffix: str, on_diagram_error=None) -> tuple[bytes, list[str]]:
    """ブロックの並びを1つの形式へ組み、(データ, 警告) を返す。

    バイト列を返すのは st.download_button がそれを受け取るためで、中間ファイルを
    作らずに済む（docgen/__init__.py の fill と同じ）。
    """
    builder = _BUILDERS.get(suffix.lower())
    if builder is None:
        raise UnsupportedOutputError(f"出力できない形式です: {suffix}")
    return builder(blocks, on_diagram_error)
```

- [ ] **Step 4: テストが通ることを確認する**

```
./myvenv313/Scripts/python.exe -m pytest tests/test_docgen_markdown_document.py -q
```

Expected: PASS（13件）

- [ ] **Step 5: コミット**

```bash
git add docgen/markdown_document.py tests/test_docgen_markdown_document.py
git commit -m "feat: build Markdown output from the block structure"
```

---

### Task 8: `markdown_document` — `.docx`

**Files:**
- Modify: `docgen/markdown_document.py`
- Test: `tests/test_docgen_markdown_document.py`

**Interfaces:**
- Consumes: Task 7 の `_BUILDERS`、`docgen.mermaid.render` / `MermaidError`
- Produces: `build(blocks, ".docx", on_diagram_error)` が docx のバイト列を返す

- [ ] **Step 1: 失敗するテストを書く**

```python
import io

import docx


def _docx_texts(data: bytes) -> list[str]:
    return [p.text for p in docx.Document(io.BytesIO(data)).paragraphs]


def test_build_docx_writes_headings_and_paragraphs():
    blocks = [md.Heading(1, "設計書"), md.Paragraph("本文")]

    data, warnings = md.build(blocks, ".docx")

    assert warnings == []
    assert "設計書" in _docx_texts(data)
    assert "本文" in _docx_texts(data)


def test_build_docx_writes_a_table():
    blocks = [md.Table(["区分", "日数"], [["6か月", "10日"]])]

    document = docx.Document(io.BytesIO(md.build(blocks, ".docx")[0]))

    assert len(document.tables) == 1
    assert document.tables[0].cell(0, 0).text == "区分"
    assert document.tables[0].cell(1, 1).text == "10日"


def test_build_docx_writes_the_references_section():
    blocks = [md.References(["main.go"], ["議事録.docx p.1"])]

    texts = _docx_texts(md.build(blocks, ".docx")[0])

    assert md.REFERENCES_HEADING in texts
    assert "main.go" in texts
    assert "議事録.docx p.1" in texts


def test_build_docx_keeps_the_mermaid_text_when_it_cannot_be_drawn(monkeypatch):
    """図にできなかったことを黙って捨てると、利用者は成果物を開くまで
    気づけない。テキストは残し、呼び出し元へ知らせる。"""
    def _fail(source):
        raise mermaid.MermaidError("mmdc を起動できませんでした")

    monkeypatch.setattr(mermaid, "render", _fail)
    seen = []

    data, warnings = md.build(
        [md.Diagram("graph TD\nA-->B")], ".docx",
        lambda name, reason: seen.append((name, reason)),
    )

    assert "graph TD" in "\n".join(_docx_texts(data))
    assert seen and "mmdc" in seen[0][1]
```

`from docgen import mermaid` をテストの冒頭に足すこと。

- [ ] **Step 2: テストが落ちることを確認する**

```
./myvenv313/Scripts/python.exe -m pytest tests/test_docgen_markdown_document.py -q -k docx
```

Expected: FAIL（`UnsupportedOutputError: 出力できない形式です: .docx`）

- [ ] **Step 3: 最小の実装を書く**

`docgen/markdown_document.py` に足す。冒頭の import に加える。

```python
import io

import docx
from docx.shared import Inches, Pt

from docgen import mermaid

# mmdc の既定の PNG は幅800px（約8.3インチ）で、A4縦の段幅（約6.5インチ）より
# 広い。docgen/docx_template.py と同じ値にする。
DIAGRAM_WIDTH = Inches(6.0)
```

```python
def _add_diagram(document, block, on_diagram_error):
    """図にできれば画像を、できなければ Mermaid のテキストを入れる。

    図にできなかったときに何も入れないと、利用者は成果物を開いても「そこに何か
    あったはず」だと分からない（docgen/mermaid.py の rendered と同じ判断）。
    """
    try:
        image = mermaid.render(block.source)
    except mermaid.MermaidError as error:
        document.add_paragraph(block.source)
        if on_diagram_error is not None:
            # 雛形と違って名前の付いた欄が存在しないので「図」で呼ぶ。
            on_diagram_error("図", str(error))
        return
    document.add_picture(io.BytesIO(image), width=DIAGRAM_WIDTH)


def _build_docx(blocks, on_diagram_error=None) -> tuple[bytes, list[str]]:
    document = docx.Document()
    for block in blocks:
        if isinstance(block, Heading):
            document.add_heading(block.text, level=min(block.level, 9))
        elif isinstance(block, Paragraph):
            document.add_paragraph(block.text)
        elif isinstance(block, Bullets):
            for item in block.items:
                document.add_paragraph(item, style="List Bullet")
        elif isinstance(block, Table):
            table = document.add_table(rows=1, cols=len(block.header))
            table.style = "Table Grid"
            for cell, text in zip(table.rows[0].cells, block.header):
                cell.text = text
            for row in block.rows:
                cells = table.add_row().cells
                for cell, text in zip(cells, row):
                    cell.text = text
        elif isinstance(block, Code):
            paragraph = document.add_paragraph(block.text)
            paragraph.runs[0].font.name = "Consolas"
            paragraph.runs[0].font.size = Pt(9)
        elif isinstance(block, Diagram):
            _add_diagram(document, block, on_diagram_error)
        elif isinstance(block, References):
            document.add_heading(REFERENCES_HEADING, level=2)
            for name in block.paths + block.citations:
                document.add_paragraph(name, style="List Bullet")
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue(), []


_BUILDERS[".docx"] = _build_docx
```

- [ ] **Step 4: テストが通ることを確認する**

```
./myvenv313/Scripts/python.exe -m pytest tests/test_docgen_markdown_document.py -q
```

Expected: PASS（17件）

- [ ] **Step 5: コミット**

```bash
git add docgen/markdown_document.py tests/test_docgen_markdown_document.py
git commit -m "feat: build Word output from the block structure"
```

---

### Task 9: `markdown_document` — `.pptx`

**Files:**
- Modify: `docgen/markdown_document.py`
- Test: `tests/test_docgen_markdown_document.py`

**Interfaces:**
- Consumes: Task 7 の `_BUILDERS`
- Produces: `build(blocks, ".pptx", on_diagram_error)` が pptx のバイト列を返す

- [ ] **Step 1: 失敗するテストを書く**

```python
from pptx import Presentation


def _slide_texts(data: bytes) -> list[list[str]]:
    presentation = Presentation(io.BytesIO(data))
    return [
        [shape.text_frame.text for shape in slide.shapes if shape.has_text_frame]
        for slide in presentation.slides
    ]


def test_build_pptx_makes_one_slide_per_second_level_heading():
    blocks = [
        md.Heading(1, "提案"),
        md.Heading(2, "現状"),
        md.Bullets(["遅い"]),
        md.Heading(2, "対策"),
        md.Bullets(["速くする"]),
    ]

    slides = _slide_texts(md.build(blocks, ".pptx")[0])

    assert len(slides) == 3  # タイトル + 2枚
    assert "提案" in slides[0][0]
    assert "現状" in slides[1][0]
    assert "遅い" in slides[1][1]


def test_build_pptx_does_not_split_on_third_level_headings():
    """見出しの深さでスライドを分けると、章立ての書き方しだいで
    数十枚に膨らむ。"""
    blocks = [md.Heading(2, "現状"), md.Heading(3, "細目"), md.Paragraph("本文")]

    assert len(_slide_texts(md.build(blocks, ".pptx")[0])) == 1


def test_build_pptx_puts_the_references_on_the_last_slide():
    blocks = [md.Heading(2, "現状"), md.References(["main.go"], [])]

    slides = _slide_texts(md.build(blocks, ".pptx")[0])

    assert md.REFERENCES_HEADING in slides[-1][0]
    assert "main.go" in slides[-1][1]


def test_build_pptx_without_any_heading_still_produces_a_slide():
    """見出しを1つも書かない回がある。空のファイルを渡さない。"""
    assert len(_slide_texts(md.build([md.Paragraph("本文")], ".pptx")[0])) == 1
```

- [ ] **Step 2: テストが落ちることを確認する**

```
./myvenv313/Scripts/python.exe -m pytest tests/test_docgen_markdown_document.py -q -k pptx
```

Expected: FAIL（`UnsupportedOutputError: 出力できない形式です: .pptx`）

- [ ] **Step 3: 最小の実装を書く**

冒頭の import に `from pptx import Presentation` を足す。

```python
# python-pptx の既定のレイアウト。0 はタイトル、1 はタイトルと内容。
_TITLE_LAYOUT = 0
_CONTENT_LAYOUT = 1


def _pptx_lines(block) -> list[str]:
    """1つのブロックをスライド本文の行の並びにする。"""
    if isinstance(block, Heading):
        return [block.text]
    if isinstance(block, Paragraph):
        return [block.text]
    if isinstance(block, Bullets):
        return list(block.items)
    if isinstance(block, Table):
        return [" | ".join(block.header)] + [" | ".join(row) for row in block.rows]
    if isinstance(block, Code):
        return block.text.split("\n")
    if isinstance(block, Diagram):
        return block.source.split("\n")
    return []


def _add_slide(presentation, title: str, lines: list[str]) -> None:
    slide = presentation.slides.add_slide(presentation.slide_layouts[_CONTENT_LAYOUT])
    slide.shapes.title.text = title
    body = slide.placeholders[1].text_frame
    body.text = lines[0] if lines else ""
    for line in lines[1:]:
        body.add_paragraph().text = line


def _build_pptx(blocks, on_diagram_error=None) -> tuple[bytes, list[str]]:
    """`##` ごとに1スライドにする。

    `###` 以下でスライドを分けないのは、見出しの深さで分けると章立ての書き方
    しだいでスライドが数十枚に膨らむためである。深い見出しは本文の1行にする。

    図は当面 PNG にせず Mermaid のテキストを本文へ入れる。スライドは本文の
    プレースホルダに文字を流し込む作りで、画像を置くと位置と大きさを決める
    判断が要る。on_diagram_error を受け取るのは他の形式と署名を揃えるためである
    （ingest/parsers/__init__.py と同じ方針）。
    """
    presentation = Presentation()
    title = ""
    current: str | None = None
    lines: list[str] = []
    made = False

    def flush():
        nonlocal current, lines, made
        if current is not None or lines:
            _add_slide(presentation, current or title or "", lines)
            made = True
        current, lines = None, []

    for block in blocks:
        if isinstance(block, Heading) and block.level == 1 and not title:
            title = block.text
            slide = presentation.slides.add_slide(presentation.slide_layouts[_TITLE_LAYOUT])
            slide.shapes.title.text = block.text
            made = True
            continue
        if isinstance(block, Heading) and block.level == 2:
            flush()
            current = block.text
            continue
        if isinstance(block, References):
            flush()
            _add_slide(presentation, REFERENCES_HEADING, block.paths + block.citations)
            made = True
            continue
        lines.extend(_pptx_lines(block))
    flush()

    if not made:
        # 見出しも本文も無い回に空のファイルを渡さない。
        _add_slide(presentation, title or "文書", [])
    buffer = io.BytesIO()
    presentation.save(buffer)
    return buffer.getvalue(), []


_BUILDERS[".pptx"] = _build_pptx
```

- [ ] **Step 4: テストが通ることを確認する**

```
./myvenv313/Scripts/python.exe -m pytest tests/test_docgen_markdown_document.py -q
```

Expected: PASS（21件）

- [ ] **Step 5: コミット**

```bash
git add docgen/markdown_document.py tests/test_docgen_markdown_document.py
git commit -m "feat: build PowerPoint output from the block structure"
```

---

### Task 10: `markdown_document` — `.xlsx`

**Files:**
- Modify: `docgen/markdown_document.py`
- Test: `tests/test_docgen_markdown_document.py`

**Interfaces:**
- Consumes: Task 7 の `_BUILDERS`
- Produces: `build(blocks, ".xlsx")` が xlsx のバイト列と警告を返す

- [ ] **Step 1: 失敗するテストを書く**

```python
import openpyxl


def _workbook(data: bytes):
    return openpyxl.load_workbook(io.BytesIO(data))


def test_build_xlsx_puts_each_table_on_its_own_sheet():
    blocks = [
        md.Heading(2, "付与日数"),
        md.Table(["区分", "日数"], [["6か月", "10日"]]),
    ]

    book = _workbook(md.build(blocks, ".xlsx")[0])

    assert book.sheetnames == ["付与日数"]
    assert [cell.value for cell in book["付与日数"][1]] == ["区分", "日数"]
    assert [cell.value for cell in book["付与日数"][2]] == ["6か月", "10日"]


def test_build_xlsx_numbers_a_table_that_has_no_heading():
    book = _workbook(md.build([md.Table(["A"], [["1"]])], ".xlsx")[0])

    assert book.sheetnames == ["表1"]


def test_build_xlsx_shortens_a_sheet_name_that_excel_rejects():
    """Excel のシート名は31文字以内で、: \\ / ? * [ ] を含められない。
    そのまま渡すと保存時に落ちる。"""
    blocks = [md.Heading(2, "あ" * 40 + "/x"), md.Table(["A"], [["1"]])]

    book = _workbook(md.build(blocks, ".xlsx")[0])

    assert len(book.sheetnames[0]) <= 31
    assert "/" not in book.sheetnames[0]


def test_build_xlsx_makes_duplicate_sheet_names_unique():
    blocks = [
        md.Heading(2, "表"), md.Table(["A"], [["1"]]),
        md.Heading(2, "表"), md.Table(["B"], [["2"]]),
    ]

    assert len(_workbook(md.build(blocks, ".xlsx")[0]).sheetnames) == 2


def test_build_xlsx_without_a_table_falls_back_to_two_columns_and_warns():
    """空のブックを渡さない。書かれた内容そのものは必ず渡す。"""
    blocks = [md.Heading(2, "現状"), md.Paragraph("遅い")]

    data, warnings = md.build(blocks, ".xlsx")
    book = _workbook(data)

    assert warnings and "表" in warnings[0]
    assert [cell.value for cell in book.worksheets[0][1]] == ["現状", "遅い"]


def test_build_xlsx_puts_the_references_on_their_own_sheet():
    blocks = [md.Table(["A"], [["1"]]), md.References(["main.go"], [])]

    book = _workbook(md.build(blocks, ".xlsx")[0])

    assert md.REFERENCES_HEADING in book.sheetnames
    assert book[md.REFERENCES_HEADING]["A1"].value == "main.go"
```

- [ ] **Step 2: テストが落ちることを確認する**

```
./myvenv313/Scripts/python.exe -m pytest tests/test_docgen_markdown_document.py -q -k xlsx
```

Expected: FAIL（`UnsupportedOutputError: 出力できない形式です: .xlsx`）

- [ ] **Step 3: 最小の実装を書く**

冒頭の import に `import openpyxl` を足す。

```python
# Excel のシート名の制限。31文字以内で、この文字を含められない。
_SHEET_NAME_LIMIT = 31
_SHEET_NAME_FORBIDDEN = re.compile(r"[:\\/?*\[\]]")


def _sheet_name(wanted: str, used: set[str]) -> str:
    """Excel が受け取れるシート名にする。重なったら連番を足す。

    そのまま渡すと保存時に落ちる。落ちると成果物が1つも手に入らない。
    """
    name = _SHEET_NAME_FORBIDDEN.sub("_", wanted).strip() or "表"
    name = name[:_SHEET_NAME_LIMIT]
    if name not in used:
        used.add(name)
        return name
    serial = 2
    while True:
        suffix = f"_{serial}"
        candidate = name[: _SHEET_NAME_LIMIT - len(suffix)] + suffix
        if candidate not in used:
            used.add(candidate)
            return candidate
        serial += 1


def _build_xlsx(blocks, on_diagram_error=None) -> tuple[bytes, list[str]]:
    """表1つにつき1シート。シート名は直前の見出しにする。

    表が1つも無いときは見出しと本文の2列で1シートを出し、警告する。空のブックを
    返さないのは、利用者が受け取るものを空にしないためである。
    """
    book = openpyxl.Workbook()
    book.remove(book.active)
    warnings: list[str] = []
    used: set[str] = set()
    heading = ""
    table_serial = 1
    rows: list[tuple[str, str]] = []

    for block in blocks:
        if isinstance(block, Heading):
            heading = block.text
            rows.append((block.text, ""))
        elif isinstance(block, Table):
            sheet = book.create_sheet(_sheet_name(heading or f"表{table_serial}", used))
            sheet.append(block.header)
            for row in block.rows:
                sheet.append(row)
            table_serial += 1
            heading = ""
        elif isinstance(block, References):
            sheet = book.create_sheet(_sheet_name(REFERENCES_HEADING, used))
            for name in block.paths + block.citations:
                sheet.append([name])
        elif isinstance(block, Paragraph):
            rows.append((heading, block.text))
            heading = ""
        elif isinstance(block, Bullets):
            for item in block.items:
                rows.append((heading, item))
                heading = ""
        elif isinstance(block, (Code, Diagram)):
            source = block.text if isinstance(block, Code) else block.source
            rows.append((heading, source))
            heading = ""

    if not any(isinstance(block, Table) for block in blocks):
        warnings.append(
            "表が1つも書かれなかったため、見出しと本文の2列で出しました。"
            "表が欲しい場合は依頼文で「表で」と指定してください。"
        )
        sheet = book.create_sheet(_sheet_name("本文", used), 0)
        for left, right in rows:
            sheet.append([left, right])

    if not book.sheetnames:
        book.create_sheet(_sheet_name("本文", used))
    buffer = io.BytesIO()
    book.save(buffer)
    return buffer.getvalue(), warnings


_BUILDERS[".xlsx"] = _build_xlsx
```

- [ ] **Step 4: テストが通ることを確認する**

```
./myvenv313/Scripts/python.exe -m pytest tests/test_docgen_markdown_document.py -q
```

Expected: PASS（27件）

- [ ] **Step 5: 全体のテストを回す**

```
./myvenv313/Scripts/python.exe -m pytest -q
```

Expected: PASS（既存の1,010件 + 新規分）

- [ ] **Step 6: コミット**

```bash
git add docgen/markdown_document.py tests/test_docgen_markdown_document.py
git commit -m "feat: build Excel output from the block structure"
```

---

### Task 11: `docgen/freeform.py` — 雛形なしのプロンプト

**Files:**
- Create: `docgen/freeform.py`
- Test: `tests/test_docgen_freeform.py`

**Interfaces:**
- Consumes: `docgen.filling.MAX_PROMPT_CHARS` / `PromptTooLongError`
- Produces:
  - `freeform.build_prompt(question, sources, attachments, tree_text, suffix) -> str`
  - `freeform.write_markdown(question, sources, attachments, tree_text, suffix, ask) -> str`
  - `sources` は `[(種類の名前, ヒットの並び)]`、`attachments` は `[(名前, 本文)]`（`filling.build_prompt` と同じ形）

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_docgen_freeform.py` を新規作成。

```python
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
    assert "表" in freeform.build_prompt("依頼", [], [], "", ".xlsx")
    assert "表で" not in freeform.build_prompt("依頼", [], [], "", ".md")


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
```

- [ ] **Step 2: テストが落ちることを確認する**

```
./myvenv313/Scripts/python.exe -m pytest tests/test_docgen_freeform.py -q
```

Expected: FAIL（`ImportError: cannot import name 'freeform' from 'docgen'`）

- [ ] **Step 3: 最小の実装を書く**

`docgen/freeform.py` を新規作成。

```python
"""雛形なしで文書を書かせる。

雛形ありの経路（docgen/filling.py）との違いは1点だけである。埋める欄の一覧の
代わりに、出力の形の指示を載せる。材料（依頼・検索結果・添付・プロジェクトの
ファイル）は同じものを同じ形で受け取る。

形式ごとにプロンプトを分けない。Markdown を1回書かせ、そこから4形式を組む
（docgen/markdown_document.py）。分けるとプロンプトが4本になり、品質のばらつきも
4箇所で別々に面倒を見ることになる。
"""
from docgen.filling import MAX_PROMPT_CHARS, PromptTooLongError

# xlsx のときだけ足す指示。一覧表が欲しいのに文章が返ると、変換のしようがない。
_TABLE_INSTRUCTION = (
    "この文書は Excel にします。本文は Markdown の表で書いてください。"
    "表の直前には、その表が何かを示す `##` の見出しを置いてください"
    "（見出しがシート名になります）。\n"
)


def build_prompt(question, sources, attachments, tree_text: str, suffix: str) -> str:
    """依頼・検索結果・添付・プロジェクトの一覧を1つのプロンプトにまとめる。

    sources は (資料の種類の名前, ヒットの並び) の並びである。種類ごとに節を
    分けるのは、混ぜて並べるとどれが社内の決定事項でどれが外部ライブラリの
    説明なのかをモデルが区別できないためである（filling.build_prompt と同じ）。
    """
    found = "\n\n".join(
        f"## {kind}の検索結果\n"
        + ("\n\n".join(f"【{hit.citation}】\n{hit.text}" for hit in hits)
           or f"（{kind}の検索結果はありません）")
        for kind, hits in sources
    ) or "## 検索結果\n（検索していません）"
    attached = "\n\n".join(
        f"【{name}】\n{text}" for name, text in attachments
    ) or "（添付ファイルはありません）"
    listing = tree_text or "（プロジェクトフォルダは指定されていません）"
    return (
        "あなたは社内文書を作成する担当者です。\n"
        "次の資料をもとに、依頼された文書を Markdown で書いてください。\n\n"
        "資料に書かれていないことは書かないでください。"
        "根拠が見つからない項目は、推測で埋めずに省いてください。\n\n"
        f"## 依頼\n{question}\n\n"
        f"{found}\n\n"
        f"## 資料の本文\n{attached}\n\n"
        f"## プロジェクトのファイル一覧\n{listing}\n\n"
        "## 書き方\n"
        "Markdown だけを返してください。説明や前置きは書かないでください。\n"
        "見出しは `#` `##` `###` を使ってください。\n"
        "表は Markdown の表で書いてください。\n"
        + (_TABLE_INSTRUCTION if suffix.lower() == ".xlsx" else "")
        + "図で表すほうがよい箇所は、```mermaid のコードブロックにしてください。\n"
        "「参照したファイル」の節は書かないでください。こちらで付けます。\n"
    )


def write_markdown(
    question, sources, attachments, tree_text: str, suffix: str, ask
) -> str:
    """モデルが書いた Markdown をそのまま返す。

    上限の判定を呼ぶ前に置くのは、呼んでから落ちると利用者が30〜60秒待たされた
    うえで何も受け取れないためである（filling.fill_values と同じ）。
    """
    prompt = build_prompt(question, sources, attachments, tree_text, suffix)
    if len(prompt) > MAX_PROMPT_CHARS:
        raise PromptTooLongError(
            f"資料が長すぎます（{len(prompt):,}文字 / 上限 {MAX_PROMPT_CHARS:,}文字）。"
            "参照するフォルダや添付を減らしてください"
        )
    return ask(prompt)
```

- [ ] **Step 4: テストが通ることを確認する**

```
./myvenv313/Scripts/python.exe -m pytest tests/test_docgen_freeform.py -q
```

Expected: PASS（5件）

- [ ] **Step 5: コミット**

```bash
git add docgen/freeform.py tests/test_docgen_freeform.py
git commit -m "feat: prompt for a document without a template"
```

---

### Task 12: 画面 — 雛形なしの選択と出力形式

**Files:**
- Modify: `rag_chat_app.py`（Cowork の入力欄、735-800行付近と、生成の分岐 820-860行付近）
- Test: `tests/test_rag_chat_app_cowork.py`

**Interfaces:**
- Consumes: `markdown_document.OUTPUT_SUFFIXES`、`freeform.write_markdown`、`markdown_document.parse` / `build`
- Produces: 雛形なしで生成できる画面。プロジェクトフォルダはまだ配線しない（Task 13）

**このタスクの前に読むこと:** `rag_chat_app.py` の `_generate_document`（340-480行）と、
Cowork の入力欄（735-800行）、生成の分岐（820-860行）。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_rag_chat_app_cowork.py` に足す。既存の `app` / `_no_network` /
`_stub_store` / `_register` をそのまま使う。

```python
NO_TEMPLATE = "（雛形なし）"


def test_cowork_offers_generating_without_a_template(app, tmp_path):
    """雛形を作る手間のほうが大きい仕事がある。雛形が0件でも画面は成立する。"""
    with (
        patch.object(store_module, "open_store", _stub_store()),
        patch.object(templates_module, "TEMPLATE_DIR", tmp_path / "templates"),
    ):
        app.run()
        app.segmented_control[0].set_value("Cowork").run()

    assert not app.exception
    assert NO_TEMPLATE in app.selectbox(key="template").options


def test_cowork_without_a_template_generates_markdown(app, tmp_path):
    with (
        patch.object(store_module, "open_store", _stub_store()),
        patch.object(templates_module, "TEMPLATE_DIR", tmp_path / "templates"),
        patch.object(chat, "ask_text", lambda *a, **k: "# 設計書\n\n本文\n"),
        patch.object(chat, "ask_json", lambda *a, **k: "{}"),
    ):
        app.run()
        app.segmented_control[0].set_value("Cowork").run()
        app.selectbox(key="template").set_value(NO_TEMPLATE).run()
        app.selectbox(key="output_suffix").set_value(".md").run()
        app.chat_input[0].set_value("設計書を書いて").run()

    assert not app.exception
    assert app.download_button[0].data.decode("utf-8").startswith("# 設計書")


def test_cowork_without_a_template_stops_when_there_is_no_evidence(app, tmp_path):
    """根拠が1つも無ければ、呼んでも中身の無い文書が出るだけである。"""
    with (
        patch.object(store_module, "open_store", _stub_store()),
        patch.object(templates_module, "TEMPLATE_DIR", tmp_path / "templates"),
    ):
        app.run()
        app.segmented_control[0].set_value("Cowork").run()
        app.selectbox(key="template").set_value(NO_TEMPLATE).run()
        app.checkbox(key="cowork_internal").set_value(False).run()
        app.chat_input[0].set_value("設計書を書いて").run()

    assert not app.exception
    assert any("根拠" in error.value for error in app.error)
```

`from ingest import chat` はファイル冒頭で既に import 済みである。

- [ ] **Step 2: テストが落ちることを確認する**

```
./myvenv313/Scripts/python.exe -m pytest tests/test_rag_chat_app_cowork.py -q -k without_a_template
```

Expected: FAIL（`KeyError` / `StreamlitAPIException`。`（雛形なし）` の選択肢が無い）

- [ ] **Step 3: 最小の実装を書く**

`rag_chat_app.py` を次のように変える。

1. import を足す

```python
from docgen import freeform as docgen_freeform
from docgen import markdown_document
from docgen import project as docgen_project
```

2. 定数を足す（`MODE_COWORK` の近く）

```python
# 雛形を選ばない選択肢。プルダウンの先頭に置く。雛形が0件でも画面が成立する
# ようにするため、選択肢そのものを常に存在させる。
NO_TEMPLATE = "（雛形なし）"
```

3. 雛形プルダウンを置き換える（`if available:` の分岐ごと）

```python
    # 雛形が0件でも「（雛形なし）」があるので、プルダウンは常に出せる。
    # 以前は0件のときプルダウンを出さず警告だけにしていたが、雛形なしが
    # 正規の選択肢になった今、その警告は行き止まりを指すだけになる。
    choices = [NO_TEMPLATE] + docgen_templates.templates()
    template_choice = left.selectbox(
        "雛形",
        choices,
        format_func=lambda item: item if item == NO_TEMPLATE else item.name,
        key="template",
        disabled=st.session_state.generating,
    )
    template_path = None if template_choice == NO_TEMPLATE else template_choice
    if right.button("雛形を登録・削除", disabled=st.session_state.generating):
        st.session_state.template_dialog_open = True

    output_suffix = markdown_document.OUTPUT_SUFFIXES[0]
    if template_path is None:
        output_suffix = st.selectbox(
            "出力形式",
            markdown_document.OUTPUT_SUFFIXES,
            key="output_suffix",
            disabled=st.session_state.generating,
        )
```

続くコーパスのチェックボックスと添付は `if available:` の中にあるが、
**この条件を外して常に出す。** 雛形なしでも検索結果と添付は使うためである。

4. 生成の分岐（820-860行付近）を書き換える。`template_path is None` は
   「雛形が無い」ではなく「雛形なしを選んだ」という意味になる。

```python
        if mode == MODE_COWORK and template_path is None:
            if not use_internal and not use_docs and not attachments:
                st.session_state.cowork_result = _cowork_error(
                    "参照する資料も添付ファイルもありません。根拠が無いため生成しません。"
                )
            else:
                _generate_freeform(
                    output_suffix, question, attachments, use_internal, use_docs
                )
        elif mode == MODE_COWORK:
            ...（既存のまま）
```

5. **先に `_collect_evidence` を切り出す。** 検索と添付の解析は雛形あり・なしで
   同じ処理である。重複を残すと、片方だけ直した状態が例外を出さずに成立する。

   `_generate_document`（340-440行付近）の「検索」と「添付の解析」をそのまま
   この関数へ移し、`_generate_document` はこれを呼ぶ形にする。中身は移すだけで
   変えない。移したあとに `pytest tests/test_rag_chat_app_cowork.py -q` が
   既存15件のまま通ることを確認してから次へ進むこと。

```python
def _collect_evidence(question, attachments, use_internal, use_docs, result):
    """検索結果と添付の本文を集める。失敗したら結果に積んで None を返す。

    雛形あり・なしの両方がこれを呼ぶ。どちらか一方にだけ検索の修正が入る状態を
    作らないため、1つにまとめてある。

    どのコーパスを引くかは画面が決め、filling.py / freeform.py へは
    (種類の名前, ヒット) の並びで渡す。生成側にコーパスの知識を持たせない
    （設計書6節）。
    """
    def ask(prompt):
        return chat.ask_json(model, prompt, num_ctx=docgen_filling.GENERATION_NUM_CTX)

    sources = []
    try:
        if use_internal:
            internal = get_collection(DB_PATH)
            sources.append((
                CORPUS_INTERNAL,
                search(
                    internal,
                    question,
                    index=get_index(internal, DB_PATH, internal.revision()),
                    rerank=rerank_callable,
                ),
            ))
        if use_docs:
            documents = get_collection(DOCS_DB_PATH)
            if documents.count() == 0:
                result["infos"].append(
                    "技術ドキュメントが取り込まれていません。この検索は飛ばしました。"
                )
            else:
                english = query_translation.translate_query(question, ask_json)
                sources.append((
                    CORPUS_DOCS,
                    search(
                        documents,
                        english,
                        index=get_index(documents, DOCS_DB_PATH, documents.revision()),
                        rerank=rerank_callable,
                        rerank_floor=DOCS_RERANK_FLOOR,
                    ),
                ))
    except (embedder.EmbeddingError, chat.ChatError) as error:
        st.session_state.cowork_result = _cowork_error(str(error))
        return None

    texts = []
    if attachments:
        caption_image, reason = caption_image_or_reason()
        if reason:
            result["warnings"].append(reason)
        with tempfile.TemporaryDirectory() as workspace:
            for file in attachments:
                path = Path(workspace) / file.name
                path.write_bytes(file.getvalue())
                try:
                    units = parse(path, caption_image=caption_image)
                except Exception as error:
                    st.session_state.cowork_result = _cowork_error(
                        f"{file.name} を開けませんでした: {error}"
                    )
                    return None
                text = "\n".join(unit.text for unit in units)
                if not text:
                    result["warnings"].append(
                        f"{file.name} から本文を取り出せませんでした。"
                    )
                texts.append((file.name, text))
    return sources, texts
```

6. `_generate_freeform` を `_generate_document` の隣に足す。

```python
def _generate_freeform(suffix, question, attachments, use_internal, use_docs):
    """雛形なしで文書を作り、結果を st.session_state.cowork_result に積む。

    _generate_document と同じく、ここで st.error や st.download_button を直接
    呼ばない（generating を戻す st.rerun() が同じ実行の描画ごと消すため）。
    """
    result = _empty_cowork_result()

    def ask_text(prompt):
        return chat.ask_text(model, prompt, num_ctx=docgen_filling.GENERATION_NUM_CTX)

    collected = _collect_evidence(question, attachments, use_internal, use_docs, result)
    if collected is None:
        return
    sources, texts = collected

    try:
        markdown = docgen_freeform.write_markdown(
            question, sources, texts, "", suffix, ask_text
        )
    except (docgen_filling.PromptTooLongError, chat.ChatError) as error:
        st.session_state.cowork_result = _cowork_error(str(error))
        return

    blocks = markdown_document.parse(markdown)
    blocks.append(
        markdown_document.References(
            paths=[name for name, _ in texts],
            citations=[hit.citation for _, hits in sources for hit in hits],
        )
    )
    undrawn = []
    data, warnings = markdown_document.build(
        blocks, suffix, lambda name, reason: undrawn.append((name, reason))
    )
    result["warnings"].extend(warnings)
    if undrawn:
        result["warnings"].append(
            "図にできなかった箇所: "
            + "、".join(f"{name}（{reason}）" for name, reason in undrawn)
        )
    for name, hits in sources:
        if not hits:
            result["infos"].append(f"{name}の検索は0件でした。")
    result["download"] = {
        "data": data,
        "file_name": f"文書_{date.today().isoformat()}{suffix}",
    }
    result["sources"] = sources
    st.session_state.cowork_result = result
```

- [ ] **Step 4: テストが通ることを確認する**

```
./myvenv313/Scripts/python.exe -m pytest tests/test_rag_chat_app_cowork.py -q
```

Expected: PASS（既存15件 + 新規3件）

- [ ] **Step 5: コミット**

```bash
git add rag_chat_app.py tests/test_rag_chat_app_cowork.py
git commit -m "feat: generate a document without a template"
```

---

### Task 13: 画面 — プロジェクトフォルダの配線と書き出し、ドキュメント

**Files:**
- Modify: `rag_chat_app.py`
- Modify: `README.md`
- Test: `tests/test_rag_chat_app_cowork.py`

**Interfaces:**
- Consumes: `docgen_project.tree` / `tree_text` / `select` / `read` / `write_output` / `ProjectFolderError`
- Produces: なし（最終タスク）

- [ ] **Step 1: 失敗するテストを書く**

```python
def test_cowork_reads_the_project_folder_and_writes_the_result_into_it(app, tmp_path):
    """成果物はダウンロードだけでなくフォルダにも残す。"""
    folder = tmp_path / "myproject"
    folder.mkdir()
    (folder / "main.go").write_text("package main\n", encoding="utf-8")

    with (
        patch.object(store_module, "open_store", _stub_store()),
        patch.object(templates_module, "TEMPLATE_DIR", tmp_path / "templates"),
        patch.object(chat, "ask_json", lambda *a, **k: '["main.go"]'),
        patch.object(chat, "ask_text", lambda *a, **k: "# 設計書\n\n本文\n"),
    ):
        app.run()
        app.segmented_control[0].set_value("Cowork").run()
        app.selectbox(key="template").set_value(NO_TEMPLATE).run()
        app.text_input(key="project_folder").set_value(str(folder)).run()
        app.chat_input[0].set_value("設計書を書いて").run()

    assert not app.exception
    written = list((folder / "generated_docs").glob("*.md"))
    assert len(written) == 1
    assert "# 設計書" in written[0].read_text(encoding="utf-8")


def test_the_generated_document_lists_the_files_it_used(app, tmp_path):
    """何を根拠にしたかを後から辿れるようにする。"""
    folder = tmp_path / "myproject"
    folder.mkdir()
    (folder / "main.go").write_text("package main\n", encoding="utf-8")

    with (
        patch.object(store_module, "open_store", _stub_store()),
        patch.object(templates_module, "TEMPLATE_DIR", tmp_path / "templates"),
        patch.object(chat, "ask_json", lambda *a, **k: '["main.go"]'),
        patch.object(chat, "ask_text", lambda *a, **k: "# 設計書\n\n本文\n"),
    ):
        app.run()
        app.segmented_control[0].set_value("Cowork").run()
        app.selectbox(key="template").set_value(NO_TEMPLATE).run()
        app.text_input(key="project_folder").set_value(str(folder)).run()
        app.chat_input[0].set_value("設計書を書いて").run()

    text = app.download_button[0].data.decode("utf-8")
    assert "## 参照したファイル" in text
    assert "main.go" in text


def test_a_folder_that_does_not_exist_stops_before_calling_the_model(app, tmp_path):
    """呼んでから落ちると、利用者は30〜60秒待たされたうえで何も受け取れない。"""
    with (
        patch.object(store_module, "open_store", _stub_store()),
        patch.object(templates_module, "TEMPLATE_DIR", tmp_path / "templates"),
    ):
        app.run()
        app.segmented_control[0].set_value("Cowork").run()
        app.selectbox(key="template").set_value(NO_TEMPLATE).run()
        app.text_input(key="project_folder").set_value(str(tmp_path / "無い")).run()
        app.chat_input[0].set_value("設計書を書いて").run()

    assert not app.exception
    assert any("フォルダ" in error.value for error in app.error)


def test_a_project_folder_alone_is_enough_evidence(app, tmp_path):
    """フォルダだけを指定した回は正当な使い方であり、止めてはならない。"""
    folder = tmp_path / "myproject"
    folder.mkdir()
    (folder / "main.go").write_text("package main\n", encoding="utf-8")

    with (
        patch.object(store_module, "open_store", _stub_store()),
        patch.object(templates_module, "TEMPLATE_DIR", tmp_path / "templates"),
        patch.object(chat, "ask_json", lambda *a, **k: '["main.go"]'),
        patch.object(chat, "ask_text", lambda *a, **k: "# 設計書\n\n本文\n"),
    ):
        app.run()
        app.segmented_control[0].set_value("Cowork").run()
        app.selectbox(key="template").set_value(NO_TEMPLATE).run()
        app.checkbox(key="cowork_internal").set_value(False).run()
        app.text_input(key="project_folder").set_value(str(folder)).run()
        app.chat_input[0].set_value("設計書を書いて").run()

    assert not app.exception
    assert not app.error
```

- [ ] **Step 2: テストが落ちることを確認する**

```
./myvenv313/Scripts/python.exe -m pytest tests/test_rag_chat_app_cowork.py -q -k "project_folder or folder or files_it_used"
```

Expected: FAIL（`project_folder` の `text_input` が無い）

- [ ] **Step 3: 最小の実装を書く**

1. 入力欄を足す（添付の `file_uploader` の隣）

```python
        project_folder = st.text_input(
            "プロジェクトフォルダ（このマシン上のパス。空欄可）",
            key="project_folder",
            disabled=st.session_state.generating,
        )
```

2. フォルダを読む処理を足す。`_generate_document` と `_generate_freeform` の
   両方が使うので、`_collect_evidence` の中に置く。

```python
def _collect_project_files(folder, question, ask_json_call, result):
    """フォルダを走査して本文を読む。読めなければ None を返す。

    LLM を呼ぶ前にパスと対象件数を確かめるのは、呼んでから落ちると利用者が
    30〜60秒待たされたうえで何も受け取れないためである。
    """
    if not folder.strip():
        return [], ""
    root = Path(folder.strip())
    try:
        entries = docgen_project.tree(root)
    except docgen_project.ProjectFolderError as error:
        st.session_state.cowork_result = _cowork_error(str(error))
        return None
    if not entries:
        st.session_state.cowork_result = _cowork_error(
            f"{root} に取り込める形式のファイルがありません。"
        )
        return None
    try:
        chosen = docgen_project.select(entries, question, ask_json_call)
    except chat.ChatError as error:
        st.session_state.cowork_result = _cowork_error(str(error))
        return None
    if not chosen:
        result["warnings"].append(
            "読むファイルを選べませんでした。ファイル一覧だけを渡します。"
        )
    files, skipped = docgen_project.read(root, chosen)
    if skipped:
        result["warnings"].append(
            "読まなかったファイル: " + "、".join(skipped)
        )
    return files, docgen_project.tree_text(entries)
```

`from pathlib import Path` は既に import 済みである。

3. `_collect_evidence` がこれを呼び、返ってきた `files` を `texts` の**先頭**へ
   足す。プロジェクトの本文は「添付の自動版」であり、専用の受け口は作らない。

4. 「根拠が無い」の判定にフォルダを数える。

```python
                elif not use_internal and not use_docs and not attachments and not project_folder.strip():
```

（雛形ありの側の同じ判定も直すこと。両方にある）

5. 雛形なしの出力ファイル名にフォルダ名を使う（設計書8節）。Task 12 では
   `文書_{日付}` 固定にしてあるので、`_generate_freeform` の該当行を置き換える。

```python
    stem = Path(project_folder.strip()).name if project_folder.strip() else "文書"
    result["download"] = {
        "data": data,
        "file_name": f"{stem}_{date.today().isoformat()}{suffix}",
    }
```

6. 生成の最後に書き出す。`_generate_document` と `_generate_freeform` の両方で、
   `result["download"]` を組んだ直後に置く。

```python
    if project_folder.strip():
        try:
            written = docgen_project.write_output(
                Path(project_folder.strip()),
                result["download"]["file_name"],
                result["download"]["data"],
            )
        except OSError as error:
            # 書けなくても成果物そのものは渡す。ダウンロードボタンは出る。
            result["warnings"].append(f"フォルダへ書き出せませんでした: {error}")
        else:
            result["infos"].append(f"{written} に書き出しました。")
```

`_generate_freeform` / `_generate_document` の引数に `project_folder` を足すこと。

- [ ] **Step 3b: `AGENTS.md` の外部通信の記述を直す**

`AGENTS.md`「外部ドキュメントの参照」の4本目（`OLLAMA_HOST`）に、この経路へ
新しく乗るものを書き足す。宛先は増えないが、**乗るデータが増える**。

```markdown
  雛形からの文書生成に加え、雛形なしの生成（`docgen/freeform.py`）と
  プロジェクトフォルダの参照（`docgen/project.py`）もこの経路を使う。
  新しい宛先は増えないが、指定したフォルダのファイル一覧と、モデルが選んだ
  ファイルの本文が `ingest/chat.py` の `ask_json` / `ask_text` に渡り、この
  経路へ乗る。手元のソースコードを扱うときは `OLLAMA_HOST` がローカルを
  指していることを確かめること。
```

- [ ] **Step 4: テストが通ることを確認する**

```
./myvenv313/Scripts/python.exe -m pytest tests/test_rag_chat_app_cowork.py -q
```

Expected: PASS（22件）

- [ ] **Step 5: 全体のテストを回す**

```
./myvenv313/Scripts/python.exe -m pytest -q
```

Expected: PASS（既存の1,010件 + 新規分。失敗0件）

- [ ] **Step 6: README を更新する**

「使い方」の Cowork の節に足す。

```markdown
### 雛形なしで作る

雛形のプルダウンで「（雛形なし）」を選ぶと、出力形式（`.md` / `.docx` /
`.xlsx` / `.pptx`）を選んで、依頼文だけから文書を作れる。

「プロジェクトフォルダ」にこのマシン上のパスを入れると、その中のファイルを
根拠に使う。フォルダの全ファイルを渡すわけではない。まずファイル一覧を
モデルに見せて依頼に要るものを選ばせ、選ばれた分だけを読む（プロンプトの上限は
28,000字で、このリポジトリ程度のフォルダでも全文は 76倍ある）。

成果物は `<プロジェクト>/generated_docs/` に書き出す。同名があれば上書きせず
連番を付ける。このフォルダは走査から外してあるので、前回の成果物が次回の根拠に
混ざることはない。

文書の末尾には「参照したファイル」の節が入る。実際にモデルへ渡したファイルと
検索の出典だけを並べる。
```

「既知の制約」に足す。

```markdown
- **雛形なしの生成で読むファイルはモデルが選ぶ。** 選び方を誤れば、根拠に
  するべきファイルが渡らないまま文書が書かれる。「参照したファイル」の節に
  実際に渡したものが並ぶので、書かれた内容がおかしいときはまずそこを見ること。
- **`.xlsx` で図は出ない。** Mermaid のテキストがセルに入る。スライドも同じで、
  pptx は本文のプレースホルダに文字を流し込む作りのため、図は PNG にせず
  テキストのまま入る。図が要るなら `.md` か `.docx` を選ぶこと。
```

- [ ] **Step 7: コミット**

```bash
git add rag_chat_app.py README.md AGENTS.md tests/test_rag_chat_app_cowork.py
git commit -m "feat: use a project folder as evidence and write the result into it"
```

---

## 完了の確認

- [ ] `./myvenv313/Scripts/python.exe -m pytest -q` が失敗0件
- [ ] `docgen/project.py` の `EXCLUDED_DIR_NAMES` に `OUTPUT_DIR_NAME` が入っている
- [ ] 生成した文書の末尾に「参照したファイル」があり、渡していないファイル名が入っていない
- [ ] `requirements.txt` が変わっていない
- [ ] README の形式一覧と既知の制約が実装と合っている
