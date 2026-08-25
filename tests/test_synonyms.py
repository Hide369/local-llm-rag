from ingest.synonyms import expand_query


def test_appends_the_kanji_reading_for_36_agreement():
    assert expand_query("36協定について教えてください") == (
        "36協定について教えてください 三六協定について"
    )


def test_does_not_duplicate_when_the_kanji_reading_is_already_present():
    assert expand_query("三六協定とは") == "三六協定とは"


def test_leaves_unrelated_queries_untouched():
    assert expand_query("有給休暇は何日ですか") == "有給休暇は何日ですか"


def test_expands_only_once_when_the_term_appears_twice():
    assert expand_query("36協定と36協定届の違いは") == (
        "36協定と36協定届の違いは 三六協定について"
    )
