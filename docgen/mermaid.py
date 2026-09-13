"""Mermaid のテキストを PNG にする。

外部サービスへは投げない。mermaid.ink や kroki.io に送れば依存は増えないが、
社内設計書の図をそのまま社外へ出すことになる（AGENTS.md）。mermaid-cli は
手元の Chromium で描くため、図の内容はマシンの外へ出ない。
"""
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

# 描画を待つ上限（秒）。実測 2026-09-13 は3.5秒だった。Chromium の起動が
# 刺さったまま返らないと、画面が「生成中」のまま戻らなくなる。
RENDER_TIMEOUT = 30

# 値の全体が1つの ```mermaid ブロックであることを求める。ブロックの前後に
# 説明文が付いた値を「図の部分だけ」描くと説明文が消える。図にしなければ
# Mermaid の記法がそのまま見えるだけで、利用者は何が起きたか分かる。
_FENCE = re.compile(r"\A\s*```mermaid[ \t]*\r?\n(?P<source>.*?)\r?\n?```\s*\Z", re.DOTALL)


class MermaidError(Exception):
    """図にできなかった。呼び出し元は Mermaid のテキストをそのまま入れる。"""


def is_diagram(value: str) -> bool:
    return _FENCE.match(value) is not None


def diagram_source(value: str) -> str:
    match = _FENCE.match(value)
    if match is None:
        raise MermaidError("Mermaid のコードブロックではありません")
    return match.group("source")


def render(source: str) -> bytes:
    # Windows での実体は mmdc.cmd である。subprocess へ "mmdc" をそのまま渡すと
    # PATHEXT を見ないため FileNotFoundError になる。shutil.which は見る。
    executable = shutil.which("mmdc")
    if executable is None:
        raise MermaidError("mmdc が見つかりません")
    # mmdc は標準入出力を扱わず、入力も出力もファイルで指定する作りである。
    with tempfile.TemporaryDirectory() as directory:
        input_path = Path(directory) / "diagram.mmd"
        output_path = Path(directory) / "diagram.png"
        input_path.write_text(source, encoding="utf-8")
        try:
            completed = subprocess.run(
                [executable, "-i", str(input_path), "-o", str(output_path)],
                capture_output=True,
                text=True,
                timeout=RENDER_TIMEOUT,
            )
        except (subprocess.TimeoutExpired, OSError) as error:
            # OSError は実行権限が無い等、起動そのものに失敗する場合に出る。
            # ここも図の失敗として扱わないと、設計書10節の「失敗しても生成は
            # 止めない」が守れず、この1枝だけ生の例外が上へ抜けてしまう。
            if isinstance(error, subprocess.TimeoutExpired):
                raise MermaidError(f"{RENDER_TIMEOUT}秒で描き終わりませんでした") from error
            raise MermaidError(f"mmdc を起動できませんでした: {error}") from error
        if completed.returncode != 0:
            raise MermaidError(completed.stderr.strip() or "mmdc が失敗しました")
        if not output_path.is_file():
            raise MermaidError("mmdc が画像を書きませんでした")
        return output_path.read_bytes()


def rendered(
    values: dict[str, str], on_diagram_error=None
) -> tuple[dict[str, str], dict[str, bytes]]:
    """値を「文字列として入れるもの」と「画像として入れるもの」に分ける。

    描けなかった値は文字列の側へ戻す。印が消えるのでも空になるのでもなく、
    Mermaid のテキストがそのまま成果物に残る。そのうえで on_diagram_error に
    知らせ、画面が利用者へ伝えられるようにする。
    """
    texts: dict[str, str] = {}
    images: dict[str, bytes] = {}
    for name, value in values.items():
        if not is_diagram(value):
            texts[name] = value
            continue
        try:
            images[name] = render(diagram_source(value))
        except MermaidError as error:
            texts[name] = value
            if on_diagram_error is not None:
                on_diagram_error(name, str(error))
    return texts, images
