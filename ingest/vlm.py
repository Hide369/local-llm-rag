"""VLM(Vision Language Model) にPDF/PPTX埋め込み画像の説明文を作らせる。

接続先は ingest/backend.py が決める。画像の渡し方が経路で違い、Ollama は
メッセージの `images` にbase64の配列を置くのに対し、OpenAI 互換は `content` を
配列にして `image_url` へ data URL を入れる。その違いだけをここで吸収する。

design: docs/superpowers/specs/2026-08-24-vlm-image-captioning-design.md
"""
import base64
import os
import time

import requests

from ingest import backend
from ingest.embedder import OLLAMA_HOST, new_session
# 装飾画像の合図語は ingest/image_text.py の DECORATION が正本。ここで文字列を
# 書き写すと、片方だけ変えたときに判定が黙って外れる（image_text側はvlmを
# importしないので循環にはならない）。
from ingest.image_text import DECORATION

# 変数名が OLLAMA_ で始まるのは、この名前で .env に書いている環境が既にあるため。
# vLLM へ向けたときもこの値を使う（そちらではHFのハンドルを入れる）。
VLM_MODEL = os.environ.get("OLLAMA_VLM_MODEL", "qwen2.5vl:7b")

CAPTION_PROMPT = (
    "この画像に写っている図表・写真の内容を、日本語で2〜3文にまとめて説明してください。"
    f"ロゴやアイコンなど内容のない装飾画像であれば「{DECORATION}」とだけ答えてください。"
)

_MAX_ATTEMPTS = 4  # embedder.pyと同じ: 初回 + 3回の再試行（1秒 → 2秒 → 4秒）
_TIMEOUT = 600


class VlmError(Exception):
    """画像の説明取得に失敗した。"""


def caption_image(image_bytes: bytes, session=None) -> str:
    """画像1枚を日本語の説明文にする。"""
    own_session = session is None
    session = session or new_session()
    try:
        encoded = base64.b64encode(image_bytes).decode("ascii")
        if backend.is_vllm():
            url = backend.vlm_url()
            payload = {
                "model": VLM_MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": CAPTION_PROMPT},
                            {
                                "type": "image_url",
                                # 画像の種類は data URL のMIME型で伝える。取り込みが
                                # 渡してくるのはPNGに正規化された bytes である。
                                "image_url": {
                                    "url": f"data:image/png;base64,{encoded}"
                                },
                            },
                        ],
                    }
                ],
                "stream": False,
            }
        else:
            url = f"{OLLAMA_HOST}/api/chat"
            payload = {
                "model": VLM_MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": CAPTION_PROMPT,
                        "images": [encoded],
                    }
                ],
                "stream": False,
                "keep_alive": "30m",
            }
        last_error = None
        for attempt in range(_MAX_ATTEMPTS):
            try:
                response = session.post(url, json=payload, timeout=_TIMEOUT)
                response.raise_for_status()
                body = response.json()
                content = (
                    backend.message_content(body)
                    if backend.is_vllm()
                    else body["message"]["content"]
                )
                return content.strip()
            except (requests.RequestException, KeyError, ValueError) as error:
                last_error = error
                if attempt < _MAX_ATTEMPTS - 1:
                    time.sleep(2**attempt)
        raise VlmError(
            f"{url} への画像説明リクエストが{_MAX_ATTEMPTS}回失敗しました: {last_error}"
        )
    finally:
        if own_session:
            session.close()


def check_vlm(session=None) -> None:
    """取り込み開始前の疎通確認。モデル未pullで460チャンクの処理が始まってから
    落ちるのを防ぐため、embedder.check_ollama() と同じ考え方で先に一度だけ確認する。
    """
    own_session = session is None
    session = session or new_session()
    try:
        if backend.is_vllm():
            host = backend.VLLM_VLM_HOST
            try:
                response = session.get(backend.models_url(host), timeout=10)
                response.raise_for_status()
                names = [model["id"] for model in response.json().get("data", [])]
            except (requests.RequestException, KeyError, ValueError) as error:
                raise VlmError(
                    f"vLLMに接続できません（{host}）。起動しているか確認してください: {error}"
                ) from error
            if VLM_MODEL not in names:
                raise VlmError(
                    f"vLLM（{host}）が出しているのは {names} で、"
                    f"OLLAMA_VLM_MODEL に指定した {VLM_MODEL} がありません。"
                )
            return
        try:
            response = session.get(f"{OLLAMA_HOST}/api/tags", timeout=10)
            response.raise_for_status()
            names = [model["name"] for model in response.json().get("models", [])]
        except (requests.RequestException, KeyError, ValueError) as error:
            raise VlmError(
                f"Ollamaに接続できません（{OLLAMA_HOST}）。起動しているか確認してください: {error}"
            ) from error
        vlm_base = VLM_MODEL.split(":")[0]
        if not any(name.split(":")[0] == vlm_base for name in names):
            raise VlmError(
                f"VLMモデル {VLM_MODEL} がありません。`ollama pull {VLM_MODEL}` を実行してください。"
            )
    finally:
        if own_session:
            session.close()
