"""雛形の保管。

原本をファイルとして残す。既存のアップロード（scripts/ingest_source.py の
ingest_uploads）は「原本を残さず、DBのチャンクだけ残す」という設計判断を
採っているが、雛形はこれと異なる。埋めるために原本そのものが要る。

名前はファイル名そのものである（`議事録.docx`）。別名を付ける仕組みは作らない。
同名を登録したら上書きする。利用者にとっては差し替えであり、版管理は作らない。
"""
import shutil
from pathlib import Path

import docgen

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"


def _checked(name: str) -> str:
    """名前がファイル名であることを確かめる。

    パス区切りを含む名前を受け取ると templates/ の外へ書いたり消したりできる。
    雛形の名前は画面の一覧から来るが、利用者が触れる値を信じる形にはしない
    （ingest/parsers/md_parser.py の _resolve が同じ理由で .. を拒んでいる）。
    """
    if name != Path(name).name or name in ("", ".", ".."):
        raise ValueError(f"フォーマットファイルの名前はファイル名でなければなりません: {name}")
    return name


def register(source: Path, directory: Path | None = None) -> Path:
    """雛形を保存し、置いた場所を返す。"""
    if source.suffix.lower() not in docgen.SUPPORTED_SUFFIXES:
        raise docgen.UnsupportedTemplateError(
            f"フォーマットファイルとして使えない形式です: {source.name}"
        )
    directory = directory or TEMPLATE_DIR
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / _checked(source.name)
    shutil.copyfile(source, destination)
    return destination


def templates(directory: Path | None = None) -> list[Path]:
    """登録済みの雛形をファイル名の昇順で返す。

    並びを決めるのは、画面のプルダウンの順序が実行のたびに変わらないように
    するためである。
    """
    directory = directory or TEMPLATE_DIR
    if not directory.is_dir():
        # まだ1つも登録していない状態は通常であり、例外ではない。
        return []
    return sorted(
        (path for path in directory.iterdir()
         if path.is_file() and path.suffix.lower() in docgen.SUPPORTED_SUFFIXES),
        key=lambda path: path.name,
    )


def remove(name: str, directory: Path | None = None) -> None:
    """雛形を消す。無ければ何もしない。

    2つの画面から同時に消したときに例外を出さない。結果は同じである。
    """
    directory = directory or TEMPLATE_DIR
    (directory / _checked(name)).unlink(missing_ok=True)
