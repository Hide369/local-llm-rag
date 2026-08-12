"""source/ 配下の資料をベクトルDBへ取り込むCLI。

初回はOCR23ページと埋め込み279件でおよそ13分かかる。Streamlitのボタンで
13分ブロックするのは現実的でないため、初回はこのCLIから実行する。

1ファイル処理するごとにDBへ書き込む。全ファイル分をまとめて書き込むと、
12分経過時点の失敗ですべてを失う。ファイル単位で保存しておけば、再実行時に
ハッシュ判定で成功済みのファイルがスキップされ、失敗分だけをやり直せる。
"""
import argparse
import hashlib
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import chromadb

from ingest import embedder, store
from ingest.chunker import chunk_units
from ingest.parsers import SUPPORTED_SUFFIXES, parse

DEFAULT_SOURCE_DIR = Path(__file__).resolve().parent.parent / "source"
DB_DIR = Path(__file__).resolve().parent.parent / "chroma_db"


@dataclass
class IngestReport:
    indexed: dict[str, int] = field(default_factory=dict)
    skipped: list[str] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)
    removed: list[str] = field(default_factory=list)


def file_hash(path: Path) -> str:
    """内容が1バイトでも変われば変わる識別子。先頭16桁で十分に衝突しない。"""
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return digest[:16]


def _target_files(source_dir: Path) -> list[Path]:
    """サブフォルダも含めて対象ファイルを集める。

    資料を分類して置けるようにするため再帰する。対象外の拡張子はここで落とすので、
    source/ に雑多なファイルが増えてもパーサーには渡らない。
    """
    return sorted(
        path
        for path in source_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    )


def _source_key(path: Path, source_dir: Path) -> str:
    """source/ からの相対パスを資料の識別子にする。

    区切りはスラッシュに統一する。WindowsのバックスラッシュがそのままチャンクIDと
    メタデータに入ると、環境をまたいだときに一致しなくなるため。
    直下のファイルは相対パスがファイル名と一致するので、既存のチャンクの識別子は
    変わらず、再取り込みは発生しない。
    """
    return path.relative_to(source_dir).as_posix()


def ingest_directory(
    source_dir: Path,
    collection,
    session=None,
    on_progress=None,
    force: bool = False,
) -> IngestReport:
    """source_dir を走査し、変更のあった資料だけを取り込む。"""
    report = IngestReport()
    notify = on_progress or (lambda _message: None)
    own_session = session is None
    session = session or embedder.new_session()
    today = date.today().isoformat()

    try:
        files = _target_files(source_dir)
        for path in files:
            source = _source_key(path, source_dir)
            current_hash = file_hash(path)

            if not force and store.stored_file_hash(collection, source) == current_hash:
                report.skipped.append(source)
                notify(f"スキップ（変更なし）: {source}")
                continue

            notify(f"処理中: {source}")
            try:
                units = parse(path)
                chunks = chunk_units(units, source, current_hash, today)
                vectors = embedder.embed_texts(
                    [chunk.text for chunk in chunks], session=session
                )
                store.replace_source(collection, source, chunks, vectors)
            except Exception as error:  # 1ファイルの失敗で全体を止めない
                report.failed[source] = str(error)
                notify(f"失敗: {source} — {error}")
                continue

            report.indexed[source] = len(chunks)
            notify(f"完了: {source}（{len(chunks)}チャンク）")

        # source/ を唯一の入力とするため、消えた資料はDBからも消す。
        report.removed = store.delete_orphans(
            collection, {_source_key(path, source_dir) for path in files}
        )
        for source in report.removed:
            notify(f"削除（source/にありません）: {source}")
    finally:
        if own_session:
            session.close()

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="source/ の資料をベクトルDBへ取り込む")
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument(
        "--force", action="store_true", help="変更がなくても再取り込みする"
    )
    args = parser.parse_args()

    if not args.source_dir.is_dir():
        print(f"ディレクトリがありません: {args.source_dir}")
        return 1

    try:
        # 279チャンクの処理を始めてから落ちないよう、先に疎通を確認する。
        embedder.check_ollama()
    except embedder.EmbeddingError as error:
        print(error)
        return 1

    collection = store.open_collection(chromadb.PersistentClient(path=str(DB_DIR)))
    report = ingest_directory(
        args.source_dir, collection, on_progress=print, force=args.force
    )

    print("\n--- 結果 ---")
    print(f"取り込み: {sum(report.indexed.values())}チャンク / {len(report.indexed)}ファイル")
    print(f"スキップ: {len(report.skipped)}ファイル")
    print(f"削除: {len(report.removed)}ファイル")
    if report.failed:
        print(f"失敗: {len(report.failed)}ファイル")
        for source, message in report.failed.items():
            print(f"  {source}: {message}")
    print(f"DB内の総チャンク数: {collection.count()}")
    return 1 if report.failed else 0


if __name__ == "__main__":
    sys.exit(main())
