"""リポジトリに置いた Markdown を docs_source/ へ写す経路（kind = "local"）。

外部通信は一切しない。ここで確かめるのは「どう写すか」だけである。
"""
import pytest

from scripts import local_source


def _source(**kwargs):
    defaults = dict(
        name="go-spec",
        path="docs/pg_data/go-language-specification.md",
        version="go1.27",
    )
    defaults.update(kwargs)
    return local_source.LocalSource(**defaults)


# --- 見出し属性の除去 ---


def test_normalise_strips_the_pandoc_anchor_from_a_heading():
    """`{#Introduction}` は pandoc がHTMLのidから作る名残で、本文ではない。

    残すと出典の見出しが「Introduction {#Introduction}」になり、埋め込む
    テキストにも同じ語が二重に入る。
    """
    body = "## Introduction {#Introduction}\n\n本文\n"
    assert local_source.normalise(body) == "## Introduction\n\n本文\n"


def test_normalise_strips_an_attribute_block_with_a_class():
    body = "## Language version go1.27 {#language-version .subtitle}\n"
    assert local_source.normalise(body) == "## Language version go1.27\n"


def test_normalise_keeps_braces_that_are_not_an_attribute_block():
    """`{` で始まる末尾すべてを落とすと、見出しの中のコードまで消える。

    落としてよいのは pandoc の属性（`{#id}` `{.class}`）だけである。
    """
    body = "## The empty struct {}\n"
    assert local_source.normalise(body) == "## The empty struct {}\n"


def test_normalise_leaves_body_text_alone():
    """属性を落とすのは見出しの行だけである。本文の波かっこは触らない。"""
    body = "本文の {#anchor} はそのまま\n"
    assert local_source.normalise(body) == body


# --- 節の境界を下の階層へ下ろす ---


def test_normalise_promotes_the_third_level_when_the_section_level_is_three():
    """取り込み側は `## ` だけを節の境界にする（ingest/parsers/md_parser.py）。

    Go の仕様書は H2 が20個しかなく、1節が最大82KBになる。H3（108個）まで
    境界にすると1節が中央値1,076バイトになり、質問の単位と揃う。
    """
    body = "## Expressions\n\n### For statements\n\n本文\n"
    assert local_source.normalise(body, section_level=3) == (
        "## Expressions\n\n## For statements\n\n本文\n"
    )


def test_normalise_shifts_the_levels_below_the_section_level_too():
    """H3 を H2 にしたのに H4 を残すと、見出しの階層が1つ飛ぶ。"""
    body = "### 節\n\n#### 小見出し\n\n##### さらに下\n"
    assert local_source.normalise(body, section_level=3) == (
        "## 節\n\n### 小見出し\n\n#### さらに下\n"
    )


def test_normalise_never_promotes_a_heading_into_the_title():
    """H1 は資料の題名で、取り込み側が各節の先頭へ1行付ける。

    増やすと、どれが題名なのか決まらなくなる。
    """
    body = "# 題名\n\n## 節\n"
    assert local_source.normalise(body, section_level=3) == body


def test_normalise_leaves_the_levels_alone_by_default():
    """既定（section_level=2）は原文の階層を変えない。"""
    body = "## 節\n\n### 小見出し\n"
    assert local_source.normalise(body) == body


# --- コードフェンスの中は本文ではない ---


def test_normalise_does_not_touch_headings_inside_a_code_fence():
    """フェンスの中の `###` はシェルのコメントやMarkdownの例である。

    規則は取り込み側と同じ（ingest/parsers/md_parser.py の FENCE_LINE）。
    """
    body = "```sh\n### これはコメント {#not-an-anchor}\n```\n\n### 本物の見出し\n"
    assert local_source.normalise(body, section_level=3) == (
        "```sh\n### これはコメント {#not-an-anchor}\n```\n\n## 本物の見出し\n"
    )


def test_normalise_tracks_an_indented_opening_fence():
    """字下げされた開きフェンスを数え落とすと、そこから先が全部本文になる。

    この取りこぼしは実測で2,205件の見出しを失わせた（commit 9c212ee）。
    """
    body = "  ```go\n### 例 {#x}\n  ```\n\n### 見出し\n"
    assert local_source.normalise(body, section_level=3) == (
        "  ```go\n### 例 {#x}\n  ```\n\n## 見出し\n"
    )


# --- 中身の無いHTMLのアンカー ---


def test_normalise_drops_a_line_that_is_only_an_anchor():
    """`<span id="x"></span>` は見出しの `{#id}` と同じ、HTML の id の名残である。

    実測 2026-09-13: Python の言語リファレンスに303個・15,145バイトあり、うち
    171個はそれだけの行になっていた。残すと本文として索引に入る。
    """
    body = '<span id="datamodel--code-objects"></span>\n\n本文\n'
    assert local_source.normalise(body) == "\n本文\n"


def test_normalise_removes_an_inline_anchor_but_keeps_the_line():
    """行の途中にあるものは、その部分だけ落とす。周りの文は本文である。"""
    body = 'これは<span id="x"></span>本文である\n'
    assert local_source.normalise(body) == "これは本文である\n"


def test_normalise_keeps_a_span_that_has_content():
    """中身のある span は本文を持っている。落とすと文が消える。"""
    body = '<span id="x">大事な語</span>\n'
    assert local_source.normalise(body) == body


def test_normalise_strips_an_anchor_from_a_heading_line():
    """アンカーが見出しの行頭に付いていても、見出しとして扱えること。"""
    body = '<span id="x"></span>## 節 {#anchor}\n'
    assert local_source.normalise(body) == "## 節\n"


def test_normalise_does_not_touch_an_anchor_inside_a_code_fence():
    """フェンスの中は HTML の例そのものであることがある。"""
    body = '```html\n<span id="x"></span>\n```\n'
    assert local_source.normalise(body) == body


# --- 章題の H1（題名が1つに決まらない資料）---


def test_normalise_leaves_h1_alone_by_default():
    """H1 は資料の題名である。既定では動かさない。"""
    body = "# 題名\n\n## 節\n"
    assert local_source.normalise(body, section_level=3) == body


def test_normalise_demotes_every_h1_to_a_section_boundary():
    """章題の H1 は節の境界へ下ろす。

    取り込み側は最初の H1 だけを題名として拾い、2つ目以降は `# 章題` という行の
    まま本文に残す（ingest/parsers/md_parser.py の parse_md）。C# の仕様書は H1 が
    31個あり、30個の章題が直前の章の最後の節に紛れ込む。
    """
    body = "# 6 字句構造\n\n本文\n\n# 7 基本的な概念\n"
    assert local_source.normalise(body, demote_h1=True) == (
        "## 6 字句構造\n\n本文\n\n## 7 基本的な概念\n"
    )


def test_normalise_demotes_h1_together_with_the_section_level():
    """C# の設定（section_level=4 + demote_h1）は H1〜H4 をすべて境界にする。

    H1..H3 までを境界にすると1節が最大55,115バイト残る（9.4.4 確定代入）。H4 まで
    下ろすと、残る最大は文法の付録（54,596バイト、1つのコード塊）だけになる。
    """
    body = (
        "# 9 変数\n\n## 9.4 確定代入\n\n### 9.4.4 正確なルール\n\n"
        "#### 9.4.4.15 Try-finally\n\n##### 補足\n"
    )
    assert local_source.normalise(body, section_level=4, demote_h1=True) == (
        "## 9 変数\n\n## 9.4 確定代入\n\n## 9.4.4 正確なルール\n\n"
        "## 9.4.4.15 Try-finally\n\n### 補足\n"
    )


def test_normalise_still_strips_the_anchor_from_a_demoted_h1():
    body = "# 序文 {#foreword}\n"
    assert local_source.normalise(body, demote_h1=True) == "## 序文\n"


def test_normalise_does_not_demote_an_h1_inside_a_code_fence():
    body = "```sh\n# コメント\n```\n\n# 章題\n"
    assert local_source.normalise(body, demote_h1=True) == (
        "```sh\n# コメント\n```\n\n## 章題\n"
    )


# --- 書き出す形 ---


def test_render_page_adds_the_title_as_the_only_h1():
    """題名が本文に無いと、取り込み側が各節の先頭に付ける資料名が空になる。

    normalise が章題の H1 を全部下ろしたあと、本文には H1 が1つも残らない。
    """
    text = local_source.render_page(
        _source(title="C# 言語仕様書"), "## 序文\n\n本文\n", "2026-09-13", "abc"
    )
    body = text.partition("\n---\n")[2]
    assert body.startswith("# C# 言語仕様書\n")
    assert "\n# " not in body


def test_render_page_uses_the_configured_title_over_the_original_one():
    """設定に書いた題名のほうが、原本のフロントマターより後から決めたものである。"""
    text = local_source.render_page(
        _source(title="C# 言語仕様書"),
        "---\ntitle: C# 言語仕様書（統合版）\n---\n## 序文\n",
        "2026-09-13",
        "abc",
    )
    assert "title: C# 言語仕様書\n" in text.partition("\n---\n")[0]


def test_render_page_leaves_the_body_alone_without_a_title():
    """題名を書いていない資料（go-spec）は原本の H1 をそのまま題名に使う。"""
    text = local_source.render_page(_source(), "# 題名\n\n## 節\n", "2026-09-13", "abc")
    assert text.partition("\n---\n")[2] == "# 題名\n\n## 節\n"


def test_render_page_records_where_the_body_came_from():
    """出典の再現に要るのは、原本のパスと中身の指紋である。

    github ソースが commit を持つのと同じ理由で、どの版を写したかを残す。
    """
    text = local_source.render_page(
        _source(), "# The Go Programming Language Specification\n", "2026-09-13", "abc123"
    )
    head = text.partition("\n---\n")[0]
    assert "name: go-spec" in head
    assert "source_path: docs/pg_data/go-language-specification.md" in head
    assert "sha256: abc123" in head
    assert "title: The Go Programming Language Specification" in head
    assert "version: go1.27" in head
    assert "fetched_at: 2026-09-13" in head


def test_render_page_records_the_section_level_when_it_was_changed():
    """書き出した本文が原本と違うなら、違う理由をファイル自身に残す。"""
    text = local_source.render_page(
        _source(section_level=3), "# 題名\n", "2026-09-13", "abc123"
    )
    assert "section_level: 3" in text.partition("\n---\n")[0]


def test_render_page_replaces_the_original_frontmatter():
    """原本にフロントマターがあっても、--- が2組並ばないようにする。

    取り込み側は先頭のフロントマターしか読まない。2組並ぶと2組目の生のYAMLが
    そのまま索引される。題名だけは引き継ぐ（github 経路と同じ）。
    """
    text = local_source.render_page(
        _source(), "---\ntitle: 元\nredirect: /x\n---\n# 題名\n", "2026-09-13", "abc"
    )
    assert text.count("\n---\n") == 1
    assert "redirect: /x" not in text
    assert "title: 元" in text


# --- 原本の読み込み ---


def test_read_body_reads_a_file_under_the_root(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "spec.md").write_text("# 題名\n", encoding="utf-8")
    body, digest = local_source.read_body(_source(path="docs/spec.md"), tmp_path)
    assert body == "# 題名\n"
    assert len(digest) == 64


def test_read_body_rejects_a_path_that_escapes_the_root(tmp_path):
    """設定ファイルはバージョン管理下だが、防ぐのに1行で足りるので防ぐ。"""
    with pytest.raises(ValueError):
        local_source.read_body(_source(path="../../secret.md"), tmp_path)


def test_read_body_rejects_an_absolute_path(tmp_path):
    with pytest.raises(ValueError):
        local_source.read_body(_source(path="C:/secret.md"), tmp_path)


def test_read_body_reports_a_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        local_source.read_body(_source(path="docs/none.md"), tmp_path)


def test_read_body_normalises_crlf(tmp_path):
    """CRLF のまま写すと、取り込み側の見出しに \r が残る。"""
    (tmp_path / "spec.md").write_bytes(b"# ok\r\n## a\r\n")
    body, _ = local_source.read_body(_source(path="spec.md"), tmp_path)
    assert body == "# ok\n## a\n"


def test_read_body_gives_the_same_digest_for_both_line_endings(tmp_path):
    """原本はチェックアウトで改行コードが書き換わる（Windowsでは LF → CRLF）。

    生バイトを数えると、内容が1文字も変わっていないのにマシンごとに違う指紋が
    フロントマターへ記録される。
    """
    (tmp_path / "lf.md").write_bytes(b"# ok\n## a\n")
    (tmp_path / "crlf.md").write_bytes(b"# ok\r\n## a\r\n")
    _, lf = local_source.read_body(_source(path="lf.md"), tmp_path)
    _, crlf = local_source.read_body(_source(path="crlf.md"), tmp_path)
    assert lf == crlf
