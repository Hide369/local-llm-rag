# 11434 番をリバースプロキシにして、推論（Ollama）と MCP を振り分ける（Windows）

検索サーバ機（Windows）の外向き `11434` 番に Caddy を置き、URL のパスで
**MCP サーバ**と **Ollama** に振り分ける手順である。外に開けるポートは `11434`
のまま増やさない。

- `/mcp` → 社内資料の MCP サーバ（`local-docs-mcp`、`127.0.0.1:8080`）
- `/api/*`・`/v1/*`（推論に要るものだけ）→ Ollama（`127.0.0.1:11500`）
- それ以外 → Caddy が 404 を返す

**前提となる作業**（この順に済ませておく）

| 対象 | 文書 | 状態 |
| --- | --- | --- |
| Ollama の移設 | [ollama-port-11500.md](ollama-port-11500.md) | Ollama が `127.0.0.1:11500` で待ち受けている |
| MCP サーバ | [mcp-server-11434-claude-code.md](mcp-server-11434-claude-code.md) 第1部 | `local-docs-mcp` が NSSM で常駐している（今は `0.0.0.0:11434`） |

クライアントの Claude Code の設定（MCP の URL `http://<検索サーバIP>:11434/mcp`）は
**変えなくてよい**。パスが同じなので、間に Caddy が入っても気づかない。

## 変更後の構成

```text
[クライアントPC]
   │  http://<検索サーバIP>:11434/mcp      （MCP：社内資料の検索）
   │  http://<検索サーバIP>:11434/api/...   （推論：Ollama ネイティブ API）
   │  http://<検索サーバIP>:11434/v1/...    （推論：OpenAI 互換 API）
   ▼
[検索サーバ機（Windows）]
   Caddy 0.0.0.0:11434  ← 外向きはここだけ
     ├─ /mcp            ─▶ local-docs-mcp 127.0.0.1:8080
     ├─ /api/chat 等    ─▶ Ollama         127.0.0.1:11500
     └─ その他          ─▶ 404
```

| ポート | 待ち受け | 外から届くか |
| --- | --- | --- |
| 11434（Caddy） | `0.0.0.0` | 届く（ファイアウォールで送信元を絞る） |
| 8080（MCP サーバ） | `127.0.0.1` | 届かない |
| 11500（Ollama） | `127.0.0.1` | 届かない（Caddy 経由でだけ届く） |

RAG（取り込み・Streamlit 画面・MCP サーバ）は今までどおり `http://127.0.0.1:11500`
へ直接繋ぐ。`OLLAMA_HOST` は変えない。

## 先に知っておくこと

### Ollama が LAN に見えるようになる

[ollama-port-11500.md](ollama-port-11500.md) では「Ollama は外から届かない」状態にした。
本書はそれを**意図して崩し**、Caddy 経由で推論 API だけを LAN に出す。Ollama には
認証が無いので、次の2つで守る。

1. **パスを絞る。** Ollama の API には `/api/pull`・`/api/delete`・`/api/create`・`/api/copy`・`/api/push`
   がある。素通しにすると、LAN の誰でもモデルを消したり入れたりできる。Caddyfile では
   推論と一覧に要るパスだけを Ollama へ通し、残りは 404 にする（手順3）。
2. **送信元を絞る。** 11434 のファイアウォール規則をクライアントのサブネットに限る（手順6）。

MCP サーバも認証・暗号化は無いままである（[mcp-server-network.md](mcp-server-network.md)
「何が守られ、何が守られないか」）。プロキシを挟んでもこれは変わらない。トークンで
守りたい場合は「任意：トークン認証を足す」を行う。

### Host ヘッダを書き換える理由

Ollama はループバック（`127.0.0.1`）で待ち受けているとき、`Host` ヘッダが
`localhost`・`127.0.0.1` 以外の要求を **403 で拒否する**（DNS リバインディング対策）。
Caddy は既定でクライアントが送った `Host: <検索サーバIP>:11434` をそのまま渡すので、
Ollama 向けだけ `header_up Host {upstream_hostport}` で `127.0.0.1:11500` に書き換える。

MCP サーバは `allowed_hosts` が空で、任意の `Host` を受け付ける（[mcp-server-network.md](mcp-server-network.md)）。
こちらは書き換えなくてよい。

### バッファリングを止める理由

Ollama の生成はストリーミング（NDJSON / SSE）、MCP の Streamable HTTP も SSE で
応答を返すことがある。プロキシが応答を溜めると、トークンが一度に届いたり、MCP の
呼び出しが応答待ちのまま止まったりする。両方に `flush_interval -1` を付けて、
届いた分をすぐ流す。

---

## 1. 現状を確かめる

```powershell
Get-NetTCPConnection -LocalPort 11434,11500,8080 -State Listen -ErrorAction SilentlyContinue |
  Select-Object LocalAddress, LocalPort, OwningProcess
```

`0.0.0.0:11434`（MCP サーバ）と `127.0.0.1:11500`（Ollama）の2行が出ること。
`8080` に何か出る場合は、別のプログラムが使っている。本書の `8080` を空いている
番号に読み替える。

## 2. MCP サーバを 127.0.0.1:8080 へ移す

11434 を Caddy に譲るため、MCP サーバの待ち受けを内側へ移す。

```powershell
nssm stop local-docs-mcp
nssm set local-docs-mcp AppParameters "-m scripts.rag_mcp_server --http --host 127.0.0.1 --port 8080"
nssm get local-docs-mcp AppEnvironmentExtra    # OLLAMA_HOST=http://127.0.0.1:11500 のままであること
nssm start local-docs-mcp
```

**`--host 127.0.0.1` にする。** `0.0.0.0` のままだと、ファイアウォール次第で 8080 に
直接届き、プロキシの意味がなくなる。

握手（`initialize`）が通るか確かめる。

```powershell
$body = '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"probe","version":"0"}}}'
Invoke-WebRequest -Uri http://127.0.0.1:8080/mcp -Method Post -Body $body `
  -ContentType "application/json" -Headers @{ Accept = "application/json, text/event-stream" }
```

応答に `local_docs` が含まれれば正しい。この時点から Caddy を起動するまでの間、
クライアントからの検索は失敗する。作業は利用者の少ない時間に行う。

## 3. Caddy を置き、Caddyfile を書く

1. [Caddy のダウンロードページ](https://caddyserver.com/download) から Windows amd64 版を取り、
   `C:\caddy\caddy.exe` に置く。ログ用に `C:\caddy\logs` を作る。

    ```powershell
    New-Item -ItemType Directory -Force C:\caddy\logs | Out-Null
    C:\caddy\caddy.exe version
    ```

2. `C:\caddy\Caddyfile`（拡張子なし）を次の内容で作る。

    ```caddyfile
    :11434 {
        route {
            # MCP（社内資料の検索）
            @mcp path /mcp /mcp/*
            reverse_proxy @mcp 127.0.0.1:8080 {
                flush_interval -1
            }

            # Ollama：推論と一覧に要るものだけ通す
            @ollama path /api/chat /api/generate /api/embed /api/embeddings /api/tags /api/show /api/ps /api/version /v1/*
            reverse_proxy @ollama 127.0.0.1:11500 {
                flush_interval -1
                header_up Host {upstream_hostport}
            }

            # それ以外（/api/pull, /api/delete など）は拒否
            respond 404
        }

        log {
            output file C:/caddy/logs/access.log {
                roll_size 10MiB
                roll_keep 5
            }
        }
    }
    ```

    - `:11434` のようにホスト名を書かないサイトは HTTP で待ち受ける。Caddy は証明書を取りに行かない。
    - `route` の中は**上から順に**評価され、最初に当たった `reverse_proxy` / `respond` で終わる。
      順番を入れ替えると振り分けが変わる。
    - ログのパスは `/` 区切りで書く。

3. 書式を確かめる。

    ```powershell
    C:\caddy\caddy.exe fmt --overwrite C:\caddy\Caddyfile
    C:\caddy\caddy.exe validate --config C:\caddy\Caddyfile
    ```

    `Valid configuration` と出れば正しい。

## 4. 手動で起動して確かめる

```powershell
C:\caddy\caddy.exe run --config C:\caddy\Caddyfile
```

別の PowerShell から確かめる。

```powershell
# 推論側（Ollama）
Invoke-RestMethod http://127.0.0.1:11434/api/version
Invoke-RestMethod http://127.0.0.1:11434/api/tags | Select-Object -ExpandProperty models | Select-Object name
Invoke-RestMethod http://127.0.0.1:11434/v1/models

# 管理系は止まっていること（404 が正しい）
curl.exe -s -o NUL -w "%{http_code}`n" -X DELETE http://127.0.0.1:11434/api/delete

# MCP 側
Invoke-WebRequest -Uri http://127.0.0.1:11434/mcp -Method Post -Body $body `
  -ContentType "application/json" -Headers @{ Accept = "application/json, text/event-stream" }
```

`$body` は手順2のものを使う。`/api/tags` にモデル一覧、`/mcp` に `local_docs` が
返り、`/api/delete` が `404` なら正しい。

ストリーミングが溜まらずに流れるかも見ておく。`<モデル名>` は `/api/tags` に出た
生成用モデルに置き換える（`bge-m3` は埋め込み専用なので生成できない）。

```powershell
'{"model":"<モデル名>","prompt":"count from 1 to 10"}' | Out-File -Encoding ascii $env:TEMP\gen.json
curl.exe -N http://127.0.0.1:11434/api/generate --data-binary "@$env:TEMP\gen.json"
```

行が少しずつ出てくれば正しい。最後にまとめて出る場合は `flush_interval -1` が
効いていない。確かめたら Ctrl+C で Caddy を止める。

## 5. 常駐させる（NSSM）

MCP サーバと同じく NSSM でサービスにする。

```powershell
nssm install caddy-proxy "C:\caddy\caddy.exe" "run --config C:\caddy\Caddyfile"
nssm set caddy-proxy AppDirectory "C:\caddy"
nssm set caddy-proxy AppStdout "C:\caddy\logs\service.log"
nssm set caddy-proxy AppStderr "C:\caddy\logs\service.log"
nssm set caddy-proxy Start SERVICE_AUTO_START
nssm start caddy-proxy
```

待ち受けを確かめる。

```powershell
Get-NetTCPConnection -LocalPort 11434,11500,8080 -State Listen |
  Select-Object LocalAddress, LocalPort, OwningProcess
```

`0.0.0.0:11434`（Caddy）・`127.0.0.1:8080`（MCP）・`127.0.0.1:11500`（Ollama）の3行になれば
正しい。

Caddyfile を直したあとは `nssm restart caddy-proxy` で読み直す。

**起動順は気にしなくてよい。** Caddy が先に上がっても、裏の MCP サーバや Ollama が
起きるまでは 502 を返すだけで、起きれば自然に繋がる。ただし Ollama をトレイアプリで
動かしている場合、誰かがログオンするまで推論は 502 のままである
（[mcp-server-11434-claude-code.md](mcp-server-11434-claude-code.md) 手順3の注意と同じ）。

## 6. ファイアウォールの規則名と送信元を直す

11434 の受信規則は今 `local-docs MCP (TCP 11434)` という名前である。中身が Caddy に
変わったので、後で見た人が誤解しないよう表示名を変える。

```powershell
# 管理者の PowerShell で
Set-NetFirewallRule -DisplayName "local-docs MCP (TCP 11434)" `
  -NewDisplayName "Caddy proxy: Ollama + local-docs MCP (TCP 11434)"

Get-NetFirewallRule -DisplayName "Caddy proxy: Ollama + local-docs MCP (TCP 11434)" |
  Get-NetFirewallAddressFilter | Select-Object RemoteAddress
```

`RemoteAddress` が `Any` なら必ず絞る。範囲はクライアントPCのサブネットに置き換える。

```powershell
Set-NetFirewallRule -DisplayName "Caddy proxy: Ollama + local-docs MCP (TCP 11434)" -RemoteAddress 192.168.1.0/24
```

8080 と 11500 の受信規則は作らない。初回起動時に「アクセスを許可しますか」と
聞かれても許可しない。

サーバ機のメモにも「11434 は Caddy（`/mcp` は MCP、`/api`・`/v1` は Ollama）」と残す。

## 7. クライアントPCから確かめる

```powershell
Test-NetConnection <検索サーバIP> -Port 11434   # True が正しい
Test-NetConnection <検索サーバIP> -Port 8080    # False が正しい
Test-NetConnection <検索サーバIP> -Port 11500   # False が正しい

Invoke-RestMethod http://<検索サーバIP>:11434/api/tags | Select-Object -ExpandProperty models | Select-Object name
```

MCP は VS Code の統合ターミナルで確かめる。設定は変えていないので、そのまま繋がるはずである。

```powershell
claude mcp list    # local_docs: http://<検索サーバIP>:11434/mcp - ✓ Connected
```

推論を使うクライアントの接続先は次のとおり。

| 使い方 | 接続先 |
| --- | --- |
| Ollama ネイティブ API（Python の `ollama` ライブラリ、Open WebUI など） | `http://<検索サーバIP>:11434` |
| OpenAI 互換 API | `http://<検索サーバIP>:11434/v1`（API キーは任意の文字列でよい） |
| `ollama` コマンド（クライアントから） | `$env:OLLAMA_HOST = "http://<検索サーバIP>:11434"` のうえで `ollama list` / `ollama run`。`ollama pull` / `rm` は 404 で失敗する（意図どおり） |

## 任意：トークン認証を足す

送信元の制限だけでは足りない場合、`route` の先頭に Bearer トークンの確認を足す。
トークンは推測されにくい長い文字列にする（例：`[guid]::NewGuid()` を2つつなげる）。

```caddyfile
:11434 {
    route {
        @noauth not header Authorization "Bearer <トークン>"
        respond @noauth 401

        # 以下、手順3と同じ
        @mcp path /mcp /mcp/*
        ...
    }
}
```

クライアント側でトークンを送れるかは使い方で変わる。

| クライアント | 送り方 |
| --- | --- |
| Claude Code の MCP | `claude mcp add` の `--header "Authorization: Bearer <トークン>"`（設定し直しが要る） |
| OpenAI 互換クライアント | API キーにトークンを入れる（`Authorization: Bearer` で送られる） |
| Python の `ollama` ライブラリ | `Client(host=..., headers={"Authorization": "Bearer <トークン>"})` |
| `ollama` コマンド | ヘッダを足せないため使えなくなる |

Caddyfile にトークンを直書きすることになるので、`C:\caddy` のアクセス権を管理者と
サービスのアカウントだけに絞る。

## 完了の確認

- [ ] `11434` を Caddy、`8080` を MCP サーバ（`127.0.0.1`）、`11500` を Ollama（`127.0.0.1`）が待ち受けている
- [ ] `http://127.0.0.1:11434/api/tags` にモデル一覧、`/mcp` の `initialize` に `local_docs` が返る
- [ ] `/api/delete` などの管理系が 404 になる
- [ ] ストリーミング生成が少しずつ届く
- [ ] `caddy-proxy` サービスが自動起動になっている
- [ ] 11434 の規則名が Caddy 用になり、送信元が絞られている
- [ ] クライアントPCから 11434 に届き、8080 と 11500 に**届かない**
- [ ] クライアントの `claude mcp list` で `local_docs` が `Connected`

## うまくいかないとき

| 症状 | 原因と対処 |
| --- | --- |
| Caddy が `bind: Only one usage of each socket address` で起動しない | MCP サーバがまだ 11434 にいる。手順2の `AppParameters` と `nssm restart local-docs-mcp` を確かめる |
| `/api/*` が 403 | `Host` ヘッダが書き換わっていない。Ollama 側の `header_up Host {upstream_hostport}` を確かめる |
| `/api/*` が 502 | Ollama が起きていない（トレイアプリで未ログオン）、または 11500 以外で待ち受けている。`Invoke-RestMethod http://127.0.0.1:11500/api/version` で直接確かめる |
| `/mcp` が 502 | MCP サーバが落ちている、または 8080 以外で待ち受けている。`nssm status local-docs-mcp` と手順2の `initialize` |
| 使いたい API が 404 | `@ollama` の `path` に入っていない。必要なパスを足して `nssm restart caddy-proxy` |
| 生成が最後にまとめて届く・MCP の呼び出しが返らない | `flush_interval -1` が抜けている |
| 特定のクライアントだけ動かない | 本書のパス制限に掛かっている。そのクライアントが何を叩くかを `C:\caddy\logs\access.log` で見て、推論系なら `path` に足す |
| クライアントから全部つながらない | ファイアウォールの送信元にその PC が含まれていない（手順6） |

## 元に戻す

```powershell
nssm stop caddy-proxy
nssm remove caddy-proxy confirm

nssm stop local-docs-mcp
nssm set local-docs-mcp AppParameters "-m scripts.rag_mcp_server --http --host 0.0.0.0 --port 11434"
nssm start local-docs-mcp

# 管理者の PowerShell で
Set-NetFirewallRule -DisplayName "Caddy proxy: Ollama + local-docs MCP (TCP 11434)" `
  -NewDisplayName "local-docs MCP (TCP 11434)"
```

これで [mcp-server-11434-claude-code.md](mcp-server-11434-claude-code.md) の構成
（11434 は MCP だけ、Ollama は外から届かない）に戻る。`C:\caddy` は残しても害はない。
