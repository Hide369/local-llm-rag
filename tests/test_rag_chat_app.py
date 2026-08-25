"""チャット画面の異常系。

回答生成の失敗（chat.ChatError）はチャット欄に短いメッセージとして出るが、
検索の失敗はどこにも捕まえていなかった。実測: 2026-08-13 07:04〜08:10 の間
Ollamaが停止しており、質問すると ingest.embedder.EmbeddingError の
トレースバックがそのまま画面に出た。

生成は ingest/chat.py 経由でOllamaのネイティブAPI（/api/chat）を直接叩く
（openaiパッケージ経由ではnum_ctxが反映されなかったため、実測を経て切り替えた。
ingest/chat.py のモジュールdocstring参照）。テストでは chat.ask_json /
chat.stream_chat をこの階層で差し替える。

AppTest は rag_chat_app.py を同じプロセスで実行する。本番の chroma_db を
開くと起動中のStreamlitとの同時アクセスでHNSWインデックスを壊す恐れがあるため
（README「既知の制約」）、PersistentClient をインメモリのものへ差し替える。
"""
from pathlib import Path
from unittest.mock import patch

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

import ingest.retrieval as retrieval
from ingest import chat
from ingest import embedder as embedder_module
from ingest import store
from ingest import vlm as vlm_module
from ingest.embedder import EmbeddingError
from scripts import ingest_source
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


def _fake_stream_chat(text):
    """生成だけを差し替える。条件抽出は属性なしのDBでそもそも呼ばれない。

    呼び出しの引数（model・messages・temperature）は .calls に積む。
    ingest/chat.py の実シグネチャ stream_chat(model, messages, temperature, session=None)
    に合わせる。
    """
    calls = []

    def stream(model, messages, temperature, session=None):
        calls.append({"model": model, "messages": messages, "temperature": temperature})
        yield from text

    stream.calls = calls
    return stream


@pytest.fixture
def app():
    # get_collection / get_schema は @st.cache_resource で、キャッシュはプロセス
    # 全体で共有される。前のテストのDBを引き継がないよう毎回捨てる。
    st.cache_resource.clear()
    return AppTest.from_file(str(APP_PATH), default_timeout=60)


def test_search_failure_is_reported_instead_of_crashing(app):
    """埋め込みAPIが落ちていても、画面に出るのはメッセージであってトレースバックではない。

    エラー文は st.error() でその場に出るだけでなく、履歴にも残す
    （入力欄を再有効化する直後の st.rerun() で st.error() の描画自体は
    消えるため、履歴に残していなければ最終的な画面から跡形もなく消える）。
    """
    with (
        patch("chromadb.PersistentClient", _stub_persistent_client({"source": "a.md"})),
        patch.object(retrieval, "embed_query", _offline_embed_query),
    ):
        app.run()
        app.chat_input[0].set_value("運転音が静かな機種は？").run()

    assert not app.exception
    assert OFFLINE_MESSAGE in app.session_state.messages[-1]["content"]


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
        # JSONにならない応答を返し、条件抽出を失敗させる
        patch.object(chat, "ask_json", lambda model, prompt, session=None: "not json"),
        patch.object(retrieval, "embed_query", _offline_embed_query),
    ):
        app.run()
        app.chat_input[0].set_value("運転音26dB以下の機種は？").run()

    assert not app.exception
    assert OFFLINE_MESSAGE in app.session_state.messages[-1]["content"]
    assert app.session_state.messages[-1].get("note") is None


def test_a_follow_up_question_is_searched_with_the_previous_one(app):
    """「決定事項を教えてほしい」だけでは議事録を引けない（実測で上位4件が別資料）。"""
    queries = []

    def record(text, session=None):
        queries.append(text)
        return [0.1, 0.2]

    with (
        patch("chromadb.PersistentClient", _stub_persistent_client({"source": "a.md"})),
        patch.object(chat, "stream_chat", _fake_stream_chat("第5回会議の決定事項は…")),
        patch.object(retrieval, "embed_query", record),
    ):
        app.run()
        app.chat_input[0].set_value("第5回会議のタイトルを教えてほしい").run()
        app.chat_input[0].set_value("決定事項を教えてほしい").run()

    assert queries == [
        "第5回会議のタイトルを教えてほしい",
        "第5回会議のタイトルを教えてほしい 決定事項を教えてほしい",
    ]


def test_the_model_is_picked_from_the_pulled_models(app):
    """モデル名の自由入力ではなく、pull済みモデルの固定リストからの選択にする。

    自由入力だと打ち間違いが生成時のchat.ChatErrorになるまで分からなかった。
    既定は qwen2.5:7b-instruct のまま（README「モデルの比較」）。
    """
    with (
        patch("chromadb.PersistentClient", _stub_persistent_client({"source": "a.md"})),
        patch.object(chat, "stream_chat", _fake_stream_chat("回答")),
        patch.object(retrieval, "embed_query", lambda *a, **k: [0.1, 0.2]),
    ):
        app.run()

    assert not app.exception
    assert app.selectbox[0].options == [
        "qwen2.5:7b-instruct",
        "llama3.1:8b",
        "gpt-oss:20b",
        "qwen3:32b",
    ]
    assert app.selectbox[0].value == "qwen2.5:7b-instruct"


def test_the_picked_model_is_the_one_that_generates(app):
    """プルダウンで選んだモデルが実際の生成に渡る。見た目だけの切り替えにしない。"""
    fake_stream = _fake_stream_chat("回答です。")
    with (
        patch("chromadb.PersistentClient", _stub_persistent_client({"source": "a.md"})),
        patch.object(chat, "stream_chat", fake_stream),
        patch.object(retrieval, "embed_query", lambda *a, **k: [0.1, 0.2]),
    ):
        app.run()
        app.selectbox[0].set_value("llama3.1:8b").run()
        app.chat_input[0].set_value("運転音は？").run()

    assert not app.exception
    used = [call["model"] for call in fake_stream.calls]
    assert used == ["llama3.1:8b"]


def _fake_ask_json_for_the_catalog_route(condition_json, ranking_json):
    """条件抽出・並べ替え抽出の2種類の呼び出しをプロンプト文面で見分けて返す。

    呼ばれる順に並べると、順序が変わるたびにテストが壊れる。
    """

    def ask_json(model, prompt, session=None):
        return ranking_json if "最大・最小" in prompt else condition_json

    return ask_json


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

    fake_ask_json = _fake_ask_json_for_the_catalog_route(
        '{"installation_depth_min_mm": {"$lte": 510}}',
        '{"washing_capacity_kg": "最大"}',
    )
    fake_stream = _fake_stream_chat("最大11.0kgです。")
    with (
        patch("chromadb.PersistentClient", factory),
        patch.object(chat, "ask_json", fake_ask_json),
        patch.object(chat, "stream_chat", fake_stream),
    ):
        app.run()
        app.chat_input[0].set_value("510mmに設置できる最大の洗濯容量は").run()

    prompts = [call["messages"][-1]["content"] for call in fake_stream.calls]
    assert prompts, "生成が呼ばれていない"
    assert "UD-1400X" not in prompts[0]
    shown = "\n".join(element.value for element in app.code)
    assert "UD-1400X" in shown
    assert "条件を満たさないので選べない" in shown


def test_vlm_checkbox_off_by_default_does_not_pass_caption_image(app):
    """既定はOFF。scripts/ingest_source.pyのCLI既定（VLM無効）と揃える。"""
    calls = []

    def fake_ingest_directory(*args, **kwargs):
        calls.append(kwargs)
        return ingest_source.IngestReport()

    with (
        patch("chromadb.PersistentClient", _stub_persistent_client({"source": "a.md"})),
        patch.object(embedder_module, "check_ollama", lambda *a, **k: None),
        patch.object(ingest_source, "ingest_directory", fake_ingest_directory),
    ):
        app.run()
        app.button[0].click().run()

    assert not app.exception
    assert calls == [{"caption_image": None}]


def test_vlm_checkbox_on_checks_vlm_and_passes_caption_image(app):
    """ONならvlm.check_vlm()で疎通確認してからcaption_imageを渡す。

    scripts/ingest_source.pyの--with-vlmと同じ配線（先に疎通確認、成功したら
    vlm.caption_imageを渡す）をStreamlit側でも踏襲する。
    """
    calls = []
    checked = []

    def fake_ingest_directory(*args, **kwargs):
        calls.append(kwargs)
        return ingest_source.IngestReport()

    with (
        patch("chromadb.PersistentClient", _stub_persistent_client({"source": "a.md"})),
        patch.object(embedder_module, "check_ollama", lambda *a, **k: None),
        patch.object(vlm_module, "check_vlm", lambda *a, **k: checked.append(True)),
        patch.object(ingest_source, "ingest_directory", fake_ingest_directory),
    ):
        app.run()
        app.checkbox[0].set_value(True).run()
        app.button[0].click().run()

    assert not app.exception
    assert checked == [True]
    assert calls == [{"caption_image": vlm_module.caption_image}]


def test_vlm_checkbox_on_but_unreachable_reports_error_without_ingesting(app):
    """VLMの疎通確認が失敗したら、取り込みを実行せずエラーだけ表示する。

    460チャンクの処理が始まってから落ちるのを防ぐ、CLI版と同じ考え方
    （ingest/vlm.py の check_vlm のdocstring）。
    """
    calls = []

    def fake_ingest_directory(*args, **kwargs):
        calls.append(kwargs)
        return ingest_source.IngestReport()

    def failing_check_vlm(*a, **k):
        raise vlm_module.VlmError("VLMモデル qwen2.5vl:7b がありません")

    with (
        patch("chromadb.PersistentClient", _stub_persistent_client({"source": "a.md"})),
        patch.object(embedder_module, "check_ollama", lambda *a, **k: None),
        patch.object(vlm_module, "check_vlm", failing_check_vlm),
        patch.object(ingest_source, "ingest_directory", fake_ingest_directory),
    ):
        app.run()
        app.checkbox[0].set_value(True).run()
        app.button[0].click().run()

    assert not app.exception
    assert calls == []
    assert any("qwen2.5vl:7b" in element.value for element in app.error)


def test_answer_is_shown_without_the_repeated_label(app):
    """モデルが付ける「答え：」は表示しない。中身は残す。"""
    generated = "省エネ基準達成率が最も高いのはUD-1100iEです。\n答え： 型番：UD-1100iE 達成率：125%"
    with (
        patch("chromadb.PersistentClient", _stub_persistent_client({"source": "a.md"})),
        patch.object(chat, "stream_chat", _fake_stream_chat(generated)),
        patch.object(retrieval, "embed_query", lambda *a, **k: [0.1, 0.2]),
    ):
        app.run()
        app.chat_input[0].set_value("省エネ基準達成率が最も高い機種は？").run()

    assert not app.exception
    shown = "\n".join(element.value for element in app.markdown)
    assert "答え：" not in shown


def test_input_is_re_enabled_and_history_has_exactly_one_exchange_after_answering(app):
    """生成中は入力欄を無効化し、完了後に再有効化する。

    生成中の無効化そのものを直接観測はできない（AppTest.run()は内部の
    st.rerun()を全部消化してから戻るため）。代わりに、完了後の最終状態で
    (1) 入力欄が有効に戻っていること (2) やりとりが二重に積まれていない
    （無効化の仕組み自体がバグって多重発火していないか）ことを確認する。
    """
    with (
        patch("chromadb.PersistentClient", _stub_persistent_client({"source": "a.md"})),
        patch.object(chat, "stream_chat", _fake_stream_chat("回答です。")),
        patch.object(retrieval, "embed_query", lambda *a, **k: [0.1, 0.2]),
    ):
        app.run()
        app.chat_input[0].set_value("運転音は？").run()

    assert not app.exception
    assert app.chat_input[0].disabled is False
    assert [m["role"] for m in app.session_state.messages] == ["user", "assistant"]
