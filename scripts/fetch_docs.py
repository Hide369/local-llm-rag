"""公式ドキュメントの llms-full.txt を取得して docs_source/ へ置く。

取得と取り込みを分けている。取得は外部通信を伴い失敗しうるが、取り込みは
ローカルで閉じる。分けておけば、取得が落ちても手元のファイルから取り込み直せる。

設定ファイルに書かれたURLしか取りに行かない。ページ内のリンクは辿らない。
クローラーにはしない。外部へ送るのはURLへのGETだけで、社内資料の内容も
検索語も含まない（AGENTS.md「外部ドキュメントの参照」参照）。
"""
import hashlib
import tomllib
from dataclasses import dataclass
from pathlib import Path

import requests

_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = _ROOT / "docs_sources.toml"
DEFAULT_OUT_DIR = _ROOT / "docs_source"

# 1.9MBのテキストを落とすことがある。既定の無制限だと、応答が返らない
# サイトでプロセスが止まったままになる。
_TIMEOUT = 60


@dataclass(frozen=True)
class DocSource:
    name: str
    url: str
    version: str


def load_sources(path: Path = DEFAULT_CONFIG) -> list[DocSource]:
    with path.open("rb") as handle:
        config = tomllib.load(handle)
    return [
        DocSource(name=entry["name"], url=entry["url"], version=str(entry["version"]))
        for entry in config.get("source", [])
    ]


def _index_url(url: str) -> str:
    """llms-full.txt に対応する llms.txt のURL。"""
    return url.replace("llms-full.txt", "llms.txt")


def fetch(source: DocSource, session=None) -> tuple[str, bool]:
    """本文と、目次に落ちたかどうかを返す。

    llms.txt は各ページへのリンクの目次であって本文ではない（実測 2026-09-12:
    docs.streamlit.io/llms.txt は66,927バイトだがコードフェンスは0個）。
    目次を取り込んでも記法の質問には答えられないので、落ちたことを必ず伝える。
    黙って取り込むと、検索は当たるのに答えが書けないという診断しにくい
    状態になる。
    """
    session = session or requests
    response = session.get(source.url, timeout=_TIMEOUT)
    if response.status_code < 400:
        return response.text, False

    index = _index_url(source.url)
    if index == source.url:
        response.raise_for_status()
    fallback = session.get(index, timeout=_TIMEOUT)
    fallback.raise_for_status()
    return fallback.text, True


def _frontmatter(source: DocSource, fetched_at: str) -> str:
    return (
        "---\n"
        f"name: {source.name}\n"
        f"url: {source.url}\n"
        f"version: {source.version}\n"
        f"fetched_at: {fetched_at}\n"
        "---\n"
    )


def _body_of(path: Path) -> str:
    """書き出し済みファイルから本文だけを取り出す。無ければ空文字。

    フロントマターを飛ばすのは、そこに fetched_at が入っているためである。
    含めて比べると、内容が同じでも取得日が違えば必ず「変わった」ことになり、
    差分検知が意味をなさなくなる。
    """
    if not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return text
    _, _, rest = text[4:].partition("---\n")
    return rest


def write_if_changed(
    source: DocSource, body: str, out_dir: Path, fetched_at: str
) -> bool:
    """本文が変わっていれば書く。書いたら True。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{source.name}.md"
    if _digest(_body_of(path)) == _digest(body):
        return False
    path.write_text(_frontmatter(source, fetched_at) + body, encoding="utf-8")
    return True


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
