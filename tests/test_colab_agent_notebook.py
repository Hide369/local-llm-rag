import asyncio
import json
import os
import sys
import types
from pathlib import Path


NOTEBOOK = Path(__file__).parents[1] / "colab" / "run_ollama_server.ipynb"


def _notebook():
    return json.loads(NOTEBOOK.read_text(encoding="utf-8"))


def _code_cell(prefix):
    for cell in _notebook()["cells"]:
        source = "".join(cell.get("source", []))
        if cell["cell_type"] == "code" and source.startswith(prefix):
            return source
    raise AssertionError(f"code cell not found: {prefix}")


def test_ollama_starts_with_copied_environment_and_coding_context(monkeypatch):
    popen_calls = []

    class Completed:
        returncode = 0
        stdout = "NVIDIA L4, 23034 MiB\n"
        stderr = ""

    fake_subprocess = types.ModuleType("subprocess")
    fake_subprocess.DEVNULL = object()
    fake_subprocess.Popen = lambda *args, **kwargs: popen_calls.append((args, kwargs))
    fake_subprocess.run = lambda *args, **kwargs: Completed()

    fake_requests = types.ModuleType("requests")
    fake_requests.RequestException = RuntimeError
    fake_requests.get = lambda *args, **kwargs: types.SimpleNamespace(status_code=200)

    monkeypatch.setitem(sys.modules, "subprocess", fake_subprocess)
    monkeypatch.setitem(sys.modules, "requests", fake_requests)
    monkeypatch.setenv("PRESERVED_FOR_OLLAMA", "yes")

    namespace = {}
    exec(compile(_code_cell("# 2."), "ollama-start-cell", "exec"), namespace)

    _, kwargs = popen_calls[0]
    assert kwargs["env"]["PRESERVED_FOR_OLLAMA"] == "yes"
    assert kwargs["env"]["OLLAMA_CONTEXT_LENGTH"] == "65536"
    assert kwargs["env"]["OLLAMA_NUM_PARALLEL"] == "1"


def _install_proxy_fakes(monkeypatch, upstreams):
    httpx = types.ModuleType("httpx")

    class RequestError(Exception):
        pass

    class TimeoutException(RequestError):
        pass

    class Timeout:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    class AsyncClient:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def build_request(self, method, path, **kwargs):
            return types.SimpleNamespace(method=method, path=path, **kwargs)

        async def send(self, request, stream=False):
            assert stream is True
            result = upstreams.pop(0)
            if isinstance(result, BaseException):
                raise result
            result.request = request
            return result

    httpx.Timeout = Timeout
    httpx.RequestError = RequestError
    httpx.TimeoutException = TimeoutException
    httpx.AsyncClient = AsyncClient

    fastapi = types.ModuleType("fastapi")

    class FastAPI:
        def api_route(self, path, methods):
            def register(function):
                self.route = (path, methods, function)
                return function

            return register

    fastapi.FastAPI = FastAPI
    fastapi.Request = object

    responses = types.ModuleType("fastapi.responses")

    class JSONResponse:
        def __init__(self, body, status_code):
            self.body = body
            self.status_code = status_code

    class StreamingResponse:
        def __init__(self, body_iterator, status_code, headers):
            self.body_iterator = body_iterator
            self.status_code = status_code
            self.headers = headers

    responses.JSONResponse = JSONResponse
    responses.StreamingResponse = StreamingResponse

    monkeypatch.setitem(sys.modules, "httpx", httpx)
    monkeypatch.setitem(sys.modules, "fastapi", fastapi)
    monkeypatch.setitem(sys.modules, "fastapi.responses", responses)


def test_proxy_reads_key_at_runtime_streams_rag_routes_and_closes_upstream(
    tmp_path, monkeypatch
):
    secret = "runtime-only-secret"
    import secrets

    monkeypatch.delenv("OLLAMA_PROXY_API_KEY", raising=False)
    monkeypatch.setattr(secrets, "token_urlsafe", lambda length: secret)
    monkeypatch.chdir(tmp_path)

    namespace = {}
    exec(compile(_code_cell("# 5."), "proxy-key-cell", "exec"), namespace)
    assert os.environ["OLLAMA_PROXY_API_KEY"] == secret
    exec(compile(_code_cell("# 6."), "proxy-generator-cell", "exec"), namespace)
    proxy_source = (tmp_path / "ollama_proxy.py").read_text(encoding="utf-8")
    assert secret not in proxy_source

    class Upstream:
        status_code = 200
        headers = {"content-type": "text/event-stream", "connection": "keep-alive"}

        def __init__(self, chunks, error=None):
            self.chunks = chunks
            self.error = error
            self.closed = False

        async def aiter_raw(self):
            for chunk in self.chunks:
                yield chunk
            if self.error:
                raise self.error

        async def aclose(self):
            self.closed = True

    upstreams = [
        Upstream([b'event: message\ndata: {"ok":true}\n\n']),
        Upstream([b'{"embedding":[]}']),
        Upstream([], RuntimeError("stream interrupted")),
    ]
    _install_proxy_fakes(monkeypatch, upstreams)

    module = types.ModuleType("ollama_proxy")
    exec(compile(proxy_source, "ollama_proxy.py", "exec"), module.__dict__)
    timeout = module._client.kwargs["timeout"]
    assert timeout is not None
    assert timeout.kwargs["connect"] > 0
    assert timeout.kwargs["read"] > 0

    class Request:
        method = "POST"
        query_params = {}
        headers = {"x-api-key": secret, "content-type": "application/json"}

        async def body(self):
            return b"{}"

    async def exercise():
        responses = []
        used = []
        for path in ("v1/responses", "api/embed"):
            upstream = upstreams[0]
            response = await module.proxy(path, Request())
            responses.append(b"".join([chunk async for chunk in response.body_iterator]))
            used.append(upstream)

        failing = upstreams[0]
        response = await module.proxy("v1/chat/completions", Request())
        try:
            _ = [chunk async for chunk in response.body_iterator]
        except RuntimeError as error:
            assert str(error) == "stream interrupted"
        else:
            raise AssertionError("upstream stream failure was swallowed")
        return responses, used, failing

    responses, used, failing = asyncio.run(exercise())
    assert responses[0].startswith(b"event: message")
    assert responses[1] == b'{"embedding":[]}'
    assert all(upstream.closed for upstream in [*used, failing])
    assert used[0].request.path == "/v1/responses"
    assert used[1].request.path == "/api/embed"


def test_proxy_rejects_missing_and_invalid_keys_without_forwarding(tmp_path, monkeypatch):
    secret = "test-runtime-key"
    monkeypatch.setenv("OLLAMA_PROXY_API_KEY", secret)
    monkeypatch.chdir(tmp_path)
    exec(compile(_code_cell("# 6."), "proxy-generator-cell", "exec"), {})
    proxy_source = (tmp_path / "ollama_proxy.py").read_text(encoding="utf-8")

    upstreams = []
    _install_proxy_fakes(monkeypatch, upstreams)
    module = types.ModuleType("ollama_proxy")
    exec(compile(proxy_source, "ollama_proxy.py", "exec"), module.__dict__)

    class Request:
        method = "POST"
        query_params = {}

        def __init__(self, headers):
            self.headers = headers

        async def body(self):
            raise AssertionError("unauthorized request body must not be read")

    async def exercise():
        return (
            await module.proxy("v1/responses", Request({})),
            await module.proxy(
                "api/embed", Request({"x-api-key": "incorrect-key"})
            ),
        )

    missing, invalid = asyncio.run(exercise())
    assert missing.status_code == invalid.status_code == 401
    assert upstreams == []
    assert secret not in json.dumps([missing.body, invalid.body])


def test_proxy_maps_upstream_connection_and_timeout_errors(tmp_path, monkeypatch):
    monkeypatch.setenv("OLLAMA_PROXY_API_KEY", "test-runtime-key")
    monkeypatch.chdir(tmp_path)
    exec(compile(_code_cell("# 6."), "proxy-generator-cell", "exec"), {})
    proxy_source = (tmp_path / "ollama_proxy.py").read_text(encoding="utf-8")

    upstreams = []
    _install_proxy_fakes(monkeypatch, upstreams)
    module = types.ModuleType("ollama_proxy")
    exec(compile(proxy_source, "ollama_proxy.py", "exec"), module.__dict__)
    upstreams.extend(
        [
            module.httpx.TimeoutException("read timed out"),
            module.httpx.RequestError("connection refused"),
        ]
    )

    class Request:
        method = "POST"
        query_params = {}
        headers = {
            "x-api-key": "test-runtime-key",
            "content-type": "application/json",
        }

        async def body(self):
            return b"{}"

    async def exercise():
        return (
            await module.proxy("v1/responses", Request()),
            await module.proxy("api/embed", Request()),
        )

    timeout, connection = asyncio.run(exercise())
    assert timeout.status_code == 504
    assert timeout.body == {"error": "Ollama upstream timed out"}
    assert connection.status_code == 502
    assert connection.body == {"error": "Unable to reach Ollama upstream"}
    assert "test-runtime-key" not in json.dumps([timeout.body, connection.body])


def test_notebook_has_no_saved_execution_data_or_user_metadata():
    notebook = _notebook()

    for cell in notebook["cells"]:
        if cell["cell_type"] == "code":
            assert cell.get("execution_count") is None
            assert cell.get("outputs") == []

        pending = [cell.get("metadata", {})]
        while pending:
            value = pending.pop()
            if isinstance(value, dict):
                assert "executionInfo" not in value
                assert "user" not in value
                pending.extend(value.values())
            elif isinstance(value, list):
                pending.extend(value)
