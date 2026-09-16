"""Ollama と vLLM(OpenAI互換) の切り替えを検査する。

既定（Ollama）の挙動が1文字も変わらないことは既存のテストが見ている。ここは
`LLM_BACKEND=vllm` にしたときだけ通る経路を対象にする。実機のvLLMは要らない。
要求の組み立てと応答の取り出しは純粋な変換であり、そこが本番と食い違うと
黙って壊れる部分だからである。
"""
import base64
import importlib

import pytest
import requests

import ingest.backend as backend
import ingest.chat as chat
import ingest.embedder as embedder
import ingest.vlm as vlm


@pytest.fixture
def on_vllm(monkeypatch):
    """接続先をvLLMに倒す。

    環境変数ではなくモジュールの定数を差し替えるのは、BACKEND が取り込み時に
    一度だけ読まれるためである。呼び出し側は is_vllm() しか見ないので、
    ここを変えれば全経路が切り替わる。
    """
    monkeypatch.setattr(backend, "BACKEND", backend.VLLM)


class _FakeResponse:
    def __init__(self, payload=None, lines=()):
        self._payload = payload
        self._lines = list(lines)

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload

    def iter_lines(self):
        return iter(self._lines)


class _FakeSession:
    """POST先のURLと本文を記録する。"""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []
        self.headers = {}

    def post(self, url, json, timeout=None, stream=False):
        self.calls.append((url, json))
        return self._responses.pop(0)

    def get(self, url, timeout=None):
        self.calls.append((url, None))
        return self._responses.pop(0)

    def close(self):
        return None


# --- 接続先の決定 -----------------------------------------------------------


def test_the_default_backend_is_ollama(monkeypatch):
    """何も設定していないノートPCが今までどおり動くこと。"""
    monkeypatch.delenv("LLM_BACKEND", raising=False)
    reloaded = importlib.reload(backend)
    try:
        assert reloaded.BACKEND == reloaded.OLLAMA
        assert reloaded.is_vllm() is False
    finally:
        importlib.reload(backend)


def test_an_unknown_backend_stops_at_import(monkeypatch):
    """綴りを間違えたまま黙ってOllamaへ落ちると、原因が分からなくなる。"""
    monkeypatch.setenv("LLM_BACKEND", "vllm2")
    with pytest.raises(ValueError, match="LLM_BACKEND"):
        importlib.reload(backend)
    monkeypatch.delenv("LLM_BACKEND", raising=False)
    importlib.reload(backend)


def test_the_auth_header_differs_by_backend(monkeypatch):
    monkeypatch.setenv("OLLAMA_API_KEY", "ollama-key")
    monkeypatch.setenv("VLLM_API_KEY", "vllm-key")

    session = _FakeSession([])
    backend.apply_auth(session)
    assert session.headers == {"X-API-Key": "ollama-key"}

    monkeypatch.setattr(backend, "BACKEND", backend.VLLM)
    session = _FakeSession([])
    backend.apply_auth(session)
    assert session.headers == {"Authorization": "Bearer vllm-key"}


# --- 応答の取り出し ---------------------------------------------------------


def test_reasoning_only_answers_are_reported(monkeypatch):
    """--reasoning-parser を付け忘れると本文が空で返る。

    そのまま返すと ask_json の呼び出し元がJSONの解釈で落ち、原因が
    サーバーの起動フラグにあることが分からない。ここで名指しする。
    """
    payload = {"choices": [{"message": {"content": "", "reasoning_content": "考えた"}}]}
    with pytest.raises(ValueError, match="--reasoning-parser"):
        backend.message_content(payload)


def test_the_content_is_taken_from_the_first_choice():
    payload = {"choices": [{"message": {"content": "204"}}]}
    assert backend.message_content(payload) == "204"


def test_embeddings_are_reordered_by_index():
    """data の並びは保証されない。入力順とずれたベクトルをDBへ書くと、
    どのチャンクにも気づかれずに間違った意味が付く。
    """
    payload = {
        "data": [
            {"index": 1, "embedding": [0.2]},
            {"index": 0, "embedding": [0.1]},
        ]
    }
    assert backend.embedding_vectors(payload) == [[0.1], [0.2]]


# --- 生成 -------------------------------------------------------------------


def test_ask_json_asks_for_json_in_each_dialect(on_vllm):
    url, payload = chat._request(
        "m", [{"role": "user", "content": "q"}], num_ctx=8192, temperature=0, json_format=True
    )
    assert url.endswith("/v1/chat/completions")
    assert payload["response_format"] == {"type": "json_object"}
    assert payload["temperature"] == 0
    # Ollama の "format" は OpenAI 互換では意味を持たない。送ってはいけない。
    assert "format" not in payload


def test_the_vllm_request_does_not_send_num_ctx(on_vllm):
    """vLLM の文脈長は起動時の --max-model-len で決まる。

    options を送ると無視されるだけだが、送らないことを明示しておかないと、
    num_ctx を上げれば効くという誤解が残る。
    """
    _, payload = chat._request("m", [], num_ctx=65536)
    assert "options" not in payload
    assert "keep_alive" not in payload


def test_the_ollama_request_still_sends_num_ctx():
    url, payload = chat._request("m", [], num_ctx=65536, temperature=0.3)
    assert url.endswith("/api/chat")
    assert payload["options"] == {"num_ctx": 65536, "temperature": 0.3}
    assert payload["keep_alive"] == "30m"


def test_ask_text_reads_the_openai_shape(on_vllm):
    session = _FakeSession([_FakeResponse({"choices": [{"message": {"content": "本文"}}]})])
    assert chat.ask_text("m", "prompt", session=session) == "本文"
    url, _ = session.calls[0]
    assert url == backend.chat_url()


def test_tool_replies_are_given_a_call_id(on_vllm):
    """道具の結果を返すメッセージの形が経路で違う。

    Ollama は tool_name、OpenAI 互換は tool_call_id を求める。履歴を組み立てる
    docgen/project.py は Ollama の形で積むので、送る直前に直す。
    """
    messages = [
        {"role": "user", "content": "質問"},
        {
            "role": "assistant",
            "tool_calls": [{"id": "call_1", "function": {"name": "read_files"}}],
        },
        {"role": "tool", "tool_name": "read_files", "content": "本文"},
    ]
    converted = chat._openai_messages(messages)
    assert converted[2] == {
        "role": "tool",
        "content": "本文",
        "tool_call_id": "call_1",
    }
    # 元の履歴は壊さない。呼び出し側が積み続けるものだからである。
    assert messages[2]["tool_name"] == "read_files"


def test_ask_tools_returns_the_ollama_shape(on_vllm):
    """呼び出し側（docgen/project.py）は tool_calls の有無だけを見る。

    思考まで返して履歴へ積み直すと、次の周で文脈を食うだけになる。
    """
    calls = [{"id": "call_1", "function": {"name": "read_files", "arguments": "{}"}}]
    session = _FakeSession(
        [
            _FakeResponse(
                {
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": None,
                                "reasoning_content": "考えた",
                                "tool_calls": calls,
                            }
                        }
                    ]
                }
            )
        ]
    )
    message = chat.ask_tools("m", [], [], session=session)
    assert message == {"role": "assistant", "content": "", "tool_calls": calls}
    assert "reasoning_content" not in message


def test_the_stream_reads_sse_deltas():
    """ネイティブAPIのNDJSONと違い、こちらは data: が付き delta に入る。"""
    response = _FakeResponse(
        lines=[
            b'data: {"choices": [{"delta": {"content": "\\u3042"}}]}',
            b"",
            b'data: {"choices": [{"delta": {"content": "\\u3044"}}]}',
            b"data: [DONE]",
            b'data: {"choices": [{"delta": {"content": "\\u3046"}}]}',
        ]
    )
    assert list(chat._stream_sse(response)) == ["あ", "い"]


def test_the_stream_raises_on_an_error_chunk():
    response = _FakeResponse(lines=['data: {"error": "こわれた"}'.encode("utf-8")])
    with pytest.raises(chat.ChatError, match="こわれた"):
        list(chat._stream_sse(response))


# --- 埋め込み ---------------------------------------------------------------


def test_the_embedding_request_uses_the_openai_endpoint(on_vllm, monkeypatch):
    monkeypatch.setattr(embedder, "EMBED_DIM", 1)
    session = _FakeSession(
        [_FakeResponse({"data": [{"index": 0, "embedding": [0.5]}]})]
    )
    assert embedder.embed_texts(["本文"], session=session) == [[0.5]]
    url, payload = session.calls[0]
    assert url == backend.embed_url()
    # keep_alive は Ollama 固有。
    assert payload == {"model": embedder.EMBED_MODEL, "input": ["本文"]}


def test_queries_and_passages_get_different_prefixes(monkeypatch):
    """接頭辞を付け違えてもエラーにはならず、精度だけが静かに落ちる。"""
    monkeypatch.setattr(embedder, "EMBED_DIM", 1)
    monkeypatch.setattr(embedder, "EMBED_QUERY_PREFIX", "query: ")
    monkeypatch.setattr(embedder, "EMBED_PASSAGE_PREFIX", "passage: ")

    session = _FakeSession([_FakeResponse({"embeddings": [[0.1]]})])
    embedder.embed_texts(["有給休暇の規定"], session=session)
    assert session.calls[0][1]["input"] == ["passage: 有給休暇の規定"]

    session = _FakeSession([_FakeResponse({"embeddings": [[0.1]]})])
    embedder.embed_query("有給休暇は何日", session=session)
    assert session.calls[0][1]["input"] == ["query: 有給休暇は何日"]


def test_no_prefix_is_added_by_default(monkeypatch):
    """bge-m3 は接頭辞を要らない。既定で何も足さないこと。"""
    monkeypatch.setattr(embedder, "EMBED_DIM", 1)
    session = _FakeSession([_FakeResponse({"embeddings": [[0.1]]})])
    embedder.embed_texts(["本文"], session=session)
    assert session.calls[0][1]["input"] == ["本文"]


def test_the_check_looks_at_the_served_model(on_vllm):
    """vLLM は1プロセス1モデル。名前が合わなければ別のモデルを立てている。"""
    session = _FakeSession([_FakeResponse({"data": [{"id": "別のモデル"}]})])
    with pytest.raises(embedder.EmbeddingError, match="EMBED_MODEL"):
        embedder.check_ollama(session=session)
    assert session.calls[0][0] == backend.models_url(backend.VLLM_EMBED_HOST)


def test_the_check_passes_when_the_model_matches(on_vllm):
    session = _FakeSession([_FakeResponse({"data": [{"id": embedder.EMBED_MODEL}]})])
    embedder.check_ollama(session=session)


def test_an_unreachable_vllm_is_reported(on_vllm):
    class _Broken(_FakeSession):
        def get(self, url, timeout=None):
            raise requests.ConnectionError("つながらない")

    with pytest.raises(embedder.EmbeddingError, match="vLLMに接続できません"):
        embedder.check_ollama(session=_Broken([]))


# --- VLM --------------------------------------------------------------------


def test_the_image_is_sent_as_a_data_url(on_vllm):
    """Ollama の images 配列は OpenAI 互換では読まれない。"""
    session = _FakeSession([_FakeResponse({"choices": [{"message": {"content": " 図の説明 "}}]})])
    assert vlm.caption_image(b"PNGDATA", session=session) == "図の説明"

    url, payload = session.calls[0]
    assert url == backend.vlm_url()
    content = payload["messages"][0]["content"]
    assert content[0]["type"] == "text"
    expected = base64.b64encode(b"PNGDATA").decode("ascii")
    assert content[1]["image_url"]["url"] == f"data:image/png;base64,{expected}"
    assert "images" not in payload["messages"][0]


def test_the_ollama_image_shape_is_unchanged():
    session = _FakeSession([_FakeResponse({"message": {"content": "図の説明"}})])
    assert vlm.caption_image(b"PNGDATA", session=session) == "図の説明"
    _, payload = session.calls[0]
    assert payload["messages"][0]["images"] == [
        base64.b64encode(b"PNGDATA").decode("ascii")
    ]
