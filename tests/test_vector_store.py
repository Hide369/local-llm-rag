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


@pytest.fixture
def filled_store():
    store = open_store(":memory:")
    store.add(
        ids=["a::1", "a::2", "b::1"],
        documents=["あ1", "あ2", "い1"],
        metadatas=[
            {"source": "a.md", "noise_wash_db": 26},
            {"source": "a.md", "noise_wash_db": 30},
            {"source": "b.md"},
        ],
        embeddings=[_vector(1.0), _vector(2.0), _vector(3.0)],
    )
    return store


def test_get_on_an_empty_store_returns_empty_lists(empty_store):
    """0件でも呼び出し側が zip できる形を返すこと。"""
    found = empty_store.get()
    assert found == {"ids": [], "documents": [], "metadatas": []}


def test_get_returns_everything_by_default(filled_store):
    found = filled_store.get()
    assert sorted(found["ids"]) == ["a::1", "a::2", "b::1"]
    assert len(found["documents"]) == 3
    assert len(found["metadatas"]) == 3


def test_get_by_ids_keeps_them_aligned(filled_store):
    found = filled_store.get(ids=["b::1", "a::1"])
    rows = dict(zip(found["ids"], found["documents"]))
    assert rows == {"b::1": "い1", "a::1": "あ1"}


def test_get_ignores_unknown_ids(filled_store):
    """BM25側のインデックスには取り込みで消えたIDが残ることがある。"""
    found = filled_store.get(ids=["a::1", "存在しない"])
    assert found["ids"] == ["a::1"]


def test_get_filters_by_where(filled_store):
    found = filled_store.get(where={"source": "a.md"})
    assert sorted(found["ids"]) == ["a::1", "a::2"]


def test_get_applies_limit(filled_store):
    assert len(filled_store.get(where={"source": "a.md"}, limit=1)["ids"]) == 1


def test_metadata_survives_the_round_trip(filled_store):
    """JSONに落として戻すため、数値が文字列になっていないことを確かめる。"""
    found = filled_store.get(ids=["a::1"])
    assert found["metadatas"][0]["noise_wash_db"] == 26
    assert isinstance(found["metadatas"][0]["noise_wash_db"], int)


def test_replace_swaps_only_that_source(filled_store):
    filled_store.replace(
        "a.md",
        ids=["a::9"],
        documents=["差し替え後"],
        metadatas=[{"source": "a.md"}],
        embeddings=[_vector(9.0)],
    )
    assert sorted(filled_store.get()["ids"]) == ["a::9", "b::1"]


def test_replace_drops_chunks_that_no_longer_exist(filled_store):
    """ページ数が減った資料を取り込み直したとき、末尾の古いページを残さない。"""
    filled_store.replace(
        "a.md", ids=[], documents=[], metadatas=[], embeddings=[]
    )
    assert filled_store.get()["ids"] == ["b::1"]


def test_failed_replace_leaves_the_previous_content(filled_store):
    """今回の障害の回帰テスト。

    書き込みの途中で失敗しても、中途半端な状態を残さない。ChromaDBでは
    「帳簿だけが進んで実体が無い」状態が作れてしまい、次にDBを開いた時点で
    初めて壊れていることが分かった。
    """
    with pytest.raises(VectorStoreError):
        filled_store.replace(
            "a.md",
            ids=["a::9"],
            documents=["差し替え後"],
            metadatas=[{"source": "a.md"}],
            embeddings=[[0.0, 0.0, 0.0, 0.0]],
        )
    assert sorted(filled_store.get()["ids"]) == ["a::1", "a::2", "b::1"]


def test_delete_removes_matching_rows(filled_store):
    filled_store.delete(where={"source": "a.md"})
    assert filled_store.get()["ids"] == ["b::1"]


def test_add_with_mismatched_lengths_raises(empty_store):
    """zipが黙って切り詰めると、帳簿だけ進んで実体が欠けた行ができる。"""
    with pytest.raises(VectorStoreError):
        empty_store.add(
            ids=["a::1", "a::2"],
            documents=["本文1"],
            metadatas=[{"source": "a.md"}, {"source": "a.md"}],
            embeddings=[_vector(1.0), _vector(2.0)],
        )


def test_failed_replace_with_mismatched_lengths_leaves_the_previous_content(
    filled_store,
):
    """今回の修正の回帰テスト。replaceの中でzipが切り詰めても書いてはならない。"""
    with pytest.raises(VectorStoreError):
        filled_store.replace(
            "a.md",
            ids=["a::9", "a::10"],
            documents=["差し替え後"],
            metadatas=[{"source": "a.md"}, {"source": "a.md"}],
            embeddings=[_vector(9.0), _vector(10.0)],
        )
    assert sorted(filled_store.get()["ids"]) == ["a::1", "a::2", "b::1"]


def test_identical_vector_has_distance_zero(filled_store):
    found = filled_store.search(_vector(1.0), limit=1)
    chunk_id, distance, text, metadata = found[0]
    assert chunk_id == "a::1"
    assert distance == pytest.approx(0.0, abs=1e-6)
    assert text == "あ1"
    assert metadata["source"] == "a.md"


def test_distance_is_one_minus_cosine_similarity():
    """ChromaDBの hnsw:space='cosine' と同一の定義であることを固定する。"""
    store = open_store(":memory:")
    store.add(
        ids=["直交", "逆向き"],
        documents=["直交", "逆向き"],
        metadatas=[{"source": "x"}, {"source": "x"}],
        embeddings=[[0.0, 1.0], [-1.0, 0.0]],
    )
    by_id = {chunk_id: distance for chunk_id, distance, _, _ in store.search([1.0, 0.0], limit=2)}
    assert by_id["直交"] == pytest.approx(1.0, abs=1e-6)
    assert by_id["逆向き"] == pytest.approx(2.0, abs=1e-6)


def test_unnormalised_query_gives_the_same_distance(filled_store):
    """呼び出し側に正規化の責任を持たせない。長さ違いで距離が変わってはならない。"""
    short = filled_store.search([1.0, 0.0, 0.0, 0.0], limit=1)[0][1]
    long = filled_store.search([23.0, 0.0, 0.0, 0.0], limit=1)[0][1]
    assert short == pytest.approx(long, abs=1e-6)


def test_results_are_sorted_by_distance(filled_store):
    distances = [distance for _, distance, _, _ in filled_store.search(_vector(1.0), limit=3)]
    assert distances == sorted(distances)


def test_search_on_empty_store_returns_nothing(empty_store):
    assert empty_store.search([1.0, 0.0, 0.0, 0.0], limit=4) == []


def test_limit_larger_than_the_corpus_is_safe(filled_store):
    """CANDIDATE_COUNT=30 に対して資料が3件しかない状況は普通に起きる。"""
    assert len(filled_store.search(_vector(1.0), limit=30)) == 3


def test_search_selects_the_nearest_when_limit_is_smaller_than_the_corpus():
    """filled_storeの3ベクトルは全て同じ向き（distance=0.0）で選抜経路を検証できない。

    ここでは向きの異なるベクトルを使い、argpartitionで上位limit件を選んでから
    整列する経路（間違ったk件を返しかねない部分）を実際に通す。
    """
    store = open_store(":memory:")
    store.add(
        ids=["近い", "直交", "遠い"],
        documents=["近い", "直交", "遠い"],
        metadatas=[{"source": "x"}, {"source": "x"}, {"source": "x"}],
        embeddings=[[1.0, 0.0], [0.0, 1.0], [-1.0, 0.0]],
    )
    found = store.search([1.0, 0.0], limit=2)
    assert [chunk_id for chunk_id, _, _, _ in found] == ["近い", "直交"]
    assert [distance for _, distance, _, _ in found] == pytest.approx(
        [0.0, 1.0], abs=1e-6
    )


def test_tied_distances_are_broken_by_chunk_id():
    """同点の並びをID任せにすると、ingest/retrieval.pyのrrf_scoreに伝播して
    根拠の順序が実行のたびに変わりうる（同ファイルが同じ理由で全順序化している）。
    """
    store = open_store(":memory:")
    store.add(
        ids=["b", "a"],
        documents=["b", "a"],
        metadatas=[{"source": "x"}, {"source": "x"}],
        embeddings=[[1.0, 0.0], [1.0, 0.0]],
    )
    for _ in range(5):
        found = store.search([1.0, 0.0], limit=2)
        assert [chunk_id for chunk_id, _, _, _ in found] == ["a", "b"]
