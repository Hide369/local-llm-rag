import pytest

from ingest import conditions
from ingest.conditions import Ranking, available_keys, extract, extract_ranking
from ingest.embedder import EMBED_DIM
from ingest.store import open_collection
from tests.conftest import ephemeral_client

SCHEMA = {
    "noise_wash_db": "number",
    "installation_depth_min_mm": "number",
    "price_tier": "string",
}


@pytest.fixture
def collection():
    client = ephemeral_client()
    yield open_collection(client)
    client.clear_system_cache()


def _answer(payload):
    """LLMの代役。渡された文字列をそのまま返す。"""
    return lambda _prompt: payload


def _add(collection, chunk_id, metadata):
    collection.add(
        ids=[chunk_id],
        documents=["本文"],
        metadatas=[metadata],
        embeddings=[[1.0] + [0.0] * (EMBED_DIM - 1)],
    )


def test_extracts_a_numeric_condition():
    result = extract("26dB以下は", SCHEMA, _answer('{"noise_wash_db": {"$lte": 26}}'))
    assert result.conditions == {"noise_wash_db": {"$lte": 26}}
    assert result.failed is False


def test_extracts_two_conditions():
    payload = '{"noise_wash_db": {"$lte": 26}, "installation_depth_min_mm": {"$lte": 510}}'
    result = extract("26dBで510mm", SCHEMA, _answer(payload))
    assert result.conditions == {
        "noise_wash_db": {"$lte": 26},
        "installation_depth_min_mm": {"$lte": 510},
    }


def test_no_conditions_is_not_a_failure():
    """通常の質問と、抽出できなかったことは区別する。前者は黙って検索に回す。"""
    result = extract("乾燥方式は", SCHEMA, _answer("{}"))
    assert result.conditions == {}
    assert result.failed is False


def test_broken_json_is_a_failure():
    result = extract("26dB以下は", SCHEMA, _answer("これはJSONではありません"))
    assert result.conditions == {}
    assert result.failed is True


def test_failing_ask_is_a_failure():
    def explode(_prompt):
        raise RuntimeError("Ollamaが落ちた")

    result = extract("26dB以下は", SCHEMA, explode)
    assert result.conditions == {}
    assert result.failed is True


def test_unknown_key_is_dropped():
    result = extract("重さは", SCHEMA, _answer('{"weight_kg": {"$lte": 80}}'))
    assert result.conditions == {}


def test_operator_without_the_dollar_prefix_is_accepted():
    """実測でllama3.1:8bは意味を正しく取れていても $ を落とすことがある。

    26dBと510mmの質問で {"lte": 26} が返り、向きも値も合っているのに
    形式だけを理由に両方の条件が捨てられ、絞り込みが丸ごと失われた。
    """
    result = extract("26dB以下は", SCHEMA, _answer('{"noise_wash_db": {"lte": 26}}'))
    assert result.conditions == {"noise_wash_db": {"$lte": 26}}


def test_unknown_operator_without_the_prefix_is_still_dropped():
    """$ を補うのは書き忘れの救済であって、演算子を増やす話ではない。"""
    result = extract("26dBより下", SCHEMA, _answer('{"noise_wash_db": {"lt": 26}}'))
    assert result.conditions == {}


def test_unknown_operator_is_dropped():
    result = extract("26dBより下", SCHEMA, _answer('{"noise_wash_db": {"$lt": 26}}'))
    assert result.conditions == {}


def test_non_numeric_value_for_comparison_is_dropped():
    result = extract("26dB以下", SCHEMA, _answer('{"noise_wash_db": {"$lte": "26"}}'))
    assert result.conditions == {}


def test_string_equality_is_kept():
    """price_tier のような文字列属性は一致で絞れる必要がある。"""
    result = extract(
        "ハイグレードは", SCHEMA, _answer('{"price_tier": {"$eq": "ハイグレード"}}')
    )
    assert result.conditions == {"price_tier": {"$eq": "ハイグレード"}}


def test_one_broken_condition_does_not_discard_the_other():
    """片方が壊れていても、残った条件で絞り込めるほうが利用者に有益である。"""
    payload = '{"noise_wash_db": {"$lte": 26}, "weight_kg": {"$lte": 80}}'
    result = extract("26dBで80kg以下", SCHEMA, _answer(payload))
    assert result.conditions == {"noise_wash_db": {"$lte": 26}}
    assert result.failed is False


def test_a_value_absent_from_the_question_is_dropped():
    """実測でllama3.1:8bは、型番だけを尋ねた質問に brand=Panasonic を返した。

    コーパスに存在しない値であり、通すと通常の質問が絞り込み経路へ流れて
    「該当なし」と答えてしまう。プロンプトで禁じても直らなかった。
    """
    result = extract(
        "UD-0900iの乾燥方式は何ですか", SCHEMA, _answer('{"price_tier": {"$eq": "Panasonic"}}')
    )
    assert result.conditions == {}
    assert result.failed is False


def test_an_empty_string_is_not_a_condition():
    """空文字は「質問文に書かれている」判定を素通りする（"" in text は常に真）。

    実測（2026-08-13・temperature 0 で再現性あり）: 会議の議事録について尋ねた
    「決定事項を教えてほしい」に、llama3.1:8b は全属性を埋めた
    {"brand": {"$eq": ""}, "model_id": {"$eq": ""}, …} を返した。数値のでっち上げは
    _grounded が捨てたが、空文字の4条件はそのまま採用され、家電製品の絞り込み経路へ
    流れた。該当0件の表を渡されたモデルは、直前の会話に出ていた型番を答えた。
    """
    payload = (
        '{"price_tier": {"$eq": ""}, "noise_wash_db": {"$lte": 26}}'
    )
    result = extract("26dB以下の機種は", SCHEMA, _answer(payload))
    assert result.conditions == {"noise_wash_db": {"$lte": 26}}


def test_a_whitespace_only_string_is_not_a_condition():
    """空白だけの値も同じ。属性に空白だけの値を持つ資料は無い。"""
    result = extract("決定事項を教えてほしい", SCHEMA, _answer('{"price_tier": {"$eq": "　 "}}'))
    assert result.conditions == {}


def test_a_threshold_absent_from_the_question_is_dropped():
    """「できるだけ大容量」から washing_capacity_kg ≥ 10 を作った実測への対処。"""
    payload = '{"noise_wash_db": {"$lte": 26}, "installation_depth_min_mm": {"$lte": 999}}'
    result = extract("26dB以下の機種は", SCHEMA, _answer(payload))
    assert result.conditions == {"noise_wash_db": {"$lte": 26}}


def test_a_fabricated_number_hiding_inside_another_number_is_dropped():
    """部分一致で照合すると、でっち上げた 10 が「510mm」に含まれて素通りする。

    実測でモデルが作った条件がまさにこれで、数として突き合わせないと防げない。
    """
    payload = '{"washing_capacity_kg": {"$gte": 10}, "installation_depth_min_mm": {"$lte": 510}}'
    result = extract("防水パン奥行きが510mmしかありません", SCHEMA, _answer(payload))
    assert result.conditions == {"installation_depth_min_mm": {"$lte": 510}}


def test_full_width_digits_in_the_question_still_match():
    """日本語入力では全角数字が普通に混ざる。照合できないと黙って条件を失う。"""
    result = extract("２６dB以下は", SCHEMA, _answer('{"noise_wash_db": {"$lte": 26}}'))
    assert result.conditions == {"noise_wash_db": {"$lte": 26}}


def test_a_whole_number_written_without_a_decimal_point_matches():
    """9.0kg の属性に対して、質問には「9キログラム」としか書かれていない。"""
    result = extract(
        "洗濯容量が9キログラム以上は", SCHEMA, _answer('{"noise_wash_db": {"$gte": 9.0}}')
    )
    assert result.conditions == {"noise_wash_db": {"$gte": 9.0}}


def test_ranking_is_not_asked_for_without_a_superlative():
    """「最大」等の語が無ければLLMを呼ばない。1問あたり数秒を無駄にしないため。"""
    calls = []

    def spy(prompt):
        calls.append(prompt)
        return "{}"

    assert extract_ranking("26dB以下の機種は", SCHEMA, spy) is None
    assert calls == []


def test_the_ranking_prompt_does_not_hand_the_model_a_placeholder_key():
    """形式を {"属性名": "最大"} と書くと、qwen2.5:7b-instruct はそれをそのまま返した。

    llama3.1:8b は置き換えていたため、モデルを変えるまで表面化しなかった。
    例に使う属性は一覧に無い架空のもの（example_kg）にする。実在のキーを書くと、
    どの質問でもそれを返してくる。
    """
    prompt = conditions._ranking_prompt("最大の洗濯容量は", ["washing_capacity_kg"])
    assert '"属性名"' not in prompt  # JSONのキーとしてのプレースホルダは渡さない
    assert "example_kg" in prompt  # 例は架空の属性で示す
    assert '{"washing_capacity_kg"' not in prompt  # 実在のキーを例にすると必ずそれを返す


def test_ranking_extracts_the_attribute_and_direction():
    result = extract_ranking(
        "最大の洗濯容量は", {"washing_capacity_kg": "number"}, _answer('{"washing_capacity_kg": "最大"}')
    )
    assert result == Ranking(key="washing_capacity_kg", descending=True)


def test_ranking_understands_the_smallest():
    result = extract_ranking(
        "最も運転音が小さい機種は", SCHEMA, _answer('{"noise_wash_db": "最小"}')
    )
    assert result == Ranking(key="noise_wash_db", descending=False)


def test_ranking_ignores_attributes_outside_the_schema():
    """スキーマに無いキーで並べ替えると、その列が無い行が落ちる。"""
    assert extract_ranking("最大の重量は", SCHEMA, _answer('{"weight_kg": "最大"}')) is None


def test_ranking_ignores_string_attributes():
    """文字列の大小は比較できない。"""
    assert extract_ranking("最大のグレードは", SCHEMA, _answer('{"price_tier": "最大"}')) is None


def test_ranking_ignores_a_broken_answer():
    assert extract_ranking("最大の洗濯容量は", SCHEMA, _answer("これはJSONではない")) is None
    assert extract_ranking("最大の洗濯容量は", SCHEMA, _answer("{}")) is None


def test_ranking_survives_an_llm_failure():
    """並べ替えが取れなくても、回答生成まで巻き添えにしない。"""

    def broken(_prompt):
        raise RuntimeError("Ollamaが落ちている")

    assert extract_ranking("最大の洗濯容量は", SCHEMA, broken) is None


def test_empty_schema_does_not_call_the_llm():
    """属性が1つも無いコーパスでLLMを呼ぶのは無駄でしかない。"""
    calls = []

    def record(prompt):
        calls.append(prompt)
        return "{}"

    assert extract("26dB以下は", {}, record).conditions == {}
    assert calls == []


def test_available_keys_reports_types(collection):
    _add(
        collection,
        "a.md::section1::0",
        {"source": "a.md", "noise_wash_db": 26, "washing_capacity_kg": 11.0,
         "price_tier": "ハイグレード"},
    )
    assert available_keys(collection) == {
        "noise_wash_db": "number",
        "washing_capacity_kg": "number",
        "price_tier": "string",
    }


def test_available_keys_excludes_reserved_keys(collection):
    _add(collection, "a.md::section1::0", {"source": "a.md", "heading": "設置情報"})
    assert available_keys(collection) == {}


def test_available_keys_is_empty_for_an_empty_collection(collection):
    assert available_keys(collection) == {}


def test_the_prompt_lists_the_available_keys():
    """スキーマを渡さなければ、モデルはどのキー名を返せばよいか分からない。"""
    seen = []

    def record(prompt):
        seen.append(prompt)
        return "{}"

    extract("26dB以下は", SCHEMA, record)
    assert "noise_wash_db" in seen[0]
    assert "26dB以下は" in seen[0]
