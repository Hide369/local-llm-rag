# VS CodeのClaude CodeをGB10のGemma 4 31BからQwen3-Coder-Nextへ切り替える（プロキシなし）

[VS CodeのClaude CodeをGB10のGemma 4 31Bへ切り替える](../gemma/claude-code-gb10-gemma4-31b.md)で
使っている `gemma4:31b-256k` を、**`qwen3-coder-next:q8_0-256k`** に置き換える手順。
推論サーバーは GB10 の Ollama のまま替えず、プロキシも立てない。

```text
Windows（VS Code + Claude Code 拡張 + ~/.claude/settings.json）
        │ HTTP（社内LAN）/ Anthropic Messages API（/v1/messages）
        ▼
GB10 → Ollama :11434 → qwen3-coder-next:q8_0-256k（常駐）
```

**前提:** [Gemma の手順](../gemma/claude-code-gb10-gemma4-31b.md)が済み、Claude Code から
`gemma4:31b-256k` を使えていること。この文書はその差分だけを書く。

Gemma の手順の[7節](../gemma/claude-code-gb10-gemma4-31b.md#7-qwen3-coder-next-を消す任意)で
Qwen を**消したかどうかで、GB10 側の作業量が変わる。** 1節で確かめて分岐する。

|Qwen の状態|GB10 側でやること|
|---|---|
|残っている（7節をしていない）|1節で確かめるだけ。2節は飛ばす|
|消した|1節で取り直し（約85GB）、2節で別名を作り直す|

まだ Gemma の手順の7節より前で、`settings.json.qwen.bak` が残っているなら、この文書は要らない。
[Gemma の手順の「元に戻す」](../gemma/claude-code-gb10-gemma4-31b.md#元に戻す)で `.bak` を戻せば済む。

**`gemma4:31b` は、Claude Code から Qwen を使えると確かめるまで消さない。** 消すのは最後の
[7節](#7-gemma4-を消す任意)で、任意である。

> **未検証である。** Ollama のソースと各モデルのページを確かめて組んだが、GB10 の実機で
> 通した記録はまだ無い。各段階の「成功の目安」で確かめながら進めること。

## 目次

- [0. 何を変えるか](#0-何を変えるか)
- [1. GB10: Qwen があるか確かめ、無ければ取得する](#1-gb10-qwen-があるか確かめ無ければ取得する)
- [2. GB10: 文脈長を伸ばした別名を作る（消した場合だけ）](#2-gb10-文脈長を伸ばした別名を作る消した場合だけ)
- [3. GB10: 思考の指定を付けても通るか確かめる](#3-gb10-思考の指定を付けても通るか確かめる)
- [4. GB10: 実配置と道具呼び出しを確かめる](#4-gb10-実配置と道具呼び出しを確かめる)
- [5. Windows: ~/.claude/settings.json を書き換える](#5-windows-claudesettingsjson-を書き換える)
- [6. 起動して確かめる](#6-起動して確かめる)
- [7. gemma4 を消す（任意）](#7-gemma4-を消す任意)
- [文脈長と圧縮](#文脈長と圧縮)
- [元に戻す](#元に戻す)
- [つまずきやすいところ](#つまずきやすいところ)
- [出典](#出典)

## 0. 何を変えるか

|場所|変更|理由|
|---|---|---|
|GB10 Ollama|`qwen3-coder-next:q8_0-256k` があるか確かめ、無ければ取得して別名を作る|Gemma の手順の7節で消していることがある|
|GB10 Ollama の常駐設定|変えない|`OLLAMA_MAX_LOADED_MODELS=1` / `OLLAMA_KEEP_ALIVE=-1` は Qwen にもそのまま効く|
|Windows `~/.claude/settings.json`|モデル名の5か所を替え、`CLAUDE_CODE_DISABLE_THINKING=1` を**戻す**|Qwen は思考しないので、思考の指定を送らない設定に戻す（下記）|
|VS Code の settings.json|変えない|`claudeCode.disableLoginPrompt` はそのまま|

### Gemma との違い

|項目|gemma4:31b|**qwen3-coder-next:q8_0**|
|---|---|---|
|構造|Dense（30.7B を毎トークン全部使う）|**MoE（80B のうち1トークンに使うのは約3B）**|
|重み|約20GB（Q4_K_M）|**85GB**|
|文脈長|256K|256K|
|思考|する（止められない）|**しない**|
|入力|テキストと画像|テキスト|

生成は Gemma より速くなる見込みである。Qwen は1トークンに約3B分しか読まないので、
毎トークン約20GB を読む Gemma より読み出しが少ない。思考の分の生成も無くなる。
代わりに重みが4倍以上あるので、**読み込み（GB10 の再起動後の1回目）は長くなる。**

### 思考の指定は送らない設定に戻す

Gemma の手順では、思考を止められないので `CLAUDE_CODE_DISABLE_THINKING` を消した。
Qwen は思考しないモデルなので、この行を**戻す**。

戻さなくても Claude Code は動く見込みである。Ollama は `/v1/messages` 経由のときだけ、
思考しないモデルへの思考の指定を黙って捨てて通す（3節で確かめる）。それでも、送らない
ほうが確実である。理由は [Qwen の Claude Code 版の0節](claude-code-gb10-qwen3-coder-next.md#0-なぜプロキシが要らないか)と同じ。

## 1. GB10: Qwen があるか確かめ、無ければ取得する

```bash
ollama list | grep -E 'qwen3-coder-next|gemma4'
```

**`qwen3-coder-next:q8_0` と `qwen3-coder-next:q8_0-256k` の両方が出る場合:** 消していない。
`ollama show qwen3-coder-next:q8_0-256k --parameters` で `num_ctx 262144` があることだけ見て、
[3節](#3-gb10-思考の指定を付けても通るか確かめる)へ進む。

**出ない場合:** 取り直す。

```bash
df -h /usr/share/ollama ~/.ollama 2>/dev/null   # 85GB 以上の空き（Gemma の 20GB はまだ残る）
ollama pull qwen3-coder-next:q8_0                # 約85GB
ollama show qwen3-coder-next:q8_0
```

**成功の目安:**

- Capabilities に **`tools` があり、`thinking` が無い**
- Parameters に `temperature 1` / `top_k 40` / `top_p 0.95`（Qwen の推奨値）

Gemma を載せている Ollama は Qwen3-Next の構造も読めるはずなので、版が古いと言われる
ことはまず無い。`requires a newer version of Ollama` と出たら Ollama を更新する。

`q8_0` を選ぶ理由（MoE なので8bit でも速度に余裕がある）は
[Qwen の手順の「なぜ q8_0 か」](ollama-gb10-qwen3-coder-next.md#なぜ-q8_0-か)にある。

## 2. GB10: 文脈長を伸ばした別名を作る（消した場合だけ）

1節で取り直した場合だけ行う。**元のモデルは書き換えず、別名で作る。**

```bash
cat <<'EOF' > /tmp/Modelfile.qwen3-coder-next
FROM qwen3-coder-next:q8_0
PARAMETER num_ctx 262144
EOF
ollama create qwen3-coder-next:q8_0-256k -f /tmp/Modelfile.qwen3-coder-next
ollama show qwen3-coder-next:q8_0-256k --parameters   # num_ctx 262144 と temperature 1 など
```

内容は [Qwen の手順の2節](ollama-gb10-qwen3-coder-next.md#2-gb10-文脈長を伸ばした別名を作る)と同じである。

## 3. GB10: 思考の指定を付けても通るか確かめる

Gemma の手順の3節と同じ3通りを Qwen に送る。Qwen では**どれも 200 で、思考のブロックが
返らない**のが正しい。

```bash
ollama stop gemma4:31b-256k 2>/dev/null   # 載っていれば降ろす
python3 - <<'PY'
import json, urllib.request, urllib.error

URL = "http://127.0.0.1:11434/v1/messages"
CASES = {
    "absent":   None,
    "enabled":  {"type": "enabled", "budget_tokens": 1024},
    "disabled": {"type": "disabled"},
}
for name, thinking in CASES.items():
    body = {"model": "qwen3-coder-next:q8_0-256k", "max_tokens": 64,
            "messages": [{"role": "user", "content": "Reply with OK."}]}
    if thinking is not None:
        body["thinking"] = thinking
    req = urllib.request.Request(URL, json.dumps(body).encode(),
                                 {"content-type": "application/json",
                                  "anthropic-version": "2023-06-01", "x-api-key": "ollama"})
    print("--- thinking =", name)
    try:
        with urllib.request.urlopen(req, timeout=600) as res:
            content = json.load(res)["content"]
        print("  HTTP 200 / blocks:", [b["type"] for b in content])
        print("  text:", "".join(b.get("text", "") for b in content)[:80])
    except urllib.error.HTTPError as e:
        print("  HTTP", e.code, e.read().decode()[:300])
PY
```

1回目はモデルの読み込み（85GB）を待つので時間がかかる。

**成功の目安:** 3つとも `HTTP 200 / blocks: ['text']` で、text に `OK` が入っている。

`enabled` が `400 … does not support thinking` になるなら、Ollama が思考の指定を捨てずに
弾いている。5節で `CLAUDE_CODE_DISABLE_THINKING=1` を戻せば Claude Code からは送られない
ので先へ進めるが、Ollama の版を控えておく。

## 4. GB10: 実配置と道具呼び出しを確かめる

### 全部GPUに載ったか

```bash
curl -s http://127.0.0.1:11434/api/ps | python3 -c "
import json, sys
for m in json.load(sys.stdin)['models']:
    print(m['name'])
    print('  context_length:', m['context_length'])
    print('  size (GiB)    :', round(m['size'] / 2**30, 1))
    print('  fully_on_gpu  :', m['size'] == m['size_vram'])
"
free -g
```

**成功の目安:** 載っているのが `qwen3-coder-next:q8_0-256k` だけで、`context_length: 262144`、
`fully_on_gpu: True`。`size` は 90GiB 前後の見込みである。

`False` なら一部がCPUに落ちている。まず Gemma が載ったままでないかを見る（Gemma の約20GB と
並ぶと、128GB に収まらない）。それでも落ちるなら、2節の `num_ctx` を 131072 にして作り直し、
[文脈長と圧縮](#文脈長と圧縮)の `CLAUDE_CODE_MAX_CONTEXT_TOKENS` を足す。

### 道具を呼んで、結果を返せるか

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
Gemma のときと違い思考しないので、`max_tokens` は 512 で足りる。思考の指定も付けない
（5節の設定で Claude Code が送らないのと同じ形）。

### 載せたままにする

```bash
ollama ps     # qwen3-coder-next:q8_0-256k だけが載り、UNTIL が Forever であること
```

GB10 を再起動したときは、最初の1回だけ 85GB の読み込みを待つ。先に
`ollama run qwen3-coder-next:q8_0-256k "hi" > /dev/null` で載せておくとよい。

> **補完用の Ollama を併設している場合:** [タブ補完用のQwen](ollama-gb10-autocomplete.md)
> の `:4000` は別のサービスなので、この置き換えの影響を受けない。メモリの使い方は、
> 補完の手順が前提にしている Qwen の構成に戻る。

## 5. Windows: ~/.claude/settings.json を書き換える

```powershell
Copy-Item $env:USERPROFILE\.claude\settings.json $env:USERPROFILE\.claude\settings.json.gemma.bak
notepad $env:USERPROFILE\.claude\settings.json
```

**書き換える前に `settings.json.gemma.bak` として複製しておく**（上の1行目）。`env` の中だけを
次のように変える。他の設定は残す。

|操作|キー|値|
|---|---|---|
|変える|`ANTHROPIC_MODEL`|`qwen3-coder-next:q8_0-256k`（**`ollama list` の表記と一字一句同じ**）|
|変える|`ANTHROPIC_DEFAULT_OPUS_MODEL` / `…_SONNET_MODEL` / `…_HAIKU_MODEL`|同上|
|変える|`CLAUDE_CODE_SUBAGENT_MODEL`|同上|
|**足す**|`CLAUDE_CODE_DISABLE_THINKING`|`"1"`。[0節](#思考の指定は送らない設定に戻す)|
|そのまま|`ANTHROPIC_BASE_URL` / `ANTHROPIC_AUTH_TOKEN` / `ANTHROPIC_API_KEY` ほか|接続先は同じ GB10 の Ollama|

変更後の `env`（[`docs/qwen/claude-settings.json`](claude-settings.json) と同じ。IP は自分の環境に合わせる）:

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

**モデル名は5か所とも替える。** 1つでも Gemma の名前が残ると、その要求のたびに Ollama が
Qwen を降ろして Gemma を読み込み、次の本筋の要求でまた Qwen（85GB）を読み直す
（`OLLAMA_MAX_LOADED_MODELS=1` のため）。エラーにならないので気づきにくい。

Gemma のときに `CLAUDE_CODE_MAX_CONTEXT_TOKENS` を足していたら、[文脈長と圧縮](#文脈長と圧縮)を見て
残すか決める。

`claudeCode.environmentVariables`（VS Code の settings.json 1つにまとめる方式）で書いている
場合は、そちらの同じキーを同じように変える。

書き換えたら **VS Code をすべてのウィンドウごと閉じてから起動し直す。**

## 6. 起動して確かめる

Claude Code のパネルを開き、`/status` と打つ。

**成功の目安:** 接続先に `http://192.168.1.50:11434`、モデルに `qwen3-coder-next:q8_0-256k` が出る。

**新しい会話で始める。** Gemma のときの会話を再開すると、履歴に Gemma の思考のブロックが
残っている。Ollama はそれを履歴として Qwen に渡すが、思考しないモデルがそれをどう扱うかは
確かめていない。

続けて、Gemma のときと同じ依頼を出す。

```
このリポジトリの README.md が何を説明しているか、ファイルを読んで答えて
```

- **応答が返ること** — 返らなければ3・4節に戻る。GB10 までは切り分け済みなので、差は設定である
- **思考が表示されないこと** — Qwen は思考しない
- **ファイルを実際に読みに行くこと** — 読まずに一般論を答えるなら、道具呼び出しが効いていない
- **小さな修正を1つ頼み、編集してテストを走らせるところまで行くこと**

GB10 側でも見ておく。

```bash
ollama ps     # qwen3-coder-next:q8_0-256k だけが載っていること（gemma4 に入れ替わっていない）
journalctl -u ollama --since "5 min ago" | grep -E 'v1/messages|does not support' | tail
```

`POST "/v1/messages"` が 200 で並んでいればよい。`/v1/messages/count_tokens` の 404 は
想定内である。

### Gemma と比べる

Gemma の手順の6節で測った結果があれば、同じ課題で Qwen も測って並べる。測り方は
[Ollama版の8節](../gb10-coding-agent.md#8-効果を測る)と同じ（課題10件、各3回、「道具を
呼んだか」「テストが通ったか」と1課題あたりの所要時間）。**7節の前に済ませること。**

## 7. gemma4 を消す（任意）

6節までで、Claude Code から Qwen を使えること、使い続けると決めたことを確かめてから行う。

```bash
ollama rm gemma4:31b-256k gemma4:31b   # 約20GB 空く
ollama list                            # qwen3-coder-next の2つだけ残ること
```

Windows 側の `settings.json.gemma.bak` も要らなくなる。**消した後で Gemma に戻すには、
[Gemma の手順](../gemma/claude-code-gb10-gemma4-31b.md)の1節から（約20GB の取り直し）やり直す。**

## 文脈長と圧縮

Gemma のときと同じである。Claude Code は知らないモデル名の文脈長を **200K と見なし**、
その手前で会話を圧縮する。Ollama 側は 262144 なので、**このままにしておく。** 余白を残す理由は
[Qwen の Claude Code 版の「文脈長と圧縮」](claude-code-gb10-qwen3-coder-next.md#文脈長と圧縮)にある。

`CLAUDE_CODE_MAX_CONTEXT_TOKENS` は、**Qwen の別名の `num_ctx` に合わせて**決める。

|Qwen の `num_ctx`（4節）|`CLAUDE_CODE_MAX_CONTEXT_TOKENS`|
|---|---|
|262144|**書かない**（Gemma のときに 131072 へ下げて足していたら消す）|
|131072|`"98304"`（131072 の3/4）|

## 元に戻す

7節の前なら、GB10 のモデルは両方そろっている。

```powershell
Copy-Item $env:USERPROFILE\.claude\settings.json.gemma.bak $env:USERPROFILE\.claude\settings.json
```

VS Code を起動し直す。GB10 側は、最初の要求が来たとき Ollama が Qwen を降ろして Gemma を
読み込む（`OLLAMA_MAX_LOADED_MODELS=1` のため）。

Qwen をやめると決めたら、GB10 側も片づける。

```bash
ollama rm qwen3-coder-next:q8_0-256k qwen3-coder-next:q8_0   # 約85GB 空く
```

## つまずきやすいところ

|症状|原因|対処|
|---|---|---|
|`ollama pull` が途中で止まる、空きが足りない|85GB 要る|`df -h` で空きを見る。足りなければ先に7節で Gemma を消す（戻る道は Gemma の取り直しになる）|
|1回目の要求がとても遅い、または切れる|85GB の読み込み待ち|[4節](#載せたままにする)の最後で先に載せておく|
|ときどき Gemma に入れ替わる、要求のたびに長く待つ|`settings.json` に Gemma の名前が1つ残っている|5か所とも `qwen3-coder-next:q8_0-256k` か確かめる。`ollama ps` で載っている名前を見る|
|`model "qwen3-coder-next…" not found`|`ANTHROPIC_MODEL` と `ollama list` の名前の食い違い、または2節を飛ばした|`ollama list` の表記をそのまま写す。無ければ2節|
|`400 … does not support thinking`|思考の指定が Qwen に届いた|`CLAUDE_CODE_DISABLE_THINKING=1` を戻したか確かめる。Ollama を更新する|
|再開した会話でおかしな応答やエラーになる|履歴に Gemma の思考のブロックが残っている|新しい会話で始める（[6節](#6-起動して確かめる)）|
|`fully_on_gpu: False`|Gemma が載ったまま、または文脈が長すぎる|`ollama ps` で確認。だめなら 131072 へ（[4節](#4-gb10-実配置と道具呼び出しを確かめる)）|
|ターンが途中で終わる（「〜を読みます:」で止まる）|Qwen3-Coder-Next で報告がある|「続けて」と送る|
|設定が効かない|JSON の構文エラー|`//` コメントと末尾カンマを消す。足した行の前の行にカンマがあるか見る|

## 出典

- [Ollama: qwen3-coder-next](https://ollama.com/library/qwen3-coder-next) — タグ（q8_0 は 85GB）、256K、既定のパラメータ
- [Ollama: gemma4:31b](https://ollama.com/library/gemma4:31b) — 約20GB、Dense
- Ollama のソース `middleware/anthropic.go`・`server/routes.go`（`relax_thinking`：`/v1/messages` 経由のときだけ、思考しないモデルへの思考指定を捨てて通す）、`anthropic/anthropic.go`（履歴の思考ブロックを保持する）
- Claude Code 側の設定項目の出典は [Qwen の Claude Code 版の出典](claude-code-gb10-qwen3-coder-next.md#出典)と同じ
- [Qwen3-Coder-Next discussions #15](https://huggingface.co/Qwen/Qwen3-Coder-Next/discussions/15) — ターンが途中で終わる報告
