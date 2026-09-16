"""Ollama のチャット生成API（/api/chat）を叩く。

openaiパッケージ経由（/v1/chat/completions）では、options.num_ctxをextra_body
でいくら指定しても無視され、既定の4096トークンに固定されたままだった
（実測: `/api/ps`のcontext_lengthが常に4096のままで変化しなかった）。

これが実害になったのは gpt-oss:20b が内部の思考（thinking）を別チャネルで
消費する挙動と重なったため。込み入った質問（有給休暇の規定を条文番号付きで
網羅的に、等）では、思考だけで4096トークンを使い切り、最終回答が1文字も
出ないまま finish_reason=length で打ち切られた（実測）。

ネイティブAPI（このモジュール）ならoptions.num_ctxが確実に反映される
（`/api/chat`に直接投げて`/api/ps`のcontext_lengthが変わることを確認済み）。

`LLM_BACKEND=vllm` のときは OpenAI 互換の `/v1/chat/completions` を叩く
（接続先の判定は ingest/backend.py）。この経路では **num_ctx は送らない**。
vLLM の文脈長はサーバー起動時の `--max-model-len` で決まり、リクエストごとには
変えられないためである。上に書いた「思考で使い切って回答が出ない」問題は、
思考を出すモデル（Nemotron 3 など）でより強く出る。vLLM 側の `--max-model-len` を
十分に取ること。詳しくは docs/vllm-gb10-models.md にある。
"""
import json
import time
from collections.abc import Iterator

import requests

from ingest import backend
from ingest.embedder import OLLAMA_HOST, new_session

# qwen3:32b（VRAM残り約4GB、L4=24GB中20GBをモデル本体が占有）でも安全に収まる値。
# 既定の4096では、有給休暇のような込み入った質問でgpt-oss:20bの思考だけで
# 使い切ってしまう実測があったため引き上げた。全モデル共通の値にしているのは、
# 会話の途中でモデルを切り替えたときにも同じ余裕を保つため。
NUM_CTX = 8192

_MAX_ATTEMPTS = 4  # embedder.pyと同じ: 初回 + 3回の再試行（1秒 → 2秒 → 4秒）
_TIMEOUT = 600


class ChatError(Exception):
    """チャット生成に失敗した。"""


def _openai_messages(messages: list[dict]) -> list[dict]:
    """Ollama 形の履歴を OpenAI 互換の形へ直す。

    道具の結果を返すメッセージの形が違う。Ollama は
    `{"role": "tool", "tool_name": 名前}`、OpenAI 互換は
    `{"role": "tool", "tool_call_id": 呼び出しのid}` である。履歴を積むのは
    docgen/project.py で、そちらに接続先の事情を持ち込みたくないので、
    送る直前のここで直す。idは直前のアシスタントの tool_calls から名前で引く。
    """
    ids_by_name: dict[str, str] = {}
    converted: list[dict] = []
    for message in messages:
        if message.get("role") == "assistant":
            for call in message.get("tool_calls") or []:
                name = (call.get("function") or {}).get("name")
                if name and call.get("id"):
                    ids_by_name[name] = call["id"]
        if message.get("role") == "tool" and "tool_call_id" not in message:
            call_id = ids_by_name.get(message.get("tool_name"))
            message = {
                key: value for key, value in message.items() if key != "tool_name"
            }
            if call_id:
                message["tool_call_id"] = call_id
        converted.append(message)
    return converted


def _request(
    model: str,
    messages: list[dict],
    *,
    num_ctx: int,
    stream: bool = False,
    temperature: float | None = None,
    json_format: bool = False,
    tools=None,
) -> tuple[str, dict]:
    """接続先に合わせてURLと本文を組み立てる。

    違いはここだけに閉じる。再試行の回数と待ち、タイムアウト、セッションの
    扱いは呼び出し側で共通のままにしておきたいためである。
    """
    if backend.is_vllm():
        payload: dict = {
            "model": model,
            "messages": _openai_messages(messages),
            "stream": stream,
        }
        if temperature is not None:
            payload["temperature"] = temperature
        if json_format:
            # Ollama の "format": "json" に当たる。キー名が違うので黙って無視される。
            payload["response_format"] = {"type": "json_object"}
        if tools is not None:
            payload["tools"] = tools
        return backend.chat_url(), payload

    payload = {
        "model": model,
        "messages": messages,
        "stream": stream,
        "keep_alive": "30m",
        "options": {"num_ctx": num_ctx},
    }
    if temperature is not None:
        payload["options"]["temperature"] = temperature
    if json_format:
        payload["format"] = "json"
    if tools is not None:
        payload["tools"] = tools
    return f"{OLLAMA_HOST}/api/chat", payload


def _content(body: dict) -> str:
    """応答から本文を取り出す。"""
    if backend.is_vllm():
        return backend.message_content(body)
    return body["message"]["content"]


def ask_json(model: str, prompt: str, session=None, num_ctx: int = NUM_CTX) -> str:
    """JSONオブジェクト1個だけを返させる。条件抽出用。temperature=0固定。

    temperature=0固定の理由はingest/conditions.pyと同じ: 同じ質問で条件が
    揺れると再現性のない誤りになるため。

    num_ctx の既定は NUM_CTX（8192）で、条件抽出とクエリ翻訳はこれで足りる。
    雛形の生成（docgen/filling.py）だけは添付ファイルを丸ごと渡すため大きい値を
    渡す。既定値を上げないのは、短いプロンプトにも大きな文脈を割り当てると
    VRAMの余裕を使い切るためである（この定数のコメントを参照）。
    """
    own_session = session is None
    session = session or new_session()
    try:
        url, payload = _request(
            model,
            [{"role": "user", "content": prompt}],
            num_ctx=num_ctx,
            temperature=0,
            json_format=True,
        )
        last_error = None
        for attempt in range(_MAX_ATTEMPTS):
            try:
                response = session.post(url, json=payload, timeout=_TIMEOUT)
                response.raise_for_status()
                return _content(response.json())
            except (requests.RequestException, KeyError, ValueError) as error:
                last_error = error
                if attempt < _MAX_ATTEMPTS - 1:
                    time.sleep(2**attempt)
        raise ChatError(
            f"{url} への生成リクエストが{_MAX_ATTEMPTS}回失敗しました: {last_error}"
        )
    finally:
        if own_session:
            session.close()


def ask_text(model: str, prompt: str, session=None, num_ctx: int = NUM_CTX) -> str:
    """平文をそのまま返させる。文書生成用。

    ask_json と違って format を送らない。数千字の Markdown を JSON 文字列へ
    押し込ませると、改行・引用符・バックスラッシュのエスケープで壊れる。

    temperature も送らない。ask_json が 0 を固定するのは条件抽出で答えが揺れると
    再現性のない誤りになるためで、文章生成にその要求はない。
    """
    own_session = session is None
    session = session or new_session()
    try:
        url, payload = _request(
            model, [{"role": "user", "content": prompt}], num_ctx=num_ctx
        )
        last_error = None
        for attempt in range(_MAX_ATTEMPTS):
            try:
                response = session.post(url, json=payload, timeout=_TIMEOUT)
                response.raise_for_status()
                return _content(response.json())
            except (requests.RequestException, KeyError, ValueError) as error:
                last_error = error
                if attempt < _MAX_ATTEMPTS - 1:
                    time.sleep(2**attempt)
        raise ChatError(
            f"{url} への生成リクエストが{_MAX_ATTEMPTS}回失敗しました: {last_error}"
        )
    finally:
        if own_session:
            session.close()


def ask_tools(model: str, messages, tools, session=None, num_ctx: int = NUM_CTX) -> dict:
    """道具を渡して1ターン投げ、message を辞書のまま返す。

    ask_json / ask_text が content の文字列を返すのに対し、ここは message 全体を
    返す。モデルが道具を呼んだかどうかは `tool_calls` の有無で分かり、content
    だけを取り出すとその情報が失われる。呼び出し側は両者を見分ける必要がある。

    **ループはここに置かない。** このモジュールは道具の意味を知らない伝送路で
    あり、道具を実行できるのはそれを定義した側だけである（プロジェクトフォルダ
    を読む道具なら docgen/project.py）。ここが実行まで抱えると、道具が増える
    たびにこのモジュールが太る。

    messages は呼び出し側が組み立てたものをそのまま送る。道具の結果を積んだ
    履歴を投げ直せないと2周目が成り立たないため、ここで作り替えない。
    """
    own_session = session is None
    session = session or new_session()
    try:
        url, payload = _request(model, messages, num_ctx=num_ctx, tools=tools)
        last_error = None
        for attempt in range(_MAX_ATTEMPTS):
            try:
                response = session.post(url, json=payload, timeout=_TIMEOUT)
                response.raise_for_status()
                body = response.json()
                if not backend.is_vllm():
                    return body["message"]
                message = body["choices"][0]["message"]
                # 呼び出し側はこれを履歴へ積み直す。思考まで送り返すと文脈を
                # 食うだけなので、次の周に要る3つだけを残す。
                return {
                    "role": message.get("role", "assistant"),
                    "content": message.get("content") or "",
                    "tool_calls": message.get("tool_calls") or [],
                }
            except (requests.RequestException, KeyError, ValueError) as error:
                last_error = error
                if attempt < _MAX_ATTEMPTS - 1:
                    time.sleep(2**attempt)
        raise ChatError(
            f"{url} への生成リクエストが{_MAX_ATTEMPTS}回失敗しました: {last_error}"
        )
    finally:
        if own_session:
            session.close()


def stream_chat(
    model: str, messages: list[dict], temperature: float, session=None
) -> Iterator[str]:
    """回答をトークン単位で流す。

    ネイティブAPIのストリームはSSEではなくNDJSON（1行1JSON）。呼び出し側が
    ジェネレータを最後まで消費し終えた時点（またはエラー）でsessionを閉じる。
    """
    own_session = session is None
    session = session or new_session()
    try:
        url, payload = _request(
            model, messages, num_ctx=NUM_CTX, stream=True, temperature=temperature
        )
        try:
            response = session.post(url, json=payload, stream=True, timeout=_TIMEOUT)
            response.raise_for_status()
        except requests.RequestException as error:
            raise ChatError(f"{url} への生成リクエストに失敗しました: {error}") from error

        if backend.is_vllm():
            yield from _stream_sse(response)
            return

        for line in response.iter_lines():
            if not line:
                continue
            try:
                data = json.loads(line)
            except ValueError as error:
                raise ChatError(f"生成結果を解釈できませんでした: {error}") from error
            if data.get("error"):
                raise ChatError(data["error"])
            content = data.get("message", {}).get("content")
            if content:
                yield content
            if data.get("done"):
                break
    finally:
        if own_session:
            session.close()


def _stream_sse(response) -> Iterator[str]:
    """OpenAI互換のストリームを読む。

    ネイティブAPIのNDJSONと違い、こちらはSSEで `data: ` が前に付き、最後に
    `data: [DONE]` が来る。本文は message ではなく delta に入る。
    """
    for raw in response.iter_lines():
        if not raw:
            continue
        line = raw.decode("utf-8") if isinstance(raw, bytes) else raw
        if not line.startswith("data:"):
            continue
        chunk = line[len("data:") :].strip()
        if chunk == "[DONE]":
            break
        try:
            data = json.loads(chunk)
        except ValueError as error:
            raise ChatError(f"生成結果を解釈できませんでした: {error}") from error
        if data.get("error"):
            raise ChatError(data["error"])
        choices = data.get("choices") or [{}]
        content = (choices[0].get("delta") or {}).get("content")
        if content:
            yield content
