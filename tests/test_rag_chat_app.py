"""チャット画面の異常系。

回答生成の失敗（APIError）はチャット欄に短いメッセージとして出るが、検索の
失敗はどこにも捕まえていなかった。実測: 2026-08-13 07:04〜08:10 の間Ollamaが
停止しており、質問すると ingest.embedder.EmbeddingError のトレースバックが
そのまま画面に出た。

AppTest は rag_chat_app.py を同じプロセスで実行する。本番の chroma_db を
開くと起動中のStreamlitとの同時アクセスでHNSWインデックスを壊す恐れがあるため
（README「既知の制約」）、PersistentClient をインメモリのものへ差し替える。
"""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

import ingest.retrieval as retrieval
from ingest import store
from ingest.embedder import EmbeddingError
from tests.conftest import ephemeral_client

APP_PATH = Path(__file__).resolve().parent.parent / "rag_chat_app.py"

OFFLINE_MESSAGE = "Ollamaに接続できません（テスト）"


def _stub_persistent_client(metadata):
    """PersistentClient の代わりに、1チャンクだけ入ったインメモリDBを返す。"""

    def factory(*args, **kwargs):
        client = ephemeral_client()
        collection = store.open_collection(client)
        collection.add(
            ids=["chunk-1"],
            documents=["洗濯機の運転音は26dBです。"],
            embeddings=[[0.1, 0.2]],
            metadatas=[metadata],
        )
        return client

    return factory


def _offline_embed_query(*args, **kwargs):
    raise EmbeddingError(OFFLINE_MESSAGE)


class _FakeStreamChunk:
    """OpenAIのストリーム1個分。1文字ずつ届く、いちばん細かい刻みを再現する。"""

    def __init__(self, content):
        self.choices = [SimpleNamespace(delta=SimpleNamespace(content=content))]


def _fake_openai(text):
    """生成だけを差し替える。条件抽出は属性なしのDBでそもそも呼ばれない。"""
    client = MagicMock()
    client.chat.completions.create.return_value = [
        _FakeStreamChunk(character) for character in text
    ]
    return MagicMock(return_value=client)


@pytest.fixture
def app():
    # get_collection / get_schema は @st.cache_resource で、キャッシュはプロセス
    # 全体で共有される。前のテストのDBを引き継がないよう毎回捨てる。
    st.cache_resource.clear()
    return AppTest.from_file(str(APP_PATH), default_timeout=60)


def test_search_failure_is_reported_instead_of_crashing(app):
    """埋め込みAPIが落ちていても、画面に出るのはメッセージであってトレースバックではない。"""
    with (
        patch("chromadb.PersistentClient", _stub_persistent_client({"source": "a.md"})),
        patch.object(retrieval, "embed_query", _offline_embed_query),
    ):
        app.run()
        app.chat_input[0].set_value("運転音が静かな機種は？").run()

    assert not app.exception
    assert any(OFFLINE_MESSAGE in element.value for element in app.error)


def test_search_failure_does_not_also_claim_it_will_search(app):
    """条件抽出と検索が同じ原因で落ちたときに、通常の検索を約束する警告を出さない。

    Ollamaが落ちていれば条件抽出（LLM）も検索（埋め込み）も失敗する。
    「通常の検索で回答します」と告げた直後にその検索が失敗するのでは、
    利用者にとって嘘になる。
    """
    # 数値属性を1つ持たせてスキーマを空でなくすると、条件抽出のLLM呼び出しが走る。
    metadata = {"source": "a.md", "noise_db": 26}
    with (
        patch("chromadb.PersistentClient", _stub_persistent_client(metadata)),
        patch("openai.OpenAI"),  # JSONにならない応答を返し、条件抽出を失敗させる
        patch.object(retrieval, "embed_query", _offline_embed_query),
    ):
        app.run()
        app.chat_input[0].set_value("運転音26dB以下の機種は？").run()

    assert not app.exception
    assert any(OFFLINE_MESSAGE in element.value for element in app.error)
    assert not app.warning


def test_a_follow_up_question_is_searched_with_the_previous_one(app):
    """「決定事項を教えてほしい」だけでは議事録を引けない（実測で上位4件が別資料）。"""
    queries = []

    def record(text, session=None):
        queries.append(text)
        return [0.1, 0.2]

    with (
        patch("chromadb.PersistentClient", _stub_persistent_client({"source": "a.md"})),
        patch("openai.OpenAI", _fake_openai("第5回会議の決定事項は…")),
        patch.object(retrieval, "embed_query", record),
    ):
        app.run()
        app.chat_input[0].set_value("第5回会議のタイトルを教えてほしい").run()
        app.chat_input[0].set_value("決定事項を教えてほしい").run()

    assert queries == [
        "第5回会議のタイトルを教えてほしい",
        "第5回会議のタイトルを教えてほしい 決定事項を教えてほしい",
    ]


def _openai_for_the_catalog_route(condition_json, ranking_json, answer):
    """条件抽出・並べ替え抽出・生成の3種類の呼び出しを引数で見分けて返す。

    呼ばれる順に並べると、順序が変わるたびにテストが壊れる。
    """
    client = MagicMock()

    def create(**kwargs):
        if kwargs.get("stream"):
            return [_FakeStreamChunk(character) for character in answer]
        prompt = kwargs["messages"][0]["content"]
        payload = ranking_json if "最大・最小" in prompt else condition_json
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=payload))]
        )

    client.chat.completions.create.side_effect = create
    return MagicMock(return_value=client)


def test_products_that_fail_the_condition_are_shown_but_not_sent_to_the_model(app):
    """設置できない機種をモデルに渡すと、答えとして挙げてしまう（実測8回中5回）。

    利用者には見せる価値があるので、画面の一覧にだけ残す。
    """
    prompts = []

    def factory(*args, **kwargs):
        client = ephemeral_client()
        collection = store.open_collection(client)
        for model, capacity, depth in (
            ("UD-1100S", 11.0, 510),
            ("UD-1400X", 14.0, 545),
        ):
            collection.add(
                ids=[f"{model}::0"],
                documents=[f"{model}の本文"],
                embeddings=[[0.1, 0.2]],
                metadatas=[
                    {
                        "source": f"家電製品/{model}.md",
                        "model_id": model,
                        "washing_capacity_kg": capacity,
                        "installation_depth_min_mm": depth,
                    }
                ],
            )
        return client

    openai_factory = _openai_for_the_catalog_route(
        '{"installation_depth_min_mm": {"$lte": 510}}',
        '{"washing_capacity_kg": "最大"}',
        "最大11.0kgです。",
    )
    client = openai_factory.return_value
    with patch("chromadb.PersistentClient", factory), patch("openai.OpenAI", openai_factory):
        app.run()
        app.chat_input[0].set_value("510mmに設置できる最大の洗濯容量は").run()

    prompts = [
        call.kwargs["messages"][-1]["content"]
        for call in client.chat.completions.create.call_args_list
        if call.kwargs.get("stream")
    ]
    assert prompts, "生成が呼ばれていない"
    assert "UD-1400X" not in prompts[0]
    shown = "\n".join(element.value for element in app.code)
    assert "UD-1400X" in shown
    assert "条件を満たさないので選べない" in shown


def test_answer_is_shown_without_the_repeated_label(app):
    """モデルが付ける「答え：」は表示しない。中身は残す。"""
    generated = "省エネ基準達成率が最も高いのはUD-1100iEです。\n答え： 型番：UD-1100iE 達成率：125%"
    with (
        patch("chromadb.PersistentClient", _stub_persistent_client({"source": "a.md"})),
        patch("openai.OpenAI", _fake_openai(generated)),
        patch.object(retrieval, "embed_query", lambda *a, **k: [0.1, 0.2]),
    ):
        app.run()
        app.chat_input[0].set_value("省エネ基準達成率が最も高い機種は？").run()

    assert not app.exception
    shown = "\n".join(element.value for element in app.markdown)
    assert "答え：" not in shown
    assert "型番：UD-1100iE 達成率：125%" in shown
