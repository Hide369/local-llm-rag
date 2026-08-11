"""Ollama の埋め込みAPIを叩く。

接続先に localhost を使ってはならない。Windowsでは localhost が先にIPv6の ::1 に
解決され、OllamaがIPv4でしか待ち受けていないためタイムアウト待ちが発生する。
実測: localhost + 毎回新規接続 2,151ms / 127.0.0.1 79ms / Session再利用 77ms。
Ollama自身の処理時間はいずれも約80msである。
"""
import os
import time

import requests

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:12000")
EMBED_MODEL = "bge-m3"
EMBED_DIM = 1024

# batch=8で1,197ms/件、batch=32で1,417ms/件。16GBのメモリでは大きなバッチが不利。
EMBED_BATCH_SIZE = 8

_MAX_ATTEMPTS = 4  # 初回 + 3回の再試行（1秒 → 2秒 → 4秒）
_TIMEOUT = 600


class EmbeddingError(Exception):
    """埋め込みの取得に失敗した。"""


def new_session() -> requests.Session:
    """接続を再利用するセッションを作る。使い回すことで1リクエストあたり約2秒を節約できる。"""
    return requests.Session()


def _post_batch(session, texts: list[str]) -> list[list[float]]:
    url = f"{OLLAMA_HOST}/api/embed"
    payload = {"model": EMBED_MODEL, "input": texts, "keep_alive": "30m"}
    last_error = None
    for attempt in range(_MAX_ATTEMPTS):
        try:
            response = session.post(url, json=payload, timeout=_TIMEOUT)
            response.raise_for_status()
            vectors = response.json()["embeddings"]
        except (requests.RequestException, KeyError, ValueError) as error:
            last_error = error
            if attempt < _MAX_ATTEMPTS - 1:
                time.sleep(2**attempt)
            continue
        # モデルを取り違えると次元が変わる。DBに書き込む前にここで止める。
        if any(len(vector) != EMBED_DIM for vector in vectors):
            raise EmbeddingError(
                f"埋め込みの次元が想定と違います（期待 {EMBED_DIM}）。"
                f"モデル {EMBED_MODEL} が正しいか確認してください。"
            )
        return vectors
    raise EmbeddingError(
        f"{OLLAMA_HOST} への埋め込みリクエストが{_MAX_ATTEMPTS}回失敗しました: {last_error}"
    )


def embed_texts(texts: list[str], session=None) -> list[list[float]]:
    """テキスト列をバッチに分けて埋め込む。"""
    if not texts:
        return []
    own_session = session is None
    session = session or new_session()
    try:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), EMBED_BATCH_SIZE):
            vectors.extend(_post_batch(session, texts[start : start + EMBED_BATCH_SIZE]))
        return vectors
    finally:
        if own_session:
            session.close()


def embed_query(text: str, session=None) -> list[float]:
    return embed_texts([text], session=session)[0]


def check_ollama(session=None) -> None:
    """取り込み開始前の疎通確認。

    260チャンクの処理を始めてから落ちるのを防ぐため、先に一度だけ確認する。
    """
    own_session = session is None
    session = session or new_session()
    try:
        try:
            response = session.get(f"{OLLAMA_HOST}/api/tags", timeout=10)
            response.raise_for_status()
            names = [model["name"] for model in response.json().get("models", [])]
        except (requests.RequestException, KeyError, ValueError) as error:
            raise EmbeddingError(
                f"Ollamaに接続できません（{OLLAMA_HOST}）。"
                f"起動しているか確認してください: {error}"
            ) from error
        if not any(name.split(":")[0] == EMBED_MODEL for name in names):
            raise EmbeddingError(
                f"埋め込みモデル {EMBED_MODEL} がありません。"
                f"`ollama pull {EMBED_MODEL}` を実行してください。"
            )
    finally:
        if own_session:
            session.close()
