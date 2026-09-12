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


def run(sources, out_dir: Path, fetched_at: str, session=None, notify=None) -> FetchReport:
    report = FetchReport()
    say = notify or (lambda _message: None)
    for source in sources:
        say(f"取得中: {source.name} — {source.url}")
        try:
            # fetch と write_if_changed の両方をここに含める。書き込み側だけ
            # 外に出すと、ディスク満杯や権限エラーがここで拾われずに run() の
            # 外へ抜けてしまい、残りのソースが一切試されなくなる
            # （仕様書5.2節「1件が失敗しても残りを続ける」はfetchに限定していない）。
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
        except Exception as error:  # 1件の失敗で残りを止めない
            report.failed[source.name] = str(error)
            say(f"失敗: {source.name} — {error}")
            continue
    return report


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
    if report.index_only:
        print(f"目次のみ（本文が取れていません）: {'、'.join(report.index_only)}")
    for name, message in report.failed.items():
        print(f"失敗 {name}: {message}")
    # 全滅は設定かネットワークの問題である。終了コードで分かるようにする。
    return 1 if report.failed and not (report.updated or report.unchanged) else 0


if __name__ == "__main__":
    raise SystemExit(main())
