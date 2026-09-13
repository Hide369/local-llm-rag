"""公式ドキュメントの llms-full.txt を取得して docs_source/ へ置く。

取得と取り込みを分けている。取得は外部通信を伴い失敗しうるが、取り込みは
ローカルで閉じる。分けておけば、取得が落ちても手元のファイルから取り込み直せる。

設定ファイルに書かれたURLしか取りに行かない。ページ内のリンクは辿らない。
クローラーにはしない。外部へ送るのはURLへのGETだけで、社内資料の内容も
検索語も含まない（AGENTS.md「外部ドキュメントの参照」参照）。
"""
import argparse
import hashlib
import tomllib
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import requests

from scripts import code_references, github_source

_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = _ROOT / "docs_sources.toml"
DEFAULT_OUT_DIR = _ROOT / "docs_source"

# 1.9MBのテキストを落とすことがある。既定の無制限だと、応答が返らない
# サイトでプロセスが止まったままになる。
_TIMEOUT = 60


@dataclass(frozen=True)
class LlmsSource:
    """`llms-full.txt` を1本の URL から取るソース（`kind = "llms"`、既定）。"""

    name: str
    url: str
    version: str


# kind ごとに「使ってよいキー」を決めておく。混ざった設定を黙って無視すると、
# 設定を直したつもりの人が直っていないことに気付けない。
_LLMS_ONLY = ("url",)
_GITHUB_ONLY = ("repo", "ref", "paths", "resolve_code_refs")


def load_sources(path: Path = DEFAULT_CONFIG) -> list:
    """docs_sources.toml を読む。kind で LlmsSource か GitHubSource になる。"""
    with path.open("rb") as handle:
        config = tomllib.load(handle)
    return [_source_of(entry) for entry in config.get("source", [])]


def _source_of(entry: dict):
    kind = entry.get("kind", "llms")
    name = entry["name"]
    version = str(entry["version"])
    if kind == "llms":
        _reject(entry, _GITHUB_ONLY, name, kind)
        return LlmsSource(name=name, url=entry["url"], version=version)
    if kind == "github":
        _reject(entry, _LLMS_ONLY, name, kind)
        return github_source.GitHubSource(
            name=name,
            repo=entry["repo"],
            ref=entry["ref"],
            paths=tuple(entry["paths"]),
            version=version,
            resolve_code_refs=bool(entry.get("resolve_code_refs", False)),
        )
    raise ValueError(
        f'{name} の kind が不明です: {kind!r}（使えるのは "llms" か "github"）'
    )


def _reject(entry: dict, forbidden, name: str, kind: str) -> None:
    found = [key for key in forbidden if key in entry]
    if found:
        raise ValueError(
            f'{name} は kind = "{kind}" なので {"、".join(found)} は書けません'
        )


def _index_url(url: str) -> str:
    """llms-full.txt に対応する llms.txt のURL。"""
    return url.replace("llms-full.txt", "llms.txt")


class NotDocumentationError(Exception):
    """取得はできたが、中身がドキュメントではなかった。

    状態コードだけを見ていると掴めない失敗がある（_looks_like_html 参照）。
    run() はこれを1件の失敗として報告し、他のライブラリの取得は続ける。
    """


# HTML の始まり方。本文の途中に <div> が出てくることは咎めない。
# ドキュメントは HTML の例を載せるものであり、それを理由に捨てると
# 正しい資料まで落とすことになる。
_HTML_PREFIXES = ("<!doctype html", "<html", "<?xml")


def _looks_like_html(text: str, content_type: str) -> bool:
    """HTML のページを掴んでいないか。

    実測 2026-09-13: `python.langchain.com/llms-full.txt` は 404 ではなく、
    ドキュメントサイトの HTML を **200 で** 返した。状態コードしか見ていな
    かったため素通りし、HTML・CSS・JavaScript が1,531チャンク（当時のコーパス
    11,993件の12.8%）DBに入った。正しい URL は
    `docs.langchain.com/llms-full.txt` である。

    この失敗は静かで、診断が遠い。取り込みは成功と表示され、検索も当たり、
    ただ答えが書けないノイズが混ざるだけだからである。掴んだ時点で止める。

    先頭と Content-Type の両方を見るのは、どちらか一方では取りこぼすため。
    doctype を持たない断片を返すサーバーがあり、逆に text/plain と名乗って
    HTML を返すサーバーもある。
    """
    if "text/html" in content_type.lower():
        return True
    return text.lstrip()[:200].lower().startswith(_HTML_PREFIXES)


def fetch(source: LlmsSource, session=None) -> tuple[str, bool]:
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
        return _checked(response, source.url), False

    index = _index_url(source.url)
    if index == source.url:
        response.raise_for_status()
    fallback = session.get(index, timeout=_TIMEOUT)
    fallback.raise_for_status()
    return _checked(fallback, index), True


def _checked(response, url: str) -> str:
    """ドキュメントとして受け入れてよい本文だけを返す。"""
    content_type = getattr(response, "headers", {}).get("Content-Type", "")
    if _looks_like_html(response.text, content_type):
        raise NotDocumentationError(
            f"{url} は本文ではなく HTML のページを返しました"
            f"（Content-Type: {content_type or '不明'}）。"
            "URL が正しいか確認してください"
        )
    return response.text


def _frontmatter(source: LlmsSource, fetched_at: str) -> str:
    return (
        "---\n"
        f"name: {source.name}\n"
        f"url: {source.url}\n"
        f"version: {source.version}\n"
        f"fetched_at: {fetched_at}\n"
        "---\n"
    )


def _without_frontmatter(text: str) -> str:
    """フロントマターを飛ばして本文だけを返す。

    飛ばすのは、そこに fetched_at が入っているためである。含めて比べると、
    内容が同じでも取得日が違えば必ず「変わった」ことになり、差分検知が
    意味をなさなくなる。
    """
    if not text.startswith("---\n"):
        return text
    _, _, rest = text[4:].partition("---\n")
    return rest


def _body_of(path: Path) -> str:
    """書き出し済みファイルから本文だけを取り出す。無ければ空文字。"""
    if not path.is_file():
        return ""
    return _without_frontmatter(path.read_text(encoding="utf-8"))


def write_page_if_changed(relative_path: str, text: str, out_dir: Path) -> bool:
    """1ページを書く。本文が変わっていなければ書かずに False を返す。

    text にはフロントマターを含めて渡す。比べるのは本文だけである。
    """
    # 木の内容は設定ファイルと違ってバージョン管理下に無い入力である。
    # ".." を含むパスを素通しすると out_dir の外へ書き出せてしまう。
    if ".." in relative_path.split("/") or relative_path.startswith("/"):
        raise ValueError(f"ページのパスが不正です: {relative_path!r}")
    path = out_dir / relative_path
    if _digest(_body_of(path)) == _digest(_without_frontmatter(text)):
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def write_if_changed(
    source: LlmsSource, body: str, out_dir: Path, fetched_at: str
) -> bool:
    """本文が変わっていれば書く。書いたら True。"""
    # name はそのままファイル名に使う。docs_sources.toml の name に
    # "../../evil" のようなパス区切りや親ディレクトリ参照が書かれていると、
    # out_dir の外（実測: docs_source/ の2階層上）へ書き出せてしまう。
    # 設定ファイルはバージョン管理下にあり悪意ある入力の危険は低いが、
    # 防ぐのに1行で足りるので防ぐ。
    if "/" in source.name or "\\" in source.name or ".." in source.name:
        raise ValueError(
            f"name にパス区切りや親ディレクトリ参照は使えません: {source.name!r}"
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{source.name}.md"
    if _digest(_body_of(path)) == _digest(body):
        return False
    path.write_text(_frontmatter(source, fetched_at) + body, encoding="utf-8")
    return True


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class FetchReport:
    updated: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)
    # llms-full.txt が無く llms.txt に落ちたもの。取り込んでも目次しか入らない。
    index_only: list[str] = field(default_factory=list)
    # GitHub ソースの内訳。ソース単位の updated/unchanged では、1,000ページの
    # うち何ページが書かれたか・落ちたかが分からない。
    pages_written: dict[str, int] = field(default_factory=dict)
    pages_failed: dict[str, int] = field(default_factory=dict)
    # 解決できなかった :::code。黙って落とすと、コードの入っていないページが
    # 混ざったことに気付けない。
    unresolved_code_refs: dict[str, int] = field(default_factory=dict)


def run(sources, out_dir: Path, fetched_at: str, session=None, notify=None) -> FetchReport:
    report = FetchReport()
    say = notify or (lambda _message: None)
    for source in sources:
        try:
            if isinstance(source, github_source.GitHubSource):
                _run_github(source, out_dir, fetched_at, session, say, report)
            else:
                _run_llms(source, out_dir, fetched_at, session, say, report)
        except Exception as error:  # 1件の失敗で残りを止めない
            report.failed[source.name] = str(error)
            say(f"失敗: {source.name} — {error}")
            continue
    return report


def _run_llms(source, out_dir, fetched_at, session, say, report) -> None:
    """`llms-full.txt` を1本取って1ファイルに書く。

    fetch と write_if_changed の両方を呼び出し元の try の中に置く。書き込み側
    だけ外に出すと、ディスク満杯や権限エラーが拾われずに run() の外へ抜けて
    しまい、残りのソースが一切試されなくなる（設計書5.2節「1件が失敗しても
    残りを続ける」は fetch に限定していない）。
    """
    say(f"取得中: {source.name} — {source.url}")
    body, fell_back = fetch(source, session=session)
    if fell_back:
        report.index_only.append(source.name)
        say(
            f"警告: {source.name} は llms-full.txt が無く llms.txt に落ちました。"
            "取り込めるのはリンクの目次だけで、記法の質問には答えられません"
        )
    if write_if_changed(source, body, out_dir, fetched_at):
        report.updated.append(source.name)
        say(f"更新: {source.name}（{len(body.encode('utf-8'))}バイト）")
    else:
        report.unchanged.append(source.name)
        say(f"変更なし: {source.name}")


def _run_github(source, out_dir, fetched_at, session, say, report) -> None:
    """1ソース分のページを取って書く。

    木の取得の失敗と truncated は呼び出し元へ抜けさせ、ソース全体の失敗に
    する。土台が無ければ、どのページが抜けたかも分からないためである。
    1ページの取得失敗はここで飲み込み、残りのページを続ける。
    """
    say(f"取得中: {source.name} — {source.repo}@{source.ref}")
    active = session or requests
    tree = github_source.fetch_tree(source.repo, source.ref, active)
    pages = github_source.select_pages(tree, source.paths)
    say(f"{source.name}: {len(pages)}ページ（commit {tree.commit[:10]}）")

    blob_paths = set(tree.paths)
    written = failed = unresolved = 0
    for page_path in pages:
        try:
            body = github_source.fetch_blob(source.repo, source.ref, page_path, active)
        except Exception as error:
            failed += 1
            say(f"警告: {source.name} の {page_path} を取得できません — {error}")
            continue
        body = github_source.strip_liquid(body)
        if source.resolve_code_refs:
            body, missed = code_references.resolve_code_references(
                body,
                page_path,
                blob_paths,
                lambda path: github_source.fetch_blob(
                    source.repo, source.ref, path, active
                ),
            )
            unresolved += missed
        text = github_source.render_page(source, tree.commit, page_path, body, fetched_at)
        # フロントマターの source_path はリポジトリ内の完全なパスを残すが、
        # 置き場所は共通部分を落とした相対パスにする（github_source.local_path）。
        local = github_source.local_path(page_path, source.paths)
        if write_page_if_changed(f"{source.name}/{local}", text, out_dir):
            written += 1

    report.pages_written[source.name] = written
    report.pages_failed[source.name] = failed
    report.unresolved_code_refs[source.name] = unresolved
    if written:
        report.updated.append(source.name)
        say(f"更新: {source.name}（{written}ページ、失敗{failed}件）")
    else:
        report.unchanged.append(source.name)
        say(f"変更なし: {source.name}（{len(pages)}ページ）")
    if unresolved:
        say(f"警告: {source.name} で解決できなかった :::code が{unresolved}件あります")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="docs_sources.toml のドキュメントを docs_source/ へ取得する"
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    if not args.config.is_file():
        print(f"設定ファイルがありません: {args.config}")
        return 1

    # docs_sources.toml はライブラリを1つ足すたびに手で編集するファイルであり、
    # 書式の崩れ（例: [[source] のかっこ抜け）も必須キーの書き忘れ（例: version
    # を書かない）も、想定外の事故ではなく起こりうる入力である。ここで拾わないと
    # tomllib.TOMLDecodeError や KeyError の生のトレースバックがそのまま
    # ターミナルへ出てしまう。
    try:
        sources = load_sources(args.config)
    except tomllib.TOMLDecodeError as error:
        print(f"設定ファイルの書式が不正です: {args.config} — {error}")
        return 1
    except KeyError as error:
        print(f"設定ファイルに必須のキーがありません: {args.config} — {error}")
        return 1

    if not sources:
        print(f"{args.config} に [[source]] が1件もありません")
        return 1

    report = run(sources, args.out_dir, date.today().isoformat(), notify=print)

    print("\n--- 結果 ---")
    print(f"更新: {len(report.updated)}件")
    print(f"変更なし: {len(report.unchanged)}件")
    for name, count in report.pages_written.items():
        print(f"  {name}: {count}ページ書き出し / 取得失敗{report.pages_failed[name]}件")
    for name, count in report.unresolved_code_refs.items():
        if count:
            print(f"  {name}: 解決できなかった :::code が{count}件")
    if report.index_only:
        print(f"目次のみ（本文が取れていません）: {'、'.join(report.index_only)}")
    for name, message in report.failed.items():
        print(f"失敗 {name}: {message}")
    # 全滅は設定かネットワークの問題である。終了コードで分かるようにする。
    return 1 if report.failed and not (report.updated or report.unchanged) else 0


if __name__ == "__main__":
    raise SystemExit(main())
