"""Ollamaに安全に接続し、実行条件を診断する。

接続先は2種類ある。**外にあるもの（ColabのL4をngrokで公開したものなど）と、
社内LANにあるもの（GB10など）である。** 前者は通信が社外を通るのでHTTPSと
APIキーを必須にする。後者は経路が社内で閉じるため、平文のHTTPと認証なしを許す。
この線引きは _validate_host と _validate_api_key が持つ。
"""

from __future__ import annotations

import ipaddress
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import requests
from dotenv import dotenv_values


# 既定のモデル。これ以外も指定できる（--model）。かつてはこの値以外を弾いて
# いたが、L4の24GBに載る大きさがこれだけだったからで、128GB級の機械では
# gpt-oss:120b のような大きいモデルを選ぶ理由がある。名前が正しいかどうかは
# ここでは判断できないので、--check が接続先のOllamaに在庫を問い合わせる。
DEFAULT_MODEL = "gpt-oss:20b"
_BACKUP_SUFFIX = "-before-coding-agent"
# 選べる値を並べて固定している。自由入力にしないのは、打ち間違いを --probe の
# 失敗まで持ち越さないためである。大きすぎる値を入れてもOllamaは例外を出さず、
# モデルの一部を黙ってCPUへ落とすだけなので、気づくのが遅れる。
#
# 32768 / 65536 は ColabのL4（24GB）で実配置を確認した値。131072 は 128GB の
# ユニファイドメモリを持つ機械（GB10/DGX Spark など）で選べるように足した。
# **どの機械でも通る値ではない。** 実際に載るかどうかは --probe が確かめる。
# 小さい順に並べること。smaller_context_size() がこの並びに依存する。
SUPPORTED_CONTEXT_SIZES = (32768, 65536, 131072)
_PROBE_TOOL_NAME = "get_probe_value"
_PROBE_VALUE = "73190462"
_MAX_STREAM_BYTES = 1024 * 1024
_MAX_STREAM_SECONDS = 120.0
_STREAM_TIMEOUT = (5, 60)


class AgentError(RuntimeError):
    """利用者が対処できる接続・設定エラー。"""


_HOST_HELP = (
    ".env の OLLAMA_HOST にHTTPSのルートURL、または社内LAN上のホストへの "
    "http://<IPアドレス>:<ポート> を設定してください"
)


def is_local_host(host: str) -> bool:
    """社内で閉じる宛先かどうか。

    平文HTTPと認証なしを許すかどうかの判断に使う。判定はホスト名だけで行い、
    名前解決はしない。解決結果に依存させると、同じ .env が実行環境によって
    通ったり弾かれたりする。
    """
    hostname = urlsplit(host).hostname or ""
    if hostname.endswith(".local"):
        # mDNS の名前は定義上リンクローカルである。DGX Spark の既定のホスト名
        # （spark-xxxx.local）がこれに当たる。
        return True
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return False
    # is_global が False なら、インターネットへ経路を持たないアドレスである。
    # ループバック・RFC1918・リンクローカルに加えて、CGNAT などもここに入る。
    # 個別に列挙するより漏れが無い。
    return not address.is_global


def _validate_host(value: object) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise AgentError(_HOST_HELP)
    if not value.isascii() or any(character.isspace() for character in value):
        raise AgentError(_HOST_HELP)

    try:
        parsed = urlsplit(value)
        # Accessing port also validates malformed or out-of-range port values.
        parsed.port
    except ValueError:
        raise AgentError(_HOST_HELP) from None

    scheme = parsed.scheme.lower()
    if (
        scheme not in ("http", "https")
        or not parsed.netloc
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
    ):
        raise AgentError(_HOST_HELP)

    normalized = urlunsplit((scheme, parsed.netloc, "", "", ""))
    # 平文を許すのは社内で閉じる宛先だけである。外に出る経路で http を許すと、
    # 指示・コード断片・道具の結果がそのまま読まれる。
    if scheme == "http" and not is_local_host(normalized):
        raise AgentError(
            "http は社内LAN上のホスト（ループバック・プライベートIP・.local）に"
            "だけ使えます。外部の宛先には https を指定してください"
        )
    return normalized


def _validate_api_key(value: object, host: str = "") -> str:
    """APIキーを検査する。社内の宛先では未設定を許す。

    ColabのOllamaは X-API-Key を見るリバースプロキシの後ろにあり、キーが無いと
    誰でも叩けてしまう。一方、社内LANのOllamaには通常その認証が無い。無い認証の
    ためにダミーのキーを .env へ書かせるのは、設定を嘘にするだけである。
    """
    if not value and is_local_host(host):
        return ""
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or not value.isascii()
        or any(character.isspace() for character in value)
    ):
        raise AgentError(
            ".env の OLLAMA_API_KEY に空白・改行を含まないASCIIキーを設定してください"
        )
    return value


def _validate_model(value: object) -> str:
    """モデル名を検査する。在庫の有無はここでは分からない。

    打ち間違いは --check（/api/tags の照合）で見つかる。ここで弾けるのは
    「Ollamaのモデル名として形になっていない」ものだけである。
    """
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or not value.isascii()
        or any(character.isspace() for character in value)
    ):
        raise AgentError("model には空白を含まないASCIIのOllamaモデル名を指定してください")
    return value


def _validate_context_size(value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value not in SUPPORTED_CONTEXT_SIZES:
        # 文言を定数から組み立てる。並びを増やしたときに、ここだけ古いまま
        # 残って利用者に嘘を伝えるのを防ぐ。
        allowed = "・".join(str(size) for size in SUPPORTED_CONTEXT_SIZES)
        raise AgentError(f"context_size は{allowed}のいずれかを指定してください")
    return int(value)


def smaller_context_size(value: int) -> int | None:
    """指定より1段小さい対応値を返す。無ければ None。

    --probe がCPU配置を見つけたときに、次に試す値を案内するために使う。
    選べる値の並びを知っているのはこのモジュールだけなので、ここに置く。
    呼び出し側が 32768 のような具体値を書くと、並びを増やしたときに案内が
    ずれる（実際、かつて --probe の文言は 32768 を直に書いていた）。
    """
    smaller = [size for size in SUPPORTED_CONTEXT_SIZES if size < value]
    return max(smaller) if smaller else None


@dataclass(frozen=True)
class AgentSettings:
    host: str
    api_key: str = field(repr=False)
    model: str = DEFAULT_MODEL
    context_size: int = 65536

    def __post_init__(self) -> None:
        # host を先に正規化する。APIキーを必須にするかどうかが宛先で決まるため、
        # 順番を入れ替えると社内の宛先でもキーを要求してしまう。
        object.__setattr__(self, "host", _validate_host(self.host))
        object.__setattr__(self, "api_key", _validate_api_key(self.api_key, self.host))
        object.__setattr__(self, "model", _validate_model(self.model))
        object.__setattr__(self, "context_size", _validate_context_size(self.context_size))


def load_settings(
    project: Path, context_size: int = 65536, model: str | None = None
) -> AgentSettings:
    """プロジェクト直下の.envだけから接続設定を読む。

    モデルは .env ではなく引数で受ける。接続先（.env）と、そこに置いてある
    どのモデルを使うか（CLIの --model、または保存済みのCodex設定）は別の決定
    だからである。同じ .env のまま 20b と 120b を測り比べられる必要がある。
    """

    env_path = Path(project) / ".env"
    if not env_path.is_file():
        raise AgentError(f"プロジェクト直下に .env がありません: {env_path.name}")
    try:
        values = dotenv_values(env_path, interpolate=False, encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise AgentError(".env を読み込めません") from error

    host = _validate_host(values.get("OLLAMA_HOST"))
    return AgentSettings(
        host=host,
        api_key=_validate_api_key(values.get("OLLAMA_API_KEY"), host),
        model=_validate_model(model if model is not None else DEFAULT_MODEL),
        context_size=_validate_context_size(context_size),
    )


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


class OllamaClient:
    def __init__(self, settings: AgentSettings, session=None):
        self.settings = settings
        self.session = session if session is not None else requests.Session()

    @property
    def _headers(self) -> dict[str, str]:
        return {"X-API-Key": self.settings.api_key}

    def _url(self, path: str) -> str:
        parsed = urlsplit(path)
        if (
            not path.startswith("/")
            or path.startswith("//")
            or parsed.scheme
            or parsed.netloc
            or "\r" in path
            or "\n" in path
        ):
            raise AgentError("Ollama API path is invalid")
        return f"{self.settings.host}{path}"

    @staticmethod
    def _raise_http_error(status_code: int) -> None:
        if 300 <= status_code < 400:
            raise AgentError(f"Ollama API redirect rejected (HTTP {status_code})")
        if status_code == 401 or status_code == 403:
            raise AgentError(f"Ollama API authentication failed (HTTP {status_code})")
        if status_code == 404:
            raise AgentError("Ollama API endpoint or model was not found (HTTP 404)")
        if status_code >= 400:
            raise AgentError(f"Ollama API request failed (HTTP {status_code})")

    def _send(self, method: str, path: str, **kwargs):
        try:
            response = self.session.request(
                method,
                self._url(path),
                headers=self._headers,
                allow_redirects=False,
                **kwargs,
            )
        except requests.Timeout:
            raise AgentError("Ollama API request timed out") from None
        except requests.RequestException:
            raise AgentError("Ollama API connection failed") from None
        if (
            isinstance(response.status_code, bool)
            or not isinstance(response.status_code, int)
            or not 100 <= response.status_code <= 599
        ):
            response.close()
            raise AgentError("Ollama API returned an unexpected HTTP status")
        try:
            self._raise_http_error(response.status_code)
        except AgentError:
            response.close()
            raise
        return response

    def request(
        self, method: str, path: str, payload=None, timeout=(5, 60)
    ) -> dict:
        """認証付きJSONリクエストを送り、オブジェクト応答だけを受け入れる。"""

        kwargs: dict[str, Any] = {"timeout": timeout}
        if payload is not None:
            kwargs["json"] = payload
        response = self._send(method, path, **kwargs)
        try:
            try:
                result = response.json()
            except (ValueError, requests.JSONDecodeError):
                raise AgentError("Ollama API returned invalid JSON") from None
            if not isinstance(result, dict):
                raise AgentError("Ollama API returned an unexpected schema")
            return result
        finally:
            response.close()

    def _request_without_body(self, method: str, path: str, payload: dict) -> None:
        """成功時に本文を持たないOllama APIを呼ぶ。"""
        response = self._send(
            method, path, json=payload, timeout=(5, 60)
        )
        response.close()

    @staticmethod
    def _models(payload: dict) -> list[dict]:
        models = payload.get("models")
        if not isinstance(models, list) or not all(
            isinstance(model, dict) for model in models
        ):
            raise AgentError("Ollama API returned an unexpected models schema")
        return models

    def _runtime_model(self, payload: dict, *, required: bool) -> dict | None:
        for model in self._models(payload):
            name = model.get("name", model.get("model"))
            if name == self.settings.model:
                return model
        if required:
            raise AgentError("The requested loaded model was not reported by Ollama")
        return None

    @staticmethod
    def _runtime_fields(model: dict | None) -> dict[str, Any]:
        if model is None:
            return {
                "context_length": None,
                "size": None,
                "size_vram": None,
                "fully_on_gpu": None,
            }
        values: dict[str, int | None] = {}
        for key in ("context_length", "size", "size_vram"):
            value = model.get(key)
            if value is not None and not _is_int(value):
                raise AgentError("Ollama API returned an unexpected runtime schema")
            values[key] = value
        size = values["size"]
        size_vram = values["size_vram"]
        fully_on_gpu = (
            size_vram == size if size is not None and size_vram is not None else None
        )
        return {**values, "fully_on_gpu": fully_on_gpu}

    def inspect(self) -> dict:
        version_payload = self.request("GET", "/api/version")
        version = version_payload.get("version")
        if not isinstance(version, str) or not version:
            raise AgentError("Ollama API returned an unexpected version schema")

        show_payload = self.request(
            "POST", "/api/show", {"model": self.settings.model}
        )
        capabilities = show_payload.get("capabilities")
        if not isinstance(capabilities, list) or not all(
            isinstance(capability, str) for capability in capabilities
        ):
            raise AgentError("Ollama API returned an unexpected model schema")

        ps_payload = self.request("GET", "/api/ps")
        runtime_model = self._runtime_model(ps_payload, required=False)
        return {
            "version": version,
            "model": self.settings.model,
            "capabilities": list(capabilities),
            "tools": "tools" in capabilities,
            "loaded": runtime_model is not None,
            **self._runtime_fields(runtime_model),
        }

    def configure_context(self) -> dict:
        backup_model = f"{self.settings.model}{_BACKUP_SUFFIX}"
        models = self._models(self.request("GET", "/api/tags"))
        names = {model.get("name", model.get("model")) for model in models}
        if self.settings.model not in names:
            raise AgentError("The required Ollama model is not installed")

        backup_created = backup_model not in names
        if backup_created:
            self._request_without_body(
                "POST",
                "/api/copy",
                {"source": self.settings.model, "destination": backup_model},
            )
        self.request(
            "POST",
            "/api/create",
            {
                "model": self.settings.model,
                "from": self.settings.model,
                "parameters": {"num_ctx": self.settings.context_size},
                "stream": False,
            },
            timeout=(5, 600),
        )
        return {
            "model": self.settings.model,
            "backup_model": backup_model,
            "backup_created": backup_created,
            "context_size": self.settings.context_size,
        }

    def restore_context(self) -> dict:
        backup_model = f"{self.settings.model}{_BACKUP_SUFFIX}"
        models = self._models(self.request("GET", "/api/tags"))
        names = {model.get("name", model.get("model")) for model in models}
        if backup_model not in names:
            raise AgentError("The original model backup is not installed")

        self.request(
            "POST",
            "/api/create",
            {
                "model": self.settings.model,
                "from": backup_model,
                "stream": False,
            },
            timeout=(5, 600),
        )
        return {"model": self.settings.model, "restored_from": backup_model}

    def warmup(self) -> dict:
        self.request(
            "POST",
            "/api/generate",
            {
                "model": self.settings.model,
                "prompt": "",
                "options": {"num_ctx": self.settings.context_size},
                "keep_alive": "30m",
                "stream": False,
            },
            timeout=(5, 600),
        )
        model = self._runtime_model(self.request("GET", "/api/ps"), required=True)
        return {
            "model": self.settings.model,
            "requested_context_length": self.settings.context_size,
            **self._runtime_fields(model),
        }

    def _read_sse(self, response) -> list[tuple[str, dict]]:
        started = time.monotonic()
        received = 0
        events: list[tuple[str, dict]] = []
        event_name = ""
        data_lines: list[str] = []

        def finish_event() -> None:
            nonlocal event_name, data_lines
            if not data_lines:
                event_name = ""
                return
            raw_data = "\n".join(data_lines)
            event_name_local = event_name
            event_name = ""
            data_lines = []
            if raw_data == "[DONE]":
                return
            try:
                payload = json.loads(raw_data)
            except (json.JSONDecodeError, TypeError):
                raise AgentError("Responses API returned invalid SSE JSON") from None
            if not isinstance(payload, dict):
                raise AgentError("Responses API returned an unexpected SSE schema")
            payload_type = payload.get("type")
            resolved_type = event_name_local or payload_type
            if not isinstance(resolved_type, str) or not resolved_type:
                raise AgentError("Responses API returned an unexpected SSE schema")
            events.append((resolved_type, payload))

        try:
            for raw_line in response.iter_lines(decode_unicode=False):
                if time.monotonic() - started > _MAX_STREAM_SECONDS:
                    raise AgentError("Responses API stream exceeded its time limit")
                if isinstance(raw_line, bytes):
                    received += len(raw_line)
                    try:
                        line = raw_line.decode("utf-8")
                    except UnicodeDecodeError:
                        raise AgentError("Responses API returned invalid SSE text") from None
                elif isinstance(raw_line, str):
                    received += len(raw_line.encode("utf-8"))
                    line = raw_line
                else:
                    raise AgentError("Responses API returned an unexpected SSE schema")
                if received > _MAX_STREAM_BYTES:
                    raise AgentError("Responses API stream exceeded its content limit")
                if line == "":
                    finish_event()
                elif line.startswith("event:"):
                    event_name = line[6:].strip()
                elif line.startswith("data:"):
                    data_lines.append(line[5:].lstrip())
            finish_event()
        except requests.Timeout:
            raise AgentError("Responses API stream timed out") from None
        except requests.RequestException:
            raise AgentError("Responses API stream disconnected") from None
        finally:
            response.close()
        return events

    def _stream(self, payload: dict) -> list[tuple[str, dict]]:
        response = self._send(
            "POST",
            "/v1/responses",
            json=payload,
            timeout=_STREAM_TIMEOUT,
            stream=True,
        )
        return self._read_sse(response)

    @staticmethod
    def _completed(events: list[tuple[str, dict]]) -> bool:
        return any(event_type == "response.completed" for event_type, _ in events)

    @staticmethod
    def _function_call(events: list[tuple[str, dict]]) -> tuple[str, str, str]:
        calls: dict[str, dict] = {}
        argument_deltas: list[str] = []
        final_arguments = None

        def consider(item: object) -> None:
            if isinstance(item, dict) and item.get("type") == "function_call":
                candidate_id = item.get("call_id")
                if not isinstance(candidate_id, str):
                    raise AgentError("Responses API returned an invalid tool call")
                calls[candidate_id] = item

        for event_type, payload in events:
            if event_type in ("response.output_item.added", "response.output_item.done"):
                consider(payload.get("item"))
            elif event_type == "response.function_call_arguments.delta":
                delta = payload.get("delta")
                if isinstance(delta, str):
                    argument_deltas.append(delta)
            elif event_type == "response.function_call_arguments.done":
                arguments = payload.get("arguments")
                if isinstance(arguments, str):
                    final_arguments = arguments

        if len(calls) != 1:
            raise AgentError("Responses API did not return exactly one probe tool call")
        call_id, item = next(iter(calls.items()))
        call_name = item.get("name")
        initial_arguments = item.get("arguments", "")
        if not isinstance(initial_arguments, str):
            initial_arguments = ""
        arguments = (
            final_arguments
            if final_arguments is not None
            else initial_arguments + "".join(argument_deltas)
        )
        if not isinstance(call_name, str):
            raise AgentError("Responses API did not request the probe tool")
        return call_name, call_id, arguments

    @staticmethod
    def _response_output(events: list[tuple[str, dict]]) -> list[dict]:
        for event_type, payload in events:
            if event_type != "response.completed":
                continue
            response = payload.get("response")
            if not isinstance(response, dict):
                continue
            output = response.get("output")
            if isinstance(output, list) and output and all(
                isinstance(item, dict) for item in output
            ):
                return output

        completed_items = [
            payload["item"]
            for event_type, payload in events
            if event_type == "response.output_item.done"
            and isinstance(payload.get("item"), dict)
        ]
        if completed_items:
            return completed_items
        added_items = [
            payload["item"]
            for event_type, payload in events
            if event_type == "response.output_item.added"
            and isinstance(payload.get("item"), dict)
        ]
        if added_items:
            return added_items
        raise AgentError("Responses API did not return reusable output items")

    @staticmethod
    def _output_text(events: list[tuple[str, dict]]) -> str:
        deltas = [
            payload["delta"]
            for event_type, payload in events
            if event_type == "response.output_text.delta"
            and isinstance(payload.get("delta"), str)
        ]
        if deltas:
            return "".join(deltas)

        for event_type, payload in events:
            if event_type != "response.completed":
                continue
            response = payload.get("response")
            if not isinstance(response, dict):
                continue
            for item in response.get("output", []):
                if not isinstance(item, dict) or item.get("type") != "message":
                    continue
                for content in item.get("content", []):
                    if isinstance(content, dict) and content.get("type") == "output_text":
                        text = content.get("text")
                        if isinstance(text, str):
                            return text
        return ""

    def probe_tools(self) -> dict:
        """固定値を返す関数をResponses API上で往復させる。"""

        first_events = self._stream(
            {
                "model": self.settings.model,
                "input": (
                    "Call get_probe_value exactly once with no arguments. "
                    "Do not answer before calling the tool."
                ),
                "tools": [
                    {
                        "type": "function",
                        "name": _PROBE_TOOL_NAME,
                        "description": "Returns the fixed connection probe value.",
                        "parameters": {
                            "type": "object",
                            "properties": {},
                            "required": [],
                            "additionalProperties": False,
                        },
                    }
                ],
                "stream": True,
            }
        )
        if not self._completed(first_events):
            raise AgentError("Responses API stream ended without a completed event")
        tool_name, call_id, arguments = self._function_call(first_events)
        if tool_name != _PROBE_TOOL_NAME:
            raise AgentError("Responses API requested an unexpected tool")
        try:
            parsed_arguments = json.loads(arguments or "{}")
        except json.JSONDecodeError:
            raise AgentError("Responses API returned invalid tool arguments") from None
        if parsed_arguments != {}:
            raise AgentError("The probe tool does not accept arguments")
        first_output = self._response_output(first_events)

        second_events = self._stream(
            {
                "model": self.settings.model,
                "input": [
                    *first_output,
                    {
                        "type": "function_call_output",
                        "call_id": call_id,
                        "output": _PROBE_VALUE,
                    }
                ],
                "instructions": (
                    "Reply with exactly the function result and no other text."
                ),
                "stream": True,
            }
        )
        if not self._completed(second_events):
            raise AgentError("Responses API stream ended without a completed event")
        if self._output_text(second_events).strip() != _PROBE_VALUE:
            raise AgentError("Responses API did not return the expected probe value")
        return {
            "tool_name": _PROBE_TOOL_NAME,
            "tool_call_id": call_id,
            "result": _PROBE_VALUE,
            "completed": True,
        }
