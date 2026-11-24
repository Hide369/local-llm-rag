# MCP サーバを 11434 番で動かし、Claude Code（GB10 のローカルLLM）から社内資料を検索する

検索サーバ機（Windows）で社内資料の MCP サーバを `11434` 番で常駐させ、クライアントPC
の VS Code の Claude Code から検索できるようにする手順である。Claude Code が使う
モデルは GB10 ×2 の `gpt-oss-120b` と `Qwen3-Coder-Next` で、チャット欄のプルダウンで
切り替える。

**前提となる作業**（この順に済ませておく）

| 対象 | 文書 | 状態 |
| --- | --- | --- |
| GB10 ×2 と LiteLLM | [gb10-dual-sglang-setup.md](proxy/gb10-dual-sglang-setup.md) の1〜7章（vLLM 版なら [gb10-dual-llm-setup.md](proxy/gb10-dual-llm-setup.md) の1〜6章） | LiteLLM 経由で両モデルが応答する |
| 検索サーバ機の RAG | [mcp-server-network.md](mcp-server-network.md) の「サーバ機の準備」1〜3（取得・依存関係・Ollama・取り込み） | 資料が取り込み済み |
| 検索サーバ機の Ollama | [ollama-port-11500.md](ollama-port-11500.md) | Ollama が `127.0.0.1:11500`、`11434` が空いている |

クライアントPC側の設定は本書の第2部にすべて書いてある。GB10 の手順書の「クライアント」の章は
読まなくてよい。本書がその上位互換である。

## 構成

```text
[クライアントPC: VS Code + Claude Code 拡張]
   │                                   │
   │ /v1/messages（会話・推論）          │ MCP（検索）  http://<検索サーバIP>:11434/mcp
   ▼                                   ▼
[LiteLLM :4000 @GB10-A]              [検索サーバ機（Windows）]
   ├─▶ GB10-A gpt-oss-120b             ├ rag_mcp_server  0.0.0.0:11434  ← 外向き
   └─▶ GB10-B qwen3-coder-next         ├ vector_store.sqlite3 / source/
                                       └ Ollama 127.0.0.1:11500（bge-m3）← 外から届かない
```

**検索を呼ぶのはクライアントPC上の Claude Code である。** モデル（GB10）は「この
ツールを呼べ」という指示を返すだけで、検索サーバへ直接は繋がない。GB10 から検索
サーバへの経路は要らない。

検索結果（社内資料の原文）は、クライアントPC → LiteLLM → GB10 と流れてモデルに
読まれる。どれも LAN の中であり、外へは出ない。

> **11434 番は MCP である。** 一般には Ollama の標準ポートとして知られている。
> 後で調べる人が誤解しないよう、ファイアウォール規則の表示名（[ollama-port-11500.md](ollama-port-11500.md)
> 手順7）とサーバ機のメモに残しておくこと。

---

# 第1部　検索サーバ機（Windows）

作業はすべて検索サーバ機の PowerShell で行う。リポジトリは `C:\App\local-llm-rag`
にある前提で書く。

## 1. 11434 と Ollama の状態を確かめる

```powershell
Get-NetTCPConnection -LocalPort 11434,11500 -State Listen -ErrorAction SilentlyContinue |
  Select-Object LocalAddress, LocalPort
```

`127.0.0.1:11500` だけが出ること。`11434` が出る場合は、Ollama がまだ `11434` で
動いている。先に [ollama-port-11500.md](ollama-port-11500.md) を済ませる。

## 2. 自機だけで起動して確かめる

先に `127.0.0.1` で起動し、外へ開く前に動くことを見る。**MCP サーバは `.env` を読まない**
ので、`OLLAMA_HOST` をそのシェルで渡す。

```powershell
cd C:\App\local-llm-rag
$env:OLLAMA_HOST = "http://127.0.0.1:11500"
.\myvenv313\Scripts\python.exe -m scripts.rag_mcp_server --http --host 127.0.0.1 --port 11434
```

別の PowerShell から握手（`initialize`）を送る。

```powershell
$body = '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"probe","version":"0"}}}'
Invoke-WebRequest -Uri http://127.0.0.1:11434/mcp -Method Post -Body $body `
  -ContentType "application/json" -Headers @{ Accept = "application/json, text/event-stream" }
```

応答に `local_docs` が含まれれば正しい。**パスは `/mcp` である。** `/` や `/api/tags`
（Ollama の API）に投げると 404 になる。これは 11434 で動いているのが Ollama ではなく
MCP サーバであることの確認にもなる。

検索まで通るかは、第2部の最後（手順10）でクライアントから確かめる。ここでは Ctrl+C で
止める。

## 3. 常駐させる（NSSM）

サービス名は [mcp-server-network.md](mcp-server-network.md) と同じ `local-docs-mcp`
にする。

**まだ登録していない場合**：

```powershell
nssm install local-docs-mcp "C:\App\local-llm-rag\myvenv313\Scripts\python.exe" "-m scripts.rag_mcp_server --http --host 0.0.0.0 --port 11434"
nssm set local-docs-mcp AppDirectory "C:\App\local-llm-rag"
nssm set local-docs-mcp AppEnvironmentExtra "OLLAMA_HOST=http://127.0.0.1:11500"
nssm set local-docs-mcp Start SERVICE_AUTO_START
nssm start local-docs-mcp
```

**`8080` などで登録済みの場合**：引数と環境変数だけを差し替える。

```powershell
nssm stop local-docs-mcp
nssm set local-docs-mcp AppParameters "-m scripts.rag_mcp_server --http --host 0.0.0.0 --port 11434"
nssm get local-docs-mcp AppEnvironmentExtra    # 既存の値を確認してから
nssm set local-docs-mcp AppEnvironmentExtra "OLLAMA_HOST=http://127.0.0.1:11500"
nssm start local-docs-mcp
```

`AppDirectory` は必須である。無いと `ModuleNotFoundError: No module named 'ingest'` で
起動に失敗する。

**Ollama の起動を待たない点に注意する。** Ollama をトレイアプリで動かしている場合、
誰かがログオンするまで Ollama は起動しない。サーバ機の再起動後にログオンしないまま
だと、検索は「Ollamaに接続できません」で失敗する。無人で運用するなら、Ollama も
サービスにするか、自動ログオンを設定する（[mcp-server-network.md](mcp-server-network.md)「6. 常駐させる」）。

起動したら、待ち受けを確かめる。

```powershell
Get-NetTCPConnection -LocalPort 11434,11500 -State Listen |
  Select-Object LocalAddress, LocalPort
```

`0.0.0.0:11434`（MCP）と `127.0.0.1:11500`（Ollama）の2行になれば正しい。

## 4. ファイアウォールを確かめる

11434 の受信規則は [ollama-port-11500.md](ollama-port-11500.md) の手順7で MCP 用に
名前を変えてある。送信元が絞られていることをもう一度確かめる。

```powershell
Get-NetFirewallRule -DisplayName "local-docs MCP (TCP 11434)" |
  Get-NetFirewallAddressFilter | Select-Object RemoteAddress
```

**`Any` のままなら、ここで必ず絞る。** この MCP サーバには認証も暗号化も無く、
ポートに届いた相手へ社内資料の原文を返す（[mcp-server-network.md](mcp-server-network.md)
「何が守られ、何が守られないか」）。

```powershell
# 管理者の PowerShell で。範囲はクライアントPCのサブネットに置き換える
Set-NetFirewallRule -DisplayName "local-docs MCP (TCP 11434)" -RemoteAddress 192.168.1.0/24
```

規則がまだ無い場合は作る。

```powershell
New-NetFirewallRule -DisplayName "local-docs MCP (TCP 11434)" -Direction Inbound `
  -Protocol TCP -LocalPort 11434 -RemoteAddress 192.168.1.0/24 -Action Allow
```

---

# 第2部　クライアントPC（VS Code + Claude Code）

各開発者の PC で行う。クライアントに Python・Ollama・資料は要らない。

**前提**

- VS Code と Claude Code 拡張。プルダウンの設定（`modelPicker`）に **v2.1.242 以降**が要る
- 統合ターミナルで `claude` コマンドが使える（拡張機能は PATH に追加しない。未導入なら
  [claude-code-vscode.md](claude-code-vscode.md)「1. 拡張機能を入れる」で CLI を入れる）

## 5. 検索サーバに届くか確かめる

```powershell
Test-NetConnection <検索サーバIP> -Port 11434   # TcpTestSucceeded : True
Test-NetConnection <検索サーバIP> -Port 11500   # TcpTestSucceeded : False が正しい
```

11434 が `False` なら、サーバ機のファイアウォールで送信元にこの PC が含まれていない（手順4）。
11500 が `True` なら Ollama が外に開いている。[ollama-port-11500.md](ollama-port-11500.md)
の手順3をやり直す。

## 6. VS Code のユーザー設定（接続先と認証）

コマンドパレット（`Ctrl+Shift+P`）で **Preferences: Open User Settings (JSON)** を開き、
次を足す。既存の項目は消さない。

```json
{
  "claudeCode.environmentVariables": [
    { "name": "ANTHROPIC_BASE_URL",   "value": "http://192.168.10.11:4000" },
    { "name": "ANTHROPIC_AUTH_TOKEN", "value": "sk-local-change-me" }
  ]
}
```

IP とトークンは LiteLLM のもの（`master_key`）に置き換える。

ここに書く理由：拡張機能は起動前のログイン確認でこの設定を読む。`~/.claude/settings.json`
にだけ書くと、ログイン画面が出て先へ進めない。

## 7. `~/.claude/settings.json`（プルダウン・モデル・MCP の扱い）

`%USERPROFILE%\.claude\settings.json` を開く。**既にある場合は上書きせず、キーごとに
マージする**（Superpowers プラグインや context7 の設定が入っていることが多い）。

```json
{
  "model": "qwen3-coder-next",
  "modelPicker": {
    "replaceBuiltInOptions": true,
    "options": [
      { "model": "gpt-oss-120b",     "label": "gpt-oss-120b（設計・レビュー）", "description": "GB10-A" },
      { "model": "qwen3-coder-next", "label": "Qwen3-Coder-Next（実装）",       "description": "GB10-B" },
      { "model": "opusplan",         "label": "設計→実装 自動切替",            "description": "プランは gpt-oss、実行は Qwen" }
    ]
  },
  "permissions": {
    "allow": ["mcp__local_docs__search_documents"]
  },
  "env": {
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "gpt-oss-120b",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "qwen3-coder-next",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "qwen3-coder-next",

    "ENABLE_TOOL_SEARCH": "false",

    "CLAUDE_CODE_ATTRIBUTION_HEADER": "0",
    "CLAUDE_CODE_AUTO_COMPACT_WINDOW": "120000",
    "CLAUDE_CODE_MAX_OUTPUT_TOKENS": "16384",
    "API_TIMEOUT_MS": "600000",
    "CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS": "1",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"
  }
}
```

プルダウン・モデルの割り当て・`CLAUDE_CODE_*` の各値の意味は
[gb10-dual-sglang-setup.md](proxy/gb10-dual-sglang-setup.md)「8.2」の表にある。
モデル名（`gpt-oss-120b` / `qwen3-coder-next`）は LiteLLM の `model_name` と**完全に**
一致させる。vLLM 版の LiteLLM で別の名前を付けている場合はそれに合わせる。

本書で足した2つのキーは次のとおりである。

| 設定 | 意味 |
| --- | --- |
| `ENABLE_TOOL_SEARCH: "false"` | **必須。** MCP のツール定義を最初のリクエストから全部モデルに渡す。下の「ツール検索を切る理由」を読むこと |
| `permissions.allow` | 検索のたびに許可を求めるダイアログを出さない。検索は読み取りだけなので許可してよい |

`modelPicker` は**ユーザー設定（このファイル）か管理者設定でしか効かない。**
リポジトリの `.claude/settings.json` に書いても無視される。トークンもリポジトリ側には
書かない（コミットされる）。

### ツール検索を切る理由

Claude Code は MCP のツールが増えたときに備え、ツールの定義をすぐには渡さず、
モデルが `ToolSearch` で探してから読み込む仕組み（ツール検索）を持つ。この仕組みは
Anthropic 固有のフィールド（`defer_loading`・`tool_reference`）に依存している。

v2.1.304 から、`ANTHROPIC_BASE_URL` が LiteLLM のようなゲートウェイを指していても、
ツール検索は**既定で有効**になった（それ以前は既定で無効だった）。ゲートウェイが
400 / 422 を返したときは外して送り直す仕組みがある。しかし SGLang / vLLM がこれらの
フィールドを**エラーにせず黙って無視した**場合は送り直しが起きない。その結果、モデルには
`search_documents` の定義が届かず、呼びようがなくなる。

これは Codex で起きた「ツール名は列挙できるのに一度も呼ばれない」と同じ形の失敗である
（[mcp-tool-not-called.md](mcp-tool-not-called.md)）。`false` にしておけば、定義は毎回
`tools` 配列に入る。本構成の MCP ツールは `search_documents` の1つだけなので、全部
渡してもコンテキストはほとんど食わない。

## 8. MCP サーバを登録する

VS Code の統合ターミナル（`` Ctrl+` ``）で実行する。

```powershell
claude mcp add --transport http --scope user local_docs http://<検索サーバIP>:11434/mcp
claude mcp list
```

`local_docs` が **Connected** になれば正しい。

- **末尾の `/mcp` を省かない。** 省くと 404 になり「応答しない」としか見えない
- **名前は `local_docs` にする。** 手順7の `permissions.allow` と手順9の指示が
  `mcp__local_docs__search_documents` という名前を前提にしている
- `--scope user` にする理由は [claude-code-vscode.md](claude-code-vscode.md)「スコープを選ぶ」にある

## 9. いつ検索するかを `CLAUDE.md` で教える

MCP の登録が教えるのは接続先だけである。**どの質問で検索するかはモデルが決める。**
`~/.claude/CLAUDE.md`（`%USERPROFILE%\.claude\CLAUDE.md`）に、本リポジトリの
[AGENTS.md](../AGENTS.md) の「社内資料の参照」節を貼る。既存のファイルがあれば追記する。
貼る範囲と理由は [claude-code-vscode.md](claude-code-vscode.md)「4. `CLAUDE.md` を置く」にある。

ローカルLLMは Claude ほど自発的にツールを使わないことがある。貼った節の先頭に、
ツール名を明示した1行を足しておく。

```markdown
- 社内資料の検索には `mcp__local_docs__search_documents` ツールを使う。
```

## 10. 反映と動作確認

VS Code を**完全に終了してから**起動し直す（Reload Window では旧設定が残ることがある）。
Claude Code のパネルを開き、新しい会話で次の順に確かめる。

| # | 操作 | 正しい結果 |
| --- | --- | --- |
| 1 | パネルを開く | ログイン画面が出ずにチャット欄が開く（手順6が効いている） |
| 2 | `/status` | `Anthropic base URL` が LiteLLM の URL |
| 3 | プルダウンを開く | 3行（と Default）だけが出る |
| 4 | `/mcp` | `local_docs` が **Connected** |
| 5 | `/context` | Memory files に `~/.claude/CLAUDE.md` が出る |
| 6 | gpt-oss-120b を選び「社内資料で〜を調べて」 | 会話に `search_documents` の呼び出しが表示され、出典つきの回答が返る |
| 7 | Qwen3-Coder-Next に切り替えて同じ質問 | 同上 |
| 8 | ツール名を言わずに社内固有の質問（例：規程の内容） | 自分から検索する |
| 9 | 資料と無縁の質問（ライブラリの使い方など） | 検索が0件なら打ち切り、「社内資料に基づかない一般的な回答」と断って答える |

**6〜8 が本書の要である。** 検索サーバのアクセスログは握手と検索を区別できない
（[mcp-tool-not-called.md](mcp-tool-not-called.md)「先に読むこと」）。呼ばれたかどうかは、
会話に表示されるツール呼び出しで判断する。

ローカルLLMのツール呼び出しには揺れがある（gpt-oss:20b での実測は 14/15）。1回だけ
呼ばれなかったのか、毎回呼ばれないのかを区別するため、同じ質問を3回は投げること。

### 一度も呼ばれないとき

まず、**モデルにツール定義が届いているか**を確かめる。Codex の件はここで止まっていた。

1. GB10-A で LiteLLM を `--detailed_debug` 付きで起動し直す
   （[gb10-dual-sglang-setup.md](proxy/gb10-dual-sglang-setup.md)「7.3」）
2. クライアントから質問を1つ送る
3. ログに出た要求の `tools` 配列に `mcp__local_docs__search_documents` があるかを見る

| `tools` に… | 判断 | 対処 |
| --- | --- | --- |
| 無い | Claude Code が渡していない | `ENABLE_TOOL_SEARCH` が `false` になっているか（`/status` や `claude --debug` のログで確認）、`/mcp` で Connected か |
| `ToolSearch` だけがあり、`search_documents` に `defer_loading` が付いている | ツール検索が効いたまま | 手順7の `env` を見直し、VS Code を完全に再起動する |
| ある | 渡っているのにモデルが呼ばない | 推論エンジンの `--tool-call-parser`（gpt-oss は `gpt-oss`、Qwen は `qwen3_coder`）を確かめる。手順9の1行を足したか。他のツール（ファイル読み取り等）は呼べているか |

## うまくいかないとき

| 症状 | 原因と対処 |
| --- | --- |
| `claude mcp list` で `Failed` | URL 末尾の `/mcp` の欠落、ファイアウォール（手順4）、サービス未起動（`nssm status local-docs-mcp`） |
| 検索結果が「Ollamaに接続できません（http://127.0.0.1:11434）」 | サービスに `OLLAMA_HOST` が渡っていない。手順3の `AppEnvironmentExtra` |
| 検索結果が「Ollamaに接続できません（http://127.0.0.1:11500）」 | Ollama が起動していない。サーバ機にログオンしていない可能性（手順3の注意） |
| 「ベクトルDBが空です」 | 取り込みが未実行。サーバ機で `scripts.ingest_source` を実行する（`.env` か環境変数の `OLLAMA_HOST` を 11500 に揃えてから） |
| 検索のたびに許可ダイアログが出る | `permissions.allow` の名前と `claude mcp add` の名前（`local_docs`）が一致していない |
| 400 エラーで会話が進まない | `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1` と `ENABLE_TOOL_SEARCH=false` が入っているか |
| ログイン画面が出る・プルダウンが変わらない | [gb10-dual-sglang-setup.md](proxy/gb10-dual-sglang-setup.md)「11. トラブルシューティング」 |
| 社内の質問なのに検索しない | 手順9。`/context` に `CLAUDE.md` が出ているか。出ていて呼ばないなら上の「一度も呼ばれないとき」 |

## 制限

- **認証も暗号化も無い。** ファイアウォールの送信元制限が唯一の境界である（手順4）。
  詳しくは [mcp-server-network.md](mcp-server-network.md)「何が守られ、何が守られないか」
- **検索は順番待ちになる。** 1回およそ 3.6 秒、サーバ起動後の初回だけ 8.2 秒
  （[mcp-server-network.md](mcp-server-network.md)「制限」）
- 資料を更新したら、サーバ機で取り込みを実行するだけでよい。MCP サーバの再起動は要らない
- 検索サーバの初回検索は、リランカーのモデル確認のため huggingface.co へ HEAD を送る
  （[AGENTS.md](../AGENTS.md)「外部ドキュメントの参照」）。オフラインの検索サーバでは
  モデルを事前に取得しておく
