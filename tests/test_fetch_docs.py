"""公式ドキュメントの取得。

ネットワークへは絶対に出ない。requests.Session を差し替えて、
状態コードと本文をこちらで決める。
"""
import sys

import pytest
import requests

from scripts import fetch_docs, github_source, local_source


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
    return fetch_docs.LlmsSource(name=name, url=url, version=version)


def test_load_sources_reads_the_name_url_and_version(tmp_path):
    config = tmp_path / "docs_sources.toml"
    config.write_text(
        '[[source]]\nname = "streamlit"\n'
        'url = "https://example.test/llms-full.txt"\nversion = "1.61.1"\n',
        encoding="utf-8",
    )
    sources = fetch_docs.load_sources(config)
    assert sources == [
        fetch_docs.LlmsSource(
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

    version は "1.61.1" のようにドットを2つ以上含む値にする。md_parser._scalar は
    数値に見える値を int/float へ変換するため、"1.0" のような値を使うと
    round-trip後に文字列ではなくfloatになってしまい、本テストの意図（バージョンが
    文字列として読み戻せること）を検証できない。
    """
    from ingest.parsers.md_parser import parse_md

    fetch_docs.write_if_changed(
        _source(version="1.61.1"), "# Streamlit\n\n## ダイアログ\n\n本文\n", tmp_path, "2026-09-12"
    )
    units = parse_md(tmp_path / "streamlit.md")

    assert units
    assert units[0].attributes["name"] == "streamlit"
    assert units[0].attributes["version"] == "1.61.1"
    assert "---" not in units[0].text
    assert "fetched_at" not in units[0].text


def test_run_reports_updated_unchanged_and_failed(tmp_path):
    sources = [
        fetch_docs.LlmsSource("a", "https://a.test/llms-full.txt", "1"),
        fetch_docs.LlmsSource("b", "https://b.test/llms-full.txt", "2"),
        fetch_docs.LlmsSource("c", "https://c.test/llms-full.txt", "3"),
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
        fetch_docs.LlmsSource("a", "https://a.test/llms-full.txt", "1"),
        fetch_docs.LlmsSource("b", "https://b.test/llms-full.txt", "2"),
        fetch_docs.LlmsSource("c", "https://c.test/llms-full.txt", "3"),
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
    """目次しか取れなかったことは、報告に必ず残す（仕様書4.1節）。

    report オブジェクトだけでなく notify に渡る文言も見る。CLI利用者は
    report ではなく notify の出力しか目にしないため、そちらで警告が
    読めなければ「本文が取れていない」ことに気づけない。
    """
    sources = [fetch_docs.LlmsSource("a", "https://a.test/llms-full.txt", "1")]
    session = _FakeSession({"https://a.test/llms.txt": _FakeResponse(200, "- [x](/x)\n")})
    messages = []
    report = fetch_docs.run(
        sources, tmp_path, "2026-09-12", session=session, notify=messages.append
    )
    assert report.index_only == ["a"]
    assert report.updated == ["a"]
    assert any("llms.txt" in message and "警告" in message for message in messages)


def test_run_continues_after_a_write_failure(tmp_path, monkeypatch):
    """書き込みが落ちても、他のソースは続けて取りに行く。

    write_if_changed を try/except の外に出していると、ディスク満杯や
    権限エラーがここで run() の外へ抜け、b・c が一切試されなくなる。
    fetch の失敗と同じ扱いにすることを monkeypatch で確かめる。
    """
    sources = [
        fetch_docs.LlmsSource("a", "https://a.test/llms-full.txt", "1"),
        fetch_docs.LlmsSource("b", "https://b.test/llms-full.txt", "2"),
        fetch_docs.LlmsSource("c", "https://c.test/llms-full.txt", "3"),
    ]
    session = _FakeSession(
        {
            "https://a.test/llms-full.txt": _FakeResponse(200, "A\n"),
            "https://b.test/llms-full.txt": _FakeResponse(200, "B\n"),
            "https://c.test/llms-full.txt": _FakeResponse(200, "C\n"),
        }
    )
    real_write_if_changed = fetch_docs.write_if_changed

    def _fail_for_b(source, body, out_dir, fetched_at):
        if source.name == "b":
            raise OSError("disk full")
        return real_write_if_changed(source, body, out_dir, fetched_at)

    monkeypatch.setattr(fetch_docs, "write_if_changed", _fail_for_b)

    report = fetch_docs.run(sources, tmp_path, "2026-09-12", session=session)

    assert report.updated == ["a", "c"]
    assert list(report.failed) == ["b"]
    assert (tmp_path / "a.md").is_file()
    assert (tmp_path / "c.md").is_file()


def test_run_notifies_progress_per_source(tmp_path):
    sources = [fetch_docs.LlmsSource("a", "https://a.test/llms-full.txt", "1")]
    session = _FakeSession({"https://a.test/llms-full.txt": _FakeResponse(200, "A\n")})
    messages = []
    fetch_docs.run(sources, tmp_path, "2026-09-12", session=session, notify=messages.append)
    assert any("a" in message for message in messages)


def test_write_if_changed_rejects_a_name_with_parent_directory_reference(tmp_path):
    """name に ../../evil のような親ディレクトリ参照が来ると、out_dir の外
    （実測: docs_source/ の2階層上）へ書き出せてしまう。設定ファイルは
    バージョン管理下で危険は低いが、1行で防げるので防ぐ。"""
    source = _source(name="../../evil")
    with pytest.raises(ValueError):
        fetch_docs.write_if_changed(source, "本文\n", tmp_path, "2026-09-12")
    assert not (tmp_path.parent.parent / "evil.md").exists()


def test_write_if_changed_rejects_a_name_with_a_path_separator(tmp_path):
    source = _source(name="sub/evil")
    with pytest.raises(ValueError):
        fetch_docs.write_if_changed(source, "本文\n", tmp_path, "2026-09-12")


def test_main_reports_a_malformed_toml_file_instead_of_a_traceback(tmp_path, monkeypatch, capsys):
    """[[source] のようにかっこが崩れた設定は tomllib.TOMLDecodeError になる。

    docs_sources.toml はライブラリを足すたびに手で編集するファイルなので、
    書式ミスは例外的な入力ではなく通常起こりうる入力として扱う。
    """
    config = tmp_path / "docs_sources.toml"
    config.write_text('[[source]\nname = "streamlit"\n', encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["fetch_docs", "--config", str(config)])

    assert fetch_docs.main() == 1

    out = capsys.readouterr().out
    assert str(config) in out
    assert "不正" in out


def test_main_reports_a_missing_required_key_instead_of_a_traceback(
    tmp_path, monkeypatch, capsys
):
    """version を書き忘れると load_sources 内で KeyError('version') になる。"""
    config = tmp_path / "docs_sources.toml"
    config.write_text(
        '[[source]]\nname = "streamlit"\nurl = "https://example.test/llms-full.txt"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "argv", ["fetch_docs", "--config", str(config)])

    assert fetch_docs.main() == 1

    out = capsys.readouterr().out
    assert str(config) in out
    assert "version" in out


# 実測 2026-09-13: python.langchain.com/llms-full.txt は 404 ではなく、
# ドキュメントサイトの HTML を 200 で返した。素通しした結果、HTML・CSS・
# JavaScript が1,531チャンク（当時のコーパスの12.8%）DBに入り、検索で
# 引けるノイズになった。正しいURLは docs.langchain.com/llms-full.txt である。
_HTML_PAGE = (
    '<!DOCTYPE html><html lang="en"><head><title>Docs</title>'
    "<script>var a=1;</script></head><body>…</body></html>"
)


def test_fetch_rejects_an_html_page_served_with_a_success_status():
    """200 で返る HTML を本文として受け入れない。

    状態コードだけでは足りない。取り込んでしまうと、失敗が「検索がノイズを
    引く」という形でしか現れず、原因に辿り着くまでが遠い。
    """
    session = _FakeSession(
        {"https://example.test/llms-full.txt": _FakeResponse(200, _HTML_PAGE)}
    )
    with pytest.raises(fetch_docs.NotDocumentationError) as error:
        fetch_docs.fetch(_source(), session=session)
    assert "HTML" in str(error.value)


def test_fetch_rejects_html_by_content_type_even_without_a_doctype():
    """本文の見た目に頼らず Content-Type も見る。

    doctype を持たない断片を返すサーバーもある。どちらか一方でも
    HTML だと分かれば受け入れない。
    """
    session = _FakeSession(
        {
            "https://example.test/llms-full.txt": _FakeResponse(
                200, "<div>本文ではない</div>", content_type="text/html; charset=utf-8"
            )
        }
    )
    with pytest.raises(fetch_docs.NotDocumentationError):
        fetch_docs.fetch(_source(), session=session)


def test_fetch_accepts_markdown_that_merely_mentions_html():
    """HTML の話をしている Markdown は本文である。誤検出しない。

    ドキュメントは HTML の例を載せることがある。先頭が HTML かどうかで
    判定し、本文中に <div> が出てくることを理由に捨てない。
    """
    body = "\n".join(
        ["# 見出し", "", "HTML を埋め込むには:", "", "```html", "<div>x</div>", "```", ""]
    )
    session = _FakeSession(
        {"https://example.test/llms-full.txt": _FakeResponse(200, body)}
    )
    text, fell_back = fetch_docs.fetch(_source(), session=session)
    assert text == body
    assert fell_back is False


def test_an_html_response_is_reported_as_a_failure_not_written(tmp_path):
    """HTML を掴んだソースは failed に入り、ファイルを書かない。

    run() は1件の失敗で止まらないので、他のライブラリの取得は続く。
    """
    sources = [
        fetch_docs.LlmsSource("a", "https://a.test/llms-full.txt", "1"),
        fetch_docs.LlmsSource("b", "https://b.test/llms-full.txt", "2"),
    ]
    session = _FakeSession(
        {
            "https://a.test/llms-full.txt": _FakeResponse(200, _HTML_PAGE),
            "https://b.test/llms-full.txt": _FakeResponse(200, "# 本文\n"),
        }
    )
    report = fetch_docs.run(sources, tmp_path, "2026-09-13", session=session)

    assert list(report.failed) == ["a"]
    assert report.updated == ["b"]
    assert not (tmp_path / "a.md").exists()


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
        'resolve_code_refs = true\nversion = "0.0.0"\n',
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


def test_the_real_config_file_loads():
    """docs_sources.toml は手で編集するファイルである。壊れたまま気付かないと、
    取得を走らせたときに初めて分かる。"""
    sources = fetch_docs.load_sources(fetch_docs.DEFAULT_CONFIG)
    assert [source.name for source in sources] == [
        "streamlit",
        "langchain-text-splitters",
        "ollama",
        "huggingface_hub",
        "pymupdf",
        "mcp",
        "csharp",
        "go",
        "go-spec",
        "csharp-spec",
        "python-spec",
        "mermaid",
        "markdown",
    ]
    by_name = {source.name: source for source in sources}
    assert by_name["csharp"].resolve_code_refs is True
    assert by_name["go"].resolve_code_refs is False
    assert by_name["streamlit"].url == "https://docs.streamlit.io/llms-full.txt"
    assert by_name["go-spec"].section_level == 3
    # 原本の H1 が31個とも章題なので、題名は設定側で決める。
    assert by_name["csharp-spec"].title == "C# 言語仕様書"
    assert by_name["go-spec"].title == ""
    # 原本の H1 は11個。1つ目が題名で残り10個は章題なので、こちらも設定側で決める。
    assert by_name["python-spec"].section_level == 4
    assert by_name["python-spec"].title == "The Python Language Reference"


def test_the_local_origin_files_exist():
    """原本が消えると取得が落ちる。設定と現物のずれをここで掴む。

    kind = "local" だけは、取得の成否がネットワークではなくリポジトリの中身で
    決まる。ファイルを動かした人がテストで気付けるようにしておく。
    """
    root = fetch_docs.DEFAULT_CONFIG.parent
    for source in fetch_docs.load_sources(fetch_docs.DEFAULT_CONFIG):
        if isinstance(source, local_source.LocalSource):
            assert (root / source.path).is_file(), source.path


def test_write_page_if_changed_writes_a_page_whose_body_is_empty(tmp_path):
    """「ファイルが無い」と「本文が空」は違う。

    どちらも空文字のダイジェストになるため、区別しないと本文の無いページが
    黙って書かれないまま残る。実測 2026-09-13: go の96ページ中8件、mermaid と
    markdown の index.md がこれで、報告には出ないまま消えていた。
    """
    written = fetch_docs.write_page_if_changed(
        "go/doc/copyright.md", "---\nname: go\n---\n", tmp_path
    )
    assert written is True
    assert (tmp_path / "go" / "doc" / "copyright.md").is_file()


def test_run_reports_pages_that_carry_no_body(tmp_path):
    """本文の無いページは取り込んでも0チャンクにしかならないので書かない。

    ただし黙って落とさず数える。選別したページ数と書き出したページ数が
    説明なく食い違うと、取りこぼしと区別が付かない。
    """
    session = _FakeSession(
        {
            _TREE: _tree_response(["docs/csharp/linq/a.md", "docs/csharp/linq/i.md"]),
            f"{_RAW}/docs/csharp/linq/a.md": _FakeResponse(200, "# A\n"),
            f"{_RAW}/docs/csharp/linq/i.md": _FakeResponse(200, "---\nredirect: /x\n---\n"),
        }
    )
    report = fetch_docs.run([_CSHARP], tmp_path, "2026-09-13", session=session)
    assert report.pages_written == {"csharp": 1}
    assert report.pages_empty == {"csharp": 1}
    assert not (tmp_path / "csharp" / "i.md").exists()


# --- kind = "local"（リポジトリに置いた Markdown を写す） ---


def test_load_sources_reads_a_local_source(tmp_path):
    config = tmp_path / "docs_sources.toml"
    config.write_text(
        '[[source]]\nname = "go-spec"\nkind = "local"\n'
        'path = "docs/pg_data/go-language-specification.md"\n'
        'section_level = 3\nversion = "go1.27"\n',
        encoding="utf-8",
    )
    assert fetch_docs.load_sources(config) == [
        local_source.LocalSource(
            name="go-spec",
            path="docs/pg_data/go-language-specification.md",
            section_level=3,
            version="go1.27",
        )
    ]


def test_load_sources_defaults_the_section_level_to_two(tmp_path):
    """既定は原文の階層のままである。下ろすのは明示したソースだけ。"""
    config = tmp_path / "docs_sources.toml"
    config.write_text(
        '[[source]]\nname = "x"\nkind = "local"\npath = "a.md"\nversion = "0.0.0"\n',
        encoding="utf-8",
    )
    assert fetch_docs.load_sources(config)[0].section_level == 2


def test_load_sources_reads_the_title_of_a_local_source(tmp_path):
    """原本の H1 が章題である資料は、題名を設定側で決める。"""
    config = tmp_path / "docs_sources.toml"
    config.write_text(
        '[[source]]\nname = "x"\nkind = "local"\npath = "a.md"\n'
        'title = "C# 言語仕様書"\nversion = "0.0.0"\n',
        encoding="utf-8",
    )
    assert fetch_docs.load_sources(config)[0].title == "C# 言語仕様書"


def test_load_sources_defaults_the_title_to_empty(tmp_path):
    """既定は原本の H1 を題名に使う。go-spec がこちらである。"""
    config = tmp_path / "docs_sources.toml"
    config.write_text(
        '[[source]]\nname = "x"\nkind = "local"\npath = "a.md"\nversion = "0.0.0"\n',
        encoding="utf-8",
    )
    assert fetch_docs.load_sources(config)[0].title == ""


def test_load_sources_rejects_a_title_on_a_github_source(tmp_path):
    """title は local のキーである。github 側の題名は各ページが持っている。"""
    config = tmp_path / "docs_sources.toml"
    config.write_text(
        '[[source]]\nname = "x"\nkind = "github"\nrepo = "a/b"\nref = "main"\n'
        'paths = ["docs"]\ntitle = "題名"\nversion = "0.0.0"\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        fetch_docs.load_sources(config)


def test_load_sources_rejects_a_url_on_a_local_source(tmp_path):
    config = tmp_path / "docs_sources.toml"
    config.write_text(
        '[[source]]\nname = "x"\nkind = "local"\npath = "a.md"\n'
        'url = "https://example.test/llms-full.txt"\nversion = "0.0.0"\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        fetch_docs.load_sources(config)


def test_load_sources_rejects_a_path_on_a_github_source(tmp_path):
    """path は local のキーである。github に書いても効かない。"""
    config = tmp_path / "docs_sources.toml"
    config.write_text(
        '[[source]]\nname = "x"\nkind = "github"\nrepo = "a/b"\nref = "main"\n'
        'paths = ["docs"]\npath = "a.md"\nversion = "0.0.0"\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        fetch_docs.load_sources(config)


def _local(**kwargs):
    defaults = dict(name="go-spec", path="docs/spec.md", version="go1.27")
    defaults.update(kwargs)
    return local_source.LocalSource(**defaults)


def _with_origin(root, text="# 題名\n\n## 節\n\n本文\n"):
    (root / "docs").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "spec.md").write_text(text, encoding="utf-8")


def test_run_writes_a_local_source_next_to_the_other_sources(tmp_path):
    root, out = tmp_path / "repo", tmp_path / "out"
    _with_origin(root)
    session = _FakeSession({})
    report = fetch_docs.run(
        [_local()], out, "2026-09-13", session=session, root=root
    )
    assert report.updated == ["go-spec"]
    assert (out / "go-spec.md").is_file()
    # 外部へは1回も出ない。原本は手元にある。
    assert session.urls == []


def test_run_applies_the_section_level_when_writing_a_local_source(tmp_path):
    root, out = tmp_path / "repo", tmp_path / "out"
    _with_origin(root, "# 題名\n\n## 章 {#Ch}\n\n### 節 {#Se}\n\n本文\n")
    fetch_docs.run([_local(section_level=3)], out, "2026-09-13", root=root)
    written = (out / "go-spec.md").read_text(encoding="utf-8")
    assert "## 節\n" in written
    assert "{#Se}" not in written


def test_run_turns_chapter_h1s_into_sections_when_a_title_is_configured(tmp_path):
    """題名を設定に書いた資料は、原本の H1 が節の境界になる。

    書き出したファイルには H1 が1つだけ（設定の題名）残る。取り込み側はそれを
    資料名として各節の先頭に付ける。
    """
    root, out = tmp_path / "repo", tmp_path / "out"
    _with_origin(root, "# 6 字句構造 {#c6}\n\n本文\n\n# 7 基本的な概念\n\n本文\n")
    fetch_docs.run([_local(title="C# 言語仕様書")], out, "2026-09-13", root=root)
    written = (out / "go-spec.md").read_text(encoding="utf-8")
    body = written.partition("\n---\n")[2]
    assert body.startswith("# C# 言語仕様書\n")
    assert "## 6 字句構造\n" in body
    assert "## 7 基本的な概念\n" in body
    assert [line for line in body.split("\n") if line.startswith("# ")] == [
        "# C# 言語仕様書"
    ]


def test_run_counts_an_unchanged_local_source_as_unchanged(tmp_path):
    """差分取り込みに乗せる。取得日だけが違うファイルを書き直さない。"""
    root, out = tmp_path / "repo", tmp_path / "out"
    _with_origin(root)
    fetch_docs.run([_local()], out, "2026-09-13", root=root)
    report = fetch_docs.run([_local()], out, "2026-09-20", root=root)
    assert report.unchanged == ["go-spec"]


def test_run_reports_a_missing_local_file_as_a_failure(tmp_path):
    """原本はバージョン管理下にある。消えていたら気付けるようにする。"""
    root, out = tmp_path / "repo", tmp_path / "out"
    root.mkdir()
    report = fetch_docs.run([_local()], out, "2026-09-13", root=root)
    assert "go-spec" in report.failed
    assert not (out / "go-spec.md").exists()


def test_run_continues_to_the_next_source_after_a_local_failure(tmp_path):
    root, out = tmp_path / "repo", tmp_path / "out"
    root.mkdir()
    session = _FakeSession(
        {"https://example.test/llms-full.txt": _FakeResponse(200, "# 本文\n")}
    )
    report = fetch_docs.run(
        [_local(), _source()], out, "2026-09-13", session=session, root=root
    )
    assert list(report.failed) == ["go-spec"]
    assert report.updated == ["streamlit"]


# --- 書き出す改行コード ---


def test_write_page_if_changed_writes_lf_on_every_platform(tmp_path):
    """docs_source/ は .gitattributes で `-text` にしてあり git が改行を直さない。

    CRLF で書くと、内容が1文字も変わっていないファイルまで生バイトが変わる。
    scripts/ingest_source.py の file_hash() は生バイトの SHA-256 なので、DB を
    一緒に持ち込んだ移植先で、差分取り込みのつもりが全量再取り込みになる。
    """
    fetch_docs.write_page_if_changed("a.md", "---\nx: 1\n---\n本文\n", tmp_path)
    assert b"\r" not in (tmp_path / "a.md").read_bytes()


def test_write_if_changed_writes_lf_on_every_platform(tmp_path):
    """llms 経路も同じ。書き出し先が同じ docs_source/ である。"""
    source = fetch_docs.LlmsSource(
        name="x", url="https://example.com/llms-full.txt", version="1"
    )
    fetch_docs.write_if_changed(source, "本文\n", tmp_path, "2026-09-15")
    assert b"\r" not in (tmp_path / "x.md").read_bytes()


def test_write_page_if_changed_rewrites_a_file_that_was_left_with_crlf(tmp_path):
    """既に CRLF で書かれてしまったファイルは、本文が変われば LF に直る。

    読み戻す _body_of は universal newlines で読むため比較が改行に鈍感で、
    本文が同じままなら CRLF のファイルは書き直されない。直るのは書くときだけで
    ある。それを承知のうえで、書いたときには必ず直ることを確かめる。
    """
    path = tmp_path / "a.md"
    path.write_bytes("---\r\nx: 1\r\n---\r\n古い本文\r\n".encode("utf-8"))
    assert fetch_docs.write_page_if_changed("a.md", "---\nx: 1\n---\n新しい本文\n", tmp_path)
    assert b"\r" not in path.read_bytes()
