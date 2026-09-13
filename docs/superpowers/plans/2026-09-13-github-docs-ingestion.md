# GitHub からのドキュメント取り込み 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** C#・Go・Markdown・Mermaid の記法を、公式リポジトリの生 Markdown から
`docs_store.sqlite3` へ取り込む。

**Architecture:** 既存の `scripts/fetch_docs.py` に取得元の種別（`kind`）を足す。
`kind = "github"` のソースは Trees API で木を1回引き、本文を
`raw.githubusercontent.com` から取り、1ページ1ファイルで `docs_source/` へ書く。
取得後の経路（`ingest_source.py` → `parse_md` → `chunk_units` → `embedder`）は
**1行も変えない**。

**Tech Stack:** Python 3.13 / `requests`（既存依存）/ `tomllib`（標準ライブラリ）/
`posixpath`・`re`（標準ライブラリ）

**Spec:** `docs/superpowers/specs/2026-09-13-github-docs-ingestion-design.md`

## Global Constraints

- **新しい依存を追加しない。** `requests` は `requirements.txt` に既にある。
  `posixpath` `re` `tomllib` は標準ライブラリ。`requirements.txt` は変更しない。
- **テストからネットワークへ出ない。** HTTP はすべて偽のセッションで閉じる。
  実際に GitHub を叩くのは Task 7 の1回だけで、これは人が手で走らせる。
- **既存6件の取り込み結果を変えない。** `docs_sources.toml` の既存6件は1行も
  編集しない。`kind` の既定は `"llms"`、`resolve_code_refs` の既定は `False`。
- **`scripts/ingest_source.py` と `ingest/` 配下は触らない。** 既に
  サブフォルダを再帰し、相対パスを資料の識別子にする（`_target_files` /
  `_source_key`）。
- **外部 URL は絶対に辿らない。** `:::code` の解決先は、同じリポジトリ・同じ
  `ref` の木にある blob に限る。木に無いパスは取りに行かない。
- テストは `./myvenv313/Scripts/python.exe -m pytest` で走らせる。
- コミットメッセージは英語、コンベンショナルコミット形式。コード内のコメントと
  docstring は日本語（既存ファイルに合わせる）。

## ファイル構成

| ファイル | 責務 |
|---|---|
| `scripts/fetch_docs.py`（変更） | 設定の読み込み、`run()`、`main()`、`llms` 取得、書き出し |
| `scripts/github_source.py`（新規） | `GitHubSource`、木の取得、ページの選別、本文の取得、ページの整形 |
| `scripts/code_references.py`（新規） | `:::code` の解決だけ |
| `tests/test_fetch_docs.py`（変更） | 設定と `run()` |
| `tests/test_github_source.py`（新規） | 木・選別・整形 |
| `tests/test_code_references.py`（新規） | `:::code` の3形式と歯止め |

**設計書5.2節は「`fetch_docs.py` に GitHub 取得を足す」と書いているが、ここでは
モジュールを3つに分ける。** 却下したのは「別スクリプト＋別設定」（利用者が2つの
コマンドを覚える形）であって、モジュール分割ではない。`fetch_docs.py` は現在254行
で、木の取得・`:::code` の解決・Liquid 除去を1ファイルに足すと3倍になる。
利用者から見た入口は `python -m scripts.fetch_docs` の1つのままである。

---

### Task 1: 設定ファイルに `kind` を足す

**Files:**
- Modify: `scripts/fetch_docs.py:28-41`（`DocSource` と `load_sources`）
- Create: `scripts/github_source.py`
- Modify: `tests/test_fetch_docs.py`（`DocSource` の14箇所を改名）
- Test: `tests/test_fetch_docs.py`

**Interfaces:**
- Produces: `fetch_docs.LlmsSource(name: str, url: str, version: str)`(frozen dataclass)、
  `github_source.GitHubSource(name: str, repo: str, ref: str, paths: tuple[str, ...],
  version: str, resolve_code_refs: bool = False)`(frozen dataclass)、
  `fetch_docs.load_sources(path: Path) -> list[LlmsSource | GitHubSource]`

- [ ] **Step 1: 既存の `DocSource` を `LlmsSource` へ機械的に改名する**

`DocSource` は14箇所（`tests/test_fetch_docs.py`）＋6箇所（`scripts/fetch_docs.py`）で
使われている。名前だけの置換で、意味は変えない。

```bash
sed -i 's/DocSource/LlmsSource/g' scripts/fetch_docs.py tests/test_fetch_docs.py
```

`scripts/fetch_docs.py` の docstring を1行足す。

```python
@dataclass(frozen=True)
class LlmsSource:
    """`llms-full.txt` を1本の URL から取るソース（`kind = "llms"`、既定）。"""
    name: str
    url: str
    version: str
```

- [ ] **Step 2: 改名だけで全テストが通ることを確かめる**

Run: `./myvenv313/Scripts/python.exe -m pytest tests/test_fetch_docs.py -q`
Expected: PASS（21件）。ここで落ちたら置換し漏れである。

- [ ] **Step 3: 失敗するテストを書く**

`tests/test_fetch_docs.py` の末尾に足す。

```python
def test_load_sources_defaults_to_the_llms_kind(tmp_path):
    """kind を書かない既存の設定は、今までどおり LlmsSource になる。

    docs_sources.toml の既存6件は1行も編集しない方針である（設計書5.1節）。
    既定が変わると、その6件が黙って別の経路に入る。
    """
    config = tmp_path / "docs_sources.toml"
    config.write_text(
        '[[source]]\nname = "streamlit"\n'
        'url = "https://example.test/llms-full.txt"\nversion = "1.61.1"\n',
        encoding="utf-8",
    )
    assert fetch_docs.load_sources(config) == [
        fetch_docs.LlmsSource(
            name="streamlit", url="https://example.test/llms-full.txt", version="1.61.1"
        )
    ]


def test_load_sources_reads_a_github_source(tmp_path):
    config = tmp_path / "docs_sources.toml"
    config.write_text(
        '[[source]]\nname = "csharp"\nkind = "github"\n'
        'repo = "dotnet/docs"\nref = "main"\n'
        'paths = ["docs/csharp/language-reference", "docs/csharp/linq"]\n'
        "resolve_code_refs = true\nversion = \"0.0.0\"\n",
        encoding="utf-8",
    )
    assert fetch_docs.load_sources(config) == [
        github_source.GitHubSource(
            name="csharp",
            repo="dotnet/docs",
            ref="main",
            paths=("docs/csharp/language-reference", "docs/csharp/linq"),
            version="0.0.0",
            resolve_code_refs=True,
        )
    ]


def test_load_sources_defaults_resolve_code_refs_to_false(tmp_path):
    """:::code の解決は明示的に有効にしたソースでだけ走る（設計書5.4節）。

    参照を辿るのは AGENTS.md の「ページ内のリンクは辿らない」と関わる。
    既定で有効にすると、設定を書いた人が気付かないまま辿ることになる。
    """
    config = tmp_path / "docs_sources.toml"
    config.write_text(
        '[[source]]\nname = "mermaid"\nkind = "github"\n'
        'repo = "mermaid-js/mermaid"\nref = "develop"\n'
        'paths = ["packages/mermaid/src/docs"]\nversion = "0.0.0"\n',
        encoding="utf-8",
    )
    assert fetch_docs.load_sources(config)[0].resolve_code_refs is False


def test_load_sources_rejects_a_github_key_on_an_llms_source(tmp_path):
    """黙って無視すると、設定を直したつもりの人が直っていないことに気付けない。"""
    config = tmp_path / "docs_sources.toml"
    config.write_text(
        '[[source]]\nname = "streamlit"\n'
        'url = "https://example.test/llms-full.txt"\n'
        'repo = "dotnet/docs"\nversion = "1.0.0"\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="repo"):
        fetch_docs.load_sources(config)


def test_load_sources_rejects_a_url_on_a_github_source(tmp_path):
    config = tmp_path / "docs_sources.toml"
    config.write_text(
        '[[source]]\nname = "csharp"\nkind = "github"\n'
        'repo = "dotnet/docs"\nref = "main"\npaths = ["docs/csharp"]\n'
        'url = "https://example.test/llms-full.txt"\nversion = "0.0.0"\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="url"):
        fetch_docs.load_sources(config)


def test_load_sources_rejects_an_unknown_kind(tmp_path):
    config = tmp_path / "docs_sources.toml"
    config.write_text(
        '[[source]]\nname = "x"\nkind = "ftp"\nversion = "0.0.0"\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="ftp"):
        fetch_docs.load_sources(config)
```

冒頭の import に `from scripts import github_source` を足す。

- [ ] **Step 4: テストが落ちることを確かめる**

Run: `./myvenv313/Scripts/python.exe -m pytest tests/test_fetch_docs.py -q`
Expected: FAIL（`ModuleNotFoundError: No module named 'scripts.github_source'`）

- [ ] **Step 5: `scripts/github_source.py` を作る**

```python
"""GitHub のリポジトリから Markdown のページを取ってくる。

`llms-full.txt` を公開していない対象（C#・Go・Markdown・Mermaid）へ届かせる
ための経路である。設計書4.1節の実測のとおり、これらには他に経路が無い。

Trees API で木を1回引き、本文は raw.githubusercontent.com から取る。未認証で
足りる（実測 2026-09-13: 4リポジトリとも200。必要な呼び出しはリポジトリに
つき1回で、未認証枠は60回/時）。raw は CDN で API のレート制限の対象外である。

設定に書かれたリポジトリとパスしか取りに行かない。クローラーにはしない。
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class GitHubSource:
    """リポジトリの一部を取るソース（`kind = "github"`）。

    resolve_code_refs は既定で False。MS Learn の :::code を辿るのは
    AGENTS.md の「ページ内のリンクは辿らない」と関わるため、明示的に
    有効にしたソースでだけ走らせる（設計書5.4節）。
    """

    name: str
    repo: str
    ref: str
    paths: tuple[str, ...]
    version: str
    resolve_code_refs: bool = False
```

- [ ] **Step 6: `load_sources` を書き換える**

`scripts/fetch_docs.py` の `load_sources` を差し替える。

```python
# kind ごとに「使ってよいキー」を決めておく。混ざった設定を黙って無視すると、
# 設定を直したつもりの人が直っていないことに気付けない。
_LLMS_ONLY = ("url",)
_GITHUB_ONLY = ("repo", "ref", "paths", "resolve_code_refs")


def load_sources(path: Path = DEFAULT_CONFIG) -> list:
    """docs_sources.toml を読む。kind で LlmsSource か GitHubSource になる。"""
    with path.open("rb") as handle:
        config = tomllib.load(handle)
    return [_source_of(entry) for entry in config.get("source", [])]


def _source_of(entry: dict):
    kind = entry.get("kind", "llms")
    name = entry["name"]
    version = str(entry["version"])
    if kind == "llms":
        _reject(entry, _GITHUB_ONLY, name, kind)
        return LlmsSource(name=name, url=entry["url"], version=version)
    if kind == "github":
        _reject(entry, _LLMS_ONLY, name, kind)
        return github_source.GitHubSource(
            name=name,
            repo=entry["repo"],
            ref=entry["ref"],
            paths=tuple(entry["paths"]),
            version=version,
            resolve_code_refs=bool(entry.get("resolve_code_refs", False)),
        )
    raise ValueError(
        f"{name} の kind が不明です: {kind!r}（使えるのは \"llms\" か \"github\"）"
    )


def _reject(entry: dict, forbidden, name: str, kind: str) -> None:
    found = [key for key in forbidden if key in entry]
    if found:
        raise ValueError(
            f"{name} は kind = \"{kind}\" なので {'、'.join(found)} は書けません"
        )
```

冒頭の import に `from scripts import github_source` を足す。

- [ ] **Step 7: テストが通ることを確かめる**

Run: `./myvenv313/Scripts/python.exe -m pytest tests/test_fetch_docs.py -q`
Expected: PASS（27件）

- [ ] **Step 8: 全テストを走らせる**

Run: `./myvenv313/Scripts/python.exe -m pytest -q`
Expected: PASS（754 passed, 3 deselected）

- [ ] **Step 9: コミット**

```bash
git add scripts/fetch_docs.py scripts/github_source.py tests/test_fetch_docs.py
git commit -m "feat: let a documentation source declare where it comes from"
```

---

### Task 2: 木の取得とページの選別

**Files:**
- Modify: `scripts/github_source.py`
- Test: `tests/test_github_source.py`（新規）

**Interfaces:**
- Consumes: `github_source.GitHubSource`（Task 1）
- Produces: `github_source.Tree(commit: str, paths: tuple[str, ...])`(frozen dataclass)、
  `github_source.TreeTruncatedError`(Exception)、
  `github_source.fetch_tree(repo: str, ref: str, session) -> Tree`、
  `github_source.select_pages(tree: Tree, paths) -> tuple[str, ...]`、
  `github_source.fetch_blob(repo: str, ref: str, path: str, session) -> str`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_github_source.py` を新規作成する。

```python
"""GitHub からのページ取得。

ネットワークへは絶対に出ない。セッションを差し替えて、状態コードと本文を
こちらで決める。
"""
import pytest
import requests

from scripts import github_source


class _FakeResponse:
    def __init__(self, status_code=200, text="", payload=None):
        self.status_code = status_code
        self.text = text
        self._payload = payload
        self.headers = {"Content-Type": "text/plain"}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}", response=self)


class _FakeSession:
    """URLごとに返す応答を決め打ちする。要求されたURLは .urls に積む。"""

    def __init__(self, responses):
        self._responses = responses
        self.urls = []

    def get(self, url, timeout=None):
        self.urls.append(url)
        if url not in self._responses:
            return _FakeResponse(404)
        return self._responses[url]


def _tree_payload(paths, sha="abc123", truncated=False):
    return {
        "sha": sha,
        "truncated": truncated,
        "tree": [{"path": path, "type": "blob"} for path in paths],
    }


_TREE_URL = "https://api.github.com/repos/dotnet/docs/git/trees/main?recursive=1"


def test_fetch_tree_returns_the_commit_and_the_blob_paths():
    session = _FakeSession(
        {_TREE_URL: _FakeResponse(payload=_tree_payload(["a.md", "b.cs"], sha="deadbeef"))}
    )
    tree = github_source.fetch_tree("dotnet/docs", "main", session)
    assert tree.commit == "deadbeef"
    assert tree.paths == ("a.md", "b.cs")


def test_fetch_tree_ignores_directories():
    """木には blob（ファイル）と tree（ディレクトリ）が混ざって返る。"""
    payload = {
        "sha": "abc",
        "truncated": False,
        "tree": [
            {"path": "docs", "type": "tree"},
            {"path": "docs/a.md", "type": "blob"},
        ],
    }
    session = _FakeSession({_TREE_URL: _FakeResponse(payload=payload)})
    assert github_source.fetch_tree("dotnet/docs", "main", session).paths == ("docs/a.md",)


def test_fetch_tree_stops_when_github_truncated_the_tree():
    """部分的な木で取り込むと、一部のページだけが静かに欠ける。

    実測 2026-09-13 では4リポジトリとも truncated は偽だった（最大は
    dotnet/docs の28,268エントリ）。だからといって黙って続けない。欠けたことが
    取り込み後まで分からない壊れ方は、今回いちばん避けたいものである
    （設計書5.2節）。
    """
    session = _FakeSession(
        {_TREE_URL: _FakeResponse(payload=_tree_payload(["a.md"], truncated=True))}
    )
    with pytest.raises(github_source.TreeTruncatedError, match="dotnet/docs"):
        github_source.fetch_tree("dotnet/docs", "main", session)


def test_fetch_tree_raises_on_an_http_error():
    session = _FakeSession({})
    with pytest.raises(requests.HTTPError):
        github_source.fetch_tree("dotnet/docs", "main", session)


def test_select_pages_keeps_only_markdown_under_the_given_paths():
    tree = github_source.Tree(
        commit="abc",
        paths=(
            "docs/csharp/linq/a.md",
            "docs/csharp/linq/snippets/Program.cs",
            "docs/csharp/misc/cs0003.md",
            "README.md",
        ),
    )
    assert github_source.select_pages(tree, ["docs/csharp/linq"]) == (
        "docs/csharp/linq/a.md",
    )


def test_select_pages_does_not_match_a_sibling_with_the_same_prefix():
    """docs/csharp/how は docs/csharp/how-to を拾ってはいけない。

    前方一致を文字列だけで見ると拾ってしまう。実際の設定には
    docs/csharp/how-to と docs/csharp/tutorials が並んでおり、取り違えると
    意図しないページが混ざる。
    """
    tree = github_source.Tree(
        commit="abc",
        paths=("docs/csharp/how-to/a.md", "docs/csharp/how/b.md"),
    )
    assert github_source.select_pages(tree, ["docs/csharp/how"]) == (
        "docs/csharp/how/b.md",
    )


def test_select_pages_returns_a_sorted_deterministic_order():
    """並びが揺れると、取得の進捗表示も失敗の再現も追えなくなる。"""
    tree = github_source.Tree(commit="abc", paths=("d/b.md", "d/a.md", "d/c.md"))
    assert github_source.select_pages(tree, ["d"]) == ("d/a.md", "d/b.md", "d/c.md")


def test_fetch_blob_reads_from_the_raw_host():
    url = "https://raw.githubusercontent.com/dotnet/docs/main/docs/a.md"
    session = _FakeSession({url: _FakeResponse(text="# A\n")})
    assert github_source.fetch_blob("dotnet/docs", "main", "docs/a.md", session) == "# A\n"
    assert session.urls == [url]


def test_fetch_blob_raises_on_an_http_error():
    session = _FakeSession({})
    with pytest.raises(requests.HTTPError):
        github_source.fetch_blob("dotnet/docs", "main", "docs/a.md", session)
```

- [ ] **Step 2: テストが落ちることを確かめる**

Run: `./myvenv313/Scripts/python.exe -m pytest tests/test_github_source.py -q`
Expected: FAIL（`AttributeError: module 'scripts.github_source' has no attribute 'Tree'`）

- [ ] **Step 3: 実装する**

`scripts/github_source.py` に足す。

```python
API = "https://api.github.com"
RAW = "https://raw.githubusercontent.com"

# 9MBのJSONが返ることがある（実測 2026-09-13: dotnet/docs は 9,265,802 バイト）。
# 既定の無制限だと、応答が返らないサイトでプロセスが止まったままになる。
_TIMEOUT = 60


class TreeTruncatedError(Exception):
    """木が大きすぎて GitHub が切り詰めた。

    部分的な木で取り込むと、一部のページだけが静かに欠ける。取り込みは成功と
    表示され、検索も当たり、ただ答えられない質問が増えるだけになる。掴んだ
    時点で止める（設計書5.2節）。
    """


@dataclass(frozen=True)
class Tree:
    commit: str
    paths: tuple[str, ...]


def fetch_tree(repo: str, ref: str, session) -> Tree:
    """リポジトリの木を1回で引く。blob のパスだけを持つ。"""
    response = session.get(f"{API}/repos/{repo}/git/trees/{ref}?recursive=1", timeout=_TIMEOUT)
    response.raise_for_status()
    payload = response.json()
    if payload.get("truncated"):
        raise TreeTruncatedError(
            f"{repo}@{ref} の木が大きすぎて GitHub が切り詰めました。"
            "このまま取り込むと一部のページが欠けます"
        )
    return Tree(
        commit=payload["sha"],
        paths=tuple(
            entry["path"] for entry in payload["tree"] if entry.get("type") == "blob"
        ),
    )


def select_pages(tree: Tree, paths) -> tuple[str, ...]:
    """paths のいずれかの下にある .md を、並びを決めて返す。

    区切りの "/" まで含めて比べるのは、docs/csharp/how が
    docs/csharp/how-to を拾わないようにするため。実際の設定にこの2つが
    並んでいる。
    """
    prefixes = tuple(f"{path.rstrip('/')}/" for path in paths)
    return tuple(
        sorted(
            path
            for path in tree.paths
            if path.endswith(".md") and path.startswith(prefixes)
        )
    )


def fetch_blob(repo: str, ref: str, path: str, session) -> str:
    """1ファイルの本文を raw から取る。CDN なので API のレート制限を使わない。"""
    response = session.get(f"{RAW}/{repo}/{ref}/{path}", timeout=_TIMEOUT)
    response.raise_for_status()
    return response.text
```

- [ ] **Step 4: テストが通ることを確かめる**

Run: `./myvenv313/Scripts/python.exe -m pytest tests/test_github_source.py -q`
Expected: PASS（9件）

- [ ] **Step 5: コミット**

```bash
git add scripts/github_source.py tests/test_github_source.py
git commit -m "feat: list and download documentation pages from a repository tree"
```

---

### Task 3: `:::code` の解決器

**Files:**
- Create: `scripts/code_references.py`
- Test: `tests/test_code_references.py`（新規）

**Interfaces:**
- Produces: `code_references.resolve_code_references(text: str, source_path: str,
  blob_paths, fetch) -> tuple[str, int]`
  （戻り値は「置換後の本文」と「解決できなかった参照の件数」。
  `blob_paths` はパスの集合、`fetch` は `fetch(path: str) -> str` の呼び出し可能）

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_code_references.py` を新規作成する。

```python
""":::code の解決。

MS Learn 形式のドキュメントは、コード例を外部ファイルへの参照で書く。
実測 2026-09-13 では、C# のどのサブディレクトリでも参照の割合が33%〜93%
あり、解決しないと「検索は当たるのにコードが書けない」状態になる
（設計書4.5節）。
"""
from scripts import code_references


def _fetcher(files):
    def fetch(path):
        return files[path]

    return fetch


def test_a_reference_without_a_selector_inlines_the_whole_file():
    text = ':::code language="csharp" source="snippets/Program.cs":::\n'
    files = {"docs/csharp/snippets/Program.cs": "int x = 1;\nint y = 2;\n"}
    resolved, unresolved = code_references.resolve_code_references(
        text, "docs/csharp/a.md", set(files), _fetcher(files)
    )
    assert resolved == "```csharp\nint x = 1;\nint y = 2;\n```\n"
    assert unresolved == 0


def test_an_id_selector_inlines_only_that_region():
    """id= は .cs 側の #region 〜 #endregion を指す。"""
    text = ':::code language="csharp" source="snippets/P.cs" id="Snippet1":::\n'
    files = {
        "docs/csharp/snippets/P.cs": (
            "using System;\n"
            "#region Snippet1\n"
            "Console.WriteLine(1);\n"
            "#endregion\n"
            "// tail\n"
        )
    }
    resolved, unresolved = code_references.resolve_code_references(
        text, "docs/csharp/a.md", set(files), _fetcher(files)
    )
    assert resolved == "```csharp\nConsole.WriteLine(1);\n```\n"
    assert unresolved == 0


def test_an_id_selector_removes_the_shared_indentation():
    """#region の中は class の内側にあり、丸ごと字下げされている。

    字下げのまま差し込むと、そのままでは動かないコードが例として出る。
    """
    text = ':::code language="csharp" source="snippets/P.cs" id="S":::\n'
    files = {
        "docs/csharp/snippets/P.cs": (
            "class C {\n    #region S\n    int a = 1;\n    int b = 2;\n    #endregion\n}\n"
        )
    }
    resolved, _ = code_references.resolve_code_references(
        text, "docs/csharp/a.md", set(files), _fetcher(files)
    )
    assert resolved == "```csharp\nint a = 1;\nint b = 2;\n```\n"


def test_a_range_selector_inlines_those_lines_inclusive():
    """range="2-3" は2行目と3行目の両方を含む（1始まり）。"""
    text = ':::code language="csharp" source="snippets/P.cs" range="2-3":::\n'
    files = {"docs/csharp/snippets/P.cs": "a\nb\nc\nd\n"}
    resolved, unresolved = code_references.resolve_code_references(
        text, "docs/csharp/a.md", set(files), _fetcher(files)
    )
    assert resolved == "```csharp\nb\nc\n```\n"
    assert unresolved == 0


def test_a_relative_parent_path_is_resolved():
    text = ':::code language="csharp" source="../shared/P.cs":::\n'
    files = {"docs/csharp/shared/P.cs": "ok\n"}
    resolved, unresolved = code_references.resolve_code_references(
        text, "docs/csharp/linq/a.md", set(files), _fetcher(files)
    )
    assert resolved == "```csharp\nok\n```\n"
    assert unresolved == 0


def test_a_reference_outside_the_tree_is_not_fetched():
    """木に無いパスは取りに行かない。外部 URL は絶対に辿らない（設計書5.4節）。

    AGENTS.md は「設定に書かれたURLしか取りに行かない。ページ内のリンクは
    辿らない」と約束している。解決先を同じ木の中に限ることが、その約束を
    保つ唯一の歯止めである。
    """
    asked = []

    def fetch(path):
        asked.append(path)
        return "should not be read"

    text = ':::code language="csharp" source="snippets/Missing.cs":::\n'
    resolved, unresolved = code_references.resolve_code_references(
        text, "docs/csharp/a.md", set(), fetch
    )
    assert asked == []
    assert resolved == text
    assert unresolved == 1


def test_an_unknown_region_leaves_the_directive_and_is_counted():
    """黙って落とすと、コードの入っていないページが混ざったことに気付けない。"""
    text = ':::code language="csharp" source="snippets/P.cs" id="Nope":::\n'
    files = {"docs/csharp/snippets/P.cs": "#region Other\nx\n#endregion\n"}
    resolved, unresolved = code_references.resolve_code_references(
        text, "docs/csharp/a.md", set(files), _fetcher(files)
    )
    assert resolved == text
    assert unresolved == 1


def test_text_without_any_directive_is_returned_unchanged():
    text = "# Records\n\n```csharp\nint x = 1;\n```\n"
    resolved, unresolved = code_references.resolve_code_references(
        text, "docs/csharp/a.md", set(), _fetcher({})
    )
    assert resolved == text
    assert unresolved == 0


def test_several_directives_in_one_page_are_all_resolved():
    text = (
        "# A\n"
        ':::code language="csharp" source="s/One.cs":::\n'
        "text between\n"
        ':::code language="csharp" source="s/Two.cs":::\n'
    )
    files = {"docs/csharp/s/One.cs": "one\n", "docs/csharp/s/Two.cs": "two\n"}
    resolved, unresolved = code_references.resolve_code_references(
        text, "docs/csharp/a.md", set(files), _fetcher(files)
    )
    assert resolved == (
        "# A\n```csharp\none\n```\ntext between\n```csharp\ntwo\n```\n"
    )
    assert unresolved == 0


def test_a_missing_language_falls_back_to_csharp():
    """language= を書かないページがある。タグ無しのフェンスにすると、
    チャンカーがコードとして扱えるかが読み手の目に頼ることになる。"""
    text = ':::code source="s/P.cs":::\n'
    files = {"docs/csharp/s/P.cs": "x\n"}
    resolved, _ = code_references.resolve_code_references(
        text, "docs/csharp/a.md", set(files), _fetcher(files)
    )
    assert resolved == "```csharp\nx\n```\n"
```

- [ ] **Step 2: テストが落ちることを確かめる**

Run: `./myvenv313/Scripts/python.exe -m pytest tests/test_code_references.py -q`
Expected: FAIL（`ModuleNotFoundError: No module named 'scripts.code_references'`）

- [ ] **Step 3: 実装する**

`scripts/code_references.py` を新規作成する。

```python
"""MS Learn の :::code を、参照先のコードに置き換える。

C# のドキュメントはコード例を本文に書かず、外部ファイルへの参照で書く。

    :::code language="csharp" source="snippets/P.cs" id="Snippet1":::

実測 2026-09-13 では、C# のどのサブディレクトリでも参照の割合が33%〜93%
あった。このまま取り込むと、検索は当たるのにコードが書けない状態になる。
`llms.txt`（本文ではなく目次）を掴んだときと同じ壊れ方である。

解決先は呼び出し側が渡す blob_paths の中に限る。これは AGENTS.md の
「設定に書かれたURLしか取りに行かない。ページ内のリンクは辿らない」を
保つための歯止めである。外部 URL は辿らない。
"""
import posixpath
import re
import textwrap

# 行まるごとが1つの指令である。本文の途中に出てくる ::: は拾わない。
_DIRECTIVE = re.compile(r"^:::code\s+(?P<attrs>.*?):::[ \t]*$", re.MULTILINE)
_ATTRIBUTE = re.compile(r'(\w[\w-]*)="([^"]*)"')

# language= を書かないページがある。このモジュールを使うのは C# の資料だけ
# なので、既定を csharp にする。タグ無しのフェンスにすると、チャンカーが
# コードとして扱えるかが読み手の目に頼ることになる。
_DEFAULT_LANGUAGE = "csharp"


def resolve_code_references(text: str, source_path: str, blob_paths, fetch):
    """:::code を参照先のコードに置き換える。

    (置換後の本文, 解決できなかった参照の件数) を返す。解決できなかった参照は
    元の行のまま残す。黙って落とすと、コードの入っていないページが混ざった
    ことに気付けない。
    """
    unresolved = 0
    cache: dict[str, str] = {}

    def replace(match: re.Match) -> str:
        nonlocal unresolved
        attributes = dict(_ATTRIBUTE.findall(match.group("attrs")))
        target = _target_of(attributes.get("source", ""), source_path)
        if target is None or target not in blob_paths:
            unresolved += 1
            return match.group(0)
        if target not in cache:
            cache[target] = fetch(target)
        snippet = _selected(cache[target], attributes)
        if snippet is None:
            unresolved += 1
            return match.group(0)
        language = attributes.get("language") or _DEFAULT_LANGUAGE
        return f"```{language}\n{snippet}\n```"

    return _DIRECTIVE.sub(replace, text), unresolved


def _target_of(source: str, source_path: str) -> str | None:
    """source= を、リポジトリのルートからのパスに直す。

    木の外（先頭が ..）を指すものは解決しない。木の中にしか無いことが
    歯止めの前提であり、外を指す時点でその前提が崩れている。
    """
    if not source:
        return None
    joined = posixpath.join(posixpath.dirname(source_path), source)
    target = posixpath.normpath(joined)
    if target.startswith("..") or target.startswith("/"):
        return None
    return target


def _selected(code: str, attributes: dict) -> str | None:
    if "id" in attributes:
        return _region(code, attributes["id"])
    if "range" in attributes:
        return _range(code, attributes["range"])
    return code.strip("\n")


def _region(code: str, name: str) -> str | None:
    """#region <name> 〜 #endregion の中身。

    字下げを落とすのは、#region の中が class の内側にあって丸ごと
    字下げされているためである。そのまま差し込むと動かないコードになる。
    """
    start = re.search(rf"^[ \t]*#region[ \t]+{re.escape(name)}[ \t]*$", code, re.MULTILINE)
    if start is None:
        return None
    rest = code[start.end():]
    end = re.search(r"^[ \t]*#endregion", rest, re.MULTILINE)
    body = rest[: end.start()] if end else rest
    return textwrap.dedent(body).strip("\n")


def _range(code: str, spec: str) -> str | None:
    """range="12-24" は12行目から24行目まで（1始まり、両端を含む）。"""
    first, _, last = spec.partition("-")
    try:
        start = int(first)
        stop = int(last) if last else start
    except ValueError:
        return None
    if start < 1 or stop < start:
        return None
    lines = code.splitlines()
    if start > len(lines):
        return None
    return "\n".join(lines[start - 1 : stop])
```

- [ ] **Step 4: テストが通ることを確かめる**

Run: `./myvenv313/Scripts/python.exe -m pytest tests/test_code_references.py -q`
Expected: PASS（10件）

- [ ] **Step 5: コミット**

```bash
git add scripts/code_references.py tests/test_code_references.py
git commit -m "feat: inline the code a MS Learn page points at"
```

---

### Task 4: ページの整形と書き出し

**Files:**
- Modify: `scripts/github_source.py`
- Modify: `scripts/fetch_docs.py:129-167`（`_body_of` と `write_if_changed` の近く）
- Test: `tests/test_github_source.py`、`tests/test_fetch_docs.py`

**Interfaces:**
- Consumes: `github_source.GitHubSource`（Task 1）、`github_source.Tree`（Task 2）
- Produces: `github_source.strip_liquid(text: str) -> str`、
  `github_source.title_of(text: str) -> str`、
  `github_source.without_frontmatter(text: str) -> str`、
  `github_source.common_prefix(paths) -> str`、
  `github_source.local_path(page_path: str, paths) -> str`、
  `github_source.render_page(source: GitHubSource, commit: str, page_path: str,
  body: str, fetched_at: str) -> str`、
  `fetch_docs.write_page_if_changed(relative_path: str, text: str, out_dir: Path) -> bool`

- [ ] **Step 1: 失敗するテストを書く（整形）**

`tests/test_github_source.py` の末尾に足す。

```python
def test_without_frontmatter_drops_the_original_yaml():
    text = "---\ntitle: Records\nms.date: 06/05/2026\n---\n# Records\n\nbody\n"
    assert github_source.without_frontmatter(text) == "# Records\n\nbody\n"


def test_without_frontmatter_leaves_a_page_that_has_none():
    text = "# Records\n\nbody\n"
    assert github_source.without_frontmatter(text) == text


def test_without_frontmatter_leaves_a_horizontal_rule_in_the_body():
    """本文中の --- は区切り線であってフロントマターではない。"""
    text = "# A\n\n---\n\nB\n"
    assert github_source.without_frontmatter(text) == text


def test_title_of_reads_the_original_frontmatter():
    text = '---\ntitle: "Records"\nms.date: 06/05/2026\n---\n# X\n'
    assert github_source.title_of(text) == "Records"


def test_title_of_falls_back_to_the_first_heading():
    assert github_source.title_of("# Flowcharts Syntax\n\nbody\n") == "Flowcharts Syntax"


def test_title_of_returns_an_empty_string_when_there_is_neither():
    assert github_source.title_of("body only\n") == ""


def test_strip_liquid_removes_the_template_tags():
    """github/docs には Liquid の記法が215箇所ある（実測 2026-09-13）。

    取り込んでも記法の説明にならず、チャンクの本文を薄めるだけである。
    """
    text = "product: {% data reusables.gated-features.markdown-ui %}\ndone\n"
    assert github_source.strip_liquid(text) == "product: \ndone\n"


def test_strip_liquid_leaves_a_lone_brace_in_the_body():
    """コード例の { を消してはいけない。"""
    text = "int x = 1; { y }\n"
    assert github_source.strip_liquid(text) == text


def test_local_path_strips_the_prefix_the_configured_paths_share():
    """docs_source/csharp/docs/csharp/... という二重の入れ子を避ける。

    設定の paths が共有する一番深いディレクトリまでを落とす。csharp の10個の
    paths は docs/csharp/ を共有するので、置き場所は
    docs_source/csharp/language-reference/... になる（設計書5.3節）。
    """
    paths = ["docs/csharp/language-reference", "docs/csharp/linq"]
    assert github_source.common_prefix(paths) == "docs/csharp"
    assert (
        github_source.local_path("docs/csharp/language-reference/keywords/a.md", paths)
        == "language-reference/keywords/a.md"
    )


def test_local_path_strips_a_single_configured_path_entirely():
    paths = ["packages/mermaid/src/docs"]
    assert (
        github_source.local_path("packages/mermaid/src/docs/syntax/flowchart.md", paths)
        == "syntax/flowchart.md"
    )


def test_local_path_keeps_the_part_that_tells_the_two_paths_apart():
    """go の _content/doc と _content/ref は _content までしか共有しない。"""
    paths = ["_content/doc", "_content/ref"]
    assert github_source.common_prefix(paths) == "_content"
    assert github_source.local_path("_content/ref/mod.md", paths) == "ref/mod.md"


def test_render_page_writes_the_frontmatter_with_the_commit_and_the_source_path():
    source = github_source.GitHubSource(
        name="csharp",
        repo="dotnet/docs",
        ref="main",
        paths=("docs/csharp/linq",),
        version="0.0.0",
    )
    rendered = github_source.render_page(
        source,
        commit="deadbeef",
        page_path="docs/csharp/linq/a.md",
        body="---\ntitle: Query\n---\n# Query\n\nbody\n",
        fetched_at="2026-09-13",
    )
    assert rendered == (
        "---\n"
        "name: csharp\n"
        "repo: dotnet/docs\n"
        "ref: main\n"
        "commit: deadbeef\n"
        "source_path: docs/csharp/linq/a.md\n"
        "title: Query\n"
        "version: 0.0.0\n"
        "fetched_at: 2026-09-13\n"
        "---\n"
        "# Query\n\nbody\n"
    )


def test_render_page_output_parses_as_markdown_with_the_attributes(tmp_path):
    """ingest/parsers/md_parser.py がフロントマターを属性として読めること。

    書き出した形が取り込み側の想定から外れていると、取り込みの段になって
    初めて分かる。ここで繋げておく。
    """
    from ingest.parsers.md_parser import parse_md

    source = github_source.GitHubSource(
        name="mermaid",
        repo="mermaid-js/mermaid",
        ref="develop",
        paths=("packages/mermaid/src/docs",),
        version="0.0.0",
    )
    rendered = github_source.render_page(
        source,
        commit="abc",
        page_path="packages/mermaid/src/docs/syntax/flowchart.md",
        body="---\ntitle: Flowcharts Syntax\n---\n# Flowcharts\n\n## Nodes\n\nbody\n",
        fetched_at="2026-09-13",
    )
    path = tmp_path / "flowchart.md"
    path.write_text(rendered, encoding="utf-8")
    units = parse_md(path)
    assert units
    assert units[0].attributes["name"] == "mermaid"
    assert units[0].attributes["source_path"] == (
        "packages/mermaid/src/docs/syntax/flowchart.md"
    )
```

- [ ] **Step 2: テストが落ちることを確かめる**

Run: `./myvenv313/Scripts/python.exe -m pytest tests/test_github_source.py -q`
Expected: FAIL（`AttributeError: module 'scripts.github_source' has no attribute 'without_frontmatter'`）

- [ ] **Step 3: 整形を実装する**

`scripts/github_source.py` に足す。冒頭の import に `import re` を足す。

```python
# {% ... %} は Liquid のテンプレート記法。github/docs が使っている
# （実測 2026-09-13: 215箇所）。記法の説明にはならず、チャンクの本文を
# 薄めるだけなので取り込む前に落とす。{ の1文字だけでは消さない。
# コード例の { を消すと、載せている例が壊れる。
_LIQUID = re.compile(r"\{%.*?%\}", re.DOTALL)
_TITLE = re.compile(r'^title:\s*"?(?P<title>.*?)"?\s*$', re.MULTILINE)
_HEADING = re.compile(r"^#\s+(?P<title>.+?)\s*$", re.MULTILINE)


def strip_liquid(text: str) -> str:
    return _LIQUID.sub("", text)


def without_frontmatter(text: str) -> str:
    """元ファイルの YAML フロントマターを落とす。

    落とすのは、こちらのフロントマター（name / repo / commit / source_path）へ
    置き換えるためである。残すと --- が2組並び、取り込み側は先頭しか読まない。
    """
    if not text.startswith("---\n"):
        return text
    _, separator, rest = text[4:].partition("\n---\n")
    if not separator:
        return text
    return rest


def title_of(text: str) -> str:
    """元のフロントマターの title。無ければ最初の見出し。どちらも無ければ空。"""
    head = text[4:].partition("\n---\n")[0] if text.startswith("---\n") else ""
    found = _TITLE.search(head)
    if found:
        return found.group("title")
    found = _HEADING.search(without_frontmatter(text))
    return found.group("title") if found else ""


def common_prefix(paths) -> str:
    """設定に書いた paths が共有する一番深いディレクトリ。"""
    segments = [path.strip("/").split("/") for path in paths]
    shared: list[str] = []
    for parts in zip(*segments):
        if len(set(parts)) != 1:
            break
        shared.append(parts[0])
    return "/".join(shared)


def local_path(page_path: str, paths) -> str:
    """docs_source/<name>/ の下に置くときの相対パス。

    設定した paths の共通部分を落とす。落とさないと
    docs_source/csharp/docs/csharp/... と入れ子が二重になり、画面に出る出典が
    読みにくくなる（設計書5.3節の例は docs_source/csharp/language-reference/...）。
    """
    prefix = common_prefix(paths)
    if prefix and page_path.startswith(f"{prefix}/"):
        return page_path[len(prefix) + 1 :]
    return page_path


def render_page(
    source: GitHubSource, commit: str, page_path: str, body: str, fetched_at: str
) -> str:
    """1ページを docs_source/ へ書く形に整える。

    commit を持つのは、llms-full.txt では取れない再現性がここでは取れるため
    である。どの時点の木から取ったかが後から分かる。
    """
    return (
        "---\n"
        f"name: {source.name}\n"
        f"repo: {source.repo}\n"
        f"ref: {source.ref}\n"
        f"commit: {commit}\n"
        f"source_path: {page_path}\n"
        f"title: {title_of(body)}\n"
        f"version: {source.version}\n"
        f"fetched_at: {fetched_at}\n"
        "---\n"
    ) + without_frontmatter(body)
```

- [ ] **Step 4: テストが通ることを確かめる**

Run: `./myvenv313/Scripts/python.exe -m pytest tests/test_github_source.py -q`
Expected: PASS（22件）

- [ ] **Step 5: 書き出しの失敗するテストを書く**

`tests/test_fetch_docs.py` の末尾に足す。

```python
def test_write_page_if_changed_creates_the_nested_directories(tmp_path):
    written = fetch_docs.write_page_if_changed(
        "csharp/linq/a.md", "---\nname: csharp\n---\n# A\n", tmp_path
    )
    assert written is True
    assert (tmp_path / "csharp" / "linq" / "a.md").read_text(encoding="utf-8") == (
        "---\nname: csharp\n---\n# A\n"
    )


def test_write_page_if_changed_does_not_rewrite_an_unchanged_body(tmp_path):
    """fetched_at はフロントマターにある。含めて比べると、内容が同じでも
    取得日が違えば必ず「変わった」ことになり、差分検知が意味をなさなくなる。"""
    first = "---\nname: csharp\nfetched_at: 2026-09-13\n---\n# A\n"
    second = "---\nname: csharp\nfetched_at: 2026-09-20\n---\n# A\n"
    assert fetch_docs.write_page_if_changed("csharp/a.md", first, tmp_path) is True
    assert fetch_docs.write_page_if_changed("csharp/a.md", second, tmp_path) is False


def test_write_page_if_changed_rewrites_a_changed_body(tmp_path):
    fetch_docs.write_page_if_changed("csharp/a.md", "---\nname: c\n---\n# A\n", tmp_path)
    assert (
        fetch_docs.write_page_if_changed("csharp/a.md", "---\nname: c\n---\n# B\n", tmp_path)
        is True
    )


def test_write_page_if_changed_rejects_a_parent_directory_reference(tmp_path):
    """木の内容は設定ファイルと違ってバージョン管理下に無い入力である。

    name だけでなく、GitHub から来るパスにも同じ検査を通す（設計書5.3節）。
    """
    with pytest.raises(ValueError):
        fetch_docs.write_page_if_changed("csharp/../../evil.md", "x", tmp_path)
```

- [ ] **Step 6: テストが落ちることを確かめる**

Run: `./myvenv313/Scripts/python.exe -m pytest tests/test_fetch_docs.py -q`
Expected: FAIL（`AttributeError: module 'scripts.fetch_docs' has no attribute 'write_page_if_changed'`）

- [ ] **Step 7: 書き出しを実装する**

`scripts/fetch_docs.py` の `_body_of` を、文字列を受ける関数に分けてから使い回す。

```python
def _without_frontmatter(text: str) -> str:
    """フロントマターを飛ばして本文だけを返す。

    そこに fetched_at が入っているためである。含めて比べると、内容が同じでも
    取得日が違えば必ず「変わった」ことになり、差分検知が意味をなさなくなる。
    """
    if not text.startswith("---\n"):
        return text
    _, _, rest = text[4:].partition("---\n")
    return rest


def _body_of(path: Path) -> str:
    """書き出し済みファイルから本文だけを取り出す。無ければ空文字。"""
    if not path.is_file():
        return ""
    return _without_frontmatter(path.read_text(encoding="utf-8"))


def write_page_if_changed(relative_path: str, text: str, out_dir: Path) -> bool:
    """1ページを書く。本文が変わっていなければ書かずに False を返す。

    text にはフロントマターを含めて渡す。比べるのは本文だけである。
    """
    # 木の内容は設定ファイルと違ってバージョン管理下に無い入力である。
    # ".." を含むパスを素通しすると out_dir の外へ書き出せてしまう。
    if ".." in relative_path.split("/") or relative_path.startswith("/"):
        raise ValueError(f"ページのパスが不正です: {relative_path!r}")
    path = out_dir / relative_path
    if _digest(_body_of(path)) == _digest(_without_frontmatter(text)):
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True
```

- [ ] **Step 8: テストが通ることを確かめる**

Run: `./myvenv313/Scripts/python.exe -m pytest tests/test_fetch_docs.py tests/test_github_source.py -q`
Expected: PASS

- [ ] **Step 9: 全テストを走らせる**

Run: `./myvenv313/Scripts/python.exe -m pytest -q`
Expected: PASS（既存の21件を含めて1件も落ちない）

- [ ] **Step 10: コミット**

```bash
git add scripts/github_source.py scripts/fetch_docs.py tests/test_github_source.py tests/test_fetch_docs.py
git commit -m "feat: render a repository page into an ingestible document"
```

---

### Task 5: `run()` に GitHub 経路を繋ぐ

**Files:**
- Modify: `scripts/fetch_docs.py:170-249`（`FetchReport`、`run`、`main`）
- Test: `tests/test_fetch_docs.py`

**Interfaces:**
- Consumes: Task 1〜4 のすべて
- Produces: `FetchReport` に `pages_written: dict[str, int]`、
  `pages_failed: dict[str, int]`、`unresolved_code_refs: dict[str, int]` を追加

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_fetch_docs.py` の末尾に足す。`_FakeSession` は既存のものを使う
（`payload` を返せるよう `_FakeResponse` に `json()` を足す）。

まず既存の `_FakeResponse` を差し替える。

```python
class _FakeResponse:
    def __init__(self, status_code, text="", content_type="text/plain", payload=None):
        self.status_code = status_code
        self.text = text
        self.headers = {"Content-Type": content_type}
        self._payload = payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}", response=self)
```

そのうえでテストを足す。

```python
_CSHARP = github_source.GitHubSource(
    name="csharp",
    repo="dotnet/docs",
    ref="main",
    paths=("docs/csharp/linq",),
    version="0.0.0",
    resolve_code_refs=True,
)

_TREE = "https://api.github.com/repos/dotnet/docs/git/trees/main?recursive=1"
_RAW = "https://raw.githubusercontent.com/dotnet/docs/main"


def _tree_response(paths, sha="abc", truncated=False):
    return _FakeResponse(
        200,
        payload={
            "sha": sha,
            "truncated": truncated,
            "tree": [{"path": path, "type": "blob"} for path in paths],
        },
    )


def test_run_writes_one_file_per_page_under_the_source_name(tmp_path):
    session = _FakeSession(
        {
            _TREE: _tree_response(["docs/csharp/linq/a.md", "docs/csharp/linq/b.md"]),
            f"{_RAW}/docs/csharp/linq/a.md": _FakeResponse(200, "# A\n"),
            f"{_RAW}/docs/csharp/linq/b.md": _FakeResponse(200, "# B\n"),
        }
    )
    report = fetch_docs.run([_CSHARP], tmp_path, "2026-09-13", session=session)
    assert report.pages_written == {"csharp": 2}
    # _CSHARP の paths は ("docs/csharp/linq",) の1つだけなので、共通部分は
    # それ自身になる。置き場所は docs_source/csharp/a.md である。
    assert (tmp_path / "csharp" / "a.md").is_file()


def test_run_resolves_code_references_when_the_source_enables_it(tmp_path):
    session = _FakeSession(
        {
            _TREE: _tree_response(
                ["docs/csharp/linq/a.md", "docs/csharp/linq/snippets/P.cs"]
            ),
            f"{_RAW}/docs/csharp/linq/a.md": _FakeResponse(
                200, ':::code language="csharp" source="snippets/P.cs":::\n'
            ),
            f"{_RAW}/docs/csharp/linq/snippets/P.cs": _FakeResponse(200, "int x = 1;\n"),
        }
    )
    fetch_docs.run([_CSHARP], tmp_path, "2026-09-13", session=session)
    written = (tmp_path / "csharp" / "a.md").read_text(encoding="utf-8")
    assert "```csharp\nint x = 1;\n```" in written
    assert ":::code" not in written


def test_run_does_not_resolve_code_references_when_the_source_disables_it(tmp_path):
    """既定は無効である。設定に書いていないソースで参照を辿ってはいけない。"""
    source = github_source.GitHubSource(
        name="go",
        repo="golang/website",
        ref="master",
        paths=("_content/doc",),
        version="0.0.0",
    )
    tree = "https://api.github.com/repos/golang/website/git/trees/master?recursive=1"
    raw = "https://raw.githubusercontent.com/golang/website/master"
    directive = ':::code language="csharp" source="snippets/P.cs":::\n'
    session = _FakeSession(
        {
            tree: _tree_response(["_content/doc/a.md", "_content/doc/snippets/P.cs"]),
            f"{raw}/_content/doc/a.md": _FakeResponse(200, directive),
            f"{raw}/_content/doc/snippets/P.cs": _FakeResponse(200, "int x = 1;\n"),
        }
    )
    fetch_docs.run([source], tmp_path, "2026-09-13", session=session)
    written = (tmp_path / "go" / "a.md").read_text(encoding="utf-8")
    assert ":::code" in written
    assert f"{raw}/_content/doc/snippets/P.cs" not in session.urls


def test_run_reports_unresolved_code_references(tmp_path):
    session = _FakeSession(
        {
            _TREE: _tree_response(["docs/csharp/linq/a.md"]),
            f"{_RAW}/docs/csharp/linq/a.md": _FakeResponse(
                200, ':::code language="csharp" source="snippets/Missing.cs":::\n'
            ),
        }
    )
    report = fetch_docs.run([_CSHARP], tmp_path, "2026-09-13", session=session)
    assert report.unresolved_code_refs == {"csharp": 1}


def test_run_continues_after_a_single_page_fails(tmp_path):
    """土台（木）は取れているので、残りのページは使える（設計書5.2節）。"""
    session = _FakeSession(
        {
            _TREE: _tree_response(["docs/csharp/linq/a.md", "docs/csharp/linq/b.md"]),
            f"{_RAW}/docs/csharp/linq/a.md": _FakeResponse(500),
            f"{_RAW}/docs/csharp/linq/b.md": _FakeResponse(200, "# B\n"),
        }
    )
    report = fetch_docs.run([_CSHARP], tmp_path, "2026-09-13", session=session)
    assert report.pages_written == {"csharp": 1}
    assert report.pages_failed == {"csharp": 1}
    assert "csharp" not in report.failed


def test_run_fails_the_whole_source_when_the_tree_is_truncated(tmp_path):
    """木が欠けていれば、どのページが抜けたかも分からない。"""
    session = _FakeSession({_TREE: _tree_response(["docs/csharp/linq/a.md"], truncated=True)})
    report = fetch_docs.run([_CSHARP], tmp_path, "2026-09-13", session=session)
    assert "csharp" in report.failed
    assert report.pages_written == {}


def test_run_continues_to_the_next_source_after_a_tree_failure(tmp_path):
    llms = fetch_docs.LlmsSource("a", "https://a.test/llms-full.txt", "1")
    session = _FakeSession(
        {
            "https://a.test/llms-full.txt": _FakeResponse(200, "# A\n"),
        }
    )
    report = fetch_docs.run([_CSHARP, llms], tmp_path, "2026-09-13", session=session)
    assert "csharp" in report.failed
    assert report.updated == ["a"]


def test_run_counts_a_github_source_as_unchanged_when_no_page_changed(tmp_path):
    session = _FakeSession(
        {
            _TREE: _tree_response(["docs/csharp/linq/a.md"]),
            f"{_RAW}/docs/csharp/linq/a.md": _FakeResponse(200, "# A\n"),
        }
    )
    fetch_docs.run([_CSHARP], tmp_path, "2026-09-13", session=session)
    report = fetch_docs.run([_CSHARP], tmp_path, "2026-09-20", session=session)
    assert report.unchanged == ["csharp"]
    assert report.pages_written == {"csharp": 0}
```

- [ ] **Step 2: テストが落ちることを確かめる**

Run: `./myvenv313/Scripts/python.exe -m pytest tests/test_fetch_docs.py -q`
Expected: FAIL（`AttributeError: 'FetchReport' object has no attribute 'pages_written'`）

- [ ] **Step 3: `FetchReport` を広げる**

```python
@dataclass
class FetchReport:
    updated: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)
    # llms-full.txt が無く llms.txt に落ちたもの。取り込んでも目次しか入らない。
    index_only: list[str] = field(default_factory=list)
    # GitHub ソースの内訳。ソース単位の updated/unchanged では、1,000ページの
    # うち何ページが書かれたか・落ちたかが分からない。
    pages_written: dict[str, int] = field(default_factory=dict)
    pages_failed: dict[str, int] = field(default_factory=dict)
    # 解決できなかった :::code。黙って落とすと、コードの入っていないページが
    # 混ざったことに気付けない。
    unresolved_code_refs: dict[str, int] = field(default_factory=dict)
```

- [ ] **Step 4: `run()` を分岐させる**

既存の `run()` の `try` の中身を `_run_llms` に切り出し、分岐を足す。

```python
def run(sources, out_dir: Path, fetched_at: str, session=None, notify=None) -> FetchReport:
    report = FetchReport()
    say = notify or (lambda _message: None)
    for source in sources:
        try:
            if isinstance(source, github_source.GitHubSource):
                _run_github(source, out_dir, fetched_at, session, say, report)
            else:
                _run_llms(source, out_dir, fetched_at, session, say, report)
        except Exception as error:  # 1件の失敗で残りを止めない
            report.failed[source.name] = str(error)
            say(f"失敗: {source.name} — {error}")
            continue
    return report


def _run_llms(source, out_dir, fetched_at, session, say, report) -> None:
    say(f"取得中: {source.name} — {source.url}")
    body, fell_back = fetch(source, session=session)
    if fell_back:
        report.index_only.append(source.name)
        say(
            f"警告: {source.name} は llms-full.txt が無く llms.txt に落ちました。"
            "取り込めるのはリンクの目次だけで、記法の質問には答えられません"
        )
    if write_if_changed(source, body, out_dir, fetched_at):
        report.updated.append(source.name)
        say(f"更新: {source.name}（{len(body.encode('utf-8'))}バイト）")
    else:
        report.unchanged.append(source.name)
        say(f"変更なし: {source.name}")


def _run_github(source, out_dir, fetched_at, session, say, report) -> None:
    """1ソース分のページを取って書く。

    木の取得の失敗と truncated は呼び出し元へ抜けさせ、ソース全体の失敗に
    する。土台が無ければ、どのページが抜けたかも分からないためである。
    1ページの取得失敗はここで飲み込み、残りのページを続ける。
    """
    say(f"取得中: {source.name} — {source.repo}@{source.ref}")
    active = session or requests
    tree = github_source.fetch_tree(source.repo, source.ref, active)
    pages = github_source.select_pages(tree, source.paths)
    say(f"{source.name}: {len(pages)}ページ（commit {tree.commit[:10]}）")

    blob_paths = set(tree.paths)
    written = failed = unresolved = 0
    for page_path in pages:
        try:
            body = github_source.fetch_blob(source.repo, source.ref, page_path, active)
        except Exception as error:
            failed += 1
            say(f"警告: {source.name} の {page_path} を取得できません — {error}")
            continue
        body = github_source.strip_liquid(body)
        if source.resolve_code_refs:
            body, missed = code_references.resolve_code_references(
                body,
                page_path,
                blob_paths,
                lambda path: github_source.fetch_blob(source.repo, source.ref, path, active),
            )
            unresolved += missed
        text = github_source.render_page(source, tree.commit, page_path, body, fetched_at)
        # フロントマターの source_path はリポジトリ内の完全なパスを残すが、
        # 置き場所は共通部分を落とした相対パスにする（github_source.local_path）。
        local = github_source.local_path(page_path, source.paths)
        if write_page_if_changed(f"{source.name}/{local}", text, out_dir):
            written += 1

    report.pages_written[source.name] = written
    report.pages_failed[source.name] = failed
    report.unresolved_code_refs[source.name] = unresolved
    if written:
        report.updated.append(source.name)
        say(f"更新: {source.name}（{written}ページ、失敗{failed}件）")
    else:
        report.unchanged.append(source.name)
        say(f"変更なし: {source.name}（{len(pages)}ページ）")
    if unresolved:
        say(f"警告: {source.name} で解決できなかった :::code が{unresolved}件あります")
```

冒頭の import に `from scripts import code_references, github_source` を足す。

- [ ] **Step 5: `main()` の表示に足す**

```python
    print("\n--- 結果 ---")
    print(f"更新: {len(report.updated)}件")
    print(f"変更なし: {len(report.unchanged)}件")
    for name, count in report.pages_written.items():
        print(f"  {name}: {count}ページ書き出し / 取得失敗{report.pages_failed[name]}件")
    for name, count in report.unresolved_code_refs.items():
        if count:
            print(f"  {name}: 解決できなかった :::code が{count}件")
    if report.index_only:
        print(f"目次のみ（本文が取れていません）: {'、'.join(report.index_only)}")
    for name, message in report.failed.items():
        print(f"失敗 {name}: {message}")
```

- [ ] **Step 6: テストが通ることを確かめる**

Run: `./myvenv313/Scripts/python.exe -m pytest tests/test_fetch_docs.py -q`
Expected: PASS

- [ ] **Step 7: 全テストを走らせる**

Run: `./myvenv313/Scripts/python.exe -m pytest -q`
Expected: PASS（既存の748件が1件も落ちない）

- [ ] **Step 8: コミット**

```bash
git add scripts/fetch_docs.py tests/test_fetch_docs.py
git commit -m "feat: fetch a github source page by page without stopping on one failure"
```

---

### Task 6: 設定に4ソースを足し、`AGENTS.md` を直す

**Files:**
- Modify: `docs_sources.toml`
- Modify: `AGENTS.md`（「外部ドキュメントの参照」の3本目）
- Test: `tests/test_fetch_docs.py`

**Interfaces:**
- Consumes: Task 1 の `load_sources`

- [ ] **Step 1: 失敗するテストを書く**

実際の設定ファイルが読めることを確かめる。設定は手で編集するファイルであり、
書式の崩れは想定外の事故ではなく起こりうる入力である。

```python
def test_the_real_config_file_loads(tmp_path):
    """docs_sources.toml は手で編集するファイルである。壊れたまま気付かないと、
    取得を走らせたときに初めて分かる。"""
    sources = fetch_docs.load_sources(fetch_docs.DEFAULT_CONFIG)
    names = [source.name for source in sources]
    assert names == [
        "streamlit",
        "langchain-text-splitters",
        "ollama",
        "huggingface_hub",
        "pymupdf",
        "mcp",
        "csharp",
        "go",
        "mermaid",
        "markdown",
    ]
    by_name = {source.name: source for source in sources}
    assert by_name["csharp"].resolve_code_refs is True
    assert by_name["go"].resolve_code_refs is False
    assert by_name["streamlit"].url == "https://docs.streamlit.io/llms-full.txt"
```

- [ ] **Step 2: テストが落ちることを確かめる**

Run: `./myvenv313/Scripts/python.exe -m pytest tests/test_fetch_docs.py::test_the_real_config_file_loads -v`
Expected: FAIL（`AssertionError`。既存6件しか無い）

- [ ] **Step 3: `docs_sources.toml` に4ソースを足す**

**既存6件は1行も編集しない。** 末尾に足す。

```toml
# ここから下は kind = "github"。llms.txt を公開していない対象を、公式リポジトリの
# 生 Markdown から取る（実測 2026-09-13: Go・C#・Java・Rust はいずれも404、
# Kotlin は200だがコードフェンス0個の目次）。設計書
# docs/superpowers/specs/2026-09-13-github-docs-ingestion-design.md を参照。
#
# ref は既定ブランチを明示する。golang/website は master、mermaid-js/mermaid は
# develop であり、main ではない（実測 2026-09-13）。

# docs/csharp/misc（409ファイル）は入れない。コンパイラのエラー番号ごとのページ
# （cs0003.md など）で、文法の説明ではなく量だけが多い。
#
# resolve_code_refs を有効にするのはここだけである。MS Learn 形式は :::code で
# 外部の .cs を参照し、実測では参照の割合が33%〜93%あった。解決しないと
# 「検索は当たるのにコードが書けない」状態になる。
[[source]]
name = "csharp"
kind = "github"
repo = "dotnet/docs"
ref = "main"
paths = [
  "docs/csharp/language-reference",
  "docs/csharp/programming-guide",
  "docs/csharp/fundamentals",
  "docs/csharp/tour-of-csharp",
  "docs/csharp/whats-new",
  "docs/csharp/advanced-topics",
  "docs/csharp/linq",
  "docs/csharp/asynchronous-programming",
  "docs/csharp/tutorials",
  "docs/csharp/how-to",
]
resolve_code_refs = true
version = "0.0.0"

# Go の言語仕様（spec.html）と Effective Go は HTML であり、ここでは取れない。
# 取れるのは各版のリリースノート（go1.1.md〜）・FAQ・modules リファレンス等の
# 96ファイルである。_content/blog（339ファイル）と _content/solutions（42ファイル）は
# 読み物と事例なので入れない。
[[source]]
name = "go"
kind = "github"
repo = "golang/website"
ref = "master"
paths = ["_content/doc", "_content/ref"]
version = "0.0.0"

[[source]]
name = "mermaid"
kind = "github"
repo = "mermaid-js/mermaid"
ref = "develop"
paths = ["packages/mermaid/src/docs"]
version = "0.0.0"

# CommonMark の仕様書は入れない。例が独自の区切り文字で書かれておりコード
# フェンスではないため、現在のチャンカーが扱えない。実務で書くのは GitHub
# Flavored Markdown なので、ここで足りる。
[[source]]
name = "markdown"
kind = "github"
repo = "github/docs"
ref = "main"
paths = ["content/get-started/writing-on-github"]
version = "0.0.0"
```

- [ ] **Step 4: テストが通ることを確かめる**

Run: `./myvenv313/Scripts/python.exe -m pytest tests/test_fetch_docs.py::test_the_real_config_file_loads -v`
Expected: PASS

- [ ] **Step 5: `AGENTS.md` の3本目を書き換える**

「外部ドキュメントの参照」の3本目（`scripts/fetch_docs.py` の段落）を、次に
差し替える。

```markdown
- 3本目は `scripts/fetch_docs.py` である。`docs_sources.toml` に書かれた宛先へ
  GET を出す。宛先は2種類ある。`kind = "llms"`（既定）は公式ドキュメントの
  `llms-full.txt` を1本取りに行く。`kind = "github"` は `api.github.com` の
  Trees API でリポジトリの木を1回引き、`raw.githubusercontent.com` から各ページの
  本文を取る。どちらも送るのはURLへの要求だけで、社内資料の内容も検索語も
  含まない。認証もトークンも使わない。
  設定に書かれたリポジトリとパスしか取りに行かず、ページ内のリンクは辿らない。
  唯一の例外が `resolve_code_refs = true` を書いたソースの `:::code` で、これは
  C# のドキュメントがコード例を外部ファイルに置いているために要る。解決先は
  **同じリポジトリ・同じ ref の木にある blob に限り**、木に無いパスは取りに
  行かない。外部のURLは辿らない。
  人が明示的に起動したときだけ走り、常駐プロセスもスケジューラも持たない。
  オフライン環境では実行できないが、取得済みの `docs_source/` があれば取り込みは
  ローカルで完結する（`scripts/ingest_source.py` が触る外部の宛先は
  `OLLAMA_HOST` だけである）。
```

- [ ] **Step 6: 全テストを走らせる**

Run: `./myvenv313/Scripts/python.exe -m pytest -q`
Expected: PASS

- [ ] **Step 7: コミット**

```bash
git add docs_sources.toml AGENTS.md tests/test_fetch_docs.py
git commit -m "feat: add the csharp, go, mermaid and markdown sources"
```

---

### Task 7: 実際に取得・取り込み、実測を記録する

**このタスクだけネットワークと Colab を使う。** 人が手で走らせ、出た数値を
資料へ書く。推測した数値は書かない。

**Files:**
- Modify: `docs/コーディング対応ライブラリ.md`

**Interfaces:**
- Consumes: Task 1〜6 のすべて

- [ ] **Step 1: 取得を走らせる**

```bash
./myvenv313/Scripts/python.exe -m scripts.fetch_docs
```

確かめること:
- 既存6件が「変更なし」でスキップされる
- csharp・go・mermaid・markdown の4件が書き出される
- 解決できなかった `:::code` の件数が出る（0でなくてもよい。**記録する**）
- `docs_source/csharp/docs/csharp/language-reference/` 以下にファイルがある

- [ ] **Step 2: `:::code` が残っていないことを確かめる**

```bash
grep -rl ':::code' docs_source/csharp/ | head
```

Expected: 何も出ない。出たら、その件数が Step 1 で報告された未解決の件数と
一致することを確かめる。一致しなければ解決器に漏れがある。

- [ ] **Step 3: 依頼者に Colab の起動を依頼する**

埋め込みに Ollama が要る。`.env` の `OLLAMA_HOST` と `OLLAMA_API_KEY` が
Colab のものになっていることを確かめてから進む。

```bash
./myvenv313/Scripts/python.exe -c "
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path('.env'))
from ingest import embedder
session = embedder.new_session()
r = session.get(f'{embedder.OLLAMA_HOST}/api/tags', timeout=30)
print(r.status_code, sorted(m['name'] for m in r.json().get('models', [])))
"
```

Expected: `200` と `bge-m3:latest` を含む一覧。

**`X-API-Key` を付けずに叩くとプロキシが401を返す。** 上のように
`embedder.new_session()` を使うこと。素の `requests.get` で確かめると、
サーバーが正常でも落ちていると誤認する。

- [ ] **Step 4: 取り込みを走らせる**

時間がかかる（推定24分）。開始と終了の時刻を控える。

```bash
./myvenv313/Scripts/python.exe -m scripts.ingest_source \
    --source-dir docs_source --db docs_store.sqlite3 --keep-code-blocks
```

控えること: ソースごとのチャンク数、総チャンク数、所要秒数。

- [ ] **Step 5: 社内資料のDBが変わっていないことを確かめる**

```bash
ls -l vector_store.sqlite3
```

Expected: バイト数が取り込み前と同じ。変わっていたら取り込み先を間違えている。

- [ ] **Step 6: 検索が効くことを実測する**

`rag_chat_app.py:481` と同じく、モデルを束縛した1引数のラッパーを
`translate_query` に渡すこと。`chat.ask_json` を直接渡すと `TypeError` になり、
翻訳が静かに原文へフォールバックする。

確かめる質問（4件、結果は外しても**そのまま記録する**）:

- 「C#のrecord型の書き方を教えて」
- 「C#のパターンマッチングの構文」
- 「マーメイドでフローチャートを書く記法」
- 「Markdownで表を書く書き方」

控えること: 訳された検索クエリ、Reranker のスコア、引いた内容、出典が
`csharp/docs/csharp/…` のようにページ単位で出ているか。

- [ ] **Step 7: `docs/コーディング対応ライブラリ.md` に書く**

書くこと:

- 1節の表に csharp・go・mermaid・markdown の行を足し、総チャンク数を直す
- 「各資料が実際に扱う範囲」に4件の段落を足す。**Go には「言語仕様は HTML なので
  入っていない。入っているのは各版のリリースノート・FAQ・modules リファレンス
  である」と明記する**（設計書4.4節）
- 3節「対象にできないもの」に、Java を「GitHub に公式の Markdown が無い（実測
  2026-09-13）」として足す
- 4節に Step 6 の実測表を足す
- 2節の取り込み実測の表に、今回の行（チャンク数と秒数）を足す

**測っていない数値は書かない。** 設計書4.7節の「約18,000チャンク」は推定であり、
実測に置き換える。

- [ ] **Step 8: 全テストを走らせる**

Run: `./myvenv313/Scripts/python.exe -m pytest -q`
Expected: PASS

- [ ] **Step 9: コミット**

```bash
git add docs/コーディング対応ライブラリ.md
git commit -m "docs: record the measured results of the github ingestion"
```
