# 社内資料 RAG MCP サーバの設定

`scripts/rag_mcp_server.py` は、取り込み済みの社内資料（`vector_store.sqlite3`）を
Codex から検索できるようにする stdio MCP サーバである。ツールは1本だけで、
検索結果は回答文ではなく根拠となる原文を出典つきで返す。

```
search_documents(query: str, n_results: int = 4) -> str
```

- `query`: 検索したい内容。自然文でよい。
- `n_results`: 返すチャンク数。既定は `SEARCH_RESULT_COUNT`（4）。

設計の経緯・却下案・エラーハンドリングの全体像は
[2026-09-05-rag-mcp-server-design.md](superpowers/specs/2026-09-05-rag-mcp-server-design.md)
にある。本ドキュメントは導入先で手を動かすための手順に絞る。

## 前提

- Ollama がセットアップ済みで、`bge-m3` が導入済みであること（下記）
- Python 依存関係が導入済みであること（`pip install -r requirements.txt`。`mcp` を含む）
- 資料が `source/` に配置され、`python -m scripts.ingest_source` で取り込み済みであること

DB のパスはサーバが `store.DB_PATH`（`ingest/store.py:20`。リポジトリルート直下の
`vector_store.sqlite3`）から自動的に決める。引数にも環境変数にも取らないため、
利用者が DB の場所を設定する項目はない。

### `ollama pull bge-m3` は必須

質問文のベクトル化に使う埋め込みモデルは `bge-m3` である（`ingest/embedder.py` の
`EMBED_MODEL`）。これを導入していないと検索が一切成立しない。導入先で一度だけ
実行する。

**このサーバが Ollama に求めるのは `bge-m3` だけである。** 回答文を作らないため
生成モデル（`gpt-oss:20b` 等）は一切呼ばない。回答を書くのは Codex 側であり、
そのために約13GBを引く必要はない。

```powershell
ollama pull bge-m3
```

取り込み時と検索時で埋め込みモデルが食い違うと、例外は出ないまま検索結果だけが
無意味になる。取り込み側（`scripts/ingest_source.py`）も同じ `bge-m3` を使うため、
このコマンドは検索用と取り込み用を兼ねる。

## `~/.codex/config.toml` への登録

`~/.codex/config.toml` の `mcp_servers` に、社内資料検索・context7（OSSドキュメント
検索）・playwright（ブラウザ操作）の3サーバを登録する。

```toml
[mcp_servers.local_docs]
command = "C:\\...\\local_llm\\myvenv313\\Scripts\\python.exe"
args = ["-m", "scripts.rag_mcp_server"]
cwd = "C:\\...\\local_llm"

[mcp_servers.context7]
url = "https://mcp.context7.com/mcp"
env_http_headers = { "CONTEXT7_API_KEY" = "CONTEXT7_API_KEY" }

[mcp_servers.playwright]
command = "npx"
args = ["-y", "@playwright/mcp@latest"]
```

`command` と `cwd` の `C:\\...\\local_llm` は、実際の `local_llm` の絶対パスに
置き換える。

### `cwd` の指定は必須

`python scripts\rag_mcp_server.py` のように直接起動すると、`sys.path` に
リポジトリルートが入らず `from ingest import ...` が `ModuleNotFoundError` に
なる。`args = ["-m", "scripts.rag_mcp_server"]`（`-m` 起動）と `cwd`
（リポジトリルート）の組み合わせで、`python -m scripts.rag_mcp_server` を
リポジトリルートで実行したのと同じ状態を作る。どちらか一方が欠けても直らない。

### context7 の API キーは値を書かない

`env_http_headers` はヘッダ名 → 参照する環境変数名の対応であり、キーの値そのもの
ではない。上の例では、ヘッダ `CONTEXT7_API_KEY` の値を環境変数 `CONTEXT7_API_KEY`
から取ることを意味する。`config.toml` は秘密情報の置き場所ではない
（リポジトリ内の `.env` と違い `.gitignore` の対象外にあるため、ここに直接
値を書くと平文でホームディレクトリに残る）。

キーは `ctx7sk-` で始まり、Context7 のダッシュボードから無償で取得できる。
未設定でも動作するが、レート制限が厳しくなる。先方環境ではまず未設定で運用し、
制限に当たってから取得すればよい。取得したキーは Windows の環境変数
（例: `setx CONTEXT7_API_KEY "ctx7sk-..."`）として設定し、`config.toml` には
書かない。

### context7 が `npx` ではなく `url` を使う理由

Windows で `npx.cmd` を `command` に指定すると、絶対パス指定や `SystemRoot` /
`APPDATA` の明示が必要になる既知の躓きがある（公式 README にトラブル
シュート専用の設定例が置かれている）。context7 は `url` 方式（streamable HTTP）
に対応しているため、これを避けられる。一方 playwright はブラウザを実際に
起動する都合上ローカル実行が必須で、`url` 方式は選べない。Node.js / `npx` は
playwright を使う導入先に別途必要になる。

## 動作確認

設定を保存したら、Codex を起動し直す。`/mcp` などで `local_docs` が接続済みで
あることを確認したうえで、社内資料に関する質問を投げる。

```text
社内資料で〇〇について調べて、出典を挙げて教えてください。
```

`search_documents` が呼ばれ、`## [1] cosine距離 ... ／ BM25 ... ／ Reranker ...`
の形式で、出典（ファイル名とページ・スライド番号）つきの原文が返れば成功である。

### 初回検索が遅い

リランカー（`bge-reranker-v2-m3`）はサーバ起動時ではなく初回の検索時に遅延
ロードされる。検索しないセッションにロード時間を払わせないためである。

実測（2026-09-08、i5-1240P / Windows 11、570出現・本文512種）:

| 経路 | 初回 | 2回目以降 |
|---|---|---|
| stdio 経由（`tools/call`） | 6.83秒 | 3.53 / 3.47秒 |
| プロセス内（同一クエリ5回） | 6.99秒 | 3.55 / 3.41 / 3.48 / 3.53秒 |

初回だけ遅いのはモデルのロードが原因であり異常ではない。2回目以降が数秒かかるのは
CPUでリランカーを回しているためで、こちらも異常ではない。CPUが違えば数字も変わる
ので、導入先で気になったら測り直すこと。

### 導入直後・DBが空のときの応答

資料を1件も取り込んでいない状態で検索すると、「見つかりませんでした」ではなく
次の文言が返る。

```
ベクトルDBが空です。取り込みが未実行の可能性があります。
python -m scripts.ingest_source を実行してください。
```

導入直後にこの文言が出た場合は、資料の取り込み（前提の3番目）が未実施である
ことを疑う。「関連する記述が無い」旨の応答（4節にある0件時の文言）とは別の
文言なので混同しないこと。

### エラー時の応答

Ollama が起動していない、あるいは `bge-m3` が未導入の場合は、`embedder` が
持つ案内文言（「`ollama pull bge-m3` を実行してください」等）がそのまま返る。
想定内のエラー（Ollama 疎通・埋め込みの失敗）は検索結果と同じ形式のテキストとして
届く。リランカーの取得に失敗した場合は、エラーにせず RRF 順のまま検索を続ける。

それ以外の想定外の例外はサーバプロセスを落とさず、MCP の `is_error=True` な結果に
なる。ただしそこに載るのは `Error executing tool search_documents` という定型文
だけで、元の例外の文面は届かない（mcp 2.2.0 の
`mcp/server/mcpserver/exceptions.py:66-67`）。原因はサーバの標準エラー出力に
トレースバックとして出るので、そちらを見ること。

## 導入先での作業手順（まとめ）

1. `pip install -r requirements.txt`（`mcp` を含む）
2. `ollama pull bge-m3`（生成モデルは不要）
3. 資料を `source/` に配置し、`python -m scripts.ingest_source` で取り込む
4. `~/.codex/config.toml` に上記3サーバを登録する
5. Codex を起動し直し、動作確認の手順で出典が返ることを見る

リランカー（`bge-reranker-v2-m3` ONNX）のモデルは初回実行時に HuggingFace Hub
から自動取得される。導入先はインターネットに到達できる前提のため、事前の
持ち込みは不要である。
