# VS CodeのClaude CodeをGB10のgpt-oss:120bへ向ける

Windows の VS Code で Claude Code を使い、推論は社内LANのGB10（DGX Spark）に置いた
`gpt-oss:120b` に行わせる手順。**MCPは使わない。**

## 先に読むこと

**Claude Code は Anthropic Messages API（`/v1/messages`）しか話さない。** Ollamaは
それを出さないので、**変換プロキシを1つ挟むことが避けられない**。MCPは使わないが、
プロキシは要る。ここを飛ばして `ANTHROPIC_BASE_URL` にOllamaを直接書いても動かない。

そのうえで、選ぶ前に知っておくべきことが3つある。

1. **Anthropicが想定・サポートする構成ではない。** 動かなくなっても公式の窓口は無い。
   Claude Code の更新で壊れる可能性がある
2. **Claude Code は Claude モデル前提で作られている。** プロンプト、ツール定義、
   思考の扱いがそれに合わせてある。別のモデルを繋ぐと、道具呼び出しの取りこぼしや
   噛み合わない応答が出やすい。DGX Spark上でエージェント用途を比べた外部の
   ベンチマークでは、**gpt-oss:120b がツール呼び出しで不正なJSONを出して失敗した**
   という報告がある
3. **同じ目的なら Codex + gpt-oss のほうが確実である。**
   [GB10のOllamaでコーディングエージェントを動かす](gb10-coding-agent.md) の経路は、
   このリポジトリで実際に使ってきたもので、モデルとの噛み合わせも確認済みの形になって
   いる。**Claude Code を選ぶ理由が「使い慣れているから」だけなら、そちらを勧める。**

> **未検証である。** 手元にGB10が無いため、この手順を通しで実行した記録は無い。
> 各段階に「何が出れば成功か」を書いたので、そこで確かめながら進めること。

## 構成

```text
Windows（VS Code + Claude Code 拡張）
        │ Anthropic Messages API（/v1/messages）
        ▼
GB10:4000  LiteLLM        ← ここで Anthropic形式 ⇄ Ollama形式 を変換する
        │ OpenAI形式
        ▼
GB10:11434 Ollama → gpt-oss:120b
```

プロキシはGB10の上で動かす。Windows側に増やすものは無い。

## 目次

- [1. GB10側: Ollamaを用意する](#1-gb10側-ollamaを用意する)
- [2. GB10側: LiteLLMを立てる](#2-gb10側-litellmを立てる)
- [3. GB10側: 変換が効いているか確かめる](#3-gb10側-変換が効いているか確かめる)
- [4. Windows側: Claude Codeを入れる](#4-windows側-claude-codeを入れる)
- [5. Windows側: 接続先を設定する](#5-windows側-接続先を設定する)
- [6. 動かして確かめる](#6-動かして確かめる)
- [MCPについて](#mcpについて)
- [うまくいかないとき](#うまくいかないとき)

## 1. GB10側: Ollamaを用意する

[GB10のOllamaでコーディングエージェントを動かす](gb10-coding-agent.md) の1節と同じ。

```bash
ollama pull gpt-oss:120b
ollama ps            # PROCESSOR 列が 100% GPU であること
```

**`100% CPU` なら、以降の手順は全部意味を失う。** 先にそれを解決する。

LiteLLMは同じGB10の上で動かすので、**Ollamaを `0.0.0.0` へ広げる必要は無い**。
`127.0.0.1:11434` のままでよい。外へ開くのはLiteLLMの4000番だけにする。

コンテキスト長を伸ばすなら、Ollama側に焼く。

```bash
cat <<'EOF' > /tmp/Modelfile
FROM gpt-oss:120b
PARAMETER num_ctx 131072
EOF
ollama create gpt-oss:120b-131k -f /tmp/Modelfile
ollama run gpt-oss:120b-131k "hi" && ollama ps   # 全層がGPUに載っているか
```

載りきらなければ `num_ctx` を 65536 に下げる。**Claude Code側から `num_ctx` は
指定できない**ので、ここで決まった値がそのまま上限になる。

## 2. GB10側: LiteLLMを立てる

```bash
python3 -m venv ~/litellm && ~/litellm/bin/pip install 'litellm[proxy]'
```

`~/litellm/config.yaml`:

```yaml
model_list:
  # Claude Code から見えるモデル名（左）と、Ollamaの実体（右）
  - model_name: gpt-oss-120b
    litellm_params:
      model: ollama_chat/gpt-oss:120b-131k
      api_base: http://127.0.0.1:11434

litellm_settings:
  # Claude Code が送るが Ollama が解さないパラメータを落とす。
  # これが無いと、未知のキーで弾かれる要求が出る。
  drop_params: true

general_settings:
  # Claude Code の ANTHROPIC_AUTH_TOKEN にこの値を入れる。
  # LAN内でもプロキシは認証を持たせる。Ollamaと違い、ここは設定できる。
  master_key: sk-<十分に長いランダム文字列>
```

```bash
~/litellm/bin/litellm --config ~/litellm/config.yaml --host 0.0.0.0 --port 4000
```

常時稼働させるなら systemd に載せる（[docs/vllm-gb10.md の3節](vllm-gb10.md#3-常時稼働させるsystemd)
と同じ形で、`ExecStart` を上のコマンドに置き換える）。

> **`master_key` は必ず設定する。** LiteLLMを `0.0.0.0` に開いた時点で、LANから
> 届く全員がGB10のモデルを使える。Ollamaと違ってここは認証を掛けられるのだから、
> 掛ける。

## 3. GB10側: 変換が効いているか確かめる

**Claude Codeを入れる前に、プロキシ単体で確かめる。** ここが通らなければ、
Claude Code側をいくら設定しても動かない。

```bash
curl http://127.0.0.1:4000/v1/messages \
  -H "x-api-key: sk-<master_key>" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{
    "model": "gpt-oss-120b",
    "max_tokens": 128,
    "messages": [{"role": "user", "content": "12*17"}]
  }'
```

Anthropic形式の応答（`{"content":[{"type":"text","text":"204"...}]}` の形）が返ること。

**道具呼び出しも試す。** Claude Code の動作はここに懸かっている。

```bash
curl http://127.0.0.1:4000/v1/messages \
  -H "x-api-key: sk-<master_key>" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{
    "model": "gpt-oss-120b",
    "max_tokens": 256,
    "tools": [{
      "name": "read_file",
      "description": "Read a file from the workspace.",
      "input_schema": {
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"]
      }
    }],
    "messages": [{"role": "user", "content": "README.md の中身を見てほしい"}]
  }'
```

`"type": "tool_use"` を含むブロックが返れば、道具が使える。**返らない、あるいは
`input` が壊れたJSONなら、そこがこの構成の限界である。** 上の「先に読むこと」で
挙げた2番目の懸念が現実になった状態で、設定では直せない。

Windows側からも届くか確かめる。

```powershell
curl.exe http://<GB10のIP>:4000/health
```

## 4. Windows側: Claude Codeを入れる

**この経路に Python は要らない。** 設定は `settings.json` に書くだけで、この
リポジトリも起動補助（`scripts/coding_agent.py`）も使わない。要るのは
**Node.js / npm** と VS Code である。Codex 側だけが Python を使う
（[GB10のOllamaでコーディングエージェントを動かす](gb10-coding-agent.md#windows側に要るもの)）。

VS Code の拡張機能から **Claude Code** を入れる。拡張は内部で Claude Code CLI を
起動するので、CLIも入れておく。

```powershell
npm install -g @anthropic-ai/claude-code
claude --version
```

**この時点ではまだAnthropicにログインしない。** 次の設定を入れてから起動する。

## 5. Windows側: 接続先を設定する

`%USERPROFILE%\.claude\settings.json` に `env` ブロックを置く。

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "http://192.168.1.50:4000",
    "ANTHROPIC_AUTH_TOKEN": "sk-<master_key>",
    "ANTHROPIC_MODEL": "gpt-oss-120b",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "gpt-oss-120b",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "gpt-oss-120b",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "gpt-oss-120b",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
    "DISABLE_TELEMETRY": "1"
  }
}
```

|キー|なぜ要るか|
|---|---|
|`ANTHROPIC_BASE_URL`|**末尾に `/v1` を付けない。** Claude Code側が `/v1/messages` を足す|
|`ANTHROPIC_AUTH_TOKEN`|`Authorization: Bearer <値>` として送られる。LiteLLMの `master_key` と一致させる|
|`ANTHROPIC_MODEL`|既定で使うモデル。`config.yaml` の `model_name` と一致させる|
|`ANTHROPIC_DEFAULT_HAIKU_MODEL`|**これを忘れない。** `haiku` は裏で走る処理（要約など）に使われる。潰さないと存在しないモデル名がプロキシへ飛ぶ|
|`ANTHROPIC_DEFAULT_SONNET_MODEL` / `_OPUS_MODEL`|`/model` で切り替えたときの行き先。潰しておかないと、切り替えた瞬間に落ちる|
|`CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`|本筋以外の外部通信を止める。社内で閉じる構成では付けておく|
|`DISABLE_TELEMETRY`|同上|

**`ANTHROPIC_API_KEY` は設定しない。** 設定するとサブスクリプションより優先され、
どちらの認証が効いているのか分からなくなる。`ANTHROPIC_AUTH_TOKEN` だけにする。

JSONは厳密である。**`//` のコメントも末尾のカンマも構文エラー**になり、
Claude Code は起動時に Settings Error として報告する。

プロジェクトごとに分けたいなら `.claude/settings.local.json` に書く。ユーザー設定
より優先される。**`master_key` を書くので、共有される `.claude/settings.json` には
書かないこと。**

設定したら **VS Code を再起動する。** 起動済みのウィンドウには反映されない。

## 6. 動かして確かめる

VS Code で Claude Code を開き、何か聞く。

```
このリポジトリの ingest/backend.py が何をしているか、ファイルを読んで説明して
```

見るのは2つ。

- **応答が返ること** — 返らなければ3節のcurlに戻る。プロキシまでは切り分け済みなので、
  差は認証かモデル名である
- **ファイルを実際に読みに行くこと** — 読まずに一般論を答えるなら、道具呼び出しが
  効いていない。3節の2つ目のcurlで `tool_use` が返っていたかを確かめる

GB10側でどのモデルが動いているかも見ておく。

```bash
ollama ps        # gpt-oss:120b-131k が 100% GPU で載っていること
```

### 裏で走る処理を軽いモデルへ逃がす

`haiku` の行き先を120bにすると、要約のような軽い処理にも120bが使われる。GB10の
帯域を食うので、小さいモデルへ分けたほうがよい。

```yaml
# config.yaml に足す
  - model_name: gpt-oss-20b
    litellm_params:
      model: ollama_chat/gpt-oss:20b
      api_base: http://127.0.0.1:11434
```

```json
"ANTHROPIC_DEFAULT_HAIKU_MODEL": "gpt-oss-20b"
```

**2つのモデルが同時にメモリへ載る。** 120b（約60GiB）と20b（約12GiB）で、
128GBには収まる見込みだが、`ollama ps` で実際の配置を確かめること。

## MCPについて

**この構成では MCP tool search が既定で無効になる。** Claude Code は
`ANTHROPIC_BASE_URL` が Anthropic 以外を指しているとき、これを自分で切る。
`tool_reference` ブロックを転送できないプロキシがあるためで、今回は MCP を使わない
のだから、むしろ都合がよい。

MCPサーバーを足したくなった場合も、この既定のままで普通のMCPは使える（無効になるのは
「tool search」という、道具が多いときに検索で絞る仕組みだけである）。ただし
**道具の定義が増えるほど、道具呼び出しの成否はモデルの出来に懸かる。** 3節の2つ目の
curlで結果が怪しかったなら、MCPを足す前にそこを直すこと。

## うまくいかないとき

|症状|原因|対処|
|---|---|---|
|401 / 403|`ANTHROPIC_AUTH_TOKEN` と `master_key` の不一致|両方を見比べる。`Bearer ` は自動で付くので値に含めない|
|404 `/v1/v1/messages`|`ANTHROPIC_BASE_URL` に `/v1` を付けた|ホストとポートまでにする|
|モデルが見つからない|`ANTHROPIC_MODEL` と `config.yaml` の `model_name` の不一致|左側（`model_name`）を書く。`ollama_chat/...` の右側ではない|
|普段は動くが、たまに落ちる|`haiku` の行き先が未設定|`ANTHROPIC_DEFAULT_HAIKU_MODEL` を設定する|
|ファイルを読まずに答える|道具呼び出しが効いていない|3節の2つ目のcurlで切り分ける。**設定では直らない**|
|応答が途中で切れる|Ollama側の `num_ctx` 不足|1節でコンテキストを焼き直す。Claude Code側からは指定できない|
|設定が効かない|VS Codeを再起動していない、またはJSONの構文エラー|再起動する。Settings Error が出ていないか見る|
|Anthropicへログインを求められる|`settings.json` の場所か綴りが違う|`%USERPROFILE%\\.claude\\settings.json` であること|

## 関連

- [GB10のOllamaでコーディングエージェントを動かす](gb10-coding-agent.md) — Codex経路。**同じ目的なら、まずこちらを試すこと**
- [Claude Code 環境変数リファレンス](https://code.claude.com/docs/en/env-vars)
- [LiteLLM `/v1/messages`](https://docs.litellm.ai/docs/anthropic_unified/)
