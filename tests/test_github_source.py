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
