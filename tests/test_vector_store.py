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
