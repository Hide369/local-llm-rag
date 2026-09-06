import json

import pytest
import requests

from coding_agent.connection import AgentError, AgentSettings, OllamaClient, load_settings


class FakeResponse:
    def __init__(self, status_code=200, payload=None, *, lines=None, stream_error=None):
        self.status_code = status_code
        self._payload = payload
        self._lines = list(lines or [])
        self._stream_error = stream_error
        self.closed = False

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload

    def iter_lines(self, decode_unicode=False):
        del decode_unicode
        yield from self._lines
        if self._stream_error is not None:
            raise self._stream_error

    def close(self):
        self.closed = True


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        result = self.responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def write_env(project, host="https://example.ngrok-free.app", api_key="private-test-key"):
    (project / ".env").write_text(
        f"OLLAMA_HOST={host}\nOLLAMA_API_KEY={api_key}\n", encoding="utf-8"
    )


def sse(event_type, **data):
    payload = {"type": event_type, **data}
    return [
        f"event: {event_type}".encode(),
        f"data: {json.dumps(payload)}".encode(),
        b"",
    ]


def test_missing_env_is_actionable(tmp_path):
    with pytest.raises(AgentError, match=r"\.env"):
        load_settings(tmp_path)


def test_settings_hide_api_key():
    settings = AgentSettings("https://example.ngrok-free.app", "private-test-key")
    assert "private-test-key" not in repr(settings)


@pytest.mark.parametrize(
    "host",
    [
        "http://example.test",
        "https://",
        "https://user@example.test",
        "https://example.test/path",
        "https://example.test?key=value",
        "https://example.test/#fragment",
    ],
)
def test_load_settings_rejects_non_root_https_urls(tmp_path, host):
    write_env(tmp_path, host=host)
    with pytest.raises(AgentError, match="OLLAMA_HOST"):
        load_settings(tmp_path)


@pytest.mark.parametrize("api_key", ["", "   ", "abc def", "café"])
def test_load_settings_rejects_invalid_api_keys(tmp_path, api_key):
    write_env(tmp_path, api_key=api_key)
    with pytest.raises(AgentError, match="OLLAMA_API_KEY"):
        load_settings(tmp_path)


def test_load_settings_rejects_multiline_api_key(tmp_path):
    (tmp_path / ".env").write_text(
        'OLLAMA_HOST=https://example.test\nOLLAMA_API_KEY="first\\nsecond"\n',
        encoding="utf-8",
    )
    with pytest.raises(AgentError, match="OLLAMA_API_KEY"):
        load_settings(tmp_path)


@pytest.mark.parametrize("context_size", [0, 16384, 131072, True])
def test_load_settings_allows_only_supported_context_sizes(tmp_path, context_size):
    write_env(tmp_path)
    with pytest.raises(AgentError, match="context"):
        load_settings(tmp_path, context_size=context_size)


@pytest.mark.parametrize("context_size", [{}, []])
def test_load_settings_rejects_unhashable_context_sizes(tmp_path, context_size):
    write_env(tmp_path)
    with pytest.raises(AgentError, match="context"):
        load_settings(tmp_path, context_size=context_size)


def test_load_settings_normalizes_root_slash_and_ignores_process_environment(
    tmp_path, monkeypatch
):
    write_env(tmp_path, host="https://example.test/", api_key="file-key")
    monkeypatch.setenv("OLLAMA_HOST", "https://wrong.example")
    monkeypatch.setenv("OLLAMA_API_KEY", "wrong-key")

    settings = load_settings(tmp_path, context_size=32768)

    assert settings.host == "https://example.test"
    assert settings.api_key == "file-key"
    assert settings.model == "gpt-oss:20b"
    assert settings.context_size == 32768


def test_request_adds_auth_timeout_and_disables_redirects():
    response = FakeResponse(payload={"version": "0.33.3"})
    session = FakeSession([response])
    client = OllamaClient(
        AgentSettings("https://example.test", "secret-key"), session=session
    )

    assert client.request("GET", "/api/version", timeout=(2, 7)) == {
        "version": "0.33.3"
    }

    method, url, kwargs = session.calls[0]
    assert (method, url) == ("GET", "https://example.test/api/version")
    assert kwargs["headers"] == {"X-API-Key": "secret-key"}
    assert kwargs["timeout"] == (2, 7)
    assert kwargs["allow_redirects"] is False
    assert response.closed is True


@pytest.mark.parametrize("status", [301, 401, 404, 500])
def test_request_http_errors_do_not_leak_response_or_endpoint(status):
    host = "https://private-tunnel.example"
    key = "private-key"
    response = FakeResponse(status_code=status, payload={"detail": f"{host} {key}"})
    client = OllamaClient(AgentSettings(host, key), session=FakeSession([response]))

    with pytest.raises(AgentError) as caught:
        client.request("GET", "/api/version")

    message = str(caught.value)
    assert str(status) in message
    assert host not in message
    assert key not in message
    assert "detail" not in message
    assert response.closed is True


@pytest.mark.parametrize("status", [True, 0, 600, "200"])
def test_request_rejects_invalid_http_status_and_closes_response(status):
    response = FakeResponse(status_code=status, payload={"version": "private"})
    client = OllamaClient(
        AgentSettings("https://example.test", "private-key"),
        session=FakeSession([response]),
    )

    with pytest.raises(AgentError, match="unexpected HTTP status"):
        client.request("GET", "/api/version")

    assert response.closed is True


@pytest.mark.parametrize(
    "error",
    [
        requests.Timeout("https://private.example private-key"),
        requests.ConnectionError("https://private.example private-key"),
    ],
)
def test_request_transport_errors_do_not_leak_exception_text(error):
    client = OllamaClient(
        AgentSettings("https://private.example", "private-key"),
        session=FakeSession([error]),
    )

    with pytest.raises(AgentError) as caught:
        client.request("GET", "/api/version")

    assert "private.example" not in str(caught.value)
    assert "private-key" not in str(caught.value)


def test_request_rejects_invalid_json_and_non_object_json():
    client = OllamaClient(
        AgentSettings("https://example.test", "key"),
        session=FakeSession(
            [FakeResponse(payload=ValueError("secret")), FakeResponse(payload=[])]
        ),
    )

    with pytest.raises(AgentError, match="JSON"):
        client.request("GET", "/api/version")
    with pytest.raises(AgentError, match="schema"):
        client.request("GET", "/api/version")


def test_inspect_returns_only_safe_structured_diagnostics():
    secret = "must-not-escape"
    session = FakeSession(
        [
            FakeResponse(payload={"version": "0.33.3", "secret": secret}),
            FakeResponse(
                payload={
                    "capabilities": ["completion", "tools", "thinking"],
                    "model_info": {"private": secret},
                }
            ),
            FakeResponse(
                payload={
                    "models": [
                        {
                            "name": "gpt-oss:20b",
                            "context_length": 65536,
                            "size": 13_000,
                            "size_vram": 13_000,
                            "digest": secret,
                        }
                    ]
                }
            ),
        ]
    )

    result = OllamaClient(
        AgentSettings("https://example.test", secret), session=session
    ).inspect()

    assert result == {
        "version": "0.33.3",
        "model": "gpt-oss:20b",
        "capabilities": ["completion", "tools", "thinking"],
        "tools": True,
        "loaded": True,
        "context_length": 65536,
        "size": 13_000,
        "size_vram": 13_000,
        "fully_on_gpu": True,
    }
    assert secret not in repr(result)


def test_inspect_rejects_unexpected_schema_without_leaking_values():
    session = FakeSession(
        [
            FakeResponse(payload={"version": "0.33.3"}),
            FakeResponse(payload={"capabilities": "private-key"}),
        ]
    )
    client = OllamaClient(
        AgentSettings("https://example.test", "private-key"), session=session
    )

    with pytest.raises(AgentError) as caught:
        client.inspect()

    assert "schema" in str(caught.value)
    assert "private-key" not in str(caught.value)


def test_configure_context_copies_backup_once_then_recreates_original_tag():
    session = FakeSession(
        [
            FakeResponse(payload={"models": [{"name": "gpt-oss:20b"}]}),
            FakeResponse(payload=ValueError("copy has no JSON body")),
            FakeResponse(payload={"status": "success"}),
        ]
    )
    client = OllamaClient(
        AgentSettings("https://example.test", "key", context_size=65536),
        session=session,
    )

    assert client.configure_context() == {
        "model": "gpt-oss:20b",
        "backup_model": "gpt-oss:20b-before-coding-agent",
        "backup_created": True,
        "context_size": 65536,
    }

    assert session.calls[1][1].endswith("/api/copy")
    assert session.calls[1][2]["json"] == {
        "source": "gpt-oss:20b",
        "destination": "gpt-oss:20b-before-coding-agent",
    }
    assert session.calls[2][1].endswith("/api/create")
    assert session.calls[2][2]["json"] == {
        "model": "gpt-oss:20b",
        "from": "gpt-oss:20b",
        "parameters": {"num_ctx": 65536},
        "stream": False,
    }


def test_configure_context_does_not_overwrite_existing_backup():
    session = FakeSession(
        [
            FakeResponse(
                payload={
                    "models": [
                        {"name": "gpt-oss:20b"},
                        {"name": "gpt-oss:20b-before-coding-agent"},
                    ]
                }
            ),
            FakeResponse(payload={"status": "success"}),
        ]
    )

    result = OllamaClient(
        AgentSettings("https://example.test", "key"), session=session
    ).configure_context()

    assert result["backup_created"] is False
    assert [call[1] for call in session.calls] == [
        "https://example.test/api/tags",
        "https://example.test/api/create",
    ]


def test_restore_context_recreates_model_from_backup():
    session = FakeSession(
        [
            FakeResponse(
                payload={
                    "models": [
                        {"name": "gpt-oss:20b"},
                        {"name": "gpt-oss:20b-before-coding-agent"},
                    ]
                }
            ),
            FakeResponse(payload={"status": "success"}),
        ]
    )

    result = OllamaClient(
        AgentSettings("https://example.test", "key"), session=session
    ).restore_context()

    assert result == {
        "model": "gpt-oss:20b",
        "restored_from": "gpt-oss:20b-before-coding-agent",
    }
    assert session.calls[1][1].endswith("/api/create")
    assert session.calls[1][2]["json"] == {
        "model": "gpt-oss:20b",
        "from": "gpt-oss:20b-before-coding-agent",
        "stream": False,
    }


def test_restore_context_requires_backup():
    client = OllamaClient(
        AgentSettings("https://example.test", "key"),
        session=FakeSession(
            [FakeResponse(payload={"models": [{"name": "gpt-oss:20b"}]})]
        ),
    )

    with pytest.raises(AgentError, match="backup"):
        client.restore_context()


def test_warmup_reports_actual_context_and_gpu_allocation():
    session = FakeSession(
        [
            FakeResponse(payload={"response": "", "done": True}),
            FakeResponse(
                payload={
                    "models": [
                        {
                            "name": "gpt-oss:20b",
                            "context_length": 32768,
                            "size": 13_000,
                            "size_vram": 12_000,
                        }
                    ]
                }
            ),
        ]
    )

    result = OllamaClient(
        AgentSettings("https://example.test", "key", context_size=65536),
        session=session,
    ).warmup()

    assert session.calls[0][2]["json"] == {
        "model": "gpt-oss:20b",
        "prompt": "",
        "options": {"num_ctx": 65536},
        "keep_alive": "30m",
        "stream": False,
    }
    assert result == {
        "model": "gpt-oss:20b",
        "requested_context_length": 65536,
        "context_length": 32768,
        "size": 13_000,
        "size_vram": 12_000,
        "fully_on_gpu": False,
    }


def test_warmup_fails_when_requested_model_is_not_loaded():
    session = FakeSession(
        [
            FakeResponse(payload={"done": True}),
            FakeResponse(payload={"models": []}),
        ]
    )
    client = OllamaClient(
        AgentSettings("https://example.test", "key"), session=session
    )

    with pytest.raises(AgentError, match="loaded model"):
        client.warmup()


def test_probe_tools_executes_function_and_returns_its_result_to_model():
    completed_output = [
        {"id": "reason_1", "type": "reasoning", "summary": []},
        {
            "id": "item_1",
            "type": "function_call",
            "name": "get_probe_value",
            "call_id": "call_1",
            "arguments": "{}",
            "status": "completed",
        },
    ]
    first_lines = [
        *sse("response.created", response={"id": "resp_1"}),
        *sse(
            "response.output_item.added",
            item={
                "type": "function_call",
                "name": "get_probe_value",
                "call_id": "call_1",
                "arguments": "",
            },
        ),
        *sse("response.function_call_arguments.delta", delta="{}"),
        *sse("response.function_call_arguments.done", arguments="{}"),
        *sse("response.output_item.done", item=completed_output[1]),
        *sse(
            "response.completed",
            response={
                "id": "resp_1",
                "status": "completed",
                "output": completed_output,
            },
        ),
    ]
    second_lines = [
        *sse("response.output_text.delta", delta="7319"),
        *sse("response.output_text.delta", delta="0462"),
        *sse("response.completed", response={"id": "resp_2", "status": "completed"}),
    ]
    session = FakeSession(
        [FakeResponse(lines=first_lines), FakeResponse(lines=second_lines)]
    )

    result = OllamaClient(
        AgentSettings("https://example.test", "key"), session=session
    ).probe_tools()

    assert result == {
        "tool_name": "get_probe_value",
        "tool_call_id": "call_1",
        "result": "73190462",
        "completed": True,
    }
    second_payload = session.calls[1][2]["json"]
    assert "tool_choice" not in session.calls[0][2]["json"]
    assert "previous_response_id" not in second_payload
    assert second_payload["input"] == [
        *completed_output,
        {
            "type": "function_call_output",
            "call_id": "call_1",
            "output": "73190462",
        }
    ]
    for _, url, kwargs in session.calls:
        assert url == "https://example.test/v1/responses"
        assert kwargs["stream"] is True
        assert kwargs["allow_redirects"] is False
        assert kwargs["timeout"] == (5, 60)


def test_probe_tools_requires_completed_event():
    lines = [
        *sse("response.created", response={"id": "resp_1"}),
        *sse(
            "response.output_item.added",
            item={
                "type": "function_call",
                "name": "get_probe_value",
                "call_id": "call_1",
                "arguments": "{}",
            },
        ),
    ]
    client = OllamaClient(
        AgentSettings("https://example.test", "key"),
        session=FakeSession([FakeResponse(lines=lines)]),
    )

    with pytest.raises(AgentError, match="completed"):
        client.probe_tools()


def test_probe_tools_caps_stream_content():
    oversized = b"data: " + (b"x" * 1_100_000)
    client = OllamaClient(
        AgentSettings("https://example.test", "key"),
        session=FakeSession([FakeResponse(lines=[oversized])]),
    )

    with pytest.raises(AgentError, match="limit"):
        client.probe_tools()


def test_probe_tools_sanitizes_disconnect_during_stream_and_closes_response():
    response = FakeResponse(
        stream_error=requests.ConnectionError(
            "https://private.example coding-agent-secret-key"
        )
    )
    client = OllamaClient(
        AgentSettings("https://private.example", "coding-agent-secret-key"),
        session=FakeSession([response]),
    )

    with pytest.raises(AgentError) as caught:
        client.probe_tools()

    assert "private.example" not in str(caught.value)
    assert "coding-agent-secret-key" not in str(caught.value)
    assert response.closed is True
