import pytest

from ingest.vector_store import WhereError, matches


def test_plain_value_is_equality():
    assert matches({"source": "a.md"}, {"source": "a.md"})
    assert not matches({"source": "b.md"}, {"source": "a.md"})


def test_no_condition_matches_everything():
    assert matches({"source": "a.md"}, None)
    assert matches({"source": "a.md"}, {})


def test_comparison_operators():
    metadata = {"noise_wash_db": 26}
    assert matches(metadata, {"noise_wash_db": {"$lte": 26}})
    assert matches(metadata, {"noise_wash_db": {"$gte": 26}})
    assert not matches(metadata, {"noise_wash_db": {"$lte": 25}})


def test_and_requires_every_clause():
    metadata = {"noise_wash_db": 26, "brand": "打田電器"}
    where = {"$and": [{"noise_wash_db": {"$lte": 30}}, {"brand": {"$eq": "打田電器"}}]}
    assert matches(metadata, where)
    assert not matches(metadata, {"$and": [{"noise_wash_db": {"$lte": 20}}]})


def test_missing_key_does_not_match():
    """属性を持たないPDF由来のチャンクが、条件に合致してはならない。"""
    assert not matches({"source": "a.pdf"}, {"noise_wash_db": {"$lte": 26}})


def test_incomparable_types_do_not_match():
    """文字列と数値の大小比較はTypeErrorになる。例外ではなく不一致として扱う。"""
    assert not matches({"price_tier": "エントリー"}, {"price_tier": {"$lte": 26}})


def test_unsupported_operator_raises():
    """黙って無視すると条件が消えたまま全件が返る。"""
    with pytest.raises(WhereError):
        matches({"k": 1}, {"k": {"$ne": 1}})


from ingest.vector_store import VectorStoreError, open_store


def _vector(seed: float, dim: int = 4) -> list[float]:
    return [seed] + [0.0] * (dim - 1)


@pytest.fixture
def empty_store():
    return open_store(":memory:")


def test_new_store_is_empty(empty_store):
    assert empty_store.count() == 0


def test_added_rows_are_counted(empty_store):
    empty_store.add(
        ids=["a::1", "a::2"],
        documents=["本文1", "本文2"],
        metadatas=[{"source": "a.md"}, {"source": "a.md"}],
        embeddings=[_vector(1.0), _vector(2.0)],
    )
    assert empty_store.count() == 2


def test_zero_vector_is_rejected(empty_store):
    """ノルム0は正規化でゼロ除算になる。埋め込みが空を返した事故を静かに通さない。"""
    with pytest.raises(VectorStoreError):
        empty_store.add(
            ids=["a::1"],
            documents=["本文"],
            metadatas=[{"source": "a.md"}],
            embeddings=[[0.0, 0.0, 0.0, 0.0]],
        )


def test_rejected_add_leaves_the_store_empty(empty_store):
    """弾いた書き込みが中途半端に残ってはならない。"""
    with pytest.raises(VectorStoreError):
        empty_store.add(
            ids=["a::1", "a::2"],
            documents=["良い", "悪い"],
            metadatas=[{"source": "a.md"}, {"source": "a.md"}],
            embeddings=[_vector(1.0), [0.0, 0.0, 0.0, 0.0]],
        )
    assert empty_store.count() == 0


def test_store_persists_across_connections(tmp_path):
    """別プロセス相当の開き直しで読めること。今回の障害はここで露見した。"""
    path = str(tmp_path / "store.sqlite3")
    open_store(path).add(
        ids=["a::1"],
        documents=["本文"],
        metadatas=[{"source": "a.md"}],
        embeddings=[_vector(1.0)],
    )
    assert open_store(path).count() == 1
