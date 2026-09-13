"""リポジトリに置いた Markdown を docs_source/ へ写す（`kind = "local"`）。

外部通信をしない3本目の経路である。`kind = "llms"` と `kind = "github"` は
どちらも公開されている Markdown が前提だが、それが無い資料がある。最初の例が
Go の言語仕様で、公式は HTML（go.dev/ref/spec）しか出しておらず、golang/website
のリポジトリにも `spec.html` しか無い（docs/コーディング対応ライブラリ.md 1節）。
人が md 化した原本をリポジトリに置き、ここから写す。

`docs_source/` は `fetch_docs` の出力であって入力ではない。2026-09-13 に移植先の
都合で追跡対象にしたが（`.gitignore`）、中身は取り直せば同じものが再現する前提の
ままである。手で置いたファイルはその前提を破る。`docs_sources.toml` に記録が残らず
どの版を入れたのか追えなくなり、`docs_source/` を作り直せば黙って消える。実測
2026-09-13: 未登録のまま置かれた Go 仕様書の生コピーが `go/doc/` に紛れており、
取り込めば go-spec.md と重複した劣化版（pandoc属性が残り1節が最大82,825バイト）が
入るところだった。原本をバージョン管理下（`docs/pg_data/`）に置き、写す側を
`docs_sources.toml` に書いておけば、他のソースと同じ1コマンドで復元できる。

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

    title は「原本の H1 は章題であって資料の題名ではない」と言うための欄である。
    取り込み側の約束は「H1 が1つだけあり、それが資料の題名。`## ` が節の境界」
    （ingest/parsers/md_parser.py の parse_md）で、H1 が複数ある原本はこれを
    破る。2つ目以降の H1 は題名として拾われず、本文の中に `# 章題` という行の
    まま、直前の章の最後の節に紛れ込む。ここに題名を書くと、原本の H1 は章題
    として節の境界（`## `）へ下ろし、資料の題名はこの文字列から1行だけ作る。
    """

    name: str
    path: str
    version: str
    section_level: int = 2
    title: str = ""


# 見出しの行。取り込み側（md_parser）が見るのは `## ` だけだが、階層を動かす
# には全階層を捕まえる必要がある。
_HEADING = re.compile(r"^(?P<hashes>#{1,6})(?P<space>[ \t]+)(?P<title>.*)$")

# 見出しの末尾に付く pandoc の属性。`{#Introduction}` `{#x .subtitle}` の形。
#
# `{` で始まる末尾すべてを落とすと、見出しの中のコード（`## The empty struct {}`）
# まで消える。落としてよいのは `#`（id）か `.`（class）で始まる属性だけである。
_ATTRIBUTES = re.compile(r"[ \t]*\{[#.][^{}]*\}[ \t]*$")


def normalise(body: str, section_level: int = 2, demote_h1: bool = False) -> str:
    """取り込み側が読める形へ整える。

    1. 見出しの末尾の pandoc 属性を落とす。`{#Introduction}` は HTML の id から
       機械的に作られた名残で本文ではない。残すと出典の見出しが
       「Introduction {#Introduction}」になり、埋め込むテキストにも同じ語が
       二重に入る（実測 2026-09-13: Go の仕様書は168見出しすべてに付いていた）。
    2. section_level 以下の見出しを `## ` まで引き上げる。取り込み側は `## ` だけを
       節の境界にする（ingest/parsers/md_parser.py 冒頭）。Go の仕様書は H2 が
       20個しかなく、1節が最大82,825バイトになる。H3（108個）まで境界にすると
       中央値1,076バイトになり、`For statements` のように質問の単位と揃う。
    3. demote_h1 なら H1 も `## ` へ下ろす。原本の H1 が章題であって資料の題名では
       ない場合で、題名は LocalSource.title から別に作る（render_page）。

    demote_h1 でないかぎり H1 と H2 は動かさない。H1 は資料の題名で、取り込み側が
    各節の先頭へ1行付けるためのものである。増やすとどれが題名なのか決まらなくなる。

    階層が潰れることは許容している。C# の仕様書を section_level=4 で写すと
    H1〜H4 がすべて `## ` になるが、この資料の見出しは「9.4.4.15 Try-finally
    ステートメント」のように番号が階層を持っているため、`#` の数を失っても
    どこの節かは見出し文字列だけで分かる。番号の無い資料にこの設定を使うと
    分からなくなる。

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
        if level == 1:
            level = 2 if demote_h1 else 1
        elif level > 2:
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

    指紋は生バイトではなく、潰したあとの本文から取る。原本はバージョン管理下に
    あり、チェックアウトで改行コードが書き換わる（実測: Windows で LF の原本が
    CRLF になる）。生バイトを数えると、内容が1文字も変わっていないのにマシンごとに
    違う指紋が記録される。
    """
    if Path(source.path).is_absolute() or ".." in Path(source.path).parts:
        raise ValueError(
            f"{source.name} の path はリポジトリ内の相対パスで書いてください: "
            f"{source.path!r}"
        )
    path = root / source.path
    if not path.is_file():
        raise FileNotFoundError(f"原本がありません: {path}")
    text = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
    return text, hashlib.sha256(text.encode("utf-8")).hexdigest()


def render_page(
    source: LocalSource, body: str, fetched_at: str, digest: str
) -> str:
    """1ファイルを docs_source/ へ書く形に整える。

    github ソースが commit を持つのと同じ理由で、原本のパスと SHA-256 を残す。
    書き出した本文は normalise を通っており原本と同じではないので、何をしたかも
    残す（section_level）。

    source.title があるなら、本文の先頭へ `# 題名` を1行足す。原本の H1 は
    normalise が章題として `## ` へ下ろしているので、この1行を足さないと題名が
    1つも無い本文になり、取り込み側が各節の先頭に付ける資料名が空になる
    （parse_md の title）。フロントマターの title はどちらの経路でも同じ文字列に
    なるが、取り込み側が読むのは本文の H1 のほうである。
    """
    title = source.title or title_of(body)
    text = without_frontmatter(body)
    if source.title:
        text = f"# {source.title}\n\n{text.lstrip()}"
    return (
        "---\n"
        f"name: {source.name}\n"
        f"source_path: {source.path}\n"
        f"sha256: {digest}\n"
        f"title: {title}\n"
        f"section_level: {source.section_level}\n"
        f"version: {source.version}\n"
        f"fetched_at: {fetched_at}\n"
        "---\n"
    ) + text
