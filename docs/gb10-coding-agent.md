# GB10のOllamaでコーディングエージェントを動かす（gpt-oss:120b）

ColabのL4に置いていた `gpt-oss:20b` を、社内LANのGB10（DGX Spark）に置いた
`gpt-oss:120b` へ移す手順。**vLLMは使わない。** Ollamaのまま、接続先とモデルと
コンテキスト長を差し替える。

VS CodeとCodex拡張はこれまでどおりWindows側で動く。変わるのは推論の宛先だけである。

```text
Windows（VS Code + Codex拡張 + myvenv313の起動補助）
        │ HTTP（社内LAN）
        ▼
GB10（DGX OS） → Ollama → gpt-oss:120b
```

> **未検証である。** 手元にGB10が無いため、この手順を通しで実行した記録は無い。
> 各段階に「何が出れば成功か」を書いたので、そこで確かめながら進めること。
> 特に**131072 と 120b の組み合わせがメモリに収まるかは `--probe` の結果でしか
> 分からない**。

## 目次

- [0. 何が変わるか](#0-何が変わるか)
- [1. GB10側: モデルを置く](#1-gb10側-モデルを置く)
- [2. GB10側: LANへ公開する](#2-gb10側-lanへ公開する)
- [3. Windows側: .env を書き換える](#3-windows側-env-を書き換える)
- [4. 接続とモデルを確かめる](#4-接続とモデルを確かめる)
- [5. コンテキスト長を焼いて実配置を測る](#5-コンテキスト長を焼いて実配置を測る)
- [6. Codex設定を作り直して起動する](#6-codex設定を作り直して起動する)
- [6.5 config.toml の中身](#65-configtoml-の中身)
- [7. 効果を測る](#7-効果を測る)
- [元に戻す](#元に戻す)
- [つまずきやすいところ](#つまずきやすいところ)

## 0. 何が変わるか

|項目|Colab L4|GB10|
|---|---|---|
|接続先|ngrokのHTTPS URL|`http://<GB10のIP>:11434`|
|認証|`X-API-Key`（必須）|**無し**（LAN内で閉じるため）|
|モデル|`gpt-oss:20b`|`gpt-oss:120b`|
|コンテキスト長|65536（24GBの上限）|131072 を狙う（`--probe` 次第で65536）|
|稼働|アイドルで切れる|常時|

起動補助（`scripts/coding_agent.py`）はこの3つを引数で受け取る。

- `--model` — モデル名
- `--context-size` — 32768 / 65536 / 131072
- 接続先 — プロジェクト直下の `.env` の `OLLAMA_HOST`

**モデルとコンテキスト長は、一度指定すると保存済みのCodex設定から引き継がれる。**
毎回書く必要はなく、片方だけ渡した回でももう片方は保たれる。

## 1. GB10側: モデルを置く

GB10にSSHで入る。

```bash
ollama pull gpt-oss:120b
ollama list          # gpt-oss:120b が並ぶこと
```

**GPUに載っているかをここで確かめる。** ユニファイドメモリなので専有VRAMという
概念は無いが、「GPUで動いているか」は別の話で、これは確認できる。

```bash
ollama run gpt-oss:120b "hello" --verbose
ollama ps            # PROCESSOR 列
```

`100% GPU` であること。`100% CPU` と出たら、そのOllamaはGB10のBlackwellを
掴めていない。先にそれを解決する（Ollamaの版を上げる）。**ここがCPUのままだと、
以降の手順は全部意味を失う。**

## 2. GB10側: LANへ公開する

Ollamaは既定で `127.0.0.1` にしかbindしない。Windows側から叩くには広げる。

```bash
sudo systemctl edit ollama
```

```ini
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
```

```bash
sudo systemctl restart ollama
ip -4 addr show | grep inet        # GB10のIPを控える
```

Windows側から届くか確かめる。

```powershell
curl.exe http://<GB10のIP>:11434/api/version
```

> **Ollamaに認証は無い。** `0.0.0.0` にbindした時点で、そのLANから届く全員が
> モデルを使える。社内の信頼できるセグメントに限ること。届く範囲が広いなら、
> ファイアウォールで送信元を絞る。

## 3. Windows側: .env を書き換える

対象プロジェクト直下の `.env` を書き換える。

```dotenv
OLLAMA_HOST=http://<GB10のIP>:11434
```

`OLLAMA_API_KEY` は**行ごと消す**。LAN上のOllamaには認証が無く、
起動補助も社内の宛先ではキーを要求しない。**ダミーの値を書かないこと。**
設定を嘘にするだけである。

平文のHTTPが許されるのは、ループバック・プライベートIP・`.local` 宛てのときだけ
である（`coding_agent/connection.py` の `is_local_host`）。外部の宛先に `http://`
を書くと弾かれる。Colabのngrok URLへ戻すときは `https://` と APIキーが要る。

**`localhost` は使わないこと。** IPアドレスで書く。

## 4. 接続とモデルを確かめる

ここから先はWindows側のPowerShellで、リポジトリ直下から実行する。

```powershell
.\myvenv313\Scripts\python.exe -m scripts.coding_agent --check --model gpt-oss:120b
```

推論は行わない。返るJSONで2つを見る。

- `"tools": true` — **これが false なら先へ進んでも無駄である。** Codexは道具
  呼び出しが全てで、対応していないモデルでは何もできない
- `"model": "gpt-oss:120b"` — 指定が届いていること

モデル名を間違えていれば、ここで `/api/show` が失敗して止まる。

## 5. コンテキスト長を焼いて実配置を測る

`--configure-context` は、いまのモデル設定を `gpt-oss:120b-before-coding-agent`
として保存してから、`num_ctx` を焼いた同名のモデルを作る。

```powershell
.\myvenv313\Scripts\python.exe -m scripts.coding_agent --configure-context --model gpt-oss:120b --context-size 131072
.\myvenv313\Scripts\python.exe -m scripts.coding_agent --probe
```

**`--probe` がこの手順の関門である。** `fully_on_gpu` が真であること。

偽なら、モデルの一部がCPUへ落ちている。エラーメッセージが次に試す値（65536）を
名指しするので、1段下げてやり直す。

```powershell
.\myvenv313\Scripts\python.exe -m scripts.coding_agent --configure-context --context-size 65536
.\myvenv313\Scripts\python.exe -m scripts.coding_agent --probe --context-size 65536
```

gpt-oss:120b はMXFP4で重みだけで約60GiBある。131072のKVキャッシュがその上に乗る
ので、**128GBに収まるかは実際に測るまで分からない。** 65536で通るなら、それでも
L4時代と同じ長さは確保できている。

`--probe` はあわせてResponses APIのツール往復も検証する。ここまで通れば、
モデルとコンテキスト長の両方が実際に使える状態になっている。

## 6. Codex設定を作り直して起動する

```powershell
.\myvenv313\Scripts\python.exe -m scripts.coding_agent --setup
```

`--model` も `--context-size` も省略してよい。5節で使った値が保存済みの設定から
引き継がれる。生成されるもののうち、モデルに連動するのは次の3つである。

|場所|内容|
|---|---|
|`codex/config.toml`|`model` と `model_context_window`、`model_auto_compact_token_limit`（文脈の3/4）|
|`codex/models.json`|`slug` / `context_window` / `comp_hash`。**config.toml の `model` と slug が食い違うとCodexはモデルを見つけられない**ので、両方を同じ設定から作っている|
|VS Codeの `window.title`|どのモデルに繋いだ窓かを見分けるため|

確認して、起動する。

```powershell
type $env:LOCALAPPDATA\local-llm\coding-agent\codex\config.toml | Select-String "^model"
.\myvenv313\Scripts\python.exe -m scripts.coding_agent
```

## 6.5 config.toml の中身

`--setup` が作る `config.toml` は、Codex拡張が読むクライアント設定である。
**手で書く必要は無いが、何が書かれているかは把握しておく。** 繋がらないときに
最初に見る場所になる。

### 置き場所

|起動の仕方|`config.toml`|
|---|---|
|`scripts.coding_agent`（この手順）|`%LOCALAPPDATA%\local-llm\coding-agent\codex\config.toml`|
|同上・別プロジェクト|`%LOCALAPPDATA%\local-llm\coding-agent\projects\<指紋>\codex\config.toml`|
|素のCodex|`%USERPROFILE%\.codex\config.toml`|

起動補助は `CODEX_HOME` を専用フォルダに向けてVS Codeを起動する。**素のCodex設定
（`~/.codex`）には触れない。** 普段使いのCodexと混ざらないようにするためである。

### GB10へ繋いだときの中身

```toml
# BEGIN LOCAL_LLM_MANAGED_CONFIG
# このブロックは起動補助が更新する。追加設定はEND行の後へ記載する。
model = "gpt-oss:120b"
model_provider = "colab-oss"
model_catalog_json = "C:\\Users\\you\\AppData\\Local\\local-llm\\coding-agent\\codex\\models.json"
model_context_window = 131072
model_auto_compact_token_limit = 98304
model_reasoning_effort = "medium"
sandbox_mode = "workspace-write"
approval_policy = "on-request"
web_search = "disabled"
developer_instructions = """
（省略）
"""

[model_providers.colab-oss]
name = "Local gpt-oss:120b"
base_url = "http://192.168.1.50:11434/v1"
wire_api = "responses"
requires_openai_auth = false
request_max_retries = 1
stream_max_retries = 0
stream_idle_timeout_ms = 120000

[shell_environment_policy]
exclude = ["OLLAMA_API_KEY"]

[windows]
sandbox = "unelevated"

[analytics]
enabled = false

[features]
plugins = false
# END LOCAL_LLM_MANAGED_CONFIG
```

### 確かめる値

繋がらないときは、上から順にこの4つを見る。

|キー|GB10での値|意味|
|---|---|---|
|`model`|`"gpt-oss:120b"`|**`models.json` の `slug` と一致していること。** 食い違うとCodexはモデルを見つけられない|
|`base_url`|`"http://<GB10のIP>:11434/v1"`|**末尾の `/v1` を落とさない。** OllamaのOpenAI互換エンドポイントである|
|`model_context_window`|`131072`|`--probe` を通した値と揃っていること|
|`model_auto_compact_token_limit`|`98304`|文脈の3/4。ここを超えると履歴の圧縮が走る|

```powershell
type $env:LOCALAPPDATA\local-llm\coding-agent\codex\config.toml | Select-String "^model|base_url"
```

### Colab接続との差

**LAN宛てでは認証ヘッダーの2つが出力されない。**

```toml
# Colab（ngrok）へ繋いだときだけ出る
[model_providers.colab-oss.env_http_headers]
X-API-Key = "OLLAMA_API_KEY"

[model_providers.colab-oss.http_headers]
ngrok-skip-browser-warning = "true"
```

どちらもColab経由のための仕掛けである。`X-API-Key` は ngrok の前に置いた認証
プロキシが見るもので、`ngrok-skip-browser-warning` は無料プランの警告ページを
避けるためのもの。**社内LANのOllamaはどちらも見ないし、キーも無い。** 意味の
無いヘッダーを設定に残さない。

`shell_environment_policy.exclude` は LAN でも残す。エージェントが起動する
シェルへ `OLLAMA_API_KEY` を渡さないための設定で、**Colabへ戻したときに
外し忘れるほうが危ない**からである。

### 自分の設定を足す

**`# END LOCAL_LLM_MANAGED_CONFIG` より後に書く。** BEGIN〜END の間は
`--setup` のたびに丸ごと差し替わるので、そこへ書いた内容は次回消える。
END行より後ろはそのまま引き継がれる。

```toml
# END LOCAL_LLM_MANAGED_CONFIG

# ここから下は --setup で保持される
[mcp_servers.playwright]
command = "npx"
args = ["-y", "@playwright/mcp@latest", "--caps=testing", "--isolated"]
```

END行より後ろが管理ブロックと衝突する（同じキーを二重に定義するなど）場合、
`--setup` は**書き込まずに中止する**。TOMLとして壊れた設定を残さないためである。
BEGIN行が無い、またはEND行が複数あるファイルも、管理形式でないとみなして
上書きしない。**手で全面的に書き換えたファイルがあると `--setup` は止まる。**

### 起動補助を使わずに手で書く

このリポジトリも仮想環境も無いPCから繋ぐ場合は、上のTOMLをそのまま
`%USERPROFILE%\.codex\config.toml` に置けば足りる。ただし2つ落ちる。

- `model_catalog_json` が指す `models.json`。**このファイルが無いと、Codexは
  そのモデルを一覧に出さない。** 生成済みのものを1つコピーして、`slug` と
  `context_window` を合わせる
- Superpowersスキルの配置と、`developer_instructions` の中身

**測り比べや日常の利用では `--setup` を使うこと。** この2つを手で揃え続けるのは
割に合わない。

## 7. 効果を測る

**入れ替えたら、上がったかどうかを測る。** モデルを大きくすれば精度が上がるとは
限らない。DGX Spark上でエージェント用途を比べた外部のベンチマークでは、
gpt-oss:120b がツール呼び出しで不正なJSONを出して失敗したという報告がある。
このリポジトリ自身、`docgen/project.py` に「gpt-oss:20b は道具を呼ばない」と
書いていたのが**実測で誤りと分かった**記録を残している。同じ性質の話である。

測り方をそろえる。

1. 実際にやらせたい課題を**10件固定する**（このリポジトリでの実作業から採る）
2. `--model gpt-oss:20b` と `--model gpt-oss:120b` で、各3回
3. 数えるのは2つだけ。**道具を呼んだか**、**テストが通ったか**
4. tok/s では判断しない。速さではなく成果を見る

モデルを切り替えるのは `--model` を渡した1回だけで、`.env` も設定も作り直さなくて
よい。同じ接続先のまま比べられる。

## 元に戻す

`--configure-context` が焼いたモデル設定を戻す。

```powershell
.\myvenv313\Scripts\python.exe -m scripts.coding_agent --restore-context --model gpt-oss:120b
```

ColabのL4へ戻すなら、`.env` を `https://` のngrok URLと `OLLAMA_API_KEY` に書き戻し、
`--model gpt-oss:20b --context-size 65536` で `--setup` をやり直す。

## つまずきやすいところ

|症状|原因|対処|
|---|---|---|
|`.env の OLLAMA_HOST に…` で止まる|`http://` を外部の宛先に書いた、または `localhost` を書いた|IPアドレスで書く。外部の宛先には `https://`|
|`OLLAMA_API_KEY` を求められる|`.env` の `OLLAMA_HOST` が `https://` のまま|LAN宛てに書き換える。キー必須は外向けの経路だけ|
|`--check` が `"tools": false`|そのモデルが道具呼び出しに対応していない|**別のモデルにする。** ここは設定で埋められない|
|`--probe` が `fully_on_gpu: false`|コンテキストが大きすぎる|メッセージが名指しする値へ1段下げる|
|`ollama ps` が `100% CPU`|OllamaがGB10のGPUを掴めていない|Ollamaの版を上げる。**この状態では他の設定は全部無意味**|
|Codexがモデルを見つけない|`config.toml` の `model` と `models.json` の `slug` の食い違い|`--setup` をやり直す（両方を同じ設定から作る）|
|文脈を伸ばしたのに読む量が増えない|`--configure-context` を実行していない|数字を変えるだけでは効かない。焼いて `--probe` で確認する|

## 関連

- [VS CodeでColabのgpt-oss:20bを使う](vscode-colab-agent.md) — 元の手順。コンテキスト長の選び方はこちらにある
- [docs/mcp-tool-not-called.md](mcp-tool-not-called.md) — 道具が呼ばれないときの切り分け
- [Playwright MCPの設定](playwright-mcp.md) — END行より後ろへ足す設定の実例
- [VS CodeのClaude CodeをGB10へ向ける](claude-code-gb10.md) — Codexではなく Claude Code を使う場合。変換プロキシが1つ要る
