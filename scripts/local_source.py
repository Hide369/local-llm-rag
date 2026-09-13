"""リポジトリに置いた Markdown を docs_source/ へ写す（`kind = "local"`）。

外部通信をしない3本目の経路である。`kind = "llms"` と `kind = "github"` は
どちらも公開されている Markdown が前提だが、それが無い資料がある。最初の例が
Go の言語仕様で、公式は HTML（go.dev/ref/spec）しか出しておらず、golang/website
のリポジトリにも `spec.html` しか無い（docs/コーディング対応ライブラリ.md 1節）。
人が md 化した原本をリポジトリに置き、ここから写す。

`docs_source/` は .gitignore 済みで「いつでも取り直せる」ことが前提の場所である。
手で置いたファイルはその前提を破り、`docs_source/` を作り直した瞬間に黙って
消える。原本をバージョン管理下に置き、写す側を `docs_sources.toml` に書いて
おけば、他のソースと同じ1コマンドで復元できる。

写すときに2つだけ本文を直す（normalise）。どちらも取り込み側の都合であって
内容の書き換えではない。原本 `docs/pg_data/` は1バイトも触らない。
"""
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from ingest.parsers.md_parser import scan_fences
from scripts.github_source import title_of, without_frontmatter


@dataclass(frozen=True)
class LocalSource:
    """リポジトリ内の Markdown を1ファイル取るソース。

    path はリポジトリの根からの相対パスである。section_level は「どの階層までを
    節の境界にするか」で、既定の2は原文の階層をそのまま使う。
    """

    name: str
    path: str
    version: str
    section_level: int = 2


# 見出しの行。取り込み側（md_parser）が見るのは `## ` だけだが、階層を動かす
# には全階層を捕まえる必要がある。
_HEADING = re.compile(r"^(?P<hashes>#{1,6})(?P<space>[ \t]+)(?P<title>.*)$")

# 見出しの末尾に付く pandoc の属性。`{#Introduction}` `{#x .subtitle}` の形。
#
# `{` で始まる末尾すべてを落とすと、見出しの中のコード（`## The empty struct {}`）
# まで消える。落としてよいのは `#`（id）か `.`（class）で始まる属性だけである。
_ATTRIBUTES = re.compile(r"[ \t]*\{[#.][^{}]*\}[ \t]*$")


def normalise(body: str, section_level: int = 2) -> str:
    """取り込み側が読める形へ整える。

    1. 見出しの末尾の pandoc 属性を落とす。`{#Introduction}` は HTML の id から
       機械的に作られた名残で本文ではない。残すと出典の見出しが
       「Introduction {#Introduction}」になり、埋め込むテキストにも同じ語が
       二重に入る（実測 2026-09-13: Go の仕様書は168見出しすべてに付いていた）。
    2. section_level 以下の見出しを `## ` まで引き上げる。取り込み側は `## ` だけを
       節の境界にする（ingest/parsers/md_parser.py 冒頭）。Go の仕様書は H2 が
       20個しかなく、1節が最大82,825バイトになる。H3（108個）まで境界にすると
       中央値1,076バイトになり、`For statements` のように質問の単位と揃う。

    H1 と H2 は動かさない。H1 は資料の題名で、取り込み側が各節の先頭へ1行付ける
    ためのものである。増やすとどれが題名なのか決まらなくなる。

    コードフェンスの中は本文ではないので触らない。規則は取り込み側と同じものを
    使う（scan_fences）。シェルの `### コメント` や Markdown の例が見出しとして
    数えられると、節が現れる場所がずれる。
    """
    shift = max(section_level - 2, 0)
    out = []
    for line, in_fence in scan_fences(body.split("\n")):
        heading = None if in_fence else _HEADING.match(line)
        if heading is None:
            out.append(line)
            continue
        level = len(heading.group("hashes"))
        if level > 2:
            level = max(level - shift, 2)
        title = _ATTRIBUTES.sub("", heading.group("title"))
        out.append(f"{'#' * level}{heading.group('space')}{title}")
    return "\n".join(out)


def read_body(source: LocalSource, root: Path) -> tuple[str, str]:
    """原本の本文と、その SHA-256 を返す。

    `docs_sources.toml` はバージョン管理下にあり悪意ある入力の危険は低いが、
    根の外を指すパスは防ぐのに1行で足りるので防ぐ（write_if_changed の name と
    同じ判断）。

    CRLF をここで潰すのは、残したまま写すと取り込み側の見出しの末尾に \\r が
    残り、出典が壊れるためである（md_parser._read_lines と同じ理由）。
    """
    if Path(source.path).is_absolute() or ".." in Path(source.path).parts:
        raise ValueError(
            f"{source.name} の path はリポジトリ内の相対パスで書いてください: "
            f"{source.path!r}"
        )
    path = root / source.path
    if not path.is_file():
        raise FileNotFoundError(f"原本がありません: {path}")
    raw = path.read_bytes()
    text = raw.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
    return text, hashlib.sha256(raw).hexdigest()


def render_page(
    source: LocalSource, body: str, fetched_at: str, digest: str
) -> str:
    """1ファイルを docs_source/ へ書く形に整える。

    github ソースが commit を持つのと同じ理由で、原本のパスと SHA-256 を残す。
    書き出した本文は normalise を通っており原本と同じではないので、何をしたかも
    残す（section_level）。
    """
    return (
        "---\n"
        f"name: {source.name}\n"
        f"source_path: {source.path}\n"
        f"sha256: {digest}\n"
        f"title: {title_of(body)}\n"
        f"section_level: {source.section_level}\n"
        f"version: {source.version}\n"
        f"fetched_at: {fetched_at}\n"
        "---\n"
    ) + without_frontmatter(body)
