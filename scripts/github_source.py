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
