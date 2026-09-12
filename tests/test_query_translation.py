import json

from ingest.query_translation import translate_query


def _answer(payload):
    """LLMの代役。渡された文字列をそのまま返す。"""
    return lambda _prompt: payload


def _json(query):
    return json.dumps({"query": query})


def test_translates_a_japanese_question_into_an_english_query():
    result = translate_query(
        "Streamlitのキャッシュはどう書く？", _answer(_json("st.cache_data caching"))
    )
    assert result == "st.cache_data caching"


def test_an_english_question_passes_through():
    """既に英語なら、モデルがそのまま返すはずのものをそのまま使う。"""
    result = translate_query(
        "How do I cache data in Streamlit?",
        _answer(_json("How do I cache data in Streamlit?")),
    )
    assert result == "How do I cache data in Streamlit?"


def test_a_failing_ask_falls_back_to_the_original_query():
    def explode(_prompt):
        raise RuntimeError("Ollamaが落ちた")

    original = "Streamlitでモーダルダイアログを出す書き方"
    assert translate_query(original, explode) == original


def test_broken_json_falls_back_to_the_original_query():
    original = "Streamlitのキャッシュはどう書く？"
    assert translate_query(original, _answer("これはJSONではありません")) == original


def test_an_empty_translation_falls_back_to_the_original_query():
    original = "Streamlitのキャッシュはどう書く？"
    assert translate_query(original, _answer(_json(""))) == original


def test_a_whitespace_only_translation_falls_back_to_the_original_query():
    original = "Streamlitのキャッシュはどう書く？"
    assert translate_query(original, _answer(_json("   "))) == original


def test_a_translation_wrapped_in_prose_is_rejected_as_too_long():
    """プロンプトで短いクエリを頼んでも、モデルが説明文を書いてしまう場合がある。

    JSONの構造自体は壊れていなくても、queryの値が丁寧な説明文になっていれば
    検索クエリとして使い物にならない。長さで弾き、原文へフォールバックする。
    """
    original = "Streamlitのキャッシュはどう書く？"
    prose = (
        "Sure, here is the translated search query you requested: "
        "how to cache data in Streamlit using the st.cache_data decorator "
        "and other related caching utilities provided by the framework, "
        "along with a short explanation of when each one should be used "
        "in a typical Streamlit application so that the answer is complete"
    )
    assert len(prose) > 200  # 前提: この長さで初めて _MAX_QUERY_LENGTH を超える
    assert translate_query(original, _answer(_json(prose))) == original


def test_a_translation_wrapped_in_quotes_has_the_quotes_stripped():
    result = translate_query(
        "st.cache_dataの使い方は", _answer(_json('"st.cache_data usage"'))
    )
    assert result == "st.cache_data usage"


def test_a_non_dict_json_falls_back_to_the_original_query():
    original = "Streamlitのキャッシュはどう書く？"
    assert translate_query(original, _answer(json.dumps(["st.cache_data"]))) == original


def test_a_non_string_query_field_falls_back_to_the_original_query():
    original = "Streamlitのキャッシュはどう書く？"
    assert translate_query(original, _answer(json.dumps({"query": 123}))) == original


def test_an_empty_original_query_is_returned_without_calling_ask():
    """空文字を渡す状況は想定していないが、ask を無駄に呼ばないことだけ保証する。"""
    calls = []

    def ask(prompt):
        calls.append(prompt)
        return _json("something")

    assert translate_query("", ask) == ""
    assert calls == []
