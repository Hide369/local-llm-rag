"""プロジェクトフォルダを資料源として扱う。

走査して一覧を作り、依頼に要るファイルを選ばせ、本文を読み、成果物を書き戻す。

除外する名前（EXCLUDED_DIR_NAMES）と書き出し先（OUTPUT_DIR_NAME）を同じ場所に
置いているのは、この2つが必ず同時に動かなければならないためである。書き出し先を
走査から外し忘れると、1回目は正しく動き、2回目から自分が書いた文書を根拠にして
次の文書を書く。例外は出ないので気づけない。
"""
import json
from pathlib import Path

from ingest.parsers import SUPPORTED_SUFFIXES, parse

# このシステム自身の出力先。走査から外す（モジュールdocstring参照）。
OUTPUT_DIR_NAME = "generated_docs"

# 隠しディレクトリ（.git .venv .pytest_cache 等）は名前の規則で一括して落とすので
# ここには挙げない。ここに挙げるのは、隠しでない生成物・依存物である。
EXCLUDED_DIR_NAMES = frozenset(
    {OUTPUT_DIR_NAME, "__pycache__", "node_modules", "venv", ".venv"}
)

# 仮想環境のディレクトリ名は決まっていない（myvenv / myvenv313 / .venv など）。
# 前方一致で落とす。
EXCLUDED_DIR_PREFIXES = ("myvenv", "venv")

# プロンプトへ載せるプロジェクト本文の上限。filling.MAX_PROMPT_CHARS(28,000)の
# うち、検索結果・添付・依頼文・指示文に残す分を引いた値である。ここを超える分は
# 落とし、落とした名前を呼び出し元へ返す。
PROJECT_BUDGET_CHARS = 16000


class ProjectFolderError(Exception):
    """指定されたパスをプロジェクトフォルダとして扱えない。"""


def _excluded(name: str) -> bool:
    return (
        name.startswith(".")
        or name in EXCLUDED_DIR_NAMES
        or name.startswith(EXCLUDED_DIR_PREFIXES)
    )


def tree(root: Path) -> list[tuple[str, int]]:
    """`(相対パス, バイト数)` をパスの昇順で返す。

    大きさに文字数ではなくバイト数を使うのは、文字数を出すには全ファイルを
    parse する必要があり、PDF や docx が混ざったフォルダでは走査だけで数十秒
    かかるためである。この一覧は LLM が「どれが要るか」を判断するための目安で
    あり、その用途にはバイト数で足りる。
    """
    if not root.is_dir():
        raise ProjectFolderError(f"フォルダではありません: {root}")
    found = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(_excluded(part) for part in relative.parts[:-1]):
            continue
        if path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        found.append((relative.as_posix(), path.stat().st_size))
    return sorted(found)


def _resolved(root: Path, relative: str) -> Path | None:
    """root の下にある実在のファイルなら絶対パスを、そうでなければ None を返す。

    判定は解決後の絶対パスが root の下にあることで行う。文字列に '..' が含まれるか
    で見ると、シンボリックリンクで外へ出る経路を見逃す。
    """
    root = root.resolve()
    try:
        candidate = (root / relative).resolve()
    except OSError:
        return None
    if not candidate.is_relative_to(root):
        return None
    return candidate if candidate.is_file() else None


def read(
    root: Path, paths: list[str], budget: int = PROJECT_BUDGET_CHARS
) -> tuple[list[tuple[str, str]], list[str]]:
    """選ばれたファイルの本文を、予算の範囲で読む。

    返り値の1つ目は (相対パス, 本文) の並びで、filling.fill_values の attachments に
    そのまま渡せる形である。プロジェクトフォルダは「添付の自動版」であり、専用の
    受け口を作らない。

    2つ目は読まなかったファイル名の並びである。予算で溢れたもの、root の外を
    指していたもの、開けなかったものをすべて含む。呼び出し元が画面で伝える。

    予算で溢れたファイルは飛ばして次へ進む（そこで打ち切らない）。大きいファイルが
    1つ先頭にあるだけで、後ろの小さいファイルまで捨てる理由がない。
    """
    files: list[tuple[str, str]] = []
    skipped: list[str] = []
    used = 0
    for relative in paths:
        path = _resolved(root, relative)
        if path is None:
            skipped.append(relative)
            continue
        try:
            units = parse(path)
        except Exception:
            # 壊れたファイル1つで生成ごと落とすと、残りの根拠まで失う。
            skipped.append(relative)
            continue
        text = "\n".join(unit.text for unit in units).strip()
        if not text or used + len(text) > budget:
            skipped.append(relative)
            continue
        files.append((relative, text))
        used += len(text)
    return files, skipped


def tree_text(entries: list[tuple[str, int]]) -> str:
    """ツリーをプロンプトに載せる形にする。"""
    return "\n".join(f"- {name} ({size} bytes)" for name, size in entries)


def build_selection_prompt(entries: list[tuple[str, int]], question: str) -> str:
    return (
        "あなたは社内文書を作成する担当者です。\n"
        "次の依頼に答えるために、どのファイルの中身を読む必要があるかを選んで"
        "ください。\n\n"
        f"## 依頼\n{question}\n\n"
        f"## ファイル一覧\n{tree_text(entries)}\n\n"
        "読むべきファイルのパスだけを、JSONの配列で返してください。"
        "説明や前置きは書かないでください。\n"
        "一覧に無いパスは返さないでください。\n"
        "依頼に関係のないファイルは選ばないでください。"
        "多く選ぶほど1つあたりに割ける分量が減ります。\n"
    )


def select(entries: list[tuple[str, int]], question: str, ask) -> list[str]:
    """読むべきファイルの相対パスを返す。決まらなければ空を返す。

    壊れた JSON が返っても例外は投げない。止めるとツリーすら渡せず、利用者は
    何も受け取れない。ツリーだけでもファイル構成は伝わる（fill_values が壊れた
    JSON で止めず、ingest/query_translation.py が翻訳の失敗で原文に落ちるのと
    同じ考え方）。

    ask が投げる ChatError は投げ直す。LLM そのものが落ちたことは利用者に伝える
    べき失敗であり、黙って「選択なし」にしてはいけない。
    """
    raw = ask(build_selection_prompt(entries, question))
    try:
        loaded = json.loads(raw)
    except (TypeError, ValueError):
        return []
    if not isinstance(loaded, list):
        return []
    known = {name for name, _ in entries}
    return [name for name in loaded if isinstance(name, str) and name in known]
