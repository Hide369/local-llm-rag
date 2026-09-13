"""Markdown の雛形。

書式を保つ必要がないため、本文全体に対する文字列置換で済む。
"""
from pathlib import Path

from docgen import marks


def placeholders(path: Path) -> list[str]:
    return marks.names(path.read_text(encoding="utf-8"))


def fill(path: Path, values: dict[str, str]) -> bytes:
    text = marks.replace(path.read_text(encoding="utf-8"), values)
    return text.encode("utf-8")
