"""ソースコードと設定ファイルの取り込み。

これらはプレーンテキストであり、書き手が引いた見出しやページの境界を持たない。
独自のパーサーは作らず txt と同じ扱いにする（文書全体で1ユニット、分割は
chunk_units に一任）。このテストが守るのは「登録漏れで黙って無視されない」
ことと、素通しであることの2点である。
"""
import pytest

from ingest.models import DOCUMENT
from ingest.parsers import SUPPORTED_SUFFIXES, parse

# go.mod / go.sum のように、拡張子だけでは形式が決まらないものも含む。
CODE_SUFFIXES = (
    ".go",
    ".cs",
    ".sh",
    ".py",
    ".ps1",
    ".json",
    ".bat",
    ".yaml",
    ".yml",
    ".mod",
    ".sum",
)


@pytest.mark.parametrize("suffix", CODE_SUFFIXES)
def test_each_code_suffix_is_registered(suffix):
    """登録を忘れると、source/ に置いても取り込み対象から静かに外れる。"""
    assert suffix in SUPPORTED_SUFFIXES


@pytest.mark.parametrize(
    ("name", "body"),
    [
        ("main.go", 'func main() {\n\tfmt.Println("起動")\n}\n'),
        ("Program.cs", "public class Program { }\n"),
        ("deploy.sh", '#!/bin/sh\nset -eu\necho "配備"\n'),
        ("app.py", 'def main():\n    print("起動")\n'),
        ("run.ps1", 'Write-Host "配備を開始します"\n'),
        ("config.json", '{\n  "timeout": 30\n}\n'),
        ("compose.yaml", "services:\n  app:\n    image: local\n"),
        ("compose.yml", "services:\n  db:\n    image: sqlite\n"),
        ("go.mod", "module example.com/tool\n\ngo 1.24\n"),
        ("go.sum", "example.com/lib v1.2.3 h1:abcdef=\n"),
    ],
)
def test_the_whole_file_is_one_unit_passed_through_verbatim(tmp_path, name, body):
    """コードは1文字も落とさない。整形も解釈もしない。"""
    path = tmp_path / name
    path.write_text(body, encoding="utf-8")

    units = parse(path)

    assert len(units) == 1
    assert units[0].location_type == DOCUMENT
    assert units[0].text == body.strip()


def test_a_cp932_batch_file_is_read_without_mojibake(tmp_path):
    """日本語Windowsのバッチファイルは現にCP932で書かれている。

    utf-8を決め打つとUnicodeDecodeErrorになり、その資料は丸ごと落ちる。
    """
    path = tmp_path / "起動.bat"
    path.write_bytes("@echo off\nrem 取り込みを開始する\n".encode("cp932"))

    assert "取り込みを開始する" in parse(path)[0].text
