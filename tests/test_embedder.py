import pytest
import requests

import ingest.embedder as embedder
from ingest.embedder import (
    DEFAULT_OLLAMA_HOST,
    EMBED_BATCH_SIZE,
    EMBED_DIM,
    EMBED_MODEL,
    EmbeddingError,
    check_ollama,
    embed_query,
    embed_texts,
)


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


def _vectors(count):
    return _FakeResponse({"embeddings": [[0.1] * EMBED_DIM for _ in range(count)]})


def test_host_never_uses_localhost():
    """Windowsでは localhost 解決に約2.1秒かかる。127.0.0.1 なら約80ms。

    OLLAMA_HOST ではなく既定値を検査する。前者は環境変数で上書きされるため、
    実行環境によってテスト結果が変わってしまう。
    """
    assert "localhost" not in DEFAULT_OLLAMA_HOST
    assert "127.0.0.1" in DEFAULT_OLLAMA_HOST


def test_default_port_matches_ollamas_own_default():
    """Ollamaはインストール直後 11434 で待ち受ける。既定値をそこに合わせておかないと、
    環境変数を設定し忘れた利用者が全員「接続できません」で詰まる。"""
    assert DEFAULT_OLLAMA_HOST == "http://127.0.0.1:11434"


def test_uses_bge_m3(monkeypatch):
    session = _FakeSession([_vectors(1)])
    embed_texts(["本文"], session=session)
    assert session.payloads[0]["model"] == EMBED_MODEL == "bge-m3"


def test_batches_are_capped_at_eight():
    """batch=32は1件あたり1,417ms、batch=8は1,197ms。大きすぎるバッチは不利。"""
    assert EMBED_BATCH_SIZE == 8
    session = _FakeSession([_vectors(8), _vectors(8), _vectors(4)])
    result = embed_texts([f"本文{i}" for i in range(20)], session=session)
    assert [len(p["input"]) for p in session.payloads] == [8, 8, 4]
    assert len(result) == 20


def test_empty_input_makes_no_request():
    session = _FakeSession([])
    assert embed_texts([], session=session) == []
    assert session.payloads == []


def test_retries_then_succeeds(monkeypatch):
    monkeypatch.setattr(embedder.time, "sleep", lambda _s: None)
    session = _FakeSession([requests.ConnectionError("boom"), _vectors(1)])
    assert len(embed_texts(["本文"], session=session)) == 1


def test_backoff_is_exponential(monkeypatch):
    waits = []
    monkeypatch.setattr(embedder.time, "sleep", waits.append)
    session = _FakeSession(
        [requests.ConnectionError("x"), requests.ConnectionError("x"), _vectors(1)]
    )
    embed_texts(["本文"], session=session)
    assert waits == [1, 2]


def test_gives_up_after_all_attempts(monkeypatch):
    monkeypatch.setattr(embedder.time, "sleep", lambda _s: None)
    session = _FakeSession([requests.ConnectionError("x")] * 4)
    with pytest.raises(EmbeddingError):
        embed_texts(["本文"], session=session)


def test_wrong_dimension_is_rejected():
    """モデルを取り違えると次元が変わり、DBに入れてから壊れていることに気付く。"""
    session = _FakeSession([_FakeResponse({"embeddings": [[0.1] * 768]})])
    with pytest.raises(EmbeddingError):
        embed_texts(["本文"], session=session)


def test_embed_query_returns_a_single_vector():
    session = _FakeSession([_vectors(1)])
    assert len(embed_query("質問", session=session)) == EMBED_DIM


def test_check_ollama_raises_when_unreachable():
    session = _FakeSession([requests.ConnectionError("refused")])
    with pytest.raises(EmbeddingError, match="Ollama"):
        check_ollama(session=session)


def test_check_ollama_passes_when_model_present():
    session = _FakeSession([_FakeResponse({"models": [{"name": "bge-m3:latest"}]})])
    check_ollama(session=session)


def test_check_ollama_raises_when_model_missing():
    session = _FakeSession([_FakeResponse({"models": [{"name": "llama3.1:8b"}]})])
    with pytest.raises(EmbeddingError, match="bge-m3"):
        check_ollama(session=session)


def test_new_session_has_no_api_key_header_by_default(monkeypatch):
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
    session = embedder.new_session()
    assert "X-API-Key" not in session.headers


def test_new_session_adds_api_key_header_when_set(monkeypatch):
    """Colab側のリバースプロキシがこのヘッダーでリクエストを認証する。"""
    monkeypatch.setenv("OLLAMA_API_KEY", "secret123")
    session = embedder.new_session()
    assert session.headers["X-API-Key"] == "secret123"
