import pytest

from ingest.catalog import Product, format_table, relaxations, select
from ingest.embedder import EMBED_DIM
from ingest.store import open_collection
from tests.conftest import ephemeral_client

QUIET_AND_SLIM = {"noise_wash_db": {"$lte": 26}, "installation_depth_min_mm": {"$lte": 510}}


@pytest.fixture
def collection():
    client = ephemeral_client()
    yield open_collection(client)
    client.clear_system_cache()


def _add_product(collection, model, noise, depth, sections=1):
    """1製品を sections 個のチャンクとして入れる。属性は全チャンクに同じ値が乗る。"""
    source = f"家電製品/{model}.md"
    for index in range(sections):
        collection.add(
            ids=[f"{source}::section{index}::0"],
            documents=[f"{model}の本文"],
            metadatas=[
                {
                    "source": source,
                    "heading": f"節{index}",
                    "noise_wash_db": noise,
                    "installation_depth_min_mm": depth,
                    "model_id": model,
                }
            ],
            embeddings=[[1.0] + [0.0] * (EMBED_DIM - 1)],
        )
    return source


def _catalogue(collection):
    _add_product(collection, "UD-1100iS", 26, 510, sections=3)
    _add_product(collection, "UD-1100i", 26, 540)
    _add_product(collection, "UD-1100iE", 26, 540)
    _add_product(collection, "UD-1000S", 28, 510)


def test_select_returns_every_match(collection):
    _catalogue(collection)
    assert [p.source for p in select(collection, QUIET_AND_SLIM)] == [
        "家電製品/UD-1100iS.md"
    ]


def test_select_folds_the_chunks_of_one_source_into_one_product(collection):
    """3チャンクある製品が3行になると、件数の質問に誤って答えることになる。"""
    _catalogue(collection)
    assert len(select(collection, {"noise_wash_db": {"$lte": 26}})) == 3


def test_select_drops_reserved_keys_from_attributes(collection):
    _catalogue(collection)
    attributes = select(collection, QUIET_AND_SLIM)[0].attributes
    assert "source" not in attributes
    assert "heading" not in attributes
    assert attributes["model_id"] == "UD-1100iS"


def test_select_returns_nothing_without_conditions(collection):
    _catalogue(collection)
    assert select(collection, {}) == []


def test_select_returns_nothing_when_no_product_matches(collection):
    _catalogue(collection)
    assert select(collection, {"noise_wash_db": {"$lte": 20}}) == []


def test_relaxations_report_products_that_miss_exactly_one_condition(collection):
    """「同じ26dBでも設置できない機種はどれか」に答えるために要る。

    外した条件ごとに群が分かれる。UD-1000S は設置できるが静かではなく、
    UD-1100i / UD-1100iE は静かだが設置できない。どちらも「1つだけ外れている」
    ため、外した条件を明記した別々の群として出す必要がある。
    """
    _catalogue(collection)
    relaxed = relaxations(collection, QUIET_AND_SLIM)
    assert dict(
        (key, [p.source for p in products]) for key, products in relaxed
    ) == {
        "noise_wash_db": ["家電製品/UD-1000S.md"],
        "installation_depth_min_mm": ["家電製品/UD-1100i.md", "家電製品/UD-1100iE.md"],
    }


def test_relaxations_exclude_products_that_already_matched(collection):
    _catalogue(collection)
    relaxed = relaxations(collection, QUIET_AND_SLIM)
    assert all(
        p.source != "家電製品/UD-1100iS.md" for _, products in relaxed for p in products
    )


def test_relaxations_are_empty_for_a_single_condition(collection):
    """条件が1つしかなければ、外した先は「条件なし」で全件になり意味がない。"""
    _catalogue(collection)
    assert relaxations(collection, {"noise_wash_db": {"$lte": 26}}) == []


def test_format_table_shows_conditions_and_rows():
    product = Product(source="家電製品/UD-1100iS.md", attributes={"noise_wash_db": 26})
    table = format_table({"noise_wash_db": {"$lte": 26}}, [product], [])
    assert "noise_wash_db 26以下" in table
    assert "家電製品/UD-1100iS.md" in table
    assert "noise_wash_db=26" in table
    assert "1件" in table


def test_format_table_labels_the_relaxed_group():
    product = Product(source="家電製品/UD-1100i.md", attributes={"noise_wash_db": 26})
    table = format_table(QUIET_AND_SLIM, [], [("installation_depth_min_mm", [product])])
    assert "installation_depth_min_mm" in table
    assert "家電製品/UD-1100i.md" in table


def test_format_table_says_none_when_nothing_matches():
    """空の表を渡すと、モデルは根拠が無いことに気づかず作り話を始める。"""
    assert "該当なし" in format_table({"noise_wash_db": {"$lte": 20}}, [], [])
