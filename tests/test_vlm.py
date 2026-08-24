import base64

import pytest
import requests

import ingest.vlm as vlm
from ingest.vlm import VLM_MODEL, VlmError, caption_image


class _FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"status {self.status_code}")

    def json(self):
        return self._payload


class _FakeSession:
    """POSTされたペイロードを記録し、あらかじめ決めた応答を返す。"""

    def __init__(self, responses):
        self._responses = list(responses)
        self.payloads = []

    def post(self, url, json, timeout):
        self.payloads.append(json)
        result = self._responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    def get(self, url, timeout):
        result = self._responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def _reply(text):
    return _FakeResponse({"message": {"content": text}})


def test_sends_image_as_base64_to_the_configured_model():
    session = _FakeSession([_reply("赤い四角形の画像です。")])
    result = caption_image(b"fake-image-bytes", session=session)
    assert result == "赤い四角形の画像です。"
    payload = session.payloads[0]
    assert payload["model"] == VLM_MODEL
    assert payload["messages"][0]["images"] == [
        base64.b64encode(b"fake-image-bytes").decode("ascii")
    ]


def test_strips_surrounding_whitespace():
    session = _FakeSession([_reply("  説明文  \n")])
    assert caption_image(b"x", session=session) == "説明文"


def test_retries_then_succeeds(monkeypatch):
    monkeypatch.setattr(vlm.time, "sleep", lambda _s: None)
    session = _FakeSession([requests.ConnectionError("boom"), _reply("説明")])
    assert caption_image(b"x", session=session) == "説明"


def test_backoff_is_exponential(monkeypatch):
    waits = []
    monkeypatch.setattr(vlm.time, "sleep", waits.append)
    session = _FakeSession(
        [requests.ConnectionError("x"), requests.ConnectionError("x"), _reply("説明")]
    )
    caption_image(b"x", session=session)
    assert waits == [1, 2]


def test_gives_up_after_all_attempts(monkeypatch):
    monkeypatch.setattr(vlm.time, "sleep", lambda _s: None)
    session = _FakeSession([requests.ConnectionError("x")] * 4)
    with pytest.raises(VlmError):
        caption_image(b"x", session=session)


def test_check_vlm_raises_when_unreachable():
    session = _FakeSession([requests.ConnectionError("refused")])
    with pytest.raises(VlmError, match="Ollama"):
        vlm.check_vlm(session=session)


def test_check_vlm_passes_when_model_present():
    session = _FakeSession([_FakeResponse({"models": [{"name": VLM_MODEL}]})])
    vlm.check_vlm(session=session)


def test_check_vlm_raises_when_model_missing():
    session = _FakeSession([_FakeResponse({"models": [{"name": "bge-m3:latest"}]})])
    with pytest.raises(VlmError, match=VLM_MODEL.split(":")[0]):
        vlm.check_vlm(session=session)
