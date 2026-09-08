# 社内資料の MCP サーバを1台に集約する（Windows / 非Server）

資料・ベクトルDB・Ollama・MCP サーバを1台の Windows PC に置き、開発者は自分の
PC の Codex から HTTP で引く構成の手順である。Windows Server ではなく、通常の
Windows（10 / 11）を想定する。

1台のPCで完結させる構成は [mcp-server.md](mcp-server.md) にある。そちらは Codex
がサーバを子プロセスとして起動する形（stdio）で、本書の構成とは起動方法も
`config.toml` の書き方も異なる。

## 構成

```text
開発者PC (Codex)  ─┐
開発者PC (Codex)  ─┼─ HTTP :8080/mcp ─▶ サーバPC（Windows 10 / 11）
開発者PC (Codex)  ─┘                      ├ rag_mcp_server（常駐）
                                          ├ vector_store.sqlite3
                                          ├ source/（資料の原本）
                                          └ Ollama :11434
```

クライアント側に必要なものは `config.toml` の1行だけである。Python も Ollama も
資料も要らない。埋め込み計算もリランクもサーバ機で行う。

## 何が守られ、何が守られないか

**先に読むこと。** この構成は社内資料の全文を、ポートに到達できる相手へ返す。

| | 状態 |
| --- | --- |
| 認証 | **無い。** 誰が繋いだかをサーバは区別しない |
| 通信の暗号化 | **無い。** 平文 HTTP である |
| ホスト名の検証 | **効いていない。** MCP SDK の DNS リバインディング保護は既定で有効だが、`allowed_hosts` が空のこの構成では機能しない。任意の `Host` ヘッダで 200 が返ることを実測で確認した（2026-09-08、`Host: 192.168.1.50:8765` で `initialize` が成功） |
| アクセス制限 | **ファイアウォールだけ。** 下の手順で送信元サブネットを絞る |

つまり「認証がある」のではなく「LAN を信頼している」構成である。到達できる範囲を
ファイアウォールで絞ることが唯一の境界であり、それを外すと社内資料が無制限に
読める状態になる。信頼できない端末が同じセグメントにいる、あるいは資料に人事・
契約などの機微情報が含まれるなら、この構成のままでは足りない。認証付きの
リバースプロキシを前段に置くこと（[server-set.md](server-set.md) が Streamlit で
同じ問題に対して採っている形が参考になる）。

## サーバ機の準備

以下では `C:\App\local-llm-rag` に配置する。パスは環境に合わせて読み替える。

### 1. 取得と依存関係

PowerShell で実行する。

```powershell
New-Item -ItemType Directory -Path "C:\App\local-llm-rag" -Force
cd C:\App\local-llm-rag
git clone https://github.com/Hide369/local-llm-rag.git .

python -m venv myvenv313
.\myvenv313\Scripts\pip.exe install -r requirements.txt
```

### 2. Ollama と埋め込みモデル

```powershell
ollama pull bge-m3
```

**これを欠くと検索が一切成立しない。** 埋め込みモデルであり、LLM ではない。この
サーバは LLM を呼ばないので、`gpt-oss:20b` などの生成モデルは不要である。

### 3. 資料を置いて取り込む

```powershell
# 資料を C:\App\local-llm-rag\source\ に配置してから
.\myvenv313\Scripts\python.exe -m scripts.ingest_source
```

`source/` は Git 管理外である。取り込みはこのサーバ機でだけ行う。

### 4. 起動を確認する

先にファイアウォールを開けず、自機だけで確かめる。

```powershell
.\myvenv313\Scripts\python.exe -m scripts.rag_mcp_server --http --host 127.0.0.1 --port 8080
```

別の PowerShell から叩く。

```powershell
$body = '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"probe","version":"0"}}}'
Invoke-WebRequest -Uri http://127.0.0.1:8080/mcp -Method Post -Body $body `
  -ContentType "application/json" -Headers @{ Accept = "application/json, text/event-stream" }
```

`serverInfo` に `local_docs` が含まれれば正しい。パスは `/mcp` である。`/` に投げると
404 になる。

確認できたら Ctrl+C で止める。

### 5. LAN へ開く

`--host 0.0.0.0` で全インターフェースに bind し、到達できる範囲をファイアウォールで
絞る。**この2つは必ずセットにする。** bind だけ広げて規則を書かないと、ポートに
届く全員へ資料が出る。

```powershell
# 送信元を自分のサブネットに限定する。範囲は環境に合わせて必ず書き換える
New-NetFirewallRule -DisplayName "local-docs MCP" -Direction Inbound `
  -Protocol TCP -LocalPort 8080 -RemoteAddress 192.168.1.0/24 -Action Allow
```

`-RemoteAddress` を省略すると「どこからでも許可」になる。省略しないこと。

### 6. 常駐させる

通常の Windows には Linux の systemd に相当する仕組みが無いので、
[NSSM](https://nssm.cc/) でサービス登録する。`server-set.md` の Streamlit と同じ
方式である。

```powershell
nssm install local-docs-mcp "C:\App\local-llm-rag\myvenv313\Scripts\python.exe" "-m scripts.rag_mcp_server --http --host 0.0.0.0 --port 8080"
nssm set local-docs-mcp AppDirectory "C:\App\local-llm-rag"
nssm set local-docs-mcp AppEnvironmentExtra "OLLAMA_HOST=http://127.0.0.1:11434"
nssm set local-docs-mcp Start SERVICE_AUTO_START
nssm start local-docs-mcp
```

`AppDirectory` の指定は必須である。`-m` 起動でリポジトリルートが `sys.path` に
入る必要があり、これを欠くと `ModuleNotFoundError: No module named 'ingest'` で
起動に失敗する。

**Ollama の起動タイミングに注意する。** Windows 版 Ollama は既定でユーザーの
ログオン時に起動する。MCP サーバをサービスとして起動時に上げると、誰もログオン
していない状態では Ollama が居らず、検索が「Ollama に接続できません」で失敗する。
サーバ機を無人運用するなら、Ollama 自体もサービスとして常駐させるか、サーバ機に
自動ログオンするアカウントを用意する。

## クライアント側の設定

各開発者の `~/.codex/config.toml` に足す。

```toml
[mcp_servers.local_docs]
url = "http://192.168.1.50:8080/mcp"
```

IP はサーバ機のものに置き換える。**末尾の `/mcp` を省かないこと。** 省くと 404 に
なり、Codex 側からは「サーバが応答しない」としか見えない。

`command` / `args` / `cwd` は書かない。それは1台構成（stdio）の書き方であり、
[mcp-server.md](mcp-server.md) にある。両方を書くと衝突する。

## 動作確認

Codex に「社内資料で〜を調べて」と頼み、出典つきの原文が返ることを見る。

DB が空のままだと「ベクトルDBが空です。取り込みが未実行の可能性があります」と
返る。「見つかりませんでした」とは別の文言なので、資料に無いのか取り込みを
忘れているのかは区別できる。

## 運用

**資料を更新したら、サーバ機で取り込みを実行するだけでよい。サーバの再起動は
要らない。** サーバは書き込みトランザクションの内側で加算される `revision()` を
リクエストごとに読み、変化していれば BM25 索引を組み直す。取り込み中に検索が
来ても待たされない（SQLite の読み手は書き込み中も一貫したスナップショットを
得る）。レビュー時の実測で、取り込み後に件数と revision の変化が即座に反映され、
新しい本文が結果に現れること、削除も同様に伝わることを確認している。

ただしサーバ起動後の**最初の1回**だけは、スキーマ確認のための書き込みを行う。
これがたまたま取り込みの書き込みと重なると、その1回は待たされる。

## 制限

**同時アクセスは順番待ちになる。** 検索は直列化してある。複数PCから同時に引くと
共有キャッシュが競合し、例外を出さないまま検索結果がずれるためである。

検索1回はおよそ **3.6 秒**、サーバ起動後の**初回だけ 8.2 秒**である（この構成
そのもの、つまり `--http` で起動したサーバへ HTTP の `tools/call` を投げて計測。
2026-09-08、i5-1240P / Windows 11、570 出現・本文 512 種）。初回の上乗せは
リランカーの読み込みである。

3人が同時に叩けば、最後の1人はおよそ 11 秒待つ。

少人数で使う前提の割り切りである。常時 10 人が叩くような使い方をするなら、
直列化ではなく読み取り側の作り直しが要る。
