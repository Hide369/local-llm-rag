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
