"""Codex と Ollama の間に挟んで、送信内容を記録する診断用プロキシ。

目的は1つだけである。**Codex が MCP ツールをモデルへ渡しているか**を見る。

検証済みの事実（2026-09-11、Colab L4 / gpt-oss:20b で実測）:
  - MCPサーバは search_documents を正しく広告し、検索も返す
  - gpt-oss:20b は mcp__local_docs__search_documents という名前・日本語の説明・
    実物のスキーマでツールを渡せば、指示なしでも自分から呼ぶ
  - Ollama は /v1/responses 経由でも 65536 のコンテキストで読み込む

つまり「正しく渡せば呼ぶ」ことは分かっている。残る未知は渡されているかだけである。

手順は docs/mcp-tool-not-called.md にある。

このファイルは単体で動く。プロジェクトの他のモジュールを import しないので、
Codex が動いている機械へこの1枚だけコピーすればよい（必要なのは Python と
requests だけである）。クライアント機にリポジトリを置く必要はない。

使い方（Codexが動いている機械で）:

    python proxy_log.py                      # 上流は http://127.0.0.1:11434
    python proxy_log.py --upstream http://...  # 別の上流を指定

そのあと ~/.codex/config.toml の base_url を http://127.0.0.1:11500/v1 に向け、
Codex から1回質問する。proxy_log.txt に結果が出る。

終わったら base_url を元に戻すこと。
"""
import argparse
import datetime
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urljoin

import requests

LOG_PATH = "proxy_log.txt"
_log_lock = threading.Lock()
UPSTREAM = "http://127.0.0.1:11434"

# 中継してはいけないヘッダ。長さと転送方式は自分で決め直す。
_SKIP_REQUEST = {"host", "content-length", "accept-encoding", "connection"}
_SKIP_RESPONSE = {"content-length", "transfer-encoding", "connection", "content-encoding"}


def log(message):
    stamp = datetime.datetime.now().strftime("%H:%M:%S")
    line = f"[{stamp}] {message}"
    with _log_lock:
        print(line, flush=True)
        with open(LOG_PATH, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")


def describe_request(path, body):
    """要求の中身のうち、知りたいことだけを書き出す。

    本文の全文は出さない。社内資料の断片やAPIキーが混ざりうるためで、
    ツール名と件数、入力の長さだけあれば今回の判定には足りる。
    """
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        log(f"  本文を解釈できませんでした（{len(body)} バイト）")
        return

    tools = payload.get("tools") or []
    log(f"  model={payload.get('model')!r}  stream={payload.get('stream')}  本文={len(body)}バイト")
    log(f"  tools配列: {len(tools)}件")
    if not tools:
        # これが出たら結論が出る。Codexはツールを1つも渡していない。
        log("  ★ ツールが1件も入っていない。モデルは呼びようがない")
    for tool in tools:
        name = tool.get("name") or (tool.get("function") or {}).get("name")
        kind = tool.get("type")
        mark = " ← これ" if name and "search_documents" in str(name) else ""
        log(f"    - {name}  (type={kind}){mark}")
    if not any("search_documents" in str(t) for t in tools):
        log("  ★ search_documents が tools に無い。MCPツールが渡されていない")

    for key in ("instructions", "input", "messages"):
        if key in payload:
            text = json.dumps(payload[key], ensure_ascii=False)
            log(f"  {key}: {len(text)}文字")


def describe_response(status, chunks):
    """応答に function_call が現れたかどうかだけを見る。"""
    text = b"".join(chunks).decode("utf-8", "replace")
    called = []
    for line in text.splitlines():
        if not line.startswith("data:"):
            continue
        try:
            event = json.loads(line[5:].strip())
        except json.JSONDecodeError:
            continue
        item = event.get("item") or {}
        if item.get("type") == "function_call":
            called.append(item.get("name"))
    log(f"  応答 HTTP {status}")
    if called:
        log(f"  ✅ モデルが呼んだツール: {called}")
    elif "function_call" in text:
        log("  応答に function_call の断片あり（形式を要確認）")
    else:
        log("  ❌ モデルはツールを呼ばなかった")


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass  # 既定のアクセスログは出さない。自前のログだけにする

    def _relay(self, method):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        headers = {
            key: value
            for key, value in self.headers.items()
            if key.lower() not in _SKIP_REQUEST
        }

        log(f"--- {method} {self.path} ---")
        interesting = "/responses" in self.path or "/chat/completions" in self.path
        if interesting and body:
            describe_request(self.path, body)

        try:
            upstream = requests.request(
                method,
                urljoin(UPSTREAM, self.path),
                data=body or None,
                headers=headers,
                stream=True,
                timeout=(10, 900),
            )
        except requests.RequestException as error:
            log(f"  上流への中継に失敗: {error}")
            self.send_error(502, "upstream failed")
            return

        self.send_response(upstream.status_code)
        for key, value in upstream.headers.items():
            if key.lower() not in _SKIP_RESPONSE:
                self.send_header(key, value)
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()

        chunks = []
        try:
            for chunk in upstream.iter_content(chunk_size=None):
                if not chunk:
                    continue
                if interesting:
                    chunks.append(chunk)
                self.wfile.write(f"{len(chunk):X}\r\n".encode())
                self.wfile.write(chunk)
                self.wfile.write(b"\r\n")
                self.wfile.flush()
            self.wfile.write(b"0\r\n\r\n")
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            # Codex が途中で切ることはある。記録だけ残して続ける。
            log("  クライアントが接続を切りました")

        if interesting:
            describe_response(upstream.status_code, chunks)

    def do_POST(self):
        self._relay("POST")

    def do_GET(self):
        self._relay("GET")


def main():
    global UPSTREAM
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream", default=UPSTREAM, help="本物のOllama")
    parser.add_argument("--port", type=int, default=11500)
    args = parser.parse_args()
    UPSTREAM = args.upstream.rstrip("/") + "/"

    log(f"プロキシ開始: http://127.0.0.1:{args.port} → {UPSTREAM}")
    log(f"~/.codex/config.toml の base_url を http://127.0.0.1:{args.port}/v1 に向けてください")
    log("終わったら base_url を元に戻すこと")
    try:
        ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()
    except KeyboardInterrupt:
        log("停止しました")
        return 0


if __name__ == "__main__":
    sys.exit(main())
