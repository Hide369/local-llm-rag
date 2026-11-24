# 検索サーバ機の Ollama を 11500 番へ移す（Windows）

検索サーバ機（Windows）で動いている Ollama の待ち受けを `11434` から
`127.0.0.1:11500` へ移し、RAG（取り込み・Streamlit 画面・MCP サーバ）をその Ollama
に繋ぎ直す手順である。

**目的**：外向きに開けてある `11434` 番を空け、後で社内資料の MCP サーバに使う。
MCP サーバを `11434` で動かす手順は本書の範囲外で、次の文書で扱う。

> `11434` は Ollama の標準ポートとして広く知られている。MCP をこの番号で動かすと、
> 後から見た人が「Ollama が外に開いている」と誤解しやすい。ファイアウォール規則の
> 表示名とサーバ機のメモに、**11434 は MCP である**と必ず残すこと（手順7）。

## 変更後の構成

```text
[クライアントPC] ──TCP 11434──▶ [検索サーバ機]
                                  ├ (後で) MCP サーバ 0.0.0.0:11434
                                  └ Ollama 127.0.0.1:11500  ← 外から届かない
```

| ポート | 待ち受け | 外から届くか |
| --- | --- | --- |
| 11500（Ollama） | `127.0.0.1` | 届かない（ループバックだけで待ち受けるため） |
| 11434 | 本書の完了時点では空き | 既存のファイアウォール規則は残す（後で MCP が使う） |

## 先に知っておくこと

### 1つの変数を2者が読む

環境変数 `OLLAMA_HOST` は Ollama 本体と RAG の両方が読む。

| 読む側 | 使い方 |
| --- | --- |
| Ollama 本体（`ollama serve`・トレイアプリ・`ollama` コマンド） | 待ち受けるアドレス、`ollama pull` 等の接続先 |
| RAG（[ingest/embedder.py:15-17](../ingest/embedder.py#L15-L17)） | 埋め込み・生成・画像説明の接続先。未設定なら `http://127.0.0.1:11434` |

値は **`http://127.0.0.1:11500`** と書く。

- **`http://` を必ず付ける。** RAG は値の後ろに `/api/embed` などを足して URL を作る
  ので、`127.0.0.1:11500` だけでは URL にならず接続に失敗する。Ollama は `http://`
  付きの値も読める（Ollama の `envconfig.Host()` が `://` の有無を両方受け付ける）。
- **ポートを省略しない。** `http://127.0.0.1` と書くと、Ollama はポートを 80 と
  解釈する（`http://` 付きでポートが無い場合、既定ポートは 80 になる）。
- **`0.0.0.0` にしない。** 外から届くようになり、本書の目的が崩れる。

### 設定がどこから入るかは起動方法で決まる

| 起動されるもの | `OLLAMA_HOST` の入り口 |
| --- | --- |
| Ollama（トレイアプリ） | ユーザー／システムの環境変数 |
| Ollama（NSSM サービスにしている場合） | NSSM の `AppEnvironmentExtra` |
| MCP サーバ（`scripts.rag_mcp_server`） | 環境変数のみ。**`.env` は読まない**（`load_dotenv()` を呼んでいない） |
| Streamlit 画面（`rag_chat_app.py`）・取り込み（`scripts.ingest_source`） | 環境変数、無ければ `.env` |

`.env` は**既存の環境変数を上書きしない**（python-dotenv の既定動作）。手順3で
`OLLAMA_HOST` を環境変数にすると、`.env` の `OLLAMA_HOST` は無視される。食い違うと
「画面では動くのに MCP では動かない」といった、症状だけでは原因が分かりにくい
ずれになるので、手順5で `.env` も揃える。

## 手順

作業はすべて検索サーバ機の PowerShell で行う。リポジトリは `C:\App\local-llm-rag`
にある前提で書く（[mcp-server-network.md](mcp-server-network.md) と同じ）。違う場合は
読み替える。

### 1. 現状を記録する

戻せるように、変更前の状態を控えておく。

```powershell
# 11434 / 11500 を誰が使っているか
Get-NetTCPConnection -LocalPort 11434,11500 -State Listen -ErrorAction SilentlyContinue |
  Select-Object LocalAddress, LocalPort, OwningProcess,
    @{ n = "Process"; e = { (Get-Process -Id $_.OwningProcess).ProcessName } }

# OLLAMA_HOST がどこに設定されているか（両方見る）
[Environment]::GetEnvironmentVariable("OLLAMA_HOST", "User")
[Environment]::GetEnvironmentVariable("OLLAMA_HOST", "Machine")

# 11434 のファイアウォール規則
Get-NetFirewallPortFilter -Protocol TCP |
  Where-Object LocalPort -eq 11434 | Get-NetFirewallRule |
  Select-Object DisplayName, Enabled, Direction, Action
```

**11500 が既に使われていたら、本書の手順を進めない。** 別の空き番号を選び、以降の
`11500` を読み替える。

`Machine`（システム）側に `OLLAMA_HOST=0.0.0.0` などが入っている場合が多い。11434 を
外に開けるために設定したものである。手順3で消す。

### 2. Ollama を止める

タスクバー右下の Ollama アイコンを右クリックし、**Quit Ollama** を選ぶ。

NSSM でサービスにしている場合は、サービスを止める（サービス名は環境に合わせる）。

```powershell
nssm stop ollama
```

続けて、RAG 側のサービスも止める。動いたままだと、Ollama が止まっている間に
検索が失敗する。

```powershell
# 登録済みのものだけ（名前は mcp-server-network.md / server-set.md の例）
nssm stop local-docs-mcp
nssm stop local-llm-rag
```

止まったことを確かめる。何も出なければよい。

```powershell
Get-NetTCPConnection -LocalPort 11434 -State Listen -ErrorAction SilentlyContinue
```

### 3. Ollama の待ち受けを 11500 にする

**トレイアプリで動かしている場合**：ユーザー環境変数に設定する。システム側に古い値が
あれば消す（どちらにも値があるとユーザー側が優先されるが、混乱の元になる）。

```powershell
[Environment]::SetEnvironmentVariable("OLLAMA_HOST", "http://127.0.0.1:11500", "User")

# システム側に値があった場合のみ。管理者の PowerShell で実行する
[Environment]::SetEnvironmentVariable("OLLAMA_HOST", $null, "Machine")
```

Ollama アプリの設定画面に **Expose Ollama to the network** がある版では、オフにして
おく。オンのままだと `0.0.0.0` で待ち受ける可能性がある。手順4の確認で
`LocalAddress` が `127.0.0.1` であることを必ず見る。

スタートメニューから **Ollama** を起動し直す。

**NSSM でサービスにしている場合**：

```powershell
nssm set ollama AppEnvironmentExtra "OLLAMA_HOST=http://127.0.0.1:11500"
nssm start ollama
```

`AppEnvironmentExtra` に他の変数（`OLLAMA_MODELS` 等）も入れている場合、この
コマンドは**全体を置き換える**。`nssm get ollama AppEnvironmentExtra` で既存の値を
見て、まとめて指定し直すこと。

### 4. Ollama を確かめる

**新しく開いた** PowerShell で実行する（環境変数は開き直したシェルにだけ入る）。

```powershell
$env:OLLAMA_HOST    # http://127.0.0.1:11500 と出ること

Get-NetTCPConnection -LocalPort 11434,11500 -State Listen -ErrorAction SilentlyContinue |
  Select-Object LocalAddress, LocalPort
```

次の状態になっていれば正しい。

- `11500` が `127.0.0.1` で待ち受けている（`0.0.0.0` や `::` なら手順3をやり直す）
- `11434` が出てこない

モデルがそのまま見えることを確かめる。保存先（`OLLAMA_MODELS`）は変えていないので、
取り直しは要らない。

```powershell
Invoke-RestMethod http://127.0.0.1:11500/api/tags | Select-Object -ExpandProperty models |
  Select-Object name
ollama list     # ollama コマンドも OLLAMA_HOST を読むので 11500 に繋がる
```

`bge-m3` が一覧にあること。無い場合は `ollama pull bge-m3` を実行する。

### 5. `.env` を揃える

`C:\App\local-llm-rag\.env` に `OLLAMA_HOST` の行があれば、同じ値に書き換える。

```dotenv
OLLAMA_HOST=http://127.0.0.1:11500
```

行が無ければ足さなくてよい（環境変数が効く）。手順3で環境変数を入れているので、
`.env` の値は実際には使われない。揃えておくのは、後で環境変数を消したときに古い
`11434` へ戻ってしまわないようにするためである。ngrok 等のリモート URL が書いて
あった場合も、**検索サーバ機では**ローカルの Ollama を指すよう書き換える。

### 6. RAG を繋ぎ直す

**取り込み・検索の疎通**：リポジトリの直下で実行する。

```powershell
cd C:\App\local-llm-rag
.\myvenv313\Scripts\python.exe -c "from ingest import embedder; print(embedder.OLLAMA_HOST); embedder.check_ollama(); print('ok')"
```

`http://127.0.0.1:11500` と `ok` が出れば、RAG から Ollama に届いていて、`bge-m3` も
ある。接続できない場合は `Ollamaに接続できません（…）` と、実際に繋ぎに行った先が
表示されるので、そこが `11500` かを見る。

**NSSM で常駐させている RAG のサービス**：サービスはユーザー環境変数を読まない。
それぞれに渡し直す。

```powershell
nssm set local-docs-mcp AppEnvironmentExtra "OLLAMA_HOST=http://127.0.0.1:11500"
nssm set local-llm-rag  AppEnvironmentExtra "OLLAMA_HOST=http://127.0.0.1:11500"
```

手順3と同じく、既存の値は置き換えられる。先に `nssm get <サービス名> AppEnvironmentExtra`
で確認すること。

ここではまだ MCP サーバを起動しない。現在の MCP サーバの待ち受けが `11434` 以外
（例：`8080`）であれば、この時点で起動して動作を確かめてよい。

```powershell
nssm start local-docs-mcp
nssm start local-llm-rag
```

検索まで通るかは、Streamlit 画面で質問を1つ投げるか、
[mcp-server-network.md](mcp-server-network.md) の「4. 起動を確認する」で確かめる。

### 7. 11434 の扱いを記録する

この時点で `11434` には何も待ち受けていない。既存のファイアウォール規則は消さずに
残す（次の手順で MCP が使う）。ただし規則の名前が「Ollama」のままだと誤解を招くので、
表示名を変えておく。

```powershell
# 管理者の PowerShell で。-DisplayName は手順1で控えた名前に置き換える
Set-NetFirewallRule -DisplayName "<手順1の規則名>" -NewDisplayName "local-docs MCP (TCP 11434)"

# 送信元が絞られているか確かめる。Any なら MCP を開ける前に必ず絞る
Get-NetFirewallRule -DisplayName "local-docs MCP (TCP 11434)" | Get-NetFirewallAddressFilter |
  Select-Object RemoteAddress
```

`RemoteAddress` が `Any` の場合、MCP を起動した瞬間にポートへ届く全員へ社内資料が
出る（[mcp-server-network.md](mcp-server-network.md)「何が守られ、何が守られないか」）。
クライアントのサブネットだけに絞る。

```powershell
Set-NetFirewallRule -DisplayName "local-docs MCP (TCP 11434)" -RemoteAddress 192.168.1.0/24
```

## 完了の確認

- [ ] `11500` が `127.0.0.1` で待ち受けている
- [ ] `11434` に何も待ち受けていない
- [ ] `ollama list` と `Invoke-RestMethod http://127.0.0.1:11500/api/tags` に `bge-m3` が出る
- [ ] `embedder.check_ollama()` が `ok` を返す
- [ ] NSSM で常駐させている RAG のサービスすべてに `OLLAMA_HOST=http://127.0.0.1:11500` が入っている
- [ ] `.env` に `OLLAMA_HOST` があれば同じ値になっている
- [ ] 11434 のファイアウォール規則の表示名が MCP 用になり、送信元が絞られている
- [ ] クライアント PC から `http://<検索サーバIP>:11500` に**届かない**ことを確かめた

最後の項目はクライアント PC で確かめる。

```powershell
Test-NetConnection <検索サーバIP> -Port 11500   # TcpTestSucceeded : False が正しい
```

## うまくいかないとき

| 症状 | 原因と対処 |
| --- | --- |
| 手順4で `11434` のまま | Ollama を Quit せずに環境変数を変えた。トレイから Quit して起動し直す。サービスの場合は `nssm restart ollama` |
| 手順4で `0.0.0.0:11500` | システム側に古い `OLLAMA_HOST` が残っている、または **Expose Ollama to the network** がオン。手順3 |
| `ollama list` が `could not connect` | その PowerShell が手順3より前に開いたもの。開き直す |
| `check_ollama()` が `127.0.0.1:11434` に繋ぎに行く | 実行したシェルに `OLLAMA_HOST` が入っていない。開き直す |
| `check_ollama()` が ngrok 等のリモートへ繋ぎに行く | 環境変数が入っておらず、`.env` のリモート URL が使われた。手順3・5 |
| `No connection adapters were found` | 値に `http://` が無い。手順3 |
| 画面からは検索できるが MCP では「Ollamaに接続できません」 | MCP サーバは `.env` を読まない。NSSM の `AppEnvironmentExtra` を見直す（手順6） |
| 再起動すると戻る | Ollama をサービスにしているのにユーザー環境変数だけを変えた（またはその逆）。手順3の該当する方を行う |

## 元に戻す

```powershell
# トレイアプリで動かしている場合（Quit してから）
[Environment]::SetEnvironmentVariable("OLLAMA_HOST", $null, "User")

# NSSM の場合
nssm set ollama AppEnvironmentExtra ""      # 元の値があればそれを入れ直す
nssm set local-docs-mcp AppEnvironmentExtra "OLLAMA_HOST=http://127.0.0.1:11434"
nssm set local-llm-rag  AppEnvironmentExtra "OLLAMA_HOST=http://127.0.0.1:11434"
```

`.env` の `OLLAMA_HOST` も手順1の前の値に戻し、Ollama と各サービスを起動し直す。
手順1で `Machine` 側に値があった場合は、それも戻す（`11434` を外に開けていた状態に
戻るので、戻す必要があるかを先に判断すること）。

## 次の文書

- MCP サーバを `11434` で起動し、クライアントの Claude Code（GB10 の gpt-oss / Qwen を
  プルダウンで切り替える構成）から検索する手順 —
  [mcp-server-11434-claude-code.md](mcp-server-11434-claude-code.md)
