"""Ollama の VLM(Vision Language Model) にPDF/PPTX埋め込み画像の説明文を作らせる。

design: docs/superpowers/specs/2026-08-24-vlm-image-captioning-design.md
"""
import base64
import time

import requests

from ingest.embedder import OLLAMA_HOST

VLM_MODEL = "qwen2.5vl:7b"

CAPTION_PROMPT = (
    "この画像に写っている図表・写真の内容を、日本語で2〜3文にまとめて説明してください。"
    "ロゴやアイコンなど内容のない装飾画像であれば「装飾画像」とだけ答えてください。"
)

_MAX_ATTEMPTS = 4  # embedder.pyと同じ: 初回 + 3回の再試行（1秒 → 2秒 → 4秒）
_TIMEOUT = 120


class VlmError(Exception):
    """画像の説明取得に失敗した。"""


def caption_image(image_bytes: bytes, session=None) -> str:
    """画像1枚を日本語の説明文にする。"""
    own_session = session is None
    session = session or requests.Session()
    try:
        url = f"{OLLAMA_HOST}/api/chat"
        payload = {
            "model": VLM_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": CAPTION_PROMPT,
                    "images": [base64.b64encode(image_bytes).decode("ascii")],
                }
            ],
            "stream": False,
        }
        last_error = None
        for attempt in range(_MAX_ATTEMPTS):
            try:
                response = session.post(url, json=payload, timeout=_TIMEOUT)
                response.raise_for_status()
                return response.json()["message"]["content"].strip()
            except (requests.RequestException, KeyError, ValueError) as error:
                last_error = error
                if attempt < _MAX_ATTEMPTS - 1:
                    time.sleep(2**attempt)
        raise VlmError(
            f"{OLLAMA_HOST} への画像説明リクエストが{_MAX_ATTEMPTS}回失敗しました: {last_error}"
        )
    finally:
        if own_session:
            session.close()
