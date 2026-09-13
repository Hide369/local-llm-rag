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
#
# 行頭に空白と ">" を許す。指令は箇条書きの中で字下げされていたり、引用ブロックの
# 中にあったりする。実測 2026-09-13（581ページ）: 字下げ254件、引用3件。行頭しか
# 見ていなかったときは、どちらも解決されず報告にも出ずに素通りしていた。
# 数えられない取りこぼしがいちばん悪い。
#
# 置き換えるフェンスは字下げも引用もしない。ingest/chunker.py の _CODE_BLOCK は
# 行頭の ``` しか見ないため、前に何か付くとコードブロックとして扱われなくなる。
_DIRECTIVE = re.compile(r"^[ \t>]*:::code\s+(?P<attrs>.*?):::[ \t]*$", re.MULTILINE)
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
        # 属性名を小書きに揃える。ID= と大文字で書いたページが3件あった
        # （実測 2026-09-13）。
        attributes = {
            key.lower(): value for key, value in _ATTRIBUTE.findall(match.group("attrs"))
        }
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
    # .cs の先頭に BOM が付いていることがある。落とさないとファイルの最初の
    # 印だけが見つからない（実測 2026-09-13: 13件）。
    code = code.lstrip("﻿")
    if "id" in attributes:
        return _region(code, attributes["id"])
    if "range" in attributes:
        return _range(code, attributes["range"])
    return code.strip("\n")


def _region(code: str, name: str) -> str | None:
    """id= が指す範囲の中身。

    印の書き方は1つではない。実測 2026-09-13 の内訳がこれを決めている。

    - `// <Name>` 〜 `// </Name>` — いまの dotnet/docs が使う形。`#region` しか
      見ていなかったとき、581ページの取得で1,384件が解決できなかった。
    - `#region Name` 〜 `#endregion` — 古い形。まだ残っている。
    - 印の名前に `Snippet` が前置されることがある（`id="PublicAccess"` が
      `//<SnippetPublicAccess>` を指す）。木にある .cs を参照しながら印が
      見つからなかった333件のうち、219件がこれだった。

    字下げを落とすのは、印の中が class やメソッドの内側にあって丸ごと
    字下げされているためである。そのまま差し込むと動かないコードになる。
    """
    for candidate in (name, f"Snippet{name}"):
        found = _between(code, candidate)
        if found is not None:
            return found
    return None


def _between(code: str, name: str) -> str | None:
    for opening, closing in (
        (rf"^[ \t]*//[ \t]*<{re.escape(name)}>[ \t]*$", r"^[ \t]*//[ \t]*</"),
        (rf"^[ \t]*#region[ \t]+{re.escape(name)}[ \t]*$", r"^[ \t]*#endregion"),
    ):
        start = re.search(opening, code, re.MULTILINE)
        if start is None:
            continue
        rest = code[start.end() :]
        end = re.search(closing, rest, re.MULTILINE)
        body = rest[: end.start()] if end else rest
        return textwrap.dedent(body).strip("\n")
    return None


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
