# 最新ドキュメント取り込み 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 公式ドキュメントの `llms-full.txt` を取り込み、モデルの古い知識ではなく
取り込んだ最新の記法でコード例・Markdown例・Mermaid を答えさせる。

**Architecture:** 取得（`scripts/fetch_docs.py`）と取り込み（既存の
`scripts/ingest_source.py`）を2段に分ける。取得したものはただの Markdown なので、
既存の `parse_md` → `chunk_units` → `embedder` → `vector_store` がそのまま動く。
格納先だけを社内資料とは別の SQLite ファイルにし、画面のラジオでどちらを検索するかを
利用者が選ぶ。

**Tech Stack:** Python 3.13 / `requests`（既存依存）/ `tomllib`（標準ライブラリ）/
`langchain-text-splitters`（既存依存）/ Streamlit 1.61.1 / SQLite

**Spec:** `docs/superpowers/specs/2026-09-12-latest-docs-ingestion-design.md`

## Global Constraints

- **新しい依存を追加しない。** `requests==2.32.3` は `requirements.txt` に既にある。
  `tomllib` は Python 3.11 以降の標準ライブラリ。`requirements.txt` は変更しない。
- **社内資料の取り込み結果を1バイトも変えない。** `chunk_units` に足す
  `keep_code_blocks` の既定は `False`。既存のチャンクIDもテキストも変わってはならない。
- **テストからネットワークへ出ない。** HTTP はすべてスタブする。
- **仮想環境は `myvenv313`。** テストは
  `./myvenv313/Scripts/python.exe -m pytest` で走らせる。
- **コミットメッセージは英語**、コンベンショナルコミット形式（`feat:` `fix:`
  `docs:` `test:` `refactor:` `chore:`）。コード中のコメントと docstring は日本語。
- **コメントは「なぜ」を書く。** 「何を」はコードで表現する。
- `MAX_CODE_BLOCK_CHARS = CHUNK_SIZE * 3`（= 2400字）。仕様書4.6節の実測による。
- 取得先は `llms-full.txt` を優先し、404 のときだけ `llms.txt` に落として警告を出す
  （仕様書4.1節）。`llms.txt` は目次であって本文ではない。
- `docs_source/` と `docs_store.sqlite3` は `.gitignore` に入れる。
  `docs_sources.toml` は追跡する。

---

## File Structure

| ファイル | 責務 |
|---|---|
| `docs_sources.toml`（新規・追跡する） | 追跡するライブラリ・URL・版の一覧。入力データ |
| `scripts/fetch_docs.py`（新規） | 設定を読み、HTTP GET し、内容が変わったものだけ `docs_source/` に書く |
| `tests/test_fetch_docs.py`（新規） | 上のテスト。HTTP はスタブ |
| `ingest/chunker.py`（変更） | コードブロックを割らない分割を選べるようにする |
| `tests/test_chunker.py`（変更） | 上のテスト |
| `scripts/ingest_source.py`（変更） | `--db` と `--keep-code-blocks` を受け取り、後者を `chunk_units` まで通す |
| `tests/test_ingest_source.py`（変更） | 上のテスト |
| `ingest/prompting.py`（変更） | 技術ドキュメント専用のプロンプト `build_docs_prompt` |
| `tests/test_prompting.py`（変更） | 上のテスト |
| `rag_chat_app.py`（変更） | コーパス切り替えのラジオと、技術ドキュメント経路の配線 |
| `tests/test_rag_chat_app.py`（変更） | 上のテスト |
| `AGENTS.md` / `README.md` / `docs/処理箇所マップ.md`（変更） | 3本目の外部通信経路、使い方、処理箇所 |

`fetch_docs.py` を `ingest/` ではなく `scripts/` に置くのは、既存の
`scripts/ingest_source.py` と同じく「人が起動する入口」だからである。`ingest/` は
UIにもCLIにも依存しないドメインの置き場所になっている。

---

## Task 1: 設定ファイルと取得処理の中核

**Files:**
- Create: `docs_sources.toml`
- Create: `scripts/fetch_docs.py`
- Create: `tests/test_fetch_docs.py`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: なし（最初のタスク）
- Produces:
  - `scripts/fetch_docs.DocSource` — `@dataclass(frozen=True)` で
    `name: str`, `url: str`, `version: str`
  - `scripts/fetch_docs.load_sources(path: Path) -> list[DocSource]`
  - `scripts/fetch_docs.fetch(source: DocSource, session=None) -> tuple[str, bool]` —
    `(本文, 目次に落ちたか)` を返す。取得できなければ `requests.RequestException` を
    そのまま投げる
  - `scripts/fetch_docs.write_if_changed(source: DocSource, body: str, out_dir: Path,
    fetched_at: str) -> bool` — 書いたら `True`、内容が同じで書かなかったら `False`
  - `scripts/fetch_docs.DEFAULT_CONFIG: Path`, `scripts/fetch_docs.DEFAULT_OUT_DIR: Path`

### 背景（実装者向け）

`llms.txt` は LLM 向けにドキュメントをまとめたプレーンテキストの慣習である。
**重要な落とし穴があり、これを外すと機能が丸ごと無意味になる。**

- `https://<domain>/llms.txt` は**リンクの目次**である。実測（2026-09-12）で
  `docs.streamlit.io/llms.txt` は 66,927 バイトあるがコードフェンスは **0個**。
- `https://<domain>/llms-full.txt` が**本文**である。同じサイトで 1,927,203 バイト、
  コードフェンス 1,877個。

したがって設定には `llms-full.txt` の URL を書き、それが 404 のときだけ
`llms.txt` に落とす。落ちたことは呼び出し元に伝える（戻り値の2つめ）。

書き出すファイルには YAML フロントマターを付ける。既存の
`ingest/parsers/md_parser.py` の `_split_frontmatter` が、先頭が `---` で始まり
`---` で閉じられたブロックを属性として拾い、**本文から除いて**くれる。
`key: value` の平らな行だけが拾われ、値は `_scalar` が int / float に変換を試みる
（`1.61.1` は float にならないので文字列のまま残る）。`partition(":")` は最初の
コロンだけで切るため、`url: https://...` は正しく `url` と `https://...` に分かれる。

- [ ] **Step 1: `.gitignore` に追記する**

`source/` の行のすぐ下に足す。理由をコメントで残す。

```gitignore
# 取得した公式ドキュメントと、その取り込み先DB。source/ と vector_store.sqlite3 と
# 同じ理由で追跡しない（大きく、docs_sources.toml からいつでも取り直せる）
docs_source/
docs_store.sqlite3
docs_store.sqlite3.bak-*
```

- [ ] **Step 2: `docs_sources.toml` を書く**

初期値は仕様書4.2節の実測（2026-09-12）で `llms.txt` の実在を確認できたものだけ。
`fastapi` `pytest` `numpy` は 404 だったので入れない。

```toml
# 取り込む公式ドキュメントの一覧。scripts/fetch_docs.py が読む。
#
# url には llms-full.txt を書くこと。llms.txt は各ページへのリンクの目次であって
# 本文ではない（実測 2026-09-12: docs.streamlit.io/llms.txt はコードフェンス0個）。
#
# version は requirements.txt で固定している版を書く。取得先は常に最新版の
# ドキュメントなので厳密には一致しないが、どの版を使っている状態で取り込んだかを
# 残すために持つ。
#
# llms.txt を公開していないライブラリは載せられない（実測 2026-09-12 で
# fastapi・pytest・numpy は404）。

[[source]]
name = "streamlit"
url = "https://docs.streamlit.io/llms-full.txt"
version = "1.61.1"

[[source]]
name = "langchain-text-splitters"
url = "https://python.langchain.com/llms-full.txt"
version = "1.1.2"

[[source]]
name = "ollama"
url = "https://docs.ollama.com/llms-full.txt"
version = "0.0.0"

[[source]]
name = "huggingface_hub"
url = "https://huggingface.co/docs/huggingface_hub/llms-full.txt"
version = "1.27.0"

[[source]]
name = "pymupdf"
url = "https://pymupdf.readthedocs.io/llms-full.txt"
version = "1.28.2"
```

`ollama` の `version` が `0.0.0` なのは、Ollama が Python パッケージとしては
`requirements.txt` に無く（HTTP で直接叩いている）、固定している版が無いためである。

- [ ] **Step 3: 失敗するテストを書く**

`tests/test_fetch_docs.py` を新規作成する。

```python
"""公式ドキュメントの取得。

ネットワークへは絶対に出ない。requests.Session を差し替えて、
状態コードと本文をこちらで決める。
"""
from pathlib import Path

import pytest
import requests

from scripts import fetch_docs


class _FakeResponse:
    def __init__(self, status_code, text=""):
        self.status_code = status_code
        self.text = text

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


def _source(name="streamlit", url="https://example.test/llms-full.txt", version="1.0"):
    return fetch_docs.DocSource(name=name, url=url, version=version)


def test_load_sources_reads_the_name_url_and_version(tmp_path):
    config = tmp_path / "docs_sources.toml"
    config.write_text(
        '[[source]]\nname = "streamlit"\n'
        'url = "https://example.test/llms-full.txt"\nversion = "1.61.1"\n',
        encoding="utf-8",
    )
    sources = fetch_docs.load_sources(config)
    assert sources == [
        fetch_docs.DocSource(
            name="streamlit", url="https://example.test/llms-full.txt", version="1.61.1"
        )
    ]


def test_fetch_returns_the_body_without_falling_back():
    session = _FakeSession(
        {"https://example.test/llms-full.txt": _FakeResponse(200, "# 本文\n")}
    )
    body, fell_back = fetch_docs.fetch(_source(), session=session)
    assert body == "# 本文\n"
    assert fell_back is False


def test_fetch_falls_back_to_the_index_when_the_full_text_is_missing():
    """llms-full.txt が無いサイトでも、目次だけは取れることがある。

    目次を取り込んでも記法の質問には答えられない（実測 2026-09-12:
    docs.streamlit.io/llms.txt はコードフェンス0個）。取れたこと自体は
    返すが、呼び出し元が警告を出せるよう「落ちた」ことを必ず伝える。
    """
    session = _FakeSession(
        {"https://example.test/llms.txt": _FakeResponse(200, "- [A](/a)\n")}
    )
    body, fell_back = fetch_docs.fetch(_source(), session=session)
    assert body == "- [A](/a)\n"
    assert fell_back is True
    assert session.urls == [
        "https://example.test/llms-full.txt",
        "https://example.test/llms.txt",
    ]


def test_fetch_raises_when_neither_is_available():
    session = _FakeSession({})
    with pytest.raises(requests.HTTPError):
        fetch_docs.fetch(_source(), session=session)


def test_write_if_changed_writes_the_frontmatter_and_the_body(tmp_path):
    written = fetch_docs.write_if_changed(
        _source(), "# Streamlit\n\n本文\n", tmp_path, "2026-09-12"
    )
    assert written is True
    text = (tmp_path / "streamlit.md").read_text(encoding="utf-8")
    assert text.startswith("---\n")
    assert "name: streamlit\n" in text
    assert "url: https://example.test/llms-full.txt\n" in text
    assert "version: 1.0\n" in text
    assert "fetched_at: 2026-09-12\n" in text
    assert text.endswith("# Streamlit\n\n本文\n")


def test_write_if_changed_does_not_rewrite_an_unchanged_body(tmp_path):
    """差分検知はフロントマターではなく本文のハッシュで行う。

    フロントマターには fetched_at が入るので、そちらを含めて比べると
    内容が同じでも毎回「更新された」ことになり、取り込みが毎回全件走る。
    """
    fetch_docs.write_if_changed(_source(), "本文\n", tmp_path, "2026-09-12")
    before = (tmp_path / "streamlit.md").read_text(encoding="utf-8")

    written = fetch_docs.write_if_changed(_source(), "本文\n", tmp_path, "2026-09-13")

    assert written is False
    assert (tmp_path / "streamlit.md").read_text(encoding="utf-8") == before


def test_write_if_changed_rewrites_a_changed_body(tmp_path):
    fetch_docs.write_if_changed(_source(), "古い本文\n", tmp_path, "2026-09-12")
    written = fetch_docs.write_if_changed(_source(), "新しい本文\n", tmp_path, "2026-09-13")
    assert written is True
    text = (tmp_path / "streamlit.md").read_text(encoding="utf-8")
    assert text.endswith("新しい本文\n")
    assert "fetched_at: 2026-09-13\n" in text


def test_the_written_file_parses_as_markdown_with_the_attributes(tmp_path):
    """書き出した形が既存のMarkdownパーサーで読めることを確かめる。

    フロントマターの書式を間違えると、生のYAMLがそのまま本文として索引される。
    parse_md を通すところまで見ないとこれに気づけない。
    """
    from ingest.parsers.md_parser import parse_md

    fetch_docs.write_if_changed(
        _source(), "# Streamlit\n\n## ダイアログ\n\n本文\n", tmp_path, "2026-09-12"
    )
    units = parse_md(tmp_path / "streamlit.md")

    assert units
    assert units[0].attributes["name"] == "streamlit"
    assert units[0].attributes["version"] == "1.0"
    assert "---" not in units[0].text
    assert "fetched_at" not in units[0].text
```

- [ ] **Step 4: テストを走らせて失敗を確認する**

Run: `./myvenv313/Scripts/python.exe -m pytest tests/test_fetch_docs.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'scripts.fetch_docs'`）

- [ ] **Step 5: `scripts/fetch_docs.py` を書く**

```python
"""公式ドキュメントの llms-full.txt を取得して docs_source/ へ置く。

取得と取り込みを分けている。取得は外部通信を伴い失敗しうるが、取り込みは
ローカルで閉じる。分けておけば、取得が落ちても手元のファイルから取り込み直せる。

設定ファイルに書かれたURLしか取りに行かない。ページ内のリンクは辿らない。
クローラーにはしない。外部へ送るのはURLへのGETだけで、社内資料の内容も
検索語も含まない（AGENTS.md「外部ドキュメントの参照」参照）。
"""
import hashlib
import tomllib
from dataclasses import dataclass
from pathlib import Path

import requests

_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = _ROOT / "docs_sources.toml"
DEFAULT_OUT_DIR = _ROOT / "docs_source"

# 1.9MBのテキストを落とすことがある。既定の無制限だと、応答が返らない
# サイトでプロセスが止まったままになる。
_TIMEOUT = 60


@dataclass(frozen=True)
class DocSource:
    name: str
    url: str
    version: str


def load_sources(path: Path = DEFAULT_CONFIG) -> list[DocSource]:
    with path.open("rb") as handle:
        config = tomllib.load(handle)
    return [
        DocSource(name=entry["name"], url=entry["url"], version=str(entry["version"]))
        for entry in config.get("source", [])
    ]


def _index_url(url: str) -> str:
    """llms-full.txt に対応する llms.txt のURL。"""
    return url.replace("llms-full.txt", "llms.txt")


def fetch(source: DocSource, session=None) -> tuple[str, bool]:
    """本文と、目次に落ちたかどうかを返す。

    llms.txt は各ページへのリンクの目次であって本文ではない（実測 2026-09-12:
    docs.streamlit.io/llms.txt は66,927バイトだがコードフェンスは0個）。
    目次を取り込んでも記法の質問には答えられないので、落ちたことを必ず伝える。
    黙って取り込むと、検索は当たるのに答えが書けないという診断しにくい
    状態になる。
    """
    session = session or requests
    response = session.get(source.url, timeout=_TIMEOUT)
    if response.status_code < 400:
        return response.text, False

    index = _index_url(source.url)
    if index == source.url:
        response.raise_for_status()
    fallback = session.get(index, timeout=_TIMEOUT)
    fallback.raise_for_status()
    return fallback.text, True


def _frontmatter(source: DocSource, fetched_at: str) -> str:
    return (
        "---\n"
        f"name: {source.name}\n"
        f"url: {source.url}\n"
        f"version: {source.version}\n"
        f"fetched_at: {fetched_at}\n"
        "---\n"
    )


def _body_of(path: Path) -> str:
    """書き出し済みファイルから本文だけを取り出す。無ければ空文字。

    フロントマターを飛ばすのは、そこに fetched_at が入っているためである。
    含めて比べると、内容が同じでも取得日が違えば必ず「変わった」ことになり、
    差分検知が意味をなさなくなる。
    """
    if not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return text
    _, _, rest = text[4:].partition("---\n")
    return rest


def write_if_changed(
    source: DocSource, body: str, out_dir: Path, fetched_at: str
) -> bool:
    """本文が変わっていれば書く。書いたら True。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{source.name}.md"
    if _digest(_body_of(path)) == _digest(body):
        return False
    path.write_text(_frontmatter(source, fetched_at) + body, encoding="utf-8")
    return True


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
```

- [ ] **Step 6: テストを走らせて通ることを確認する**

Run: `./myvenv313/Scripts/python.exe -m pytest tests/test_fetch_docs.py -v`
Expected: PASS（8件）

- [ ] **Step 7: 全体のテストが壊れていないことを確認する**

Run: `./myvenv313/Scripts/python.exe -m pytest tests/ -q`
Expected: 既存の690件に8件足して 698 passed, 3 deselected

- [ ] **Step 8: コミット**

```bash
git add .gitignore docs_sources.toml scripts/fetch_docs.py tests/test_fetch_docs.py
git commit -m "feat: fetch official documentation from llms-full.txt"
```

---

## Task 2: 取得コマンドの入口

**Files:**
- Modify: `scripts/fetch_docs.py`
- Modify: `tests/test_fetch_docs.py`

**Interfaces:**
- Consumes: `DocSource`, `load_sources()`, `fetch()`, `write_if_changed()`,
  `DEFAULT_CONFIG`, `DEFAULT_OUT_DIR`（Task 1）
- Produces: `scripts/fetch_docs.run(sources, out_dir, fetched_at, session=None,
  notify=None) -> FetchReport` と
  `scripts/fetch_docs.FetchReport`（`updated: list[str]`, `unchanged: list[str]`,
  `failed: dict[str, str]`, `index_only: list[str]`）、`main() -> int`

### 背景（実装者向け）

1件の失敗で全体を止めない。既存の `scripts/ingest_source.py` の `_ingest_one` が
`except Exception` で1ファイルの失敗を報告に落として続けているのと同じ方針である。
5つ設定されていて3つめが落ちたとき、4つめと5つめが取れないのは損である。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_fetch_docs.py` の末尾に足す。

```python
def test_run_reports_updated_unchanged_and_failed(tmp_path):
    sources = [
        fetch_docs.DocSource("a", "https://a.test/llms-full.txt", "1"),
        fetch_docs.DocSource("b", "https://b.test/llms-full.txt", "2"),
        fetch_docs.DocSource("c", "https://c.test/llms-full.txt", "3"),
    ]
    session = _FakeSession(
        {
            "https://a.test/llms-full.txt": _FakeResponse(200, "A\n"),
            "https://b.test/llms-full.txt": _FakeResponse(200, "B\n"),
        }
    )
    first = fetch_docs.run(sources, tmp_path, "2026-09-12", session=session)
    assert first.updated == ["a", "b"]
    assert first.unchanged == []
    assert list(first.failed) == ["c"]

    second = fetch_docs.run(sources, tmp_path, "2026-09-13", session=session)
    assert second.updated == []
    assert second.unchanged == ["a", "b"]


def test_run_continues_after_a_failure(tmp_path):
    """3件中1件が落ちても、後ろの2件は取りに行く。

    1件の失敗で止めると、落ちたサイトが直るまで他のライブラリも
    更新できなくなる。ingest_source.py の _ingest_one と同じ方針。
    """
    sources = [
        fetch_docs.DocSource("a", "https://a.test/llms-full.txt", "1"),
        fetch_docs.DocSource("b", "https://b.test/llms-full.txt", "2"),
        fetch_docs.DocSource("c", "https://c.test/llms-full.txt", "3"),
    ]
    session = _FakeSession(
        {
            "https://a.test/llms-full.txt": _FakeResponse(200, "A\n"),
            "https://c.test/llms-full.txt": _FakeResponse(200, "C\n"),
        }
    )
    report = fetch_docs.run(sources, tmp_path, "2026-09-12", session=session)
    assert report.updated == ["a", "c"]
    assert list(report.failed) == ["b"]
    assert (tmp_path / "c.md").is_file()


def test_run_records_the_sources_that_only_yielded_an_index(tmp_path):
    """目次しか取れなかったことは、報告に必ず残す（仕様書4.1節）。"""
    sources = [fetch_docs.DocSource("a", "https://a.test/llms-full.txt", "1")]
    session = _FakeSession({"https://a.test/llms.txt": _FakeResponse(200, "- [x](/x)\n")})
    report = fetch_docs.run(sources, tmp_path, "2026-09-12", session=session)
    assert report.index_only == ["a"]
    assert report.updated == ["a"]


def test_run_notifies_progress_per_source(tmp_path):
    sources = [fetch_docs.DocSource("a", "https://a.test/llms-full.txt", "1")]
    session = _FakeSession({"https://a.test/llms-full.txt": _FakeResponse(200, "A\n")})
    messages = []
    fetch_docs.run(sources, tmp_path, "2026-09-12", session=session, notify=messages.append)
    assert any("a" in message for message in messages)
```

- [ ] **Step 2: テストを走らせて失敗を確認する**

Run: `./myvenv313/Scripts/python.exe -m pytest tests/test_fetch_docs.py -k "run_" -v`
Expected: FAIL（`AttributeError: module 'scripts.fetch_docs' has no attribute 'run'`）

- [ ] **Step 3: `run()` と `FetchReport` と `main()` を足す**

`scripts/fetch_docs.py` に追記する。`import argparse` と
`from dataclasses import dataclass, field`、`from datetime import date` を
先頭の import に足すこと。

```python
@dataclass
class FetchReport:
    updated: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)
    # llms-full.txt が無く llms.txt に落ちたもの。取り込んでも目次しか入らない。
    index_only: list[str] = field(default_factory=list)


def run(sources, out_dir: Path, fetched_at: str, session=None, notify=None) -> FetchReport:
    report = FetchReport()
    say = notify or (lambda _message: None)
    for source in sources:
        say(f"取得中: {source.name} — {source.url}")
        try:
            body, fell_back = fetch(source, session=session)
        except Exception as error:  # 1件の失敗で残りを止めない
            report.failed[source.name] = str(error)
            say(f"失敗: {source.name} — {error}")
            continue
        if fell_back:
            report.index_only.append(source.name)
            say(
                f"警告: {source.name} は llms-full.txt が無く llms.txt に落ちました。"
                "取り込めるのはリンクの目次だけで、記法の質問には答えられません"
            )
        if write_if_changed(source, body, out_dir, fetched_at):
            report.updated.append(source.name)
            say(f"更新: {source.name}（{len(body)}バイト）")
        else:
            report.unchanged.append(source.name)
            say(f"変更なし: {source.name}")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="docs_sources.toml のドキュメントを docs_source/ へ取得する"
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    if not args.config.is_file():
        print(f"設定ファイルがありません: {args.config}")
        return 1

    sources = load_sources(args.config)
    if not sources:
        print(f"{args.config} に [[source]] が1件もありません")
        return 1

    report = run(sources, args.out_dir, date.today().isoformat(), notify=print)

    print("\n--- 結果 ---")
    print(f"更新: {len(report.updated)}件")
    print(f"変更なし: {len(report.unchanged)}件")
    if report.index_only:
        print(f"目次のみ（本文が取れていません）: {'、'.join(report.index_only)}")
    for name, message in report.failed.items():
        print(f"失敗 {name}: {message}")
    # 全滅は設定かネットワークの問題である。終了コードで分かるようにする。
    return 1 if report.failed and not (report.updated or report.unchanged) else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: テストを走らせて通ることを確認する**

Run: `./myvenv313/Scripts/python.exe -m pytest tests/test_fetch_docs.py -v`
Expected: PASS（12件）

- [ ] **Step 5: 実際に1件取得して動作を確かめる**

これはネットワークへ出る。テストではなく手元での確認である。

Run: `./myvenv313/Scripts/python.exe -m scripts.fetch_docs`
Expected: `docs_source/streamlit.md` などが作られ、「更新: 5件」と出る。
もう一度同じコマンドを走らせると「変更なし: 5件」になること。

`docs_source/streamlit.md` の先頭が `---` で始まり、`fetched_at:` を含み、
ファイルサイズが1MBを超えていることを確認する。

- [ ] **Step 6: コミット**

```bash
git add scripts/fetch_docs.py tests/test_fetch_docs.py
git commit -m "feat: add a CLI entry point for fetching documentation"
```

---

## Task 3: コードブロックを割らない分割

**Files:**
- Modify: `ingest/chunker.py`
- Modify: `tests/test_chunker.py`

**Interfaces:**
- Consumes: `ingest.models.ParsedUnit`, `ingest.models.Chunk`
- Produces: `chunk_units(units, source, file_hash, indexed_at,
  keep_code_blocks: bool = False) -> list[Chunk]`、
  `ingest.chunker.MAX_CODE_BLOCK_CHARS`（= 2400）

### 背景（実装者向け）

**この変更の理由は実測にある。** Streamlit の `llms-full.txt` を現在の
`parse_md` → `chunk_units` に通すと、3,427チャンク中 **284件（8.3%）** で
コードブロックが途中で割れる。開きフェンスだけ、あるいは閉じフェンスだけを含む
チャンクになり、検索で当たってもモデルには不完全なコードが渡る。

**やってはいけない直し方がある。** 区切り（`_SEPARATORS`）の先頭に
`"\n```"` を足す案は直感的だが、実測すると割れが **8.3% → 17.0% に悪化する**。
`RecursiveCharacterTextSplitter` は区切りの手前で切るため、開きフェンスの手前
だけでなく**閉じフェンスの手前でも切り**、コードブロックが「本体」と
「閉じフェンス」に分断されるからである。この案は採用しない。

採用するのは「コードブロックを分割器に通さず、丸ごと1チャンクにする」方式で、
実測で割れは **0.1%（4件）** まで落ちる。残る4件は元の文書のフェンスが
対になっていない箇所であり、分割の問題ではない。

ただし丸ごと保持すると `chunk_size` を超えるチャンクが100件生じ、最大は
**24,864字**になる。これは bge-m3 の入力窓を超えるため埋め込みで後ろが
切り捨てられる。そこで上限 `MAX_CODE_BLOCK_CHARS = CHUNK_SIZE * 3`（2400字）を
設け、超えるブロックは地の文と同じ分割器に通す。対象はブロック938個中33個
（3.5%）にとどまる（ブロックの大きさは中央値122字、平均465字）。

**既定は `False` にすること。** 社内資料の取り込み結果が1バイトでも変わっては
ならない。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_chunker.py` の末尾に足す。既存のファイルが `ParsedUnit` をどう
組み立てているかに合わせること（`from ingest.models import ParsedUnit, SECTION`）。

```python
def _long_prose(marker: str, length: int) -> str:
    """分割器に確実に掛かる長さの地の文。句点があるので日本語の区切りで切れる。"""
    sentence = f"{marker}はここに説明があります。"
    return sentence * (length // len(sentence) + 1)


def test_a_code_block_is_not_split_when_code_blocks_are_kept():
    """コードブロックが割れると、モデルには不完全なコードが渡る。

    実測（2026-09-12、Streamlit の llms-full.txt）では、既定の分割で
    3,427チャンク中284件（8.3%）がフェンスの途中で割れていた。
    """
    code = "```python\n" + "x = 1\n" * 60 + "```"
    text = _long_prose("前置き", 900) + "\n\n" + code + "\n\n" + _long_prose("後書き", 900)
    unit = ParsedUnit(text=text, location_type=SECTION, location=1)

    chunks = chunk_units([unit], "a.md", "hash", "2026-09-12", keep_code_blocks=True)

    assert all(chunk.text.count("```") % 2 == 0 for chunk in chunks)
    assert any(chunk.text.strip() == code for chunk in chunks)


def test_a_code_block_longer_than_the_limit_is_split():
    """入力窓を超える巨大なブロックは、丸ごと残すほうが害になる。

    bge-m3 は入力窓を超えた分を切り捨てる。24,864字のブロックを1チャンクに
    すると、後ろが黙って失われる（実測での最大値）。割れても分割するほうがよい。
    """
    huge = "```python\n" + "y = 2\n" * 1000 + "```"
    assert len(huge) > MAX_CODE_BLOCK_CHARS
    unit = ParsedUnit(text=huge, location_type=SECTION, location=1)

    chunks = chunk_units([unit], "a.md", "hash", "2026-09-12", keep_code_blocks=True)

    assert len(chunks) > 1
    assert all(len(chunk.text) <= MAX_CODE_BLOCK_CHARS for chunk in chunks)


def test_keeping_code_blocks_is_off_by_default():
    """社内資料の取り込み結果を1バイトも変えないための既定。"""
    code = "```python\n" + "x = 1\n" * 60 + "```"
    text = _long_prose("前置き", 900) + "\n\n" + code
    unit = ParsedUnit(text=text, location_type=SECTION, location=1)

    default = chunk_units([unit], "a.md", "hash", "2026-09-12")
    explicit = chunk_units([unit], "a.md", "hash", "2026-09-12", keep_code_blocks=False)

    assert [chunk.text for chunk in default] == [chunk.text for chunk in explicit]


def test_prose_without_any_code_block_is_chunked_the_same_either_way():
    """コードが無ければ、どちらの経路でも結果は同じでなければならない。

    切り分けの処理が地の文の分割まで変えてしまっていないかを見る。
    """
    unit = ParsedUnit(text=_long_prose("本文", 2000), location_type=SECTION, location=1)

    off = chunk_units([unit], "a.md", "hash", "2026-09-12")
    on = chunk_units([unit], "a.md", "hash", "2026-09-12", keep_code_blocks=True)

    assert [chunk.text for chunk in off] == [chunk.text for chunk in on]


def test_chunk_ids_stay_sequential_when_code_blocks_are_kept():
    """IDが重複すると、ストアが例外を出さずに上書きしてチャンクを失う。

    INSERT OR REPLACE のため、衝突は静かに起きる。
    """
    code = "```python\nx = 1\n```"
    unit = ParsedUnit(
        text=_long_prose("前", 900) + "\n\n" + code + "\n\n" + _long_prose("後", 900),
        location_type=SECTION,
        location=1,
    )
    chunks = chunk_units([unit], "a.md", "hash", "2026-09-12", keep_code_blocks=True)
    ids = [chunk.id for chunk in chunks]
    assert len(ids) == len(set(ids))
    assert ids == [f"a.md::section1::{index}" for index in range(len(chunks))]
```

テストファイルの先頭の import に `MAX_CODE_BLOCK_CHARS` を足す：

```python
from ingest.chunker import MAX_CODE_BLOCK_CHARS, chunk_units
```

- [ ] **Step 2: テストを走らせて失敗を確認する**

Run: `./myvenv313/Scripts/python.exe -m pytest tests/test_chunker.py -k "code_block" -v`
Expected: FAIL（`ImportError: cannot import name 'MAX_CODE_BLOCK_CHARS'`）

- [ ] **Step 3: `ingest/chunker.py` を変更する**

先頭の import に `import re` を足す。`_SEPARATORS` の定義の下に定数と正規表現を置く。

```python
# コードブロックを丸ごと1チャンクに保つときの上限。
#
# 上限が要るのは、丸ごと保持すると巨大なチャンクが生じるためである。実測
# （2026-09-12、Streamlit の llms-full.txt）では chunk_size を超えるチャンクが
# 100件生じ、最大は24,864字だった。bge-m3 は入力窓を超えた分を切り捨てるので、
# 丸ごと残すと後ろが黙って失われる。割れても分割するほうがましである。
#
# 2400字（CHUNK_SIZEの3倍）にしたのは分布による。ブロック938個の中央値は122字、
# 平均465字で、2400字を超えるのは33個（3.5%）にとどまる。
MAX_CODE_BLOCK_CHARS = CHUNK_SIZE * 3

# 行頭のフェンスから行頭のフェンスまでを1ブロックとする。
#
# 区切り（_SEPARATORS）にフェンスを足す方法は採らない。実測では割れが
# 8.3%から17.0%へ悪化する。RecursiveCharacterTextSplitter は区切りの手前で
# 切るため、開きフェンスの手前だけでなく閉じフェンスの手前でも切り、
# コードブロックが本体と閉じフェンスに分断されるからである。
_CODE_BLOCK = re.compile(r"^```.*?^```", re.DOTALL | re.MULTILINE)
```

`_split` の下に、コードブロックを保つ分割を足す。

```python
def _split_keeping_code(text: str) -> list[str]:
    """コードブロックは分割器に通さず1片として残し、地の文だけを分割する。

    コード例が途中で切れると、検索で当たってもモデルには構文として壊れた
    断片が渡る。実測（2026-09-12、Streamlit の llms-full.txt）では、既定の
    分割で3,427チャンク中284件（8.3%）が割れていた。この方式では4件（0.1%）
    まで落ちる（残る4件は元の文書のフェンスが対になっていない箇所である）。

    MAX_CODE_BLOCK_CHARS を超えるブロックだけは地の文と同じ分割器に通す。
    理由は定数のコメントを参照。
    """
    parts: list[str] = []
    last = 0
    for match in _CODE_BLOCK.finditer(text):
        parts.extend(_split(text[last : match.start()]))
        block = match.group(0)
        parts.extend([block] if len(block) <= MAX_CODE_BLOCK_CHARS else _split(block))
        last = match.end()
    parts.extend(_split(text[last:]))
    return parts
```

`chunk_units` の署名と、分割を呼んでいる1行を変える。

```python
def chunk_units(
    units: list[ParsedUnit],
    source: str,
    file_hash: str,
    indexed_at: str,
    keep_code_blocks: bool = False,
) -> list[Chunk]:
```

docstring の末尾に足す：

```
    keep_code_blocks は技術ドキュメントの取り込みだけが True にする。既定を
    False にしているのは、社内資料の取り込み結果を1バイトも変えないためである。
```

本体の `for part in _split(text):` を次に変える：

```python
        split = _split_keeping_code if keep_code_blocks else _split
        for part in split(text):
```

`_split` は空文字や空白だけの入力に対して `MIN_CHUNK_CHARS` の判定で空リストを
返すので、`_split_keeping_code` が渡す前後の空断片は自然に消える。

- [ ] **Step 4: テストを走らせて通ることを確認する**

Run: `./myvenv313/Scripts/python.exe -m pytest tests/test_chunker.py -v`
Expected: PASS（既存の全件 + 新規5件）

- [ ] **Step 5: 既存の取り込み結果が変わらないことを確認する**

Run: `./myvenv313/Scripts/python.exe -m pytest tests/ -q`
Expected: 698 + 5 = 703 passed, 3 deselected。**1件も失敗しないこと。**
`tests/test_ingest_source.py` や `tests/test_parser_md.py` が落ちたら、既定が
`False` になっていないか、`_split_keeping_code` が地の文の分割を変えている。

- [ ] **Step 6: 実データで割れの率を測り直す**

Task 2 で取得した `docs_source/streamlit.md` を使う。

```bash
./myvenv313/Scripts/python.exe -c "
from pathlib import Path
from ingest.parsers.md_parser import parse_md
from ingest.chunker import chunk_units
units = parse_md(Path('docs_source/streamlit.md'))
for keep in (False, True):
    chunks = chunk_units(units, 's.md', 'h', '2026-09-12', keep_code_blocks=keep)
    broken = sum(1 for c in chunks if c.text.count('\`\`\`') % 2 == 1)
    print(f'keep={keep}: chunks={len(chunks)} broken={broken} ({100*broken/len(chunks):.1f}%)')
"
```

Expected: `keep=False` で 8%前後、`keep=True` で 1%未満。数値が仕様書4.5節と
大きく違ったら、実装が意図どおりでない可能性がある。結果を次のコミットメッセージに
書き残すこと。

- [ ] **Step 7: コミット**

```bash
git add ingest/chunker.py tests/test_chunker.py
git commit -m "feat: add a chunking mode that keeps code blocks whole"
```

---

## Task 4: 取り込みコマンドに `--db` と `--keep-code-blocks`

**Files:**
- Modify: `scripts/ingest_source.py`
- Modify: `tests/test_ingest_source.py`

**Interfaces:**
- Consumes: `chunk_units(..., keep_code_blocks: bool = False)`（Task 3）
- Produces: `ingest_directory(..., keep_code_blocks: bool = False)`、
  `_ingest_one(..., keep_code_blocks)`、CLI の `--db` と `--keep-code-blocks`

### 背景（実装者向け）

`main()` は現在 DB パスを直書きしている（`store.open_store(str(DB_PATH))`）。

**`--db` を足すときに注意が要る。** `ingest/store.py` の `DB_PATH` のコメントに
書いてあるとおり、**`open_store` はパスを間違えても例外を出さず空のDBを新規作成
する**。タイポは「検索結果が全部空」という静かな失敗になり、テストも緑のまま通る。
そのため、取り込みのあとにDBの総チャンク数を必ず表示し、0件なら警告を出す。

`keep_code_blocks` は `main()` → `ingest_directory()` → `_ingest_one()` →
`chunk_units()` と通す。`ingest_uploads` には通さない。画面からのアップロードは
社内資料であり、コードブロック保持は技術ドキュメントの取り込みだけが使う。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_ingest_source.py` の末尾に足す。既存のテストがどうやって
`embedder` をスタブしているかに合わせること。

```python
def test_ingest_directory_passes_keep_code_blocks_to_the_chunker(tmp_path, monkeypatch):
    """取り込み経路の端から端まで通っていることを見る。

    chunk_units まで届いていなければ、コードブロック保持の実装が
    あっても技術ドキュメントの取り込みでは一切効かない。
    """
    from ingest import chunker

    (tmp_path / "a.md").write_text(
        "# 題\n\n## 節\n\n" + "説明です。" * 200 + "\n\n```python\nx = 1\n```\n",
        encoding="utf-8",
    )
    seen = []
    real = chunker.chunk_units

    def spy(units, source, file_hash, indexed_at, keep_code_blocks=False):
        seen.append(keep_code_blocks)
        return real(units, source, file_hash, indexed_at, keep_code_blocks=keep_code_blocks)

    monkeypatch.setattr(ingest_source, "chunk_units", spy)

    collection = open_store(":memory:")
    ingest_source.ingest_directory(
        tmp_path, collection, session=_FakeSession(), keep_code_blocks=True
    )

    assert seen == [True]


def test_ingest_directory_does_not_keep_code_blocks_by_default(tmp_path, monkeypatch):
    from ingest import chunker

    (tmp_path / "a.md").write_text("# 題\n\n## 節\n\n本文です。\n", encoding="utf-8")
    seen = []
    real = chunker.chunk_units

    def spy(units, source, file_hash, indexed_at, keep_code_blocks=False):
        seen.append(keep_code_blocks)
        return real(units, source, file_hash, indexed_at, keep_code_blocks=keep_code_blocks)

    monkeypatch.setattr(ingest_source, "chunk_units", spy)

    collection = open_store(":memory:")
    ingest_source.ingest_directory(tmp_path, collection, session=_FakeSession())

    assert seen == [False]
```

`_FakeSession` と `open_store` はこのテストファイルに既にある。`_FakeSession` は
埋め込みAPIの代わりに `EMBED_DIM` 長のベクトルを返すダミーで、`open_store` は
`from ingest.store import open_store` で import 済みである。新しく作らないこと。

- [ ] **Step 2: テストを走らせて失敗を確認する**

Run: `./myvenv313/Scripts/python.exe -m pytest tests/test_ingest_source.py -k "keep_code" -v`
Expected: FAIL（`TypeError: ingest_directory() got an unexpected keyword argument
'keep_code_blocks'`）

- [ ] **Step 3: 引数を通す**

`_ingest_one` の署名に `keep_code_blocks` を足し、`chunk_units` の呼び出しに渡す。

```python
def _ingest_one(
    path: Path,
    source: str,
    current_hash: str,
    collection,
    session,
    today: str,
    caption_image,
    notify,
    report: IngestReport,
    keep_code_blocks: bool = False,
) -> None:
```

```python
        chunks = chunk_units(
            units, source, current_hash, today, keep_code_blocks=keep_code_blocks
        )
```

`ingest_directory` の署名に足し、`_ingest_one` の呼び出しに渡す。

```python
def ingest_directory(
    source_dir: Path,
    collection,
    session=None,
    on_progress=None,
    force: bool = False,
    only_suffix: str | None = None,
    caption_image=None,
    keep_code_blocks: bool = False,
) -> IngestReport:
```

`_ingest_one(...)` の呼び出しの最後の引数として `keep_code_blocks` を渡す
（`report` の次）。

`ingest_uploads` は変更しない。画面からのアップロードは社内資料であり、
コードブロック保持は技術ドキュメントの取り込みだけが使う。

- [ ] **Step 4: テストを走らせて通ることを確認する**

Run: `./myvenv313/Scripts/python.exe -m pytest tests/test_ingest_source.py -v`
Expected: PASS

- [ ] **Step 5: CLI に `--db` と `--keep-code-blocks` を足す**

`main()` の `argparse` に足す。

```python
    parser.add_argument(
        "--db",
        type=Path,
        default=store.DB_PATH,
        help=(
            "取り込み先のDBファイル（既定は社内資料の vector_store.sqlite3）。"
            "技術ドキュメントは docs_store.sqlite3 を指定する"
        ),
    )
    parser.add_argument(
        "--keep-code-blocks",
        action="store_true",
        help=(
            "コードブロックを途中で割らずに1チャンクへ収める"
            "（技術ドキュメント向け。社内資料には指定しない）"
        ),
    )
```

`collection = store.open_store(str(DB_PATH))` を次に置き換える。

```python
    # open_store はパスを間違えても例外を出さず空のDBを新規作成する
    # （ingest/store.py の DB_PATH のコメント参照）。タイポは「検索結果が全部空」
    # という静かな失敗になり、テストも緑のまま通る。どのファイルを開いたかを
    # 必ず画面に出し、取り込み後の件数でも裏を取る。
    print(f"取り込み先: {args.db}")
    collection = store.open_store(str(args.db))
```

`ingest_directory(...)` の呼び出しに `keep_code_blocks=args.keep_code_blocks` を
足す。

結果表示の最後（`return 0` の直前）に足す。

```python
    total = collection.count()
    print(f"DB内の総チャンク数: {total}")
    if total == 0:
        # 0件で正常終了すると、検索が全部空になる原因に気づけない。
        print(f"警告: {args.db} は空です。--db のパスが正しいか確認してください")
```

既存の結果表示に総チャンク数の行が既にある場合は、重複させず既存の行を活かして
0件警告だけを足すこと。

- [ ] **Step 6: 手元で動作を確かめる**

Run:
```bash
./myvenv313/Scripts/python.exe -m scripts.ingest_source \
  --source-dir docs_source --db docs_store.sqlite3 --keep-code-blocks
```

Expected: 「取り込み先: docs_store.sqlite3」が出て、各ファイルの取り込みが進み、
最後に総チャンク数が出る。Streamlit だけで4,000件を超える見込みで、埋め込みに
時間がかかる。**Ollama への接続が要る。** `.env` の `OLLAMA_HOST` が Colab を
指している場合はそちらのGPUで走る。

終わったら `vector_store.sqlite3` の更新時刻が変わっていないことを確認する
（社内資料のDBに触れていないこと）。

- [ ] **Step 7: 全体のテスト**

Run: `./myvenv313/Scripts/python.exe -m pytest tests/ -q`
Expected: 705 passed, 3 deselected

- [ ] **Step 8: コミット**

```bash
git add scripts/ingest_source.py tests/test_ingest_source.py
git commit -m "feat: let the ingest CLI target another database and keep code blocks"
```

---

## Task 5: 技術ドキュメント専用のプロンプト

**Files:**
- Modify: `ingest/prompting.py`
- Modify: `tests/test_prompting.py`

**Interfaces:**
- Consumes: `ingest.retrieval.Hit`（`.citation`、`.text`）
- Produces: `ingest.prompting.build_docs_prompt(question: str, hits) -> str`

### 背景（実装者向け）

既存の `build_prompt` は技術ドキュメントには使えない。「社内文書からは回答できない
旨を伝えてください」という歯止めが文面ごと不適切になるためである。

指示の骨子は3つ。

1. 取り込んだドキュメントに書かれている記法だけを使うこと。
2. 知っている古い書き方を混ぜないこと。ドキュメントに無い API を補わないこと。
3. ドキュメントに書かれていなければ、書かれていないと答えること。

**2つめがこの機能の核である。** 1つめだけでは、モデルは文脈を読んだうえで学習時の
記法に戻る余地が残る。

本文に出典を書かせない扱いは社内資料側と揃える（2026-09-12 の変更で
`build_prompt` からも外した）。出典は画面の「参考にした情報」で見せる。

**禁止形の指示には前例がある。** README の「回答の言い回しはプロンプトでは
制御できない」の節に、`llama3.1:8b` で「同じ内容を繰り返さないでください」を
足したところ7回中2回で型番そのものを答えられなくなった、という実測が残っている。
禁止を足したら実機で確かめること（Task 7 で行う）。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_prompting.py` に足す。先頭の import に `build_docs_prompt` を加える。

```python
def test_docs_prompt_tells_the_model_to_use_only_the_retrieved_syntax():
    """この機能の核。文脈を読んだうえで学習時の記法に戻るのを止める。

    「ドキュメントに書かれている記法を使え」だけでは足りない。モデルは
    参考にしたうえで、知っている古い書き方を混ぜる余地が残る。混ぜるなと
    明示的に言う。
    """
    prompt = build_docs_prompt("ダイアログの出し方は", [_hit(text="st.dialog を使う")])
    assert "st.dialog を使う" in prompt
    assert "ダイアログの出し方は" in prompt
    assert "混ぜないでください" in prompt


def test_docs_prompt_does_not_mention_internal_documents():
    """社内資料向けの歯止めをそのまま流用すると文面が嘘になる。

    技術ドキュメントの検索結果に対して「社内文書からは回答できない」と
    答えさせるのは意味が通らない。
    """
    prompt = build_docs_prompt("ダイアログの出し方は", [_hit()])
    assert "社内" not in prompt


def test_docs_prompt_forbids_inventing_an_api():
    prompt = build_docs_prompt("ダイアログの出し方は", [_hit()])
    assert "推測で補わないでください" in prompt


def test_docs_prompt_forbids_writing_the_citation_in_the_answer_body():
    """社内資料側と揃える。出典は画面の畳み込みで見せる。"""
    prompt = build_docs_prompt("ダイアログの出し方は", [_hit()])
    assert "出典を書かないでください" in prompt


def test_docs_prompt_declines_when_there_are_no_hits():
    """根拠が1件も無いときこそ歯止めが要る。

    ここで質問をそのまま返すと、system prompt だけが残りモデルは
    知識で答えにいく。それはこの機能が避けたかったことそのものである。
    """
    prompt = build_docs_prompt("ダイアログの出し方は", [])
    assert "ダイアログの出し方は" in prompt
    assert "見つかりませんでした" in prompt
```

- [ ] **Step 2: テストを走らせて失敗を確認する**

Run: `./myvenv313/Scripts/python.exe -m pytest tests/test_prompting.py -k "docs_prompt" -v`
Expected: FAIL（`ImportError: cannot import name 'build_docs_prompt'`）

- [ ] **Step 3: `build_docs_prompt` を書く**

`ingest/prompting.py` の `build_prompt` の直後に足す。

```python
def build_docs_prompt(question: str, hits) -> str:
    """取り込んだ公式ドキュメントだけを根拠に、最新の記法で答えさせる。

    build_prompt を流用できない。「社内文書からは回答できない旨を伝えて
    ください」という歯止めが、技術ドキュメントの検索結果に対しては文面ごと
    意味を成さないためである。

    核になるのは「知っている古い書き方を混ぜるな」の指示である。「ドキュメントに
    書かれている記法を使え」だけでは足りず、モデルは文脈を参考にしたうえで
    学習時の記法へ戻る余地が残る。この機能はまさにそれを止めるためにある。

    本文に出典を書かせないのは社内資料側と揃えるためである（2026-09-12）。
    出典は画面の「参考にした情報」で見せる。文脈に [出典] を残すのは
    チャンクの境目を示すためで、build_prompt と同じ判断である。
    """
    if not hits:
        return (
            "取り込んだ公式ドキュメントを検索しましたが、"
            "この質問に関連する記述は見つかりませんでした。"
            "推測で答えず、取り込んだドキュメントからは回答できない旨を伝えてください。\n\n"
            f"ユーザーの質問: {question}"
        )
    context = "\n\n".join(f"[{hit.citation}]\n{hit.text}" for hit in hits)
    return (
        "以下は公式ドキュメントから検索した記述です。"
        "ここに書かれている記法だけを使って回答してください。"
        "あなたが知っている古い書き方を混ぜないでください。"
        "ドキュメントに出てこない関数名・引数・設定項目を推測で補わないでください。"
        "必要な記述がドキュメントに無い場合は、無いことをそのまま伝えてください。"
        "回答の本文には [ ] 内の出典を書かないでください。\n\n"
        f"{context}\n\nユーザーの質問: {question}"
    )
```

- [ ] **Step 4: テストを走らせて通ることを確認する**

Run: `./myvenv313/Scripts/python.exe -m pytest tests/test_prompting.py -v`
Expected: PASS

- [ ] **Step 5: コミット**

```bash
git add ingest/prompting.py tests/test_prompting.py
git commit -m "feat: add a prompt that answers from the fetched documentation only"
```

---

## Task 6: 画面のコーパス切り替え

**Files:**
- Modify: `rag_chat_app.py`
- Modify: `tests/test_rag_chat_app.py`

**Interfaces:**
- Consumes: `build_docs_prompt(question, hits)`（Task 5）、
  `store.open_store(path)`、`build_index(collection)`、
  `search(collection, query, index=None, rerank=None)`
- Produces: `rag_chat_app.DOCS_DB_PATH`、`rag_chat_app.CORPUS_INTERNAL`（`"社内資料"`）、
  `rag_chat_app.CORPUS_DOCS`（`"技術ドキュメント"`）

### 背景（実装者向け）

`get_collection` は `@st.cache_resource` でパスを引数に取るので、2つのDBが並行して
キャッシュされる。新しい仕組みは要らない。

**技術ドキュメント側は絞り込み経路（`ingest/catalog.py`）を通さない。** 型番の
絞り込みは社内の製品仕様書に固有の仕組みであり、技術ドキュメントには当てはまらない。
`conditions.extract` も呼ばない（LLM 呼び出しが1回無駄に増える）。

`get_schema` も技術ドキュメント側では呼ばない。絞り込みに使う属性一覧であり、
絞り込みを通さない以上いらない。

**テストのスタブに注意。** 既存の `_stub_open_store(metadata)` が返す factory は
引数を無視して同じインメモリDBを返す。2つのコーパスを区別するテストでは、
パスごとに違う中身を返す factory が要る。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_rag_chat_app.py` に足す。

```python
def _stub_open_store_per_path(bodies):
    """パスごとに中身の違うインメモリDBを返す。

    既存の _stub_open_store は引数を無視して同じDBを返すため、
    2つのコーパスを区別するテストには使えない。
    """
    stores = {}

    def factory(path, *args, **kwargs):
        key = str(path)
        if key not in stores:
            collection = open_real_store(":memory:")
            body = next(
                (text for marker, text in bodies.items() if marker in key),
                "該当なし",
            )
            collection.add(
                ids=["chunk-1"],
                documents=[body],
                embeddings=[[0.1, 0.2]],
                metadatas=[{"source": "a.md", "location_type": "section", "location": 1}],
            )
            stores[key] = collection
        return stores[key]

    return factory


def test_the_corpus_switch_offers_both_choices(app):
    with patch.object(store_module, "open_store", _stub_open_store_per_path({})):
        app.run()
    assert list(app.sidebar.radio[0].options) == ["社内資料", "技術ドキュメント"]


def test_choosing_the_documentation_corpus_searches_the_other_database(app):
    """切り替えが本当に別のDBを引いていることを、返る本文で見る。

    ラジオが画面に出ているだけでは配線されている証拠にならない。
    """
    stream = _fake_stream_chat("回答")
    with (
        patch.object(
            store_module,
            "open_store",
            _stub_open_store_per_path(
                {"docs_store": "st.dialog でダイアログを出します。",
                 "vector_store": "洗濯機の運転音は26dBです。"},
            ),
        ),
        patch.object(retrieval, "embed_query", lambda *a, **k: [0.1, 0.2]),
        patch.object(chat, "stream_chat", stream),
    ):
        app.run()
        app.sidebar.radio[0].set_value("技術ドキュメント").run()
        app.chat_input[0].set_value("ダイアログの出し方は").run()

    sent = stream.calls[-1]["messages"][-1]["content"]
    assert "st.dialog でダイアログを出します。" in sent
    assert "洗濯機" not in sent


def test_the_documentation_corpus_uses_the_documentation_prompt(app):
    """社内資料向けの歯止めが技術ドキュメントに混ざらないことを見る。"""
    stream = _fake_stream_chat("回答")
    with (
        patch.object(
            store_module,
            "open_store",
            _stub_open_store_per_path({"docs_store": "st.dialog を使います。"}),
        ),
        patch.object(retrieval, "embed_query", lambda *a, **k: [0.1, 0.2]),
        patch.object(chat, "stream_chat", stream),
    ):
        app.run()
        app.sidebar.radio[0].set_value("技術ドキュメント").run()
        app.chat_input[0].set_value("ダイアログの出し方は").run()

    sent = stream.calls[-1]["messages"][-1]["content"]
    assert "混ぜないでください" in sent
    assert "社内文書" not in sent


def test_the_internal_corpus_is_unchanged_by_the_switch(app):
    """既定は社内資料で、振る舞いは変更前と同じでなければならない。"""
    stream = _fake_stream_chat("回答")
    with (
        patch.object(
            store_module,
            "open_store",
            _stub_open_store_per_path({"vector_store": "洗濯機の運転音は26dBです。"}),
        ),
        patch.object(retrieval, "embed_query", lambda *a, **k: [0.1, 0.2]),
        patch.object(chat, "stream_chat", stream),
    ):
        app.run()
        app.chat_input[0].set_value("運転音は").run()

    sent = stream.calls[-1]["messages"][-1]["content"]
    assert "洗濯機の運転音は26dBです。" in sent
    assert "社内文書" in sent
```

- [ ] **Step 2: テストを走らせて失敗を確認する**

Run: `./myvenv313/Scripts/python.exe -m pytest tests/test_rag_chat_app.py -k "corpus" -v`
Expected: FAIL（ラジオが存在せず `IndexError`）

- [ ] **Step 3: `rag_chat_app.py` を変更する**

import に `build_docs_prompt` を足す。

```python
from ingest.prompting import (
    build_catalog_prompt,
    build_docs_prompt,
    build_prompt,
    format_hit_caption,
    format_report,
)
```

`DB_PATH = str(store.DB_PATH)` の下に足す。

```python
# 技術ドキュメントの取り込み先。社内資料とはファイルごと分ける。
# 同じDBに入れると、社内規程の質問にライブラリのドキュメントが混ざり、
# 「社内資料に無ければ答えない」という歯止めが効かなくなる。
DOCS_DB_PATH = str(store.DB_PATH.parent / "docs_store.sqlite3")

CORPUS_INTERNAL = "社内資料"
CORPUS_DOCS = "技術ドキュメント"
```

`model = st.sidebar.selectbox(...)` の近く、`collection = get_collection(DB_PATH)` の
**直前**にラジオを置く。

```python
# どちらを検索するかは利用者が選ぶ。質問文からの自動判定にしないのは、
# 誤判定が利用者から見えない失敗になるためである。選択はそのまま
# 「どちらを検索したか」の表示も兼ねる。
corpus = st.sidebar.radio("検索対象", [CORPUS_INTERNAL, CORPUS_DOCS])
searching_docs = corpus == CORPUS_DOCS
```

`collection = get_collection(DB_PATH)` を次に変える。

```python
collection = get_collection(DOCS_DB_PATH if searching_docs else DB_PATH)
```

`schema = get_schema(collection, collection.revision())` を次に変える。

```python
# 絞り込みは社内の製品仕様書に固有の仕組みである。技術ドキュメントでは
# 属性一覧を組み立てない（条件抽出のLLM呼び出しも走らせない）。
schema = None if searching_docs else get_schema(collection, collection.revision())
```

サイドバーの取り込みボタンとアップロードダイアログは社内資料のときだけ出す。
技術ドキュメントの更新は `scripts/fetch_docs.py` と
`scripts/ingest_source.py --db docs_store.sqlite3` で行うためである。
`st.sidebar.caption(f"取り込み元: {DEFAULT_SOURCE_DIR.name}/")` から
`upload_dialog(collection)` までのブロックを `if not searching_docs:` で囲む。
技術ドキュメント側には代わりに案内を出す。

```python
if searching_docs:
    st.sidebar.caption(
        "更新は CLI で行います: "
        "python -m scripts.fetch_docs のあと "
        "python -m scripts.ingest_source --source-dir docs_source "
        "--db docs_store.sqlite3 --keep-code-blocks"
    )
```

検索とプロンプト組み立ての分岐を変える。既存の

```python
        if extraction.conditions:
```

の手前に技術ドキュメントの経路を足し、`extraction` の計算自体も社内資料の
ときだけにする。`extraction = conditions.extract(question, schema, ask_json)` の
行を次に変える。

```python
    # 技術ドキュメントでは条件抽出を走らせない。型番の絞り込みは社内の
    # 製品仕様書に固有の仕組みであり、ここではLLM呼び出しが1回無駄に増えるだけ。
    extraction = (
        conditions.Extraction()
        if searching_docs
        else conditions.extract(question, schema, ask_json)
    )
```

`conditions.Extraction` は `ingest/conditions.py:27` のデータクラスで、
`conditions: dict = field(default_factory=dict)` と `failed: bool = False` を
持つ。引数なしで作れば「条件なし・失敗なし」になり、既存の分岐がそのまま
ベクトル検索へ流れる。

検索の分岐を次にする。

```python
        if searching_docs:
            query = contextual_query(question, st.session_state.messages[:-1])
            hits = search(collection, query, index=index, rerank=rerank_callable)
            user_content = build_docs_prompt(question, hits)
        elif extraction.conditions:
            ...（既存のまま）
        else:
            ...（既存のまま）
```

- [ ] **Step 4: テストを走らせて通ることを確認する**

Run: `./myvenv313/Scripts/python.exe -m pytest tests/test_rag_chat_app.py -v`
Expected: PASS。**既存のテストが1件も落ちないこと。** 落ちる場合、ラジオを
置いた位置が既存のサイドバー要素の順序を壊している可能性がある
（`test_no_quality_switches_are_left_to_the_reader` や
`test_the_close_button_comes_before_the_uploaded_list` が順序を見ている）。

- [ ] **Step 5: 全体のテスト**

Run: `./myvenv313/Scripts/python.exe -m pytest tests/ -q`
Expected: 全件 passed, 3 deselected

- [ ] **Step 6: 画面で確かめる**

Run: `./myvenv313/Scripts/python.exe -m streamlit run rag_chat_app.py`

確認すること:
1. サイドバーに「検索対象」のラジオがあり、既定が「社内資料」。
2. 「社内資料」のまま従来の質問をすると、変更前と同じように答える。
3. 「技術ドキュメント」に切り替えると、取り込みボタンとアップロードが消え、
   CLI の案内が出る。
4. 「Streamlit でダイアログを出すには」と尋ねると、取り込んだドキュメントを
   根拠に答え、「参考にした情報」に `streamlit.md` の出典が出る。

- [ ] **Step 7: コミット**

```bash
git add rag_chat_app.py tests/test_rag_chat_app.py
git commit -m "feat: let the user choose which corpus to search"
```

---

## Task 7: ドキュメントと実機での確認

**Files:**
- Modify: `AGENTS.md`
- Modify: `README.md`
- Modify: `docs/処理箇所マップ.md`

**Interfaces:**
- Consumes: これまでの全タスク
- Produces: なし（ドキュメントのみ）

### 背景（実装者向け）

このリポジトリは実測を文書に残す文化を持っている。推測で数値を書かないこと。
測っていないことは「測っていない」と書く。

- [ ] **Step 1: 実機で「最新の文法で答えるか」を確かめる**

**これは自動テストでは測れない。** 取り込み前後で同じ質問を投げ、結果を記録する。

Ollama に接続した状態で、`streamlit run rag_chat_app.py` を起動し、
**同じ質問を「社内資料」と「技術ドキュメント」の両方で**投げて結果を並べる。
質問は Streamlit の比較的新しい API を狙う。例：

- 「Streamlit でモーダルダイアログを出す書き方を教えて」
- 「Streamlit でマーメイドの図を描くには」
- 「Streamlit のキャッシュはどう書く？」

各3回ずつ投げ、次を記録する。

1. 技術ドキュメント側が、取り込んだドキュメントに実在する API を答えたか。
2. 社内資料側が「回答できない」と正しく答えたか。
3. 本文にファイル名が出ていないか（2026-09-12 の変更が効いているか）。

**3つめは特に注意して見ること。** README の「回答の言い回しはプロンプトでは
制御できない」の節に、禁止形の指示が逆効果になった実測が残っている。効いて
いなければ、文脈から `[出典]` ヘッダーごと外して `【資料1】` のような中立な
区切りにする案がある（見えないものは真似できない）。効かなかった事実も記録する。

- [ ] **Step 2: `AGENTS.md` に3本目の外部通信経路を書く**

「外部ドキュメントの参照」の節の末尾に足す。既存の文が「外部へ出る通信は
context7 だけではない」と述べて2本目（リランカーの HEAD）を挙げているので、
その流れに続ける。

```markdown
- 3本目は `scripts/fetch_docs.py` である。`docs_sources.toml` に書かれたURLへ
  GET を出し、公式ドキュメントの `llms-full.txt` を取得する。送るのはURLへの
  要求だけで、社内資料の内容も検索語も含まない。設定に書かれたURLしか取りに
  行かず、ページ内のリンクは辿らない。人が明示的に起動したときだけ走り、
  常駐プロセスもスケジューラも持たない。オフライン環境では実行できないが、
  取得済みの `docs_source/` があれば取り込みはローカルで完結する。
```

- [ ] **Step 3: `README.md` に使い方を書く**

「対応形式」や取り込みの runbook がある節の近くに、新しい節を足す。

```markdown
## 技術ドキュメントの取り込み

公式ドキュメントを取り込み、モデルの古い知識ではなく取り込んだ記法で
コード例を答えさせる。社内資料とは**別のDB**（`docs_store.sqlite3`）に入れ、
画面のサイドバー「検索対象」で切り替える。

```bash
# 1. 取得（外部通信あり。docs_sources.toml に書かれたURLだけ）
python -m scripts.fetch_docs

# 2. 取り込み（Ollama への接続が要る）
python -m scripts.ingest_source --source-dir docs_source \
    --db docs_store.sqlite3 --keep-code-blocks
```

対象ライブラリは `docs_sources.toml` で管理する。追加するときは
`llms-full.txt` の URL を書くこと。**`llms.txt` は本文ではなくリンクの目次
である**（実測 2026-09-12: `docs.streamlit.io/llms.txt` は66,927バイトあるが
コードフェンスは0個）。`llms-full.txt` を公開していないライブラリは対象に
できない（実測 2026-09-12 で fastapi・pytest・numpy は404）。

`--keep-code-blocks` はコードブロックを途中で割らずに1チャンクへ収める。
指定しないと、実測でチャンクの8.3%がフェンスの途中で割れる。社内資料の
取り込みでは指定しない（結果が変わる）。

`docs_source/` と `docs_store.sqlite3` は追跡しない。`source/` と
`vector_store.sqlite3` と同じく、いつでも取り直せるためである。
```

Step 1 で測った結果を「既知の制約」か新しい節に残す。測っていないことは
書かないこと。

- [ ] **Step 4: `docs/処理箇所マップ.md` に行を足す**

`ingest/prompting.py` と `ingest/chunker.py` の節に、新しい関数の行を足す。
**行番号は実際のファイルを見て書くこと。** 既存の行番号がずれていないかも
確認する（このブランチで `ingest/prompting.py` と `ingest/chunker.py` に
行を挿入しているため、後ろの行がずれている）。

足す行の例（行番号は実際に確認したものに置き換える）:

| 処理 | 場所 |
|---|---|
| `build_docs_prompt()` — 取り込んだドキュメントの記法だけで答えさせる。「古い書き方を混ぜるな」がこの機能の核 | `ingest/prompting.py` |
| `_split_keeping_code()` — コードブロックを分割器に通さず1片として残す。区切りにフェンスを足す案は実測で悪化するため採らない | `ingest/chunker.py` |
| `fetch()` — `llms-full.txt` を優先し、404のときだけ `llms.txt` に落として警告する | `scripts/fetch_docs.py` |

- [ ] **Step 5: 全体のテスト**

Run: `./myvenv313/Scripts/python.exe -m pytest tests/ -q`
Expected: 全件 passed, 3 deselected

- [ ] **Step 6: コミット**

```bash
git add AGENTS.md README.md docs/処理箇所マップ.md
git commit -m "docs: describe the documentation corpus and its egress path"
```

---

## 完了条件（仕様書9節）

1. `python -m scripts.fetch_docs` が `docs_source/` に Markdown を書き出す。
   2回目の実行は「変更なし」と報告し、ファイルを書き換えない。
2. `python -m scripts.ingest_source --source-dir docs_source --db docs_store.sqlite3
   --keep-code-blocks` が完走し、総チャンク数を表示する。
3. 社内資料の `vector_store.sqlite3` は1バイトも変わらない。
4. 画面のラジオで技術ドキュメントを選ぶと、Streamlit の記法に関する質問に
   取り込んだドキュメントを出典として答える。
5. 社内資料を選んだときの挙動が変更前と変わらない。
6. `AGENTS.md` に3本目の外部通信経路が記載されている。
