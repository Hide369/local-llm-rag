"""Cowork タブ（雛形からの文書生成）。

実機のOllamaにもネットワークにも触れない。AppTest は rag_chat_app.py を同じ
プロセスで実行するため、本番のストアと本番の templates/ を開かせない。
"""
import json
from pathlib import Path
from unittest.mock import patch

import docx
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

import ingest.retrieval as retrieval
from docgen import filling
from docgen import mermaid
from docgen import templates as templates_module
from ingest import chat
from ingest import reranker as reranker_module
from ingest import store as store_module
from ingest import vlm as vlm_module
from ingest.vector_store import open_store as open_real_store

APP_PATH = Path(__file__).resolve().parent.parent / "rag_chat_app.py"


@pytest.fixture
def app():
    st.cache_resource.clear()
    return AppTest.from_file(str(APP_PATH), default_timeout=60)


@pytest.fixture(autouse=True)
def _no_network():
    with (
        patch.object(reranker_module, "check_reranker", lambda: None),
        patch.object(reranker_module, "rerank", lambda query, texts: [9.0] * len(texts)),
        patch.object(vlm_module, "check_vlm", lambda *a, **k: None),
    ):
        yield


def _stub_store():
    def factory(*args, **kwargs):
        collection = open_real_store(":memory:")
        collection.add(
            ids=["chunk-1"],
            documents=["第5回 AI活用検討会を開催した。"],
            embeddings=[[0.1, 0.2]],
            metadatas=[{"source": "議事録.docx", "location_type": "section", "location": 1}],
        )
        return collection

    return factory


def _register(directory, name="議事録.docx"):
    directory.mkdir(parents=True, exist_ok=True)
    document = docx.Document()
    document.add_paragraph("{{会議名}}")
    document.add_paragraph("{{決定事項}}")
    document.save(directory / name)


def test_the_mode_toggle_offers_both_modes(app, tmp_path):
    with (
        patch.object(store_module, "open_store", _stub_store()),
        patch.object(templates_module, "TEMPLATE_DIR", tmp_path / "templates"),
    ):
        app.run()
    assert not app.exception
    assert "Cowork" in str(app)


def test_cowork_without_any_template_tells_the_user_to_register_one(app, tmp_path):
    """雛形が0件のまま生成ボタンだけ出すと、押しても何も起きない。"""
    with (
        patch.object(store_module, "open_store", _stub_store()),
        patch.object(templates_module, "TEMPLATE_DIR", tmp_path / "templates"),
    ):
        app.run()
        app.segmented_control[0].set_value("Cowork").run()

    assert not app.exception
    assert any("雛形" in warning.value for warning in app.warning)


def test_cowork_without_a_template_does_not_silently_answer_as_chat(app, tmp_path):
    """雛形が無いまま Cowork で送ると、黙ってチャットの回答を返さない。

    元の分岐は「Cowork かつ雛形あり」以外を全部チャットの else 節に落として
    いたため、雛形0件で送信すると通常のチャット回答が返っていた。利用者は
    Cowork のつもりで読むため、どこから来た答えなのかを取り違える。
    """
    with (
        patch.object(store_module, "open_store", _stub_store()),
        patch.object(templates_module, "TEMPLATE_DIR", tmp_path / "templates"),
        patch.object(retrieval, "embed_query", lambda *a, **k: [0.1, 0.2]),
    ):
        app.run()
        app.segmented_control[0].set_value("Cowork").run()
        app.chat_input[0].set_value("第5回会議の議事録を作って").run()

    assert not app.exception
    assert any("雛形が登録されていません" in error.value for error in app.error)


def test_cowork_shows_the_error_when_generation_fails(app, tmp_path):
    """PromptTooLongError等の失敗は、埋まらない欄を残すだけでなく画面に伝える。

    黙って落とすと、利用者は生成が止まったこと自体に気づけない
    （_generate_document は結果を st.session_state.cowork_result に積むだけで
    直接 st.error を呼ばないため、例外経路がその積み方から漏れていないかを
    別途押さえる）。
    """
    store = tmp_path / "templates"
    _register(store)
    with (
        patch.object(store_module, "open_store", _stub_store()),
        patch.object(templates_module, "TEMPLATE_DIR", store),
        patch.object(retrieval, "embed_query", lambda *a, **k: [0.1, 0.2]),
        patch.object(
            filling,
            "fill_values",
            side_effect=filling.PromptTooLongError("添付と検索結果が長すぎます"),
        ),
    ):
        app.run()
        app.segmented_control[0].set_value("Cowork").run()
        app.chat_input[0].set_value("第5回会議の議事録を作って").run()

    assert not app.exception
    assert any("添付と検索結果が長すぎます" in error.value for error in app.error)


def test_cowork_generates_a_file_and_offers_it_for_download(app, tmp_path):
    store = tmp_path / "templates"
    _register(store)
    with (
        patch.object(store_module, "open_store", _stub_store()),
        patch.object(templates_module, "TEMPLATE_DIR", store),
        patch.object(retrieval, "embed_query", lambda *a, **k: [0.1, 0.2]),
        patch.object(
            chat,
            "ask_json",
            lambda model, prompt, session=None, num_ctx=None: json.dumps(
                {"会議名": "第5回 AI活用検討会", "決定事項": "・継続"}, ensure_ascii=False
            ),
        ),
    ):
        app.run()
        app.segmented_control[0].set_value("Cowork").run()
        app.chat_input[0].set_value("第5回会議の議事録を作って").run()

    assert not app.exception
    assert app.download_button


def test_cowork_lists_the_marks_it_could_not_fill(app, tmp_path):
    """埋まらなかった欄を出さないと、利用者は雛形を開くまで気づけない。"""
    store = tmp_path / "templates"
    _register(store)
    with (
        patch.object(store_module, "open_store", _stub_store()),
        patch.object(templates_module, "TEMPLATE_DIR", store),
        patch.object(retrieval, "embed_query", lambda *a, **k: [0.1, 0.2]),
        patch.object(
            chat,
            "ask_json",
            lambda model, prompt, session=None, num_ctx=None: json.dumps(
                {"会議名": "第5回 AI活用検討会"}, ensure_ascii=False
            ),
        ),
    ):
        app.run()
        app.segmented_control[0].set_value("Cowork").run()
        app.chat_input[0].set_value("第5回会議の議事録を作って").run()

    assert not app.exception
    assert any("決定事項" in warning.value for warning in app.warning)


def test_cowork_uses_a_larger_context_size(app, tmp_path):
    """8192 のままだと、文字起こしを添付した瞬間に文脈からこぼれる。"""
    store = tmp_path / "templates"
    _register(store)
    seen = []

    def ask_json(model, prompt, session=None, num_ctx=None):
        seen.append(num_ctx)
        return json.dumps({"会議名": "第5回"}, ensure_ascii=False)

    with (
        patch.object(store_module, "open_store", _stub_store()),
        patch.object(templates_module, "TEMPLATE_DIR", store),
        patch.object(retrieval, "embed_query", lambda *a, **k: [0.1, 0.2]),
        patch.object(chat, "ask_json", ask_json),
    ):
        app.run()
        app.segmented_control[0].set_value("Cowork").run()
        app.chat_input[0].set_value("議事録を作って").run()

    from docgen import filling

    assert seen == [filling.GENERATION_NUM_CTX]


def test_cowork_does_not_search_the_documentation_unless_it_is_asked(app, tmp_path):
    """既定で技術ドキュメントまで引くと、1回の生成ごとに英訳のLLM呼び出しが
    1回と検索が1本、要らないまま増える（30〜60秒）。"""
    store = tmp_path / "templates"
    _register(store)
    opened = []
    collection = _stub_store()

    def factory(db_path, *args, **kwargs):
        opened.append(str(db_path))
        return collection(db_path)

    with (
        patch.object(store_module, "open_store", factory),
        patch.object(templates_module, "TEMPLATE_DIR", store),
        patch.object(retrieval, "embed_query", lambda *a, **k: [0.1, 0.2]),
        patch.object(
            chat,
            "ask_json",
            lambda model, prompt, session=None, num_ctx=None: json.dumps(
                {"会議名": "第5回"}, ensure_ascii=False
            ),
        ),
    ):
        app.run()
        app.segmented_control[0].set_value("Cowork").run()
        app.chat_input[0].set_value("第5回会議の議事録を作って").run()

    assert not app.exception
    assert not any("docs_store" in path for path in opened)


def test_cowork_tells_the_user_when_a_diagram_could_not_be_drawn(app, tmp_path):
    """黙って Mermaid のテキストが入っていると、利用者は成果物を開くまで
    気づけない。"""
    store = tmp_path / "templates"
    _register(store)
    with (
        patch.object(store_module, "open_store", _stub_store()),
        patch.object(templates_module, "TEMPLATE_DIR", store),
        patch.object(retrieval, "embed_query", lambda *a, **k: [0.1, 0.2]),
        patch.object(
            mermaid, "render", side_effect=mermaid.MermaidError("mmdc が見つかりません")
        ),
        patch.object(
            chat,
            "ask_json",
            lambda model, prompt, session=None, num_ctx=None: json.dumps(
                {
                    "会議名": "```mermaid\nsequenceDiagram\n  利用者->>画面: 生成\n```",
                    "決定事項": "・継続",
                },
                ensure_ascii=False,
            ),
        ),
    ):
        app.run()
        app.segmented_control[0].set_value("Cowork").run()
        app.chat_input[0].set_value("設計書を作って").run()

    assert not app.exception
    assert any("図にできなかった" in warning.value for warning in app.warning)
