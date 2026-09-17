# GB10のOllamaでコーディングエージェントを動かす（gpt-oss:120b）

ColabのL4に置いていた `gpt-oss:20b` を、社内LANのGB10（DGX Spark）に置いた
`gpt-oss:120b` へ移す手順。**vLLMは使わない。**

**クライアントには Ollama も Python も入れない。** Windows側に置くのは VS Code と
Codex拡張、それに設定ファイル2つ（`config.toml` / `models.json`）だけである。
モデルの取得・コンテキスト長・実配置の確認はすべてGB10側でSSH越しに行う。
起動補助（`scripts/coding_agent.py`）もこのリポジトリのクローンも使わない。

```text
Windows（VS Code + Codex拡張 + config.toml / models.json）
        │ HTTP（社内LAN）
        ▼
GB10（DGX OS） → Ollama → gpt-oss:120b-131k
```

> **未検証である。** 手元にGB10が無いため、この手順を通しで実行した記録は無い。
> 各段階に「何が出れば成功か」を書いたので、そこで確かめながら進めること。
> 特に**131072 と 120b の組み合わせがメモリに収まるかは、3節の `/api/ps` の
> 値でしか分からない**。

## 目次

- [0. 役割分担](#0-役割分担)
- [1. GB10側: モデルを置く](#1-gb10側-モデルを置く)
- [2. GB10側: コンテキスト長を伸ばす](#2-gb10側-コンテキスト長を伸ばす)
- [3. GB10側: 実配置と道具呼び出しを確かめる](#3-gb10側-実配置と道具呼び出しを確かめる)
- [4. GB10側: LANへ公開する](#4-gb10側-lanへ公開する)
- [Windows側に要るもの](#windows側に要るもの)
- [5. Windows側: config.toml を置く](#5-windows側-configtoml-を置く)
- [6. Windows側: models.json を置く](#6-windows側-modelsjson-を置く)
- [7. 起動して確かめる](#7-起動して確かめる)
- [8. 効果を測る](#8-効果を測る)
- [元に戻す](#元に戻す)
  - [GB10側の後始末](#gb10側の後始末)
  - [ColabのL4へ戻す](#colabのl4へ戻す)
- [Pythonを入れてよいなら](#pythonを入れてよいなら)
- [つまずきやすいところ](#つまずきやすいところ)

## 0. 役割分担

**確認と操作はGB10側、設定はWindows側**、と割り切る。クライアントに実行環境を
足さない代わりに、モデルに関わる作業はすべてサーバーの上で行う。

|やること|どこで|使うもの|
|---|---|---|
|モデルを置く|GB10|`ollama pull`|
|コンテキスト長を伸ばす|GB10|Modelfile と `ollama create`|
|GPUに全部載ったかの確認|GB10|`/api/ps` の `size` と `size_vram`|
|道具呼び出しの確認|GB10|`curl`|
|LANへ公開する|GB10|systemd|
|Codexの設定|Windows|テキストエディタで2ファイル|
|起動|Windows|VS Code|

このリポジトリには起動補助（`scripts/coding_agent.py`）があり、下の作業を
まとめて行える。**それはPythonが要る道**なので、この手順では使わない。
対応関係だけ載せておく。

|起動補助|この手順での代わり|
|---|---|
|`--check`|`ollama show`（`tools` が capabilities に並ぶか）|
|`--configure-context`|Modelfile と `ollama create`（**別名で作る**）|
|`--probe`|`/api/ps` の `size` / `size_vram` / `context_length` と、`/v1/responses` へのcurl|
|`--setup`|`config.toml` と `models.json` を手で置く|
|`--restore-context`|`ollama rm`（別名で作るので、元のモデルは無傷）|

**1つだけ自動では埋まらないものがある。** 起動補助はSuperpowersスキルを
プロジェクトへ配置していた。手で置く構成での扱いは[5節](#superpowersスキルをどうするか)にある。

## 1. GB10側: モデルを置く

GB10にSSHで入る。WindowsにはOpenSSHクライアントが標準で入っているので、
追加で入れるものは無い。

```powershell
ssh <ユーザー名>@<GB10のIP>
```

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

**道具呼び出しに対応しているかも、ここで見る。**

```bash
ollama show gpt-oss:120b     # Capabilities に tools があること
```

`tools` が無いモデルではCodexは何もできない。**ここは設定で埋められない。**
別のモデルを選ぶしかない。

## 2. GB10側: コンテキスト長を伸ばす

Ollamaの既定の文脈長は、Codexの用途には短い。伸ばすにはモデル側に焼く。
**Codex（クライアント）側から `num_ctx` は指定できない。** ここで決めた値が
そのまま上限になる。

```bash
cat <<'EOF' > /tmp/Modelfile
FROM gpt-oss:120b
PARAMETER num_ctx 131072
EOF
ollama create gpt-oss:120b-131k -f /tmp/Modelfile
ollama list          # gpt-oss:120b-131k が増えていること
```

**元の `gpt-oss:120b` は書き換えない。** `gpt-oss:120b-131k` という別の名前で
作るので、やめるときは消すだけで済む。GB10を他の人・他の用途と共有している
場合、この差は大きい。同じ名前で作り直すと、そのOllamaを使う全員の文脈長が
変わる。

> 起動補助の `--configure-context` は**同じ名前で作り直す**方式で、退避用の
> `gpt-oss:120b-before-coding-agent` を作ってから元を置き換える。だから
> `--restore-context` という後始末が要る。この手順では別名にしたので要らない。

gpt-oss:120b はMXFP4で重みだけで約60GiBある。131072のKVキャッシュがその上に
乗るので、**128GBに収まるかは実際に測るまで分からない。** 収まらなければ
`num_ctx` を 65536 に下げて作り直す。65536 でもL4時代と同じ長さは確保できている。

## 3. GB10側: 実配置と道具呼び出しを確かめる

**ここがこの手順の関門である。** Windows側を触る前に、GB10の上で2つ確かめる。

### 全部GPUに載ったか

Ollamaは大きすぎる文脈を指定しても例外を出さず、**モデルの一部を黙ってCPUへ
落とす**。速度が出ないだけで動いてしまうので、気づくのが遅れる。数字で見る。

```bash
ollama run gpt-oss:120b-131k "hi" > /dev/null
curl -s http://127.0.0.1:11434/api/ps | python3 -c "
import json, sys
model = json.load(sys.stdin)['models'][0]
print('context_length:', model['context_length'])
print('size        :', model['size'])
print('size_vram   :', model['size_vram'])
print('fully_on_gpu:', model['size'] == model['size_vram'])
"
```

見るのは2つ。

- **`fully_on_gpu` が `True`** — `False` なら一部がCPUにある。2節へ戻って
  `num_ctx` を 65536 で作り直す
- **`context_length` が 131072** — 焼いた値が実際に効いていること。
  ここが既定値のままなら、`ollama create` の対象を間違えている

（この2つは起動補助の `--probe` が見ているものと同じである。`fully_on_gpu` は
`size == size_vram` で判定している。）

### 道具を呼んで、結果を返せるか

Codexは道具呼び出しが全てである。**モデルが道具を呼べても、結果を受け取って
続きを話せるとは限らない。** 往復させて確かめる。

```bash
curl -s http://127.0.0.1:11434/v1/responses \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "gpt-oss:120b-131k",
    "input": "Call get_probe_value exactly once with no arguments. Do not answer before calling the tool.",
    "tools": [{
      "type": "function",
      "name": "get_probe_value",
      "description": "Returns the fixed connection probe value.",
      "parameters": {"type": "object", "properties": {}, "required": []}
    }],
    "stream": false
  }'
```

`"type": "function_call"` と `"name": "get_probe_value"` を含む出力が返ること。
返らない、あるいは引数が壊れたJSONなら、**そのモデルはこの用途に向いていない。**
設定では直せない。

> **`404` が返る場合、そのOllamaは Responses API を持っていない。** 版を上げるか、
> `/v1/chat/completions` に `"tools"` を付けて同じことを確かめ、[5節](#5-windows側-configtoml-を置く)の
> `wire_api` を `"chat"` にする。Codexが叩く先をそちらへ変えるという意味である。

## 4. GB10側: LANへ公開する

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

Windows側から届くか確かめる。`curl.exe` はWindows 10 1803以降に標準で入って
いるので、これも追加で入れるものは無い。

```powershell
curl.exe http://<GB10のIP>:11434/api/version
```

> **Ollamaに認証は無い。** `0.0.0.0` にbindした時点で、そのLANから届く全員が
> モデルを使える。社内の信頼できるセグメントに限ること。届く範囲が広いなら、
> ファイアウォールで送信元を絞る。**キーを設定する場所が無い**ので、絞る以外に
> 手は無い。

## Windows側に要るもの

|要るもの|なぜ|
|---|---|
|VS Code と **Codex拡張**（`openai.chatgpt`）|エージェント本体|
|テキストエディタ|`config.toml` と `models.json` を書く。VS Codeで足りる|
|`models.json` の雛形1つ|このリポジトリの `infra/codex-colab/models.json` を、ブラウザーから**1ファイルだけ**落とす|
|SSHクライアント|GB10を操作する。Windows標準のOpenSSHでよい|
|`curl.exe`|疎通確認だけに使う。Windows標準|

**要らないもの**を並べておく。

- **Python と仮想環境**（`myvenv313`）、`requests` / `python-dotenv`
- **このリポジトリのクローン**（`models.json` を1つ落とすだけ）
- **Ollama**（クライアント側では一切使わない）
- **`.env`** — 接続先は `config.toml` の `base_url` に直接書く

## 5. Windows側: config.toml を置く

### 置き場所

|使い方|`config.toml`|
|---|---|
|Codexを普段から使っていない|`%USERPROFILE%\.codex\config.toml`|
|普段使いのCodexと分けたい|`CODEX_HOME` を別フォルダに向けてVS Codeを起動する（下記）|

普段使いのCodex（ChatGPTアカウントで使うもの）と混ぜたくない場合は、設定一式を
別フォルダに置き、**そのフォルダを指した状態でVS Codeを起動する**。

```powershell
$env:CODEX_HOME = "$env:LOCALAPPDATA\local-llm\codex-gb10"
code <プロジェクトのフォルダ>
```

Codex拡張は起動元プロセスの環境変数を引き継ぐので、この窓だけがGB10向けの設定に
なる。起動補助が行っていたのも同じことである。**すでに開いているVS Codeには
効かない。** 上のコマンドで開き直す。

### 中身

`%USERPROFILE%\.codex\config.toml`（または `CODEX_HOME` 配下）に置く。

```toml
model = "gpt-oss:120b-131k"
model_provider = "gb10-oss"
model_catalog_json = "C:\\Users\\you\\.codex\\models.json"
model_context_window = 131072
model_auto_compact_token_limit = 98304
model_reasoning_effort = "medium"
sandbox_mode = "workspace-write"
approval_policy = "on-request"
web_search = "disabled"
developer_instructions = """
Before other work, inspect the available skills and use every skill explicitly named by the user.
For a named Superpowers skill, first read `.agents/skills/<skill-name>/SKILL.md`
with a shell command, then follow it. Never skip this read as unnecessary.
If an apply_patch tool is unavailable, edit through a short, direct PowerShell command instead
of repeatedly requesting that unavailable tool.
Only report a command or test as successful when its actual command output proves success.
"""

[model_providers.gb10-oss]
name = "GB10 gpt-oss:120b"
base_url = "http://192.168.1.50:11434/v1"
wire_api = "responses"
requires_openai_auth = false
request_max_retries = 1
stream_max_retries = 0
stream_idle_timeout_ms = 120000

[windows]
sandbox = "unelevated"

[analytics]
enabled = false
```

### 確かめる値

繋がらないときは、上から順にこの5つを見る。

|キー|値|意味|
|---|---|---|
|`model`|`"gpt-oss:120b-131k"`|**`models.json` の `slug` と一致していること。** 食い違うとCodexはモデルを見つけられない。2節で作った名前である|
|`base_url`|`"http://<GB10のIP>:11434/v1"`|**末尾の `/v1` を落とさない。** OllamaのOpenAI互換エンドポイントである。`localhost` ではなくIPで書く|
|`wire_api`|`"responses"`|Codexが叩く先。3節のcurlが404だったなら `"chat"`|
|`model_context_window`|`131072`|3節の `context_length` と揃っていること|
|`model_auto_compact_token_limit`|`98304`|文脈の3/4。ここを超えると履歴の圧縮が走る|
|`model_provider`|`"gb10-oss"`|**`[model_providers.gb10-oss]` の名前と一致していること。** 名前自体は何でもよいが、2か所で揃える|

`model_catalog_json` は**絶対パス**で、バックスラッシュを2つ重ねる。TOMLの
基本文字列ではエスケープが要る。`'C:\Users\you\.codex\models.json'` のように
シングルクォートで書いてもよい（リテラル文字列）。

### Colabへ繋ぐときとの差

**LAN宛てでは認証ヘッダーの2つを書かない。**

```toml
# Colab（ngrok）へ繋ぐときだけ足す
[model_providers.gb10-oss.env_http_headers]
X-API-Key = "OLLAMA_API_KEY"

[model_providers.gb10-oss.http_headers]
ngrok-skip-browser-warning = "true"
```

どちらもColab経由のための仕掛けである。`X-API-Key` は ngrok の前に置いた認証
プロキシが見るもので、`ngrok-skip-browser-warning` は無料プランの警告ページを
避けるためのもの。**社内LANのOllamaはどちらも見ないし、キーも無い。** 意味の
無いヘッダーを設定に残さない。**ダミーの値も書かないこと。** 設定を嘘にする
だけである。

`env_http_headers` は「その名前の環境変数の値を送る」という指定なので、Colabへ
戻す場合は `OLLAMA_API_KEY` をVS Codeの起動元で設定しておく必要がある。

### Superpowersスキルをどうするか

起動補助は、Codexのプラグイン置き場（`~/.codex/plugins/cache`）にある
Superpowers 6.3.0 を見つけ、対象プロジェクトの `.agents/skills/` へスキルごとに
リンクを張り、Codex自身のプラグイン機能は `[features] plugins = false` で
切っていた。**この手順ではその逆をとる。**

上の `config.toml` に `[features]` ブロックを書いていないのは、**Codexの
プラグイン機能をそのまま使う**ためである。Superpowersは拡張のプラグイン画面
から入れる。Pythonは要らない。

`.agents/skills/` に置く形にしたい場合（`AGENTS.md` がこの配置を前提にしている）
は、プラグイン置き場の `superpowers/<版>/skills/<スキル名>` を、プロジェクトの
`.agents/skills/` へ**フォルダごとコピーする**。リンクである必要は無い。
コピーなのでエクスプローラーでできる。

## 6. Windows側: models.json を置く

**このファイルが無いと、Codexはそのモデルを一覧に出さない。** `config.toml` の
`model_catalog_json` が指す先である。

このリポジトリの
[`infra/codex-colab/models.json`](../infra/codex-colab/models.json) を、
ブラウザーの「Raw」から1ファイルだけ落として、`config.toml` の
`model_catalog_json` が指す場所に置く。**書き換えるのは4か所だけ**である。

|キー|雛形の値|GB10での値|
|---|---|---|
|`slug`|`"gpt-oss:20b"`|`"gpt-oss:120b-131k"`（**`config.toml` の `model` と一致させる**）|
|`display_name`|`"gpt-oss:20b (Colab L4)"`|`"gpt-oss:120b-131k"`|
|`context_window`|`65536`|`131072`|
|`comp_hash`|`"local-gpt-oss-20b-v1"`|`"local-gpt-oss-120b-131k"`（**他と重複しない値にする**）|

`max_context_window` は `131072` のままでよい。`comp_hash` を変えるのは、
モデルを替えたときにキャッシュを取り違えないためである。

**`slug` と `config.toml` の `model` の食い違いが、この構成で最も多い事故である。**
別々のファイルに同じ名前を書くことになるので、2節で作ったモデル名を決めたら、
両方に貼り付ける。

## 7. 起動して確かめる

```powershell
$env:CODEX_HOME = "$env:LOCALAPPDATA\local-llm\codex-gb10"   # 分けている場合だけ
code <プロジェクトのフォルダ>
```

VS CodeでCodexを開き、モデル一覧に `gpt-oss:120b-131k` が出ていることを確かめて
選ぶ。出てこないなら `models.json` の `slug` と `config.toml` の `model` を見比べる。

何か聞いてみる。

```
このリポジトリの README.md が何を説明しているか、ファイルを読んで答えて
```

見るのは2つ。

- **応答が返ること** — 返らなければ4節のcurlに戻る。GB10までは切り分け済みなので、
  差は `base_url` かモデル名である
- **ファイルを実際に読みに行くこと** — 読まずに一般論を答えるなら、道具呼び出しが
  効いていない。3節の2つ目のcurlの結果を思い出す

GB10側でも見ておく。

```bash
ollama ps        # gpt-oss:120b-131k が 100% GPU で載っていること
```

## 8. 効果を測る

**入れ替えたら、上がったかどうかを測る。** モデルを大きくすれば精度が上がるとは
限らない。DGX Spark上でエージェント用途を比べた外部のベンチマークでは、
gpt-oss:120b がツール呼び出しで不正なJSONを出して失敗したという報告がある。
このリポジトリ自身、`docgen/project.py` に「gpt-oss:20b は道具を呼ばない」と
書いていたのが**実測で誤りと分かった**記録を残している。同じ性質の話である。

測り方をそろえる。

1. 実際にやらせたい課題を**10件固定する**（このリポジトリでの実作業から採る）
2. `gpt-oss:20b` と `gpt-oss:120b-131k` で、各3回
3. 数えるのは2つだけ。**道具を呼んだか**、**テストが通ったか**
4. tok/s では判断しない。速さではなく成果を見る

モデルを切り替えるには、`config.toml` の `model` と `models.json` の `slug` を
両方書き換えてVS Codeを開き直す。**2か所であることを忘れない。** 比べる頻度が
高いなら、`CODEX_HOME` をモデルごとに分けて2つ用意し、起動時に選ぶほうが早い。

## 元に戻す

性質の違う2つがある。**「効果が出なかったとき」の話は後半だけ**で、前半は
使い続けるかどうかと関係なく必要になることがある。

### GB10側の後始末

2節で**別名のモデルを作った**ので、消すだけで終わる。

```bash
ollama rm gpt-oss:120b-131k
```

元の `gpt-oss:120b` には触れていないため、そのOllamaを使う他の処理・他の人への
影響は無い。**コンテキスト長を変えたいだけなら、後始末は要らない。**
`ollama create` で同じ名前を作り直せばよい（値だけが変わる）。

|場面|やること|
|---|---|
|エージェントを使うのをやめる|`ollama rm gpt-oss:120b-131k`|
|GB10を他の用途・他の人に渡す|同上。元のモデルは無傷なので、これで元通り|
|コンテキスト長を変えたい|`ollama create` を打ち直す。消さなくてよい|
|LANへの公開もやめる|4節のsystemd設定を戻し、`sudo systemctl restart ollama`|

> **起動補助を使った場合だけ話が違う。** `--configure-context` は同じ名前で
> 作り直すので、GB10の `gpt-oss:120b` そのものが置き換わる。その場合は
> `--restore-context` で退避した `gpt-oss:120b-before-coding-agent` から戻す
> 必要がある（[Pythonを入れてよいなら](#pythonを入れてよいなら)）。
> vLLM版にはどちらも無い。コンテキスト長がサーバー起動時の `--max-model-len` で
> 決まり、モデル自体を書き換えないためである（[vLLM版](vllm-gb10-coding-agent.md)）。

### ColabのL4へ戻す

**こちらが「効果が出なかった」「やめる」場合である。**

`config.toml` を3か所、`models.json` を3か所書き戻す。

|ファイル|キー|Colabの値|
|---|---|---|
|`config.toml`|`model`|`"gpt-oss:20b"`|
|`config.toml`|`base_url`|ngrokの **`https://`** URL + `/v1`|
|`config.toml`|`model_context_window`|`65536`（`model_auto_compact_token_limit` は `49152`）|
|`config.toml`|`env_http_headers` / `http_headers`|[5節の2ブロック](#colabへ繋ぐときとの差)を足す|
|`models.json`|`slug` / `display_name` / `context_window`|`gpt-oss:20b` / `65536`|

`OLLAMA_API_KEY` を、VS Codeを起動するシェルで設定しておくこと。`env_http_headers`
はその環境変数を読む。

**その状態では、エージェントが開くシェルにもキーが渡る。** 渡したくないなら
次を足す。起動補助が常に書いていたのはこのためである。

```toml
[shell_environment_policy]
exclude = ["OLLAMA_API_KEY"]
```

上のGB10側の後始末も忘れずに行う。使わないモデルが60GiB居座る。

## Pythonを入れてよいなら

クライアントにPython 3.13を入れられるなら、起動補助が上の作業をまとめて行う。
**この手順の代わりであって、併用するものではない。**

```powershell
py -3.13 -m venv myvenv313
.\myvenv313\Scripts\python.exe -m pip install requests python-dotenv
```

要るのは、このリポジトリ一式（`scripts/coding_agent.py`・`coding_agent/`・
`infra/codex-colab/` の雛形）、上の2パッケージ、対象プロジェクト直下の `.env`
（`OLLAMA_HOST=http://<GB10のIP>:11434`）、そしてCodexのプラグイン画面から入れた
Superpowers 6.3.0 である。`requirements.txt` の全部（pymupdf・streamlit・
onnxruntime など）はRAGアプリ用で、起動補助は触らない。

```powershell
.\myvenv313\Scripts\python.exe -m scripts.coding_agent --check --model gpt-oss:120b
.\myvenv313\Scripts\python.exe -m scripts.coding_agent --configure-context --context-size 131072
.\myvenv313\Scripts\python.exe -m scripts.coding_agent --probe
.\myvenv313\Scripts\python.exe -m scripts.coding_agent
```

手で置く場合との違いは3つある。

- **`--configure-context` は同じ名前でモデルを作り直す。** 退避（`-before-coding-agent`）
  を作るので戻せるが、共有サーバー上の状態が変わる。`--restore-context` が要る
- **`config.toml` と `models.json` を同じ設定から作る**ので、`model` と `slug` が
  食い違わない
- **Superpowersスキルをプロジェクトの `.agents/skills/` へ配置する**

詳しくは [VS CodeでColabのgpt-oss:20bを使う](vscode-colab-agent.md)。接続先が
ngrokからLANのアドレスに変わるだけで、使い方は同じである。

**台数が増えるなら、手で置くほうが現実的である。** 1台で動く設定を作り、
`config.toml` と `models.json` の2ファイルを配ればよい。

## つまずきやすいところ

|症状|原因|対処|
|---|---|---|
|Codexがモデルを見つけない|`config.toml` の `model` と `models.json` の `slug` の食い違い|2か所に同じ名前を書く。2節で作った名前である|
|プロバイダが見つからない|`model_provider` と `[model_providers.<名前>]` の食い違い|同じ名前にする。この文書では `gb10-oss`|
|モデル一覧に何も出ない|`model_catalog_json` のパスが違う、またはファイルが無い|絶対パスで、バックスラッシュを2つ重ねる。[6節](#6-windows側-modelsjson-を置く)|
|404 が返る|`base_url` の末尾 `/v1` が無い|ホストとポートの後ろに `/v1` を付ける|
|接続できない|`localhost` を書いた、またはOllamaが `127.0.0.1` のまま|IPで書く。[4節](#4-gb10側-lanへ公開する)のsystemd設定を確認|
|`/v1/responses` が404|そのOllamaにResponses APIが無い|`wire_api = "chat"` にする。[3節](#道具を呼んで結果を返せるか)|
|`ollama show` に `tools` が無い|そのモデルが道具呼び出しに対応していない|**別のモデルにする。** ここは設定で埋められない|
|`fully_on_gpu` が `False`|コンテキストが大きすぎる|`num_ctx` を 65536 にして `ollama create` をやり直す|
|`ollama ps` が `100% CPU`|OllamaがGB10のGPUを掴めていない|Ollamaの版を上げる。**この状態では他の設定は全部無意味**|
|文脈を伸ばしたのに読む量が増えない|`config.toml` だけ直して、モデルに焼いていない|[2節](#2-gb10側-コンテキスト長を伸ばす)。数字を変えるだけでは効かない|
|設定が効かない|VS Codeを開き直していない、または `CODEX_HOME` が渡っていない|[5節](#置き場所)のコマンドで開き直す|

## 関連

- [VS CodeでColabのgpt-oss:20bを使う](vscode-colab-agent.md) — 起動補助を使う元の手順。コンテキスト長の選び方はこちらにある
- [docs/mcp-tool-not-called.md](mcp-tool-not-called.md) — 道具が呼ばれないときの切り分け
- [VS CodeのClaude CodeをGB10へ向ける](claude-code-gb10.md) — Codexではなく Claude Code を使う場合。変換プロキシが1つ要る
- [GB10のvLLM + gpt-oss-120b でCodexとClaude Codeを使う](vllm-gb10-coding-agent.md) — OllamaではなくvLLMを使う場合
