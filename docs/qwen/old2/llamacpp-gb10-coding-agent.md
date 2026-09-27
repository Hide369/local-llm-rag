# GB10のllama.cppでコーディングエージェントを動かす（Qwen3-Coder-Next）

GB10（DGX Spark）で動かしている **Ollama + `gpt-oss:120b`** を、コーディング専用の
**llama.cpp（`llama-server`）+ Qwen3-Coder-Next Q4_K_M** に入れ替える手順。
クライアントは今までどおり Windows の VS Code + Codex拡張 + `config.toml` である。

```text
Windows（VS Code + Codex拡張 + config.toml / models.json）
        │ HTTP（社内LAN）+ APIキー / Responses API
        ▼
GB10（DGX OS） → systemd → llama-server :4000 → Qwen3-Coder-Next Q4_K_M（256K）
```

GB10側の作業は [setup_qwen3_coder_next.sh](setup_qwen3_coder_next.sh) にまとめてある。
**段階を分けてあり、`gpt-oss:120b` を消すのは Codex から動くと確かめた後の最後の段階だけ**
である。それまでは `rollback` 1回で元の Ollama に戻せる。

> **未検証である。** 2026-09-27 時点の llama.cpp（`b11205`）と Codex の仕様を
> 調べて組んだが、GB10 の実機で通しで実行した記録はまだ無い。各段階に
> 「何が出れば成功か」を書いたので、そこで確かめながら進めること。

## 目次

- [0. Ollama版との違い](#0-ollama版との違い)
- [1. GB10: 前提を確かめる](#1-gb10-前提を確かめる)
- [2. GB10: ビルドとモデルの取得（Ollamaは動かしたまま）](#2-gb10-ビルドとモデルの取得ollamaは動かしたまま)
- [3. GB10: 常駐させる（ここでOllamaが止まる）](#3-gb10-常駐させるここでollamaが止まる)
- [4. GB10: メモリの載り方を見る](#4-gb10-メモリの載り方を見る)
- [5. GB10: LANへの公開範囲を絞る](#5-gb10-lanへの公開範囲を絞る)
- [6. Windows: APIキーを渡す](#6-windows-apiキーを渡す)
- [7. Windows: config.toml](#7-windows-configtoml)
- [8. Windows: models.json](#8-windows-modelsjson)
- [9. 起動して確かめる](#9-起動して確かめる)
- [10. gpt-oss:120b を削除する（最後に）](#10-gpt-oss120b-を削除する最後に)
- [元に戻す](#元に戻す)
- [llama.cpp を更新する](#llamacpp-を更新する)
- [つまずきやすいところ](#つまずきやすいところ)
- [出典](#出典)

## 0. Ollama版との違い

|項目|Ollama版（[gb10-coding-agent.md](../../gb10-coding-agent.md)）|この手順|
|---|---|---|
|推論サーバー|Ollama（`ollama.service`）|llama.cpp の `llama-server`（`qwen3-coder.service`）|
|モデル|`gpt-oss:120b`（思考あり）|Qwen3-Coder-Next 80B-A3B Q4_K_M（**思考なし**、約48.4GB）|
|コンテキスト長|Modelfile と `ollama create` で焼く|起動フラグ `--ctx-size 262144`|
|ポート|11434|4000|
|認証|無し（付けられない）|**APIキー必須**（`--api-key-file`）|
|Codex の `wire_api`|`responses`|`responses`（**`chat` は今の Codex では使えない**、[7節](#wire_api-は-responses-にする)）|
|起動補助 `scripts/coding_agent.py`|使える|**使えない。** `/api/tags` `/api/show` など Ollama 固有のAPIを叩くため|
|確認手段|`/api/ps`、`ollama ps`|スクリプトの `verify`、`journalctl`、`free -g`|

入れ替えの理由は「コーディング専用のモデルにする」ことである。**上がったかどうかは
測って決める**（[9節](#比べてから決める)）。モデルを替えれば良くなるとは限らない。

## 1. GB10: 前提を確かめる

スクリプトを GB10 へ運ぶ。**Windows のチェックアウトから運ぶ場合、改行が CRLF に
なっていないこと**を確かめる（このリポジトリは `.gitattributes` で `*.sh` を LF に
固定している）。

```powershell
scp docs\qwen\old2\setup_qwen3_coder_next.sh <ユーザー>@<GB10のIP>:~/
```

GB10 で:

```bash
uname -m                      # aarch64
nvidia-smi                    # NVIDIA GB10 が見えること
ls /usr/local/cuda/bin/nvcc   # CUDA Toolkit（無ければ build が止まる）
df -h /opt                    # 60GB 以上の空き
```

`nvidia-smi` の Memory-Usage は GB10 では `Not Supported` と出る。ユニファイド
メモリなので、メモリは `free -g` で見る（[4節](#4-gb10-メモリの載り方を見る)）。

## 2. GB10: ビルドとモデルの取得（Ollamaは動かしたまま）

```bash
sudo bash ~/setup_qwen3_coder_next.sh build
```

この段階では **Ollama に一切触れない**。今の Codex 環境は使い続けられる。

|やること|中身|
|---|---|
|前提の確認|aarch64、`nvidia-smi`、`nvcc`（sudo 下で PATH に無ければ `/usr/local/cuda/bin` を足す）|
|パッケージ|`git cmake build-essential curl libssl-dev openssl ca-certificates`|
|llama.cpp|`/opt/llama.cpp` に clone し、**`b11205` に固定して** `llama-server` だけビルドする|
|モデル|`Qwen/Qwen3-Coder-Next-GGUF` の Q4_K_M 4分割を `/opt/models/Qwen3-Coder-Next-Q4_K_M/` へ|

**モデルはリビジョンと SHA-256 で固定している。** 取得した各ファイルをハッシュで
照合し、一致しなければ止まる。途中で切れても、もう一度 `build` を打てば続きから
取る（`curl -C -`）。

ビルドは `CMAKE_CUDA_ARCHITECTURES` を指定しない。GB10 の上でビルドすると
llama.cpp が `native`（ビルド時に見えるGPU）を選ぶからである。別の機械でビルド
して持ち込む運用にはしないこと。

**成功の目安:** 最後に `build 完了。Ollama には触れていません。` と出る。

### 外へ出る通信

`build` だけが外部へ出る。宛先は `github.com`（llama.cpp の取得）、
`huggingface.co` とそのCDN（モデルの取得）、apt のミラーである。送るのは
URLへの要求だけで、社内の情報は含まない。常駐するサーバーはモデルをローカルの
パスから読み（`-hf` を使わない）、起動のたびに外へ出ることは無い。

オフラインの GB10 に入れる場合は、接続できる機械で `/opt/llama.cpp` の clone と
モデルの4ファイルを用意して同じパスへ運べば、`build` はビルドだけを行う
（取得済みのファイルは飛ばす）。

## 3. GB10: 常駐させる（ここでOllamaが止まる）

```bash
sudo bash ~/setup_qwen3_coder_next.sh install
```

|やること|中身|
|---|---|
|サービス用ユーザー|`llama`（ログイン不可のシステムユーザー）|
|APIキー|`/etc/llama/qwen3-coder.keys`（`root:llama` 0640）。**既にあれば作り直さない**|
|Ollama|`systemctl disable --now ollama`。**止めるだけで、モデルは消さない**|
|systemd|`/etc/systemd/system/qwen3-coder.service` を書いて起動|
|待つ|`/health` が ok になるまで（最大900秒）|
|確かめる|`verify` を自動で実行（下）|

Ollama を止めるのは、128GB のユニファイドメモリに `gpt-oss:120b`（約65GB）と
並べて載せられないからである。

### 起動フラグ

|フラグ|値|理由|
|---|---|---|
|`--model`|4分割の1本目|残りは llama.cpp が自動で読む|
|`--alias`|`qwen3-coder-next`|Codex の `model` と `models.json` の `slug` に書く名前|
|`--api-key-file`|`/etc/llama/qwen3-coder.keys`|LANへ開くので必須。`/health` だけはキー無しで通る|
|`--ctx-size`|`262144`|このモデルが素で持つ長さ|
|`--parallel`|`1`|既定の auto はスロットを複数作り、`--ctx-size` を分け合ってしまう|
|`--n-gpu-layers`|`999`|全層をGPUへ|
|`--flash-attn`|`on`||
|`--jinja`|—|モデルのチャットテンプレートで道具呼び出しを組み立てる。**エージェントには必須**|
|`--no-context-shift`|—|文脈があふれたら古い部分を黙って捨てず、エラーにする。Codex 側の圧縮に任せる|
|`--temp` / `--top-p` / `--top-k` / `--min-p`|`1.0` / `0.95` / `40` / `0`|Qwen のモデルカードの推奨値。llama-server の既定（temp 0.8 など）とは違う|

systemd 側は `ProtectSystem=strict` などで書き込める場所を絞り、CUDA のキャッシュ用に
`/var/lib/llama` だけを与えている。

### verify が確かめること

`install` の最後に自動で走る。後から単独でも打てる。

```bash
sudo bash ~/setup_qwen3_coder_next.sh verify
```

```text
OK: キーなしは 401
OK: /v1/models に qwen3-coder-next
OK: /v1/responses で function_call
OK: 道具の結果を受け取って回答
```

**4行目までが出れば成功である。** 3行目は「道具を呼ぶか」、4行目は「道具の結果を
受け取って答えに使うか」で、エージェントの1往復そのものである。Codex が叩くのと
同じ `/v1/responses` で確かめている。

## 4. GB10: メモリの載り方を見る

```bash
free -g
journalctl -u qwen3-coder --no-pager | grep -Ei 'buffer size|kv|CUDA'
```

見積もりは次のとおりである。**実測で置き換えること。**

|内訳|見積もり|根拠|
|---|---|---|
|重み（Q4_K_M）|約45GiB|4ファイルの合計 48.4GB|
|KVキャッシュ（256K、f16）|約6GiB|KVを持つのは48層のうち full attention の12層だけ（KVヘッド2本、次元256）。残り36層は Gated DeltaNet で、文脈長に比例するKVを持たない|
|計算用バッファ等|数GiB||

gpt-oss:120b（131072 で Ollama 上）より軽く、256K でも余裕がある見込みである。
逆に言えば、**余裕があるからといって `--parallel` を上げる前に、1本で安定することを
確かめる。** 上げる場合は `sudo PARALLEL=2 CTX_SIZE=524288 bash ... install` の
ように、1本あたりの長さが保たれるよう `CTX_SIZE` も倍にする。

## 5. GB10: LANへの公開範囲を絞る

APIキーで守られているが、届く範囲も絞っておく。`ufw` を使う場合:

```bash
sudo ufw status
# 無効なら、有効にする前に必ず SSH を許可する（締め出されないように）
sudo ufw allow OpenSSH
sudo ufw allow from 192.168.1.0/24 to any port 4000 proto tcp   # 社内のサブネットに合わせる
sudo ufw enable
```

Ollama を止めたので、11434 番を開けていた規則があれば消してよい。
**インターネット側へ 4000 番を開けないこと。**

## 6. Windows: APIキーを渡す

キーを GB10 から読む（`sudo` があるので `-t` を付ける）。

```powershell
ssh -t <ユーザー>@<GB10のIP> sudo cat /etc/llama/qwen3-coder.keys
```

ユーザー環境変数に置く。**`config.toml` にキーを直接書かない。**

```powershell
[Environment]::SetEnvironmentVariable("GB10_LLAMA_API_KEY", "<上で表示された値>", "User")
```

**VS Code をすべてのウィンドウごと終了してから起動し直す。** 環境変数は起動した
プロセスにしか渡らない。「Reload Window」では古い環境のままである。新しい
ターミナルで `$env:GB10_LLAMA_API_KEY` が表示されれば渡っている。

## 7. Windows: config.toml

**書き換える前に、今の `config.toml` を `config.toml.ollama` として複製しておく。**
[元に戻す](#元に戻す)ときにそのまま使う。

置き場所（`%USERPROFILE%\.codex\config.toml` か、`CODEX_HOME` で分けるか）の考え方は
[Ollama版の5節](../../gb10-coding-agent.md#置き場所)と同じである。

```toml
model = "qwen3-coder-next"
model_provider = "gb10-llama"
model_catalog_json = 'C:\Users\you\.codex\models.json'
model_context_window = 262144
model_auto_compact_token_limit = 196608
model_supports_reasoning_summaries = false
model_reasoning_summary = "none"
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

[model_providers.gb10-llama]
name = "GB10 llama.cpp Qwen3-Coder-Next"
base_url = "http://192.168.1.50:4000/v1"
wire_api = "responses"
env_key = "GB10_LLAMA_API_KEY"
request_max_retries = 1
stream_max_retries = 0
stream_idle_timeout_ms = 600000

[shell_environment_policy]
exclude = ["GB10_LLAMA_API_KEY"]

[windows]
sandbox = "unelevated"

[analytics]
enabled = false
```

### 確かめる値

|キー|値|意味|
|---|---|---|
|`model`|`"qwen3-coder-next"`|**`--alias` と `models.json` の `slug` の3か所で一致させる**|
|`base_url`|`"http://<GB10のIP>:4000/v1"`|末尾の `/v1` を落とさない。ポートは 11434 ではない|
|`wire_api`|`"responses"`|下記|
|`env_key`|`"GB10_LLAMA_API_KEY"`|[6節](#6-windows-apiキーを渡す)の環境変数の**名前**。値ではない|
|`model_context_window`|`262144`|`--ctx-size` と揃える|
|`model_auto_compact_token_limit`|`196608`|文脈の3/4。`--no-context-shift` なので、あふれる前にCodexに圧縮させる|
|`stream_idle_timeout_ms`|`600000`|長い文脈を最初に読み込む間はトークンが1つも来ない。既定の5分では切られうる|
|`model_supports_reasoning_summaries` / `model_reasoning_summary`|`false` / `"none"`|思考しないモデルなので、思考の要約を求めない|

`model_reasoning_effort` は書かない。Qwen3-Coder-Next は思考しないので効かない。

### wire_api は responses にする

**今の Codex は `wire_api = "chat"` を受け付けない。** 設定を読んだ時点で
「`` `wire_api = "chat"` is no longer supported `` … set `wire_api = "responses"`」
というエラーになる（公式の設定リファレンスでも `responses` が唯一の値）。
`chat` に変えた `config.toml` は `responses` に戻すこと。

llama-server の `/v1/responses` は、受けた要求を内部で Chat Completions に変換して
処理する。道具呼び出しは `--jinja` 付きで動く。[3節の verify](#verify-が確かめること)
がこの経路を確かめている。

### APIキーをエージェントのシェルへ渡さない

`[shell_environment_policy] exclude` は、Codex が開くシェルにキーの環境変数を
渡さないための設定である。既定では名前に `KEY` を含む変数も**引き継がれる**。

## 8. Windows: models.json

[`docs/qwen/old2/models.json`](models.json) を `config.toml` の `model_catalog_json` が
指す場所へ置く。Ollama版の雛形（`infra/codex-colab/models.json`）から、次を
変えてある。

|キー|値|
|---|---|
|`slug`|`"qwen3-coder-next"`（**`config.toml` の `model` と一致**）|
|`display_name`|`"Qwen3-Coder-Next Q4_K_M (GB10 llama.cpp)"`|
|`context_window` / `max_context_window`|`262144`|
|`comp_hash`|`"local-qwen3-coder-next-q4km-v1"`（他と重複しない値）|
|`supported_reasoning_levels`|1段だけ（思考しないので段を選ぶ意味が無い）|
|`default_reasoning_summary`|`"none"`|

## 9. 起動して確かめる

VS Code を起動し直し、Codex のモデル一覧で `Qwen3-Coder-Next Q4_K_M (GB10 llama.cpp)`
を選ぶ。

```
このリポジトリの README.md が何を説明しているか、ファイルを読んで答えて
```

- **応答が返ること** — 返らなければ [つまずきやすいところ](#つまずきやすいところ)
- **ファイルを実際に読みに行くこと** — 読まずに一般論を答えるなら、道具呼び出しが効いていない
- **ファイルを編集してテストを走らせるところまで行くこと** — 小さな修正を1つ頼む

GB10 側でも見ておく。

```bash
journalctl -u qwen3-coder -f     # 要求が来ていること、エラーが無いこと
```

### 比べてから決める

**`gpt-oss:120b` を消す前に、入れ替えて良くなったかを測る。** 測り方は
[Ollama版の8節](../../gb10-coding-agent.md#8-効果を測る)と同じにする（実作業から10件、
各3回、数えるのは「道具を呼んだか」「テストが通ったか」の2つだけ）。

両方を同時には載せられないので、切り替えて測る。

```bash
# gpt-oss:120b で測るとき
sudo systemctl stop qwen3-coder && sudo systemctl start ollama
# Qwen3-Coder-Next で測るとき
sudo systemctl stop ollama && sudo systemctl start qwen3-coder
```

Windows 側は `config.toml` と `config.toml.ollama` を差し替えて、VS Code を起動し直す。

## 10. gpt-oss:120b を削除する（最後に）

9節までで**Codex から Qwen3-Coder-Next を使えること、そして使い続けると決めたこと**を
確かめてから実行する。

```bash
sudo bash ~/setup_qwen3_coder_next.sh remove-gpt-oss
```

`yes` と打たない限り何もしない。`ollama rm` にはOllamaのサーバーが要るので、削除の
間だけ起こして、終わったら元の状態（止まっていれば止める）に戻す。モデルを読み込む
わけではないので、`llama-server` と並べてもメモリは足りる。

**Ollama 本体は残す。** 完全に消すかどうかは別に判断する。消した後に Ollama へ戻す
には、`ollama pull gpt-oss:120b` で約65GBを取り直すことになる。

## 元に戻す

### GB10

```bash
sudo bash ~/setup_qwen3_coder_next.sh rollback
```

`qwen3-coder` を止めて自動起動を切り、Ollama の自動起動を戻して起こす。
`gpt-oss:120b` が既に消されていれば、取り直すよう表示する。llama.cpp とモデルの
ファイル（`/opt/llama.cpp`、`/opt/models/…`）は残る。要らなければ手で消す（約50GB）。

### Windows

`config.toml.ollama` を `config.toml` に戻し、`models.json` も Ollama版のものに戻す。
VS Code を起動し直す。

## llama.cpp を更新する

`LLAMA_CPP_REF` を新しいビルド番号にして `build` をやり直し、再起動して `verify` を打つ。

```bash
sudo LLAMA_CPP_REF=b11300 bash ~/setup_qwen3_coder_next.sh build
sudo systemctl restart qwen3-coder
sudo bash ~/setup_qwen3_coder_next.sh verify
```

**master を追わない。** Qwen3-Coder-Next は llama.cpp 側の修正に出力の質が左右されて
きた（2026-02 に出力の破損と道具呼び出しの解析が直っている）。動いた番号を
スクリプトの既定値に書き戻して残すこと。問題が出たら、前の番号で同じことをすれば戻る。

## つまずきやすいところ

|症状|原因|対処|
|---|---|---|
|Codex が起動時に `wire_api = "chat" is no longer supported`|今の Codex は `chat` を受け付けない|`wire_api = "responses"`。[7節](#wire_api-は-responses-にする)|
|Codex が 401|APIキーが渡っていない|`$env:GB10_LLAMA_API_KEY` を新しいターミナルで確認。VS Code を**全部閉じてから**起動し直す|
|Codex がモデルを見つけない|`model`・`slug`・`--alias` の食い違い|3か所に `qwen3-coder-next`|
|接続できない|ポート違い、または ufw|`curl.exe http://<GB10のIP>:4000/health` を Windows から。`{"status":"ok"}` なら経路は通っている|
|ターンが途中で終わる（「〜を読みます:」で止まる）|このモデルと Codex の組み合わせで報告がある|「続けて」と送る。改善しなければ llama.cpp を更新する|
|道具呼び出しが本文にテキストで出る|`--jinja` が無い、または古い llama.cpp|ユニットを確認。`verify` の3行目で分かる|
|長い作業の途中で応答が止まり、タイムアウト|文脈の読み込みに時間がかかっている|`stream_idle_timeout_ms` を上げる。`journalctl` で処理中か見る|
|文脈があふれたというエラー|`--no-context-shift` で止めている|`model_auto_compact_token_limit` を下げる|
|`install` の待ちが終わらない / 落ちる|メモリ不足、CUDA エラー|`journalctl -u qwen3-coder -n 100`。メモリなら `sudo CTX_SIZE=131072 bash ... install`|
|ログに GPU が無い旨（`no CUDA-capable device`）|`llama` ユーザーが `/dev/nvidia*` を開けない|`ls -l /dev/nvidia*`。0666 でなければ `usermod -aG video llama`|
|`build` で `nvcc が見つかりません`|CUDA Toolkit が無い|DGX OS の CUDA を確認。`/usr/local/cuda/bin/nvcc` があれば自動で拾う|
|`build` でハッシュ不一致|取得の破損、または上流の差し替え|表示された `.part` を消して `build` をやり直す。繰り返すなら上流を確認し、スクリプトの `HF_REVISION` とハッシュを見直す|
|`scripts/coding_agent.py --check` が失敗|Ollama 固有のAPIを叩く|この構成では使わない。`verify` を使う|

## 出典

- [Qwen/Qwen3-Coder-Next-GGUF](https://huggingface.co/Qwen/Qwen3-Coder-Next-GGUF) — 推奨サンプリング、262,144 トークン、思考なし、量子化ごとの大きさ
- [llama.cpp server README](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md) — `/v1/responses`、`/health` がキー不要であること、`--parallel` の既定値 auto
- [Codex 設定リファレンス](https://learn.chatgpt.com/docs/config-file/config-reference) — `wire_api` は `responses` のみ、`env_key`、`stream_idle_timeout_ms`
- [openai/codex discussions #7782](https://github.com/openai/codex/discussions/7782) — `chat` の廃止
- [Unsloth: Qwen3-Coder-Next](https://unsloth.ai/docs/models/qwen3-coder-next) — 2026-02 の llama.cpp 側の修正
- [Qwen3-Coder-Next discussions #15](https://huggingface.co/Qwen/Qwen3-Coder-Next/discussions/15) — Codex + llama.cpp でターンが途中で終わる報告
- [ggml-org/llama.cpp#19305](https://github.com/ggml-org/llama.cpp/issues/19305) — 出力の破損
