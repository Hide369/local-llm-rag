"""検索の実測スクリプトの異常系。

open_store は存在しないパスに対して例外を出さず、空のDBを新規作成する。
ベクトルは復元できず全量再取り込みが要るため、移行直後にまだ取り込んでいない
状態でこのスクリプトを回すのは事故ではなく通常の順序であり、そこで書式化の
TypeError を出すと原因から遠い場所で落ちることになる。
"""
import sys

import pytest

from ingest.embedder import EMBED_DIM
from ingest.store import open_store
from scripts import check_retrieval


def test_an_empty_store_stops_main_with_a_reason(monkeypatch, tmp_path, capsys):
    """件数0なら測るものが無い。何をすればよいかを告げて終了する。"""
    monkeypatch.setattr(check_retrieval, "DB_PATH", tmp_path / "empty.sqlite3")
    monkeypatch.setattr(check_retrieval.embedder, "check_ollama", lambda: None)
    monkeypatch.setattr(sys, "argv", ["check_retrieval"])

    assert check_retrieval.main() == 1
    assert "scripts.ingest_source" in capsys.readouterr().out


def test_a_vector_search_that_returns_nothing_names_the_question(monkeypatch):
    """None を返すと呼び出し側の :.3f で TypeError になり、原因から3フレーム遠ざかる。"""
    monkeypatch.setattr(
        check_retrieval.embedder,
        "embed_query",
        lambda question, session=None: [1.0] + [0.0] * (EMBED_DIM - 1),
    )
    with pytest.raises(RuntimeError, match="運転音"):
        check_retrieval._vector_best(open_store(":memory:"), "運転音は", session=None)
