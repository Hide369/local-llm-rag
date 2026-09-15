import json

from ingest import query_translation
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


def test_topic_query_asks_what_to_look_up_not_what_to_write():
    """依頼文をそのまま訳すと、リランカーが「答えていない文章」として切り捨てる。

    実測 2026-09-15（docs_store.sqlite3 54,054チャンク、bge-reranker-v2-m3）:
      "How do goroutines work in Go?"      最高 2.87  → 床1.0を通る
      "Write an ingestion routine in Go"   最高 -3.82 → 全件却下
    話題は合っていた（日本語の依頼での1位は go-spec.md）。落としていたのは形である。
    """
    seen = {}

    def ask(prompt):
        seen["prompt"] = prompt
        return '{"query": "Go io package reading files"}'

    result = query_translation.topic_query("Go で取り込み処理を書いて", ask)

    assert result == "Go io package reading files"
    assert "Go で取り込み処理を書いて" in seen["prompt"]
    # 「書く対象」ではなく「調べる話題」を求めていることが文面に出ていること。
    assert "調べ" in seen["prompt"]


def test_topic_query_falls_back_to_the_request_when_the_reply_is_broken():
    """止めない。検索の的が外れるだけで、生成そのものは続ける
    （translate_query と同じ考え方）。"""
    request = "Go で取り込み処理を書いて"

    assert query_translation.topic_query(request, lambda p: "すみません") == request
    assert query_translation.topic_query(request, lambda p: '["a"]') == request
    assert query_translation.topic_query(request, lambda p: '{"query": 1}') == request
    assert query_translation.topic_query(request, lambda p: '{"query": "  "}') == request


def test_topic_query_falls_back_when_the_model_writes_an_essay():
    """短いクエリの指示を無視して説明文を書いた返答は使わない。"""
    request = "Go で取り込み処理を書いて"
    long_reply = '{"query": "' + "a" * 300 + '"}'

    assert query_translation.topic_query(request, lambda p: long_reply) == request


def test_topic_query_falls_back_when_the_model_itself_fails():
    """LLM が落ちても検索まで巻き添えにしない。"""
    def ask(prompt):
        raise RuntimeError("落ちた")

    assert query_translation.topic_query("依頼", ask) == "依頼"


def test_topic_query_asks_for_a_short_query():
    """語を並べるほどクロスエンコーダのスコアが落ちる。

    クロスエンコーダは「この本文はこのクエリ全体に答えているか」を測る。語を
    足すと、どの本文も一部しか答えていないことになり、全体が下がる。

    実測 2026-09-15（gpt-oss:20b、docs_store.sqlite3 54,054チャンク、
    bge-reranker-v2-m3、DOCS_RERANK_FLOOR = 1.0）。同じ意図・同じコーパスで
    語を足しただけ:
      "Go goroutine concurrency"                               4件 最高  3.08
      "Go goroutine concurrency sync.WaitGroup channel select" 0件 最高 -0.49
    """
    seen = {}

    def ask(prompt):
        seen["prompt"] = prompt
        return '{"query": "Go goroutine concurrency"}'

    query_translation.topic_query("Goでgoroutineを使った並行処理を書いて", ask)

    assert "2語" in seen["prompt"]


def test_the_topic_prompt_does_not_demand_api_names():
    """translate_query から流用してはいけない指示である。

    あちらは質問文を訳すので、API名を1つ引き当てれば的が絞れる（実測で
    st.cache_data を含むクエリが 7.02、丁寧な英文が 5.73）。こちらは依頼から
    話題を作るため、同じ指示が「API名を並べる」に化ける。実測 2026-09-15、
    gpt-oss:20b が作ったクエリ:
      "Go goroutine concurrency example sync.WaitGroup channel"  0件
      "Go file reading os.Open ioutil.ReadFile"                  0件
    どちらも話題は当たっていて、落としていたのは語数である。
    """
    assert "API名" not in query_translation._topic_prompt("依頼")
