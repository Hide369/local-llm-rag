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

# ファイル一覧に載せる上限。MAX_PROMPT_CHARS(28,000)から PROJECT_BUDGET_CHARS
# (16,000)を引いた12,000が、依頼文・指示文・検索結果・添付に残る分である。
# 一覧はその半分までとする。ここを無制限にすると、このリポジトリのように
# 一覧だけで MAX_PROMPT_CHARS を超え（実測 67,193文字）、雛形なしの生成が
# 本文0件・検索結果0件のまま PromptTooLongError で止まる。
TREE_BUDGET_CHARS = 6000


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


def tree_text(
    entries: list[tuple[str, int]], budget: int = TREE_BUDGET_CHARS
) -> tuple[str, int]:
    """ツリーをプロンプトに載せる形にする。

    2つ目の返り値は予算で落とした件数である。黙って全部載せると、この設計書
    自身の参照実装であるこのリポジトリのように一覧だけで MAX_PROMPT_CHARS を
    超えうる（TREE_BUDGET_CHARS のコメント参照）。落とすときは末尾に件数を
    書いた行を足す。件数を書かないと、利用者はモデルが一覧の一部しか
    見ていないことに気づけない。
    """
    lines: list[str] = []
    used = 0
    omitted = 0
    for index, (name, size) in enumerate(entries):
        line = f"- {name} ({size} bytes)"
        cost = len(line) + (1 if lines else 0)  # 2行目以降は改行の1文字も数える
        if used + cost > budget:
            omitted = len(entries) - index
            break
        lines.append(line)
        used += cost
    if omitted:
        lines.append(f"- （ほか {omitted} 件は一覧に載せきれませんでした）")
    return "\n".join(lines), omitted


# モデルに渡す道具。プロジェクトの中へ触れる口はこれ1つだけで、書き込みも
# コマンド実行も渡さない。読む側だけをループにするのがこの機能の範囲である。
_TOOL_NAME = "read_files"

READ_FILES_TOOL = {
    "type": "function",
    "function": {
        "name": _TOOL_NAME,
        "description": (
            "プロジェクトフォルダの中のファイルを読む。"
            "一覧に出ている相対パスで指定する。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "読むファイルの相対パス",
                }
            },
            "required": ["paths"],
        },
    },
}

# 何周まで回すか。MAX_PROMPT_CHARS(28,000) の内訳が、一覧 TREE_BUDGET_CHARS(6,000)
# ＋本文 PROJECT_BUDGET_CHARS(16,000) ＋依頼と指示で約6,000である。1周ごとに
# assistant と tool のメッセージが履歴へ積まれるので、収まるのはこの回数までである。
MAX_ROUNDS = 3


def _opening_message(entries: list[tuple[str, int]], question: str) -> str:
    listing, _omitted = tree_text(entries)
    return (
        "あなたは社内文書を作成する担当者です。\n"
        "次の依頼に答えるために、必要なファイルを read_files で読んでください。\n\n"
        f"## 依頼\n{question}\n\n"
        f"## ファイル一覧\n{listing}\n\n"
        "一覧に無いパスは指定しないでください。\n"
        "読んだ結果を見て足りなければ、もう一度 read_files を呼べます。\n"
        "十分に読めたら、道具を呼ばずにその旨だけ答えてください。\n"
    )


def _requested_paths(call: dict) -> list[str]:
    """道具の呼び出しから相対パスの並びを取り出す。

    arguments は辞書で返るモデルと JSON 文字列で返すモデルがある。どちらでも
    同じ結果になるようにする。読めない形なら空を返す。その周が空振りするだけで、
    ループ自体は次へ進める。
    """
    arguments = (call.get("function") or {}).get("arguments")
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except (TypeError, ValueError):
            return []
    if not isinstance(arguments, dict):
        return []
    paths = arguments.get("paths")
    if isinstance(paths, str):
        # 1つだけ渡すときに配列にし忘れるモデルがある。
        paths = [paths]
    if not isinstance(paths, list):
        return []
    return [path for path in paths if isinstance(path, str)]


def _tool_reply(files: list[tuple[str, str]], skipped: list[str]) -> str:
    """読んだ結果をモデルへ返す文面。読めなかったものも伝える。

    伝えないと、モデルは同じパスを何度も要求して周回を使い切る。
    """
    parts = [f"【{name}】\n{text}" for name, text in files]
    if skipped:
        parts.append("読めませんでした: " + "、".join(skipped))
    return "\n\n".join(parts) or "読めたファイルはありません。"


def gather(
    root: Path,
    entries: list[tuple[str, int]],
    question: str,
    ask_tools_call,
    budget: int = PROJECT_BUDGET_CHARS,
) -> tuple[list[tuple[str, str]], list[str]]:
    """モデルに読むファイルを選ばせ、読み、足りなければもう一周する。

    1回で選ばせる形では、読んでみて初めて要ると分かったファイルを取れない。
    そのためにここだけをループにしてある。**書き込みもコマンド実行も渡さない。**

    予算は周をまたいで1つである。周ごとに配ると3周で上限の3倍をプロンプトへ
    積むことになり、ループの履歴にはファイル本文がそのまま残るため
    MAX_PROMPT_CHARS を超える。

    読み取りは read() をそのまま使う。道具の引数はモデルが書いた文字列なので
    root の外を拒む検査は必須であり、その判定を2つに分けないためである。

    モデルが1周目から道具を呼ばなければ、ファイルは0件で返る。呼び出し元は
    ツリーだけをプロンプトへ載せることになり、ループを入れる前と同じ結果になる。
    道具をうまく使えないモデルでも、現状より悪くはならない。

    ask_tools_call が投げる ChatError は投げ直す。LLM そのものが落ちたことは
    利用者に伝えるべき失敗である。
    """
    messages: list[dict] = [
        {"role": "user", "content": _opening_message(entries, question)}
    ]
    files: list[tuple[str, str]] = []
    skipped: list[str] = []
    seen: set[str] = set()
    remaining = budget

    for _ in range(MAX_ROUNDS):
        message = ask_tools_call(messages, [READ_FILES_TOOL])
        calls = message.get("tool_calls") or []
        if not calls:
            break
        messages.append(message)
        for call in calls:
            # 同じファイルを2度読むと、予算を二重に使ったうえで履歴も膨らむ。
            wanted = [path for path in _requested_paths(call) if path not in seen]
            seen.update(wanted)
            read_files, read_skipped = read(root, wanted, remaining)
            files.extend(read_files)
            skipped.extend(read_skipped)
            remaining -= sum(len(text) for _, text in read_files)
            messages.append(
                {
                    "role": "tool",
                    "tool_name": _TOOL_NAME,
                    "content": _tool_reply(read_files, read_skipped),
                }
            )
        if remaining <= 0:
            break

    return files, skipped


def write_output(root: Path, file_name: str, data: bytes) -> Path:
    """成果物を <root>/generated_docs/ に書き、置いた場所を返す。

    既存のファイルは上書きしない。ファイル名に日付が入っていても同じ日に2回
    作れば衝突し、上書きすると1回目の成果物が黙って消える。

    このフォルダは走査から外れている（EXCLUDED_DIR_NAMES）。外れていないと、
    2回目から自分が書いた文書を根拠にして次の文書を書く。
    """
    if file_name != Path(file_name).name or file_name in ("", ".", ".."):
        raise ValueError(f"成果物の名前はファイル名でなければなりません: {file_name}")
    directory = root / OUTPUT_DIR_NAME
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / file_name
    stem, suffix = destination.stem, destination.suffix
    serial = 2
    while destination.exists():
        destination = directory / f"{stem}_{serial}{suffix}"
        serial += 1
    destination.write_bytes(data)
    return destination
