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
