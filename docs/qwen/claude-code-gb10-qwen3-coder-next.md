# VS CodeのClaude CodeをGB10のQwen3-Coder-Nextへ向ける（プロキシなし）

[GB10のOllamaを Qwen3-Coder-Next（q8_0）に置き換える](ollama-gb10-qwen3-coder-next.md)で
載せた `qwen3-coder-next:q8_0-256k` を、Codex ではなく **VS Code の Claude Code 拡張**から
使う手順。**GB10 側には何も足さない**（変換プロキシを立てない）。クライアント側は
**`settings.json` を2つ書くだけ**である。

```text
Windows（VS Code + Claude Code 拡張 + ~/.claude/settings.json）
        │ HTTP（社内LAN）/ Anthropic Messages API（/v1/messages）
        ▼
GB10 → Ollama :11434 → qwen3-coder-next:q8_0-256k（常駐、Codex と共用）
```

**前提:** [Qwen の手順](ollama-gb10-qwen3-coder-next.md)の**1〜5節**が済み、GB10 の
Ollama が `0.0.0.0:11434` で `qwen3-coder-next:q8_0-256k` を載せていること。Windows 側の
Codex の設定（6・7節）は要らない。Codex と併用してもよい（[下記](#codex-と併用する)）。

> **未検証である。** Ollama のソースと Claude Code のドキュメントを確かめて組んだが、
> GB10 の実機で通した記録はまだ無い。各段階の「成功の目安」で確かめながら進めること。
> 特に[1節](#1-gb10-anthropic-形式で答えるか確かめる)は、この構成が成り立つかどうかの関門である。

**Anthropic が想定・サポートする構成ではない。** Claude Code のドキュメントは、ゲートウェイ
経由で Claude 以外のモデルへ繋ぐことをサポートしないと明記している。プロンプトも道具の
定義も Claude に合わせて作られているので、道具呼び出しの取りこぼしは Codex より出やすい
と見ておく。どちらが良いかは[5節](#codex-と比べる)で測って決める。

## 目次

- [0. なぜプロキシが要らないか](#0-なぜプロキシが要らないか)
- [1. GB10: Anthropic 形式で答えるか確かめる](#1-gb10-anthropic-形式で答えるか確かめる)
- [2. Windows: 拡張を入れる](#2-windows-拡張を入れる)
- [3. Windows: ~/.claude/settings.json を書く](#3-windows-claudesettingsjson-を書く)
- [4. Windows: VS Code の settings.json を書く](#4-windows-vs-code-の-settingsjson-を書く)
- [5. 起動して確かめる](#5-起動して確かめる)
- [文脈長と圧縮](#文脈長と圧縮)
- [Codex と併用する](#codex-と併用する)
- [何が外へ出るか](#何が外へ出るか)
- [元に戻す](#元に戻す)
- [つまずきやすいところ](#つまずきやすいところ)
- [出典](#出典)

## 0. なぜプロキシが要らないか

**Ollama は v0.14.0（2026-01）から Anthropic Messages API（`/v1/messages`）を自分で
話す。** [VS CodeのClaude CodeをGB10へ向ける](../claude-code-gb10.md)は、それより前の
前提で LiteLLM を挟んでいた。いまは `ANTHROPIC_BASE_URL` に Ollama を直接書けば届く。
Qwen3-Coder-Next を読める Ollama はこれより新しいので、[Qwen の手順の1節](ollama-gb10-qwen3-coder-next.md#1-gb10-モデルを取得する)
が通っていれば版は足りている。

Codex で問題になった「思考の指定で 400」も、この経路では起きない。

|経路|思考しないモデルに思考を指定したとき|
|---|---|
|`/v1/responses`（Codex）|`400 … does not support thinking`。だから Codex 側で `none` を持たせた|
|**`/v1/messages`（Claude Code）**|**指定を黙って捨てて通す。** Ollama は Claude Code のためにこの経路だけ緩めている|

念のため、Claude Code 側でも思考の指定を送らない設定にする（[3節](#3-windows-claudesettingsjson-を書く)の
`CLAUDE_CODE_DISABLE_THINKING`）。

Ollama の `/v1/messages` に無いものと、そのとき Claude Code がどうなるか:

|無いもの|Claude Code 側の影響|
|---|---|
|`/v1/messages/count_tokens`|文字数からの概算で文脈の使用量を数える。`/context` の数字は目安になる|
|`cache_control`（プロンプトキャッシュ）|エラーにはならず無視される。Ollama は自前で先頭一致の KV を再利用する|
|`tool_choice`|無視される。道具を使うかはモデル任せになる|
|API キーの検証|しない。`ANTHROPIC_AUTH_TOKEN` は何を入れても通る（空にはしない）|

## 1. GB10: Anthropic 形式で答えるか確かめる

**GB10 の設定は変えない。** 確かめるだけである。

```bash
ollama --version                       # 0.14.0 以上
ollama ps                              # qwen3-coder-next:q8_0-256k が載っている（UNTIL が Forever）
```

### 思考の指定を付けても通るか

Claude Code が送りうる形（思考の指定つき）で1回投げる。

```bash
curl -s -w '\nHTTP %{http_code}\n' http://127.0.0.1:11434/v1/messages \
  -H 'content-type: application/json' \
  -H 'anthropic-version: 2023-06-01' \
  -H 'x-api-key: ollama' \
  -d '{"model":"qwen3-coder-next:q8_0-256k","max_tokens":64,
       "thinking":{"type":"enabled","budget_tokens":1024},
       "messages":[{"role":"user","content":"Reply with OK."}]}'
```

**成功の目安:** `HTTP 200` で、`"content":[{"type":"text","text":"OK"…` の形が返る。
[Qwen の手順の3節](ollama-gb10-qwen3-coder-next.md#3-gb10-思考の指定で弾かれないことを確かめる)で
`medium` が 400 になったのと対照的に、ここは通るのが正しい。**400 なら Ollama が古い。**
先へ進まず Ollama を更新する。

### 道具を呼んで、結果を返せるか

Codex 版の4節と同じ往復を、Anthropic 形式で行う。

```bash
python3 - <<'PY'
import json, urllib.request

URL = "http://127.0.0.1:11434/v1/messages"
MODEL = "qwen3-coder-next:q8_0-256k"
TOOL = {"name": "get_probe_value",
        "description": "Returns the fixed connection probe value.",
        "input_schema": {"type": "object", "properties": {}, "required": []}}
PROMPT = "Call get_probe_value exactly once, then tell me the value it returned."

def post(messages):
    body = {"model": MODEL, "max_tokens": 512, "tools": [TOOL], "messages": messages}
    req = urllib.request.Request(URL, json.dumps(body).encode(),
                                 {"content-type": "application/json",
                                  "anthropic-version": "2023-06-01", "x-api-key": "ollama"})
    with urllib.request.urlopen(req, timeout=600) as res:
        return json.load(res)

first = post([{"role": "user", "content": PROMPT}])
uses = [b for b in first["content"] if b["type"] == "tool_use"]
print("tool_use     :", bool(uses), "/ stop_reason:", first["stop_reason"])
if uses:
    second = post([
        {"role": "user", "content": PROMPT},
        {"role": "assistant", "content": first["content"]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": uses[0]["id"],
                                      "content": "73190462"}]},
    ])
    print("used result  :", "73190462" in json.dumps(second["content"]))
PY
```

**成功の目安:** `tool_use     : True / stop_reason: tool_use` と `used result  : True`。

### Windows から届くか

```powershell
curl.exe http://192.168.1.50:11434/api/version
```

`{"version":"0.…"}` が返ればよい。IP は GB10 のものに置き換える。Codex で既に使えて
いるなら、ここは通っているはずである。

## 2. Windows: 拡張を入れる

VS Code の拡張機能ビュー（`Ctrl+Shift+X`）で **Claude Code**（発行元 Anthropic）を入れる。
**この経路ではサインインしない。** サインイン画面が出ても閉じてよい（4節で出なくする）。

拡張はチャットパネル用の CLI を同梱しているので、CLI を別に入れる必要は無い。統合
ターミナルで `claude` を叩きたい場合だけ入れる（[クライアントPCで Claude Code を使う](../claude-code-vscode.md#1-拡張機能を入れる)）。
Python も Node.js もこのリポジトリも要らない。

## 3. Windows: ~/.claude/settings.json を書く

接続先はここに書く。このファイルは VS Code 拡張と CLI の両方が読む。

```powershell
notepad $env:USERPROFILE\.claude\settings.json
```

**既にファイルがある場合は、`env` の中身だけを足す（上書きしない）。** 無ければ
[`docs/qwen/claude-settings.json`](claude-settings.json) をそのまま置く。

```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "env": {
    "ANTHROPIC_BASE_URL": "http://192.168.1.50:11434",
    "ANTHROPIC_AUTH_TOKEN": "ollama",
    "ANTHROPIC_API_KEY": "",
    "ANTHROPIC_MODEL": "qwen3-coder-next:q8_0-256k",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "qwen3-coder-next:q8_0-256k",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "qwen3-coder-next:q8_0-256k",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "qwen3-coder-next:q8_0-256k",
    "CLAUDE_CODE_SUBAGENT_MODEL": "qwen3-coder-next:q8_0-256k",
    "CLAUDE_CODE_DISABLE_THINKING": "1",
    "CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS": "1",
    "CLAUDE_CODE_ATTRIBUTION_HEADER": "0",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
    "DISABLE_TELEMETRY": "1"
  }
}
```

|キー|理由|
|---|---|
|`ANTHROPIC_BASE_URL`|GB10 の Ollama。**末尾に `/v1` を付けない。** Claude Code が `/v1/messages` を足す|
|`ANTHROPIC_AUTH_TOKEN`|Ollama は検証しないが、**空だと Claude Code がサインインを求める。** 値は何でもよい|
|`ANTHROPIC_API_KEY`|**空文字で上書きする。** Windows の環境変数に本物のキーが残っていると、そちらが使われる|
|`ANTHROPIC_MODEL`|[Qwen の手順の2節](ollama-gb10-qwen3-coder-next.md#2-gb10-文脈長を伸ばした別名を作る)で作った名前と一字一句同じにする|
|`ANTHROPIC_DEFAULT_OPUS/SONNET/HAIKU_MODEL`|`/model` で `opus` などを選んだときや、裏の軽い処理の行き先。**潰さないと Ollama に無い `claude-…` の名前が飛び、404 になる**|
|`CLAUDE_CODE_SUBAGENT_MODEL`|サブエージェントの行き先。同じ理由で潰す|
|`CLAUDE_CODE_DISABLE_THINKING`|思考の指定を送らない。Ollama は捨ててくれるが、送らないほうが確実である|
|`CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS`|Claude 向けの試験的な欄（`context_management`、道具の `defer_loading` など）を送らない。Ollama は解さない|
|`CLAUDE_CODE_ATTRIBUTION_HEADER`|システムプロンプトの先頭に付く版番号などの行を省く。Anthropic の API はこれを取り除くが、Ollama はそのまま Qwen に読ませてしまう|
|`CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` / `DISABLE_TELEMETRY`|推論以外の Anthropic への通信を止める（[何が外へ出るか](#何が外へ出るか)）|

**JSON は厳密である。** `//` のコメントも末尾のカンマも構文エラーになる。`$schema` の
行があれば、VS Code でこのファイルを開いたとき誤りに波線が付く。

**`ANTHROPIC_BASE_URL` をリポジトリの `.claude/settings.json` に書かないこと。** GB10 の
IP をリポジトリに固定し、Claude を普通に使う他の人の設定まで奪う。個人の設定に置く。

## 4. Windows: VS Code の settings.json を書く

`Ctrl+Shift+P` → **Preferences: Open User Settings (JSON)** で開き、1行足す。

```json
"claudeCode.disableLoginPrompt": true
```

Anthropic へのサインイン画面を出さない設定である。これが無いと、3節の接続先が効いて
いても初回にサインインを促される。

足したら **VS Code をすべてのウィンドウごと閉じてから起動し直す。** 開いていたウィンドウ
には新しい環境変数が渡らない。

### VS Code の settings.json 1つにまとめる場合

3節の `env` を `claudeCode.environmentVariables` に書けば、`~/.claude/settings.json` を
置かずに済む。

```json
"claudeCode.disableLoginPrompt": true,
"claudeCode.environmentVariables": [
  { "name": "ANTHROPIC_BASE_URL", "value": "http://192.168.1.50:11434" },
  { "name": "ANTHROPIC_AUTH_TOKEN", "value": "ollama" },
  { "name": "ANTHROPIC_API_KEY", "value": "" },
  { "name": "ANTHROPIC_MODEL", "value": "qwen3-coder-next:q8_0-256k" },
  { "name": "ANTHROPIC_DEFAULT_OPUS_MODEL", "value": "qwen3-coder-next:q8_0-256k" },
  { "name": "ANTHROPIC_DEFAULT_SONNET_MODEL", "value": "qwen3-coder-next:q8_0-256k" },
  { "name": "ANTHROPIC_DEFAULT_HAIKU_MODEL", "value": "qwen3-coder-next:q8_0-256k" },
  { "name": "CLAUDE_CODE_SUBAGENT_MODEL", "value": "qwen3-coder-next:q8_0-256k" },
  { "name": "CLAUDE_CODE_DISABLE_THINKING", "value": "1" },
  { "name": "CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS", "value": "1" },
  { "name": "CLAUDE_CODE_ATTRIBUTION_HEADER", "value": "0" },
  { "name": "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC", "value": "1" },
  { "name": "DISABLE_TELEMETRY", "value": "1" }
]
```

ただし**公式は3節のやり方を勧めている。** こちらは VS Code の拡張にしか効かず、統合
ターミナルの `claude` には渡らない。また `~/.claude/settings.json` の `env` にも同じキーが
あると、どちらが効いているのか分かりにくくなる。**どちらか一方にする。**

## 5. 起動して確かめる

Claude Code のパネルを開き、`/status` と打つ。

**成功の目安:** 接続先に `http://192.168.1.50:11434`、モデルに
`qwen3-coder-next:q8_0-256k` が出る。Anthropic のアカウントやプランが出るなら、3節の
設定が読まれていない。

続けて、Codex 版の8節と同じ依頼を出す。

```
このリポジトリの README.md が何を説明しているか、ファイルを読んで答えて
```

- **応答が返ること** — 返らなければ1節の curl に戻る。GB10 までは切り分け済みなので、差は接続先かモデル名である
- **ファイルを実際に読みに行くこと** — 読まずに一般論を答えるなら、道具呼び出しが効いていない
- **小さな修正を1つ頼み、編集してテストを走らせるところまで行くこと**

GB10 側でも見ておく。

```bash
ollama ps     # qwen3-coder-next:q8_0-256k だけが載っていること（claude-… の名前で読み込もうとしていない）
journalctl -u ollama --since "5 min ago" | grep -E 'v1/messages|does not support' | tail
```

`POST "/v1/messages"` が 200 で並んでいればよい。`/v1/messages/count_tokens` の 404 は
[0節](#0-なぜプロキシが要らないか)のとおり想定内である。

### Codex と比べる

どちらを使うかは測って決める。測り方は Codex 版と同じ（[Ollama版の8節](../gb10-coding-agent.md#8-効果を測る)：
実作業から課題を10件固定、各3回、数えるのは「道具を呼んだか」「テストが通ったか」の2つ）。
モデルは同じなので、差はエージェント側のプロンプトと道具の定義から来る。

## 文脈長と圧縮

Claude Code は知らないモデル名の文脈長を **200K と見なし**、その手前で会話を圧縮する。
Ollama 側は 262144 なので、**このままにしておく。**

`CLAUDE_CODE_MAX_CONTEXT_TOKENS=262144` で上限を合わせることもできるが、勧めない。
`count_tokens` が無いので Claude Code の数え方は概算であり、Ollama の実際の上限と
ぴったり合わせると余白が無くなる。**Ollama は上限を超えた要求をエラーにせず、古い部分を
黙って切り捨てる**（[Qwen の手順の7節](ollama-gb10-qwen3-coder-next.md#modelsjson-を置かない場合)と
同じ理由）。約6万トークンの余白は、ここで効く。

[Qwen の手順の4節](ollama-gb10-qwen3-coder-next.md#4-gb10-実配置と道具呼び出しを確かめる)で
文脈を 131072 に下げた場合は、既定の 200K では Ollama の上限を超える。同じく余白を
残した値（131072 の3/4）を3節の `env` に足す。

```json
"CLAUDE_CODE_MAX_CONTEXT_TOKENS": "98304"
```

## Codex と併用する

GB10 の設定は変えずに、Codex（`/v1/responses`）と Claude Code（`/v1/messages`）の両方から
同じモデルを使える。モデルは1つしか載らないので、読み込み直しは起きない。

ただし**同時には処理しない。** Ollama の同時処理数は既定で1本なので、誰かの Codex が長く
生成している間、Claude Code の要求は待たされる（逆も同じ）。Claude Code は本筋の要求の
ほかに、会話の題名付けのような軽い要求も同じモデルへ送るので、1人で使っていても
順番待ちが起きうる。同時処理数を上げると 256K の KV が本数倍になり、128GB に収まらない
恐れがある（[タブ補完の手順の0節](ollama-gb10-autocomplete.md#なぜ-ollama-を2つにするか)）。

## 何が外へ出るか

|宛先|何が乗るか|止め方|
|---|---|---|
|GB10（`ANTHROPIC_BASE_URL`）|質問・会話・読んだファイルの中身・道具の結果。**社内LANに留まる**|—|
|Anthropic（テレメトリ、自動更新、機能フラグなど）|使用状況|3節の `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` / `DISABLE_TELEMETRY`|
|`api.anthropic.com`（WebFetch の宛先確認）|WebFetch で取りに行く先のドメイン名|WebFetch を使わせない（下記）|
|WebFetch / WebSearch の宛先|モデルが決めた URL・検索語|同上|

`CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` は、自動更新も止める。**拡張の更新は VS Code
の拡張機能ビューで手で行う。**

社外へ出したくない資料を扱うなら、3節の `settings.json` に `permissions` を足して Web の
道具を封じる（`env` と同じ階層に置く）。

```json
"permissions": {
  "deny": ["WebFetch", "WebSearch"]
}
```

## 元に戻す

1. `~/.claude/settings.json` から3節の `env` のキーを消す（他の設定は残す）
2. VS Code の settings.json から `claudeCode.disableLoginPrompt`（と `claudeCode.environmentVariables`）を消す
3. VS Code を起動し直し、Anthropic のアカウントでサインインする

GB10 側は何も変えていないので、戻す作業は無い。

## つまずきやすいところ

|症状|原因|対処|
|---|---|---|
|サインイン画面が出続ける|`ANTHROPIC_AUTH_TOKEN` が空、または settings.json が読まれていない|3節を見直す。場所は `%USERPROFILE%\.claude\settings.json`。VS Code を全部閉じて起動し直す|
|`/status` に Anthropic のプランが出る|同上|同上|
|404 `/v1/v1/messages`|`ANTHROPIC_BASE_URL` に `/v1` を付けた|ホストとポートまでにする|
|`model "claude-…" not found`|`ANTHROPIC_DEFAULT_*_MODEL` / `CLAUDE_CODE_SUBAGENT_MODEL` の書き漏れ|5つとも Qwen の名前にする|
|`model "qwen3-coder-next…" not found`|`ANTHROPIC_MODEL` と `ollama create` の名前の食い違い|`ollama list` の表記をそのまま写す|
|`400 … does not support thinking`|Ollama が古い（v0.14.0 未満）|Ollama を更新する|
|`Extra inputs are not permitted` などの 400|試験的な欄が送られている|`CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS` を確かめる|
|ファイルを読まずに答える|道具呼び出しが効いていない|1節の Python で切り分ける。そこが通るなら、Claude Code の道具の定義が Qwen に合っていない。**設定では直らない**。Codex を使う|
|1回目の要求がとても遅い、または切れる|GB10 の再起動後で、85GB の読み込み待ち|[Qwen の手順の5節](ollama-gb10-qwen3-coder-next.md#5-gb10-常駐させ2つ目を載せない)の最後で先に載せておく|
|たまに長く待たされる|Codex や他の人の要求の後ろに並んでいる|[Codex と併用する](#codex-と併用する)|
|`/context` の数字が合わない|`count_tokens` が無く概算している|想定内。圧縮は200Kの手前で起きる|
|設定が効かない|JSON の構文エラー|`//` コメントと末尾カンマを消す。Claude Code が Settings Error を出していないか見る|

## 出典

- Ollama のドキュメント `docs/api/anthropic-compatibility.mdx` — `/v1/messages` の対応範囲（`count_tokens`・`tool_choice`・`cache_control` は非対応、API キーは検証しない）、`ANTHROPIC_AUTH_TOKEN=ollama`
- Ollama のドキュメント `docs/integrations/claude-code.mdx` — `ANTHROPIC_BASE_URL` / `ANTHROPIC_AUTH_TOKEN` / `ANTHROPIC_API_KEY=""` の手動設定
- Ollama のソース `middleware/anthropic.go`・`server/routes.go`（`relax_thinking`：`/v1/messages` 経由のときだけ、思考しないモデルへの思考指定を捨てて通す。`#13692`、v0.14.0）、`anthropic/anthropic.go`（`#13600`、v0.14.0 で追加）
- [Claude Code: VS Code](https://code.claude.com/docs/en/vs-code) — `~/.claude/settings.json` は拡張と CLI で共有、`claudeCode.disableLoginPrompt`、`claudeCode.environmentVariables`
- [Claude Code: 環境変数](https://code.claude.com/docs/en/env-vars) — 各キーの意味
- [Claude Code: ゲートウェイ互換ガイド](https://code.claude.com/docs/en/llm-gateway-protocol) — `count_tokens` が無ければ概算、知らないモデル名は200K、`CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS`、システムプロンプト先頭の帰属ブロック
- [Claude Code: モデル設定](https://code.claude.com/docs/en/model-config#correct-the-window-for-a-gateway-or-custom-model-id) — `CLAUDE_CODE_MAX_CONTEXT_TOKENS`
