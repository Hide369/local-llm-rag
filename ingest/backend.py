"""生成・埋め込み・VLMの接続先を Ollama と vLLM（OpenAI互換）で切り替える。

Ollama のネイティブAPI（`/api/chat`・`/api/embed`）と vLLM の OpenAI 互換API
（`/v1/chat/completions`・`/v1/embeddings`）は、URL・要求の組み立て・応答の
取り出し方・認証ヘッダーのすべてが違う。その違いをこのモジュールに集める。

`ingest/chat.py` と `ingest/embedder.py` を丸ごと二重化しないのは、再試行の
回数と待ち、タイムアウト、セッションの使い回し、次元の検査といった中身が
両者で1文字も変わらないためである。変わるのは要求の形と応答の取り出しだけで、
そこだけを差し替えるほうが、片方を直してもう片方を直し忘れる事故が起きない。

既定は `ollama` で、環境変数を何も足さなければ従来と同じ経路をそのまま通る。
GB10サーバーへ寄せる手順は docs/vllm-gb10.md と docs/vllm-gb10-models.md にある。
"""
import os

OLLAMA = "ollama"
VLLM = "vllm"

# 既定を ollama にしてあるのは、この値を知らない利用者のノートPCが今までどおり
# 動く必要があるためである。vLLM へ向けるのは明示的な選択に限る。
BACKEND = os.environ.get("LLM_BACKEND", OLLAMA).strip().lower() or OLLAMA

if BACKEND not in (OLLAMA, VLLM):
    raise ValueError(
        f"LLM_BACKEND は {OLLAMA} か {VLLM} を指定してください（指定値: {BACKEND}）"
    )

DEFAULT_VLLM_HOST = "http://127.0.0.1:8000"

# 生成・埋め込み・VLMで別のポートに立てられる。docs/vllm-gb10-models.md の
# 構成では 8000/8002/8003 に分けている。1本にまとめているなら VLLM_HOST だけを
# 設定すればよく、残りはそこへ落ちる。
VLLM_HOST = os.environ.get("VLLM_HOST", DEFAULT_VLLM_HOST).rstrip("/")
VLLM_EMBED_HOST = (os.environ.get("VLLM_EMBED_HOST") or VLLM_HOST).rstrip("/")
VLLM_VLM_HOST = (os.environ.get("VLLM_VLM_HOST") or VLLM_HOST).rstrip("/")


def is_vllm() -> bool:
    """vLLM（OpenAI互換）に繋いでいるかどうか。

    呼び出し側はこの1か所だけを見る。`BACKEND` を直接読ませないのは、テストが
    このモジュールの属性を差し替えるだけで両方の経路を通せるようにするため。
    """
    return BACKEND == VLLM


def chat_url() -> str:
    """1ターンの生成（ストリームも含む）を投げる先。"""
    return f"{VLLM_HOST}/v1/chat/completions"


def vlm_url() -> str:
    """画像つきの生成を投げる先。VLMを別ポートに立てている場合に分かれる。"""
    return f"{VLLM_VLM_HOST}/v1/chat/completions"


def embed_url() -> str:
    return f"{VLLM_EMBED_HOST}/v1/embeddings"


def models_url(host: str) -> str:
    """疎通確認に使う。Ollama の `/api/tags` に当たるもの。"""
    return f"{host}/v1/models"


def apply_auth(session) -> None:
    """接続先に合わせた認証ヘッダーを付ける。

    Ollama側は `X-API-Key`（ColabのL4に立てたリバースプロキシ）、vLLM側は
    `--api-key` に対応する `Authorization: Bearer` で、形式が違う。
    """
    if is_vllm():
        api_key = os.environ.get("VLLM_API_KEY")
        if api_key:
            session.headers["Authorization"] = f"Bearer {api_key}"
        return
    api_key = os.environ.get("OLLAMA_API_KEY")
    if api_key:
        session.headers["X-API-Key"] = api_key


def message_content(payload: dict) -> str:
    """OpenAI互換の応答から本文だけを取り出す。

    推論モデル（Nemotron 3 など）は思考を出す。サーバーに `--reasoning-parser` を
    付けていれば思考は `reasoning_content` に分かれ、`content` は本文だけになる。
    付け忘れていると本文側に思考が混ざり、JSONを期待する呼び出し（ask_json）が
    黙って壊れる。ここで気づけるよう、本文が空で思考だけ返ってきた場合は
    何が起きているかを名指しで知らせる。

    KeyError / IndexError はそのまま投げる。呼び出し側の再試行ループが
    ValueError と並べて捕まえており、通信の失敗と同じ扱いでよい。
    """
    message = payload["choices"][0]["message"]
    content = message.get("content")
    if content:
        return content
    if message.get("reasoning_content"):
        raise ValueError(
            "本文が空で、思考（reasoning_content）だけが返りました。"
            "vLLM の起動フラグに --reasoning-parser を付けているか確認してください。"
        )
    # 空文字を返すモデルもある。呼び出し側が判断できるよう、そのまま渡す。
    return content or ""


def embedding_vectors(payload: dict) -> list[list[float]]:
    """OpenAI互換の応答からベクトルを取り出す。

    `data` の並び順はAPIの保証に含まれないが `index` が付く。入力の順と
    ずれたベクトルをDBへ書くと、どのチャンクにも気づかれずに間違った意味が
    付く。ここで index に従って並べ直す。
    """
    rows = sorted(payload["data"], key=lambda row: row["index"])
    return [row["embedding"] for row in rows]
