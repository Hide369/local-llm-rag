import pytest

from ingest.catalog import Product, exceeding, format_table, relaxations, select
from ingest.conditions import Ranking
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
    product = Product(
        source="家電製品/UD-1100iS_spec_step3.md",
        attributes={"model_id": "UD-1100iS", "noise_wash_db": 26},
    )
    table = format_table({"noise_wash_db": {"$lte": 26}}, [product], [])
    assert "noise_wash_db 26以下" in table
    assert "noise_wash_db=26" in table
    assert "1件" in table


def test_format_table_identifies_products_by_model_id_only():
    """モデルは行を丸写しする。ファイル名を渡すと回答にもファイル名が出る。

    実測では「UD-1100S_spec_step3.md と UD-1100iS_spec_step3.md です」と、
    利用者に意味のない取り込み元のファイル名で製品を指した。列を末尾へ動かしても
    行ごと写されるため、表に載せないことで断つ。
    """
    product = Product(
        source="家電製品/UD-1100iS_spec_step3.md",
        attributes={"model_id": "UD-1100iS", "noise_wash_db": 26},
    )
    table = format_table({"noise_wash_db": {"$lte": 26}}, [product], [])
    assert "UD-1100iS | noise_wash_db=26" in table
    assert ".md" not in table


def test_format_table_does_not_repeat_the_model_id_as_an_attribute():
    """行頭に出したものを model_id=… として繰り返す必要はない。"""
    product = Product(
        source="家電製品/UD-1100iS_spec_step3.md",
        attributes={"model_id": "UD-1100iS", "noise_wash_db": 26},
    )
    assert "model_id=" not in format_table({"noise_wash_db": {"$lte": 26}}, [product], [])


def test_format_table_falls_back_to_the_file_name_without_a_model_id():
    """フロントマターに model_id が無い資料でも行は成立させる。"""
    product = Product(source="家電製品/UD-1100iS.md", attributes={"noise_wash_db": 26})
    table = format_table({"noise_wash_db": {"$lte": 26}}, [product], [])
    assert "家電製品/UD-1100iS.md | noise_wash_db=26" in table


def test_format_table_labels_the_relaxed_group():
    product = Product(source="家電製品/UD-1100i.md", attributes={"noise_wash_db": 26})
    table = format_table(QUIET_AND_SLIM, [], [("installation_depth_min_mm", [product])])
    assert "installation_depth_min_mm" in table
    assert "家電製品/UD-1100i.md" in table


def test_relaxed_group_states_which_condition_fails():
    """見出しが「条件を外すと合致」だけだと、モデルはこの群を読み違える。

    実測では、26dBだが設置できない機種を尋ねられて「該当する製品はありません」と
    答えた。表には該当機種が並んでいたので、欠けていたのは数値ではなく説明である。
    """
    product = Product(source="家電製品/UD-1100i.md", attributes={"noise_wash_db": 26})
    table = format_table(QUIET_AND_SLIM, [], [("installation_depth_min_mm", [product])])
    assert "installation_depth_min_mm 510以下" in table
    assert "だけを満たさない" in table


def _capacity(model, capacity, depth=510):
    return Product(
        source=f"家電製品/{model}_spec_step3.md",
        attributes={
            "model_id": model,
            "drying_capacity_kg": 6.0,
            "installation_depth_min_mm": depth,
            "washing_capacity_kg": capacity,
        },
    )


RANKING = Ranking(key="washing_capacity_kg", descending=True)
DEPTH = {"installation_depth_min_mm": {"$lte": 510}}


def test_format_table_orders_rows_by_the_ranking():
    """最大値を探させない。並べ替えて先頭に置く。

    実測: 12行の表で「最大の洗濯容量と該当型番」の正答は8回中2回。降順に並べ、
    その属性を先頭カラムへ出すと4回中4回になった。モデルは行の先頭を掴む。
    """
    products = [_capacity("UD-1000S", 10.0), _capacity("UD-1100S", 11.0)]
    rows = format_table(DEPTH, products, [], ranking=RANKING).splitlines()
    assert rows[3].startswith("UD-1100S | washing_capacity_kg=11.0")
    assert rows[4].startswith("UD-1000S | washing_capacity_kg=10.0")


def test_format_table_orders_ascending_for_a_smallest_question():
    products = [_capacity("UD-1100S", 11.0), _capacity("UD-1000S", 10.0)]
    ranking = Ranking(key="washing_capacity_kg", descending=False)
    rows = format_table(DEPTH, products, [], ranking=ranking).splitlines()
    assert rows[3].startswith("UD-1000S | ")


def test_format_table_keeps_the_source_order_without_a_ranking():
    """並べ替えを尋ねられていない質問の表は、これまでどおり型番順で出す。"""
    products = [_capacity("UD-1000S", 10.0), _capacity("UD-1100S", 11.0)]
    rows = format_table(DEPTH, products, []).splitlines()
    assert rows[3].startswith("UD-1000S | ")


def test_format_table_shows_the_ranked_attribute_first():
    """実測では、行の最初の数値を容量として拾い drying_capacity_kg=6.0 と答えた。"""
    row = format_table(DEPTH, [_capacity("UD-1100S", 11.0)], [], ranking=RANKING).splitlines()[3]
    assert row.index("washing_capacity_kg") < row.index("drying_capacity_kg")


def test_format_table_does_not_duplicate_the_ranked_attribute():
    row = format_table(DEPTH, [_capacity("UD-1100S", 11.0)], [], ranking=RANKING).splitlines()[3]
    assert row.count("washing_capacity_kg=") == 1


def _add_capacity_product(collection, model, capacity, depth):
    source = f"家電製品/{model}.md"
    collection.add(
        ids=[f"{source}::0"],
        documents=[f"{model}の本文"],
        metadatas=[
            {
                "source": source,
                "model_id": model,
                "washing_capacity_kg": capacity,
                "installation_depth_min_mm": depth,
            }
        ],
        embeddings=[[1.0] + [0.0] * (EMBED_DIM - 1)],
    )


def _capacity_catalogue(collection):
    _add_capacity_product(collection, "UD-1000S", 10.0, 510)
    _add_capacity_product(collection, "UD-1100S", 11.0, 510)
    _add_capacity_product(collection, "UD-1400X", 14.0, 545)  # 設置できないが大容量
    _add_capacity_product(collection, "UD-0500M", 5.0, 545)  # 設置できず容量も小さい
    collection.add(  # 属性を持たないPDF由来のチャンク
        ids=["就業規則.pdf::0"],
        documents=["本文"],
        metadatas=[{"source": "モデル就業規則.pdf"}],
        embeddings=[[1.0] + [0.0] * (EMBED_DIM - 1)],
    )


def test_exceeding_reports_what_the_condition_rules_out(collection):
    """「もっと大容量が欲しいが、なぜ選べないのか」に答えるために要る。

    条件が1つのとき relaxations は何も返さない。順位の上側だけに絞れば数件で済む。
    """
    _capacity_catalogue(collection)
    matched = select(collection, DEPTH)
    beyond = exceeding(collection, DEPTH, RANKING, matched)
    assert [p.attributes["model_id"] for p in beyond] == ["UD-1400X"]


def test_exceeding_is_empty_without_a_ranking(collection):
    _capacity_catalogue(collection)
    matched = select(collection, DEPTH)
    assert exceeding(collection, DEPTH, None, matched) == []


def test_exceeding_is_empty_when_nothing_matched(collection):
    """比較の基準が無い。全件を「上回る」として並べてはいけない。"""
    _capacity_catalogue(collection)
    assert exceeding(collection, DEPTH, RANKING, []) == []


def test_format_table_says_the_exceeding_group_cannot_be_chosen(collection):
    """見出しが弱いと、モデルはこの群を条件に合う機種として混ぜて答える。"""
    _capacity_catalogue(collection)
    matched = select(collection, DEPTH)
    table = format_table(
        DEPTH, matched, [], RANKING, exceeding(collection, DEPTH, RANKING, matched)
    )
    assert "条件を満たさないので選べない" in table
    assert "UD-1400X | washing_capacity_kg=14.0" in table
    assert "installation_depth_min_mm=545" in table


def test_format_table_says_none_when_nothing_matches():
    """空の表を渡すと、モデルは根拠が無いことに気づかず作り話を始める。"""
    assert "該当なし" in format_table({"noise_wash_db": {"$lte": 20}}, [], [])
