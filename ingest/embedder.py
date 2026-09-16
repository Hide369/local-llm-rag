"""埋め込みAPIを叩く。

接続先は ingest/backend.py が決める。既定は Ollama のネイティブAPI
（`/api/embed`）で、`LLM_BACKEND=vllm` なら OpenAI 互換の `/v1/embeddings` を
叩く。どちらでもバッチの切り方・再試行・次元の検査は変わらない。

接続先に localhost を使ってはならない。Windowsでは localhost が先にIPv6の ::1 に
解決され、OllamaがIPv4でしか待ち受けていないためタイムアウト待ちが発生する。
実測: localhost + 毎回新規接続 2,151ms / 127.0.0.1 79ms / Session再利用 77ms。
Ollama自身の処理時間はいずれも約80msである。
"""
import os
import time

import requests

from ingest import backend

# Ollamaがインストール直後に待ち受けるポートに合わせてある。教材の udemy1.py〜udemy3.py は
# 12000番をコードに直接書いているが、環境変数を読まないためここの既定値とは無関係。
DEFAULT_OLLAMA_HOST = "http://127.0.0.1:11434"

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", DEFAULT_OLLAMA_HOST)
# モデルと次元を環境変数で差し替えられるようにしてあるのは、vLLM へ寄せるときに
# 別の埋め込みモデル（例: nvidia/Nemotron-3-Embed-1B-NVFP4 は2048次元）を選べる
# ようにするためである。既定値は従来と同じで、何も設定しなければ挙動は変わらない。
#
# **次元を変えたら、既存のベクトルDBは作り直しになる。** 取り込み済みのベクトルと
# 問い合わせのベクトルは同じモデルで作られている必要があり、差分取り込みでは
# 直らない（`scripts.ingest_source --force`）。ingest/retrieval.py の
# RELEVANCE_THRESHOLD も距離の分布が変わるため測り直しが要る。
EMBED_MODEL = os.environ.get("EMBED_MODEL", "bge-m3")
EMBED_DIM = int(os.environ.get("EMBED_DIM", "1024"))

# 検索の問い合わせと、取り込む文書とで、別の接頭辞を求めるモデルがある
# （Nemotron-3-Embed は "query: " と "passage: "）。bge-m3 は要らないので既定は空。
# 付け忘れてもエラーにはならず、精度だけが静かに落ちる。ここで一元化しておく。
EMBED_QUERY_PREFIX = os.environ.get("EMBED_QUERY_PREFIX", "")
EMBED_PASSAGE_PREFIX = os.environ.get("EMBED_PASSAGE_PREFIX", "")

# batch=8で1,197ms/件、batch=32で1,417ms/件。16GBのメモリでは大きなバッチが不利。
EMBED_BATCH_SIZE = 8

_MAX_ATTEMPTS = 4  # 初回 + 3回の再試行（1秒 → 2秒 → 4秒）
_TIMEOUT = 600


class EmbeddingError(Exception):
    """埋め込みの取得に失敗した。"""


def new_session() -> requests.Session:
    """接続を再利用するセッションを作る。使い回すことで1リクエストあたり約2秒を節約できる。

    認証ヘッダーは接続先で形が違う（Ollamaは X-API-Key、vLLMは Bearer）ので
    ingest/backend.py に任せる。
    """
    session = requests.Session()
    backend.apply_auth(session)
    return session


def _endpoint() -> tuple[str, dict]:
    """接続先のURLと、モデル以外の固定部分を返す。"""
    if backend.is_vllm():
        # keep_alive は Ollama 固有。vLLM は起動時からモデルを載せたままにする。
        return backend.embed_url(), {}
    return f"{OLLAMA_HOST}/api/embed", {"keep_alive": "30m"}


def _post_batch(session, texts: list[str]) -> list[list[float]]:
    url, extra = _endpoint()
    payload = {"model": EMBED_MODEL, "input": texts, **extra}
    last_error = None
    for attempt in range(_MAX_ATTEMPTS):
        try:
            response = session.post(url, json=payload, timeout=_TIMEOUT)
            response.raise_for_status()
            body = response.json()
            vectors = (
                backend.embedding_vectors(body)
                if backend.is_vllm()
                else body["embeddings"]
            )
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
        f"{url} への埋め込みリクエストが{_MAX_ATTEMPTS}回失敗しました: {last_error}"
    )


def _embed(texts: list[str], prefix: str, session=None) -> list[list[float]]:
    if not texts:
        return []
    own_session = session is None
    session = session or new_session()
    try:
        prefixed = [prefix + text for text in texts] if prefix else texts
        vectors: list[list[float]] = []
        for start in range(0, len(prefixed), EMBED_BATCH_SIZE):
            vectors.extend(
                _post_batch(session, prefixed[start : start + EMBED_BATCH_SIZE])
            )
        return vectors
    finally:
        if own_session:
            session.close()


def embed_texts(texts: list[str], session=None) -> list[list[float]]:
    """取り込む文書をバッチに分けて埋め込む。"""
    return _embed(texts, EMBED_PASSAGE_PREFIX, session=session)


def embed_query(text: str, session=None) -> list[float]:
    """検索の問い合わせを埋め込む。

    embed_texts と分けているのは接頭辞が違うためである。同じ関数に寄せると、
    文書側の接頭辞が問い合わせにも付き、精度だけが静かに落ちる。
    """
    return _embed([text], EMBED_QUERY_PREFIX, session=session)[0]


def check_ollama(session=None) -> None:
    """取り込み開始前の疎通確認。

    460チャンクの処理を始めてから落ちるのを防ぐため、先に一度だけ確認する。

    名前を check_ollama のままにしてあるのは、7か所の呼び出し元とテストが
    この名前を使っているためである。vLLM に繋いでいるときは同じ役割の
    `/v1/models` を見る。
    """
    own_session = session is None
    session = session or new_session()
    try:
        if backend.is_vllm():
            _check_vllm(session)
            return
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


def _check_vllm(session) -> None:
    host = backend.VLLM_EMBED_HOST
    try:
        response = session.get(backend.models_url(host), timeout=10)
        response.raise_for_status()
        names = [model["id"] for model in response.json().get("data", [])]
    except (requests.RequestException, KeyError, ValueError) as error:
        raise EmbeddingError(
            f"vLLMに接続できません（{host}）。起動しているか確認してください: {error}"
        ) from error
    # vLLM は1プロセス1モデルなので、名前が合わなければ別のモデルを立てている。
    if EMBED_MODEL not in names:
        raise EmbeddingError(
            f"vLLM（{host}）が出しているのは {names} で、"
            f"EMBED_MODEL に指定した {EMBED_MODEL} がありません。"
        )
