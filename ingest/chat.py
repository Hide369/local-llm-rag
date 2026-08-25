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
"""
import json
import time
from collections.abc import Iterator

import requests

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


def ask_json(model: str, prompt: str, session=None) -> str:
    """JSONオブジェクト1個だけを返させる。条件抽出用。temperature=0固定。

    temperature=0固定の理由はingest/conditions.pyと同じ: 同じ質問で条件が
    揺れると再現性のない誤りになるため。
    """
    own_session = session is None
    session = session or new_session()
    try:
        url = f"{OLLAMA_HOST}/api/chat"
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "format": "json",
            "keep_alive": "30m",
            "options": {"temperature": 0, "num_ctx": NUM_CTX},
        }
        last_error = None
        for attempt in range(_MAX_ATTEMPTS):
            try:
                response = session.post(url, json=payload, timeout=_TIMEOUT)
                response.raise_for_status()
                return response.json()["message"]["content"]
            except (requests.RequestException, KeyError, ValueError) as error:
                last_error = error
                if attempt < _MAX_ATTEMPTS - 1:
                    time.sleep(2**attempt)
        raise ChatError(
            f"{OLLAMA_HOST} への生成リクエストが{_MAX_ATTEMPTS}回失敗しました: {last_error}"
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
        url = f"{OLLAMA_HOST}/api/chat"
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "keep_alive": "30m",
            "options": {"temperature": temperature, "num_ctx": NUM_CTX},
        }
        try:
            response = session.post(url, json=payload, stream=True, timeout=_TIMEOUT)
            response.raise_for_status()
        except requests.RequestException as error:
            raise ChatError(f"{OLLAMA_HOST} への生成リクエストに失敗しました: {error}") from error

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
