"""1テーブル時代のベクトルストアを chunks / occurrences に変換する。

再埋め込みは要らない。本文もメタデータもベクトルも旧DBに揃っている。
変換して検証が通ってから初めて元のファイルを置き換える。
"""
import json
import shutil
import sqlite3
import sys
from datetime import date
from pathlib import Path

from ingest.vector_store import _SCHEMA, _text_id


def _is_old(connection) -> bool:
    columns = {row[1] for row in connection.execute("PRAGMA table_info(chunks)")}
    return "source" in columns


def migrate(path: str) -> int:
    source_path = Path(path)
    if not source_path.exists():
        print(f"見つかりません: {source_path}")
        return 1

    connection = sqlite3.connect(source_path)
    try:
        if not _is_old(connection):
            print("すでに新しいスキーマです。何もしません。")
            return 0
        rows = connection.execute(
            "SELECT id, text, metadata, embedding FROM chunks"
        ).fetchall()
        revision = connection.execute(
            "SELECT value FROM meta WHERE key = 'revision'"
        ).fetchone()[0]
    finally:
        connection.close()

    backup = source_path.with_name(
        f"{source_path.name}.bak-{date.today():%Y%m%d}"
    )
    shutil.copy2(source_path, backup)
    print(f"退避しました: {backup}")

    target_path = source_path.with_name(f"{source_path.name}.migrating")
    target_path.unlink(missing_ok=True)
    target = sqlite3.connect(target_path)
    try:
        target.execute("PRAGMA foreign_keys = ON")
        target.executescript(_SCHEMA)
        try:
            with target:
                for occurrence_id, text, metadata, embedding in rows:
                    chunk_id = _text_id(text)
                    target.execute(
                        "INSERT INTO chunks (id, text, embedding) VALUES (?, ?, ?)"
                        " ON CONFLICT(id) DO NOTHING",
                        (chunk_id, text, embedding),
                    )
                    target.execute(
                        "INSERT INTO occurrences (id, chunk_id, source, metadata)"
                        " VALUES (?, ?, ?, ?)",
                        (
                            occurrence_id,
                            chunk_id,
                            json.loads(metadata).get("source", ""),
                            metadata,
                        ),
                    )
                target.execute(
                    "UPDATE meta SET value = ? WHERE key = 'revision'", (revision,)
                )

            occurrences = target.execute("SELECT COUNT(*) FROM occurrences").fetchone()[0]
            chunks = target.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
            orphans = target.execute(
                "SELECT COUNT(*) FROM chunks"
                " WHERE id NOT IN (SELECT chunk_id FROM occurrences)"
            ).fetchone()[0]
        except Exception as e:
            target.close()
            target_path.unlink(missing_ok=True)
            print(f"変換に失敗しました: {e}")
            print(f"元のファイルは変更していません: {source_path}")
            print(f"退避は次の場所にあります: {backup}")
            return 1
    finally:
        target.close()

    expected_chunks = len({text for _, text, _, _ in rows})
    problems = []
    if occurrences != len(rows):
        problems.append(f"出現数が合いません: {occurrences} ≠ {len(rows)}")
    if chunks != expected_chunks:
        problems.append(f"本文の種類数が合いません: {chunks} ≠ {expected_chunks}")
    if orphans:
        problems.append(f"孤児の本文が {orphans} 件あります")
    if problems:
        # 書き戻さない。元のファイルは触っていないので、退避も含めて無傷である。
        for problem in problems:
            print(f"検証に失敗: {problem}")
        print(f"元のファイルは変更していません: {source_path}")
        print(f"退避は次の場所にあります: {backup}")
        target_path.unlink(missing_ok=True)
        return 1

    target_path.replace(source_path)
    print(f"変換しました: {len(rows)}出現 / {chunks}本文（{len(rows) - chunks}行削減）")
    return 0


def main() -> int:
    if len(sys.argv) != 2:
        print("使い方: python -m scripts.migrate_store <DBのパス>")
        return 1
    return migrate(sys.argv[1])


if __name__ == "__main__":
    raise SystemExit(main())
