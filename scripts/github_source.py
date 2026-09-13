"""GitHub のリポジトリから Markdown のページを取ってくる。

`llms-full.txt` を公開していない対象（C#・Go・Markdown・Mermaid）へ届かせる
ための経路である。設計書4.1節の実測のとおり、これらには他に経路が無い
（Go・C#・Java・Rust は404、Kotlin は200だがコードフェンス0個の目次）。

Trees API で木を1回引き、本文は raw.githubusercontent.com から取る。未認証で
足りる（実測 2026-09-13: 4リポジトリとも200。必要な呼び出しはリポジトリに
つき1回で、未認証枠は60回/時）。raw は CDN で API のレート制限の対象外である。

設定に書かれたリポジトリとパスしか取りに行かない。クローラーにはしない。
"""
import re
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
    response = session.get(
        f"{API}/repos/{repo}/git/trees/{ref}?recursive=1", timeout=_TIMEOUT
    )
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
