# Windows PC 上の gpt-oss と Playwright MCP の設定

Windows Server ではない通常の Windows PC を推論サーバーとし、別の Windows PC で Codex を使う構成を対象にする。以下では、推論サーバーを **サーバーPC**、Codex を操作する端末を **クライアントPC** と呼ぶ。

## 結論と推奨構成

同一 PC 内では HTTPS は不要である。クライアントPCとサーバーPCが別でも、閉じた信頼済み LAN 内だけで使うなら、Ollama の推論 API は HTTP で動かせる。ただしプロンプト、ソースコード、ツール結果が平文で流れるため、VPN 外・共有 Wi-Fi・インターネットへは公開しない。

Playwright MCP はクライアントPCで `stdio` 接続として起動する構成を推奨する。この場合、MCP のために HTTP/HTTPS ポートを開く必要はない。ブラウザーもクライアントPCで起動する。

```text
クライアントPC
  Codex ── stdio ── Playwright MCP ── ブラウザー
    │
    └── HTTP (信頼済み LAN のみ) ──> サーバーPC: Ollama / gpt-oss
```

MCP サーバーを LAN に公開する構成は、ブラウザー操作権限をネットワークへ出すことになるため推奨しない。サーバーPC上のブラウザーを操作する必要がある場合は、クライアントPCからリモート デスクトップでサーバーPCへ接続し、そのセッション内で Codex と Playwright MCP を起動する。

## 前提

- サーバーPC: Windows 10/11、Ollama、`gpt-oss:20b`（または使用する gpt-oss モデル）
- クライアントPC: Windows 10/11、Codex、Node.js 20 以降
- 両 PC は信頼できる LAN または VPN 内にあり、サーバーPCの固定 IP アドレスまたは予約済み DHCP アドレスを使う

このリポジトリの `scripts.coding_agent --setup` は Colab 向けで、`.env` の `OLLAMA_HOST` に HTTPS URL を要求する。LAN 上の HTTP 接続にはその設定を流用せず、以下の独立した Codex 設定を使用する。

## 1. サーバーPC: Ollama を LAN 向けに設定する

管理者権限ではない PowerShell で、Ollama を全インターフェースで待ち受けるようにユーザー環境変数を設定する。設定後、タスクトレイの Ollama を終了してから起動し直す。

```powershell
[Environment]::SetEnvironmentVariable("OLLAMA_HOST", "0.0.0.0:11434", "User")
```

モデルを取得し、サーバーPC自身から応答を確認する。

```powershell
ollama pull gpt-oss:20b
Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags"
```

次に、**管理者として起動した PowerShell** で、クライアントPCの IP アドレスだけから TCP 11434 への受信を許可する。`192.168.1.50` は実際のクライアントPCの IP アドレスに置き換える。ネットワーク全体を許可する `Any` や `0.0.0.0/0` は指定しない。

```powershell
New-NetFirewallRule `
  -DisplayName "Ollama from Codex client" `
  -Direction Inbound `
  -Action Allow `
  -Protocol TCP `
  -LocalPort 11434 `
  -RemoteAddress "192.168.1.50"
```

クライアントPCから、サーバーPCの IP アドレスを使って確認する。

```powershell
Invoke-RestMethod -Uri "http://192.168.1.10:11434/api/tags"
```

ここで接続できない場合は、Ollama を再起動したこと、両 PC のネットワーク プロファイルが「プライベート」であること、ファイアウォール規則の `RemoteAddress` がクライアントPCと一致することを確認する。

## 2. クライアントPC: Codex の推論先と Playwright MCP を設定する

Node.js と `npx` を確認する。

```powershell
node --version
npx --version
```

Codex が読む `config.toml` に、推論プロバイダーと Playwright MCP を設定する。既存の `config.toml` を使う場合は、その内容を保持して次の設定を追加または調整する。`192.168.1.10` はサーバーPCの IP アドレスへ置き換える。

```toml
model = "gpt-oss:20b"
model_provider = "ollama-lan"

[model_providers.ollama-lan]
name = "Windows LAN Ollama"
base_url = "http://192.168.1.10:11434/v1"
wire_api = "responses"
requires_openai_auth = false
request_max_retries = 1
stream_max_retries = 0
stream_idle_timeout_ms = 120000

[mcp_servers.playwright]
command = "npx"
args = ["-y", "@playwright/mcp@latest", "--caps=testing", "--isolated"]
startup_timeout_sec = 30
tool_timeout_sec = 120
default_tools_approval_mode = "writes"
```

`base_url` の `/v1` は必要である。Codex は Ollama の Responses API に `/responses` を追加して接続する。Ollama は 0.13.4 以降を使用する。

`--isolated` は一時ブラウザープロファイルを使うため、既存のログイン情報や Cookie を通常は引き継がない。ログイン済みのブラウザーを使う必要がある場合だけ、このオプションを外し、操作対象のサイトと権限を最小限にする。

設定後に Codex を起動し、チャットで `/mcp` を実行して `playwright` が接続済みであることを確認する。最初の検証では、ローカル開発サーバーを起動してから、変更を伴わない依頼を行う。

```text
http://127.0.0.1:3000 を開き、見出しが表示されることを確認してください。
ファイルやデータは変更しないでください。
```

## HTTPS が必要になる場合

次のいずれかに該当するときは、サーバーPCへの素の HTTP 接続を使わない。HTTPS/TLS、認証、アクセス元制限を備えたリバースプロキシまたは VPN を先に用意する。

- サーバーPCをインターネット、共有 Wi-Fi、または信頼できない LAN から到達可能にする
- クライアントPCの IP アドレスを限定できない
- プロンプトやツール出力に機密情報が含まれる
- Playwright MCP を `--host 0.0.0.0` で公開しようとしている

Playwright MCP の単体 HTTP サーバーは `npx @playwright/mcp@latest --port 8931` で起動できるが、これは通常 `http://localhost:8931/mcp` 用である。`--host 0.0.0.0` で LAN 公開する前に、TLS 終端、クライアント認証、Origin 検証、送信元 IP 制限を必ず設計する。ブラウザー制御を提供する MCP に認証なしの LAN 公開をしてはいけない。

## トラブルシューティング

- Codex がモデルへ接続できない: サーバーPCで `ollama --version` を確認し、クライアントPCで `http://<server-ip>:11434/api/tags` を実行する。`/v1/responses` に直接アクセスして確認する必要はない。
- `playwright` が `/mcp` に表示されない: `node --version`、`npx --version`、`config.toml` の `command` と `args` を確認して Codex を再起動する。
- 初回だけ起動に失敗する: `npx` が Playwright MCP とブラウザーを取得するため、クライアントPCに一時的なインターネット接続が必要なことがある。取得後もパッケージ更新時には接続が必要になる。
- ページ操作でログイン状態が見つからない: `--isolated` の動作である。必要性を確認したうえで外すが、個人用・管理者用ブラウザープロファイルは使わない。

## 参考資料

- [Playwright MCP: Configuration](https://playwright.dev/mcp/configuration/options)
- [MCP: Transports and security guidance](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports)
- [OpenAI: Codex agent loop and local gpt-oss endpoint](https://openai.com/index/unrolling-the-codex-agent-loop/)
