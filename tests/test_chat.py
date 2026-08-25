import json as json_module

import pytest
import requests

import ingest.chat as chat
from ingest.chat import NUM_CTX, ChatError, ask_json, stream_chat


class _FakeResponse:
    def __init__(self, payload=None, lines=None, status=200):
        self._payload = payload
        self._lines = lines or []
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"status {self.status_code}")

    def json(self):
        return self._payload

    def iter_lines(self):
        return iter(self._lines)


class _FakeSession:
    """POSTされたペイロードを記録し、あらかじめ決めた応答を返す（tests/test_vlm.pyと同じ形）。"""

    def __init__(self, responses):
        self._responses = list(responses)
        self.payloads = []

    def post(self, url, json, timeout=None, stream=None):
        self.payloads.append(json)
        result = self._responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def _reply(text):
    return _FakeResponse({"message": {"content": text}})


def _ndjson(*objs):
    """ネイティブAPIのストリームはSSEではなくNDJSON（1行1JSON）。"""
    return [json_module.dumps(obj).encode("utf-8") for obj in objs]


def test_ask_json_requests_json_format_and_temperature_zero():
    """条件抽出は再現性が要るのでtemperature=0固定。JSON以外を返されると困るのでformat=jsonも固定。"""
    session = _FakeSession([_reply('{"a": 1}')])
    result = ask_json("qwen2.5:7b-instruct", "prompt", session=session)
    assert result == '{"a": 1}'
    payload = session.payloads[0]
    assert payload["model"] == "qwen2.5:7b-instruct"
    assert payload["format"] == "json"
    assert payload["stream"] is False
    assert payload["options"]["temperature"] == 0
    assert payload["options"]["num_ctx"] == NUM_CTX


def test_ask_json_retries_then_succeeds(monkeypatch):
    monkeypatch.setattr(chat.time, "sleep", lambda _s: None)
    session = _FakeSession([requests.ConnectionError("boom"), _reply('{"ok": true}')])
    assert ask_json("m", "p", session=session) == '{"ok": true}'


def test_ask_json_gives_up_after_all_attempts(monkeypatch):
    monkeypatch.setattr(chat.time, "sleep", lambda _s: None)
    session = _FakeSession([requests.ConnectionError("x")] * 4)
    with pytest.raises(ChatError):
        ask_json("m", "p", session=session)


def test_stream_chat_yields_content_pieces_in_order():
    session = _FakeSession(
        [
            _FakeResponse(
                lines=_ndjson(
                    {"message": {"content": "こん"}, "done": False},
                    {"message": {"content": "にちは"}, "done": False},
                    {"message": {"content": ""}, "done": True},
                )
            )
        ]
    )
    result = "".join(
        stream_chat("m", [{"role": "user", "content": "hi"}], 0.3, session=session)
    )
    assert result == "こんにちは"


def test_stream_chat_sends_num_ctx_and_temperature():
    """既定4096ではgpt-oss:20bの思考だけで使い切り、finish_reason=lengthで
    回答が0文字になった実測がある。num_ctxを確実に送ることをここでロックする。
    """
    session = _FakeSession(
        [_FakeResponse(lines=_ndjson({"message": {"content": "x"}, "done": True}))]
    )
    list(stream_chat("m", [{"role": "user", "content": "hi"}], 0.7, session=session))
    payload = session.payloads[0]
    assert payload["stream"] is True
    assert payload["options"]["num_ctx"] == NUM_CTX
    assert payload["options"]["temperature"] == 0.7


def test_stream_chat_raises_when_ollama_reports_an_error_mid_stream():
    session = _FakeSession(
        [
            _FakeResponse(
                lines=_ndjson(
                    {"message": {"content": "途中まで"}, "done": False},
                    {"error": "model not found"},
                )
            )
        ]
    )
    gen = stream_chat("m", [], 0.3, session=session)
    assert next(gen) == "途中まで"
    with pytest.raises(ChatError, match="model not found"):
        next(gen)


def test_stream_chat_raises_when_the_connection_fails():
    session = _FakeSession([requests.ConnectionError("refused")])
    with pytest.raises(ChatError):
        list(stream_chat("m", [], 0.3, session=session))
